#!/usr/bin/env python
"""Read-only inspection of the processed OMOMO_new dataset (*.pt).

Reports the file inventory (count, name pattern, objects, subjects, sizes) and, for a few
sampled files, the full nested structure: keys, types, shapes, dtypes and value ranges.
No data values beyond summary statistics are written, and nothing is copied.

Usage:
  python scripts/common/inspect_omomo_new.py --run-id R002_omomo_new_format [--root PATH] [--n 5]
  (root defaults to $OMOMO_NEW_ROOT, then configs/data.yaml)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from h2d.common.runinfo import ProvenanceError, add_run_args, start_run  # noqa: E402
from h2d.paths import data_path  # noqa: E402

NAME_RE = re.compile(r"^(?P<subject>sub\d+)_(?P<object>[a-z]+)_(?P<seq>\d+)$")


def describe(x, depth: int = 0, max_depth: int = 6):
    """Structure of a loaded object: dict/list/tuple recursion, tensors and arrays summarized."""
    try:
        import torch
    except ImportError:  # pragma: no cover
        torch = None
    if depth > max_depth:
        return {"type": type(x).__name__, "truncated": True}
    if isinstance(x, dict):
        return {"type": "dict", "keys": {str(k): describe(v, depth + 1) for k, v in list(x.items())[:200]}}
    if isinstance(x, (list, tuple)):
        out = {"type": type(x).__name__, "len": len(x)}
        if len(x):
            out["first"] = describe(x[0], depth + 1)
        return out
    if torch is not None and isinstance(x, torch.Tensor):
        a = x.detach().cpu()
        info = {"type": "tensor", "shape": list(a.shape), "dtype": str(a.dtype)}
        if a.numel() and (a.is_floating_point() or a.dtype in (torch.int32, torch.int64, torch.uint8, torch.bool)):
            af = a.float()
            info.update(min=float(af.min()), max=float(af.max()), mean=float(af.mean()))
            if a.ndim == 2 and a.shape[1] <= 2048:
                # per-column ranges help reverse-engineer a packed feature layout
                info["col_min"] = [round(float(v), 4) for v in af.min(0).values]
                info["col_max"] = [round(float(v), 4) for v in af.max(0).values]
        return info
    if isinstance(x, np.ndarray):
        info = {"type": "ndarray", "shape": list(x.shape), "dtype": str(x.dtype)}
        if x.size and np.issubdtype(x.dtype, np.number):
            info.update(min=float(x.min()), max=float(x.max()))
        return info
    if isinstance(x, (int, float, bool, str)) or x is None:
        return {"type": type(x).__name__, "value": x if not isinstance(x, str) or len(x) < 200 else x[:200]}
    return {"type": type(x).__name__}


def main() -> int:
    ap = argparse.ArgumentParser()
    add_run_args(ap)
    ap.add_argument("--root", default=None)
    ap.add_argument("--n", type=int, default=5, help="number of files to describe in full")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--allow-pickle", action="store_true",
                    help="fall back to torch.load(weights_only=False) for files that need it (trusted data only)")
    args = ap.parse_args()
    try:
        prov = start_run(args.run_id, needs=(), configs=("data.yaml",),
                         allow_dirty=args.allow_dirty, allow_external_mismatch=args.allow_external_mismatch)
    except ProvenanceError as e:
        print(f"[refused] {e}", file=sys.stderr)
        return 2
    import torch

    root = Path(args.root).expanduser() if args.root else data_path("omomo_new")
    out = Path(args.out or f"outputs/{args.run_id}")
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(root.rglob("*.pt"))
    if not files:
        print(f"no .pt files under {root}", file=sys.stderr)
        return 1

    objects, subjects, unmatched = Counter(), Counter(), []
    for f in files:
        m = NAME_RE.match(f.stem)
        if m:
            objects[m["object"]] += 1
            subjects[m["subject"]] += 1
        else:
            unmatched.append(f.name)
    sizes = np.array([f.stat().st_size for f in files])

    rng = np.random.default_rng(args.seed)
    picks = [files[i] for i in sorted(rng.choice(len(files), size=min(args.n, len(files)), replace=False))]
    samples = {}
    for f in picks:
        rec = {"bytes": int(f.stat().st_size)}
        try:
            obj = torch.load(f, map_location="cpu", weights_only=True)
            rec["loaded_with"] = "weights_only=True"
        except Exception as e:  # noqa: BLE001
            rec["weights_only_error"] = str(e)[:500]
            if not args.allow_pickle:
                samples[f.name] = rec
                continue
            obj = torch.load(f, map_location="cpu", weights_only=False)
            rec["loaded_with"] = "weights_only=False"
        rec["structure"] = describe(obj)
        samples[f.name] = rec

    results = {
        "provenance": prov,
        "root": str(root),
        "n_files": len(files),
        "subdirs": sorted({str(f.parent.relative_to(root)) for f in files})[:50],
        "name_pattern": NAME_RE.pattern,
        "n_unmatched_names": len(unmatched),
        "unmatched_examples": unmatched[:20],
        "objects": dict(objects.most_common()),
        "n_subjects": len(subjects),
        "file_size_bytes": {"min": int(sizes.min()), "median": int(np.median(sizes)), "max": int(sizes.max())},
        "samples": samples,
    }
    (out / "summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    lines = [
        "# OMOMO_new format (read-only)",
        "",
        f"Run `{prov['run_id']}` · code `{prov['git']['describe']}` (dirty={prov['git']['dirty']}) · root `{root}`",
        "",
        f"* files: {len(files)}; names matching `{NAME_RE.pattern}`: {len(files) - len(unmatched)}",
        f"* subjects: {len(subjects)}; objects: " + ", ".join(f"{k} ({v})" for k, v in objects.most_common()),
        f"* file size: min {sizes.min()/1e3:.0f} kB, median {np.median(sizes)/1e3:.0f} kB, max {sizes.max()/1e3:.0f} kB",
        "",
        "## Sampled files",
    ]
    for name, rec in samples.items():
        lines += ["", f"### {name}", "", "```json", json.dumps(rec, indent=1)[:6000], "```"]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:8]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
