#!/usr/bin/env python
"""Profile OMOMO_new: what interactions the data contains (descriptive only, no selection).

For every clip, hand-contact segments with raw descriptors and coarse labels
(``h2d/common/data/describe.py``); per-object aggregates; which body parts touch the objects; and two
convention checks:

* mesh / pose: the bodies flagged in contact lie on the object surface when the recorded object pose
  is applied to the InterMimic meshes (per object, median distance of the closest flagged hand body);
* floor: objects rest at z = 0 at the clip start.

Examples: for every object, the most common and second most common (hands, object state) of the
clip's longest segment; within each, the clip whose duration is closest to the group median.
Each example gets a keyframe + timeline PNG, and with ``--videos`` an MP4 (for Google Drive).

Writes outputs/<run-id>/{summary.json, report.md, clips.csv, segments.csv, per_object.csv, overview.png,
distributions.png, bodies.png, checks.png, examples/<clip>.png, videos/<clip>.mp4}.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from h2d.common.data.describe import DEFAULTS, HAND_LABELS, OBJECT_STATES, describe_clip  # noqa: E402
from h2d.common.data.omomo_new import load_clip  # noqa: E402
from h2d.common.data.omomo_objects import load_object  # noqa: E402
from h2d.common.runinfo import ProvenanceError, add_run_args, start_run  # noqa: E402
from h2d.common.viz_hoi import example_figure, example_video  # noqa: E402
from h2d.paths import data_path  # noqa: E402

CHECK_CONTACT_M = 0.05      # per object: median distance of the closest flagged hand body to the surface
CHECK_FLOOR_M = 0.03        # per object: |median lowest point height at the clip start|
STATE_COLORS = {"lifted": "#2a78d6", "tilted": "#eb6834", "slid": "#1baf7a", "turned": "#eda100", "still": "#b5b4ad"}
HAND_COLORS = {"left": "#2a78d6", "right": "#eb6834", "both": "#1baf7a", "mixed": "#b5b4ad"}
INK, GRID = "#2b2b2b", "#e4e3dd"
GROUP_COLS = ["palm", "fingers", "forearm", "upper_arm", "collar", "torso", "head_neck", "pelvis", "thigh", "shin",
              "foot"]


def _round(v):
    if isinstance(v, float):
        return None if math.isnan(v) else round(v, 4)
    return v


def clean(v):
    """JSON-safe copy: NaN -> None, numpy scalars -> Python."""
    if isinstance(v, dict):
        return {k: clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if isinstance(v, (np.floating, float)):
        return None if math.isnan(float(v)) else float(v)
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.bool_):
        return bool(v)
    return v


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows([{k: _round(v) for k, v in r.items()} for r in rows])


def nanmed(x) -> float:
    x = np.asarray([v for v in x if v is not None and not (isinstance(v, float) and math.isnan(v))], float)
    return float(np.median(x)) if x.size else float("nan")


def share(rows: list[dict], key: str, labels) -> dict:
    c = Counter(r[key] for r in rows)
    n = max(1, len(rows))
    return {lab: c.get(lab, 0) / n for lab in labels}


def _style(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(labelsize=8, colors=INK)
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)


def stacked(ax, objs, shares: dict, labels, colors, title):
    left = np.zeros(len(objs))
    for lab in labels:
        v = np.array([shares[o][lab] for o in objs])
        ax.barh(objs, v, left=left, color=colors[lab], edgecolor="white", linewidth=1.0, label=lab, height=0.75)
        left += v
    ax.set_xlim(0, 1)
    ax.invert_yaxis()
    ax.set_title(title, fontsize=9, loc="left", color=INK)
    ax.legend(fontsize=7, ncol=len(labels), loc="lower center", bbox_to_anchor=(0.5, -0.16), frameon=False)
    _style(ax)


def main() -> int:
    ap = argparse.ArgumentParser()
    add_run_args(ap)
    ap.add_argument("--root", default=None)
    ap.add_argument("--limit", type=int, default=0, help="only the first N files (debug)")
    ap.add_argument("--objects", nargs="*", default=None, help="only these objects (debug)")
    ap.add_argument("--mesh-check-frames", type=int, default=10)
    ap.add_argument("--examples-per-object", type=int, default=2)
    ap.add_argument("--videos", action="store_true", help="also write an MP4 per example (needs ffmpeg)")
    args = ap.parse_args()
    try:
        prov = start_run(args.run_id, needs=("hoi_retarget",), configs=("data.yaml", "external.yaml"),
                         allow_dirty=args.allow_dirty, allow_external_mismatch=args.allow_external_mismatch)
    except ProvenanceError as e:
        print(f"[refused] {e}", file=sys.stderr)
        return 2
    root = Path(args.root).expanduser() if args.root else data_path("omomo_new")
    out = Path(args.out or f"outputs/{args.run_id}")
    (out / "examples").mkdir(parents=True, exist_ok=True)

    files = sorted(root.rglob("*.pt"))
    if args.objects:
        files = [f for f in files if any(f"_{o}_" in f.stem for o in args.objects)]
    if args.limit:
        files = files[: args.limit]
    clips, segs, errors = [], [], []
    checks = {"contact_hand_min_m": {}, "free_hand_min_m": {}, "contact_body_min_m": {}}
    t0 = time.time()
    for i, f in enumerate(files):
        try:
            c = load_clip(f)
            d = describe_clip(c, load_object(c.obj), DEFAULTS, args.mesh_check_frames)
        except Exception as e:  # noqa: BLE001 - report and continue
            errors.append({"file": f.name, "error": f"{type(e).__name__}: {str(e)[:300]}"})
            continue
        clips.append(d["clip"])
        segs += d["segments"]
        for k, v in d["check"].items():
            checks[k].setdefault(c.obj, []).extend(v)
        if (i + 1) % 250 == 0:
            print(f"  {i + 1}/{len(files)}  ({time.time() - t0:.0f} s)", flush=True)
    if not clips:
        print(f"no clip could be processed from {root}; first errors: {errors[:3]}", file=sys.stderr)
        return 1
    write_csv(out / "clips.csv", clips)
    write_csv(out / "segments.csv", segs)

    # ------------------------------------------------------------------ per object
    objs = [o for o, _ in Counter(r["object"] for r in clips).most_common()]
    per_obj, crosstab = [], {}
    for o in objs:
        C = [r for r in clips if r["object"] == o]
        S = [r for r in segs if r["object"] == o]
        mesh = load_object(o)
        hs, ss = share(S, "hands", HAND_LABELS), share(S, "object_state", OBJECT_STATES)
        w = np.array([r["duration_s"] for r in S]) if S else np.zeros(0)
        grp = {}
        for g in GROUP_COLS:
            key = {"palm": "frac_palm", "fingers": "frac_fingers"}.get(g, f"frac_{g}")
            grp[g] = float(np.average([r[key] for r in S], weights=w)) if S else float("nan")
        combos = Counter((r["hands"], r["object_state"], r["human"]) for r in S)
        crosstab[o] = [{"hands": h, "object_state": st, "human": hu, "share": n / max(1, len(S))}
                       for (h, st, hu), n in combos.most_common(4)]
        per_obj.append({
            "object": o, "clips": len(C), "subjects": len({r["subject"] for r in C}),
            "size_m": "x".join(f"{v:.2f}" for v in mesh.extents),
            "clip_s_median": nanmed([r["duration_s"] for r in C]),
            "segments_per_clip": len(S) / len(C), "contact_coverage": nanmed([r["contact_coverage"] for r in C]),
            "segment_s_median": nanmed([r["duration_s"] for r in S]),
            **{f"hands_{k}": v for k, v in hs.items()}, **{f"state_{k}": v for k, v in ss.items()},
            "walk_share": share(S, "human", ("walk",))["walk"],
            "body_share": float(np.mean([r["frac_body"] > 0.2 for r in S])) if S else float("nan"),
            "contact_z_median_m": nanmed([r["contact_z_median_m"] for r in S]),
            "obj_clear_max_median_m": nanmed([r["obj_clear_max_m"] for r in S]),
            "obj_disp_xy_median_m": nanmed([r["obj_disp_xy_m"] for r in S]),
            "root_disp_xy_median_m": nanmed([r["root_disp_xy_m"] for r in S]),
            **{f"group_{g}": v for g, v in grp.items()},
            "check_contact_hand_median_m": nanmed(checks["contact_hand_min_m"].get(o, [])),
            "check_free_hand_median_m": nanmed(checks["free_hand_min_m"].get(o, [])),
            "check_contact_body_median_m": nanmed(checks["contact_body_min_m"].get(o, [])),
            "floor_lowest_z_start_median_m": nanmed([r["obj_lowest_z_start_m"] for r in C]),
            "toe_z_min_median_m": nanmed([r["toe_z_min_m"] for r in C]),
        })
    write_csv(out / "per_object.csv", per_obj)
    P = {r["object"]: r for r in per_obj}

    # ------------------------------------------------------------------ checks
    all_contact = [v for vs in checks["contact_hand_min_m"].values() for v in vs]
    all_free = [v for vs in checks["free_hand_min_m"].values() for v in vs]
    bad_mesh = [o for o in objs if not (P[o]["check_contact_hand_median_m"] <= CHECK_CONTACT_M)]
    bad_floor = [o for o in objs if not (abs(P[o]["floor_lowest_z_start_median_m"]) <= CHECK_FLOOR_M)]
    check_res = {
        "all_files_processed": {"pass": not errors, "n_errors": len(errors)},
        "mesh_pose_convention": {
            "pass": not bad_mesh, "threshold_m": CHECK_CONTACT_M, "failing_objects": bad_mesh,
            "median_contact_hand_m": nanmed(all_contact), "median_free_hand_m": nanmed(all_free),
            "n_contact": len(all_contact), "n_free": len(all_free)},
        "contact_labels_informative": {
            "pass": bool(nanmed(all_contact) < 0.5 * nanmed(all_free)),
            "rule": "median(contact) < 0.5 * median(free hand)"},
        "floor_at_zero": {"pass": not bad_floor, "threshold_m": CHECK_FLOOR_M, "failing_objects": bad_floor,
                          "median_lowest_z_start_m": nanmed([r["obj_lowest_z_start_m"] for r in clips]),
                          "median_toe_z_min_m": nanmed([r["toe_z_min_m"] for r in clips])},
    }
    passed = all(v["pass"] for v in check_res.values())

    # ------------------------------------------------------------------ examples
    examples = []
    for o in objs:
        C = [r for r in clips if r["object"] == o and r["n_segments"] > 0]
        combos = Counter((r["longest_hands"], r["longest_state"]) for r in C).most_common(args.examples_per_object)
        for rank, ((h, st), n) in enumerate(combos):
            G = [r for r in C if (r["longest_hands"], r["longest_state"]) == (h, st)]
            med = np.median([r["duration_s"] for r in G])
            pick = min(G, key=lambda r: (abs(r["duration_s"] - med), r["name"]))
            examples.append({"object": o, "rank": rank + 1, "hands": h, "object_state": st,
                             "group_share": n / len(C), "name": pick["name"]})
    vid_ok = None
    for ex in examples:
        f = next(p for p in files if p.stem == ex["name"])
        c = load_clip(f)
        rows = [r for r in segs if r["name"] == c.name]
        example_figure(c, load_object(c.obj), rows, out / "examples" / f"{c.name}.png")
        if args.videos:
            (out / "videos").mkdir(exist_ok=True)
            vid_ok = example_video(c, load_object(c.obj), rows, out / "videos" / f"{c.name}.mp4")
            if not vid_ok:
                print("[warn] ffmpeg writer not available: no videos", file=sys.stderr)
                args.videos = False

    # ------------------------------------------------------------------ figures
    fig, ax = plt.subplots(2, 2, figsize=(15, 9.5))
    ax[0, 0].barh(objs, [P[o]["clips"] for o in objs], color="#2a78d6", height=0.7)
    for i, o in enumerate(objs):
        ax[0, 0].text(P[o]["clips"] + 0.02 * max(P[x]["clips"] for x in objs), i, f"{P[o]['clips']} clips · {P[o]['subjects']} subj · {P[o]['size_m']} m",
                      va="center", fontsize=7, color=INK)
    ax[0, 0].invert_yaxis()
    ax[0, 0].set_xlim(0, 2.0 * max(P[o]["clips"] for o in objs))
    ax[0, 0].set_title("clips per object (with object bounding box, sorted sides)", fontsize=9, loc="left")
    _style(ax[0, 0])
    stacked(ax[0, 1], objs, {o: {k: P[o][f"state_{k}"] for k in OBJECT_STATES} for o in objs}, OBJECT_STATES,
            STATE_COLORS, "what happens to the object during a hand-contact segment (share of segments)")
    stacked(ax[1, 0], objs, {o: {k: P[o][f"hands_{k}"] for k in HAND_LABELS} for o in objs}, HAND_LABELS,
            HAND_COLORS, "which hands are used (share of segments)")
    y = np.arange(len(objs))
    ax[1, 1].barh(y - 0.2, [P[o]["walk_share"] for o in objs], height=0.38, color="#2a78d6",
                  label=f"human walks (root moves ≥ {DEFAULTS['walk_m']} m)")
    ax[1, 1].barh(y + 0.2, [P[o]["body_share"] for o in objs], height=0.38, color="#eb6834",
                  label="other body parts touch (> 20 % of frames)")
    ax[1, 1].set_yticks(y, objs)
    ax[1, 1].invert_yaxis()
    ax[1, 1].set_xlim(0, 1)
    ax[1, 1].set_title("how often the human walks / other body parts touch (share of segments)", fontsize=9,
                       loc="left")
    ax[1, 1].legend(fontsize=7, loc="lower center", bbox_to_anchor=(0.5, -0.16), ncol=2, frameon=False)
    _style(ax[1, 1])
    fig.suptitle(f"OMOMO_new: {len(clips)} clips, {len(segs)} hand-contact segments", fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(out / "overview.png", dpi=90)
    plt.close(fig)

    metrics = [("duration_s", "segment duration [s]"), ("obj_clear_max_m", "object max lowest-point height [m]"),
               ("obj_disp_xy_m", "object horizontal displacement [m]"), ("obj_tilt_max_deg", "object max tilt [deg]"),
               ("root_disp_xy_m", "human root horizontal displacement [m]"),
               ("contact_z_median_m", "height of hand contact [m]")]
    fig, ax = plt.subplots(2, 3, figsize=(16, 9), sharey=True)
    for a, (k, lab) in zip(ax.ravel(), metrics):
        data = [[r[k] for r in segs if r["object"] == o and not math.isnan(r[k])] or [np.nan] for o in objs]
        a.boxplot(data, vert=False, showfliers=False, widths=0.6,
                  medianprops={"color": "#eb6834", "lw": 2}, boxprops={"color": "#2a78d6"},
                  whiskerprops={"color": "#2a78d6"}, capprops={"color": "#2a78d6"})
        a.set_yticks(range(1, len(objs) + 1), objs)
        a.set_title(lab, fontsize=9, loc="left")
        _style(a)
    ax[0, 0].invert_yaxis()
    fig.suptitle("per hand-contact segment, by object (box = quartiles, whiskers = 1.5 IQR, outliers hidden)",
                 fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(out / "distributions.png", dpi=90)
    plt.close(fig)

    M = np.array([[P[o][f"group_{g}"] for g in GROUP_COLS] for o in objs])
    fig, a = plt.subplots(figsize=(12, 6.5))
    im = a.imshow(M, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    a.set_xticks(range(len(GROUP_COLS)), GROUP_COLS, rotation=30, ha="right", fontsize=8)
    a.set_yticks(range(len(objs)), objs, fontsize=8)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            if not math.isnan(M[i, j]):
                a.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=7,
                       color="white" if M[i, j] > 0.55 else INK)
    fig.colorbar(im, ax=a, fraction=0.03, label="share of segment frames")
    a.set_title("which body parts touch the object during hand-contact segments (duration-weighted)", fontsize=9,
                loc="left")
    fig.tight_layout()
    fig.savefig(out / "bodies.png", dpi=90)
    plt.close(fig)

    fig, ax = plt.subplots(1, 3, figsize=(16, 4.5))
    bins = np.logspace(-3.5, 0.5, 50)
    ax[0].hist(np.clip(all_contact, 10 ** -3.5, None), bins=bins, color="#2a78d6", alpha=0.8,
               label="closest flagged body of a hand in contact")
    ax[0].hist(np.clip(all_free, 10 ** -3.5, None), bins=bins, color="#eb6834", alpha=0.6,
               label="closest body of the other hand (not in contact)")
    ax[0].set_xscale("log")
    ax[0].set_xlabel("distance to the transformed object surface [m]", fontsize=8)
    ax[0].legend(fontsize=7, frameon=False)
    ax[0].set_title("mesh / pose convention and contact labels", fontsize=9, loc="left")
    ax[1].barh(objs, [P[o]["check_contact_hand_median_m"] for o in objs], color="#2a78d6", height=0.7)
    ax[1].axvline(CHECK_CONTACT_M, color=INK, lw=1, ls="--")
    ax[1].text(CHECK_CONTACT_M, 0.02, f" threshold {CHECK_CONTACT_M} m", fontsize=7, color=INK,
               transform=ax[1].get_xaxis_transform())
    ax[1].invert_yaxis()
    ax[1].set_title("median distance of the closest flagged hand body, per object [m]", fontsize=9, loc="left")
    zb = np.linspace(-10, 20, 121)
    ax[2].hist(np.clip([100 * r["obj_lowest_z_start_m"] for r in clips], -10, 20), bins=zb, color="#2a78d6",
               alpha=0.8, label="object lowest point at clip start")
    ax[2].hist(np.clip([100 * r["toe_z_min_m"] for r in clips], -10, 20), bins=zb, color="#eb6834", alpha=0.6,
               label="lowest toe joint over the clip")
    ax[2].set_xlabel("height [cm] (clipped to [-10, 20])", fontsize=8)
    ax[2].legend(fontsize=7, frameon=False)
    ax[2].set_title("floor at z = 0?", fontsize=9, loc="left")
    for a in ax:
        _style(a)
    fig.tight_layout()
    fig.savefig(out / "checks.png", dpi=90)
    plt.close(fig)

    # ------------------------------------------------------------------ summary + report
    summary = {
        "provenance": prov, "root": str(root), "n_files": len(files), "n_clips": len(clips), "n_segments": len(segs),
        "errors": errors[:50], "params": DEFAULTS, "checks": check_res, "pass": passed,
        "totals": {"hands": share(segs, "hands", HAND_LABELS), "object_state": share(segs, "object_state", OBJECT_STATES),
                   "walk_share": share(segs, "human", ("walk",))["walk"],
                   "clips_without_segments": sum(r["n_segments"] == 0 for r in clips),
                   "total_hours": sum(r["duration_s"] for r in clips) / 3600},
        "per_object": per_obj, "crosstab": crosstab, "examples": examples, "videos": bool(args.videos),
    }
    (out / "summary.json").write_text(json.dumps(clean(summary), indent=2), encoding="utf-8")

    pct = lambda v: "–" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{100 * v:.0f}"  # noqa: E731
    lines = [
        "# OMOMO_new data profile",
        "",
        f"Run `{prov['run_id']}` · code `{prov['git']['describe']}` (dirty={prov['git']['dirty']}) · "
        f"{len(clips)}/{len(files)} clips · {len(segs)} hand-contact segments · "
        f"{summary['totals']['total_hours']:.2f} h · {summary['totals']['clips_without_segments']} clips without hand contact",
        "",
        "## Checks",
        "",
        "| check | value | pass |",
        "|---|---|---|",
        f"| all files processed | {len(errors)} errors | {check_res['all_files_processed']['pass']} |",
        f"| mesh/pose convention: median distance of closest flagged hand body ≤ {CHECK_CONTACT_M} m per object | "
        f"overall {check_res['mesh_pose_convention']['median_contact_hand_m']:.4f} m; failing {bad_mesh} | "
        f"{check_res['mesh_pose_convention']['pass']} |",
        f"| contact labels informative | contact {nanmed(all_contact):.3f} m vs free hand {nanmed(all_free):.3f} m | "
        f"{check_res['contact_labels_informative']['pass']} |",
        f"| floor at z = 0: abs(median object lowest point at start) ≤ {CHECK_FLOOR_M} m per object | overall "
        f"{check_res['floor_at_zero']['median_lowest_z_start_m']:+.4f} m, toe min "
        f"{check_res['floor_at_zero']['median_toe_z_min_m']:+.3f} m; failing {bad_floor} | {check_res['floor_at_zero']['pass']} |",
        "",
        "![checks](checks.png)",
        "",
        "## Overview",
        "",
        "![overview](overview.png)",
        "",
        "Shares of segments, in % (hands: L / R / both / mixed; object: lifted / tilted / slid / turned / still).",
        "",
        "| object | clips | subj | size [m] | clip s | seg/clip | coverage | hands L/R/both/mixed | object li/ti/sl/tu/st | "
        "walk | other body | contact z [m] |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for o in objs:
        r = P[o]
        lines.append(
            f"| {o} | {r['clips']} | {r['subjects']} | {r['size_m']} | {r['clip_s_median']:.1f} | {r['segments_per_clip']:.2f} | "
            f"{pct(r['contact_coverage'])} | " + "/".join(pct(r[f'hands_{k}']) for k in HAND_LABELS) + " | "
            + "/".join(pct(r[f'state_{k}']) for k in OBJECT_STATES) + f" | {pct(r['walk_share'])} | {pct(r['body_share'])} | "
            f"{r['contact_z_median_m']:.2f} |")
    lines += ["", "## Most common segment kinds per object (hands / object / human, share of the object's segments)", ""]
    for o in objs:
        lines.append(f"* **{o}**: " + "; ".join(f"{c['hands']} / {c['object_state']} / {c['human']} {pct(c['share'])} %"
                                               for c in crosstab[o]))
    lines += ["", "## Distributions and body parts", "", "![distributions](distributions.png)", "",
              "![bodies](bodies.png)", "", "## Examples", "",
              "Per object: most common and second most common (hands, object) of the clip's longest segment; "
              "the clip with the median duration in that group.", ""]
    for ex in examples:
        lines += [f"### {ex['object']} #{ex['rank']}: {ex['hands']} / {ex['object_state']} "
                  f"({pct(ex['group_share'])} % of its clips) — `{ex['name']}`", "",
                  f"![{ex['name']}](examples/{ex['name']}.png)", ""]
    lines += ["## Label thresholds", "", "```", json.dumps(DEFAULTS), "```", ""]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:16]))
    print(f"done in {time.time() - t0:.0f} s; pass={passed}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
