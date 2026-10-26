"""Interaction-mesh body placement (spec learned v0.8 §5.5, Kevin: keep the human's role; the dog's absolute
position is not copied from the human).

The legs and the arm come from the X-Morph prior; this step decides where the body is relative to the object, frame
by frame, so that the dog keeps the human's body-object relations and not only the contact:

* correspondences: human pelvis -> B2 trunk centre, human chest -> Z1 base (joint1 anchor), human virtual hand ->
  the gripper's contact target (fixed here; the arm IK reaches it afterwards);
* mesh: per frame, a Delaunay tetrahedralisation of the human side (pelvis, chest, hand, object surface samples);
  the edges from the pelvis or the chest to the hand or an object sample are kept;
* placement: a per-frame SE(2) of the raw prior, world = R(psi_t) p + b_t (z unchanged), solved over the window at
  once (least squares, sparse finite differences) for
  - edge directions: each edge's horizontal unit direction matches the human's (lengths free: another body size);
  - heading: the trunk's forward axis matches the human's facing (from the shoulders);
  - reach: Z1 base to the contact target near the arm's comfortable distance and within [r_min, r_max] (hinge).
    Directions come from the human, the distance from the dog's arm: the edge directions alone would pull the
    body to human-like distances (object samples span the box), too far for the arm (dry run on the test push);
  - clearance: trunk and legs outside the object hull by a margin (hinge);
  - smoothness (first difference) and a weak pull to the constant registration.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import coo_matrix
from scipy.spatial import Delaunay
from scipy.spatial.transform import Rotation as R

from h2d.common.registration import wrap

FEET = ("FL_foot", "FR_foot", "RL_foot", "RR_foot")


def _unit2(v: np.ndarray) -> np.ndarray:
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)


def se2(p: np.ndarray, psi: np.ndarray, b: np.ndarray | float = 0.0) -> np.ndarray:
    """Per-frame planar transform of xy points p (n, ..., 2)."""
    c, s = np.cos(psi), np.sin(psi)
    Rm = np.stack([np.stack([c, -s], -1), np.stack([s, c], -1)], -2)                # (n, 2, 2)
    b = np.broadcast_to(np.asarray(b, float), (len(psi), 2))
    return np.einsum("nij,n...j->n...i", Rm, p) + b.reshape(len(psi), *[1] * (p.ndim - 2), 2)


@dataclass
class PriorPoints:
    """Raw (unregistered) prior points per window frame, from forward kinematics."""
    trunk: np.ndarray       # (n, 3)
    arm_base: np.ndarray    # (n, 3)
    forward: np.ndarray     # (n, 2) unit, the trunk's x axis
    feet: np.ndarray        # (n, 4, 3)
    body: np.ndarray        # (n, m, 3) trunk and leg collision samples


def prior_points(robot, coll, motion, frames, per_geom: int = 8) -> PriorPoints:
    from h2d.learned.reach import shoulder

    base, feet = robot._bid("base_link"), [robot._bid(f) for f in FEET]
    out = {k: [] for k in ("trunk", "arm_base", "forward", "feet", "body")}
    for t in frames:
        robot.set_qpos(robot.qpos_from_xmorph(motion.root_pos[t], motion.root_rot_xyzw[t], motion.dof_pos[t]))
        d = robot.data
        out["trunk"].append(d.xpos[base].copy())
        out["arm_base"].append(shoulder(robot))
        out["forward"].append(_unit2(d.xmat[base].reshape(3, 3)[:2, 0]))
        out["feet"].append(d.xpos[feet].copy())
        out["body"].append(np.concatenate([coll.samples[g][:: max(1, len(coll.samples[g]) // per_geom)]
                                           @ d.geom_xmat[g].reshape(3, 3).T + d.geom_xpos[g] for g in coll.body]))
    return PriorPoints(**{k: np.array(v) for k, v in out.items()})


def object_samples(verts: np.ndarray, k: int) -> np.ndarray:
    """Farthest-point samples of the object's hull vertices (local frame)."""
    idx, d = [0], np.linalg.norm(verts - verts[0], axis=1)
    for _ in range(min(k, len(verts)) - 1):
        idx.append(int(d.argmax()))
        d = np.minimum(d, np.linalg.norm(verts - verts[idx[-1]], axis=1))
    return verts[idx]


