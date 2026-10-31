"""Which tasks the full-optimization line solves.

The same selection as the learned line (passing OMOMO_new candidates that press; grasping needs the jaw site, not
modelled), so both lines are compared on the same tasks; kept here so the lines stay independent.
"""

from __future__ import annotations

import csv


def solvable_task_ids(tasks_csv, max_tasks: int | None = None) -> list[str]:
    """Ids in tasks.csv order (a prepare_tasks.py run)."""
    with open(tasks_csv, newline="", encoding="utf-8") as fh:
        ids = [r["id"] for r in csv.DictReader(fh) if r["pass"] == "True" and r["confirmed"] == "False"
               and r["dataset"] == "omomo_new" and r["grip"] != "grasp"]
    return ids[:max_tasks]
