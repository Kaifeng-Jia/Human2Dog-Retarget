"""Small helpers for run outputs: JSON-safe values, CSV tables, NaN-aware medians."""

from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np


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
    if isinstance(v, np.ndarray):
        return clean(v.tolist())
    return v


def write_csv(path: Path, rows: list[dict], columns: list[str] | None = None) -> None:
    """Rows as CSV (floats rounded to 4 decimals). ``columns`` selects and orders; default: all keys in order
    of first appearance."""
    if not rows:
        Path(path).write_text("", encoding="utf-8")
        return
    if columns is None:
        columns = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows([{k: _round(r.get(k)) for k in columns} for r in rows])


def nanmed(x) -> float:
    x = np.asarray([v for v in x if v is not None and not (isinstance(v, float) and math.isnan(v))], float)
    return float(np.median(x)) if x.size else float("nan")
