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
    """Stands in for any chumpy class while unpickling; chumpy pickles an object's ``__dict__``.
    ``_kind`` is the pickled class name (Ch, Select, Reshape, transpose, ...)."""

    _kind = "Ch"

    def __setstate__(self, state):
        self.__dict__.update(state if isinstance(state, dict) else {"state": state})


_CHUMPY_STUBS: dict[str, type] = {}


def _chumpy_value(v):
    """Evaluate a pickled chumpy expression the way chumpy's ``compute_r`` would (leaf ``Ch`` objects hold ``x``;
    reordering ops are recomputed from their stored operand ``a`` and terms)."""
    if not isinstance(v, _ChumpyStub):
        return np.asarray(v)
    d, kind = v.__dict__, v._kind
    if "a" not in d:
        if "x" in d:
            return np.asarray(_chumpy_value(d["x"]))
        raise UnconvertibleEntry(f"chumpy {kind} without a stored 'x' or 'a' (fields {sorted(d)})")
    a = _chumpy_value(d["a"])
    ops = {
        "Select": lambda: (a.ravel()[_chumpy_value(d["idxs"]).astype(np.int64).ravel()].reshape(d["preferred_shape"])
                           if "preferred_shape" in d else a.ravel()[_chumpy_value(d["idxs"]).astype(np.int64)]),
        "Reshape": lambda: a.reshape(d["newshape"]),
        "transpose": lambda: np.transpose(a, axes=d.get("axes")),
        "swapaxes": lambda: np.swapaxes(a, d["axis1"], d["axis2"]),
        "rollaxis": lambda: np.rollaxis(a, d["axis"], d.get("start", 0)),
        "Tile": lambda: np.tile(a, d["reps"]),
        "Repeat": lambda: np.repeat(a, d["repeats"], d.get("axis")),
        "Roll": lambda: np.roll(a, d["shift"], d.get("axis")),
        "Diag": lambda: np.diag(a, d.get("k", 0)),
        "DiagFlat": lambda: np.diagflat(a, d.get("k", 0)),
        "Rot90": lambda: np.rot90(a, d.get("k", 1)),
    }
    if kind not in ops:
        raise UnconvertibleEntry(f"chumpy {kind} is not supported (fields {sorted(d)})")
    return np.asarray(ops[kind]())


class _SparseStub:
    """Stands in for scipy sparse matrices pickled by old scipy versions (module paths and attribute names
    changed since). ``_kind`` is the pickled class name (csc_matrix, coo_matrix, ...)."""

    _kind = "sparse"

    def __init__(self, *args, **kwargs):
        pass

    def __setstate__(self, state):
        if isinstance(state, tuple) and len(state) == 2:          # (dict state, slot state)
            state = {**(state[0] or {}), **(state[1] or {})}
        self.__dict__.update(state)


_SPARSE_STUBS: dict[str, type] = {}


class _Unpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module.split(".")[0] == "chumpy":
            if name not in _CHUMPY_STUBS:
                _CHUMPY_STUBS[name] = type(f"_Chumpy_{name}", (_ChumpyStub,), {"_kind": name})
            return _CHUMPY_STUBS[name]
        if module.startswith("scipy.sparse") and name.endswith("_matrix"):
            if name not in _SPARSE_STUBS:
                _SPARSE_STUBS[name] = type(f"_Stub_{name}", (_SparseStub,), {"_kind": name})
            return _SPARSE_STUBS[name]
        return super().find_class(module, name)


class UnconvertibleEntry(ValueError):
    pass


def _sparse_from_state(kind: str, d: dict) -> sp.csr_matrix:
    """Rebuild a sparse matrix from a pickled ``__dict__`` across scipy versions."""
    shape = d.get("_shape", d.get("shape"))
    shape = tuple(int(x) for x in shape) if shape is not None else None
    data = np.asarray(d["data"]) if "data" in d else None
    fmt = d.get("format") or kind.split("_")[0]
    if data is not None and "indptr" in d:
        idx = next((d[k] for k in ("indices", "rowind", "colind") if k in d), None)
        if idx is not None:
            cls = sp.csr_matrix if fmt == "csr" or "colind" in d else sp.csc_matrix
            return cls((data, np.asarray(idx), np.asarray(d["indptr"])), shape=shape).tocsr()
    if data is not None and "row" in d and "col" in d:
        return sp.coo_matrix((data, (np.asarray(d["row"]), np.asarray(d["col"]))), shape=shape).tocsr()
    if data is not None and "offsets" in d:                        # dia
        return sp.dia_matrix((data, np.asarray(d["offsets"])), shape=shape).tocsr()
    if "rows" in d and data is not None:                          # lil: object arrays of lists
        m = sp.lil_matrix(shape)
        m.rows, m.data = np.asarray(d["rows"], dtype=object), np.asarray(d["data"], dtype=object)
        return m.tocsr()
    raise UnconvertibleEntry(f"cannot rebuild {kind} from pickled fields {sorted(d)}")


