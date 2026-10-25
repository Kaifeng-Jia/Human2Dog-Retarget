#!/usr/bin/env python
"""Screen all OMOMO_new clips for course-version candidates (spec v0.5 §7.1).

Course candidate = single-hand contact interval that looks like pushing/dragging along the floor:
  * one hand only (no other hand, no non-hand body contact) for >= --min-dur seconds,
  * object moves horizontally >= --min-obj-disp m during the interval,
  * object stays low and upright: vertical range <= --max-obj-dz m, rotation <= --max-obj-rot deg,
  * human root moves <= --max-root-disp m during the interval (frozen-body friendly).
Candidates are ranked by (object displacement - root displacement). Right-hand candidates come first
(X-Morph maps the G1 right arm to the Z1); left-hand ones are listed separately.

Writes outputs/<run-id>/{summary.json, report.md, clips.csv, candidates.csv, screen.png}.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from h2d.common.data.omomo_new import MODES, clip_stats, load_clip  # noqa: E402
from h2d.common.runinfo import ProvenanceError, add_run_args, start_run  # noqa: E402
from h2d.paths import data_path  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    add_run_args(ap)
    ap.add_argument("--root", default=None)
    ap.add_argument("--limit", type=int, default=0, help="only the first N files (debug)")
    ap.add_argument("--min-dur", type=float, default=1.0)
    ap.add_argument("--min-obj-disp", type=float, default=0.10)
    ap.add_argument("--max-obj-dz", type=float, default=0.05)
    ap.add_argument("--max-obj-rot", type=float, default=30.0)
    ap.add_argument("--max-root-disp", type=float, default=0.5)
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args()
    try:
        prov = start_run(args.run_id, needs=(), configs=("data.yaml",),
                         allow_dirty=args.allow_dirty, allow_external_mismatch=args.allow_external_mismatch)
    except ProvenanceError as e:
        print(f"[refused] {e}", file=sys.stderr)
        return 2
    root = Path(args.root).expanduser() if args.root else data_path("omomo_new")
    out = Path(args.out or f"outputs/{args.run_id}")
    out.mkdir(parents=True, exist_ok=True)

    files = sorted(root.rglob("*.pt"))
    if args.limit:
        files = files[: args.limit]
    rows, errors = [], []
    for i, f in enumerate(files):
        try:
            s = clip_stats(load_clip(f))
        except Exception as e:  # noqa: BLE001
            errors.append({"file": f.name, "error": str(e)[:300]})
            continue
        b = s["longest_single_hand"] or {}
        rows.append({
            "name": s["name"], "object": s["object"], "subject": s["subject"], "frames": s["frames"],
            "pelvis_z_median_m": round(s["pelvis_z_median_m"], 3),
            **{f"frac_{m}": round(s["mode_fraction"][m], 3) for m in MODES},
            "side": b.get("side"), "start": b.get("start"), "end": b.get("end"),
            "dur_s": round(b.get("duration_s", 0.0), 2),
            "obj_disp_xy_m": round(b.get("obj_disp_xy_m", 0.0), 3),
            "obj_path_xy_m": round(b.get("obj_path_xy_m", 0.0), 3),
            "obj_dz_m": round(b.get("obj_dz_m", 0.0), 3),
            "obj_max_rot_deg": round(b.get("obj_max_rot_deg", 0.0), 1),
            "root_disp_xy_m": round(b.get("root_disp_xy_m", 0.0), 3),
        })
        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{len(files)}", flush=True)

    def ok(r):
        return (r["side"] is not None and r["dur_s"] >= args.min_dur and r["obj_disp_xy_m"] >= args.min_obj_disp
                and r["obj_dz_m"] <= args.max_obj_dz and r["obj_max_rot_deg"] <= args.max_obj_rot
                and r["root_disp_xy_m"] <= args.max_root_disp)

    if not rows:
        print(f"no clip could be loaded from {root}; first errors: {errors[:3]}", file=sys.stderr)
        return 1
    base_fields = list(rows[0].keys())
    cands = sorted([r for r in rows if ok(r)], key=lambda r: -(r["obj_disp_xy_m"] - r["root_disp_xy_m"]))
    right = [r for r in cands if r["side"] == "right"]
    left = [r for r in cands if r["side"] == "left"]
    for r in cands:
        r["score"] = round(r["obj_disp_xy_m"] - r["root_disp_xy_m"], 3)

    with open(out / "clips.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=base_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    with open(out / "candidates.csv", "w", newline="", encoding="utf-8") as f:
        fields = base_fields + ["score"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(right + left)

    pel = np.array([r["pelvis_z_median_m"] for r in rows])
    frac = {m: float(np.mean([r[f"frac_{m}"] for r in rows])) for m in MODES}
    by_obj = {}
    for r in cands:
        by_obj.setdefault(r["object"], [0, 0])
        by_obj[r["object"]][0 if r["side"] == "right" else 1] += 1
    summary = {
        "provenance": prov, "root": str(root), "n_files": len(files), "n_loaded": len(rows),
        "errors": errors[:50], "n_errors": len(errors),
        "criteria": {k: getattr(args, k) for k in ("min_dur", "min_obj_disp", "max_obj_dz", "max_obj_rot", "max_root_disp")},
        "mean_mode_fraction": frac,
        "pelvis_z_median_over_clips_m": float(np.median(pel)) if len(pel) else None,
        "n_candidates_right": len(right), "n_candidates_left": len(left),
        "candidates_by_object_right_left": by_obj,
        "top_right": right[: args.top], "top_left": left[: min(args.top, 10)],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    ax[0].bar(list(frac), list(frac.values()))
    ax[0].set_title("mean fraction of frames per contact mode (all clips)")
    xs = [r["root_disp_xy_m"] for r in rows if r["side"]]
    ys = [r["obj_disp_xy_m"] for r in rows if r["side"]]
    ax[1].scatter(xs, ys, s=4, alpha=0.3, label="longest single-hand interval per clip")
    ax[1].scatter([r["root_disp_xy_m"] for r in right], [r["obj_disp_xy_m"] for r in right], s=10, c="#d62728",
                  label="right-hand candidates")
    ax[1].set_xlabel("human root displacement during contact [m]")
    ax[1].set_ylabel("object displacement during contact [m]")
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "screen.png", dpi=110)

    cols = ["name", "dur_s", "obj_disp_xy_m", "obj_dz_m", "obj_max_rot_deg", "root_disp_xy_m", "score"]
    lines = [
        "# OMOMO_new screening",
        "",
        f"Run `{prov['run_id']}` · code `{prov['git']['describe']}` (dirty={prov['git']['dirty']}) · "
        f"{len(rows)}/{len(files)} clips loaded, {len(errors)} errors · pelvis z median {summary['pelvis_z_median_over_clips_m']}",
        "",
        "Mean mode fractions: " + ", ".join(f"{m} {v:.3f}" for m, v in frac.items()),
        "",
        f"Criteria: {summary['criteria']}",
        f"Candidates: right {len(right)}, left {len(left)}; by object (right, left): {by_obj}",
        "",
        "## Top right-hand candidates",
        "",
        "| " + " | ".join(cols) + " |",
        "|" + "---|" * len(cols),
    ]
    lines += ["| " + " | ".join(str(r[c]) for c in cols) + " |" for r in right[: args.top]]
    lines += ["", "![screen](screen.png)", ""]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:9]))
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
