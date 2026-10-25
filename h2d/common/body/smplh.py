"""SMPL-H body model in plain numpy: loading without chumpy, forward kinematics, skinning.

Model files are licensed downloads (MANO website, "Models & Code": ``mano_v1_2/models/SMPLH_{male,female}.pkl``)
and are never committed. The MANO pickles store some arrays as chumpy objects; chumpy does not import
under numpy >= 1.24, so ``load_model`` unpickles them through a stub that keeps the stored ``x`` array.
An ``.npz`` export with the same keys is also accepted.

Joint order (52): the 22 SMPL body joints, then 15 left-hand and 15 right-hand joints
(index, middle, pinky, ring, thumb; segments 1-3), as in SMPL-X without jaw and eyes.
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from scipy.spatial.transform import Rotation as R

BODY_JOINTS = [
    "pelvis", "left_hip", "right_hip", "spine1", "left_knee", "right_knee", "spine2", "left_ankle", "right_ankle",
    "spine3", "left_foot", "right_foot", "neck", "left_collar", "right_collar", "head", "left_shoulder",
    "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist",
]
_FINGERS = ["index", "middle", "pinky", "ring", "thumb"]
JOINT_NAMES = BODY_JOINTS + [f"{s}_{f}{k}" for s in ("left", "right") for f in _FINGERS for k in (1, 2, 3)]
REQUIRED = ("v_template", "shapedirs", "posedirs", "J_regressor", "weights", "kintree_table", "f")


class _ChumpyStub:
    """Stands in for any chumpy class while unpickling; chumpy pickles an object's ``__dict__``."""

    def __setstate__(self, state):
        self.__dict__.update(state if isinstance(state, dict) else {"state": state})


class _SparseStub:
    """Stands in for scipy sparse matrices pickled by old scipy versions (module paths changed since)."""

    def __init__(self, *args, **kwargs):
        pass

    def __setstate__(self, state):
        self.__dict__.update(state)


class _Unpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module.split(".")[0] == "chumpy":
            return _ChumpyStub
        if module.startswith("scipy.sparse") and name.endswith("_matrix"):
            return _SparseStub
        return super().find_class(module, name)


def _plain(v):
    if isinstance(v, _ChumpyStub):
        if "x" in v.__dict__:
            return _plain(v.__dict__["x"])
        raise ValueError(f"chumpy object without a stored 'x' (keys {sorted(v.__dict__)})")
    if isinstance(v, _SparseStub):
        d = v.__dict__
        shape = tuple(d.get("_shape") or d.get("shape"))
        fmt = d.get("format", "csc")
        cls = {"csc": sp.csc_matrix, "csr": sp.csr_matrix}[fmt if fmt in ("csc", "csr") else "csc"]
        return cls((np.asarray(d["data"]), np.asarray(d["indices"]), np.asarray(d["indptr"])), shape=shape).tocsr()
    if sp.issparse(v):
        return v.tocsr()
    return np.asarray(v) if isinstance(v, (list, tuple, np.ndarray)) else v


def load_raw(path: str | Path) -> dict:
    path = Path(path)
    if path.suffix == ".npz":
        d = dict(np.load(path, allow_pickle=True))
    else:
        with open(path, "rb") as f:
            d = _Unpickler(f, encoding="latin1").load()
    return {k: _plain(v) for k, v in d.items()}


