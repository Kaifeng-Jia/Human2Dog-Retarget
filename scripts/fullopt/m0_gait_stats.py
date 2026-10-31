#!/usr/bin/env python
"""M0: human gait on the solvable tasks and the dog's natural rhythm at the same speed (fullopt spec §6.1-6.3, §10).

Per task, on the whole clip: foot contacts, touchdowns, stand / shuffle / walk segments, leg length h_h; inside
the task window: how much of it is walk, shuffle or stand. Per walk segment: speed, measured step frequency, the
Alexander prediction for the human, and the dog's natural footfalls per human step at that speed with the lock
deviation (the frequency change a whole-number ratio needs). The B2 hip height h_d comes from the model.

Checks (all must hold): every clip loads; every clip has a walk or shuffle segment; walk step frequency within
0.8-2.6 Hz; touchdowns alternate feet (>= 0.8 of consecutive pairs); h_h within 0.70-1.05 m.

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
from h2d.common.data.omomo_new import intervals, load_clip  # noqa: E402
from h2d.common.data.tasks import load_task, solvable_task_ids  # noqa: E402
from h2d.common.robot import B2Z1Robot  # noqa: E402
from h2d.common.runinfo import ProvenanceError, add_run_args, start_run  # noqa: E402
from h2d.common.tables import clean, write_csv  # noqa: E402
from h2d.fullopt import gait, signals  # noqa: E402
from h2d.paths import data_path, load_config  # noqa: E402

LIMITS = {"step_hz": (0.8, 2.6), "alternation_min": 0.8, "leg_m": (0.70, 1.05)}
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
FOOT = {"L": "#2a78d6", "R": "#eb6834"}


def analyse(clip, task: dict, cfg: dict, h_d: float) -> tuple[dict, list[dict]]:
    fps, hc = clip.fps, cfg["human"]
    con = signals.foot_contacts(clip.body_pos, fps, hc)
    ev = signals.touchdowns(con)
    segs = signals.segments(clip.body_pos, fps, ev, hc)
    h_h = signals.leg_length(clip.body_pos, con, fps)
    w0, w1 = task["window"]
    kind = np.full(clip.n, "stand", dtype=object)
    for s in segs:
        kind[s["start"]:s["end"]] = s["kind"]
    win = kind[w0:w1]
    walks = []
    for s in segs:
        if s["kind"] != "walk":
            continue
        v, f = s["speed_mps"], s["step_hz"]
        g = "trot" if gait.froude(v, h_d) > cfg["dog"]["trot_froude"] else "walk"
        r = float(gait.footfalls_per_step(f, v, h_d, g))
        walks.append({"task": task["id"], "clip": clip.name, "start": s["start"], "end": s["end"],
                      "duration_s": (s["end"] - s["start"]) / fps, "steps": s["steps"], "speed_mps": v,
                      "step_hz": f, "step_hz_alexander": float(2 * gait.stride_hz(v, h_h)),
                      "froude_human": float(gait.froude(v, h_h)), "froude_dog": float(gait.froude(v, h_d)),
                      "dog_gait": g, "dog_per_step": r,
                      "lock_dev": float(gait.lock_deviation(r, 1 if g == "walk" else 2)),
                      "in_window": bool(s["start"] < w1 and s["end"] > w0)})
    row = {"task": task["id"], "clip": clip.name, "frames": clip.n, "fps": fps, "window": [w0, w1], "leg_m": h_h,
           "touchdowns": len(ev), "alternation": signals.alternation(ev),
           "walk_segments": sum(s["kind"] == "walk" for s in segs),
           "shuffle_segments": sum(s["kind"] == "shuffle" for s in segs),
           "window_steps": sum(w0 <= f < w1 for f, _ in ev),
           **{f"window_{k}_frac": float(np.mean(win == k)) for k in ("walk", "shuffle", "stand")}}
    return {"row": row, "contact": con, "events": ev, "segments": segs}, walks


def lockable(walks: list[dict], deltas) -> dict:
    """Fraction of walk segments (and of walking time) whose lock deviation is within each delta."""
    if not walks:
        return {}
    dev = np.abs([w["lock_dev"] for w in walks])
    dur = np.array([w["duration_s"] for w in walks])
    return {f"{d:.2f}": {"segments": float(np.mean(dev <= d)), "time": float(dur[dev <= d].sum() / dur.sum())}
            for d in deltas}


def figures(out: Path, per: list[dict], walks: list[dict], h_h: float, h_d: float, deltas) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                         "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": SURF, "axes.facecolor": SURF})
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6), constrained_layout=True)
    v = np.linspace(0.1, 1.6, 100)
    sp = np.array([w["speed_mps"] for w in walks]) if walks else np.zeros(0)
    ax[0].plot(v, 2 * gait.stride_hz(v, h_h), color=INK2, lw=2, label=f"Alexander, h = {h_h:.2f} m")
    if walks:
        ax[0].scatter(sp, [w["step_hz"] for w in walks], s=[12 + 6 * w["duration_s"] for w in walks],
                      color=FOOT["L"], edgecolor=SURF, linewidth=1, label="walk segments", zorder=3)
    ax[0].set(xlabel="speed [m/s]", ylabel="human steps per second", title="Human step frequency")
    ax[0].legend(frameon=False)
    for n in (2, 3, 4):                                  # lockable with delta = 0.10 (light) and 0.05 (dark)
        for d, a in ((0.10, 0.12), (0.05, 0.25)):
            ax[1].axhspan(n / (1 + d), n / (1 - d), color=INK2, alpha=a, lw=0)
        ax[1].axhline(n, color=INK2, lw=0.8)
    if walks:
        ax[1].scatter(sp, [w["dog_per_step"] for w in walks], s=[12 + 6 * w["duration_s"] for w in walks],
                      color=FOOT["L"], edgecolor=SURF, linewidth=1, zorder=3)
    ax[1].set(xlabel="speed [m/s]", ylabel="dog footfalls per human step", ylim=(1.5, 4.5),
              title=f"Dog footfalls per human step, h_d = {h_d:.2f} m")
    for a in ax:
        a.grid(color=GRID, lw=0.6)
        a.set_xlim(0, 1.7)
    fig.savefig(out / "freq_speed.png", dpi=130)
    plt.close(fig)
    if not per:
        return
    fig, axs = plt.subplots(len(per), 1, figsize=(10, 0.55 * len(per) + 0.6), sharex=False, squeeze=False,
                            constrained_layout=True)
    for a, p in zip(axs[:, 0], per):
        r = p["row"]
        fps = r["fps"]
        for s in p["segments"]:
            a.axvspan(s["start"] / fps, s["end"] / fps, color=INK2, alpha=0.28 if s["kind"] == "walk" else 0.12, lw=0)
        for j, side in enumerate("LR"):
            a.broken_barh([(s / fps, (e - s) / fps) for s, e in intervals(p["contact"][:, j])], (1 - j + 0.15, 0.7),
                          color=FOOT[side])
        w0, w1 = r["window"]
        a.axvline(w0 / fps, color=INK, lw=1)
        a.axvline(w1 / fps, color=INK, lw=1)
        a.set_yticks([0.5, 1.5], ["R", "L"])
        a.set_xlim(0, r["frames"] / fps)
        a.set_ylabel(r["task"].split("_")[0], rotation=0, ha="right", va="center")
        a.tick_params(length=0)
        for k in a.spines.values():
            k.set_visible(False)
    axs[0, 0].set_title("Foot contacts (L blue, R orange); grey: walk (dark), shuffle (light); task window between "
                        "the black lines", fontsize=9, color=INK)
    axs[-1, 0].set_xlabel("time [s]")
    fig.savefig(out / "timelines.png", dpi=110)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    add_run_args(ap)
    ap.add_argument("--tasks-csv", required=True)
    ap.add_argument("--tasks-dir", required=True)
    ap.add_argument("--max-tasks", type=int, default=12)
    ap.add_argument("--omomo-root", default=None)
    args = ap.parse_args()
    try:
        prov = start_run(args.run_id, needs=("xmorph",), configs=("data.yaml", "external.yaml", "b2z1.yaml",
                                                                  "fullopt/gait.yaml"),
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
    root = Path(args.omomo_root).expanduser() if args.omomo_root else data_path("omomo_new")
    files = {p.stem: p for p in root.rglob("*.pt")}
    per, walks, errors = [], [], []
    for tid in solvable_task_ids(args.tasks_csv, args.max_tasks):
        try:
            task = {**load_task(Path(args.tasks_dir) / f"{tid}.npz"), "id": tid}
            p, w = analyse(load_clip(files[task["clip"]]), task, cfg, h_d)
            per.append(p)
            walks += w
            print(f"  {tid}: {len(w)} walk segments, h_h {p['row']['leg_m']:.2f} m", flush=True)
        except Exception as e:  # noqa: BLE001 - report and continue
            errors.append({"id": tid, "error": f"{type(e).__name__}: {str(e)[:300]}"})
            print(f"  {tid}: error {errors[-1]['error']}", flush=True)
    rows = [p["row"] for p in per]
    h_h = float(np.median([r["leg_m"] for r in rows])) if rows else float("nan")
    lo, hi = LIMITS["step_hz"]
    checks = {
        "all_clips_loaded": {"pass": bool(rows) and not errors, "n": len(rows), "n_errors": len(errors)},
        "steps_found": {"pass": all(r["walk_segments"] + r["shuffle_segments"] > 0 for r in rows),
                        "without": [r["task"] for r in rows if r["walk_segments"] + r["shuffle_segments"] == 0]},
        "step_hz_in_human_range": {"pass": all(lo <= w["step_hz"] <= hi for w in walks), "range": [lo, hi],
                                   "outside": [(w["task"], w["start"], round(w["step_hz"], 2)) for w in walks
                                               if not lo <= w["step_hz"] <= hi]},
        "feet_alternate": {"pass": all(r["alternation"] >= LIMITS["alternation_min"] for r in rows),
                           "min": min((r["alternation"] for r in rows), default=float("nan"))},
        "leg_length_in_range": {"pass": all(LIMITS["leg_m"][0] <= r["leg_m"] <= LIMITS["leg_m"][1] for r in rows),
                                "range": LIMITS["leg_m"]},
    }
    passed = all(c["pass"] for c in checks.values())
    deltas = cfg["dog"]["deltas"]
    agg = {"leg_m_median": h_h, "hip_height_dog_m": h_d,
           "ratio_constant": (h_h / h_d) ** 0.7 if rows else float("nan"),
           "walk_segments": len(walks), "walking_s": float(sum(w["duration_s"] for w in walks)),
           **{f"{k}_median": float(np.median([w[k] for w in walks])) if walks else float("nan")
              for k in ("speed_mps", "step_hz", "dog_per_step", "lock_dev")},
           "dog_trot_segments": sum(w["dog_gait"] == "trot" for w in walks),
           "lockable": lockable(walks, deltas), "lockable_in_windows": lockable([w for w in walks if w["in_window"]],
                                                                                 deltas)}
    figures(out / "figures", per, walks, h_h, h_d, deltas)
    write_csv(out / "segments.csv", walks)
    summary = {"provenance": prov, "limits": LIMITS, "checks": checks, "pass": passed, "dog": dog,
               "aggregate": agg, "tasks": rows, "walk_segments": walks, "errors": errors,
               "elapsed_s": time.time() - t0}
    (out / "summary.json").write_text(json.dumps(clean(summary), indent=2), encoding="utf-8")
    f = lambda x, nd=2: "–" if x is None or x != x else f"{x:.{nd}f}"  # noqa: E731
    L = ["# M0: human gait and the dog's natural rhythm (fullopt spec §6.1-6.3)", "",
         f"Run `{prov['run_id']}` · code `{prov['git']['describe']}` (dirty={prov['git']['dirty']}) · "
         f"{len(rows)} tasks · {len(errors)} errors · **{'PASS' if passed else 'FAIL'}**", "",
         "| check | pass |", "|---|---|", *[f"| {k} | {c['pass']} |" for k, c in checks.items()], "",
         f"B2 (home pose): hip height h_d {f(h_d)} m, thigh {f(dog['thigh_m'])} m, calf {f(dog['calf_m'])} m, "
         f"longest walk stride {f(dog['max_stride_walk_m'])} m. Human leg length h_h (median) {f(h_h)} m; "
         f"(h_h / h_d)^0.7 = {f(agg['ratio_constant'])}.", "",
         f"Walk segments: {len(walks)} ({f(agg['walking_s'], 1)} s); median speed {f(agg['speed_mps_median'])} m/s, "
         f"step frequency {f(agg['step_hz_median'])} Hz, dog footfalls per human step {f(agg['dog_per_step_median'])}, "
         f"lock deviation {f(agg['lock_dev_median'], 3)}; {agg['dog_trot_segments']} would be trot.", "",
         "| δ | lockable walk segments | lockable walking time | same, inside task windows |", "|---|---|---|---|",
         *[f"| {d} | {f(v['segments'])} | {f(v['time'])} | "
           f"{f(agg['lockable_in_windows'].get(d, {}).get('time'))} |" for d, v in agg["lockable"].items()], "",
         "| task | clip | h_h [m] | touchdowns | alternation | walk / shuffle segments | "
         "window: steps, walk / shuffle / stand |", "|---|---|---|---|---|---|---|",
         *[f"| {r['task']} | {r['clip']} | {f(r['leg_m'])} | {r['touchdowns']} | {f(r['alternation'])} | "
           f"{r['walk_segments']} / {r['shuffle_segments']} | {r['window_steps']}, {f(r['window_walk_frac'])} / "
           f"{f(r['window_shuffle_frac'])} / {f(r['window_stand_frac'])} |" for r in rows], "",
         "| task | frames | steps | speed [m/s] | step Hz (Alexander) | dog gait | dog per step | lock dev |",
         "|---|---|---|---|---|---|---|---|",
         *[f"| {w['task']} | {w['start']}–{w['end']} | {w['steps']} | {f(w['speed_mps'])} | {f(w['step_hz'])} "
           f"({f(w['step_hz_alexander'])}) | {w['dog_gait']} | {f(w['dog_per_step'])} | {f(w['lock_dev'], 3)} |"
           for w in walks], "",
         "Right panel: grey bands are lockable at δ = 0.05 (dark) and 0.10 (light).", "",
         "![](figures/freq_speed.png)", "", "![](figures/timelines.png)"]
    if errors:
        L += ["", "Errors:", *[f"- {e['id']}: {e['error']}" for e in errors]]
    (out / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"pass={passed}  tasks={len(rows)}  walk segments={len(walks)}  -> {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
