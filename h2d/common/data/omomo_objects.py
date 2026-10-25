"""OMOMO object meshes and object-pose helpers.

Meshes: the 13 InterMimic re-exports of the OMOMO objects that HOI-Retarget ships under MIT
(leggedrobotics/hoi-retarget, ``assets/objects/objects/<name>/<name>.obj``, see its LICENSE-OBJECTS).
They are in the object frame that OMOMO_new's ``obj_pos`` / ``obj_rot`` refer to: HOI-Retarget applies
the recorded pose to them directly, and ``scripts/common/profile_omomo.py`` checks it on our copy
(recorded contact bodies must lie on the transformed surface).

The local frame is not upright in general (e.g. the floor lamp's long axis is local x), so tilt and
yaw are measured relative to the object's own pose at a reference frame, never against local z.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull, cKDTree
from scipy.spatial.transform import Rotation as R

from h2d.common.meshgeom import closest_points_on_triangles
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


def load_obj(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Vertices (N, 3) and triangle indices (M, 3) of a Wavefront OBJ (``f a/b/c ...`` fan-triangulated)."""
    verts, faces = [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("v "):
                verts.append([float(x) for x in line.split()[1:4]])
            elif line.startswith("f "):
                idx = [int(tok.split("/")[0]) for tok in line.split()[1:]]
                idx = [i - 1 if i > 0 else len(verts) + i for i in idx]
                for k in range(1, len(idx) - 1):
                    faces.append([idx[0], idx[k], idx[k + 1]])
    return np.asarray(verts, np.float64), np.asarray(faces, np.int64)


@dataclass
class ObjectMesh:
    name: str
    verts: np.ndarray            # (N, 3) local
    faces: np.ndarray            # (M, 3)
    _cache: dict = field(default_factory=dict, repr=False)

    # ------------------------------------------------------------------ static geometry
    @property
    def hull_verts(self) -> np.ndarray:
        """Convex-hull vertices (the lowest point of any pose is one of them)."""
        if "hull" not in self._cache:
            self._cache["hull"] = self.verts[ConvexHull(self.verts).vertices]
        return self._cache["hull"]

    @property
    def extents(self) -> np.ndarray:
        """Bounding-box side lengths of the local frame, sorted descending [m]."""
        return np.sort(self.verts.max(0) - self.verts.min(0))[::-1]

    @property
    def tree(self) -> cKDTree:
        if "tree" not in self._cache:
            self._cache["tree"] = cKDTree(self.verts)
        return self._cache["tree"]

    @property
    def vert_faces(self) -> tuple[np.ndarray, np.ndarray]:
        """CSR adjacency vertex -> incident faces: (offsets (N+1,), face ids)."""
        if "vf" not in self._cache:
            v = self.faces.reshape(-1)
            f = np.repeat(np.arange(len(self.faces)), 3)
            order = np.argsort(v, kind="stable")
            counts = np.bincount(v, minlength=len(self.verts))
            self._cache["vf"] = (np.concatenate([[0], np.cumsum(counts)]), f[order])
        return self._cache["vf"]

    # ------------------------------------------------------------------ poses
    @staticmethod
    def to_local(points_world: np.ndarray, pos: np.ndarray, rot_xyzw: np.ndarray) -> np.ndarray:
        """World points (T, K, 3) at object poses (T, 3), (T, 4) -> local frame (T, K, 3)."""
        Rm = R.from_quat(np.asarray(rot_xyzw).reshape(-1, 4)).as_matrix()      # world <- local
        P = np.asarray(points_world, np.float64) - np.asarray(pos, np.float64).reshape(-1, 1, 3)
        return np.einsum("tji,tkj->tki", Rm, P)

    def world_points(self, pos: np.ndarray, rot_xyzw: np.ndarray, local: np.ndarray | None = None) -> np.ndarray:
        """Local points (default all vertices) at one pose -> world (K, 3)."""
        local = self.verts if local is None else local
        return R.from_quat(rot_xyzw).apply(local) + np.asarray(pos)

    def lowest_z(self, pos: np.ndarray, rot_xyzw: np.ndarray) -> np.ndarray:
        """World height of the object's lowest point per frame, (T,)."""
        Rm = R.from_quat(np.asarray(rot_xyzw).reshape(-1, 4)).as_matrix()      # (T, 3, 3)
        z = np.einsum("tj,kj->tk", Rm[:, 2, :], self.hull_verts)                # row 2 = world z
        return z.min(1) + np.asarray(pos).reshape(-1, 3)[:, 2]

    def surface_distance(self, p_local: np.ndarray, k: int = 12, exact_below: float = 0.15) -> np.ndarray:
        """Unsigned distance of local points (K, 3) to the mesh surface.

        Exact (point-triangle) over the faces incident to the k nearest vertices for points within
        ``exact_below`` of a vertex; beyond that the nearest-vertex distance (an upper bound) is returned.
        """
        p = np.asarray(p_local, np.float64).reshape(-1, 3)
        d_vert, idx = self.tree.query(p, k=k)
        out = d_vert[:, 0].copy()
        near = np.flatnonzero(d_vert[:, 0] < exact_below)
        if len(near) == 0:
            return out
        for i in near:
            out[i] = self._exact(p[i], idx[i])
        return out

    def min_surface_distance(self, p_local: np.ndarray, top: int = 3, k: int = 12) -> float:
        """Smallest surface distance over a set of local points (K, 3); exact for the ``top`` points
        closest by nearest-vertex distance (exact <= vertex distance, vertices ~1 cm apart)."""
        p = np.asarray(p_local, np.float64).reshape(-1, 3)
        d_vert, idx = self.tree.query(p, k=k)
        order = np.argsort(d_vert[:, 0])[:top]
        return float(min(self._exact(p[i], idx[i]) for i in order))

    def _exact(self, p: np.ndarray, vert_ids: np.ndarray) -> float:
        off, fid = self.vert_faces
        cand = np.unique(np.concatenate([fid[off[j]:off[j + 1]] for j in vert_ids]))
        q = closest_points_on_triangles(p, self.verts[self.faces[cand]])
        return float(np.min(np.linalg.norm(q - p, axis=1)))


@lru_cache(maxsize=None)
def load_object(name: str) -> ObjectMesh:
    v, f = load_obj(object_mesh_path(name))
    return ObjectMesh(name, v, f)


# ----------------------------------------------------------------------- relative object motion
def tilt_and_yaw(rot_xyzw: np.ndarray, ref: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Per-frame tilt [deg] and unwrapped yaw change [deg] relative to the pose at frame ``ref``.

    The relative world rotation D_t = R_t R_ref^-1 is split into a tilt (angle between D_t z and z)
    and a rotation about world z (swing-twist split, twist about z).
    """
    Rt = R.from_quat(rot_xyzw)
    D = Rt * Rt[ref].inv()
    z = D.apply([0.0, 0.0, 1.0])
    tilt = np.degrees(np.arccos(np.clip(z[:, 2], -1.0, 1.0)))
    q = D.as_quat()                                   # xyzw
    twist = 2.0 * np.arctan2(q[:, 2], q[:, 3])        # rotation about z of the twist part
    yaw = np.degrees(np.unwrap(twist))
    return tilt, yaw - yaw[ref]
