#!/usr/bin/env python
"""MuJoCo video of the human and the robot body layouts of a reachability run (spec learned v0.8 §7.2).

A 2 x 2 grid rendered by MuJoCo from one fixed camera: the human (capsule skeleton) with the object, then the B2-Z1
with its body placed by each layout (default: prior ``reach_fit``, script ``reach_track``, interaction mesh ``mesh``)
and the arm at the IK solution of one problem (default ``pos_dir``). The object is added to the robot's scene as a
mocap mesh; the contact target is a small sphere; the arm turns red on frames where it does not reach. Contact
frames only (the diagnostic solves those).

Offscreen rendering needs OpenGL: ``MUJOCO_GL=egl`` on a GPU machine, ``MUJOCO_GL=osmesa`` without one. Inputs as for
``render_layouts.py``. Writes <out>/<id>.mp4 and <out>/<id>.png (middle frame).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

os.environ.setdefault("MUJOCO_GL", "egl")
import mujoco  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from scipy.spatial.transform import Rotation as R  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from h2d.common.collision import MOVING_ARM  # noqa: E402
from h2d.common.data.omomo_new import BODY_PARENTS  # noqa: E402
from h2d.common.data.omomo_objects import load_object  # noqa: E402
from h2d.common.data.tasks import load_task  # noqa: E402
from h2d.common.registration import SE2  # noqa: E402
from h2d.common.robot import B2Z1Robot  # noqa: E402
from h2d.learned.prior import load_motion  # noqa: E402
from h2d.paths import load_config, xmorph_path  # noqa: E402

NAMES = {"reach_fit": "prior placement", "reach_track": "script: body follows the object",
         "mesh": "interaction mesh (ours)", "start_anchored": "start-anchored"}
RED = np.array([0.85, 0.2, 0.15, 1.0])


def build_model(obj, width: int, height: int) -> mujoco.MjModel:
    """The robot's scene plus the object as a visual-only mocap mesh."""
    spec = mujoco.MjSpec.from_file(str(xmorph_path(load_config("b2z1.yaml")["xmorph"]["model_xml"])))
    spec.visual.global_.offwidth, spec.visual.global_.offheight = width, height
    mesh = spec.add_mesh()
    mesh.name, mesh.uservert, mesh.userface = "hoi_object", obj.verts.ravel().tolist(), obj.faces.ravel().tolist()
    body = spec.worldbody.add_body()
    body.name, body.mocap = "hoi_object", True
    g = body.add_geom()
    g.type, g.meshname, g.contype, g.conaffinity, g.density = mujoco.mjtGeom.mjGEOM_MESH, "hoi_object", 0, 0, 0
    g.rgba = [0.82, 0.62, 0.38, 1.0]
    return spec.compile()


def add_capsule(scn, a, b, radius, rgba):
    if scn.ngeom >= scn.maxgeom:
        return
    g = scn.geoms[scn.ngeom]
    mujoco.mjv_initGeom(g, mujoco.mjtGeom.mjGEOM_CAPSULE, np.zeros(3), np.zeros(3), np.zeros(9), np.asarray(rgba, np.float32))
    mujoco.mjv_connector(g, mujoco.mjtGeom.mjGEOM_CAPSULE, radius, np.asarray(a, float), np.asarray(b, float))
    scn.ngeom += 1


def add_sphere(scn, p, radius, rgba):
    if scn.ngeom >= scn.maxgeom:
        return
    mujoco.mjv_initGeom(scn.geoms[scn.ngeom], mujoco.mjtGeom.mjGEOM_SPHERE, np.full(3, radius), np.asarray(p, float),
                        np.eye(3).ravel(), np.asarray(rgba, np.float32))
    scn.ngeom += 1


