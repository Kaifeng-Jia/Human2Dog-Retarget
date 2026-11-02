#!/usr/bin/env python
"""MuJoCo videos of a solve run (fullopt spec v0.2 §8.3): the human and the robot side by side, one camera.

Left: the human (capsules on the input's semantic joints) with the object; right: the robot of the solve with the
object. Both tiles render one scene (the robot's model plus the object as a visual mocap mesh) from the same camera,
across the object -> human line and panning with the scene (1 s moving average). The scene light moves with the
robot's base, so the human tile hides the robot (geom group 1) instead of moving it away. The contact target is a
dark sphere; on contact frames the arm turns red where the frame is not reached. Per clip: <out>/<id>.mp4 (H.264)
and <out>/<id>.png, a key-frame strip (approach, contact, end) small enough for the reports branch.

A grasp (spec §7.5) adds a third tile, a close-up of the gripper at the grasp point, labels the gripper's opening and
phase, and its strip shows the opening's key frames: fully open before the contact, at the contact, closed, the hold,
reopened and retreating.

Offscreen rendering: MUJOCO_GL=egl on a GPU machine, MUJOCO_GL=osmesa without one.
"""

from __future__ import annotations

import os

# One BLAS / OpenMP thread, set before numpy loads (as solve.py): small problems, where threads only contend.
os.environ.update({k: "1" for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")})

import argparse  # noqa: E402
import json  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

os.environ.setdefault("MUJOCO_GL", "egl")
import mujoco  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from scipy.ndimage import uniform_filter1d  # noqa: E402
from scipy.spatial.transform import Rotation as R  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from h2d.fullopt.hoi import HOIClip, leveled  # noqa: E402
from h2d.fullopt.robot import Robot  # noqa: E402
from h2d.paths import load_config, xmorph_path  # noqa: E402

BONES = [("pelvis", "spine"), ("spine", "chest"), ("chest", "neck"), ("neck", "head")] + [
    (f"{s}_{a}", f"{s}_{b}") for s in "lr" for a, b in (("hip", "knee"), ("knee", "ankle"), ("ankle", "toe"),
                                                       ("shoulder", "elbow"), ("elbow", "wrist"))] + [
    (a, f"{s}_{b}") for s in "lr" for a, b in (("pelvis", "hip"), ("chest", "shoulder"))]
HANDS = [(f"{s}_wrist", f"{s}_{f}") for s in "lr" for f in ("index", "pinky")]
SKIN, TARGET, RED = (0.16, 0.47, 0.84, 1.0), (0.08, 0.08, 0.08, 1.0), np.array([0.85, 0.2, 0.15, 1.0])


def scene(robot: Robot, c: HOIClip, width: int, height: int) -> mujoco.MjModel:
    """The robot's model with the object as a visual-only mocap mesh."""
    spec = mujoco.MjSpec.from_file(str(xmorph_path(load_config("b2z1.yaml")["xmorph"][robot.desc["model_xml"]])))
    spec.visual.global_.offwidth, spec.visual.global_.offheight = width, height
    mesh = spec.add_mesh()
    mesh.name, mesh.uservert, mesh.userface = "hoi_object", c.obj_verts.ravel().tolist(), c.obj_faces.ravel().tolist()
    body = spec.worldbody.add_body()
    body.name, body.mocap = "hoi_object", True
    g = body.add_geom()
    g.type, g.meshname, g.contype, g.conaffinity, g.density = mujoco.mjtGeom.mjGEOM_MESH, "hoi_object", 0, 0, 0
    g.rgba = [0.82, 0.62, 0.38, 1.0]
    m = spec.compile()
    m.mat_reflectance[:] = 0.0
    m.vis.quality.shadowsize = 8192
    m.vis.map.shadowclip = 0.4                  # a tight shadow frustum: sharp shadows of the robot and the human
    return m


def capsule(scn, a, b, radius, rgba, shadow=True):
    if scn.ngeom >= scn.maxgeom:
        return
    g = scn.geoms[scn.ngeom]
    mujoco.mjv_initGeom(g, mujoco.mjtGeom.mjGEOM_CAPSULE, np.zeros(3), np.zeros(3), np.zeros(9),
                        np.asarray(rgba, np.float32))
    mujoco.mjv_connector(g, mujoco.mjtGeom.mjGEOM_CAPSULE, radius, np.asarray(a, float), np.asarray(b, float))
    if not shadow:                              # thin capsules cast striped shadows
        g.category = mujoco.mjtCatBit.mjCAT_DECOR
    scn.ngeom += 1


def sphere(scn, p, radius, rgba):
    if scn.ngeom >= scn.maxgeom:
        return
    mujoco.mjv_initGeom(scn.geoms[scn.ngeom], mujoco.mjtGeom.mjGEOM_SPHERE, np.full(3, radius), np.asarray(p, float),
                        np.eye(3).ravel(), np.asarray(rgba, np.float32))
    scn.ngeom += 1


def label(img: np.ndarray, lines: list[str], bad: bool = False) -> np.ndarray:
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im, "RGBA")
    font = ImageFont.load_default(size=max(12, img.shape[0] // 30))
    step = font.size * 1.35
    width = max(d.textlength(t, font=font) for t in lines) + 16
    d.rectangle([0, 0, width, step * len(lines) + 10], fill=(0, 0, 0, 140))
    for k, t in enumerate(lines):
        red = bad and k == len(lines) - 1
        d.text((8, 5 + k * step), t, fill=(255, 120, 100) if red else (255, 255, 255), font=font)
    return np.asarray(im)


class Renderer:
    def __init__(self, robot: Robot, c: HOIClip, sol, info: dict, args):
        self.robot, self.c, self.sol, self.info, self.args = robot, c, sol, info, args
        self.model = scene(robot, c, args.width, args.height)
        self.data = mujoco.MjData(self.model)
        self.mocap = self.model.body_mocapid[mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "hoi_object")]
        arm = {robot.body_id(b) for b in robot.desc["collision"]["arm_chain"][1:]}
        self.arm = [g for g in range(self.model.ngeom) if self.model.geom_bodyid[g] in arm]
        self.arm_rgba = self.model.geom_rgba[self.arm].copy()
        self.gl = mujoco.Renderer(self.model, args.height, args.width)
        k = max(1, round(c.fps)) | 1
        pel, trunk = c.joint("pelvis"), sol["q"][:, robot.base_qadr:robot.base_qadr + 3]
        side = np.median(pel[:, :2] - c.obj_pos[:, :2], axis=0)
        side /= max(float(np.linalg.norm(side)), 1e-9)
        self.look = uniform_filter1d((c.obj_pos + pel + trunk) / 3.0, k, axis=0, mode="nearest")
        self.look[:, 2] = 0.65
        self.cam = mujoco.MjvCamera()
        self.cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        self.cam.distance, self.cam.elevation = args.distance, args.elevation
        self.cam.azimuth = float(np.degrees(np.arctan2(side[1], side[0]))) + args.azimuth_offset
        self.s, self.e = (int(x) for x in sol["segment"])
        self.grasp = info.get("task", {}).get("grasp") if "theta" in sol else None
        self.cam_close = mujoco.MjvCamera()
        self.cam_close.type, self.cam_close.distance = mujoco.mjtCamera.mjCAMERA_FREE, args.closeup_distance
        self.cam_close.elevation = -10.0
        if self.grasp:                  # the close-up looks along the jaws' width: the opening in the a-c plane
            Ro = R.from_quat(c.obj_quat)
            self.E = Ro.apply(np.asarray(self.grasp["E_local"])) + c.obj_pos
            t = Ro.apply(np.cross(self.grasp["c_local"], self.grasp["a_local"]))
            t *= np.sign(np.sum((trunk - self.E)[:, :2] * t[:, :2], 1) + 1e-9)[:, None]   # the camera off the trunk
            self.az = np.degrees(np.arctan2(t[:, 1], t[:, 0]))
            self.el = np.where(np.abs(t[:, 2]) > 0.7, -80.0, -10.0)    # a post: the jaws' plane is level

    def phase(self, t: int) -> str:
        if not self.grasp:
            return "approach" if t < self.s else "contact" if t < self.e else "after contact"
        p = self.grasp["phases"]
        return ("approach, gripper closed" if t < p["open_start"] else "opening" if t < p["open_done"] else
                "open" if t < self.s else "closing" if t <= p["closed"] else "hold" if t < self.e else
                "reopening" if t <= p["released"] else "retreat" if p["reclose"] is None or t < p["reclose"] else
                "retreat, closing")

    def tile(self, t: int, kind: str) -> np.ndarray:
        c, sol, m, d = self.c, self.sol, self.model, self.data
        d.qpos[:] = sol["q"][t]                     # the robot stays in place: the light rides on its base
        d.mocap_pos[self.mocap] = c.obj_pos[t]
        d.mocap_quat[self.mocap] = R.from_quat(c.obj_quat[t]).as_quat(scalar_first=True)
        i = t - self.s
        ok = not (0 <= i < len(sol["reached"])) or bool(sol["reached"][i])
        m.geom_rgba[self.arm] = self.arm_rgba if ok else RED
        mujoco.mj_forward(m, d)
        opt = mujoco.MjvOption()
        opt.geomgroup[1] = int(kind != "human")
        cam = self.cam if kind != "closeup" else self.cam_close
        if kind == "closeup":
            cam.azimuth, cam.elevation = self.az[t], self.el[t]
        cam.lookat[:] = self.look[t] if kind != "closeup" else self.E[t]
        self.gl.update_scene(d, camera=cam, scene_option=opt)
        scn = self.gl.scene
        if kind == "human":
            J = {n: c.joint(n)[t] for n in c.joint_names}
            for a, b in BONES:
                capsule(scn, J[a], J[b], 0.03, SKIN)
            for a, b in HANDS:
                if b in J:
                    capsule(scn, J[a], J[b], 0.012, SKIN, shadow=False)
            sphere(scn, J["head"] + [0, 0, 0.06], 0.08, SKIN)
        if np.isfinite(sol["target"][t]).all():
            sphere(scn, sol["target"][t], 0.022, TARGET)
        img = self.gl.render()
        sec = f"t = {t / c.fps:.1f} s, {self.phase(t)}"
        if kind == "closeup":
            g = self.grasp
            return label(img, [f"gripper {sol['theta'][t]:.0f}° · {sec}",
                               f"{g['kind']} {g['beta_deg']:.0f}°, w {100 * g['w_m']:.1f} cm, "
                               f"closing {g['theta_c_deg']:.0f}°, mu {g['mu_need']:.2f}"], bad=not ok)
        if kind == "human":
            return label(img, [f"human ({self.info.get('dataset') or 'input'}) · {self.info['object']}", sec])
        lines = [f"{self.robot.desc.get('title', self.robot.name)} · full optimization, pass 1, relation (a)",
                 "the soles slide on the floor (gait: M3) · dark sphere: contact target"]
        if 0 <= i < len(sol["reached"]):
            lines.append(f"{'reached' if ok else 'NOT reached'}: {100 * sol['err'][i]:.1f} cm, tool axis "
                         f"{sol['angle'][i]:.0f}°, body in object {100 * sol['body_in_object'][t]:.1f} cm")
        return label(img, lines, bad=not ok)

    def frame(self, t: int) -> np.ndarray:
        gap = np.full((self.args.height, 4, 3), 255, np.uint8)
        tiles = [self.tile(t, "human"), gap, self.tile(t, "robot")]
        return np.concatenate(tiles + ([gap, self.tile(t, "closeup")] if self.grasp else []), 1)

    def close(self):
        self.gl.close()


def strip(r: Renderer, path: Path, scale: float = 0.6) -> None:
    """Approach, contact and end as rows of a small PNG (palette, under 1 MB for the reports branch)."""
    w0, w1 = (int(x) for x in r.sol["window"])
    picks = [max(w0, r.s - round(0.5 * r.c.fps)), (r.s + r.e) // 2, w1 - 1]
    if r.grasp:                    # fully open, at the contact, closed, the hold, reopened and retreating
        p, scale = r.grasp["phases"], 0.5
        picks = [max(p["open_done"], 0), r.s, p["closed"], (r.s + r.e) // 2, min(p["released"] + 4, r.c.n - 1)]
    W = r.frame(picks[0]).shape[1]
    size = (int(scale * W), int(scale * r.args.height))
    rows = [np.asarray(Image.fromarray(r.frame(t)).resize(size, Image.LANCZOS)) for t in picks]
    img = Image.fromarray(np.concatenate(rows, 0)).quantize(256, method=Image.Quantize.MEDIANCUT,
                                                            dither=Image.Dither.NONE)
    img.save(path, optimize=True)


def render(robot: Robot, c: HOIClip, sol, info: dict, out: Path, args) -> None:
    r = Renderer(robot, c, sol, info, args)
    if args.strips_only:
        strip(r, out / f"{info['id']}.png")
        r.close()
        return
    W, H = r.frame(0).shape[1], args.height
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", f"{c.fps / args.stride:g}", "-i", "-", "-pix_fmt", "yuv420p",
                            "-vcodec", "libx264", "-preset", "veryfast", "-crf", "23", str(out / f"{info['id']}.mp4")],
                           stdin=subprocess.PIPE)
    for t in range(0, c.n, args.stride):
        enc.stdin.write(r.frame(t).tobytes())
    enc.stdin.close()
    if enc.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    strip(r, out / f"{info['id']}.png")
    r.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solve-dir", required=True, help="outputs/<run> of solve.py (summary.json, solutions/)")
    ap.add_argument("--clips", required=True, help="the HOIClip folder the run solved")
    ap.add_argument("--ids", nargs="*", default=None, help="clip ids (default: every solution)")
    ap.add_argument("--stride", type=int, default=1, help="every n-th frame (1: real time at the clip's rate)")
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--distance", type=float, default=3.6, help="camera distance [m]")
    ap.add_argument("--elevation", type=float, default=-20.0, help="camera elevation [deg]")
    ap.add_argument("--azimuth-offset", type=float, default=60.0,
                    help="camera azimuth relative to the object -> human direction [deg] (90: from the side)")
    ap.add_argument("--closeup-distance", type=float, default=0.45, help="grasps: close-up camera distance [m]")
    ap.add_argument("--strips-only", action="store_true", help="the key-frame strips, no video")
    ap.add_argument("--out", default=None, help="default <solve-dir>/videos")
    args = ap.parse_args()
    sd = Path(args.solve_dir)
    out = Path(args.out or sd / "videos")
    out.mkdir(parents=True, exist_ok=True)
    summary = json.loads((sd / "summary.json").read_text())
    info = {r["id"]: r for r in summary["clips"]}
    robot = Robot(summary.get("robot", "b2z1"))
    for p in sorted((sd / "solutions").glob("*.npz")):
        if args.ids and p.stem not in args.ids:
            continue
        c = leveled(HOIClip.load(Path(args.clips) / p.name))
        render(robot, c, dict(np.load(p)), info.get(p.stem, {"id": p.stem, "object": "object"}), out, args)
        print(f"  {p.stem} -> {out / p.stem}" + (".png" if args.strips_only else ".mp4, .png"), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
