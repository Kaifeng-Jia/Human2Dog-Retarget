#!/usr/bin/env python
"""Frozen-body reachability diagnostic (spec learned v0.6 §7.1, go / no-go): can the Z1 arm alone reach the human
contact targets while the base and legs follow the X-Morph prior?

Inputs: task files from ``scripts/common/prepare_tasks.py`` and the prior from ``scripts/learned/d0_chain.py``
(``<clip>_b2z1.pkl`` + sidecar). Per task (default: the confirmed ids in ``configs/push_candidates.yaml``):

1. registration (``h2d/common/registration.py``): start-anchored and contact-fitted SE(2) of the robot root
   trajectory, object trajectory fixed;
2. for each layout and each contact frame, three problems with the multi-start, collision-aware arm IK
   (``h2d/learned/reach.py``): position (joint limits only), position + direction (joint limits only),
   position + direction within +-budget around the prior;
3. per problem: frames feasible (error <= pos_tol, angle <= max_angle, no self / floor / arm-object
   collision), failure labels, joint speed over consecutive feasible frames against the Z1 limit, arm change
   (per-joint max and RMS, deg), jump to the prior at the segment ends; the frozen body's penetration of the
   object (scene infeasible).

Failure labels (spec §7.1 step 5): "proven_unreachable" (target farther from the joint1 anchor than the sum of
the arm's segment lengths), "no_feasible_solution_within_budget" (all other failures of the local search),
"coordinate_or_tool_offset_error" (frame mismatch, target below the floor, registration residual above the
suspect level). "Task not expressible" comes only from the task definition and is not produced here.

Writes outputs/<run-id>/{summary.json, report.md, tasks/<id>.png, solutions/<id>.npz}.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402
from scipy.spatial.transform import Rotation as R  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from h2d.common.collision import ObjectHull, RobotCollision  # noqa: E402
from h2d.common.data.omomo_objects import load_object  # noqa: E402
from h2d.common.data.tasks import load_task  # noqa: E402
from h2d.common.registration import contact_fit, start_anchored  # noqa: E402
from h2d.common.robot import B2Z1Robot  # noqa: E402
from h2d.common.runinfo import ProvenanceError, add_run_args, start_run  # noqa: E402
from h2d.common.tables import clean  # noqa: E402
from h2d.learned.prior import Motion, load_motion  # noqa: E402
from h2d.learned.reach import ArmIK, ObjectPose, reach_bound, shoulder  # noqa: E402
from h2d.paths import REPO_ROOT, load_config  # noqa: E402

PROBLEMS = (("pos", False, False), ("pos_dir", True, False), ("pos_dir_budget", True, True))
LAYOUTS = ("contact_fit", "start_anchored")


def solve_task(task: dict, motion: Motion, sidecar: dict, robot: B2Z1Robot, coll: RobotCollision, cfg: dict,
               reg_cfg: dict, bound: float) -> dict:
    fr, c = task["frames"], task["in_contact"].astype(bool)
    cf = fr[c]
    out = {"labels": {}, "flags": []}
    if motion.n < fr[-1] + 1:
        out["flags"].append(f"prior has {motion.n} frames, task needs {fr[-1] + 1}")
        out["labels"] = {f"{lay}/{p}": "coordinate_or_tool_offset_error" for lay in LAYOUTS for p, *_ in PROBLEMS}
        return out
    y_all = task["target_world"][c]
    if y_all[:, 2].min() < -0.02:
        out["flags"].append(f"target below the floor ({y_all[:, 2].min():.3f} m)")
    obj = load_object(task["object"])
    hull = ObjectHull.from_vertices(obj.hull_verts)
    arm_idx = slice(12, 18)

    def set_frame(t, T):
        rp, rq = T.apply_root(motion.root_pos[t][None], motion.root_rot_xyzw[t][None])
        robot.set_qpos(robot.qpos_from_xmorph(rp[0], rq[0], motion.dof_pos[t]))

    # ---- registration
    raw = type("Id", (), {"apply_root": staticmethod(lambda p, q: (p, q))})()
    p_raw = []
    for t in cf:
        set_frame(t, raw)
        p_raw.append(robot.contact_site())
    p_raw = np.array(p_raw)
    anchor = start_anchored(sidecar["src_root_pos0"], sidecar["src_yaw0"], sidecar["out_root_pos0"], sidecar["out_yaw0"])
    fit = contact_fit(p_raw, y_all, None, anchor.psi, reg_cfg["lambda_psi"], reg_cfg["min_target_spread_m"],
                      reg_cfg["psi_grid_deg"])
    anchor_res = np.linalg.norm(anchor.apply_points(p_raw)[:, :2] - y_all[:, :2], axis=1)
    anchor.info = {"residual_xy_rms_m": float(np.sqrt(np.mean(anchor_res ** 2))), "residual_xy_max_m": float(anchor_res.max())}
    out["registration"] = {"contact_fit": fit.to_dict(), "start_anchored": anchor.to_dict()}
    if fit.info["residual_xy_rms_m"] > cfg["registration_residual_suspect_m"]:
        out["flags"].append(f"contact-fit residual {fit.info['residual_xy_rms_m']:.2f} m")

    ik = ArmIK(robot, coll, cfg["pos_tol_m"], cfg["max_angle_deg"], cfg["n_random_starts"],
               margin_m=cfg["avoid_margin_m"])
    vmax = np.asarray(cfg["joint_speed_limit_rad_s"])
    budget = np.radians(cfg["budget_deg"])
    fps = float(task["fps"])
    sol = {}
    for lay, T in (("contact_fit", fit), ("start_anchored", anchor)):
        n_c = len(cf)
        prior_q = np.array([motion.dof_pos[t][arm_idx] for t in cf])
        scene, prior_site, dist_sh = np.zeros(n_c), np.zeros((n_c, 3)), np.zeros(n_c)
        res = {p: {"q": np.zeros((n_c, 6)), "err": np.zeros(n_c), "ang": np.zeros(n_c), "ok": np.zeros(n_c, bool),
                   "self": np.zeros(n_c), "floor": np.zeros(n_c), "armobj": np.zeros(n_c), "toolobj": np.zeros(n_c),
                   "start": []} for p, *_ in PROBLEMS}
        prev = {p: None for p, *_ in PROBLEMS}
        for i, t in enumerate(cf):
            set_frame(t, T)
            base_q = robot.data.qpos.copy()
            k = int(np.flatnonzero(fr == t)[0])
            op = ObjectPose(hull, task["obj_pos"][k], R.from_quat(task["obj_rot_xyzw"][k]).as_matrix())
            n_w = op.rot @ task["n_bar_local"]
            y = task["target_world"][k]
            prior_site[i] = robot.contact_site()
            dist_sh[i] = float(np.linalg.norm(y - shoulder(robot)))
            scene[i] = coll.check(hull, op.to_local)["body_obj_depth_m"]
            for p, use_dir, use_budget in PROBLEMS:
                robot.set_qpos(base_q)
                full = i % cfg["full_search_every"] == 0 or prev[p] is not None
                r = ik.solve(y, n_w, prior_q[i], prev[p], use_dir, budget if use_budget else None, op, full)
                d = res[p]
                d["q"][i], d["err"][i], d["ang"][i], d["ok"][i] = r.q, r.pos_err_m, r.angle_deg, r.feasible
                d["self"][i], d["floor"][i] = r.collision["self_min_dist_m"], r.collision["floor_min_dist_m"]
                d["armobj"][i], d["toolobj"][i] = r.collision["arm_obj_depth_m"], r.collision["tool_obj_depth_m"]
                d["start"].append(r.start)
                prev[p] = r.q if r.feasible else None
        lay_out = {"scene_body_depth_max_m": float(scene.max()),
                   "scene_infeasible": bool(scene.max() > cfg["scene_body_depth_m"]),
                   "target_to_shoulder_m": [float(dist_sh.min()), float(dist_sh.max())], "reach_bound_m": bound,
                   "prior_site_error_m": [float(np.linalg.norm(prior_site - y_all, axis=1).min()),
                                          float(np.linalg.norm(prior_site - y_all, axis=1).max())]}
        for p, *_ in PROBLEMS:
            d = res[p]
            ok = d["ok"]
            dq = np.degrees(np.abs(d["q"] - prior_q))
            both = ok[1:] & ok[:-1]
            speed = np.abs(np.diff(d["q"], axis=0)) * fps
            ratio = (speed / vmax).max(1)[both] if both.any() else np.zeros(0)
            unreachable = (~ok) & (dist_sh > bound)
            if ok.all():
                label = "feasible"
            elif out["flags"]:
                label = "coordinate_or_tool_offset_error"
            elif unreachable.any() and unreachable.sum() == (~ok).sum():
                label = "proven_unreachable"
            else:
                label = "no_feasible_solution_within_budget"
            fail = ~ok
            why = {"pos_error": int(np.sum(fail & (d["err"] > cfg["pos_tol_m"]))),
                   "angle": int(np.sum(fail & (d["ang"] > cfg["max_angle_deg"]))) if p != "pos" else 0,
                   "self_collision": int(np.sum(fail & (d["self"] <= -cfg["penetration_tol_m"]))),
                   "floor": int(np.sum(fail & (d["floor"] <= -cfg["penetration_tol_m"]))),
                   "arm_object": int(np.sum(fail & (d["armobj"] > cfg["penetration_tol_m"])))}
            lay_out[p] = {
                "label": label, "feasible_frac": float(ok.mean()), "n_frames": int(len(ok)),
                "n_proven_unreachable": int(unreachable.sum()), "fail_reasons": why,
                "pos_err_max_m": float(d["err"].max()), "pos_err_median_m": float(np.median(d["err"])),
                "angle_max_deg": float(d["ang"].max()), "angle_median_deg": float(np.median(d["ang"])),
                "arm_change_max_deg": dq[ok].max(0).tolist() if ok.any() else None,
                "arm_change_rms_deg": float(np.sqrt(np.mean(dq[ok] ** 2))) if ok.any() else None,
                "speed_ratio_max": float(ratio.max()) if ratio.size else None,
                "speed_violations": int(np.sum(ratio > 1.0)),
                "jump_to_prior_at_ends_deg": [float(dq[0].max()), float(dq[-1].max())],
                "tool_obj_depth_max_m": float(d["toolobj"].max()),
                "starts": {s: d["start"].count(s) for s in set(d["start"])},
            }
            out["labels"][f"{lay}/{p}"] = label
        out[lay] = lay_out
        sol[lay] = res | {"prior_q": prior_q, "prior_site": prior_site, "dist_shoulder": dist_sh, "scene": scene}
    out["_sol"] = sol
    out["_y"] = y_all
    return out


def figure(tid: str, task: dict, out: dict, cfg: dict, path: Path) -> None:
    sol = out["_sol"]["contact_fit"]
    t = task["frames"][task["in_contact"].astype(bool)] / float(task["fps"])
    fig, ax = plt.subplots(1, 4, figsize=(20, 4.2))
    cols = {"pos": "#2a78d6", "pos_dir": "#eb6834", "pos_dir_budget": "#1baf7a"}
    for p, col in cols.items():
        d = sol[p]
        ax[0].plot(t, 100 * d["err"], color=col, lw=1.5, label=p)
        ax[1].plot(t, d["ang"], color=col, lw=1.5, label=p)
        ax[2].plot(t, np.degrees(np.abs(d["q"] - sol["prior_q"])).max(1), color=col, lw=1.5, label=p)
        bad = ~d["ok"]
        ax[0].scatter(t[bad], 100 * d["err"][bad], color=col, s=8, marker="x")
    ax[0].axhline(100 * cfg["pos_tol_m"], color="#888", ls="--", lw=0.8)
    ax[1].axhline(cfg["max_angle_deg"], color="#888", ls="--", lw=0.8)
    ax[2].axhline(cfg["budget_deg"], color="#888", ls="--", lw=0.8)
    ax[0].set_title("contact-site error [cm] (x = infeasible frame)", fontsize=9, loc="left")
    ax[1].set_title("tool axis vs inward normal [deg]", fontsize=9, loc="left")
    ax[2].set_title("largest joint change from the prior [deg]", fontsize=9, loc="left")
    y = out["_y"]
    ax[3].plot(y[:, 0], y[:, 1], color="#2b2b2b", lw=2, label="contact target")
    ax[3].plot(sol["prior_site"][:, 0], sol["prior_site"][:, 1], color="#888", lw=1, ls="--", label="prior gripper")
    ax[3].set_aspect("equal", adjustable="datalim")
    ax[3].set_title("top view, contact-fit layout [m]", fontsize=9, loc="left")
    for a in ax:
        a.legend(fontsize=7, frameon=False)
        a.tick_params(labelsize=7)
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
    labs = ", ".join(f"{k}: {v}" for k, v in out["labels"].items() if k.startswith("contact_fit"))
    fig.suptitle(f"{tid} · {task['clip']} · {labs}", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=80)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    add_run_args(ap)
    ap.add_argument("--tasks-dir", required=True)
    ap.add_argument("--d0-dir", required=True)
    ap.add_argument("--ids", nargs="*", default=None, help="task ids (default: confirmed ids in configs/push_candidates.yaml)")
    args = ap.parse_args()
    try:
        prov = start_run(args.run_id, needs=("xmorph", "hoi_retarget"),
                         configs=("b2z1.yaml", "external.yaml", "learned/reach.yaml", "registration.yaml",
                                  "push_candidates.yaml"),
                         allow_dirty=args.allow_dirty, allow_external_mismatch=args.allow_external_mismatch)
    except ProvenanceError as e:
        print(f"[refused] {e}", file=sys.stderr)
        return 2
    cfg, reg_cfg = load_config("learned/reach.yaml"), load_config("registration.yaml")["contact_fit"]
    ids = args.ids or [s["id"] for s in yaml.safe_load((REPO_ROOT / "configs" / "push_candidates.yaml").read_text())["segments"]]
    out_dir = Path(args.out or f"outputs/{args.run_id}")
    (out_dir / "tasks").mkdir(parents=True, exist_ok=True)
    (out_dir / "solutions").mkdir(exist_ok=True)
    robot = B2Z1Robot()
    coll = RobotCollision(robot, cfg["penetration_tol_m"])
    bound, sampled = reach_bound(robot)
    results, errors = {}, []
    t0 = time.time()
    for tid in ids:
        try:
            task = load_task(Path(args.tasks_dir) / f"{tid}.npz")
            pkl = Path(args.d0_dir) / f"{task['clip']}_b2z1.pkl"
            sidecar = json.loads(Path(str(pkl) + ".sidecar.json").read_text())
            t1 = time.time()
            r = solve_task(task, load_motion(pkl), sidecar, robot, coll, cfg, reg_cfg, bound)
            if "_sol" in r:
                figure(tid, task, r, cfg, out_dir / "tasks" / f"{tid}.png")
                np.savez_compressed(out_dir / "solutions" / f"{tid}.npz",
                                    **{f"{lay}__{p}__{k}": np.asarray(v) for lay, res in r["_sol"].items()
                                       for p, dd in res.items() if isinstance(dd, dict)
                                       for k, v in dd.items() if k != "start"})
            r.pop("_sol", None)
            r.pop("_y", None)
            r["runtime_s"] = time.time() - t1
            results[tid] = {"clip": task["clip"], "object": task["object"], "mode": task["mode"], **r}
            print(f"  {tid}: {r['labels']}  ({r['runtime_s']:.0f} s)", flush=True)
        except Exception as e:  # noqa: BLE001 - report and continue
            import traceback

            errors.append({"id": tid, "error": traceback.format_exc()[-2000:]})
            print(f"  {tid}: error {type(e).__name__}: {e}", flush=True)
    checks = {"all_tasks_processed": {"pass": not errors and bool(results), "n_errors": len(errors)}}
    summary = {"provenance": prov, "config": cfg, "registration_config": reg_cfg,
               "reach_bound_m": bound, "reach_sampled_max_m": sampled, "checks": checks,
               "pass": all(c["pass"] for c in checks.values()), "errors": errors, "tasks": results,
               "elapsed_s": time.time() - t0}
    (out_dir / "summary.json").write_text(json.dumps(clean(summary), indent=2, default=str), encoding="utf-8")
    f = lambda v, nd=2: "–" if v is None else f"{v:.{nd}f}"  # noqa: E731
    lines = ["# Frozen-body reachability (spec learned v0.6 §7.1)", "",
             f"Run `{prov['run_id']}` · code `{prov['git']['describe']}` (dirty={prov['git']['dirty']}) · "
             f"{len(results)}/{len(ids)} tasks · reach bound {bound:.3f} m (sampled max {sampled:.3f} m) · "
             f"{summary['elapsed_s'] / 60:.1f} min", "",
             "| task | layout | registration (psi, residual RMS) | scene body in object [m] | target–shoulder [m] | problem "
             "| label | feasible | err max [cm] | angle median / max [°] | arm change max / RMS [°] | speed ratio max |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for tid, r in results.items():
        for lay in LAYOUTS:
            if lay not in r:
                continue
            reg = r["registration"][lay]
            L = r[lay]
            for p, *_ in PROBLEMS:
                q = L[p]
                ch = q["arm_change_max_deg"]
                lines.append(f"| {tid} | {lay} | {reg['psi_deg']:.1f}°, {f(reg['info']['residual_xy_rms_m'])} m | "
                             f"{f(L['scene_body_depth_max_m'], 3)} | {f(L['target_to_shoulder_m'][0])}–{f(L['target_to_shoulder_m'][1])} | "
                             f"{p} | {q['label']} | {100 * q['feasible_frac']:.0f} % | {f(100 * q['pos_err_max_m'], 1)} | "
                             f"{f(q['angle_median_deg'], 0)} / {f(q['angle_max_deg'], 0)} | "
                             f"{f(max(ch) if ch else None, 0)} / {f(q['arm_change_rms_deg'], 0)} | {f(q['speed_ratio_max'])} |")
    if errors:
        lines += ["", "## Errors", ""] + [f"- `{e['id']}`: {e['error'].splitlines()[-1]}" for e in errors]
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[4:]))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
