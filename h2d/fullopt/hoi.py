"""The input of the full-optimization line: one human-object interaction clip (fullopt spec v0.2 §2.1).

As in OmniRetarget (holosoma), the method reads world joint positions under a joint mapping per source format, and
the object as a mesh with a pose trajectory; everything dataset-specific stays in the adapters (``from_common_clip``
here for OMOMO_new and FORCE, ``scripts/fullopt/export_hoi.py``). Mappings: ``configs/fullopt/formats.yaml``.

Conventions: metres, z up, world frame; object world point = R(obj_quat) @ local + obj_pos, quaternion xyzw.
On disk: one ``.npz`` per clip (``HOIClip.save`` / ``HOIClip.load``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from h2d.paths import load_config

REQUIRED = ("pelvis", "spine", "chest", "neck", "head", "l_hip", "r_hip", "l_knee", "r_knee", "l_ankle", "r_ankle",
            "l_toe", "r_toe", "l_shoulder", "r_shoulder", "l_elbow", "r_elbow", "l_wrist", "r_wrist")
OPTIONAL = ("l_index", "r_index", "l_pinky", "r_pinky")      # finger bases (the palm); else the palm comes from the arm
UPRIGHT_FRAC = 0.10      # validate units and axes on this share of frames, those with the head highest above the ankles


@dataclass
class HOIClip:
    fps: float
    joints: np.ndarray                      # (T, J, 3)
    joint_names: tuple[str, ...]            # semantic names (REQUIRED, optionally OPTIONAL)
    obj_verts: np.ndarray                   # (V, 3) object frame
    obj_faces: np.ndarray                   # (F, 3)
    obj_pos: np.ndarray                     # (T, 3)
    obj_quat: np.ndarray                    # (T, 4) xyzw
    floor_z: float = 0.0
    hand_contact: np.ndarray | None = None  # (T, 2) bool, left / right; None: the method derives it from distances
    meta: dict = field(default_factory=dict)

    @property
    def n(self) -> int:
        return int(len(self.joints))

    def has(self, name: str) -> bool:
        return name in self.joint_names

    def joint(self, name: str) -> np.ndarray:
        return self.joints[:, self.joint_names.index(name)]

    def save(self, path) -> None:
        arrays = {k: getattr(self, k) for k in ("joints", "obj_verts", "obj_faces", "obj_pos", "obj_quat")}
        if self.hand_contact is not None:
            arrays["hand_contact"] = self.hand_contact
        np.savez_compressed(path, fps=self.fps, floor_z=self.floor_z, joint_names=np.array(self.joint_names),
                            meta=np.array(json.dumps(self.meta)), **arrays)

    @classmethod
    def load(cls, path) -> HOIClip:
        z = np.load(path)
        return cls(fps=float(z["fps"]), joints=z["joints"], joint_names=tuple(str(s) for s in z["joint_names"]),
                   obj_verts=z["obj_verts"], obj_faces=z["obj_faces"], obj_pos=z["obj_pos"], obj_quat=z["obj_quat"],
                   floor_z=float(z["floor_z"]), hand_contact=z["hand_contact"] if "hand_contact" in z.files else None,
                   meta=json.loads(str(z["meta"])))


def mapping(fmt: str) -> dict[str, str]:
    """Semantic name -> source joint name for a source format (configs/fullopt/formats.yaml)."""
    return load_config("fullopt/formats.yaml")[fmt]


def rename(joints: np.ndarray, src_names, fmt: str) -> tuple[np.ndarray, tuple[str, ...]]:
    """(T, J_src, 3) joints named in a source format -> the semantic joints the format provides."""
    src = list(src_names)
    names = tuple(k for k, v in mapping(fmt).items() if v in src)
    return np.asarray(joints, float)[:, [src.index(mapping(fmt)[k]) for k in names]], names


def validate(c: HOIClip) -> list[str]:
    """Problems that make a clip unusable (empty when it is fine): missing joints, shapes, units, axes, floor."""
    out = [f"missing joint {k}" for k in REQUIRED if not c.has(k)]
    T = c.n
    if out or T < 2:
        return out + ([] if T >= 2 else ["fewer than 2 frames"])
    if c.joints.shape[1:] != (len(c.joint_names), 3) or c.obj_pos.shape != (T, 3) or c.obj_quat.shape != (T, 4):
        out.append("shapes: joints (T, J, 3), obj_pos (T, 3), obj_quat (T, 4) with one T")
    if c.hand_contact is not None and c.hand_contact.shape != (T, 2):
        out.append("hand_contact must be (T, 2)")
    if not (np.isfinite(c.joints).all() and np.isfinite(c.obj_pos).all() and np.isfinite(c.obj_quat).all()):
        out.append("non-finite values")
    if not 10 <= c.fps <= 240:
        out.append(f"fps {c.fps:g} outside 10-240")
    if np.abs(np.linalg.norm(c.obj_quat, axis=1) - 1).max() > 1e-3:
        out.append("object quaternions not unit")
    # Units and axes on the person's most upright frames: crouching or bending over for most of a clip lowers the head
    # (R026: head below the pelvis in the median), standing up at some point shows the height and the up axis again.
    ank = np.stack([c.joint("l_ankle")[:, 2], c.joint("r_ankle")[:, 2]], 1)
    head, pelvis = c.joint("head")[:, 2], c.joint("pelvis")[:, 2]
    stand = head - ank.min(1)
    up = stand >= np.quantile(stand, 1 - UPRIGHT_FRAC)
    if not np.median(head[up]) > np.median(pelvis[up]) > np.median(ank[up].max(1)):
        out.append("not z-up: head, pelvis and ankles are not above one another when most upright")
    stature = float(np.median(stand[up]))
    if not 0.8 <= stature <= 2.1:
        out.append(f"head above the ankles {stature:.2f} m when most upright: not metres, or not a person")
    foot = np.minimum(c.joint("l_toe")[:, 2], c.joint("r_toe")[:, 2]) - c.floor_z
    if not -0.05 <= np.percentile(foot, 5) <= 0.20:
        out.append(f"feet not near the floor (lowest toe {np.percentile(foot, 5):+.2f} m from floor_z)")
    return out


def from_common_clip(clip, mesh, meta: dict | None = None) -> HOIClip:
    """Adapter for ``h2d.common.data.omomo_new.Clip``, the layout both OMOMO_new and FORCE are read into."""
    from h2d.common.data.omomo_new import BODY_NAMES, hand_contact

    joints, names = rename(clip.body_pos, BODY_NAMES, "common_clip")
    known = (clip.contact_body != -1).any(1)                  # OMOMO_new marks frames without contact data by -1
    return HOIClip(fps=float(clip.fps), joints=joints, joint_names=names, obj_verts=np.asarray(mesh.verts, float),
                   obj_faces=np.asarray(mesh.faces, np.int64), obj_pos=np.asarray(clip.obj_pos, float),
                   obj_quat=np.asarray(clip.obj_rot_xyzw, float), floor_z=0.0,
                   hand_contact=hand_contact(clip) if known.all() else None,
                   meta={"subject": clip.subject, "object": clip.obj, "clip": clip.name, **(meta or {})})


def load_dir(folder) -> list[HOIClip]:
    return [HOIClip.load(p) for p in sorted(Path(folder).glob("*.npz"))]
