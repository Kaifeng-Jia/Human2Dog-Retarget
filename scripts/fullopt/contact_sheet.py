#!/usr/bin/env python
"""Contact sheets of HOI clips (fullopt spec v0.2 §8.3): one MuJoCo still per clip, the person and the object at the
middle of the contact segment, seen from the side of the object -> person line. The person's pelvis path over the
segment is drawn as dots on the floor (blue), the object's centre path in orange, so a still shows who walks where.
Label: id and split, object and hand, how far the pelvis and the object travel over the segment, the hand height.

Writes <out>/<split>_<page>.png (16 clips a page, small enough for the reports branch).
Offscreen rendering: MUJOCO_GL=egl on a GPU machine, MUJOCO_GL=osmesa without one.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from render import BONES, HANDS, SKIN, capsule, label, scene, sphere  # noqa: E402

import mujoco  # noqa: E402
from PIL import Image  # noqa: E402
from scipy.spatial.transform import Rotation as R  # noqa: E402

from h2d.fullopt.hoi import HOIClip, leveled, load_dir  # noqa: E402
from h2d.fullopt.robot import Robot  # noqa: E402

PATH, OBJ = (0.16, 0.47, 0.84, 0.8), (0.92, 0.45, 0.15, 0.9)
PER_PAGE, COLS = 16, 4


def still(robot: Robot, c: HOIClip, args) -> np.ndarray:
    s, e = (int(x) for x in c.meta["segment"])
    t = (s + e) // 2
    m = scene(robot, c, args.width, args.height)
    d = mujoco.MjData(m)
    pel = c.joint("pelvis")
    d.qpos[:] = robot.placed(pel[t, :2], 0.0)               # hidden; the scene light rides on the robot's base
    mocap = m.body_mocapid[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "hoi_object")]
    d.mocap_pos[mocap] = c.obj_pos[t]
    d.mocap_quat[mocap] = R.from_quat(c.obj_quat[t]).as_quat(scalar_first=True)
    mujoco.mj_forward(m, d)
    centre = R.from_quat(c.obj_quat).apply(0.5 * (c.obj_verts.min(0) + c.obj_verts.max(0))) + c.obj_pos
    line = pel[t, :2] - centre[t, :2]
    cam = mujoco.MjvCamera()
    cam.type, cam.distance, cam.elevation = mujoco.mjtCamera.mjCAMERA_FREE, args.distance, args.elevation
    cam.azimuth = float(np.degrees(np.arctan2(line[1], line[0]))) + args.azimuth_offset
    cam.lookat[:] = [*(0.5 * (pel[t, :2] + centre[t, :2])), 0.5]
    gl = mujoco.Renderer(m, args.height, args.width)
    opt = mujoco.MjvOption()
    opt.geomgroup[1] = 0
    gl.update_scene(d, camera=cam, scene_option=opt)
    scn = gl.scene
    J = {n: c.joint(n)[t] for n in c.joint_names}
    for a, b in BONES:
        capsule(scn, J[a], J[b], 0.03, SKIN)
    for a, b in HANDS:
        if b in J:
            capsule(scn, J[a], J[b], 0.012, SKIN, shadow=False)
    sphere(scn, J["head"] + [0, 0, 0.06], 0.08, SKIN)
    for k in range(s, e, max(1, round(c.fps / 6))):
        sphere(scn, [*pel[k, :2], 0.01], 0.015, PATH)
        sphere(scn, [*centre[k, :2], 0.01], 0.015, OBJ)
    img = gl.render()
    gl.close()
    hand = {"L": "left hand", "R": "right hand", "B": "both hands"}.get(c.meta.get("mode"), c.meta.get("mode", ""))
    wrist = [f"{x}_wrist" for x in ("l", "r") if c.meta.get("mode") in (x.upper(), "B")]
    z = np.median([c.joint(w)[s:e, 2] for w in wrist]) if wrist else float("nan")
    walk = np.linalg.norm(pel[e - 1, :2] - pel[s, :2])
    moved = np.linalg.norm(centre[e - 1, :2] - centre[s, :2])
    how = f"{c.meta.get('interaction', '')} ({c.meta.get('grip', '')})"
    what = " · ".join(x for x in (c.meta.get("object"), hand, how) if x.strip(" ()"))
    return label(img, [f"{c.meta.get('id')} · {c.meta.get('split', '')}", what,
                       f"pelvis {walk:.2f} m, object {moved:.2f} m, wrist {z:.2f} m high"])


def pages(tiles: list[np.ndarray], out: Path, name: str, width: int, height: int) -> list[Path]:
    paths = []
    for p in range(0, len(tiles), PER_PAGE):
        chunk = tiles[p:p + PER_PAGE]
        rows = -(-len(chunk) // COLS)
        sheet = np.full((rows * (height + 4), COLS * (width + 4), 3), 255, np.uint8)
        for k, img in enumerate(chunk):
            i, j = divmod(k, COLS)
            sheet[i * (height + 4):i * (height + 4) + height, j * (width + 4):j * (width + 4) + width] = img
        path = out / f"{name}_{p // PER_PAGE + 1}.png"
        Image.fromarray(sheet).quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(
            path, optimize=True)
        paths.append(path)
    return paths


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", required=True, help="folder of HOIClip .npz files (export_hoi.py)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--robot", default="b2z1", help="its model hosts the scene (hidden)")
    ap.add_argument("--width", type=int, default=480)
    ap.add_argument("--height", type=int, default=360)
    ap.add_argument("--distance", type=float, default=3.2, help="camera distance [m]")
    ap.add_argument("--elevation", type=float, default=-18.0, help="camera elevation [deg]")
    ap.add_argument("--azimuth-offset", type=float, default=90.0,
                    help="camera azimuth relative to the object -> person direction [deg] (90: from the side)")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    robot = Robot(args.robot)
    clips = [leveled(c) for c in load_dir(args.clips)]
    for split in sorted({c.meta.get("split", "dev") for c in clips}):
        tiles = [still(robot, c, args) for c in clips if c.meta.get("split", "dev") == split]
        for p in pages(tiles, out, split, args.width, args.height):
            print(f"  {p}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
