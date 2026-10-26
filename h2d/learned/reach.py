"""Frozen-body reachability of the contact targets with the Z1 arm only (spec learned v0.6 §7.1).

Per frame the base and legs stay at the (registered) prior; only the 6 arm joints move, within the joint limits
(no budget) or within the prior +- a per-joint budget. Two problems:

* position: contact site p_c(q) -> target y (3 residuals);
* position + direction (two-point version, spec §5.2): p_c -> y and p_c + l x_tool -> y - l n (6 residuals),
  l = 0.05 m, n the outward normal; passes when the tool axis is within ``max_angle_deg`` of -n.

Solver: projected Levenberg-Marquardt from several starts (previous frame's solution, the prior, then seeded
random configurations until one is feasible). A failure of this local search is only "no feasible solution found
within the budget". "Proven unreachable" needs a bound: the target lies farther from the joint1 anchor than the
sum of the arm's segment lengths (``reach_bound``).
"""

from __future__ import annotations

from dataclasses import dataclass

import mujoco
import numpy as np

from h2d.common.collision import ObjectHull, RobotCollision
from h2d.common.robot import B2Z1Robot

LEVER_M = 0.05


@dataclass
class IKResult:
    q: np.ndarray
    pos_err_m: float
    angle_deg: float
    collision: dict
    feasible: bool
    start: str
    iters: int


@dataclass
class ObjectPose:
    """Object hull and pose at one frame (for avoidance in the solve and the penetration check)."""
    hull: ObjectHull
    pos: np.ndarray
    rot: np.ndarray            # (3, 3) world <- local

    def to_local(self, pw: np.ndarray) -> np.ndarray:
        return (np.asarray(pw) - self.pos) @ self.rot


