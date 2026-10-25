"""Path resolution for configs and the external X-Morph checkout."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "configs"


def load_config(name: str = "b2z1.yaml") -> dict:
    with open(CONFIG_DIR / name, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def xmorph_root() -> Path:
    """Return the X-Morph checkout given by $XMORPH_ROOT, or external/morph."""
    env = os.environ.get("XMORPH_ROOT")
    root = Path(env).expanduser() if env else REPO_ROOT / "external" / "morph"
    if not (root / "assets").is_dir():
        raise FileNotFoundError(
            f"X-Morph checkout not found at {root}. Set XMORPH_ROOT or follow docs/setup_ubuntu.md."
        )
    return root


def xmorph_path(rel: str) -> Path:
    return xmorph_root() / rel
