"""OMOMO object meshes.

Meshes: the 13 InterMimic re-exports of the OMOMO objects that HOI-Retarget ships under MIT
(leggedrobotics/hoi-retarget, ``assets/objects/objects/<name>/<name>.obj``, see its LICENSE-OBJECTS).
They are in the object frame that OMOMO_new's ``obj_pos`` / ``obj_rot`` refer to: HOI-Retarget applies
the recorded pose to them directly, and the data profile (R003) checked it on our copy: recorded contact
bodies lie 2-7 mm from the transformed surface. Known issue: the suitcase mesh bottom sits ~3 cm above
the recorded floor contact (R003, issue #6).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from h2d.common.objectmesh import ObjectMesh, load_obj, tilt_and_yaw  # noqa: F401 - re-exported
from h2d.paths import REPO_ROOT

OBJECT_NAMES = ("clothesstand", "floorlamp", "largebox", "largetable", "monitor", "plasticbox", "smallbox",
                "smalltable", "suitcase", "trashcan", "tripod", "whitechair", "woodchair")


def hoi_retarget_root() -> Path:
    env = os.environ.get("HOI_RETARGET_ROOT")
    return Path(env).expanduser() if env else REPO_ROOT / "external" / "hoi-retarget"


def object_mesh_path(name: str) -> Path:
    p = hoi_retarget_root() / "assets" / "objects" / "objects" / name / f"{name}.obj"
    if not p.is_file():
        raise FileNotFoundError(f"object mesh not found: {p} (set HOI_RETARGET_ROOT, see docs/setup_ubuntu.md)")
    return p


@lru_cache(maxsize=None)
def load_object(name: str) -> ObjectMesh:
    v, f = load_obj(object_mesh_path(name))
    return ObjectMesh(name, v, f)
