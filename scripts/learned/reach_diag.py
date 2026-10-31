#!/usr/bin/env python
"""Evaluate body layouts for the learned line (spec §7): the legs follow the X-Morph prior, the body is placed by a
layout, and the Z1 arm is solved to reach the human's contact targets.

Inputs: task files from ``scripts/common/prepare_tasks.py`` and the prior from ``scripts/learned/d0_chain.py``
(``<clip>_b2z1.pkl`` + sidecar). Per task:

1. body layouts (``h2d/common/registration.py``, ``h2d/learned/imesh.py``): ``reach_fit`` (the prior: one constant
   SE(2) placing a nominal reach point of the base on the contact targets); ``reach_track`` (the script baseline:
   the same plus a smoothed per-frame translation, the body follows the object); ``mesh`` (ours, spec §5.5:
   per-frame SE(2) keeping the human's body-object relations); ``start_anchored`` (the prior started where the
   human started). The object trajectory is fixed. Every layout gets the relation metrics of the mesh (edge
   direction and heading errors, extra foot slide) on the contact frames;
2. for each layout and each contact frame, three problems with the multi-start, collision-aware arm IK
   (``h2d/learned/reach.py``): position (joint limits only), position + direction (joint limits only),
   position + direction within +-budget around the prior. The direction is the task's tool approach target (the
   human forearm within a cone about the inward normal, spec §5.4), with the hand's roll as a soft roll target;
3. per problem: frames feasible (error <= pos_tol, angle <= max_angle, no self / floor / arm-object
   collision), failure labels, joint speed over consecutive feasible frames against the Z1 limit, arm change
   (per-joint max and RMS, deg), jump to the prior at the segment ends; the frozen body's penetration of the
   object (scene infeasible).

Failure labels (spec §7.1): "proven_unreachable" (target farther from the joint1 anchor than the sum of the arm's
segment lengths), "no_feasible_solution_within_budget" (all other failures of the local search),
"coordinate_or_tool_offset_error" (frame mismatch, target below the floor). A large registration residual is the
prior's path drift and is reported in ``notes``, not as a label.

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
from h2d.common.data.candidates import face_of  # noqa: E402
from h2d.common.registration import SE2Track, contact_fit, reach_points, start_anchored, track  # noqa: E402
from h2d.common.robot import B2Z1Robot  # noqa: E402
from h2d.common.runinfo import ProvenanceError, add_run_args, start_run  # noqa: E402
from h2d.common.tables import clean  # noqa: E402
from h2d.learned.prior import Motion, load_motion  # noqa: E402
from h2d.learned.imesh import InteractionMesh, object_samples, prior_points  # noqa: E402
from h2d.learned.reach import ArmIK, ObjectPose, reach_bound, shoulder  # noqa: E402
from h2d.paths import REPO_ROOT, load_config  # noqa: E402

PROBLEMS = (("pos", False, False), ("pos_dir", True, False), ("pos_dir_budget", True, True))
LAYOUTS = ("mesh", "reach_track", "reach_fit", "start_anchored")   # ours, script baseline, prior, start anchor


def solve_task(task: dict, motion: Motion, sidecar: dict, robot: B2Z1Robot, coll: RobotCollision, cfg: dict,
               reg_cfg: dict, bound: float, reach_cfg: dict, mesh_cfg: dict, layouts=LAYOUTS) -> dict:
    fr, c = task["frames"], task["in_contact"].astype(bool)
    cf = fr[c]
    out = {"labels": {}, "flags": [], "notes": []}     # flags: coordinate problems; notes: everything else
    if motion.n < fr[-1] + 1:
        out["flags"].append(f"prior has {motion.n} frames, task needs {fr[-1] + 1}")
        out["labels"] = {f"{lay}/{p}": "coordinate_or_tool_offset_error" for lay in LAYOUTS for p, *_ in PROBLEMS}
        return out
    y_all = task["target_world"][c]
    if y_all[:, 2].min() < -0.02:
        out["flags"].append(f"target below the floor ({y_all[:, 2].min():.3f} m)")
    obj = load_object(task["object"])
    if not task["forearm_used"]:
        out["notes"].append(f"forearm points away ({float(task['forearm_face_deg']):.0f}° from the inward normal): "
                            "approach = inward normal")
    if not task["palm_used"]:
        out["notes"].append(f"palm {float(task['palm_face_deg']):.0f}° off the contact: no roll target")
    if task["palm_flipped"]:
        out["notes"].append("palm side taken from the contact (the hand's points gave it mirrored)")
    hull = ObjectHull.from_vertices(obj.hull_verts)
    arm_idx = slice(12, 18)

    def set_frame(t, T, i=None):
        if hasattr(T, "apply_root_at"):
            rp, rq = T.apply_root_at(i, motion.root_pos[t][None], motion.root_rot_xyzw[t][None])
        else:
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
    k0 = int(np.flatnonzero(c)[0])
    face = face_of(float(np.degrees(np.arcsin(min(1.0, abs((R.from_quat(task["obj_rot_xyzw"][k0]).as_matrix()
                                                                @ task["n_bar_local"])[2]))))))
    ahead = reach_cfg["reach_point"]["ahead_m"].get(face, 0.7)
    p_reach = reach_points(motion.root_pos[cf], motion.root_rot_xyzw[cf], ahead)
    fit = contact_fit(p_reach, y_all, None, anchor.psi, reg_cfg["lambda_psi"], reg_cfg["min_target_spread_m"],
                      reg_cfg["psi_grid_deg"])
    fit.kind = "reach_fit"
    trk = track(p_reach, y_all, fit, float(task["fps"]), reach_cfg["track"]["smooth_s"])
    anchor_res = np.linalg.norm(anchor.apply_points(p_raw)[:, :2] - y_all[:, :2], axis=1)
    anchor.info = {"residual_xy_rms_m": float(np.sqrt(np.mean(anchor_res ** 2))), "residual_xy_max_m": float(anchor_res.max())}
    out["registration"] = {"reach_fit": fit.to_dict(), "reach_track": trk.to_dict(), "start_anchored": anchor.to_dict(),
                           "face": face, "reach_ahead_m": ahead}
    if fit.info["residual_xy_rms_m"] > cfg["registration_residual_suspect_m"]:
        # the prior's own root path drifts from the source (speed mapping, half turn rate), which one SE(2) cannot
        # remove; reported, not a coordinate error
        out["notes"].append(f"contact-fit residual {fit.info['residual_xy_rms_m']:.2f} m (prior path drift)")
    placed = {"reach_fit": fit, "reach_track": trk, "start_anchored": anchor}
    n_w, ci = len(fr), np.flatnonzero(c)
    im = InteractionMesh(task, prior_points(robot, coll, motion, fr),
                         object_samples(obj.hull_verts, mesh_cfg["object_samples"]), hull, mesh_cfg)
    psi_w, b_w, info = im.place(fit.psi, np.asarray(fit.b))
    placed["mesh"] = SE2Track(psi_w[c], b_w[c], kind="mesh", info=info)
    out["registration"]["mesh"] = placed["mesh"].to_dict()

    def window(T):              # a layout over the whole window (a track is held outside the contact frames)
        if isinstance(T, SE2Track):
            return (np.interp(np.arange(n_w), ci, np.broadcast_to(T.psi, len(T.b))),
                    np.stack([np.interp(np.arange(n_w), ci, T.b[:, k]) for k in (0, 1)], 1))
        return np.full(n_w, T.psi), np.tile(np.asarray(T.b), (n_w, 1))
    rel = {k: im.metrics(*((psi_w, b_w) if k == "mesh" else window(T)), sel=ci) for k, T in placed.items()}

    ik = ArmIK(robot, coll, cfg["pos_tol_m"], cfg["max_angle_deg"], cfg["n_random_starts"],
               margin_m=cfg["avoid_margin_m"], w_prev=cfg.get("prev_weight_m_per_rad", 0.0),
               w_roll=cfg.get("roll_weight_m", 0.0))
    vmax = np.asarray(cfg["joint_speed_limit_rad_s"])
    budget = np.radians(cfg["budget_deg"])
    fps = float(task["fps"])
    sol = {}
    for lay, T in ((k, placed[k]) for k in layouts if k in placed):
        n_c = len(cf)
        prior_q = np.array([motion.dof_pos[t][arm_idx] for t in cf])
        psi_c = np.broadcast_to(np.asarray(T.psi, float), (n_c,)).copy()                 # body placement per frame
        b_c = np.asarray(T.b, float).reshape(-1, 2) if isinstance(T, SE2Track) else np.tile(np.asarray(T.b, float), (n_c, 1))
        scene, prior_site, dist_sh = np.zeros(n_c), np.zeros((n_c, 3)), np.zeros(n_c)
        res = {p: {"q": np.zeros((n_c, 6)), "err": np.zeros(n_c), "ang": np.zeros(n_c), "roll": np.zeros(n_c),
                   "ok": np.zeros(n_c, bool),
                   "self": np.zeros(n_c), "floor": np.zeros(n_c), "armobj": np.zeros(n_c), "toolobj": np.zeros(n_c),
                   "start": []} for p, *_ in PROBLEMS}
        prev = {p: None for p, *_ in PROBLEMS}
        for i, t in enumerate(cf):
            set_frame(t, T, i)
            base_q = robot.data.qpos.copy()
            k = int(np.flatnonzero(fr == t)[0])
            op = ObjectPose(hull, task["obj_pos"][k], R.from_quat(task["obj_rot_xyzw"][k]).as_matrix())
            n_dir = -(op.rot @ task["tool_x_local"][k])
            z_ref = op.rot @ task["tool_z_local"][k]
            y = task["target_world"][k]
            prior_site[i] = robot.contact_site()
            dist_sh[i] = float(np.linalg.norm(y - shoulder(robot)))
            scene[i] = coll.check(hull, op.to_local)["body_obj_depth_m"]
            for p, use_dir, use_budget in PROBLEMS:
                robot.set_qpos(base_q)
                full = i % cfg["full_search_every"] == 0 or prev[p] is not None
                r = ik.solve(y, n_dir, prior_q[i], prev[p], use_dir, budget if use_budget else None, op, full, z_ref)
                d = res[p]
                d["q"][i], d["err"][i], d["ang"][i], d["ok"][i] = r.q, r.pos_err_m, r.angle_deg, r.feasible
                d["roll"][i] = r.roll_deg
                d["self"][i], d["floor"][i] = r.collision["self_min_dist_m"], r.collision["floor_min_dist_m"]
                d["armobj"][i], d["toolobj"][i] = r.collision["arm_obj_depth_m"], r.collision["tool_obj_depth_m"]
                d["start"].append(r.start)
                prev[p] = r.q if r.feasible else None
        lay_out = {"relations": rel[lay], "scene_body_depth_max_m": float(scene.max()),
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
                "roll_median_deg": float(np.nanmedian(d["roll"])) if np.isfinite(d["roll"]).any() else None,
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
        sol[lay] = res | {"prior_q": prior_q, "prior_site": prior_site, "dist_shoulder": dist_sh, "scene": scene,
                          "psi": psi_c, "b": b_c}
    out["_sol"] = sol
    out["_y"] = y_all
    return out


def figure(tid: str, task: dict, out: dict, cfg: dict, path: Path) -> None:
    lay = next(k for k in LAYOUTS if k in out["_sol"])
    sol = out["_sol"][lay]
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
    ax[1].set_title("tool axis vs approach target [deg]", fontsize=9, loc="left")
    ax[2].set_title("largest joint change from the prior [deg]", fontsize=9, loc="left")
    y = out["_y"]
    ax[3].plot(y[:, 0], y[:, 1], color="#2b2b2b", lw=2, label="contact target")
    ax[3].plot(sol["prior_site"][:, 0], sol["prior_site"][:, 1], color="#888", lw=1, ls="--", label="prior gripper")
    ax[3].set_aspect("equal", adjustable="datalim")
    ax[3].set_title(f"top view, {lay} layout [m]", fontsize=9, loc="left")
    for a in ax:
        a.legend(fontsize=7, frameon=False)
        a.tick_params(labelsize=7)
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
    labs = ", ".join(f"{k}: {v}" for k, v in out["labels"].items() if k.startswith(lay))
    fig.suptitle(f"{tid} · {task['clip']} · {labs}", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=80)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    add_run_args(ap)
    ap.add_argument("--tasks-dir", required=True)
    ap.add_argument("--d0-dir", required=True)
    ap.add_argument("--ids", nargs="*", default=None, help="task ids (default: the pilot segments in configs/push_candidates.yaml)")
    ap.add_argument("--tasks-csv", default=None, help="tasks.csv of prepare_tasks.py: take its passing candidates in order")
    ap.add_argument("--max-tasks", type=int, default=8, help="with --tasks-csv: at most this many")
    ap.add_argument("--layouts", nargs="*", default=["mesh", "reach_track", "reach_fit"], choices=LAYOUTS)
    args = ap.parse_args()
    try:
        prov = start_run(args.run_id, needs=("xmorph", "hoi_retarget"),
                         configs=("b2z1.yaml", "external.yaml", "learned/reach.yaml", "learned/mesh.yaml",
                                  "registration.yaml", "push_candidates.yaml"),
                         allow_dirty=args.allow_dirty, allow_external_mismatch=args.allow_external_mismatch)
    except ProvenanceError as e:
        print(f"[refused] {e}", file=sys.stderr)
        return 2
    reg_all = load_config("registration.yaml")
    cfg, reg_cfg, mesh_cfg = load_config("learned/reach.yaml"), reg_all["contact_fit"], load_config("learned/mesh.yaml")
    if args.tasks_csv:
        import csv

        with open(args.tasks_csv, newline="", encoding="utf-8") as fh:
            rows = [r for r in csv.DictReader(fh) if r["pass"] == "True" and r["confirmed"] == "False"  # candidates
                    and r["dataset"] == "omomo_new"                    # the prior chain covers OMOMO_new only
                    and r["grip"] != "grasp"]                          # grasping needs the jaw site (not modelled)
        ids = [r["id"] for r in rows][: args.max_tasks]
    else:
        ids = args.ids or [s["id"] for s in
                           yaml.safe_load((REPO_ROOT / "configs" / "push_candidates.yaml").read_text())["segments"]]
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
            r = solve_task(task, load_motion(pkl), sidecar, robot, coll, cfg, reg_cfg, bound, reg_all, mesh_cfg,
                           args.layouts)
            if "_sol" in r:
                figure(tid, task, r, cfg, out_dir / "tasks" / f"{tid}.png")
                arrays = {}
                for lay, res in r["_sol"].items():          # <layout>__<problem>__<key> and <layout>__<key>
                    for k, v in res.items():
                        if isinstance(v, dict):
                            arrays.update({f"{lay}__{k}__{kk}": np.asarray(vv) for kk, vv in v.items() if kk != "start"})
                        else:
                            arrays[f"{lay}__{k}"] = np.asarray(v)
                np.savez_compressed(out_dir / "solutions" / f"{tid}.npz", **arrays)
            r.pop("_sol", None)
            r.pop("_y", None)
            r["runtime_s"] = time.time() - t1
            results[tid] = {"clip": task["clip"], "object": task["object"], "mode": task["mode"],
                            "grip": task["grip"], "palm_used": task["palm_used"], "palm_face_deg": task["palm_face_deg"],
                            "forearm_used": task["forearm_used"], "forearm_face_deg": task["forearm_face_deg"],
                            "contact_moved": task["height"]["contact_moved"], **r}
            print(f"  {tid}: {r['labels']}  ({r['runtime_s']:.0f} s)", flush=True)
        except Exception as e:  # noqa: BLE001 - report and continue
            import traceback

            errors.append({"id": tid, "error": traceback.format_exc()[-2000:]})
            print(f"  {tid}: error {type(e).__name__}: {e}", flush=True)
    checks = {"all_tasks_processed": {"pass": not errors and bool(results), "n_errors": len(errors)}}
    summary = {"provenance": prov, "config": cfg, "registration_config": reg_cfg, "mesh_config": mesh_cfg,
               "reach_bound_m": bound, "reach_sampled_max_m": sampled, "checks": checks,
               "pass": all(c["pass"] for c in checks.values()), "errors": errors, "tasks": results,
               "elapsed_s": time.time() - t0}
    (out_dir / "summary.json").write_text(json.dumps(clean(summary), indent=2, default=str), encoding="utf-8")
    f = lambda v, nd=2: "–" if v is None else f"{v:.{nd}f}"  # noqa: E731
    lines = ["# Body layouts and arm reachability (spec §7)", "",
             f"Run `{prov['run_id']}` · code `{prov['git']['describe']}` (dirty={prov['git']['dirty']}) · "
             f"{len(results)}/{len(ids)} tasks · reach bound {bound:.3f} m (sampled max {sampled:.3f} m) · "
             f"{summary['elapsed_s'] / 60:.1f} min", "",
             "| task | layout | registration (psi, residual RMS) | relations: edge / heading [°], foot slide [m/s] "
             "| scene body in object [m] | target–shoulder [m] | problem "
             "| label | feasible | err max [cm] | angle median / max [°] | roll median [°] | arm change max / RMS [°] "
             "| speed ratio max |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for tid, r in results.items():
        for lay in LAYOUTS:
            if lay not in r:
                continue
            reg = r["registration"][lay]
            L = r[lay]
            for p, *_ in PROBLEMS:
                q = L[p]
                ch = q["arm_change_max_deg"]
                extra = (f", body +{f(reg['info']['extra_base_shift_max_m'])} m" if lay == "reach_track" else "")
                rl = L["relations"] or {}
                rel_s = (f"{f(rl.get('edge_dir_err_deg'), 0)} / {f(rl.get('heading_err_deg'), 0)}, "
                         f"{f(rl.get('extra_foot_slide_max_mps'))}") if rl else "–"
                lines.append(f"| {tid} | {lay} | {reg['psi_deg']:.1f}°, {f((reg['info'] or {}).get('residual_xy_rms_m'))} m{extra} | "
                             f"{rel_s} | "
                             f"{f(L['scene_body_depth_max_m'], 3)} | {f(L['target_to_shoulder_m'][0])}–{f(L['target_to_shoulder_m'][1])} | "
                             f"{p} | {q['label']} | {100 * q['feasible_frac']:.0f} % | {f(100 * q['pos_err_max_m'], 1)} | "
                             f"{f(q['angle_median_deg'], 0)} / {f(q['angle_max_deg'], 0)} | {f(q['roll_median_deg'], 0)} | "
                             f"{f(max(ch) if ch else None, 0)} / {f(q['arm_change_rms_deg'], 0)} | {f(q['speed_ratio_max'])} |")
    notes = [f"- `{tid}`: " + "; ".join(r.get("flags", []) + r.get("notes", [])) for tid, r in results.items()
             if r.get("flags") or r.get("notes")]
    if notes:
        lines += ["", "## Flags and notes", ""] + notes
    if errors:
        lines += ["", "## Errors", ""] + [f"- `{e['id']}`: {e['error'].splitlines()[-1]}" for e in errors]
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[4:]))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
