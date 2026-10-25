"""A crude stand-in for the licensed SMPL-H model: an approximate SMPL rest skeleton (y-up, T-pose, facing +z,
subject's left = +x) with point 'vertices' along each bone. For tests and dry runs only; real runs use
SMPLH_{male,female}.pkl."""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from h2d.common.body.smplh import JOINT_NAMES, SMPLH

_OFF = {  # joint: (parent, offset from parent) [m]; the pelvis rests at (0, -0.22, 0.03) as in SMPL, not at 0
    "pelvis": (None, (0.0, -0.22, 0.03)), "spine1": ("pelvis", (0, 0.11, -0.01)), "spine2": ("spine1", (0, 0.13, 0)),
    "spine3": ("spine2", (0, 0.05, 0)), "neck": ("spine3", (0, 0.21, -0.03)), "head": ("neck", (0, 0.09, 0.05)),
}
for s, x in (("left", 1.0), ("right", -1.0)):
    _OFF.update({
        f"{s}_hip": ("pelvis", (0.06 * x, -0.09, 0)), f"{s}_knee": (f"{s}_hip", (0, -0.38, 0)),
        f"{s}_ankle": (f"{s}_knee", (0, -0.40, -0.04)), f"{s}_foot": (f"{s}_ankle", (0, -0.06, 0.12)),
        f"{s}_collar": ("spine3", (0.07 * x, 0.12, 0)), f"{s}_shoulder": (f"{s}_collar", (0.12 * x, 0.04, 0)),
        f"{s}_elbow": (f"{s}_shoulder", (0.25 * x, 0, 0)), f"{s}_wrist": (f"{s}_elbow", (0.25 * x, 0, 0)),
    })
    for f, (dz, dx) in {"index": (0.02, 0.09), "middle": (0.0, 0.095), "pinky": (-0.04, 0.08), "ring": (-0.02, 0.09),
                        "thumb": (0.04, 0.03)}.items():
        _OFF[f"{s}_{f}1"] = (f"{s}_wrist", (dx * x, -0.005, dz))
        _OFF[f"{s}_{f}2"] = (f"{s}_{f}1", (0.03 * x, 0, 0))
        _OFF[f"{s}_{f}3"] = (f"{s}_{f}2", (0.025 * x, 0, 0))


def fake_smplh(points_per_joint: int = 24, seed: int = 0) -> SMPLH:
    J = len(JOINT_NAMES)
    parents = np.array([-1 if _OFF[n][0] is None else JOINT_NAMES.index(_OFF[n][0]) for n in JOINT_NAMES])
    rest = np.zeros((J, 3))
    for j, n in enumerate(JOINT_NAMES):
        rest[j] = (rest[parents[j]] if parents[j] >= 0 else 0) + np.array(_OFF[n][1], float)
    children = {j: [k for k in range(J) if parents[k] == j] for j in range(J)}
    rng = np.random.default_rng(seed)
    V, W = [], []
    for j in range(J):
        end = rest[children[j][0]] if children[j] else rest[j] + (rest[j] - rest[parents[j]]) * 0.5
        small = "_" in JOINT_NAMES[j] and JOINT_NAMES[j][-1].isdigit()
        r = 0.008 if small else 0.04
        t = rng.random(points_per_joint)[:, None]
        V.append(rest[j] + t * (end - rest[j]) + rng.normal(size=(points_per_joint, 3)) * r)
        W += [j] * points_per_joint
    V = np.concatenate(V)
    Wm = np.zeros((len(V), J))
    Wm[np.arange(len(V)), W] = 1.0
    A = np.zeros((J, len(V)))             # J_regressor: joint = mean of its points
    for j in range(J):
        idx = np.flatnonzero(np.array(W) == j)
        A[j, idx] = 1.0 / len(idx)
    corr = rest - A @ V
    V2 = V.copy()
    for j in range(J):                    # shift each joint's points so their mean is the joint
        V2[np.array(W) == j] += corr[j]
    return SMPLH(v_template=V2, shapedirs=np.zeros((len(V2), 3, 10)), posedirs=np.zeros((len(V2), 3, 9 * (J - 1))),
                 J_regressor=sp.csr_matrix(A), weights=Wm, parents=parents, faces=np.zeros((0, 3), np.int64),
                 path="fake")