def label(img: np.ndarray, lines: list[str], bad: bool = False) -> np.ndarray:
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im, "RGBA")
    try:
        font = ImageFont.load_default(size=max(12, img.shape[0] // 28))
    except TypeError:                                          # Pillow < 10.1
        font = ImageFont.load_default()
    w = max(d.textlength(t, font=font) for t in lines) + 16
    h = (font.size if hasattr(font, "size") else 11) * 1.35 * len(lines) + 10
    d.rectangle([0, 0, w, h], fill=(0, 0, 0, 140))
    for k, t in enumerate(lines):
        col = (255, 120, 100) if bad and k == len(lines) - 1 else (255, 255, 255)
        d.text((8, 5 + k * (h - 10) / len(lines)), t, fill=col, font=font)
    return np.asarray(im)


def render(tid, task, sol, summary, motion, robot, layouts, problem, out: Path, args):
    c = task["in_contact"].astype(bool)
    fr, ci = task["frames"], np.flatnonzero(c)
    obj = load_object(task["object"])
    model = build_model(obj, args.width, args.height)
    data = mujoco.MjData(model)
    mocap = model.body_mocapid[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "hoi_object")]
    arm_geoms = [g for g in range(model.ngeom)
                 if mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, model.geom_bodyid[g]) in MOVING_ARM]
    arm_rgba = model.geom_rgba[arm_geoms].copy()
    renderer = mujoco.Renderer(model, args.height, args.width)

    v = task["obj_pos"][ci[-1]] - task["obj_pos"][ci[0]]
    push = np.degrees(np.arctan2(v[1], v[0])) if np.linalg.norm(v[:2]) > 1e-3 else 0.0
    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    centre = task["obj_pos"][ci].mean(0)
    back = -np.r_[np.cos(np.radians(push)), np.sin(np.radians(push)), 0.0]
    cam.lookat[:] = centre + 0.45 * back + [0, 0, 0.6 - centre[2]]
    cam.distance, cam.elevation, cam.azimuth = args.distance, args.elevation, push + args.azimuth_offset
    rel = {lay: (summary.get(lay) or {}).get("relations") or {} for lay in layouts}

    def tile(i, j, lay):
        data.mocap_pos[mocap] = task["obj_pos"][i]
        data.mocap_quat[mocap] = R.from_quat(task["obj_rot_xyzw"][i]).as_quat(scalar_first=True)
        if lay is None:                                          # the human: robot out of sight
            q = robot.model.qpos0.copy()
            q[2] = -50.0
            ok = True
        else:
            rp, rq = SE2(float(sol[f"{lay}__psi"][j]), tuple(sol[f"{lay}__b"][j])).apply_root(
                motion.root_pos[fr[i]][None], motion.root_rot_xyzw[fr[i]][None])
            q = robot.qpos_from_xmorph(rp[0], rq[0], motion.dof_pos[fr[i]])
            q[robot.arm_qadr] = sol[f"{lay}__{problem}__q"][j]
            ok = bool(sol[f"{lay}__{problem}__ok"][j])
        data.qpos[:] = q
        model.geom_rgba[arm_geoms] = arm_rgba if ok else RED
        mujoco.mj_forward(model, data)
        renderer.update_scene(data, camera=cam)
        scn = renderer.scene
        if lay is None:
            sk = task["skeleton_world"][i]
            for k, par in enumerate(BODY_PARENTS):
                if par >= 0:
                    add_capsule(scn, sk[par], sk[k], 0.025, (0.16, 0.47, 0.84, 1.0))
        add_sphere(scn, task["target_world"][i], 0.025, (0.1, 0.1, 0.1, 1.0))
        img = renderer.render()
        if lay is None:
            return label(img, ["human", f"t = {(fr[i] - fr[ci[0]]) / task['fps']:.1f} s"])
        r = rel[lay]
        err, ang = 100 * float(sol[f"{lay}__{problem}__err"][j]), float(sol[f"{lay}__{problem}__ang"][j])
        return label(img, [NAMES.get(lay, lay),
                           f"relation to the human: edge {r.get('edge_dir_err_deg', float('nan')):.0f}°, "
                           f"heading {r.get('heading_err_deg', float('nan')):.0f}°",
                           f"{'reached' if ok else 'NOT reached'}: {err:.1f} cm, tool axis {ang:.0f}°"], bad=not ok)

    cols = 2
    cells = [None] + list(layouts)
    rows = (len(cells) + cols - 1) // cols
    js = np.arange(0, len(ci), args.stride)
    W, H = args.width * cols, args.height * rows
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", f"{task['fps'] / args.stride:g}", "-i", "-", "-pix_fmt", "yuv420p", "-vcodec", "libx264",
                            "-crf", "23", str(out / f"{tid}.mp4")], stdin=subprocess.PIPE)
    mid = int(js[len(js) // 2])
    for j in js:
        frame = np.full((H, W, 3), 255, np.uint8)
        for n, lay in enumerate(cells):
            r0, c0 = divmod(n, cols)
            frame[r0 * args.height:(r0 + 1) * args.height, c0 * args.width:(c0 + 1) * args.width] = tile(ci[j], j, lay)
        enc.stdin.write(frame.tobytes())
        if j == mid:
            Image.fromarray(frame).resize((W // 2, H // 2)).save(out / f"{tid}.png", optimize=True)
    enc.stdin.close()
    if enc.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    renderer.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reach-dir", required=True, help="outputs/<run> of reach_diag.py")
    ap.add_argument("--tasks-dir", required=True)
    ap.add_argument("--d0-dir", required=True)
    ap.add_argument("--ids", nargs="*", default=None, help="task ids (default: every solution file)")
    ap.add_argument("--layouts", nargs="*", default=["reach_fit", "reach_track", "mesh"])
    ap.add_argument("--problem", default="pos_dir", choices=["pos", "pos_dir", "pos_dir_budget"])
    ap.add_argument("--stride", type=int, default=2, help="every n-th contact frame (2: 15 fps, real time)")
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--distance", type=float, default=3.8, help="camera distance [m]")
    ap.add_argument("--elevation", type=float, default=-18.0, help="camera elevation [deg]")
    ap.add_argument("--azimuth-offset", type=float, default=120.0, help="camera azimuth relative to the push [deg]")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    rd = Path(args.reach_dir)
    out = Path(args.out or rd / "videos_mujoco")
    out.mkdir(parents=True, exist_ok=True)
    summary = json.loads((rd / "summary.json").read_text())["tasks"]
    ids = args.ids or sorted(p.stem for p in (rd / "solutions").glob("*.npz"))
    robot = B2Z1Robot()
    for tid in ids:
        task = load_task(Path(args.tasks_dir) / f"{tid}.npz")
        sol = np.load(rd / "solutions" / f"{tid}.npz")
        layouts = [lay for lay in args.layouts if f"{lay}__psi" in sol]
        motion = load_motion(Path(args.d0_dir) / f"{task['clip']}_b2z1.pkl")
        render(tid, task, sol, summary.get(tid, {}), motion, robot, layouts, args.problem, out, args)
        print(f"  {tid}: {', '.join(layouts)} -> {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
