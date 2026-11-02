#!/usr/bin/env python
"""M1 and M1g of the full-optimization line: pass 1 with relation (a) on every input clip, presses and grasps (fullopt
spec v0.2 §3 steps 1-3, §7, §8.1, §8.6, §10).

Per HOI clip (``export_hoi.py``): the task targets from the clip alone (``h2d/fullopt/task.py``), compared with the
learned line's task file of the same segment when it exists (``<learned-root>/<meta task_run>/tasks/<task_id>.npz``);
the relation term; the per-frame SQP (trunk, legs and arm; the soles slide on the floor); the evaluation with the
learned line's definitions. Dev and held-out are reported apart, and the run passes on the dev split only
(configs/fullopt/evaluation.yaml ``pass``): every clip solved; at least ``dev_reached_min`` tasks reached on every
contact frame; the body at most ``body_in_object_max_m`` inside the object and the object under the body on no
frame; no collision (self, or through the floor) on any frame; every sole on the floor and the trunk within its speed
and acceleration limits on every frame; and on every task the targets within ``target_agreement`` of the learned
line's. ``--learned-reach`` (a ``reach_diag.py``
summary) adds the learned line's interaction-mesh numbers next to each task.

A clip whose ``meta.grip`` is ``grasp`` is a grasp task (``h2d/fullopt/grasp.py``): its own checks (spec §8.6), the
same M1 checks on the body, and no comparison with the learned line (which does not grasp). Presses and grasps are
checked apart, dev and held-out apart; the run passes on the dev groups.

Writes outputs/<run-id>/{summary.json, report.md, solutions/<id>.npz, figures/<id>.png}.
"""

from __future__ import annotations

import os

