"""Rigid object meshes: loading (OBJ, PLY), pose helpers, lowest point, distances to the surface.

Used by every dataset adapter (OMOMO_new meshes are dense, ~30-70k faces; FORCE scans are coarse,
~1-8k faces), so surface queries go through area-weighted surface samples that remember their face:
the nearest samples give the candidate faces for an exact point-triangle distance, and the
nearest-sample distance alone is a fast approximation (error below the sample spacing).

The local frame is not upright in general (e.g. the OMOMO floor lamp's long axis is local x), so
tilt and yaw are measured relative to the object's own pose at a reference frame, never against local z.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull, cKDTree
from scipy.spatial.transform import Rotation as R

from h2d.common.meshgeom import closest_points_on_triangles


# ----------------------------------------------------------------------------- file formats
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


_PLY_TYPES = {"char": "i1", "int8": "i1", "uchar": "u1", "uint8": "u1", "short": "i2", "int16": "i2",
              "ushort": "u2", "uint16": "u2", "int": "i4", "int32": "i4", "uint": "u4", "uint32": "u4",
              "float": "f4", "float32": "f4", "double": "f8", "float64": "f8"}


def load_ply(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Vertices and triangles of a PLY file (ascii or binary_little_endian; polygons fan-triangulated)."""
    raw = Path(path).read_bytes()
    end = raw.index(b"end_header") + len(b"end_header")
    end = raw.index(b"\n", end) + 1
    header = raw[:end].decode("ascii", "replace").splitlines()
    fmt, elements = None, []
    for line in header:
        tok = line.split()
        if not tok:
            continue
        if tok[0] == "format":
            fmt = tok[1]
        elif tok[0] == "element":
            elements.append({"name": tok[1], "count": int(tok[2]), "props": []})
        elif tok[0] == "property":
            elements[-1]["props"].append(("list", tok[2], tok[3], tok[4]) if tok[1] == "list" else (tok[1], tok[2]))
    if fmt not in ("ascii", "binary_little_endian"):
        raise ValueError(f"{path}: unsupported PLY format {fmt}")
    body = raw[end:]
    verts = faces = None
    if fmt == "ascii":
        lines = body.decode("ascii").split("\n")
        pos = 0
        for el in elements:
            rows = lines[pos:pos + el["count"]]
            pos += el["count"]
            if el["name"] == "vertex":
                names = [p[1] for p in el["props"]]
                arr = np.array([[float(x) for x in r.split()[: len(names)]] for r in rows])
                verts = arr[:, [names.index("x"), names.index("y"), names.index("z")]]
            elif el["name"] == "face":
                faces = [[int(x) for x in r.split()[1: 1 + int(r.split()[0])]] for r in rows]
    else:
        off = 0
        for el in elements:
            if el["name"] == "vertex":
                dt = np.dtype([(p[1], "<" + _PLY_TYPES[p[0]]) for p in el["props"]])
                arr = np.frombuffer(body, dtype=dt, count=el["count"], offset=off)
                off += dt.itemsize * el["count"]
                verts = np.stack([arr["x"], arr["y"], arr["z"]], 1).astype(np.float64)
            elif el["name"] == "face":
                (_, ct, it, _), = [p for p in el["props"] if p[0] == "list"]
                ct, it = np.dtype("<" + _PLY_TYPES[ct]), np.dtype("<" + _PLY_TYPES[it])
                faces = []
                for _ in range(el["count"]):
                    n = int(np.frombuffer(body, ct, 1, off)[0])
                    off += ct.itemsize
                    faces.append(np.frombuffer(body, it, n, off).tolist())
                    off += it.itemsize * n
            else:
                raise ValueError(f"{path}: element {el['name']} before vertex/face is not supported")
    tris = [[f[0], f[k], f[k + 1]] for f in faces for k in range(1, len(f) - 1)]
    return np.asarray(verts, np.float64), np.asarray(tris, np.int64)