class ArmIK:
    """Projected Levenberg-Marquardt on the task residuals plus avoidance residuals w (margin - distance) for the
    arm against the body, itself, the floor (MuJoCo geom distances, broadphase on bounding spheres) and the
    object hull (sample points of the non-tool arm geoms). Feasibility is decided by ``RobotCollision.check``."""

    def __init__(self, robot: B2Z1Robot, coll: RobotCollision, pos_tol_m: float = 0.01, max_angle_deg: float = 15.0,
                 n_random: int = 16, seed: int = 0, max_iter: int = 60, margin_m: float = 0.01,
                 w_avoid: float = 1.0, n_random_light: int = 3):
        self.r, self.coll = robot, coll
        self.pos_tol, self.max_angle = pos_tol_m, max_angle_deg
        self.n_random, self.n_light, self.max_iter = n_random, n_random_light, max_iter
        self.margin, self.w = margin_m, w_avoid
        self.rng = np.random.default_rng(seed)
        m = robot.model
        self.pairs = np.array(coll.pairs + [(a, f) for a in coll.arm for f in coll.floor], dtype=int)
        self.nontool = [g for g in coll.arm if g not in coll.tool]
        self._ft = np.zeros(6)
        self._jac = np.zeros((3, m.nv))

    def _point_jac(self, p, body):
        mujoco.mj_jac(self.r.model, self.r.data, self._jac, None, p, body)
        return self._jac[:, self.r.arm_dofadr].copy()

    def _avoid(self, obj: ObjectPose | None):
        m, d = self.r.model, self.r.data
        rows, jacs = [], []
        c, rb = d.geom_xpos, m.geom_rbound
        P = self.pairs
        gap = np.linalg.norm(c[P[:, 0]] - c[P[:, 1]], axis=1) - rb[P[:, 0]] - rb[P[:, 1]]
        for a, g in P[gap < self.margin]:
            dist = mujoco.mj_geomDistance(m, d, int(a), int(g), 2 * self.margin, self._ft)
            if dist >= self.margin:
                continue
            p1, p2 = self._ft[:3].copy(), self._ft[3:].copy()
            v = p2 - p1
            nv = np.linalg.norm(v)
            if nv < 1e-9:
                continue
            nn = v / nv * (1.0 if dist >= 0 else -1.0)
            J = nn @ (self._point_jac(p2, int(m.geom_bodyid[g])) - self._point_jac(p1, int(m.geom_bodyid[a])))
            rows.append(self.w * (self.margin - dist))
            jacs.append(-self.w * J)
        if obj is not None:
            for g in self.nontool:
                W = self.coll.samples[g] @ d.geom_xmat[g].reshape(3, 3).T + d.geom_xpos[g]
                S = obj.to_local(W) @ obj.hull.A.T + obj.hull.b
                k = S.argmax(1)
                s = S[np.arange(len(W)), k]
                for i in np.flatnonzero(s < self.margin):
                    nw = obj.rot @ obj.hull.A[k[i]]
                    rows.append(self.w * (self.margin - s[i]))
                    jacs.append(-self.w * (nw @ self._point_jac(W[i], int(m.geom_bodyid[g]))))
        if not rows:
            return np.zeros(0), np.zeros((0, 6))
        return np.array(rows), np.array(jacs)

    # ------------------------------------------------------------------ one local solve
    def _residual(self, y, n, use_dir, obj):
        p = self.r.contact_site()
        Jp = self.r.contact_site_jacobian()
        if use_dir:
            a, Ja = self.r.approach_axis(), self.r.approach_axis_jacobian()
            e, J = np.r_[p - y, (p + LEVER_M * a) - (y - LEVER_M * n)], np.vstack([Jp, Jp + LEVER_M * Ja])
        else:
            e, J = p - y, Jp
        ea, Jav = self._avoid(obj)
        return np.r_[e, ea], np.vstack([J, Jav])

    def _local(self, q0, lo, hi, y, n, use_dir, obj):
        q = np.clip(q0, lo, hi)
        mu, it = 1e-3, 0
        self.r.set_arm(q)
        e, J = self._residual(y, n, use_dir, obj)
        f = e @ e
        for it in range(1, self.max_iter + 1):
            H = J.T @ J
            step = np.linalg.solve(H + mu * np.diag(np.diag(H) + 1e-9), J.T @ e)
            qn = np.clip(q - step, lo, hi)
            self.r.set_arm(qn)
            en, Jn = self._residual(y, n, use_dir, obj)
            fn = en @ en
            if fn < f:
                q, e, J, f, mu = qn, en, Jn, fn, max(mu / 3, 1e-7)
                if f < 1e-10 or np.abs(step).max() < 1e-7:
                    break
            else:
                mu *= 4
                if mu > 1e6:
                    break
        self.r.set_arm(q)
        return q, it

    def _evaluate(self, q, y, n, use_dir, obj):
        self.r.set_arm(q)
        err = float(np.linalg.norm(self.r.contact_site() - y))
        ang = float(np.degrees(np.arccos(np.clip(self.r.approach_axis() @ (-n), -1, 1))))
        col = self.coll.check(obj.hull if obj else None, obj.to_local if obj else None)
        ok = err <= self.pos_tol and col["collision_free"] and (not use_dir or ang <= self.max_angle)
        return err, ang, col, ok

    # ------------------------------------------------------------------ multi-start
    def solve(self, y, n, q_prior, q_prev=None, use_dir=False, budget_rad: float | None = None,
              obj: ObjectPose | None = None, full: bool = True) -> IKResult:
        """``full``: all ``n_random`` random starts (else ``n_random_light``); the caller uses the full search on the
        first frame, every few frames and wherever the warm start fails after a feasible frame."""
        lo, hi = self.r.arm_lower.copy(), self.r.arm_upper.copy()
        if budget_rad is not None:
            lo, hi = np.maximum(lo, q_prior - budget_rad), np.minimum(hi, q_prior + budget_rad)
        starts = ([("previous", q_prev)] if q_prev is not None else []) + [("prior", q_prior)]
        starts += [(f"random{i}", self.rng.uniform(lo, hi)) for i in range(self.n_random if full else self.n_light)]
        best = None
        for name, q0 in starts:
            q, it = self._local(q0, lo, hi, y, n, use_dir, obj)
            err, ang, col, ok = self._evaluate(q, y, n, use_dir, obj)
            res = IKResult(q, err, ang, col, ok, name, it)
            key = (not ok, err if not ok else 0.0, float(np.sum((q - q_prior) ** 2)))
            if best is None or key < best[0]:
                best = (key, res)
            if ok:
                break
        return best[1]


def reach_bound(robot: B2Z1Robot) -> tuple[float, float]:
    """Rigorous upper bound of |contact site - joint1 anchor| for any arm configuration: the sum of the fixed
    distances between consecutive arm joint anchors plus the last anchor to the contact site (triangle
    inequality). Returns (bound, sampled max over 20k random configurations, for context)."""
    saved = robot.data.qpos.copy()
    jids = [robot._jid(n) for n in robot.cfg["robot"]["arm_joints"]]
    a = robot.data.xanchor[jids].copy()
    bound = float(np.linalg.norm(np.diff(a, axis=0), axis=1).sum() + np.linalg.norm(robot.contact_site() - a[-1]))
    rng = np.random.default_rng(0)
    best = 0.0
    for q in rng.uniform(robot.arm_lower, robot.arm_upper, size=(20000, 6)):
        robot.set_arm(q)
        best = max(best, float(np.linalg.norm(robot.contact_site() - robot.data.xanchor[jids[0]])))
    robot.set_qpos(saved)
    return bound, best


def shoulder(robot: B2Z1Robot) -> np.ndarray:
    """World position of the joint1 anchor (moves with the base only)."""
    return robot.data.xanchor[robot._jid(robot.cfg["robot"]["arm_joints"][0])].copy()