# One BLAS / OpenMP thread, before numpy loads: the per-frame QPs are small, and threads only contend (R027: more
# system than user time). Set here, not inherited, so every run of the script is alike.
THREADS = {k: "1" for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")}
os.environ.update(THREADS)

import argparse  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import traceback  # noqa: E402
from importlib.metadata import PackageNotFoundError, version  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from h2d.common.data.tasks import load_task  # noqa: E402
from h2d.common.runinfo import ProvenanceError, add_run_args, start_run  # noqa: E402
from h2d.common.tables import clean  # noqa: E402
from h2d.fullopt import task as tk  # noqa: E402
from h2d.fullopt.evaluate import evaluate  # noqa: E402
from h2d.fullopt.grasp import Gripper  # noqa: E402
from h2d.fullopt.hoi import HOIClip, leveled, validate  # noqa: E402
from h2d.fullopt.relation import REPRESENTATIONS  # noqa: E402
from h2d.fullopt.robot import Collision, Robot  # noqa: E402
from h2d.fullopt.solver import Solver  # noqa: E402
from h2d.paths import load_config  # noqa: E402

INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
BLUE, ORANGE, GREEN = "#2a78d6", "#eb6834", "#1baf7a"


def solve_clip(c: HOIClip, robot, coll, solver, corr, cfg, ecfg, band, learned_root: Path,
               gripper: Gripper) -> tuple[dict, dict]:
    task, fb0, rt0 = tk.build(c, cfg["task"], band, gripper), coll.fallbacks, coll.retries
    relation = REPRESENTATIONS[cfg["relation"]["kind"]](c, task, robot, corr, cfg["relation"])
    sol = solver.solve(c, task, relation)
    ev, arr = evaluate(c, task, sol["q"], robot, coll, corr, ecfg, gripper)
    m = c.meta
    path = learned_root / str(m.get("task_run", "")) / "tasks" / f"{m.get('task_id', '')}.npz"
    agree = tk.compare(task, load_task(path)) if path.is_file() and task.grip == "press" else None
    row = {"id": m.get("id"), "split": m.get("split", "dev"), "kind": task.grip, "task_id": m.get("task_id"),
           "object": m.get("object"),
           "subject": m.get("subject"), "dataset": m.get("dataset"), "frames": c.n, "mode": task.mode,
           "segment": list(task.segment), "window": list(task.window), "task": task.record, "agreement": agree,
           "span": list(task.span),
           "solver": {"time_s": sol["time_s"], "ms_per_frame": 1e3 * sol["time_s"] / c.n,
                      "iters_mean": float(sol["iters"].mean()), "iters_max": int(sol["iters"].max()),
                      "unconverged_frames": int(np.sum(~sol["converged"])),
                      "unconverged": [int(t) for t in np.flatnonzero(~sol["converged"])],
                      "stops": {k: int(np.sum(sol["stop"] == k)) for k in ("step", "merit", "radius", "cap")},
                      "rejected_steps": int(sol["rejected"].sum()), "radius_final_min": float(sol["radius"].min()),
                      "radius_final_median": float(np.median(sol["radius"])),
                      "qp_failures": int(np.sum(~sol["qp_ok"])), "slack_max": float(np.nanmax(sol["slack_max"])),
                      "distance_retries": coll.retries - rt0, "distance_fallbacks": coll.fallbacks - fb0},
           **ev}
    arrays = {"q": sol["q"], "fps": c.fps, "floor_z": c.floor_z, "gate": task.gate, "target": task.target,
              "tool_x": task.tool_x, "tool_z": task.tool_z, "segment": np.array(task.segment),
              "window": np.array(task.window), "span": np.array(task.span), "relation_targets": relation.targets,
              "iters": sol["iters"], "rejected": sol["rejected"], "converged": sol["converged"], "stop": sol["stop"],
              "radius": sol["radius"], "step": sol["step"], "slack_max": sol["slack_max"], "reached": arr["ok"],
              "err": arr["err"], "angle": arr["ang"], "body_in_object": arr["body_in_object"],
              "object_under_body": arr["object_under_body"]}
    if task.grip == "grasp":
        g = robot.desc["gripper"]
        arrays.update(theta=np.degrees(sol["q"][:, robot.qadr[g["joint"]]] / g["open_sign"]),
                      **{k: arr[k] for k in ("e_a", "e_t", "e_c", "ang_c")})
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
    if "theta" in a:
        ax[2].plot(t, a["theta"] / 5, color=BLUE, lw=1.2, label="gripper opening / 5 [deg]")
    ax[2].plot(t, 100 * a["body_in_object"], color=INK, lw=1.2, label="body in object [cm]")
    ax[2].plot(t, 100 * a["object_under_body"], color=INK2, lw=1.0, ls="--", label="object under body [cm]")
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


def packages() -> dict:
    """Versions of the solver's packages (provenance records numpy, scipy, mujoco)."""
    out = {}
    for name in ("cvxpy", "clarabel", "mujoco", "scipy"):
        try:
            out[name] = version(name)
        except PackageNotFoundError:
            out[name] = None
    return out


def checks_of(rows: list[dict], n_errors: int, crit: dict, split: str = "dev", kind: str = "press") -> dict:
    """The run's checks on one group of clips (a split and a task kind); pass is None where only reported. The body
    checks (body in object, object under the body, feet, trunk) are taken over the clips the reach check does not
    already count as failed (the clips not reached, of the feasible ones for grasps); those clips' values are listed
    under ``not_reached``. Collisions are checked on every clip."""
    dev = split == "dev"
    failed = lambda r: not r["reach"]["reached"] and (kind == "press" or r["reach"]["grasp"]["feasible"])  # noqa: E731
    counted, missed = [r for r in rows if not failed(r)], [r for r in rows if failed(r)]
    worst = lambda f: max((f(r) for r in counted), default=float("nan"))  # noqa: E731
    each = lambda f: {r["id"]: f(r) for r in missed}  # noqa: E731
    body_of = lambda r: r["penetration"]["body_in_object_m"]  # noqa: E731
    under_of = lambda r: r["penetration"]["object_under_body_frames"]  # noqa: E731
    sole_of = lambda r: r["feet"]["sole_height_max_m"]  # noqa: E731
    trunk_of = lambda r: max(r["limits"]["trunk_speed_ratio_max"], r["limits"]["trunk_accel_ratio_max"])  # noqa: E731
    body, sole, trunk = worst(body_of), worst(sole_of), worst(trunk_of)
    under = {r["id"]: under_of(r) for r in counted if under_of(r)}
    hits = {r["id"]: r["penetration"]["collision_frames"] for r in rows if r["penetration"]["collision_frames"]}
    unconverged = {r["id"]: r["solver"]["unconverged_frames"] for r in rows if r["solver"]["unconverged_frames"]}
    out = {"all_clips_solved": {"pass": bool(rows) and not n_errors, "n": len(rows), "n_errors": n_errors,
                                "qp_failures": sum(r["solver"]["qp_failures"] for r in rows)}}
    if kind == "press":
        reached = [r["id"] for r in rows if r["reach"]["reached"]]
        out["reached"] = {"pass": len(reached) >= crit["dev_reached_min"] if dev else None, "reached": len(reached),
                          "of": len(rows), "min": crit["dev_reached_min"] if dev else None,
                          "not_reached": [r["id"] for r in rows if r["id"] not in reached]}
    else:                                       # of the feasible clips; the others are listed with their reasons
        feas = [r for r in rows if r["reach"]["grasp"]["feasible"]]
        reached = [r["id"] for r in feas if r["reach"]["reached"]]
        need = math.ceil(crit["grasp_reached_frac_min"] * len(feas))
        out["reached"] = {"pass": len(reached) >= need if dev else None, "reached": len(reached), "of": len(feas),
                          "min": need if dev else None,
                          "not_reached": {r["id"]: {k: v for k, v in r["reach"]["fail_reasons"].items() if v}
                                          for r in feas if not r["reach"]["reached"]},
                          "infeasible": {r["id"]: r["reach"]["grasp"]["reasons"] for r in rows if r not in feas}}
        bad = {r["id"]: r["reach"]["clear"]["bad_frames"] for r in feas if r["reach"]["clear"]["bad_frames"]}
        out["jaws_clear_of_part"] = {"pass": sum(map(len, bad.values())) <= crit["grasp_clear_frames_max"],
                                     "frames": bad}
    out.update({
        "collision_free_all_frames": {"pass": sum(hits.values()) <= crit["collision_frames_max"], "frames": hits},
        "body_in_object": {"pass": bool(body <= crit["body_in_object_max_m"]), "max_m": body,
                           "not_reached": each(body_of)},
        "object_under_body": {"pass": sum(under.values()) <= crit["object_under_body_frames_max"], "frames": under,
                              "not_reached": each(under_of)},
        "feet_on_floor": {"pass": bool(sole <= crit["sole_height_max_m"]), "sole_height_max_m": sole,
                          "not_reached": each(sole_of)},
        "trunk_within_limits": {"pass": bool(trunk <= crit["trunk_limit_ratio_max"]), "ratio_max": trunk,
                                "not_reached": each(trunk_of)},
        "converged": {"pass": None, "unconverged_frames": unconverged}})
    if kind == "press":
        ag = crit["target_agreement"]

        def agrees(a: dict | None) -> bool:
            return bool(a) and a["target_m"][0] is not None and a["target_m"][0] <= ag["position_m"] \
                and a["tool_x_deg"][0] <= ag["tool_x_deg"]

        bad = [r["id"] for r in rows if not agrees(r["agreement"])]
        out["targets_agree_with_learned"] = {"pass": not bad, "failing_or_missing": bad}
    else:
        fr = {k: [r["id"] for r in rows if r["reach"]["friction"] == k] for k in ("limit", "beyond")}
        out["friction"] = {"pass": None, **fr}
    return out


NOTE = ("Reached: contact point within 1 cm, tool axis within 15° and collision free on every contact frame (the "
        "learned line's definition). Body in object: deepest trunk or leg sample inside the object's hull, all "
        "frames / contact frames. Collision: frames where a self pair, or any geom but the soles through the floor, "
        "penetrates beyond 2 mm (all frames), and the closest self pair / geom to the floor. Under body: frames "
        "where the object's hull overlaps the box under the trunk (thicker than the penetration tolerance) and the "
        "thickest overlap. Feet: the largest horizontal path of a sole (they slide: no gait before M3); every sole "
        "is within 2 mm of the floor. Trunk: largest vertical speed, vertical and horizontal acceleration (limits "
        "0.3 m/s, 3 and 5 m/s²) and tilt (15°). The body checks (body in object, under body, feet, trunk) are taken "
        "over the clips the reach check does not already count as failed; those clips' values are listed apart "
        "(not_reached). Relations: the fixed evaluation network on the contact frames. Unconverged: frames whose "
        "SQP stopped at the iteration cap, or on the trust-region floor with a row violated (reported, not a pass "
        "criterion).")
GRASP_NOTE = ("Grasps (spec §8.6): a contact frame (the closing and the hold) is reached when the point between the "
              "pads is within 5 mm of the target along the closing axis c, 1 cm along the approach a and 2 cm along "
              "the part, both axes within 15°, collision free, the pads at most 5 mm and any other jaw part at most "
              "2 mm (3 mm single-sheet meshes) in the part. Reached counts the feasible clips (a grasp the part's "
              "geometry allows at the contact); the others are listed with the reasons. Clear: frames from fully "
              "open to the closing, and from the release until 5 cm out, whose jaws are in the part. μ: tan(θc/2), "
              "the friction a wedge of the pads needs (limit: 0.25-0.35). Lead: fully open before the contact; "
              "closing: until θc; reopen: θc back to open at the release; release lag: robot minus human, 15 cm out.")


def report(prov, passed, checks, rows, learned, cfg) -> list[str]:
    f = lambda x, nd=1: "–" if x is None or x != x else f"{x:.{nd}f}"  # noqa: E731
    detail = lambda v: ", ".join(f"{a}: {b}" for a, b in v.items() if a != "pass")  # noqa: E731
    git = prov["git"]
    L = ["# M1, M1g: full optimization, pass 1, relation (a) (fullopt spec v0.2 §7, §8.1, §8.6)", "",
         f"Run `{prov['run_id']}` · code `{git['describe']}` (dirty={git['dirty']}) · {len(rows)} clips · relation "
         f"({cfg['relation']['kind']}) · **{'PASS' if passed else 'FAIL'}** (dev only; held-out reported apart)", "",
         "| split | check | pass | detail |", "|---|---|---|---|",
         *[f"| {s} | {k} | {'–' if v['pass'] is None else v['pass']} | {detail(v)} |" for s, cs in checks.items()
           for k, v in cs.items()], "",
         NOTE, "", *([GRASP_NOTE, ""] if any(r["kind"] == "grasp" for r in rows) else [])]
    presses, grasps = [r for r in rows if r["kind"] == "press"], [r for r in rows if r["kind"] == "grasp"]
    cols = ["split", "task", "object", "hand", "reached (frames)", "err max [cm]", "angle med / max [°]",
            "body in object all / contact [cm]", "under body: frames, [cm]", "collision: frames, self / floor min [mm]",
            "foot slide [m]",
            "trunk vz [m/s], az / a [m/s²], tilt [°]", "edge / heading [°], same side",
            "targets vs learned: pos med [cm], tool x [°]", "unconverged / rejected", "ms / frame"]
    cols += ["learned mesh: reached, edge / heading [°], body [cm]"] if learned else []
    L += ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] if presses else []
    for r in sorted(presses, key=lambda r: (r["split"], r["id"])):
        rc, pe, rl, ag, lm_ = r["reach"], r["penetration"], r["relations"]["contact"], r["agreement"], r["limits"]
        cells = [r["split"], r["id"], r["object"], r["mode"], f"{rc['reached']} ({100 * rc['reached_frac']:.0f} %)",
                 f(100 * rc["err_m"]["max"]), f"{f(rc['angle_deg']['median'], 0)} / {f(rc['angle_deg']['max'], 0)}",
                 f"{f(100 * pe['body_in_object_m'])} / {f(100 * r['body_in_object_contact_m'])}",
                 f"{pe['object_under_body_frames']}, {f(100 * pe['object_under_body_m'])}",
                 f"{pe['collision_frames']}, {f(1000 * pe['self_worst']['dist_m'])} / "
                 f"{f(1000 * pe['floor_worst']['dist_m'])}", f(r["feet"]["slide_path_max_m"], 2),
                 f"{f(lm_['trunk_vertical_speed_max_mps'], 2)}, {f(lm_['trunk_vertical_accel_max_mps2'])} / "
                 f"{f(lm_['trunk_accel_max_mps2'])}, {f(lm_['trunk_tilt_max_deg'])}",
                 f"{f(rl['edge_dir_err_deg'])} / {f(rl['heading_err_deg'])}, {f(rl['same_side_frac'], 2)}",
                 f"{f(100 * ag['target_m'][0])}, {f(ag['tool_x_deg'][0])}" if ag else "–",
                 f"{r['solver']['unconverged_frames']} / {r['solver']['rejected_steps']}",
                 f(r["solver"]["ms_per_frame"], 0)]
        if learned:
            lm = (learned.get(r.get("task_id")) or {}).get("mesh")
            cells.append(f"{lm['pos_dir']['label'] == 'feasible'}, {f(lm['relations']['edge_dir_err_deg'])} / "
                         f"{f(lm['relations']['heading_err_deg'])}, {f(100 * lm['scene_body_depth_max_m'])}"
                         if lm else "–")
        L.append("| " + " | ".join(str(x) for x in cells) + " |")
    if grasps:
        L += ["", *grasp_table(grasps, f)]
    L += ["", *[f"![{r['id']}](figures/{r['id']}.png)" for r in sorted(rows, key=lambda r: (r["split"], r["id"]))]]
    return L