def _plain(v):
    if isinstance(v, _ChumpyStub):
        return _chumpy_value(v)
    if isinstance(v, _SparseStub):
        return _sparse_from_state(v._kind, v.__dict__)
    if sp.issparse(v):
        return v.tocsr()
    return np.asarray(v) if isinstance(v, (list, tuple, np.ndarray)) else v


def load_raw(path: str | Path, strict: tuple[str, ...] = REQUIRED) -> dict:
    """All entries as numpy / scipy objects. Entries in ``strict`` must convert; any other entry that cannot be
    converted is kept as an ``UnconvertibleEntry`` (the model needs only ``REQUIRED``)."""
    path = Path(path)
    if path.suffix == ".npz":
        d = dict(np.load(path, allow_pickle=True))
    else:
        with open(path, "rb") as f:
            d = _Unpickler(f, encoding="latin1").load()
    out = {}
    for k, v in d.items():
        try:
            out[k] = _plain(v)
        except (UnconvertibleEntry, KeyError, TypeError, ValueError) as e:
            if k in strict:
                raise UnconvertibleEntry(f"{path.name}: required entry '{k}': {e}") from e
            out[k] = UnconvertibleEntry(str(e))
    return out


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
        and optionally skinned vertices (T, V', 3) for ``vertex_ids`` (default all), with pose blend shapes.
        The result also carries what ``skin`` needs to skin any vertex subset at any frame subset later."""
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
        A = G.copy()                                                             # remove rest joint offsets
        A[:, :, :3, 3] -= np.einsum("tjab,jb->tja", G[:, :, :3, :3], Jr)
        out = {"joints": G[:, :, :3, 3] + trans[:, None], "rotations": G[:, :, :3, :3],
               "_A": A, "_feat": (Rm[:, 1:] - np.eye(3)).reshape(T, -1), "_trans": trans, "_v_rest": v_rest}
        if vertices:
            ids = np.arange(len(v_rest)) if vertex_ids is None else np.asarray(vertex_ids)
            out["vertices"] = np.concatenate([self.skin(out, np.arange(s, min(T, s + chunk)), ids)
                                              for s in range(0, T, chunk)]) if T else np.zeros((0, len(ids), 3))
        return out

    def skin(self, fk: dict, frames: np.ndarray, ids: np.ndarray) -> np.ndarray:
        """Skinned vertices ``ids`` at ``frames`` of a ``forward`` result, (len(frames), len(ids), 3)."""
        frames, ids = np.asarray(frames), np.asarray(ids)
        J = self.n_joints
        P = self.posedirs[ids].reshape(-1, self.posedirs.shape[2])              # (3V', 9(J-1))
        v_posed = fk["_v_rest"][ids][None] + (P @ fk["_feat"][frames].T).T.reshape(len(frames), len(ids), 3)
        M = np.matmul(self.weights[ids], fk["_A"][frames].reshape(len(frames), J, 16))
        M = M.reshape(len(frames), len(ids), 4, 4)
        return np.einsum("tvab,tvb->tva", M[..., :3, :3], v_posed) + M[..., :3, 3] + fk["_trans"][frames][:, None]


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
    """Shapes and types of a model file's entries (for run reports; no model data). Never raises on an entry:
    an entry that cannot be converted is reported with its pickled class and field names."""
    d = load_raw(path, strict=())
    out = {}
    for k, v in d.items():
        if sp.issparse(v) or isinstance(v, np.ndarray):
            out[k] = {"shape": list(v.shape), "type": type(v).__name__}
        elif isinstance(v, UnconvertibleEntry):
            out[k] = {"type": "UNCONVERTIBLE", "detail": str(v)}
        else:
            out[k] = {"type": type(v).__name__}
    return out
