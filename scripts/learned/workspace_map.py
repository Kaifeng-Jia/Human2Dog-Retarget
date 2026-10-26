#!/usr/bin/env python
"""Where can the Z1 push? Reachability of contact points around a level, standing B2 (spec learned v0.6 §7.1).

For a grid of points ahead of the base (x forward, z up, y lateral) and two face classes, the position + direction
arm IK (``h2d/learned/reach.py``: contact site on the point, tool axis within 15 deg of the inward normal, no self /
floor collision) from the folded arm plus random starts:

* side face: normal pointing back at the robot (-x), the tool pushes forward;
* top face: normal up (+z), the tool presses down.

The base stands level at ``--root-z`` with the model's standing legs. Used to set the contact-height band of the
candidate selection (``configs/candidate_selection.yaml``). Writes outputs/<run-id>/{summary.json, workspace.png}.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from h2d.common.collision import RobotCollision  # noqa: E402
from h2d.common.robot import B2Z1Robot  # noqa: E402
from h2d.common.runinfo import ProvenanceError, add_run_args, start_run  # noqa: E402
from h2d.common.tables import clean  # noqa: E402
from h2d.learned.reach import ArmIK, shoulder  # noqa: E402
from h2d.paths import load_config  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    add_run_args(ap)
    ap.add_argument("--root-z", type=float, nargs="+", default=[0.5])
    ap.add_argument("--lateral", type=float, nargs="+", default=[0.0, 0.2])
    args = ap.parse_args()
    try:
        prov = start_run(args.run_id, needs=("xmorph",), configs=("b2z1.yaml", "external.yaml", "learned/reach.yaml"),
                         allow_dirty=args.allow_dirty, allow_external_mismatch=args.allow_external_mismatch)
    except ProvenanceError as e:
        print(f"[refused] {e}", file=sys.stderr)
        return 2
    cfg = load_config("learned/reach.yaml")
    out = Path(args.out or f"outputs/{args.run_id}")
    out.mkdir(parents=True, exist_ok=True)
    robot = B2Z1Robot()
    coll = RobotCollision(robot, cfg["penetration_tol_m"])
    xs, zs = np.round(np.arange(0.3, 1.31, 0.1), 2), np.round(np.arange(0.0, 1.31, 0.1), 2)
    faces = {"side": np.array([-1.0, 0, 0]), "top": np.array([0, 0, 1.0])}
    maps = {}
    for rz in args.root_z:
        q = robot.model.qpos0.copy()
        q[2] = rz
        robot.set_qpos(q)
        ik = ArmIK(robot, coll, cfg["pos_tol_m"], cfg["max_angle_deg"], 10, margin_m=cfg["avoid_margin_m"])
        for ly in args.lateral:
            for face, n in faces.items():
                grid = np.zeros((len(zs), len(xs)), bool)
                for i, z in enumerate(zs):
                    for j, x in enumerate(xs):
                        robot.set_qpos(q)
                        grid[i, j] = ik.solve(np.array([x, ly, z]), n, np.zeros(6), use_dir=True, full=False).feasible
                maps[f"root{rz:g}_y{ly:g}_{face}"] = grid
                zr = zs[grid.any(1)]
                print(f"root {rz:g} m, y {ly:g} m, {face}: reachable z {zr.min() if zr.size else '-'}–"
                      f"{zr.max() if zr.size else '-'} m", flush=True)
        robot.set_qpos(q)
        sh = shoulder(robot)
    keys = list(maps)
    fig, ax = plt.subplots(1, len(keys), figsize=(3.2 * len(keys), 4.2), squeeze=False)
    for a, k in zip(ax[0], keys):
        a.imshow(maps[k], origin="lower", cmap="Greens", vmin=0, vmax=1.4, aspect="auto",
                 extent=[xs[0] - 0.05, xs[-1] + 0.05, zs[0] - 0.05, zs[-1] + 0.05])
        a.set_title(k.replace("_", " "), fontsize=9)
        a.set_xlabel("ahead of the base [m]", fontsize=8)
        a.set_ylabel("contact height [m]", fontsize=8)
        a.tick_params(labelsize=7)
    fig.suptitle("Z1 contact points reachable with position + direction IK (green), level B2", fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "workspace.png", dpi=90)
    plt.close(fig)
    summary = {"provenance": prov, "x_m": xs.tolist(), "z_m": zs.tolist(), "shoulder_last_m": sh.tolist(),
               "maps": {k: v.astype(int).tolist() for k, v in maps.items()},
               "reachable_z_range_m": {k: ([float(zs[v.any(1)].min()), float(zs[v.any(1)].max())] if v.any() else None)
                                       for k, v in maps.items()}}
    (out / "summary.json").write_text(json.dumps(clean(summary), indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
