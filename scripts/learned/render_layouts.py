#!/usr/bin/env python
"""Side-by-side video of the human and the robot body layouts of a reachability run (spec learned v0.8 §7.2).

Columns: the human; then per layout (default: prior ``reach_fit``, script ``reach_track``, interaction mesh ``mesh``)
the B2-Z1 with its body placed by that layout and the arm at the IK solution of one problem (default ``pos_dir``),
drawn as silhouettes of its collision geometry (no OpenGL needed). Top row: top view; bottom row: side view; both
turned so that the object moves to the right. Contact frames only (the diagnostic solves those).

Inputs: ``reach_diag.py`` outputs (``solutions/<id>.npz`` with the placements, ``summary.json``), the task files and
the prior. Writes <out>/<id>.mp4 and <out>/<id>.png (middle frame).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import animation  # noqa: E402
from scipy.spatial import ConvexHull, QhullError  # noqa: E402
from scipy.spatial.transform import Rotation as R  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from h2d.common.collision import RobotCollision  # noqa: E402
from h2d.common.data.omomo_new import BODY_PARENTS  # noqa: E402
from h2d.common.data.omomo_objects import load_object  # noqa: E402
from h2d.common.data.tasks import load_task  # noqa: E402
from h2d.common.registration import SE2  # noqa: E402
from h2d.common.robot import B2Z1Robot  # noqa: E402
from h2d.learned.prior import load_motion  # noqa: E402

NAMES = {"reach_fit": "prior placement", "reach_track": "script: body follows the object",
         "mesh": "interaction mesh (ours)", "start_anchored": "start-anchored"}
HUMAN, OBJ, OK, BAD = "#2a78d6", "#b5b5b5", "#eb6834", "#c0392b"


def fill_hull(ax, P, **kw):
    try:
        ax.fill(*P[ConvexHull(P).vertices].T, **kw)
    except (QhullError, ValueError):
        pass


def render(tid: str, task: dict, sol, summary: dict, motion, robot, coll, layouts, problem, out: Path, stride: int):
    c = task["in_contact"].astype(bool)
    fr, ci = task["frames"], np.flatnonzero(c)
    obj = load_object(task["object"])
    v = task["obj_pos"][ci[-1]] - task["obj_pos"][ci[0]]
    e1 = np.r_[v[:2] / max(np.linalg.norm(v[:2]), 1e-9), 0.0]           # push direction -> right
    e2 = np.cross([0, 0, 1.0], e1)
    view = lambda P, side: np.stack([P @ e1, P[:, 2] if side else P @ e2], 1)  # noqa: E731
    verts = obj.verts[np.random.default_rng(0).choice(len(obj.verts), min(1500, len(obj.verts)), replace=False)]
    sk = task["skeleton_world"][ci]
    allp = np.concatenate([task["obj_pos"][ci], sk.reshape(-1, 3)])
    lim = [(allp @ e1).min() - 1.0, (allp @ e1).max() + 0.6, (allp @ e2).min() - 0.9, (allp @ e2).max() + 0.9]
    rel = {lay: (summary.get(lay) or {}).get("relations") or {} for lay in layouts}

    fig, axes = plt.subplots(2, 1 + len(layouts), figsize=(4.2 * (1 + len(layouts)), 7.4))

    def frame(j):
        i = ci[j]
        Rm, p = R.from_quat(task["obj_rot_xyzw"][i]).as_matrix(), task["obj_pos"][i]
        ow = verts @ Rm.T + p
        hull_w = obj.hull_verts @ Rm.T + p
        robots = {}
        for lay in layouts:
            rp, rq = SE2(float(sol[f"{lay}__psi"][j]), tuple(sol[f"{lay}__b"][j])).apply_root(
                motion.root_pos[fr[i]][None], motion.root_rot_xyzw[fr[i]][None])
            robot.set_qpos(robot.qpos_from_xmorph(rp[0], rq[0], motion.dof_pos[fr[i]]))
            robot.set_arm(sol[f"{lay}__{problem}__q"][j])
            d = robot.data
            robots[lay] = [coll.samples[g] @ d.geom_xmat[g].reshape(3, 3).T + d.geom_xpos[g] for g in coll.body + coll.arm]
        for row, side in ((0, False), (1, True)):
            for col in range(1 + len(layouts)):
                ax = axes[row, col]
                ax.cla()
                fill_hull(ax, view(hull_w, side), color=OBJ, alpha=0.35, lw=0)
                ax.scatter(*view(ow, side).T, s=0.4, color="#7d7d7d", lw=0)
                ax.scatter(*view(task["target_world"][i][None], side).T, s=70, marker="*", color="k", zorder=5)
                if col == 0:
                    S = view(sk[j], side)
                    for k, par in enumerate(BODY_PARENTS):
                        if par >= 0:
                            ax.plot(*S[[par, k]].T, color=HUMAN, lw=2, solid_capstyle="round")
                    title = "human" if row == 0 else ""
                else:
                    lay = layouts[col - 1]
                    ok = bool(sol[f"{lay}__{problem}__ok"][j])
                    for P in robots[lay]:
                        fill_hull(ax, view(P, side), color=OK if ok else BAD, alpha=0.45, lw=0)
                    err = 100 * float(sol[f"{lay}__{problem}__err"][j])
                    ang = float(sol[f"{lay}__{problem}__ang"][j])
                    r = rel[lay]
                    title = (f"{NAMES.get(lay, lay)}\nrelations: edge {r.get('edge_dir_err_deg', float('nan')):.0f}°, "
                             f"heading {r.get('heading_err_deg', float('nan')):.0f}°" if row == 0 else
                             f"{'reached' if ok else 'not reached'}: {err:.1f} cm, tool axis {ang:.0f}°")
                ax.set_title(title, fontsize=8.5, loc="left", color="k" if row == 0 or col == 0 or ok else BAD)
                ax.set_xlim(lim[0], lim[1])
                ax.set_ylim((0, 1.8) if side else (lim[2], lim[3]))
                ax.set_aspect("equal")
                ax.tick_params(labelsize=6)
        fig.suptitle(f"{tid} · {task['clip']} · t = {(fr[i] - fr[0]) / task['fps']:.1f} s · {problem} · "
                     f"orange = arm reaches, red = not", fontsize=9)
        return []

    js = np.arange(0, len(ci), stride)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    frame(int(js[len(js) // 2]))
    fig.savefig(out / f"{tid}.png", dpi=70)
    if animation.writers.is_available("ffmpeg"):
        anim = animation.FuncAnimation(fig, frame, frames=js, blit=False)
        anim.save(out / f"{tid}.mp4", writer=animation.FFMpegWriter(fps=task["fps"] / stride, bitrate=1800), dpi=80)
    else:
        print("[warn] ffmpeg not available: PNG only", file=sys.stderr)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reach-dir", required=True, help="outputs/<run> of reach_diag.py")
    ap.add_argument("--tasks-dir", required=True)
    ap.add_argument("--d0-dir", required=True)
    ap.add_argument("--ids", nargs="*", default=None, help="task ids (default: every solution file)")
    ap.add_argument("--layouts", nargs="*", default=["reach_fit", "reach_track", "mesh"])
    ap.add_argument("--problem", default="pos_dir", choices=["pos", "pos_dir", "pos_dir_budget"])
    ap.add_argument("--stride", type=int, default=2, help="every n-th contact frame (2: 15 fps, real time)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    rd = Path(args.reach_dir)
    out = Path(args.out or rd / "videos")
    out.mkdir(parents=True, exist_ok=True)
    summary = json.loads((rd / "summary.json").read_text())["tasks"]
    ids = args.ids or sorted(p.stem for p in (rd / "solutions").glob("*.npz"))
    robot = B2Z1Robot()
    coll = RobotCollision(robot)
    for tid in ids:
        task = load_task(Path(args.tasks_dir) / f"{tid}.npz")
        sol = np.load(rd / "solutions" / f"{tid}.npz")
        layouts = [lay for lay in args.layouts if f"{lay}__psi" in sol]
        motion = load_motion(Path(args.d0_dir) / f"{task['clip']}_b2z1.pkl")
        render(tid, task, sol, summary.get(tid, {}), motion, robot, coll, layouts, args.problem, out, args.stride)
        print(f"  {tid}: {', '.join(layouts)} -> {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