class InteractionMesh:
    """Human-side mesh of one task window and the placement energy of the dog's body."""

    def __init__(self, task: dict, pp: PriorPoints, obj_local: np.ndarray, hull, cfg: dict):
        self.pp, self.hull, self.cfg = pp, hull, cfg
        self.n = n = len(task["frames"])
        self.fps = float(task["fps"])
        Rm = R.from_quat(task["obj_rot_xyzw"]).as_matrix()
        self.Rm, self.pos = Rm, task["obj_pos"]
        O = np.einsum("nij,kj->nki", Rm, obj_local) + self.pos[:, None]                 # (n, k, 3)
        H = task["body_world"]                                                            # pelvis, chest, L/R shoulder
        fix_h = np.concatenate([task["palm_world"][:, None], O], 1)                      # hand, object samples
        fix_d = np.concatenate([task["target_world"][:, None], O], 1)                    # gripper target, samples
        E = []
        for t in range(n):
            pts = np.vstack([H[t, :2], fix_h[t]])
            pairs = {(a, b) for s in Delaunay(pts, qhull_options="QJ").simplices for a in s for b in s if a < b}
            E += [(t, a, j - 2) for a, j in pairs if a < 2 <= j
                  and np.linalg.norm(pts[a, :2] - pts[j, :2]) >= cfg["min_edge_m"]]
        self.t_e, self.a_e, j_e = np.array(E).T
        self.fix_d = fix_d[self.t_e, j_e, :2]
        self.u_h = _unit2(H[self.t_e, self.a_e, :2] - fix_h[self.t_e, j_e, :2])
        sh = H[:, 2] - H[:, 3]
        self.f_h = _unit2(np.stack([sh[:, 1], -sh[:, 0]], 1))                            # (L - R) x z
        self.g = task["target_world"]
        self.dog = np.stack([pp.trunk, pp.arm_base], 1)

    def terms(self, psi: np.ndarray, b: np.ndarray) -> dict:
        """Unweighted terms of a placement (psi (n,), b (n, 2))."""
        P = se2(self.dog[..., :2], psi, b)
        arm = np.concatenate([P[:, 1], self.pp.arm_base[:, 2:]], 1)
        W = np.concatenate([se2(self.pp.body[..., :2], psi, b), self.pp.body[..., 2:]], 2)
        local = np.einsum("nji,nmj->nmi", self.Rm, W - self.pos[:, None])
        return {"edge": _unit2(P[self.t_e, self.a_e] - self.fix_d) - self.u_h,
                "heading": se2(self.pp.forward, psi) - self.f_h,
                "reach": np.linalg.norm(arm - self.g, axis=1),
                "clear": (local @ self.hull.A.T + self.hull.b).max(-1)}

    def _residual(self, x, x0):
        c, x = self.cfg, x.reshape(-1, 3)
        k = self.terms(x[:, 0], x[:, 1:])
        relu = lambda v: np.maximum(v, 0.0)  # noqa: E731
        dx = np.c_[np.diff(x[:, 1:], axis=0), 0.5 * wrap(np.diff(x[:, 0]))]
        return np.concatenate([
            c["w_mesh"] * k["edge"].ravel(), c["w_heading"] * k["heading"].ravel(),
            c["w_reach"] * relu(k["reach"] - c["r_max_m"]), c["w_reach"] * relu(c["r_min_m"] - k["reach"]),
            c["w_reach_pref"] * (k["reach"] - c["reach_pref_m"]),
            c["w_clear"] * relu(c["clear_margin_m"] - k["clear"]).ravel(),
            c["w_smooth"] * dx.ravel(),
            c["w_anchor"] * np.c_[x[:, 1:] - x0[:, 1:], 0.5 * wrap(x[:, 0] - x0[:, 0])].ravel()])

    def _sparsity(self):
        """Rows in ``_residual`` order -> the frame whose (psi, b) they depend on; smoothness rows also on t - 1."""
        n, m = self.n, self.pp.body.shape[1]
        rep = lambda t, k: np.repeat(t, k)  # noqa: E731
        frames = np.concatenate([rep(self.t_e, 2), rep(np.arange(n), 2), np.arange(n), np.arange(n), np.arange(n),
                                 rep(np.arange(n), m), rep(np.arange(1, n), 3), rep(np.arange(n), 3)])
        smooth = np.arange(len(frames) - 3 * n - 3 * (n - 1), len(frames) - 3 * n)
        rows = np.r_[np.arange(len(frames)), smooth]
        cols = 3 * np.r_[frames, frames[smooth] - 1][:, None] + np.arange(3)
        return coo_matrix((np.ones(cols.size), (np.repeat(rows, 3), cols.ravel())), shape=(len(frames), 3 * n))

    def place(self, psi0: float, b0) -> tuple[np.ndarray, np.ndarray, dict]:
        """Start from the constant registration (psi0, b0); returns per-frame psi (n,), b (n, 2) and solver info."""
        x0 = np.tile(np.r_[psi0, b0], (self.n, 1))
        sol = least_squares(self._residual, x0.ravel(), args=(x0,), jac_sparsity=self._sparsity(), method="trf",
                            max_nfev=self.cfg["max_nfev"])
        x = sol.x.reshape(-1, 3)
        return x[:, 0], x[:, 1:], {"cost": float(sol.cost), "nfev": int(sol.nfev), "status": int(sol.status),
                                   "n_edges": int(len(self.t_e))}

    def metrics(self, psi: np.ndarray, b: np.ndarray, sel=None) -> dict:
        """Relation errors of a placement over the frames ``sel`` (default all): edge direction and heading (deg),
        reach distance, body inside the object, extra foot slide from the placement change (m/s, stance feet)."""
        sel = np.arange(self.n) if sel is None else np.asarray(sel)
        k = self.terms(psi, b)
        ang = lambda d: np.degrees(2 * np.arcsin(np.clip(np.linalg.norm(d, axis=-1) / 2, 0, 1)))  # noqa: E731
        e = ang(k["edge"])[np.isin(self.t_e, sel)]
        feet = self.pp.feet[sel]
        stance = feet[1:, :, 2] < 0.04
        moved = se2(feet[1:, :, :2], psi[sel][1:], b[sel][1:]) - se2(feet[1:, :, :2], psi[sel][:-1], b[sel][:-1])
        slide = np.linalg.norm(moved, axis=-1)[stance] * self.fps
        return {"edge_dir_err_deg": float(e.mean()) if e.size else None,
                "heading_err_deg": float(ang(k["heading"])[sel].mean()),
                "reach_m": [float(k["reach"][sel].min()), float(k["reach"][sel].max())],
                "body_in_object_m": float(np.maximum(-k["clear"][sel], 0).max()),
                "extra_foot_slide_max_mps": float(slide.max()) if slide.size else 0.0}