# ----------------------------------------------------------------------------- mesh
@dataclass
class ObjectMesh:
    name: str
    verts: np.ndarray            # (N, 3) local
    faces: np.ndarray            # (M, 3)
    sample_spacing: float = 0.005
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
    def area(self) -> float:
        t = self.verts[self.faces]
        return float(0.5 * np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1).sum())

    def _samples(self) -> tuple[np.ndarray, np.ndarray, cKDTree]:
        """Surface samples (vertices + area-weighted random points, ~``sample_spacing`` apart) with face ids."""
        if "samples" not in self._cache:
            t = self.verts[self.faces]
            a = 0.5 * np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1)
            n = int(min(400_000, max(5_000, a.sum() / self.sample_spacing ** 2)))
            rng = np.random.default_rng(0)
            fid = rng.choice(len(a), size=n, p=a / a.sum())
            u, v = rng.random(n), rng.random(n)
            flip = u + v > 1
            u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
            pts = t[fid, 0] + u[:, None] * (t[fid, 1] - t[fid, 0]) + v[:, None] * (t[fid, 2] - t[fid, 0])
            vfid = np.zeros(len(self.verts), np.int64)                 # one incident face per vertex
            vfid[self.faces.reshape(-1)] = np.repeat(np.arange(len(self.faces)), 3)
            used = np.zeros(len(self.verts), bool)
            used[self.faces.reshape(-1)] = True
            P = np.concatenate([self.verts[used], pts])
            F = np.concatenate([vfid[used], fid])
            self._cache["samples"] = (P, F, cKDTree(P))
        return self._cache["samples"]

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

    # ------------------------------------------------------------------ distances (local frame)
    def approx_distance(self, p_local: np.ndarray, upper: float = np.inf, refine_below: float = 0.10) -> np.ndarray:
        """Distance to the surface samples, vectorized. Two levels: a coarse sample set (~3000 points) for every
        point, the full set (error below ``sample_spacing``) for points within ``refine_below`` of the coarse set;
        farther points keep the coarse value (an overestimate by at most the coarse spacing, a few cm).
        Points farther than ``upper`` get ``inf``."""
        P, _, tree = self._samples()
        if "coarse" not in self._cache:
            step = max(1, len(P) // 3000)
            self._cache["coarse"] = cKDTree(P[::step])
        q = np.asarray(p_local, np.float64).reshape(-1, 3)
        d = self._cache["coarse"].query(q, distance_upper_bound=max(upper, refine_below) + 0.1, workers=-1)[0]
        near = d < refine_below
        if near.any():
            d[near] = tree.query(q[near], distance_upper_bound=upper, workers=-1)[0]
        d[d > upper] = np.inf
        return d

    def surface_distance(self, p_local: np.ndarray, k: int = 16, exact_below: float = 0.15) -> np.ndarray:
        """Unsigned distance of local points (K, 3) to the surface: exact (point-triangle over the faces of the
        k nearest samples) within ``exact_below`` of the surface, nearest-sample distance beyond."""
        p = np.asarray(p_local, np.float64).reshape(-1, 3)
        _, F, tree = self._samples()
        d, idx = tree.query(p, k=k)
        out = d[:, 0].copy()
        for i in np.flatnonzero(d[:, 0] < exact_below):
            out[i] = self._exact(p[i], np.unique(F[idx[i]]))
        return out

    def min_surface_distance(self, p_local: np.ndarray, top: int = 3, k: int = 16) -> float:
        """Smallest surface distance over a set of local points (K, 3); exact for the ``top`` points closest
        by nearest-sample distance."""
        p = np.asarray(p_local, np.float64).reshape(-1, 3)
        _, F, tree = self._samples()
        d, idx = tree.query(p, k=k)
        order = np.argsort(d[:, 0])[:top]
        return float(min(self._exact(p[i], np.unique(F[idx[i]])) for i in order))

    def _exact(self, p: np.ndarray, face_ids: np.ndarray) -> float:
        q = closest_points_on_triangles(p, self.verts[self.faces[face_ids]])
        return float(np.min(np.linalg.norm(q - p, axis=1)))

    @property
    def center(self) -> np.ndarray:
        """Bounding-box centre of the local frame."""
        return 0.5 * (self.verts.min(0) + self.verts.max(0))

    @property
    def face_normals(self) -> np.ndarray:
        """Unit face normals (local) as wound in the file. The winding is not consistent across the meshes used
        here (thin parts, open boxes, one inverted scan), so callers sign them, see ``patch_normals``."""
        if "fn" not in self._cache:
            t = self.verts[self.faces]
            n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
            self._cache["fn"] = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        return self._cache["fn"]

    def closest_face(self, p_local: np.ndarray, k: int = 16) -> tuple[np.ndarray, np.ndarray]:
        """Closest face id (K,) and closest surface point (K, 3) for local points (K, 3)."""
        p = np.asarray(p_local, np.float64).reshape(-1, 3)
        _, F, tree = self._samples()
        _, idx = tree.query(p, k=k)
        fid = np.zeros(len(p), np.int64)
        q = np.zeros_like(p)
        for i in range(len(p)):
            cand = np.unique(F[idx[i]])
            cq = closest_points_on_triangles(p[i], self.verts[self.faces[cand]])
            j = int(np.argmin(np.linalg.norm(cq - p[i], axis=1)))
            fid[i], q[i] = cand[j], cq[j]
        return fid, q

    def patch_normals(self, p_local: np.ndarray, radius: float = 0.03) -> tuple[np.ndarray, np.ndarray, np.ndarray,
                                                                              np.ndarray]:
        """Surface patch under each local point p (K, 3) as seen from p.

        Returns the closest surface point q (K, 3), the distance |p - q| (K,), the patch normal (K, 3) and its
        coherence (K,). The patch normal is the mean of the face normals of the (area-weighted) surface
        samples within ``radius`` of q, each signed to point towards p (the side the hand is on; this also
        handles thin parts and inconsistent winding), normalised. Coherence is the length before
        normalisation: 1 on a flat patch, lower on edges, corners and curved or noisy patches.
        """
        p = np.asarray(p_local, np.float64).reshape(-1, 3)
        _, q = self.closest_face(p)
        pts, F, tree = self._samples()
        fn = self.face_normals
        n = np.zeros_like(p)
        coh = np.zeros(len(p))
        for i, nb in enumerate(tree.query_ball_point(q, r=radius)):
            if not nb:
                nb = [int(tree.query(q[i])[1])]
            nf = fn[F[nb]]
            side = p[i] - q[i]
            if np.linalg.norm(side) < 1e-6:              # on the surface: fall back to the file's winding
                side = nf.mean(0)
            nf = nf * np.where(nf @ side < 0, -1.0, 1.0)[:, None]
            m = nf.mean(0)
            coh[i] = float(np.linalg.norm(m))
            n[i] = m / max(coh[i], 1e-12)
        return q, np.linalg.norm(p - q, axis=1), n, coh


# ----------------------------------------------------------------------------- relative object motion
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
