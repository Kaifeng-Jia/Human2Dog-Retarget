#!/usr/bin/env python
"""M0: human gait in the input clips and the dog's natural rhythm at the same speed (fullopt spec §6.1-6.3, §10).

Reads ``HOIClip`` files (``export_hoi.py``) and reports the dev and held-out splits apart (spec v0.2 §8.5). Per clip:
foot contacts, touchdowns, stand / shuffle / walk segments, leg length h_h; inside the task window: how much of it is
walk, shuffle or stand. Per walk segment: speed, measured step frequency, the Alexander prediction for the human,
and the dog's natural footfalls per human step at that speed with the lock deviation (the frequency change a
whole-number ratio needs). The B2 hip height h_d comes from the model.

Checks of the input and the measurement (all must hold, every split): every clip loads and passes ``hoi.validate``;
every clip has a walk or shuffle segment; no two touchdowns closer than 0.2 s (a double detection; quick real steps
around an object are 0.24 s apart and more); touchdowns alternate feet (>= 0.8 of consecutive pairs); h_h within
0.70-1.05 m and, as the bones are fixed per person, within 3 cm across one subject's clips. Step frequencies are
data, not checked: around objects people take short quick steps far from steady walking.

Writes outputs/<run-id>/{summary.json, report.md, segments.csv, figures/{freq_speed,timelines}.png}.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from h2d.common.data.omomo_new import intervals  # noqa: E402
from h2d.common.robot import B2Z1Robot  # noqa: E402
from h2d.common.runinfo import ProvenanceError, add_run_args, start_run  # noqa: E402
from h2d.common.tables import clean, write_csv  # noqa: E402
from h2d.fullopt import gait, hoi, signals  # noqa: E402
from h2d.paths import load_config  # noqa: E402

LIMITS = {"min_step_gap_s": 0.2, "alternation_min": 0.8, "leg_m": (0.70, 1.05), "leg_spread_subject_m": 0.03}
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
FOOT = {"L": "#2a78d6", "R": "#eb6834"}
SPLIT = {"dev": "#2a78d6", "heldout": "#eb6834"}


def analyse(c: hoi.HOIClip, cfg: dict, h_d: float) -> tuple[dict, list[dict]]:
    hc, m = cfg["human"], c.meta
    con = signals.foot_contacts(c, hc)
    ev = signals.touchdowns(con)
    segs = signals.segments(c, ev, hc)
    h_h = signals.leg_length(c, con)
    w0, w1 = m.get("window", [0, c.n])
    kind = np.full(c.n, "stand", dtype=object)
    for s in segs:
        kind[s["start"]:s["end"]] = s["kind"]
    win = kind[w0:w1]
    key = {"task": m["id"], "split": m["split"], "dataset": m["dataset"], "clip": m["clip"]}
    walks = []
    for s in segs:
        if s["kind"] != "walk":
            continue
        v, f = s["speed_mps"], s["step_hz"]
        g = "trot" if gait.froude(v, h_d) > cfg["dog"]["trot_froude"] else "walk"
        r = float(gait.footfalls_per_step(f, v, h_d, g))
        walks.append({**key, "start": s["start"], "end": s["end"], "duration_s": (s["end"] - s["start"]) / c.fps,
                      "steps": s["steps"], "speed_mps": v, "step_hz": f,
                      "step_hz_alexander": float(2 * gait.stride_hz(v, h_h)),
                      "froude_human": float(gait.froude(v, h_h)),
                      "froude_dog": float(gait.froude(v, h_d)), "dog_gait": g, "dog_per_step": r,
                      "lock_dev": float(gait.lock_deviation(r, 1 if g == "walk" else 2)),
                      "in_window": bool(s["start"] < w1 and s["end"] > w0)})
    row = {**key, "subject": m.get("subject"), "frames": c.n, "fps": c.fps, "window": [w0, w1], "leg_m": h_h,
           "problems": hoi.validate(c), "touchdowns": len(ev), "alternation": signals.alternation(ev),
           "min_step_gap_s": float(np.diff([f for f, _ in ev]).min() / c.fps) if len(ev) > 1 else float("nan"),
           "walk_segments": sum(s["kind"] == "walk" for s in segs),
           "shuffle_segments": sum(s["kind"] == "shuffle" for s in segs),
           "window_steps": sum(w0 <= f < w1 for f, _ in ev),
           **{f"window_{k}_frac": float(np.mean(win == k)) for k in ("walk", "shuffle", "stand")}}
    return {"row": row, "contact": con, "segments": segs}, walks


def lockable(walks: list[dict], deltas) -> dict:
    """Fraction of walk segments (and of walking time) whose lock deviation is within each delta."""
    if not walks:
        return {}
    dev = np.abs([w["lock_dev"] for w in walks])
    dur = np.array([w["duration_s"] for w in walks])
    return {f"{d:.2f}": {"segments": float(np.mean(dev <= d)), "time": float(dur[dev <= d].sum() / dur.sum())}
            for d in deltas}


def checks_of(rows: list[dict], n_errors: int) -> dict:
    by_subject = {}
    for r in rows:
        by_subject.setdefault(r["subject"], []).append(r["leg_m"])
    spread = {s: float(np.ptp(v)) for s, v in by_subject.items() if len(v) > 1}
    lo, hi = LIMITS["leg_m"]
    return {
        "inputs_valid": {"pass": bool(rows) and not n_errors and not any(r["problems"] for r in rows),
                         "n": len(rows), "n_errors": n_errors,
                         "invalid": {r["task"]: r["problems"] for r in rows if r["problems"]}},
        "steps_found": {"pass": all(r["walk_segments"] + r["shuffle_segments"] > 0 for r in rows),
                        "without": [r["task"] for r in rows if r["walk_segments"] + r["shuffle_segments"] == 0]},
        "no_double_touchdowns": {"pass": all(not r["min_step_gap_s"] < LIMITS["min_step_gap_s"] for r in rows),
                                 "below": [r["task"] for r in rows if r["min_step_gap_s"] < LIMITS["min_step_gap_s"]]},
        "feet_alternate": {"pass": all(not r["alternation"] < LIMITS["alternation_min"] for r in rows),
                           "below": [r["task"] for r in rows if r["alternation"] < LIMITS["alternation_min"]]},
        "leg_length_in_range": {"pass": all(lo <= r["leg_m"] <= hi for r in rows),
                                "outside": [r["task"] for r in rows if not lo <= r["leg_m"] <= hi]},
        "leg_length_same_per_subject": {"pass": all(v <= LIMITS["leg_spread_subject_m"] for v in spread.values()),
                                        "spread_m": spread},
    }


def aggregate(rows: list[dict], walks: list[dict], h_d: float, deltas) -> dict:
    h_h = float(np.median([r["leg_m"] for r in rows])) if rows else float("nan")
    return {"clips": len(rows), "leg_m_median": h_h, "ratio_constant": (h_h / h_d) ** 0.7,
            "walk_segments": len(walks), "walking_s": float(sum(w["duration_s"] for w in walks)),
            **{f"{k}_median": float(np.median([w[k] for w in walks])) if walks else float("nan")
               for k in ("speed_mps", "step_hz", "dog_per_step", "lock_dev")},
            "dog_trot_segments": sum(w["dog_gait"] == "trot" for w in walks), "lockable": lockable(walks, deltas),
            "lockable_in_windows": lockable([w for w in walks if w["in_window"]], deltas)}


def figures(out: Path, per: list[dict], walks: list[dict], h_h: float, h_d: float) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                         "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": SURF, "axes.facecolor": SURF})
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6), constrained_layout=True)
    v = np.linspace(0.1, 1.6, 100)
    ax[0].plot(v, 2 * gait.stride_hz(v, h_h), color=INK2, lw=2, label=f"Alexander, h = {h_h:.2f} m")
    for n in (1, 2, 3, 4):                               # lockable with delta = 0.10 (light) and 0.05 (dark)
        for d, a in ((0.10, 0.12), (0.05, 0.25)):
            ax[1].axhspan(n / (1 + d), n / (1 - d), color=INK2, alpha=a, lw=0)
        ax[1].axhline(n, color=INK2, lw=0.8)
    for split, col in SPLIT.items():
        ws = [w for w in walks if w["split"] == split]
        if not ws:
            continue
        sp, sz = [w["speed_mps"] for w in ws], [12 + 6 * w["duration_s"] for w in ws]
        ax[0].scatter(sp, [w["step_hz"] for w in ws], s=sz, color=col, edgecolor=SURF, linewidth=1, zorder=3,
                      label=f"{split} walk segments")
        ax[1].scatter(sp, [w["dog_per_step"] for w in ws], s=sz, color=col, edgecolor=SURF, linewidth=1, zorder=3,
                      label=split)
    ax[0].set(xlabel="speed [m/s]", ylabel="human steps per second", title="Human step frequency")
    ax[1].set(xlabel="speed [m/s]", ylabel="dog footfalls per human step", ylim=(0.8, 4.5),
              title=f"Dog footfalls per human step, h_d = {h_d:.2f} m")
    for a in ax:
        a.grid(color=GRID, lw=0.6)
        a.set_xlim(0, 1.7)
        a.legend(frameon=False)
    fig.savefig(out / "freq_speed.png", dpi=130)
    plt.close(fig)
    if not per:
        return
    fig, axs = plt.subplots(len(per), 1, figsize=(10, 0.55 * len(per) + 0.6), squeeze=False, constrained_layout=True)
    for a, p in zip(axs[:, 0], per):
        r = p["row"]
        fps = r["fps"]
        for s in p["segments"]:
            a.axvspan(s["start"] / fps, s["end"] / fps, color=INK2, alpha=0.28 if s["kind"] == "walk" else 0.12, lw=0)
        for j, side in enumerate("LR"):
            a.broken_barh([(s / fps, (e - s) / fps) for s, e in intervals(p["contact"][:, j])], (1 - j + 0.15, 0.7),
                          color=FOOT[side])
        for w in r["window"]:
            a.axvline(w / fps, color=INK, lw=1)
        a.set_yticks([0.5, 1.5], ["R", "L"])
        a.set_xlim(0, r["frames"] / fps)
        a.set_ylabel(f"{r['split'][0]} {r['task'][:14]}", rotation=0, ha="right", va="center", fontsize=8)
        a.tick_params(length=0)
        for k in a.spines.values():
            k.set_visible(False)
    axs[0, 0].set_title("Foot contacts (L blue, R orange); grey: walk (dark), shuffle (light); task window between "
                        "the black lines; d = dev, h = held-out", fontsize=9, color=INK)
    axs[-1, 0].set_xlabel("time [s]")
    fig.savefig(out / "timelines.png", dpi=110)
    plt.close(fig)


def report(prov, passed, checks, dog, agg, rows, walks) -> list[str]:
    f = lambda x, nd=2: "–" if x is None or x != x else f"{x:.{nd}f}"  # noqa: E731
    L = ["# M0: human gait and the dog's natural rhythm (fullopt spec §6.1-6.3, §8.5)", "",
         f"Run `{prov['run_id']}` · code `{prov['git']['describe']}` (dirty={prov['git']['dirty']}) · "
         f"{len(rows)} clips · **{'PASS' if passed else 'FAIL'}**", "",
         "| check | " + " | ".join(checks) + " |", "|---|" + "---|" * len(checks),
         *[f"| {k} | " + " | ".join(str(checks[s][k]["pass"]) for s in checks) + " |"
           for k in (next(iter(checks.values())) if checks else [])],
         "", f"B2 (home pose): hip height h_d {f(dog['hip_height_m'])} m, thigh {f(dog['thigh_m'])} m, calf "
         f"{f(dog['calf_m'])} m, longest walk stride {f(dog['max_stride_walk_m'])} m.", "",
         "| split | clips | h_h median [m] | walk segments (s) | speed [m/s] | step Hz | dog per step | lock dev | "
         "lockable at δ " + " / ".join(next((a["lockable"] for a in agg.values() if a["lockable"]), {})) + " |",
         "|---|---|---|---|---|---|---|---|---|",
         *[f"| {s} | {a['clips']} | {f(a['leg_m_median'])} | {a['walk_segments']} ({f(a['walking_s'], 1)}) | "
           f"{f(a['speed_mps_median'])} | {f(a['step_hz_median'])} | {f(a['dog_per_step_median'])} | "
           f"{f(a['lock_dev_median'], 3)} | " + " / ".join(f(v["segments"]) for v in a["lockable"].values()) + " |"
           for s, a in agg.items()], "",
         "| split | task | dataset / clip | h_h [m] | touchdowns | shortest gap [s] | alternation | walk / shuffle | "
         "window: steps, walk / shuffle / stand | problems |", "|---|---|---|---|---|---|---|---|---|---|",
         *[f"| {r['split']} | {r['task']} | {r['dataset']} / {r['clip']} | {f(r['leg_m'])} | {r['touchdowns']} | "
           f"{f(r['min_step_gap_s'])} | {f(r['alternation'])} | {r['walk_segments']} / {r['shuffle_segments']} | "
           f"{r['window_steps']}, {f(r['window_walk_frac'])} / {f(r['window_shuffle_frac'])} / "
           f"{f(r['window_stand_frac'])} | {'; '.join(r['problems'])} |" for r in rows], "",
         "| split | task | frames | steps | speed [m/s] | step Hz (Alexander) | dog gait | dog per step | lock dev |",
         "|---|---|---|---|---|---|---|---|---|",
         *[f"| {w['split']} | {w['task']} | {w['start']}–{w['end']} | {w['steps']} | {f(w['speed_mps'])} | "
           f"{f(w['step_hz'])} ({f(w['step_hz_alexander'])}) | {w['dog_gait']} | {f(w['dog_per_step'])} | "
           f"{f(w['lock_dev'], 3)} |" for w in walks], "",
         "Right panel: grey bands are lockable at δ = 0.05 (dark) and 0.10 (light).", "",
         "![](figures/freq_speed.png)", "", "![](figures/timelines.png)"]
    return L


def main() -> int:
    ap = argparse.ArgumentParser()
    add_run_args(ap)
    ap.add_argument("--clips", required=True, help="folder of HOIClip .npz files (export_hoi.py)")
    args = ap.parse_args()
    try:
        prov = start_run(args.run_id, needs=("xmorph",), configs=("external.yaml", "b2z1.yaml", "fullopt/gait.yaml"),
                         allow_dirty=args.allow_dirty, allow_external_mismatch=args.allow_external_mismatch)
    except ProvenanceError as e:
        print(f"[refused] {e}", file=sys.stderr)
        return 2
    t0 = time.time()
    cfg = load_config("fullopt/gait.yaml")
    out = Path(args.out or f"outputs/{args.run_id}")
    (out / "figures").mkdir(parents=True, exist_ok=True)
    dog = gait.hip_height(B2Z1Robot())
    h_d = dog["hip_height_m"]
    dog["max_stride_walk_m"] = gait.max_stride_m(dog["thigh_m"] + dog["calf_m"], h_d - dog["foot_radius_m"],
                                                 cfg["dog"]["walk"]["duty"])
    per, walks, errors = [], [], []
    for path in sorted(Path(args.clips).glob("*.npz")):
        try:
            p, w = analyse(hoi.HOIClip.load(path), cfg, h_d)
            per.append(p)
            walks += w
            print(f"  {path.stem}: {len(w)} walk segments, h_h {p['row']['leg_m']:.2f} m", flush=True)
        except Exception as e:  # noqa: BLE001 - report and continue
            errors.append({"file": path.name, "error": f"{type(e).__name__}: {str(e)[:300]}"})
            print(f"  {path.stem}: error {errors[-1]['error']}", flush=True)
    per.sort(key=lambda p: (p["row"]["split"], p["row"]["task"]))
    rows = [p["row"] for p in per]
    splits = sorted({r["split"] for r in rows})
    checks = {s: checks_of([r for r in rows if r["split"] == s], len(errors)) for s in splits}
    passed = bool(rows) and all(c["pass"] for cs in checks.values() for c in cs.values())
    deltas = cfg["dog"]["deltas"]
    agg = {s: aggregate([r for r in rows if r["split"] == s], [w for w in walks if w["split"] == s], h_d, deltas)
           for s in splits}
    figures(out / "figures", per, walks, float(np.median([r["leg_m"] for r in rows])) if rows else 0.9, h_d)
    write_csv(out / "segments.csv", walks)
    summary = {"provenance": prov, "limits": LIMITS, "checks": checks, "pass": passed, "dog": dog, "aggregate": agg,
               "clips": rows, "walk_segments": walks, "errors": errors, "elapsed_s": time.time() - t0}
    (out / "summary.json").write_text(json.dumps(clean(summary), indent=2), encoding="utf-8")
    L = report(prov, passed, checks, dog, agg, rows, walks)
    if errors:
        L += ["", "Errors:", *[f"- {e['file']}: {e['error']}" for e in errors]]
    (out / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"pass={passed}  clips={len(rows)}  walk segments={len(walks)}  -> {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
