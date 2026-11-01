#!/usr/bin/env python
"""Export push tasks as ``HOIClip`` files, the only input of the full-optimization line (fullopt spec v0.2 §2.1).

The tasks come from ``prepare_tasks.py`` runs (any dataset its sources read: OMOMO_new, FORCE). Split (spec §8.5):
``--dev``: the tasks both lines solve (h2d/fullopt/tasks.py), where parameters are tuned; ``--heldout``: every other
passing press task of the given runs whose subject or object the dev split does not have (Kevin: objects and people
not used yet), fixed by this rule before any held-out result is seen. A segment already exported is skipped; every
skipped row is listed with its reason. Each clip is the whole recording; the task's window and segment go into ``meta``.

Writes outputs/<run-id>/{clips/<clip>_<start>.npz, summary.json, report.md}. Derived from licensed data: keep the
clips out of git.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from h2d.common.data.sources import SOURCES  # noqa: E402
from h2d.common.data.tasks import load_task  # noqa: E402
from h2d.common.runinfo import ProvenanceError, add_run_args, start_run  # noqa: E402
from h2d.common.tables import clean  # noqa: E402
from h2d.fullopt.hoi import from_common_clip, validate  # noqa: E402
from h2d.fullopt.tasks import solvable_task_ids  # noqa: E402
from h2d.paths import data_path  # noqa: E402


def task_rows(run: Path) -> list[dict]:
    with open(run / "tasks.csv", newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r["pass"] == "True" and r["grip"] != "grasp"]


def main() -> int:
    ap = argparse.ArgumentParser()
    add_run_args(ap)
    ap.add_argument("--dev", required=True, help="prepare_tasks.py output folder of the dev tasks")
    ap.add_argument("--heldout", nargs="*", default=[], help="prepare_tasks.py output folders for the held-out split")
    ap.add_argument("--max-dev", type=int, default=12)
    ap.add_argument("--omomo-root", default=None)
    ap.add_argument("--force-root", default=None)
    ap.add_argument("--smplh-root", default=None)
    args = ap.parse_args()
    dev = Path(args.dev)
    dev_ids = set(solvable_task_ids(dev / "tasks.csv", args.max_dev))
    todo = [("dev", dev, r) for r in task_rows(dev) if r["id"] in dev_ids]
    todo += [("heldout", Path(h), r) for h in args.heldout for r in task_rows(Path(h))]
    datasets = sorted({r["dataset"] for _, _, r in todo})
    needs = tuple(sorted({n for d in datasets for n in SOURCES[d].needs}))
    try:
        prov = start_run(args.run_id, needs=needs, configs=("data.yaml", "external.yaml", "fullopt/formats.yaml"),
                         allow_dirty=args.allow_dirty, allow_external_mismatch=args.allow_external_mismatch)
    except ProvenanceError as e:
        print(f"[refused] {e}", file=sys.stderr)
        return 2
    out = Path(args.out or f"outputs/{args.run_id}")
    (out / "clips").mkdir(parents=True, exist_ok=True)
    roots = {"omomo_new": args.omomo_root, "force": args.force_root}
    srcs = {d: SOURCES[d](Path(roots[d]).expanduser() if roots[d] else data_path(d), args) for d in datasets}
    files = {d: {p.stem: p for p in s.files} for d, s in srcs.items()}
    rows, seen, errors, skipped, dev_seen = [], {}, [], [], {"subject": set(), "object": set()}
    for split, run, r in todo:
        key = (r["dataset"], r["clip"], int(r["start"]), int(r["end"]))
        uid = f"{r['clip']}_{r['start']}"
        if key in seen:
            skipped.append({"id": uid, "task_id": r["id"], "task_run": run.name,
                            "reason": f"same segment as {seen[key]}"})
            continue
        seen[key] = f"{split} {r['id']} ({run.name})"
        try:
            task = load_task(run / "tasks" / f"{r['id']}.npz")
            clip, mesh, _ = srcs[r["dataset"]].load(files[r["dataset"]][r["clip"]])
            if split == "dev":
                dev_seen["subject"].add(clip.subject)
                dev_seen["object"].add(clip.obj)
            elif clip.subject in dev_seen["subject"] and clip.obj in dev_seen["object"]:
                skipped.append({"id": uid, "task_id": r["id"], "task_run": run.name,
                                "reason": "not held out: subject and object both in dev"})
                continue
            c = from_common_clip(clip, mesh, {"id": uid, "task_id": r["id"], "task_run": run.name, "split": split,
                                              "dataset": r["dataset"], "mode": r["mode"], "window": task["window"],
                                              "segment": task["segment"]})
            problems = validate(c)
            c.save(out / "clips" / f"{uid}.npz")
            rows.append({"id": uid, "split": split, "dataset": r["dataset"], "task_run": run.name, "task_id": r["id"],
                         "object": clip.obj, "subject": clip.subject, "frames": c.n, "fps": c.fps,
                         "hand_contact": c.hand_contact is not None, "problems": problems})
            print(f"  {split} {uid}: {c.n} frames {'; '.join(problems) or 'ok'}", flush=True)
        except Exception as e:  # noqa: BLE001 - report and continue
            errors.append({"id": uid, "error": f"{type(e).__name__}: {str(e)[:300]}"})
            print(f"  {uid}: error {errors[-1]['error']}", flush=True)
    n = {s: sum(r["split"] == s for r in rows) for s in ("dev", "heldout")}
    passed = not errors and not any(r["problems"] for r in rows) and n["dev"] == len(dev_ids)
    (out / "summary.json").write_text(json.dumps(clean({"provenance": prov, "pass": passed, "counts": n, "clips": rows,
                                                        "skipped": skipped, "errors": errors}), indent=2),
                                      encoding="utf-8")
    lines = ["# HOI clips for the full-optimization line (fullopt spec v0.2 §2.1, §8.5)", "",
             f"Run `{prov['run_id']}` · code `{prov['git']['describe']}` (dirty={prov['git']['dirty']}) · "
             f"dev {n['dev']} · held-out {n['heldout']} · {len(errors)} errors · "
             f"**{'PASS' if passed else 'FAIL'}**", "",
             "| split | id | dataset | task (run) | object | subject | frames | fps | hand contact labels | problems |",
             "|---|---|---|---|---|---|---|---|---|---|",
             *[f"| {r['split']} | {r['id']} | {r['dataset']} | {r['task_id']} ({r['task_run']}) | {r['object']} | "
               f"{r['subject']} | {r['frames']} | {r['fps']:g} | {r['hand_contact']} | {'; '.join(r['problems'])} |"
               for r in rows]]
    if skipped:
        lines += ["", f"Skipped ({len(skipped)}):", *[f"- {k['id']} ({k['task_id']}, {k['task_run']}): {k['reason']}"
                                                     for k in skipped]]
    if errors:
        lines += ["", "Errors:", *[f"- {e['id']}: {e['error']}" for e in errors]]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"pass={passed}  dev={n['dev']}  heldout={n['heldout']}  -> {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