def grasp_table(rows: list[dict], f) -> list[str]:
    cols = ["split", "task", "object", "grasp", "reached (frames)", "e_c / e_a / e_t max [mm]",
            "approach / closing axis max [°]", "pads / jaws in part max [mm]", "clear: bad frames, max [mm]",
            "θc (gap table) / open [°], μ", "lead / closing / reopen [s]", "moved closing [cm]", "release lag [s]",
            "body in object [cm]", "collision frames", "foot slide [m]", "trunk ratio", "unconverged", "ms / frame"]
    L = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in sorted(rows, key=lambda r: (r["split"], r["object"], r["id"])):
        rc, g, tm, lm = r["reach"], r["reach"]["grasp"], r["reach"]["timing"], r["limits"]
        kind = f"{g['kind']} {g['beta_deg']:.0f}°, w {f(100 * g['w_m'])} cm" + (
            f", slid {f(100 * g['slide_m'])} cm" if g["slide_m"] else "") + (
            "" if g["feasible"] else f", **infeasible**: {'; '.join(g['reasons'])}")
        cells = [r["split"], r["id"], r["object"], kind, f"{rc['reached']} ({100 * rc['reached_frac']:.0f} %)",
                 " / ".join(f(1000 * rc[k]["max"]) for k in ("e_c_m", "e_a_m", "e_t_m")),
                 f"{f(rc['angle_deg']['max'], 0)} / {f(rc['closing_angle_deg']['max'], 0)}",
                 f"{f(1000 * rc['pad_in_part_m']['max'])} / {f(1000 * rc['jaw_in_part_m']['max'])}",
                 f"{len(rc['clear']['bad_frames'])}, {f(1000 * rc['clear']['jaw_in_part_max_m'])}",
                 f"{f(g['theta_c_deg'])} ({f(g['theta_c_gap_deg'])}) / {f(g['theta_open_deg'])}, "
                 f"{f(g['mu_need'], 2)} {rc['friction']}",
                 f"{f(tm['open_lead_s'], 2)}{'*' if tm['late_start'] else ''} / {f(tm['closing_s'], 2)} / "
                 f"{f(tm['reopen_s'], 2)}", f(100 * tm["moved_while_closing_m"]), f(tm["release_lag_s"], 2),
                 f(100 * r["penetration"]["body_in_object_m"]), r["penetration"]["collision_frames"],
                 f(r["feet"]["slide_path_max_m"], 2),
                 f(max(lm["trunk_speed_ratio_max"], lm["trunk_accel_ratio_max"]), 3),
                 r["solver"]["unconverged_frames"], f(r["solver"]["ms_per_frame"], 0)]
        L.append("| " + " | ".join(str(x) for x in cells) + " |")
    return L + ["", "\\* the clip starts too late to open before the contact: open from its first frame."]


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
                   "fullopt/correspondence.yaml", "fullopt/solver.yaml", "fullopt/evaluation.yaml",
                   "fullopt/grasp.yaml")
        prov = start_run(args.run_id, needs=("xmorph",), configs=configs, allow_dirty=args.allow_dirty,
                         allow_external_mismatch=args.allow_external_mismatch)
    except ProvenanceError as e:
        print(f"[refused] {e}", file=sys.stderr)
        return 2
    prov["packages"].update(packages())
    prov["threads"] = {k: os.environ.get(k) for k in THREADS}
    cfg, ecfg = load_config("fullopt/solver.yaml"), load_config("fullopt/evaluation.yaml")
    band = load_config("candidate_selection.yaml")["reach_band"]
    out = Path(args.out or f"outputs/{args.run_id}")
    for sub in ("solutions", "figures"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    robot = Robot(args.robot)
    coll = Collision(robot, ecfg["penetration_tol_m"])
    corr = load_config("fullopt/correspondence.yaml")[robot.name]
    solver = Solver(robot, cfg, coll=coll)
    gripper = None                                            # built at the first grasp clip
    learned = json.loads(Path(args.learned_reach).read_text())["tasks"] if args.learned_reach else None
    files = [p for p in sorted(Path(args.clips).glob("*.npz")) if args.ids is None or p.stem in args.ids]
    rows, errors, t0 = [], [], time.time()
    for p in files:
        split, kind = "?", "?"
        try:
            c = HOIClip.load(p)
            split, kind = c.meta.get("split", "dev"), "grasp" if c.meta.get("grip") == "grasp" else "press"
            problems = validate(c)
            if problems:
                raise ValueError("; ".join(problems))
            if kind == "grasp" and gripper is None:
                gripper = Gripper(robot, load_config("fullopt/grasp.yaml"))
            row, arrays = solve_clip(leveled(c), robot, coll, solver, corr, cfg, ecfg, band, Path(args.learned_root),
                                     gripper)
            np.savez_compressed(out / "solutions" / f"{p.stem}.npz", **arrays)
            figure(leveled(c), row, arrays, out / "figures" / f"{p.stem}.png")
            rows.append(row)
            rc, depth = row["reach"], 100 * row["penetration"]["body_in_object_m"]
            extra = "" if kind == "press" else f", {rc['grasp']['kind']} {rc['grasp']['beta_deg']:.0f}°" + (
                "" if rc["grasp"]["feasible"] else " (infeasible)")
            print(f"  {split} {p.stem}: reached {rc['reached']} ({100 * rc['reached_frac']:.0f} %), body in object "
                  f"{depth:.1f} cm, {row['solver']['time_s']:.0f} s{extra}", flush=True)
        except Exception as e:  # noqa: BLE001 - report and continue
            errors.append({"id": p.stem, "split": split, "kind": kind, "error": traceback.format_exc()[-1500:]})
            print(f"  {p.stem}: error {type(e).__name__}: {e}", flush=True)
    kinds = sorted({r["kind"] for r in rows} | {e["kind"] for e in errors if e["kind"] != "?"}) or ["press"]
    groups = sorted({(r["split"], r["kind"]) for r in rows} | {("dev", k) for k in kinds})
    name = lambda s, k: s if k == "press" else f"{s} {k}"  # noqa: E731
    n_err = {(s, k): sum(e["split"] in (s, "?") and e["kind"] in (k, "?") for e in errors) for s, k in groups}
    checks = {name(s, k): checks_of([r for r in rows if r["split"] == s and r["kind"] == k], n_err[s, k],
                                    ecfg["pass"], s, k) for s, k in groups}  # (a clip that did not load counts)
    passed = all(v["pass"] for s, k in groups if s == "dev" for v in checks[name(s, k)].values()
                 if v["pass"] is not None)
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
