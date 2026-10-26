#!/usr/bin/env python
"""Extract the human-side task targets of push segments (spec learned v0.6 §4 step 1; h2d/common/data/tasks.py).

Segments: the confirmed ones in ``configs/push_candidates.yaml`` and, with ``--candidates``, every row of a
``push_candidates.py`` candidates.csv (so whichever is confirmed later already has its task). Per segment:
``tasks/<id>.npz`` (object trajectory, contact frames, object-local contact target and normal, approach /
retreat distance, world target path), a sheet ``figures/<id>.png`` and the checks below.

Checks (per task, all must hold): contact frames > 0; contact proxy median <= 8 cm from the surface; patch
coherence median >= 0.8; normal spread p90 <= 20 deg; target equals the on-surface contact target in contact.
Run passes when every confirmed task passes and all files load.

Writes outputs/<run-id>/{summary.json, report.md, tasks.csv, tasks/*.npz, figures/*.png, clips_omomo.txt}.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from h2d.common.data.describe import DEFAULTS, describe_clip, push_descriptors  # noqa: E402
from h2d.common.data.sources import SOURCES  # noqa: E402
from h2d.common.data.tasks import TASK_VERSION, build_task, save_task, task_checks  # noqa: E402
from h2d.common.runinfo import ProvenanceError, add_run_args, start_run  # noqa: E402
from h2d.common.tables import clean, write_csv  # noqa: E402
from h2d.common.viz_hoi import candidate_figure  # noqa: E402
from h2d.paths import REPO_ROOT, data_path  # noqa: E402

LIMITS = {"proxy_surface_dist_median_m": ("<=", 0.08), "patch_coherence_median": (">=", 0.8),
          "normal_spread_p90_deg": ("<=", 20.0), "target_equals_c_bar_in_contact_m": ("<=", 1e-6),
          "contact_frames": (">", 0), "target_on_face_m": ("<=", 0.02)}


def task_ok(ck: dict) -> tuple[bool, list[str]]:
    bad = [k for k, (op, v) in LIMITS.items()
           if not (ck[k] <= v if op == "<=" else ck[k] >= v if op == ">=" else ck[k] > v)]
    return not bad, bad


def segments_to_do(config: Path, cand_csv: Path | None) -> list[dict]:
    cfg = yaml.safe_load(config.read_text())
    out = [{"id": s["id"], "dataset": s["dataset"], "clip": s["clip"], "object": s["object"], "mode": s["mode"],
            "start": int(s["frames"][0]), "end": int(s["frames"][1]), "confirmed": True,
            "interaction": s.get("interaction", "push"), "grip": s.get("grip", "press")} for s in cfg["segments"]]
    seen = {(r["dataset"], r["clip"], r["start"], r["end"]) for r in out}
    if cand_csv:
        with open(cand_csv, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                key = (r["dataset"], r["name"], int(r["start"]), int(r["end"]))
                if key in seen:
                    continue
                seen.add(key)
                out.append({"id": f"c{int(r['rank']):02d}_{r['name']}", "dataset": r["dataset"], "clip": r["name"],
                            "object": r["object"], "mode": r["mode"], "start": key[2], "end": key[3],
                            "confirmed": False, "interaction": r.get("interaction") or "push",
                            "grip": r.get("grip") or "press"})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    add_run_args(ap)
    ap.add_argument("--config", default=str(REPO_ROOT / "configs" / "push_candidates.yaml"))
    ap.add_argument("--candidates", default=None, help="candidates.csv of a push_candidates.py run (optional)")
    ap.add_argument("--omomo-root", default=None)
    ap.add_argument("--force-root", default=None)
    ap.add_argument("--smplh-root", default=None)
    ap.add_argument("--pre-s", type=float, default=1.0)
    ap.add_argument("--post-s", type=float, default=1.0)
    ap.add_argument("--selection", default=None,
                    help="selection config with reach_band: adapt contact heights on side faces to the arm (spec v0.7)")
    args = ap.parse_args()
    band = yaml.safe_load(Path(args.selection).read_text()).get("reach_band") if args.selection else None
    todo = segments_to_do(Path(args.config), Path(args.candidates) if args.candidates else None)
    datasets = sorted({t["dataset"] for t in todo})
    needs = tuple(sorted({n for d in datasets for n in SOURCES[d].needs}))
    try:
        prov = start_run(args.run_id, needs=needs, configs=("data.yaml", "external.yaml", "push_candidates.yaml"),
                         allow_dirty=args.allow_dirty, allow_external_mismatch=args.allow_external_mismatch)
    except ProvenanceError as e:
        print(f"[refused] {e}", file=sys.stderr)
        return 2
    out = Path(args.out or f"outputs/{args.run_id}")
    (out / "tasks").mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(exist_ok=True)
    roots = {"omomo_new": args.omomo_root, "force": args.force_root}
    srcs = {}
    for d in datasets:
        root = Path(roots[d]).expanduser() if roots[d] else data_path(d)
        srcs[d] = SOURCES[d](root, args)
    t0 = time.time()
    rows, errors = [], []
    for t in todo:
        try:
            src = srcs[t["dataset"]]
            f = next(p for p in src.files if p.stem == t["clip"])
            clip, mesh, _ = src.load(f)
            task = build_task(clip, mesh, (t["start"], t["end"]), t["mode"], args.pre_s, args.post_s, band=band,
                              grip=t["grip"])
            ck = task_checks(task)
            ok, bad = task_ok(ck)
            task.update({"dataset": t["dataset"], "id": t["id"], "confirmed": t["confirmed"]})
            save_task(task, out / "tasks" / f"{t['id']}.npz")
            seg = next((r for r in describe_clip(clip, mesh, DEFAULTS, 0)["segments"]
                        if r["start"] == t["start"] and r["end"] == t["end"]), None)
            cand = dict(seg or {"start": t["start"], "end": t["end"], "duration_s": (t["end"] - t["start"]) / clip.fps,
                                "obj_disp_xy_m": float("nan"), "obj_path_xy_m": float("nan"),
                                "obj_tilt_max_deg": float("nan"), "obj_yaw_maxabs_deg": float("nan")})
            cand.update(push_descriptors(clip, mesh, (t["start"], t["end"]), t["mode"]))
            cand["tier"] = "confirmed" if t["confirmed"] else "candidate"
            candidate_figure(clip, mesh, cand, out / "figures" / f"{t['id']}.png", side=t["mode"],
                             title=f"{t['id']} · hand {t['mode']} · {t['dataset']} / {t['object']} · {clip.name} · "
                                   f"frames {t['start']}–{t['end']}")
            rows.append({**t, "pass": ok, "failed": ";".join(bad), **ck,
                         "approach_angle_deg": cand.get("approach_angle_deg"),
                         "retreat_angle_deg": cand.get("retreat_angle_deg"),
                         "normal_tilt_deg": cand.get("normal_tilt_median_deg"),
                         "contact_z_m": float(np.median(task["target_world"][task["in_contact"], 2]))})
            print(f"  {t['id']}: {'ok' if ok else 'FAIL ' + ','.join(bad)}", flush=True)
        except Exception as e:  # noqa: BLE001 - report and continue
            errors.append({"id": t["id"], "error": f"{type(e).__name__}: {str(e)[:300]}"})
            print(f"  {t['id']}: error {errors[-1]['error']}", flush=True)
    write_csv(out / "tasks.csv", rows)
    omomo = sorted({r["clip"] for r in rows if r["dataset"] == "omomo_new"})
    (out / "clips_omomo.txt").write_text("\n".join(omomo) + "\n", encoding="utf-8")
    confirmed = [r for r in rows if r["confirmed"]]
    checks = {
        "all_segments_processed": {"pass": not errors, "n_errors": len(errors), "n_segments": len(todo)},
        "confirmed_tasks_pass": {"pass": bool(confirmed) and all(r["pass"] for r in confirmed),
                                 "n_confirmed": len(confirmed),
                                 "failing": [r["id"] for r in confirmed if not r["pass"]]},
    }
    passed = all(c["pass"] for c in checks.values())
    summary = {"provenance": prov, "task_version": TASK_VERSION, "limits": LIMITS, "reach_band": band, "window_s": [args.pre_s, args.post_s],
               "checks": checks, "pass": passed, "errors": errors, "tasks": rows,
               "data_versions": {d: s.versions() for d, s in srcs.items()}, "elapsed_s": time.time() - t0}
    (out / "summary.json").write_text(json.dumps(clean(summary), indent=2), encoding="utf-8")
    f2 = lambda v, nd=2: "–" if v is None or v != v else f"{v:.{nd}f}"  # noqa: E731
    lines = ["# Task targets (spec learned v0.6 §4 step 1)", "",
             f"Run `{prov['run_id']}` · code `{prov['git']['describe']}` (dirty={prov['git']['dirty']}) · "
             f"{len(rows)}/{len(todo)} segments · {len(errors)} errors · **{'PASS' if passed else 'FAIL'}**", "",
             "| id | confirmed | hand | dataset / clip | frames | contact z human → robot [m] | face tilt [°] | proxy–surface [m] | "
             "coherence | spread p90 [°] | approach / retreat [°] | d max [m] | grip | palm vs face [°] | pass |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {r['confirmed']} | {r['mode']} | {r['dataset']} / {r['clip']} | {r['start']}–{r['end']} | "
                     f"{f2(r['contact_z_m'] - r['height_shift_m'])} → {f2(r['robot_contact_z_m'])}{'' if r['in_band'] else ' (out of band)'} | {f2(r['normal_tilt_deg'], 0)} | {f2(r['proxy_surface_dist_median_m'], 3)} | "
                     f"{f2(r['patch_coherence_median'])} | {f2(r['normal_spread_p90_deg'], 1)} | "
                     f"{f2(r['approach_angle_deg'], 0)} / {f2(r['retreat_angle_deg'], 0)} | {f2(r['d_max_m'])} | "
                     f"{r['grip']} | {f2(r['palm_face_deg'], 0)}{'' if r['palm_used'] else ' (not used)'} | {r['pass']} |")
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"pass={passed}  tasks={len(rows)}  -> {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
