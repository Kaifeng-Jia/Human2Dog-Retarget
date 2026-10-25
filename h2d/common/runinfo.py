"""Run provenance: which code, configs, external commits and environment produced a result.

Every script calls ``start_run`` before doing work and stores the returned dict under
``summary.json["provenance"]``. By default a run is refused when the working tree has
uncommitted changes or when an external repository is not at its pinned commit, so every
reported number can be traced to an exact commit (see docs/versioning.md).
"""

from __future__ import annotations

import hashlib
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from h2d import __version__
from h2d.paths import CONFIG_DIR, REPO_ROOT, load_config


class ProvenanceError(RuntimeError):
    pass


def _git(args: list[str], cwd: Path) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


_DEFAULT_DIRS = {"xmorph": "morph", "gmr": "GMR"}


def _external(name: str, spec: dict) -> dict:
    default = REPO_ROOT / "external" / _DEFAULT_DIRS.get(name, name)
    root = Path(os.environ.get(spec.get("env_var", ""), "") or default).expanduser()
    info = {"path": str(root), "pinned": spec["commit"], "present": root.is_dir()}
    if root.is_dir():
        head = _git(["rev-parse", "HEAD"], root)
        info["actual"] = head
        info["match"] = head == spec["commit"]
        dirty = _git(["status", "--porcelain", "--untracked-files=no"], root)
        info["dirty"] = bool(dirty) if dirty is not None else None
    return info


def _package_versions() -> dict:
    out = {"python": sys.version.split()[0]}
    for mod in ("numpy", "scipy", "mujoco", "torch"):
        try:
            m = __import__(mod)
            out[mod] = getattr(m, "__version__", "unknown")
        except Exception:  # noqa: BLE001 - optional packages
            continue
    try:
        import torch  # noqa: F401

        out["cuda_available"] = bool(torch.cuda.is_available())
        if out["cuda_available"]:
            out["cuda_device"] = torch.cuda.get_device_name(0)
            out["torch_cuda"] = torch.version.cuda
    except Exception:  # noqa: BLE001
        pass
    return out


def start_run(
    run_id: str,
    needs: tuple[str, ...] = ("xmorph",),
    configs: tuple[str, ...] = ("b2z1.yaml", "external.yaml"),
    allow_dirty: bool = False,
    allow_external_mismatch: bool = False,
) -> dict:
    """Collect provenance and enforce the clean-tree / pinned-external rules."""
    commit = _git(["rev-parse", "HEAD"], REPO_ROOT)
    status = _git(["status", "--porcelain", "--untracked-files=no"], REPO_ROOT)
    dirty = bool(status) if status is not None else None
    if dirty and not allow_dirty:
        raise ProvenanceError(
            "Working tree has uncommitted changes; commit them or pass --allow-dirty "
            "(the run will then be marked dirty and must not be reported as a result)."
        )

    ext_cfg = load_config("external.yaml")
    externals = {name: _external(name, ext_cfg[name]) for name in needs}
    bad = [n for n, e in externals.items() if e.get("present") and e.get("match") is False]
    missing = [n for n, e in externals.items() if not e.get("present")]
    if missing:
        raise ProvenanceError(f"External checkout(s) not found: {missing}. See docs/setup_ubuntu.md.")
    if bad and not allow_external_mismatch:
        detail = {n: (externals[n]["actual"], externals[n]["pinned"]) for n in bad}
        raise ProvenanceError(f"External repo not at pinned commit (actual, pinned): {detail}")

    return {
        "run_id": run_id,
        "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "h2d_version": __version__,
        "git": {
            "commit": commit,
            "branch": _git(["rev-parse", "--abbrev-ref", "HEAD"], REPO_ROOT),
            "describe": _git(["describe", "--tags", "--always", "--dirty"], REPO_ROOT),
            "dirty": dirty,
        },
        "flags": {"allow_dirty": allow_dirty, "allow_external_mismatch": allow_external_mismatch},
        "externals": externals,
        "configs": {c: _sha256(CONFIG_DIR / c) for c in configs},
        "command": " ".join([Path(sys.argv[0]).name, *sys.argv[1:]]),
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "packages": _package_versions(),
    }


def add_run_args(ap) -> None:
    ap.add_argument("--run-id", required=True, help="run ticket id, e.g. R001_b01")
    ap.add_argument("--out", default=None, help="output folder (default outputs/<run-id>)")
    ap.add_argument("--allow-dirty", action="store_true", help="run with uncommitted changes (not reportable)")
    ap.add_argument("--allow-external-mismatch", action="store_true", help="run with unpinned external repos")
