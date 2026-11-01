#!/usr/bin/env python
"""Export tasks as ``HOIClip`` files, the only input of the full-optimization line (fullopt spec v0.2 §2.1, §8.5).

Press tasks (default) come from ``prepare_tasks.py`` runs (any dataset its sources read: OMOMO_new, FORCE). Split:
``--dev``: the tasks both lines solve (h2d/fullopt/tasks.py), where parameters are tuned; ``--heldout``: every other
passing press task of the given runs whose subject or object the dev split does not have (Kevin: objects and people
not used yet), fixed by this rule before any held-out result is seen.

Grasp tasks (``--grasp``): the passing grasp segments (pulls on a side or slant face) of ``push_candidates.py`` pools
run with ``configs/fullopt/grasp_selection.yaml``. Split by person (``tasks.split_by_person``): the people of the press
dev split (``--dev-people-from``, the press export's summary.json) are dev, everyone else is held out.

A segment already exported is skipped; every skipped row is listed with its reason. Each clip is the whole recording;
the task's window (the segment and 1 s either side), segment, hand mode, grip and interaction go into ``meta``.

Writes outputs/<run-id>/{clips/<clip>_<start>.npz, summary.json, report.md}. Derived from licensed data: keep the
clips out of git.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from h2d.common.data.sources import SOURCES  # noqa: E402
from h2d.common.data.tasks import load_task  # noqa: E402
from h2d.common.runinfo import ProvenanceError, add_run_args, start_run  # noqa: E402
from h2d.common.tables import clean  # noqa: E402
from h2d.fullopt.hoi import from_common_clip, validate  # noqa: E402
from h2d.fullopt.tasks import grasp_rows, solvable_task_ids, split_by_person  # noqa: E402
from h2d.paths import data_path  # noqa: E402

WINDOW_S = 1.0      # either side of the segment, as prepare_tasks.py


def task_rows(run: Path) -> list[dict]:
    with open(run / "tasks.csv", newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r["pass"] == "True" and r["grip"] != "grasp"]


def press_items(dev: Path, heldout: list[str], max_dev: int) -> tuple[list[dict], set[str]]:
    dev_ids = set(solvable_task_ids(dev / "tasks.csv", max_dev))
    rows = [("dev", dev, r) for r in task_rows(dev) if r["id"] in dev_ids]
    rows += [("heldout", Path(h), r) for h in heldout for r in task_rows(Path(h))]
    return [{"split": s, "dataset": r["dataset"], "clip": r["clip"], "start": int(r["start"]), "end": int(r["end"]),
             "mode": r["mode"], "task_id": r["id"], "task_run": run.name, "task_file": run / "tasks" / f"{r['id']}.npz",
             "grip": r.get("grip") or "press", "interaction": r.get("interaction") or "push"}
            for s, run, r in rows], dev_ids


def grasp_items(pools: list[str], people: set[str]) -> list[dict]:
    items = [{"split": split_by_person(r["subject"], people), "dataset": r["dataset"], "clip": r["name"],
              "start": int(r["start"]), "end": int(r["end"]), "mode": r["mode"], "task_id": "",
              "task_run": Path(p).parent.name, "task_file": None, "grip": "grasp", "interaction": r["interaction"],
              "pool": {k: r[k] for k in ("human", "contact_z_median_m", "root_disp_xy_m", "obj_disp_xy_m",
                                         "obj_yaw_maxabs_deg", "face")}}
             for p in pools for r in grasp_rows(p)]
    return sorted(items, key=lambda i: i["split"] != "dev")         # dev first (stable)


def main() -> int:
    ap = argparse.ArgumentParser()
    add_run_args(ap)
    ap.add_argument("--dev", default=None, help="press: prepare_tasks.py output folder of the dev tasks")
    ap.add_argument("--heldout", nargs="*", default=[], help="press: prepare_tasks.py output folders, held-out split")
    ap.add_argument("--max-dev", type=int, default=12)
    ap.add_argument("--grasp", nargs="*", default=None,
                    help="grasp: pool.csv files of push_candidates.py runs (configs/fullopt/grasp_selection.yaml)")
    ap.add_argument("--dev-people-from", default=None,
                    help="grasp: summary.json of the press export; the subjects of its dev clips are the dev people")
    ap.add_argument("--omomo-root", default=None)
    ap.add_argument("--force-root", default=None)
    ap.add_argument("--smplh-root", default=None)
    args = ap.parse_args()
    grasp = args.grasp is not None
    if grasp == bool(args.dev) or (grasp and not args.dev_people_from):
        ap.error("either --dev (press) or --grasp with --dev-people-from (grasp)")
    if grasp:
        press = json.loads(Path(args.dev_people_from).read_text())["clips"]
        people = {r["subject"] for r in press if r["split"] == "dev"}
        todo, dev_ids = grasp_items(args.grasp, people), set()
    else:
        people = set()
        todo, dev_ids = press_items(Path(args.dev), args.heldout, args.max_dev)
    datasets = sorted({i["dataset"] for i in todo})
    needs = tuple(sorted({n for d in datasets for n in SOURCES[d].needs}))
    configs = ("data.yaml", "external.yaml", "fullopt/formats.yaml")
    configs += ("fullopt/grasp_selection.yaml",) if grasp else ()
    try:
        prov = start_run(args.run_id, needs=needs, configs=configs, allow_dirty=args.allow_dirty,
                         allow_external_mismatch=args.allow_external_mismatch)
    except ProvenanceError as e:
        print(f"[refused] {e}", file=sys.stderr)
        return 2
    out = Path(args.out or f"outputs/{args.run_id}")
    (out / "clips").mkdir(parents=True, exist_ok=True)
    roots = {"omomo_new": args.omomo_root, "force": args.force_root}
    srcs = {d: SOURCES[d](Path(roots[d]).expanduser() if roots[d] else data_path(d), args) for d in datasets}
    files = {d: {p.stem: p for p in s.files} for d, s in srcs.items()}
    rows, seen, errors, skipped, dev_seen = [], {}, [], [], {"subject": set(), "object": set()}
    for it in todo:
        key = (it["dataset"], it["clip"], it["start"], it["end"])
        uid = f"{it['clip']}_{it['start']}"
        split = it["split"]
        if key in seen:
            skipped.append({"id": uid, "task_id": it["task_id"], "task_run": it["task_run"],
                            "reason": f"same segment as {seen[key]}"})
            continue
        seen[key] = f"{split} {it['task_id'] or uid} ({it['task_run']})"
        try:
            clip, mesh, _ = srcs[it["dataset"]].load(files[it["dataset"]][it["clip"]])
            if grasp:
                s, e, k = it["start"], it["end"], round(WINDOW_S * clip.fps)
                win, seg = [max(0, s - k), min(clip.n, e + k)], [s, e]
            else:
                task = load_task(it["task_file"])
                win, seg = task["window"], task["segment"]
                if split == "dev":
                    dev_seen["subject"].add(clip.subject)
                    dev_seen["object"].add(clip.obj)
                elif clip.subject in dev_seen["subject"] and clip.obj in dev_seen["object"]:
                    skipped.append({"id": uid, "task_id": it["task_id"], "task_run": it["task_run"],
                                    "reason": "not held out: subject and object both in dev"})
                    continue
            c = from_common_clip(clip, mesh, {"id": uid, "task_id": it["task_id"], "task_run": it["task_run"],
                                              "split": split, "dataset": it["dataset"], "mode": it["mode"],
                                              "window": win, "segment": seg, "grip": it["grip"],
                                              "interaction": it["interaction"]})
            problems = validate(c)
            c.save(out / "clips" / f"{uid}.npz")
            rows.append({"id": uid, "split": split, "dataset": it["dataset"], "task_run": it["task_run"],
                         "task_id": it["task_id"], "object": clip.obj, "subject": clip.subject, "mode": it["mode"],
                         "grip": it["grip"], "frames": c.n, "fps": c.fps, "hand_contact": c.hand_contact is not None,
                         "problems": problems, **({"pool": it["pool"]} if grasp else {})})
            print(f"  {split} {uid}: {c.n} frames {'; '.join(problems) or 'ok'}", flush=True)
        except Exception as e:  # noqa: BLE001 - report and continue
            errors.append({"id": uid, "error": f"{type(e).__name__}: {str(e)[:300]}"})
            print(f"  {uid}: error {errors[-1]['error']}", flush=True)
    n = {s: sum(r["split"] == s for r in rows) for s in ("dev", "heldout")}
    complete = n["dev"] > 0 if grasp else n["dev"] == len(dev_ids)
    passed = not errors and not any(r["problems"] for r in rows) and complete
    by_object = Counter((r["object"], r["split"]) for r in rows)
    summary = {"provenance": prov, "kind": "grasp" if grasp else "press", "pass": passed, "counts": n,
               "dev_people": sorted(people) if grasp else None,
               "by_object": {o: {s: by_object[(o, s)] for s in ("dev", "heldout")}
                             for o in sorted({k[0] for k in by_object})},
               "clips": rows, "skipped": skipped, "errors": errors}
    (out / "summary.json").write_text(json.dumps(clean(summary), indent=2), encoding="utf-8")
    title = "grasp" if grasp else "press"
    lines = [f"# HOI clips for the full-optimization line, {title} tasks (fullopt spec v0.2 §2.1, §8.5)", "",
             f"Run `{prov['run_id']}` · code `{prov['git']['describe']}` (dirty={prov['git']['dirty']}) · "
             f"dev {n['dev']} · held-out {n['heldout']} · {len(errors)} errors · "
             f"**{'PASS' if passed else 'FAIL'}**", ""]
    if grasp:
        lines += [f"Dev people (the press dev split): {', '.join(sorted(people))}", "",
                  "| object | dev | held-out |", "|---|---|---|",
                  *[f"| {o} | {v['dev']} | {v['heldout']} |" for o, v in summary["by_object"].items()], ""]
    lines += ["| split | id | dataset | task (run) | object | subject | hand | frames | fps | hand contact labels | "
              "problems |", "|---|---|---|---|---|---|---|---|---|---|---|",
              *[f"| {r['split']} | {r['id']} | {r['dataset']} | {r['task_id'] or '–'} ({r['task_run']}) | "
                f"{r['object']} | {r['subject']} | {r['mode']} | {r['frames']} | {r['fps']:g} | {r['hand_contact']} | "
                f"{'; '.join(r['problems'])} |" for r in rows]]
    if skipped:
        lines += ["", f"Skipped ({len(skipped)}):", *[f"- {k['id']} ({k['task_id'] or '–'}, {k['task_run']}): "
                                                     f"{k['reason']}" for k in skipped]]
    if errors:
        lines += ["", "Errors:", *[f"- {e['id']}: {e['error']}" for e in errors]]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"pass={passed}  dev={n['dev']}  heldout={n['heldout']}  -> {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
