#!/usr/bin/env python
"""M1 of the full-optimization line: pass 1 with relation (a) on every input clip (fullopt spec v0.2 §3 steps 1-3,
§7, §8.1, §10).

Per HOI clip (``export_hoi.py``): the task targets from the clip alone (``h2d/fullopt/task.py``), compared with the
learned line's task file of the same segment when it exists (``<learned-root>/<meta task_run>/tasks/<task_id>.npz``);
the relation term; the per-frame SQP (trunk and arm, legs at home); the evaluation with the learned line's
definitions. Dev and held-out are reported apart, and the run passes on the dev split only
(configs/fullopt/evaluation.yaml ``pass``): every clip solved, at least ``dev_reached_min`` tasks reached on every
contact frame, the body at most ``body_in_object_max_m`` inside the object on any frame, and on every task the
targets within ``target_agreement`` of the learned line's. ``--learned-reach`` (a ``reach_diag.py`` summary) adds
the learned line's interaction-mesh numbers next to each task.

Writes outputs/<run-id>/{summary.json, report.md, solutions/<id>.npz, figures/<id>.png}.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from h2d.common.data.tasks import load_task  # noqa: E402
from h2d.common.runinfo import ProvenanceError, add_run_args, start_run  # noqa: E402
from h2d.common.tables import clean  # noqa: E402
from h2d.fullopt import task as tk  # noqa: E402
from h2d.fullopt.evaluate import evaluate  # noqa: E402
from h2d.fullopt.hoi import HOIClip, leveled, validate  # noqa: E402
from h2d.fullopt.relation import REPRESENTATIONS  # noqa: E402
from h2d.fullopt.robot import Collision, Robot  # noqa: E402
from h2d.fullopt.solver import Solver  # noqa: E402
from h2d.paths import load_config  # noqa: E402

INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
BLUE, ORANGE, GREEN = "#2a78d6", "#eb6834", "#1baf7a"


def solve_clip(c: HOIClip, robot, coll, solver, corr, cfg, ecfg, band, learned_root: Path) -> tuple[dict, dict]:
    task = tk.build(c, cfg["task"], band)
    relation = REPRESENTATIONS[cfg["relation"]["kind"]](c, task, robot, corr, cfg["relation"])
    sol = solver.solve(c, task, relation)
    ev, arr = evaluate(c, task, sol["q"], robot, coll, corr, ecfg)
    m = c.meta
    path = learned_root / str(m.get("task_run", "")) / "tasks" / f"{m.get('task_id', '')}.npz"
    agree = tk.compare(task, load_task(path)) if path.is_file() else None
    row = {"id": m.get("id"), "split": m.get("split", "dev"), "task_id": m.get("task_id"), "object": m.get("object"),
           "subject": m.get("subject"), "dataset": m.get("dataset"), "frames": c.n, "mode": task.mode,
           "segment": list(task.segment), "window": list(task.window), "task": task.record, "agreement": agree,
           "solver": {"time_s": sol["time_s"], "ms_per_frame": 1e3 * sol["time_s"] / c.n,
                      "iters_mean": float(sol["iters"].mean()), "iters_max": int(sol["iters"].max()),
                      "unconverged_frames": int(np.sum(sol["step"] >= cfg["sqp"]["tol"])),
                      "qp_failures": int(np.sum(~sol["qp_ok"])), "slack_max": float(np.nanmax(sol["slack_max"]))},
           **ev}
    arrays = {"q": sol["q"], "fps": c.fps, "floor_z": c.floor_z, "gate": task.gate, "target": task.target,
              "tool_x": task.tool_x, "tool_z": task.tool_z, "segment": np.array(task.segment),
              "window": np.array(task.window), "relation_targets": relation.targets, "iters": sol["iters"],
              "step": sol["step"], "slack_max": sol["slack_max"], "reached": arr["ok"], "err": arr["err"],
              "angle": arr["ang"], "body_in_object": arr["body_in_object"]}
    return row, arrays


def figure(c: HOIClip, row: dict, a: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy.spatial.transform import Rotation as R

    plt.rcParams.update({"font.size": 8, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                         "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": SURF, "axes.facecolor": SURF})
    fps, (s, e) = float(a["fps"]), a["segment"]
    t, tc = np.arange(c.n) / fps, np.arange(s, e) / fps
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.4), constrained_layout=True)
    ax[0].plot(tc, 100 * a["err"], color=BLUE, lw=1.4, label="contact point error [cm]")
    ax[0].plot(tc, a["angle"], color=ORANGE, lw=1.4, label="tool axis vs approach target [deg]")
    ax[0].axhline(1.0, color=BLUE, ls=":", lw=0.8)
    ax[0].axhline(15.0, color=ORANGE, ls=":", lw=0.8)
    bad = ~a["reached"].astype(bool)
    ax[0].scatter(tc[bad], 100 * a["err"][bad], color=INK, s=8, marker="x", zorder=3, label="not reached")
    ax[0].set(xlabel="time [s]", title="Reach on the contact frames")
    q = a["q"]
    verts = R.from_quat(c.obj_quat[s]).apply(c.obj_verts)[:, :2] + c.obj_pos[s, :2]
    ax[1].scatter(verts[:, 0], verts[:, 1], s=1, color=INK2, alpha=0.15, lw=0)
    ax[1].plot(*c.joint("pelvis")[:, :2].T, color=BLUE, lw=1.4, label="human pelvis")
    ax[1].plot(*q[:, :2].T, color=ORANGE, lw=1.4, label="robot trunk")
    ax[1].plot(*a["target"][s:e, :2].T, color=GREEN, lw=2.0, label="contact target")
    ax[1].plot(*c.obj_pos[:, :2].T, color=INK2, lw=0.8, ls="--", label="object")
    ax[1].set_aspect("equal", adjustable="datalim")
    ax[1].set(xlabel="x [m]", ylabel="y [m]", title="Top view (object at first contact)")
    ax[2].plot(t, 100 * (q[:, 2] - q[0, 2]), color=ORANGE, lw=1.4, label="trunk height change [cm]")
    ax[2].plot(t, 10 * a["gate"], color=GREEN, lw=1.2, label="task gate x 10")
    ax[2].plot(t, 100 * a["body_in_object"], color=INK, lw=1.2, label="body in object [cm]")
    ax[2].axvspan(s / fps, e / fps, color=GRID, lw=0)
    ax[2].set(xlabel="time [s]", title="Trunk, gate, penetration (contact shaded)")
    for x in ax:
        x.grid(color=GRID, lw=0.6)
        x.legend(frameon=False, fontsize=7)
    fig.suptitle(f"{row['id']} · {row['split']} · {row['object']} · hand {row['mode']} · "
                 f"{'reached' if row['reach']['reached'] else 'NOT reached'} "
                 f"({100 * row['reach']['reached_frac']:.0f} % of contact frames)", fontsize=9, color=INK)
    fig.savefig(path, dpi=80)
    plt.close(fig)


def checks_of(rows: list[dict], n_errors: int, crit: dict) -> dict:
    ag = crit["target_agreement"]
    reached = [r["id"] for r in rows if r["reach"]["reached"]]
    body = max((r["penetration"]["body_in_object_m"] for r in rows), default=float("nan"))

    def agrees(a: dict | None) -> bool:
        return bool(a) and a["target_m"][0] is not None and a["target_m"][0] <= ag["position_m"] \
            and a["tool_x_deg"][0] <= ag["tool_x_deg"]

    return {"all_clips_solved": {"pass": bool(rows) and not n_errors, "n": len(rows), "n_errors": n_errors,
                                 "qp_failures": sum(r["solver"]["qp_failures"] for r in rows)},
            "reached": {"pass": len(reached) >= crit["dev_reached_min"], "reached": len(reached), "of": len(rows),
                        "min": crit["dev_reached_min"],
                        "not_reached": [r["id"] for r in rows if r["id"] not in reached]},
            "body_in_object": {"pass": bool(body <= crit["body_in_object_max_m"]), "max_m": body},
            "targets_agree_with_learned": {"pass": all(agrees(r["agreement"]) for r in rows),
                                           "failing_or_missing": [r["id"] for r in rows if not agrees(r["agreement"])]}}


NOTE = ("Reached: contact point within 1 cm, tool axis within 15° and collision free on every contact frame (the "
        "learned line's definition). Body in object: deepest trunk or leg sample inside the object's hull, all "
        "frames / contact frames. Relations: the fixed evaluation network on the contact frames. Feet below the "
        "floor: pass 1 holds the legs at home, so a lowered or pitched trunk puts the feet there (the gait pass "
        "bends the legs).")


def report(prov, passed, checks, rows, learned, cfg) -> list[str]:
    f = lambda x, nd=1: "–" if x is None or x != x else f"{x:.{nd}f}"  # noqa: E731
    detail = lambda v: ", ".join(f"{a}: {b}" for a, b in v.items() if a != "pass")  # noqa: E731
    git = prov["git"]
    L = ["# M1: full optimization, pass 1, relation (a) (fullopt spec v0.2 §7, §8.1)", "",
         f"Run `{prov['run_id']}` · code `{git['describe']}` (dirty={git['dirty']}) · {len(rows)} clips · relation "
         f"({cfg['relation']['kind']}) · **{'PASS' if passed else 'FAIL'}** (dev only; held-out reported apart)", "",
         "| split | check | pass | detail |", "|---|---|---|---|",
         *[f"| {s} | {k} | {v['pass']} | {detail(v)} |" for s, cs in checks.items() for k, v in cs.items()], "",
         NOTE, ""]
    cols = ["split", "task", "object", "hand", "reached (frames)", "err max [cm]", "angle med / max [°]",
            "body in object all / contact [cm]", "self min [mm]", "feet below floor [cm]",
            "edge / heading [°], same side", "targets vs learned: pos med [cm], tool x [°]", "ms / frame"]
    cols += ["learned mesh: reached, edge / heading [°], body [cm]"] if learned else []
    L += ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in sorted(rows, key=lambda r: (r["split"], r["id"])):
        rc, pe, rl, ag = r["reach"], r["penetration"], r["relations"]["contact"], r["agreement"]
        cells = [r["split"], r["id"], r["object"], r["mode"], f"{rc['reached']} ({100 * rc['reached_frac']:.0f} %)",
                 f(100 * rc["err_m"]["max"]), f"{f(rc['angle_deg']['median'], 0)} / {f(rc['angle_deg']['max'], 0)}",
                 f"{f(100 * pe['body_in_object_m'])} / {f(100 * r['body_in_object_contact_m'])}",
                 f(1000 * pe["self_min_dist_m"]), f(100 * pe["feet_below_floor_m"]),
                 f"{f(rl['edge_dir_err_deg'])} / {f(rl['heading_err_deg'])}, {f(rl['same_side_frac'], 2)}",
                 f"{f(100 * ag['target_m'][0])}, {f(ag['tool_x_deg'][0])}" if ag else "–",
                 f(r["solver"]["ms_per_frame"], 0)]
        if learned:
            lm = (learned.get(r.get("task_id")) or {}).get("mesh")
            cells.append(f"{lm['pos_dir']['label'] == 'feasible'}, {f(lm['relations']['edge_dir_err_deg'])} / "
                         f"{f(lm['relations']['heading_err_deg'])}, {f(100 * lm['scene_body_depth_max_m'])}"
                         if lm else "–")
        L.append("| " + " | ".join(str(x) for x in cells) + " |")
    L += ["", *[f"![{r['id']}](figures/{r['id']}.png)" for r in sorted(rows, key=lambda r: (r["split"], r["id"]))]]
    return L


def main() -> int:
    ap = argparse.ArgumentParser()
    add_run_args(ap)
    ap.add_argument("--clips", required=True, help="folder of HOIClip .npz files (export_hoi.py)")
    ap.add_argument("--ids", nargs="*", default=None, help="clip ids (default: all)")
    ap.add_argument("--robot", default="b2z1", help="configs/fullopt/robots/<robot>.yaml")
    ap.add_argument("--learned-root", default="outputs", help="where the learned line's task runs are (meta task_run)")
    ap.add_argument("--learned-reach", default=None, help="summary.json of a reach_diag.py run, for the comparison")
    args = ap.parse_args()
    try:
        configs = ("b2z1.yaml", "external.yaml", "candidate_selection.yaml", f"fullopt/robots/{args.robot}.yaml",
                   "fullopt/correspondence.yaml", "fullopt/solver.yaml", "fullopt/evaluation.yaml")
        prov = start_run(args.run_id, needs=("xmorph",), configs=configs, allow_dirty=args.allow_dirty,
                         allow_external_mismatch=args.allow_external_mismatch)
    except ProvenanceError as e:
        print(f"[refused] {e}", file=sys.stderr)
        return 2
    cfg, ecfg = load_config("fullopt/solver.yaml"), load_config("fullopt/evaluation.yaml")
    band = load_config("candidate_selection.yaml")["reach_band"]
    out = Path(args.out or f"outputs/{args.run_id}")
    for sub in ("solutions", "figures"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    robot = Robot(args.robot)
    coll = Collision(robot, ecfg["penetration_tol_m"])
    corr = load_config("fullopt/correspondence.yaml")[robot.name]
    solver = Solver(robot, cfg, coll=coll)
    learned = json.loads(Path(args.learned_reach).read_text())["tasks"] if args.learned_reach else None
    files = [p for p in sorted(Path(args.clips).glob("*.npz")) if args.ids is None or p.stem in args.ids]
    rows, errors, t0 = [], [], time.time()
    for p in files:
        split = "?"
        try:
            c = HOIClip.load(p)
            split = c.meta.get("split", "dev")
            problems = validate(c)
            if problems:
                raise ValueError("; ".join(problems))
            row, arrays = solve_clip(leveled(c), robot, coll, solver, corr, cfg, ecfg, band, Path(args.learned_root))
            np.savez_compressed(out / "solutions" / f"{p.stem}.npz", **arrays)
            figure(leveled(c), row, arrays, out / "figures" / f"{p.stem}.png")
            rows.append(row)
            rc, depth = row["reach"], 100 * row["penetration"]["body_in_object_m"]
            print(f"  {split} {p.stem}: reached {rc['reached']} ({100 * rc['reached_frac']:.0f} %), body in object "
                  f"{depth:.1f} cm, {row['solver']['time_s']:.0f} s", flush=True)
        except Exception as e:  # noqa: BLE001 - report and continue
            errors.append({"id": p.stem, "split": split, "error": traceback.format_exc()[-1500:]})
            print(f"  {p.stem}: error {type(e).__name__}: {e}", flush=True)
    splits = sorted({r["split"] for r in rows} | {"dev"})
    n_err = {s: sum(e["split"] in (s, "?") for e in errors) for s in splits}     # a clip that did not load counts
    checks = {s: checks_of([r for r in rows if r["split"] == s], n_err[s], ecfg["pass"]) for s in splits}
    passed = all(v["pass"] for v in checks["dev"].values())
    summary = {"provenance": prov, "robot": robot.name, "config": cfg, "evaluation": ecfg, "checks": checks,
               "pass": passed, "clips": rows, "errors": errors, "elapsed_s": time.time() - t0}
    (out / "summary.json").write_text(json.dumps(clean(summary), indent=2, default=str), encoding="utf-8")
    L = report(prov, passed, checks, rows, learned, cfg)
    if errors:
        L += ["", "## Errors", "", *[f"- {e['id']}: {e['error'].splitlines()[-1]}" for e in errors]]
    (out / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"pass={passed}  clips={len(rows)}  errors={len(errors)}  -> {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
