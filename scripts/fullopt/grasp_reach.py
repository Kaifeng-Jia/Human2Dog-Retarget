#!/usr/bin/env python
"""Whole-body reach of a grasp (fullopt spec v0.2 §8.5): for a gripper contact-point height z and an approach pitched
down by beta (0: level, jaws closing vertically across a table top; 90: from above, jaws closing horizontally across a
bin rim), is there a pose of the robot with

* the four feet planted at the home stance, the trunk 0.40-0.58 m high (the description's range) and pitched by at
  most ``--max-pitch-deg``, every joint in range;
* no self collision and the arm off the floor (the learned line's collision rules), no leg below the floor;
* the trunk and the legs at least 3 cm behind the vertical plane through the contact point (the part is beyond it)?

The distance ahead is free. Damped least squares on all 24 dofs from a few seeds (home arm and random ones); joints
at a limit leave the step (active set); collisions closer than 1 cm and legs below the floor enter as penalty rows.
A cell that no seed solves is "not found", not proven unreachable. This sets the grasp band of
``configs/fullopt/grasp_selection.yaml``.

Writes <out>/{grasp_reach.json, grasp_reach.png}. Data-free: needs only the robot model.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from h2d.fullopt.robot import Collision, Robot  # noqa: E402

BEHIND_M, CLEAR_M = 0.03, 0.01


class WholeBodyIK:
    def __init__(self, robot: Robot):
        self.r, self.coll = robot, Collision(robot)
        self.D = robot.dofs("base", "legs", "arm")
        self.home = robot.placed([0.0, 0.0], 0.0)
        robot.set(self.home)
        self.anchors = robot.data.xpos[robot.feet].copy()
        jq = robot.dof_qadr[self.D]
        self.lo, self.hi = robot.lower[self.D].copy(), robot.upper[self.D].copy()
        self.lo[2], self.hi[2] = robot.height_range                       # base dof 2: vertical translation
        self.jq = jq

    def _rows(self, q, z, axes):
        r, D, coll = self.r, self.D, self.coll
        r.set(q)
        p = r.tool_point()
        Jp = r.body_point_jac(r.tool_body, p, D)
        e, J = [(p[1:] - [0.0, z])], [Jp[1:]]                            # side and height; the distance ahead is free
        for loc, target in zip((r.approach_local, r.jaw_local), axes):
            e.append(0.3 * (r.axis(r.tool_body, loc) - target))
            J.append(0.3 * r.axis_jac(r.tool_body, loc, D))
        for f, a in zip(r.feet, self.anchors):
            e.append(3.0 * (r.data.xpos[f] - a))
            J.append(3.0 * r.body_point_jac(f, r.data.xpos[f], D))
        b = r.base_qadr
        qw, qx, qy, qz = q[b + 3:b + 7]
        # base y, roll and yaw held (the sagittal plane); pitch and height weakly to nominal (redundancy only)
        w, dof = np.array([3.0, 3.0, 3.0, 0.05, 0.05]), [1, 3, 5, 4, 2]
        sel = np.zeros((5, len(D)))
        sel[np.arange(5), dof] = w
        e.append(w * [q[b + 1], 2 * np.arctan2(qx, qw), 2 * np.arctan2(qz, qw), 2 * np.arctan2(qy, qw),
                      q[b + 2] - r.nominal_height])
        J.append(sel)
        P, B = coll.world_samples(coll.body)                # trunk and legs behind the contact point
        for k in np.flatnonzero(P[:, 0] > p[0] - BEHIND_M):
            e.append([10.0 * (P[k, 0] - p[0] + BEHIND_M)])
            J.append(10.0 * (r.body_point_jac(B[k], P[k], D)[0] - Jp[0])[None])
        gb = r.model.geom_bodyid
        for dist, ft, ga, gg in coll.self_distances(0.03):   # self pairs apart by 1 cm (geoms -> their bodies)
            v = ft[3:] - ft[:3]
            if dist < CLEAR_M and np.linalg.norm(v) > 1e-9:
                n = v / np.linalg.norm(v) * (1.0 if dist >= 0 else -1.0)
                e.append([10.0 * (dist - CLEAR_M)])
                J.append(10.0 * (n @ (r.body_point_jac(gb[gg], ft[3:], D) - r.body_point_jac(gb[ga], ft[:3], D)))[None])
        P, B = coll.world_samples(coll.legs)                 # legs above the floor
        for k in np.flatnonzero(P[:, 2] < 0.005):
            e.append([10.0 * (P[k, 2] - 0.005)])
            J.append(10.0 * r.body_point_jac(B[k], P[k], D)[2][None])
        return np.concatenate([np.ravel(x) for x in e]), np.vstack(J)

    def solve(self, z: float, beta: float, seed, iters: int = 300) -> tuple[bool, dict]:
        r, D = self.r, self.D
        c, s = np.cos(beta), np.sin(beta)
        axes = (np.array([c, 0.0, -s]), np.array([s, 0.0, c]))           # approach pitched down, jaw axis in the plane
        q = self.home.copy()
        q[r.dof_qadr[r.groups["arm"]]] = seed
        for _ in range(iters):
            e, J = self._rows(q, z, axes)
            if np.linalg.norm(e) < 1e-6:
                break
            val = np.full(len(D), np.nan)
            val[self.jq >= 0] = q[self.jq[self.jq >= 0]]
            val[2] = q[r.base_qadr + 2]
            free = np.ones(len(D), bool)
            for _ in range(4):                                  # joints at a limit leave the step
                Jf = J * free
                dx = -Jf.T @ np.linalg.solve(Jf @ Jf.T + 1e-4 * np.eye(len(e)), e)
                stuck = free & (((val <= self.lo + 1e-6) & (dx < 0)) | ((val >= self.hi - 1e-6) & (dx > 0)))
                if not stuck.any():
                    break
                free &= ~stuck
            q = r.clip(r.integrate(q, dx * min(1.0, 0.2 / max(float(np.linalg.norm(dx)), 1e-12)), D))
        r.set(q)
        p, b = r.tool_point(), r.base_qadr
        col = self.coll.check()
        info = {"pos_err_m": float(np.linalg.norm(p[1:] - [0.0, z])),
                "axis_err_deg": float(np.degrees(np.arccos(np.clip(r.axis(r.tool_body, r.approach_local) @ axes[0],
                                                                   -1, 1)))),
                "feet_err_m": float(np.abs(r.data.xpos[r.feet] - self.anchors).max()),
                "behind_m": float(self.coll.world_samples(self.coll.body)[0][:, 0].max() - p[0]),
                "legs_min_z_m": float(self.coll.world_samples(self.coll.legs)[0][:, 2].min()),
                "trunk_height_m": float(q[b + 2]), "pitch_deg": float(np.degrees(2 * np.arctan2(q[b + 5], q[b + 3]))),
                "ahead_m": float(p[0] - q[b]), "collision_free": col["collision_free"], "q": q.tolist()}
        return info["pos_err_m"] < 5e-3 and info["axis_err_deg"] < 3.0 and info["feet_err_m"] < 1e-2 \
            and info["collision_free"] and info["behind_m"] <= -BEHIND_M + 0.01 and info["legs_min_z_m"] >= -0.005, info


def chart(cells: dict, betas, heights, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch, Rectangle

    INK2, GRID, SURF, FILL = "#52514e", "#e4e3df", "#fcfcfb", "#9ec5f4"
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                         "figure.facecolor": SURF, "axes.facecolor": SURF})
    fig, ax = plt.subplots(figsize=(7.5, 5.0), constrained_layout=True)
    dz = heights[1] - heights[0]
    for i, b in enumerate(betas):
        for z in heights:
            ok = cells[f"{b}_{z:.2f}"] is not None
            ax.add_patch(Rectangle((i - 0.48, z - dz / 2 + 0.002), 0.96, dz - 0.004, lw=0 if ok else 0.6,
                                   fc=FILL if ok else SURF, ec=GRID))
    ax.set(xlim=(-0.5, len(betas) - 0.5), ylim=(heights[0] - dz / 2, heights[-1] + dz / 2),
           xlabel="approach pitched down by [deg] (0: level, 90: from above)",
           ylabel="gripper contact point height [m]")
    ax.set_xticks(range(len(betas)), [str(b) for b in betas])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(handles=[Patch(fc=FILL, label="reachable"), Patch(fc=SURF, ec=GRID, label="not found")],
              frameon=False, loc="upper left", bbox_to_anchor=(0, -0.12), ncol=2)
    ax.set_title("Whole-body grasp reach: feet planted, trunk 0.40-0.58 m, no collision, body behind the part",
                 fontsize=9, loc="left")
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--robot", default="b2z1")
    ap.add_argument("--betas", type=float, nargs="+", default=[0, 15, 30, 45, 60, 90])
    ap.add_argument("--heights", type=float, nargs=3, default=[0.15, 0.85, 0.05], help="first, last, step [m]")
    ap.add_argument("--max-pitch-deg", type=float, default=15.0)
    ap.add_argument("--seeds", type=int, default=8, help="the home arm and random arm configurations")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    robot = Robot(args.robot)
    ik = WholeBodyIK(robot)
    rng = np.random.default_rng(0)
    arm = robot.groups["arm"]
    seeds = [ik.home[robot.dof_qadr[arm]]] + [rng.uniform(robot.lower[arm], robot.upper[arm])
                                               for _ in range(args.seeds - 1)]
    a, b, st = args.heights
    heights = np.round(np.arange(a, b + st / 2, st), 3)
    betas = [int(x) if float(x).is_integer() else x for x in args.betas]
    cells = {}
    for beta in betas:
        for z in heights:
            hit = None
            for s in seeds:
                ok, info = ik.solve(float(z), np.radians(beta), s)
                if ok and abs(info["pitch_deg"]) <= args.max_pitch_deg:
                    hit = info
                    break
            cells[f"{beta}_{z:.2f}"] = hit
            print(f"  approach {beta:>4} deg, {z:.2f} m: " + (f"trunk {hit['trunk_height_m']:.2f} m, pitch "
                  f"{hit['pitch_deg']:+.0f} deg, {hit['ahead_m']:.2f} m ahead" if hit else "not found"), flush=True)
    lowest = {str(b): min((float(z) for z in heights if cells[f"{b}_{z:.2f}"]), default=None) for b in betas}
    (out / "grasp_reach.json").write_text(json.dumps({"lowest_m": lowest, "max_pitch_deg": args.max_pitch_deg,
                                                       "cells": cells}, indent=1), encoding="utf-8")
    chart(cells, betas, heights, out / "grasp_reach.png")
    print("lowest reachable height per approach:", lowest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