@dataclass
class SMPLH:
    v_template: np.ndarray      # (V, 3)
    shapedirs: np.ndarray       # (V, 3, B)
    posedirs: np.ndarray        # (V, 3, 9 * (J - 1))
    J_regressor: sp.csr_matrix  # (J, V)
    weights: np.ndarray         # (V, J)
    parents: np.ndarray         # (J,), -1 for the root
    faces: np.ndarray           # (F, 3)
    path: str = ""

    @property
    def n_joints(self) -> int:
        return int(self.weights.shape[1])

    def vertex_joint(self) -> np.ndarray:
        """Dominant skinning joint per vertex, (V,)."""
        return np.argmax(self.weights, axis=1)

    # ------------------------------------------------------------------ kinematics
    def rest_joints(self, betas: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        b = np.zeros(self.shapedirs.shape[2])
        betas = np.asarray(betas, float).reshape(-1)[: len(b)]
        b[: len(betas)] = betas
        v = self.v_template + self.shapedirs @ b
        return v, np.asarray(self.J_regressor @ v)

    def forward(self, pose: np.ndarray, trans: np.ndarray, betas: np.ndarray, vertices: bool = False,
                vertex_ids: np.ndarray | None = None, chunk: int = 128) -> dict:
        """pose (T, 3J) axis-angle (root first), trans (T, 3) -> joints (T, J, 3), joint rotations (T, J, 3, 3),
        and optionally skinned vertices (T, V', 3) for ``vertex_ids`` (default all), with pose blend shapes."""
        T, J = len(pose), self.n_joints
        Rm = R.from_rotvec(np.asarray(pose, float).reshape(-1, 3)).as_matrix().reshape(T, J, 3, 3)
        v_rest, Jr = self.rest_joints(betas)
        G = np.zeros((T, J, 4, 4))
        G[:, :, 3, 3] = 1.0
        for j in range(J):
            p = self.parents[j]
            local = np.zeros((T, 4, 4))
            local[:, :3, :3] = Rm[:, j]
            local[:, :3, 3] = Jr[j] - (Jr[p] if p >= 0 else 0.0)
            local[:, 3, 3] = 1.0
            G[:, j] = local if p < 0 else G[:, p] @ local
        trans = np.asarray(trans, float).reshape(T, 3)
        out = {"joints": G[:, :, :3, 3] + trans[:, None], "rotations": G[:, :, :3, :3]}
        if vertices:
            ids = np.arange(len(v_rest)) if vertex_ids is None else np.asarray(vertex_ids)
            P = self.posedirs[ids].reshape(-1, self.posedirs.shape[2])          # (3V', 9(J-1))
            W = self.weights[ids]                                                # (V', J)
            A = G.copy()                                                         # remove rest joint offsets
            A[:, :, :3, 3] -= np.einsum("tjab,jb->tja", G[:, :, :3, :3], Jr)
            verts = np.empty((T, len(ids), 3))
            for s in range(0, T, chunk):                                          # bounded memory, BLAS matmuls
                e = min(T, s + chunk)
                feat = (Rm[s:e, 1:] - np.eye(3)).reshape(e - s, -1)              # (t, 9(J-1))
                v_posed = v_rest[ids][None] + (P @ feat.T).T.reshape(e - s, len(ids), 3)
                M = np.matmul(W, A[s:e].reshape(e - s, J, 16)).reshape(e - s, len(ids), 4, 4)
                verts[s:e] = np.einsum("tvab,tvb->tva", M[..., :3, :3], v_posed) + M[..., :3, 3]
            out["vertices"] = verts + trans[:, None]
        return out


def load_model(path: str | Path) -> SMPLH:
    d = load_raw(path)
    missing = [k for k in REQUIRED if k not in d]
    if missing:
        raise KeyError(f"{path}: missing keys {missing}; found {sorted(d)}")
    kt = np.asarray(d["kintree_table"]).astype(np.int64)
    parents = kt[0].copy()
    parents[0] = -1
    J_reg = d["J_regressor"]
    J_reg = J_reg if sp.issparse(J_reg) else sp.csr_matrix(np.asarray(J_reg))
    return SMPLH(
        v_template=np.asarray(d["v_template"], float), shapedirs=np.asarray(d["shapedirs"], float),
        posedirs=np.asarray(d["posedirs"], float), J_regressor=J_reg, weights=np.asarray(d["weights"], float),
        parents=parents, faces=np.asarray(d["f"]).astype(np.int64), path=str(path),
    )


def describe_file(path: str | Path) -> dict:
    """Shapes and types of a model file's entries (for run reports; no model data)."""
    d = load_raw(path)
    out = {}
    for k, v in d.items():
        if sp.issparse(v) or isinstance(v, np.ndarray):
            out[k] = {"shape": list(v.shape), "type": type(v).__name__}
        else:
            out[k] = {"type": type(v).__name__}
    return out
