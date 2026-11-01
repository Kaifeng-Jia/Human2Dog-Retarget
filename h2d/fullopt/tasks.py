"""Which tasks the full-optimization line solves.

Press tasks: the same selection as the learned line (passing OMOMO_new candidates that press), so both lines are
compared on the same tasks. Grasp tasks (pulls on a side or slant face, which the learned line does not model): the
passing grasp segments of a ``push_candidates.py`` pool under ``configs/fullopt/grasp_selection.yaml``, split by person
(fullopt spec v0.2 §8.5). Kept here so the lines stay independent.
"""

from __future__ import annotations

import csv


def solvable_task_ids(tasks_csv, max_tasks: int | None = None) -> list[str]:
    """Ids in tasks.csv order (a prepare_tasks.py run)."""
    with open(tasks_csv, newline="", encoding="utf-8") as fh:
        ids = [r["id"] for r in csv.DictReader(fh) if r["pass"] == "True" and r["confirmed"] == "False"
               and r["dataset"] == "omomo_new" and r["grip"] != "grasp"]
    return ids[:max_tasks]


def grasp_rows(pool_csv) -> list[dict]:
    """Passing segments of a push_candidates.py pool (``pool.csv``) whose robot grip is a grasp, in file order."""
    with open(pool_csv, newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r["passed"] == "True" and r["grip"] == "grasp"]


def split_by_person(subject: str, dev_people) -> str:
    """Grasp split: the people of the press dev split are dev, everyone else is held out (each held-out person is
    unseen in dev). FORCE's "subject" is a recording session, never one of the dev people: FORCE is held out."""
    return "dev" if subject in set(dev_people) else "heldout"
