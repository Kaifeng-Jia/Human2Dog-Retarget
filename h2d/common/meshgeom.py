"""Small exact mesh-geometry helpers (no external mesh library needed)."""

from __future__ import annotations

import numpy as np


def closest_points_on_triangles(p: np.ndarray, tri: np.ndarray) -> np.ndarray:
    """Closest point to ``p`` (3,) on each triangle of ``tri`` (T, 3, 3).

    Vectorized version of the Voronoi-region method (Ericson, Real-Time
    Collision Detection, sec. 5.1.5). Returns (T, 3).
    """
    p = np.asarray(p, dtype=np.float64)
    a, b, c = tri[:, 0].astype(np.float64), tri[:, 1].astype(np.float64), tri[:, 2].astype(np.float64)
    ab, ac, ap = b - a, c - a, p - a
    d1 = np.einsum("ij,ij->i", ab, ap)
    d2 = np.einsum("ij,ij->i", ac, ap)
    bp = p - b
    d3 = np.einsum("ij,ij->i", ab, bp)
    d4 = np.einsum("ij,ij->i", ac, bp)
    cp = p - c
    d5 = np.einsum("ij,ij->i", ab, cp)
    d6 = np.einsum("ij,ij->i", ac, cp)

    va = d3 * d6 - d5 * d4
    vb = d5 * d2 - d1 * d6
    vc = d1 * d4 - d3 * d2

    out = np.empty_like(a)
    done = np.zeros(len(a), dtype=bool)

    def assign(mask, val):
        nonlocal done
        m = mask & ~done
        out[m] = val[m]
        done |= m

    eps = 1e-300
    assign((d1 <= 0) & (d2 <= 0), a)                                   # vertex A
    assign((d3 >= 0) & (d4 <= d3), b)                                  # vertex B
    v_ab = d1 / np.where(np.abs(d1 - d3) > eps, d1 - d3, eps)
    assign((vc <= 0) & (d1 >= 0) & (d3 <= 0), a + v_ab[:, None] * ab)  # edge AB
    assign((d6 >= 0) & (d5 <= d6), c)                                  # vertex C
    w_ac = d2 / np.where(np.abs(d2 - d6) > eps, d2 - d6, eps)
    assign((vb <= 0) & (d2 >= 0) & (d6 <= 0), a + w_ac[:, None] * ac)  # edge AC
    den_bc = (d4 - d3) + (d5 - d6)
    w_bc = (d4 - d3) / np.where(np.abs(den_bc) > eps, den_bc, eps)
    assign((va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0), b + w_bc[:, None] * (c - b))  # edge BC
    denom = va + vb + vc
    denom = np.where(np.abs(denom) > eps, denom, eps)
    v = vb / denom
    w = vc / denom
    assign(np.ones(len(a), dtype=bool), a + v[:, None] * ab + w[:, None] * ac)  # face interior
    return out


def point_mesh_distance(p: np.ndarray, verts: np.ndarray, faces: np.ndarray) -> float:
    """Unsigned distance from point ``p`` to a triangle mesh."""
    tri = verts[faces]
    q = closest_points_on_triangles(p, tri)
    return float(np.min(np.linalg.norm(q - p, axis=1)))


def triangle_areas(verts: np.ndarray, faces: np.ndarray) -> np.ndarray:
    tri = verts[faces]
    return 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
