"""OMOMO_new adapter: one InterMimic-processed OMOMO clip -> typed arrays, contact modes, SMPL-X params.

Format: docs/data/omomo_new_format.md. Column layout and the y-up -> z-up body-frame conversion follow
the open-source HOI-Retarget reader (leggedrobotics/hoi-retarget @ b341dad, BSD-3-Clause,
``hoi_retarget/datasets/intermimic.py`` and ``hoi_retarget/gmr/utils/smpl.py``), re-implemented here.

Two uses, kept separate on purpose:
* interaction targets (contacts, hand and object poses) use the *recorded* body positions and the
  object pose, which share one world frame;
* the prior input (GMR -> G1) uses SMPL-X parameters with mean shape; their joint positions differ
  from the recorded ones by the subject's shape (checked by ``smplx_consistency``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

FPS = 30.0
DIM = 591
SLICES = {
    "root_pos": slice(0, 3),
    "root_rot_xyzw": slice(3, 7),
    "dof_pos": slice(9, 162),          # 51 joints x 3 (body order without the pelvis)
    "body_pos": slice(162, 318),       # 52 x 3, world
    "obj_pos": slice(318, 321),
    "obj_rot_xyzw": slice(321, 325),
    "contact_obj": slice(330, 331),
    "contact_body": slice(331, 383),   # 52 flags: 1 contact, 0 none, -1 no data
    "body_rot_xyzw": slice(383, 591),  # 52 x 4, world
}

BODY_NAMES = [
    "Pelvis", "L_Hip", "L_Knee", "L_Ankle", "L_Toe", "R_Hip", "R_Knee", "R_Ankle", "R_Toe",
    "Torso", "Spine", "Chest", "Neck", "Head",
    "L_Thorax", "L_Shoulder", "L_Elbow", "L_Wrist",
    "L_Index1", "L_Index2", "L_Index3", "L_Middle1", "L_Middle2", "L_Middle3",
    "L_Pinky1", "L_Pinky2", "L_Pinky3", "L_Ring1", "L_Ring2", "L_Ring3", "L_Thumb1", "L_Thumb2", "L_Thumb3",
    "R_Thorax", "R_Shoulder", "R_Elbow", "R_Wrist",
    "R_Index1", "R_Index2", "R_Index3", "R_Middle1", "R_Middle2", "R_Middle3",
    "R_Pinky1", "R_Pinky2", "R_Pinky3", "R_Ring1", "R_Ring2", "R_Ring3", "R_Thumb1", "R_Thumb2", "R_Thumb3",
]
BODY_INDEX = {n: i for i, n in enumerate(BODY_NAMES)}
FINGERS = ["Index1", "Index2", "Index3", "Middle1", "Middle2", "Middle3", "Pinky1", "Pinky2", "Pinky3",
           "Ring1", "Ring2", "Ring3", "Thumb1", "Thumb2", "Thumb3"]
# A hand = its wrist body (the palm segment of the SMPL-X humanoid) + the 15 finger bodies.
HAND_BODIES = {s: [BODY_INDEX[f"{s}_Wrist"]] + [BODY_INDEX[f"{s}_{f}"] for f in FINGERS] for s in ("L", "R")}
NON_HAND_BODIES = [i for i in range(len(BODY_NAMES)) if i not in HAND_BODIES["L"] + HAND_BODIES["R"]]


def _parent(name: str) -> int:
    chain = {"L_Hip": "Pelvis", "R_Hip": "Pelvis", "Torso": "Pelvis", "Spine": "Torso", "Chest": "Spine",
             "Neck": "Chest", "Head": "Neck", "L_Thorax": "Chest", "R_Thorax": "Chest"}
    if name == "Pelvis":
        return -1
    if name in chain:
        return BODY_INDEX[chain[name]]
    side, part = name[:2], name[2:]
    limb = {"Knee": "Hip", "Ankle": "Knee", "Toe": "Ankle", "Shoulder": "Thorax", "Elbow": "Shoulder",
            "Wrist": "Elbow"}
    if part in limb:
        return BODY_INDEX[side + limb[part]]
    k = int(part[-1])                                   # finger segment 1..3
    return BODY_INDEX[side + "Wrist"] if k == 1 else BODY_INDEX[side + part[:-1] + str(k - 1)]


BODY_PARENTS = [_parent(n) for n in BODY_NAMES]

# Body groups for reporting (the SMPL-X humanoid link named after a joint is the segment distal to it:
# "Hip" = thigh, "Knee" = shin, "Shoulder" = upper arm, "Elbow" = forearm, "Wrist" = palm).
BODY_GROUPS = {
    "L_hand": HAND_BODIES["L"], "R_hand": HAND_BODIES["R"],
    "forearm": [BODY_INDEX["L_Elbow"], BODY_INDEX["R_Elbow"]],
    "upper_arm": [BODY_INDEX["L_Shoulder"], BODY_INDEX["R_Shoulder"]],
    "collar": [BODY_INDEX["L_Thorax"], BODY_INDEX["R_Thorax"]],
    "torso": [BODY_INDEX[n] for n in ("Torso", "Spine", "Chest")],
    "head_neck": [BODY_INDEX["Neck"], BODY_INDEX["Head"]],
    "pelvis": [BODY_INDEX["Pelvis"]],
    "thigh": [BODY_INDEX["L_Hip"], BODY_INDEX["R_Hip"]],
    "shin": [BODY_INDEX["L_Knee"], BODY_INDEX["R_Knee"]],
    "foot": [BODY_INDEX[n] for n in ("L_Ankle", "L_Toe", "R_Ankle", "R_Toe")],
}
NAME_RE = re.compile(r"^(?P<subject>sub\d+)_(?P<object>[a-z]+)_(?P<seq>\d+)$")

# InterMimic body frames are y-up; SMPL-X joint frames are z-up (permutation, per HOI-Retarget).
_YUP_TO_ZUP = R.from_matrix(np.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]))

# SMPL-X body joints 1..21 and their OMOMO names.
SMPLX_BODY_JOINTS = [
    "left_hip", "right_hip", "spine1", "left_knee", "right_knee", "spine2", "left_ankle", "right_ankle",
    "spine3", "left_foot", "right_foot", "neck", "left_collar", "right_collar", "head",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist",
]


def smplx_to_omomo_name(j: str) -> str:
    special = {"pelvis": "Pelvis", "spine1": "Torso", "spine2": "Spine", "spine3": "Chest",
               "neck": "Neck", "head": "Head"}
    if j in special:
        return special[j]
    side, _, part = j.partition("_")
    prefix = {"left": "L_", "right": "R_"}[side]
    part = {"foot": "Toe", "collar": "Thorax"}.get(part, part.capitalize())
    return prefix + part


@dataclass
class Clip:
    name: str
    subject: str | None
    obj: str | None
    root_pos: np.ndarray        # (T, 3)
    root_rot_xyzw: np.ndarray   # (T, 4)
    dof_pos: np.ndarray         # (T, 153)
    body_pos: np.ndarray        # (T, 52, 3)
    body_rot_xyzw: np.ndarray   # (T, 52, 4)
    obj_pos: np.ndarray         # (T, 3)
    obj_rot_xyzw: np.ndarray    # (T, 4)
    contact_obj: np.ndarray     # (T,) int
    contact_body: np.ndarray    # (T, 52) int in {-1, 0, 1}
    dropped_first_frame: bool
    fps: float = FPS

    @property
    def n(self) -> int:
        return int(self.root_pos.shape[0])


def _unit(q: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(q, axis=-1, keepdims=True)
    return q / np.where(n > 1e-12, n, 1.0)


def parse_array(a: np.ndarray, name: str = "clip") -> Clip:
    a = np.asarray(a, dtype=np.float32)
    if a.ndim != 2 or a.shape[1] != DIM:
        raise ValueError(f"{name}: expected [T, {DIM}], got {a.shape}")
    dropped = bool(np.allclose(a[0], 0.0))
    if dropped:
        a = a[1:]
    T = a.shape[0]
    m = NAME_RE.match(name)
    return Clip(
        name=name,
        subject=m["subject"] if m else None,
        obj=m["object"] if m else None,
        root_pos=a[:, SLICES["root_pos"]].astype(np.float64),
        root_rot_xyzw=_unit(a[:, SLICES["root_rot_xyzw"]].astype(np.float64)),
        dof_pos=a[:, SLICES["dof_pos"]].astype(np.float64),
        body_pos=a[:, SLICES["body_pos"]].reshape(T, 52, 3).astype(np.float64),
        body_rot_xyzw=_unit(a[:, SLICES["body_rot_xyzw"]].reshape(T, 52, 4).astype(np.float64)),
        obj_pos=a[:, SLICES["obj_pos"]].astype(np.float64),
        obj_rot_xyzw=_unit(a[:, SLICES["obj_rot_xyzw"]].astype(np.float64)),
        contact_obj=np.round(a[:, SLICES["contact_obj"]]).astype(np.int32).reshape(-1),
        contact_body=np.round(a[:, SLICES["contact_body"]]).astype(np.int32),
        dropped_first_frame=dropped,
    )


def load_clip(path: str | Path) -> Clip:
    import torch

    path = Path(path)
    payload = torch.load(path, map_location="cpu", weights_only=True)
    if isinstance(payload, dict):
        payload = payload.get("hoi_data", payload)
    arr = payload.detach().cpu().numpy() if hasattr(payload, "detach") else np.asarray(payload)
    return parse_array(arr, path.stem)


# ----------------------------------------------------------------------------- contacts
def hand_contact(clip: Clip) -> np.ndarray:
    """(T, 2) bool: any body of the left / right hand (wrist/palm or finger) flagged in contact."""
    c = clip.contact_body == 1
    return np.stack([c[:, HAND_BODIES["L"]].any(1), c[:, HAND_BODIES["R"]].any(1)], axis=1)


def body_contact(clip: Clip) -> np.ndarray:
    """(T,) bool: any non-hand body (feet, legs, torso, forearms and above) in contact."""
    return (clip.contact_body[:, NON_HAND_BODIES] == 1).any(1)


def no_data(clip: Clip) -> np.ndarray:
    """(T,) bool: every per-body flag is -1."""
    return (clip.contact_body == -1).all(1)


def remove_short_runs(mask: np.ndarray, min_len: int) -> np.ndarray:
    """Drop True runs shorter than min_len frames."""
    out = mask.copy()
    for s, e in intervals(mask):
        if e - s < min_len:
            out[s:e] = False
    return out


def intervals(mask: np.ndarray) -> list[tuple[int, int]]:
    """Half-open [start, end) runs of True."""
    m = np.concatenate([[False], np.asarray(mask, bool), [False]])
    d = np.diff(m.astype(np.int8))
    return list(zip(np.flatnonzero(d == 1).tolist(), np.flatnonzero(d == -1).tolist()))


MODES = ("none", "left", "right", "both", "body", "unknown")


def contact_modes(clip: Clip, min_sec: float = 0.2) -> np.ndarray:
    """Per-frame mode from the contact flags (spec §5.1).

    unknown: all flags -1. body: a non-hand body touches the object (whatever the hands do; such
    frames are outside the course scope). Otherwise none / left / right / both from the hand flags,
    after removing contact runs shorter than ``min_sec``. Same-face vs opposing two-hand contact needs
    the object mesh and is decided later.
    """
    k = max(1, int(round(min_sec * clip.fps)))
    h = hand_contact(clip)
    L = remove_short_runs(h[:, 0], k)
    Rr = remove_short_runs(h[:, 1], k)
    mode = np.full(clip.n, "none", dtype=object)
    mode[L & ~Rr] = "left"
    mode[Rr & ~L] = "right"
    mode[L & Rr] = "both"
    mode[remove_short_runs(body_contact(clip), k)] = "body"
    mode[no_data(clip)] = "unknown"
    return mode


# ------------------------------------------------------------------------------- SMPL-X
def smplx_params(clip: Clip) -> dict:
    """SMPL-X parameters (mean shape, neutral) for the GMR prior input."""
    root_orient = (R.from_quat(clip.root_rot_xyzw) * _YUP_TO_ZUP).as_rotvec()
    pose_body = np.zeros((clip.n, 63))
    for i, j in enumerate(SMPLX_BODY_JOINTS):
        k = BODY_INDEX[smplx_to_omomo_name(j)] - 1          # dof_pos excludes the pelvis
        pose_body[:, 3 * i:3 * i + 3] = clip.dof_pos[:, 3 * k:3 * k + 3][:, [1, 2, 0]]
    return {
        "gender": np.array("neutral"),
        "betas": np.zeros(16, dtype=np.float32),            # mean shape; smplx builds SMPL-X with 16 betas
        "mocap_frame_rate": np.array(clip.fps, dtype=np.float32),
        "trans": clip.root_pos.astype(np.float32),
        "root_orient": root_orient.astype(np.float32),
        "pose_body": pose_body.astype(np.float32),
    }
