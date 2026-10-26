#!/usr/bin/env python
"""Propose push candidates for the first reachability diagnostic (spec learned v0.6 §7.1 step 1).

For every clip of the chosen datasets: hand-contact segments (``describe_clip``), the segment criteria, and for
the segments that pass them the push descriptors of the segment's virtual hand (one hand, or both hands: the
midpoint; spec v0.6 §5.1): push vs pull, contact face and its normal, approach and retreat direction
(``push_descriptors``) and the push criteria (``h2d/common/data/candidates.py``). The
passing segments are ranked and at most ``--top`` are proposed, then confirmed by hand.

Checks: all files processed; at least 3 candidates; the contact proxy lies on the object surface for the
segments that reach the push criteria (median <= 8 cm, a convention check like the profile's); FORCE data at
the pinned commit (when FORCE is used).

Writes outputs/<run-id>/{summary.json, report.md, candidates.csv, pool.csv (every slid segment with the
criteria it fails), gallery.png, candidates/<rank>_<clip>.png, videos/<rank>_<clip>.mp4 (with --videos)}.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from h2d.common.data import candidates as cd  # noqa: E402
from h2d.common.data.describe import DEFAULTS, MODE_OF_HANDS, describe_clip, push_descriptors  # noqa: E402
from h2d.common.data.sources import SOURCES  # noqa: E402
from h2d.common.runinfo import ProvenanceError, add_run_args, start_run  # noqa: E402
from h2d.common.tables import clean, nanmed, write_csv  # noqa: E402
from h2d.common.viz_hoi import candidate_figure, example_video, gallery  # noqa: E402
from h2d.paths import data_path  # noqa: E402

MIN_CANDIDATES = 3
CHECK_ON_SURFACE_M = 0.08
POOL_COLS = ["dataset", "object", "name", "subject", "seg", "start", "end", "start_s", "duration_s", "hands",
             "mode", "object_state", "human", "passed", "failed", "obj_disp_xy_m", "obj_path_xy_m", "obj_lifted_frac",
             "obj_tilt_max_deg", "obj_yaw_maxabs_deg", "frac_body", "contact_z_median_m", "root_disp_xy_m",
             "push_alignment", "moving_frac", "normal_spread_p90_deg", "normal_tilt_median_deg",
             "patch_coherence_median", "hands_face_angle_deg", "contact_surface_dist_median_m", "approach_angle_deg",
             "approach_time_s",
             "retreat_angle_deg", "retreat_time_s", "approach_available_s", "retreat_available_s",
             "ann_hands", "ann_dir", "ann_weight_kg"]
CAND_COLS = ["rank", "tier", "mode"] + POOL_COLS[:4] + ["start_s", "duration_s", "obj_disp_xy_m", "push_alignment",
             "normal_spread_p90_deg", "normal_tilt_median_deg", "patch_coherence_median", "hands_face_angle_deg",
             "approach_angle_deg", "retreat_angle_deg", "approach_available_s", "contact_z_median_m", "contact_surface_dist_median_m",
             "obj_tilt_max_deg", "obj_yaw_maxabs_deg", "frac_body", "root_disp_xy_m", "human", "obj_size_m",
             "normal_local", "start", "end", "ann_hands", "ann_dir", "ann_weight_kg"]


def main() -> int:
    ap = argparse.ArgumentParser()
    add_run_args(ap)
    ap.add_argument("--datasets", nargs="+", default=["omomo_new", "force"], choices=sorted(SOURCES))
    ap.add_argument("--omomo-root", default=None)
    ap.add_argument("--force-root", default=None)
    ap.add_argument("--smplh-root", default=None, help="FORCE: folder with SMPLH_{male,female}.pkl")
    ap.add_argument("--top", type=int, default=16)
    ap.add_argument("--per-object", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0, help="only the first N files per dataset (debug)")
    ap.add_argument("--objects", nargs="*", default=None, help="only these objects (debug)")
    ap.add_argument("--videos", action="store_true", help="also write an MP4 per candidate (needs ffmpeg)")
    args = ap.parse_args()
    needs = tuple(sorted({n for d in args.datasets for n in SOURCES[d].needs}))
    try:
        prov = start_run(args.run_id, needs=needs, configs=("data.yaml", "external.yaml"),
                         allow_dirty=args.allow_dirty, allow_external_mismatch=args.allow_external_mismatch)
    except ProvenanceError as e:
        print(f"[refused] {e}", file=sys.stderr)
        return 2
    out = Path(args.out or f"outputs/{args.run_id}")
    (out / "candidates").mkdir(parents=True, exist_ok=True)

    roots = {"omomo_new": args.omomo_root, "force": args.force_root}
    srcs, versions, files, errors, pool, n_segs = {}, {}, {}, [], [], Counter()
    t0 = time.time()
    for ds in args.datasets:
        root = Path(roots[ds]).expanduser() if roots[ds] else data_path(ds)
        src = SOURCES[ds](root, args)
        srcs[ds], versions[ds] = src, {"root": str(root), **src.versions()}
        fs = [f for f in src.files if not args.objects or src.object_of(f) in args.objects]
        files[ds] = fs[: args.limit] if args.limit else fs
        print(f"{ds}: {len(files[ds])} files", flush=True)
        for i, f in enumerate(files[ds]):
            try:
                c, mesh, extra = src.load(f)
                d = describe_clip(c, mesh, DEFAULTS, mesh_check_frames=0)
                size = "x".join(f"{v:.2f}" for v in mesh.extents)
                for r in d["segments"]:
                    n_segs[ds] += 1
                    r = {"dataset": ds, **r, **{k: v for k, v in extra.items() if k.startswith("ann_")},
                         "obj_size_m": size, "file": f.name}
                    fail = cd.failed(r, cd.SEGMENT_CRITERIA)
                    if not fail:
                        r["mode"] = MODE_OF_HANDS[r["hands"]]
                        r.update(push_descriptors(c, mesh, (r["start"], r["end"]), r["mode"]))
                        fail = cd.failed(r, cd.PUSH_CRITERIA)
                    r["failed"] = ";".join(fail)
                    r["passed"] = not fail
                    pool.append(r)
            except Exception as e:  # noqa: BLE001 - report and continue
                errors.append({"dataset": ds, "file": f.name, "error": f"{type(e).__name__}: {str(e)[:300]}"})
            if (i + 1) % 200 == 0:
                print(f"  {ds} {i + 1}/{len(files[ds])}  ({time.time() - t0:.0f} s)", flush=True)
    if not pool:
        print(f"no segment found; first errors: {errors[:3]}", file=sys.stderr)
        return 1

    chosen = cd.select(pool, top=args.top, per_object=args.per_object)
    slid = [r for r in pool if r["object_state"] == "slid"]
    write_csv(out / "pool.csv", slid, POOL_COLS)
    write_csv(out / "candidates.csv", chosen, CAND_COLS)
    funnels = {ds: cd.funnel([r for r in pool if r["dataset"] == ds]) for ds in args.datasets}
    by_object = {}
    for ds in args.datasets:
        rows = [r for r in pool if r["dataset"] == ds and r["object_state"] == "slid"]
        for o in sorted({r["object"] for r in rows}):
            R_ = [r for r in rows if r["object"] == o]
            by_object[f"{ds}/{o}"] = {"slid": len(R_), "passed": sum(r["passed"] for r in R_),
                                      "first_failure": dict(Counter(r["failed"].split(";")[0] for r in R_
                                                                    if r["failed"]).most_common(4))}

    # ---------------------------------------------------------------- figures for the candidates
    items = []
    for c in chosen:
        src = srcs[c["dataset"]]
        f = next(p for p in files[c["dataset"]] if p.name == c["file"])
        clip, mesh, _ = src.load(f)
        c["file_sha256_16"] = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
        stem = f"{c['rank']:02d}_{clip.name}"
        title = (f"#{c['rank']} tier {c['tier']} · hand {c['mode']}  ·  {c['dataset']} / {c['object']}  ·  {clip.name}  ·  "
                 f"segment {c['start_s']:.2f}–{c['start_s'] + c['duration_s']:.2f} s")
        candidate_figure(clip, mesh, c, out / "candidates" / f"{stem}.png", side=c["mode"], title=title)
        c["figure"] = f"candidates/{stem}.png"
        if args.videos:
            (out / "videos").mkdir(exist_ok=True)
            seg_rows = [{"start": c["start"], "end": c["end"], "hands": c["hands"], "object_state": c["object_state"],
                         "human": c["human"]}]
            if not example_video(clip, mesh, seg_rows, out / "videos" / f"{stem}.mp4"):
                print("[warn] ffmpeg writer not available: no videos", file=sys.stderr)
                args.videos = False
        items.append((clip, mesh, c))
    if items:
        gallery(items, out / "gallery.png")

    # ---------------------------------------------------------------- checks, summary, report
    reached = [r for r in pool if not cd.failed(r, cd.SEGMENT_CRITERIA)]
    on_surf = nanmed([r.get("contact_surface_dist_median_m") for r in reached])
    checks = {
        "all_files_processed": {"pass": not errors, "n_errors": len(errors)},
        "enough_candidates": {"pass": len(chosen) >= MIN_CANDIDATES, "threshold": MIN_CANDIDATES,
                              "n_candidates": len(chosen), "n_passing_segments": sum(r["passed"] for r in pool)},
        "contact_proxy_on_surface": {"pass": bool(on_surf <= CHECK_ON_SURFACE_M) if reached else True,
                                     "threshold_m": CHECK_ON_SURFACE_M, "median_m": on_surf,
                                     "n_segments": len(reached)},
    }
    if "force" in versions:
        checks["force_data_pinned"] = {"pass": bool(versions["force"]["force_commit_match"]),
                                       "actual": versions["force"]["force_commit"],
                                       "pinned": versions["force"]["force_commit_pinned"]}
    passed = all(v["pass"] for v in checks.values())
    summary = {
        "provenance": prov, "datasets": args.datasets, "data_versions": versions,
        "n_files": {ds: len(files[ds]) for ds in args.datasets}, "n_segments": dict(n_segs),
        "n_slid_segments": len(slid), "errors": errors[:50], "segment_params": DEFAULTS,
        "criteria": cd.criteria_table(), "ranking": {"near_normal_deg": cd.NEAR_NORMAL_DEG,
                                                     "vertical_face_deg": cd.VERTICAL_FACE_DEG,
                                                     "top": args.top, "per_object": args.per_object},
        "funnel": {ds: dict(f) for ds, f in funnels.items()}, "by_object": by_object,
        "passed_by_mode": dict(Counter(f"{r['dataset']}/{r['mode']}" for r in pool if r["passed"])),
        "checks": checks, "pass": passed,
        "candidates": [{k: c.get(k) for k in CAND_COLS + ["figure", "file", "file_sha256_16"]} for c in chosen],
        "elapsed_s": time.time() - t0,
    }
    (out / "summary.json").write_text(json.dumps(clean(summary), indent=2), encoding="utf-8")

    def f1(v, nd=1):
        return "–" if v is None or math.isnan(v) else f"{v:.{nd}f}"

    lines = [
        "# Push candidates (spec learned v0.6 §7.1 step 1)", "",
        f"Run `{prov['run_id']}` · code `{prov['git']['describe']}` (dirty={prov['git']['dirty']}) · "
        + " · ".join(f"{ds} {len(files[ds])} files, {n_segs[ds]} segments" for ds in args.datasets)
        + f" · {len(errors)} errors · {summary['elapsed_s'] / 60:.1f} min", "",
        f"**Checks: {'PASS' if passed else 'FAIL'}** — "
        + ", ".join(f"{k}: {'pass' if v['pass'] else 'FAIL'}" for k, v in checks.items()), "",
        "## Criteria (in order) and how many segments are left", "",
        "| criterion | rule | meaning | " + " | ".join(args.datasets) + " |",
        "|---|---|---|" + "---|" * len(args.datasets),
        "| all segments | | | " + " | ".join(str(dict(funnels[ds])["all segments"]) for ds in args.datasets) + " |",
    ]
    for c in cd.criteria_table():
        lines.append(f"| {c['name']} | `{c['key']} {c['op']} {c['value']}` | {c['meaning']} | "
                     + " | ".join(str(dict(funnels[ds])[c["name"]]) for ds in args.datasets) + " |")
    lines += ["", f"Ranking: tier (A = approach and retreat observed and within {cd.NEAR_NORMAL_DEG:.0f}° of the "
              "normal; B = within, but one is not observable; C = sideways), then a vertical face "
              f"(tilt ≤ {cd.VERTICAL_FACE_DEG:.0f}°), then duration × displacement; at most {args.per_object} "
              "per object, one per clip.", "",
              "Passing segments by virtual-hand mode (R = right hand, L = left hand, B = both hands on one face): "
              + ", ".join(f"{m} {n}" for m, n in sorted(Counter(r["mode"] for r in pool if r["passed"]).items())),
              "", "## Candidates", "", "![gallery](gallery.png)", "",
              "| # | tier | mode | dataset / object | clip | segment [s] | moves [m] | push | spread p90 [°] | face tilt [°] "
              "| approach / retreat [°] | contact z [m] | figure |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in chosen:
        lines.append(f"| {c['rank']} | {c['tier']} | {c['mode']} | {c['dataset']} / {c['object']} | {c['name']} | "
                     f"{c['start_s']:.1f}–{c['start_s'] + c['duration_s']:.1f} | {f1(c['obj_disp_xy_m'], 2)} | "
                     f"{f1(c['push_alignment'], 2)} | {f1(c['normal_spread_p90_deg'])} | "
                     f"{f1(c['normal_tilt_median_deg'])} | {f1(c['approach_angle_deg'])} / "
                     f"{f1(c['retreat_angle_deg'])} | {f1(c['contact_z_median_m'], 2)} | [png]({c['figure']}) |")
    lines += ["", "## Slid segments per object (passed / slid, most common first failure)", "",
              "| dataset / object | slid | passed | first failure |", "|---|---|---|---|"]
    for k, v in by_object.items():
        ff = ", ".join(f"{a} {b}" for a, b in v["first_failure"].items())
        lines.append(f"| {k} | {v['slid']} | {v['passed']} | {ff} |")
    if errors:
        lines += ["", "## Errors", ""] + [f"- {e['dataset']} `{e['file']}`: {e['error']}" for e in errors[:20]]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"pass={passed}  candidates={len(chosen)}  -> {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
