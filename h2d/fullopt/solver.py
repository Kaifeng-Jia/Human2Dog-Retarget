"""Per-frame SQP of the full-optimization line (fullopt spec v0.2 §7).

Frame by frame, the robot configuration q_t minimises

    w_rel E_rel + w_task g_t E_task + E_nom + |q_t - q_t-1|^2_Wv + |q_t - 2 q_t-1 + q_t-2|^2_Wa

* E_rel: the relation term (``h2d/fullopt/relation.py``);
* E_task: contact point, two-point direction (lever 0.05 m) and a soft roll (0.02 m), gated by the task's
  g_t = a c kappa (``h2d/fullopt/task.py``);
* E_nom: trunk roll and pitch to 0, trunk height to the nominal one (weak), joints to home (very weak);

subject to, linearised at every iteration (spec §7.2): joint limits and joint speeds (boxes on the step; the step
dx = 0 always satisfies them), robot samples outside the object's convex hull (the tool excepted: it pushes), trunk and
arm samples above the floor, the arm clear of the trunk, the legs and itself (``Collision``), and the trust region
|dx| <= rho. The hull, floor and self constraints get L1 slacks with a large weight: a frame always has a solution,
and a violation is measured afterwards (``evaluate.py``), never assumed away. Each iteration is one QP with a
second-order cone (cvxpy + Clarabel), compiled once with parameters (DPP) and reused for every frame and clip.

Pass 1 (spec §7.3): the trunk (6) and the arm (6) move; the legs stay at home and no foot is constrained. The first
frame starts with the trunk over the human's pelvis, facing the human's facing (shoulder line x vertical), and iterates
up to ``first_frame_iters``; every later frame starts from the previous two, extrapolated.
"""

from __future__ import annotations

import time

import cvxpy as cp
import numpy as np
from scipy.spatial.transform import Rotation as R

from h2d.common.collision import ObjectHull
from h2d.fullopt.hoi import HOIClip
from h2d.fullopt.robot import Collision, Robot
from h2d.fullopt.signals import smooth

EZ = np.array([0.0, 0.0, 1.0])


class StepQP:
    """min |A dx - b|^2 + w sum(s)  s.t.  G dx + h + s >= 0,  s >= 0,  lo <= dx <= hi,  |dx| <= rho."""

    def __init__(self, n: int, m: int, k: int, slack_weight: float):
        self.A, self.b, self.G, self.h = cp.Parameter((m, n)), cp.Parameter(m), cp.Parameter((k, n)), cp.Parameter(k)
        self.lo, self.hi, self.rho = cp.Parameter(n), cp.Parameter(n), cp.Parameter(nonneg=True)
        self.dx, self.s = cp.Variable(n), cp.Variable(k, nonneg=True)
        cost = cp.sum_squares(self.A @ self.dx - self.b) + slack_weight * cp.sum(self.s)
        self.problem = cp.Problem(cp.Minimize(cost), [self.G @ self.dx + self.h + self.s >= 0, self.dx >= self.lo,
                                                      self.dx <= self.hi, cp.SOC(self.rho, self.dx)])

    def solve(self, A, b, G, h, lo, hi, rho) -> tuple[np.ndarray, float, bool]:
        """Step, largest slack, solved."""
        for p, v in zip((self.A, self.b, self.G, self.h, self.lo, self.hi, self.rho), (A, b, G, h, lo, hi, rho)):
            p.value = v
        try:
            self.problem.solve(solver=cp.CLARABEL)
        except cp.SolverError:
            return np.zeros(self.dx.shape), float("nan"), False
        if self.dx.value is None:
            return np.zeros(self.dx.shape), float("nan"), False
        return np.asarray(self.dx.value), float(np.max(self.s.value, initial=0.0)), True


class Solver:
    """``cfg``: configs/fullopt/solver.yaml. ``groups``: the robot's dof groups that move (pass 1: base and arm)."""

    def __init__(self, robot: Robot, cfg: dict, groups=("base", "arm"), coll: Collision | None = None):
        self.robot, self.cfg = robot, cfg
        self.coll = coll or Collision(robot)
        self.dofs = robot.dofs(*groups)
        self.n = len(self.dofs)
        w = cfg["weights"]
        base0 = robot.groups["base"][0]
        key = {d: ("base_pos" if d - base0 < 3 else "base_rot") if d in robot.groups["base"] else g
               for g in groups for d in robot.groups[g]}
        self.sv = np.sqrt([w["velocity"][key[d]] for d in self.dofs])
        self.sa = np.sqrt([w["acceleration"][key[d]] for d in self.dofs])
        self.sh = np.sqrt(w["home"]) * (robot.dof_qadr[self.dofs] >= 0)
        c = self.coll
        self.obj_geoms = c.body + [g for g in c.arm if g not in c.tool]
        self.floor_geoms = [g for g in c.body + c.arm if g not in c.legs]       # pass 1: the legs stand at home
        self.rows = cfg["constraints"]["rows"]
        self._qp: dict[int, StepQP] = {}

    def _step_qp(self, m: int) -> StepQP:
        if m not in self._qp:
            self._qp[m] = StepQP(self.n, m, sum(self.rows.values()), self.cfg["constraints"]["slack_weight"])
        return self._qp[m]

    # ------------------------------------------------------------------ one linearisation
    def objective(self, t: int, q, q1, q2, task, relation) -> tuple[np.ndarray, np.ndarray]:
        """Stacked weighted residuals r and Jacobian J at q: the step minimises |J dx + r|^2."""
        r, d, w = self.robot, self.dofs, self.cfg["weights"]
        eye, Z = np.eye(self.n), np.zeros((3, self.n))
        rows: list[tuple[np.ndarray, np.ndarray, np.ndarray | float]] = []
        rows.append((*relation.residual(t, r, d), np.sqrt(w["relation"])))
        g = float(task.gate[t])
        if g > 0:
            sw, lev, rm = np.sqrt(w["task"] * g), w["lever_m"], w["roll_m"]
            p = r.tool_point()
            Jp = r.body_point_jac(r.tool_body, p, d)
            a, Ja = r.axis(r.tool_body, r.approach_local), r.axis_jac(r.tool_body, r.approach_local, d)
            y = task.target[t]
            rows += [(p - y, Jp, sw), (p + lev * a - (y + lev * task.tool_x[t]), Jp + lev * Ja, sw)]
            z_ref, jaw = task.tool_z[t], r.jaw_local
            if np.all(np.isfinite(z_ref)):
                rows.append((rm * (r.axis(r.tool_body, jaw) - z_ref), rm * r.axis_jac(r.tool_body, jaw, d), sw))
            else:
                rows.append((np.zeros(3), Z, 0.0))
        else:
            rows += [(np.zeros(3), Z, 0.0)] * 3
        up, base = r.base_rot()[:, 2], r.data.xpos[r.base]
        rows.append((up[:2], r.axis_jac(r.base, EZ, d)[:2], np.sqrt(w["tilt"])))
        rows.append(([base[2] - r.nominal_height], r.body_point_jac(r.base, base, d)[2:], np.sqrt(w["height"])))
        rows.append((r.difference(r.home, q, d), eye, self.sh))
        v = r.difference(q1, q, d) if q1 is not None else np.zeros(self.n)
        rows.append((v, eye, self.sv * (q1 is not None)))
        a = v - r.difference(q2, q1, d) if q2 is not None else np.zeros(self.n)
        rows.append((a, eye, self.sa * (q2 is not None)))
        res = np.concatenate([np.reshape(s, -1) * np.asarray(e) for e, _, s in rows])
        jac = np.vstack([np.reshape(s, (-1, 1)) * J for _, J, s in rows])
        return res, jac

    def constraints(self, t: int, hull: ObjectHull, Ro: np.ndarray, po: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """G dx + h >= 0 on the most critical object, floor and self rows (unused rows: 0 dx + 1 >= 0)."""
        r, d, c = self.robot, self.dofs, self.cfg["constraints"]
        act = c["activation_m"]
        G, h = np.zeros((sum(self.rows.values()), self.n)), np.ones(sum(self.rows.values()))
        i = 0
        P, B = self.coll.world_samples(self.obj_geoms)                              # outside the object's hull
        S = ((P - po) @ Ro) @ hull.A.T + hull.b
        f = S.argmax(1)
        s = S[np.arange(len(P)), f]
        for j in self._critical(s, act, self.rows["object"]):
            G[i], h[i] = (Ro @ hull.A[f[j]]) @ r.body_point_jac(B[j], P[j], d), s[j] - c["object_margin_m"]
            i += 1
        i = self.rows["object"]
        P, B = self.coll.world_samples(self.floor_geoms)                            # above the floor
        z = P[:, 2] - c["floor_clearance_m"]
        for j in self._critical(z, act, self.rows["floor"]):
            G[i], h[i] = r.body_point_jac(B[j], P[j], d)[2], z[j]
            i += 1
        i = self.rows["object"] + self.rows["floor"]
        near = sorted(self.coll.self_distances(act), key=lambda x: x[0])[: self.rows["self"]]
        for dist, ft, ba, bg in near:                                               # arm against itself and the body
            v = ft[3:] - ft[:3]
            if np.linalg.norm(v) < 1e-9:
                continue
            nn = v / np.linalg.norm(v) * (1.0 if dist >= 0 else -1.0)
            G[i] = nn @ (r.body_point_jac(bg, ft[3:], d) - r.body_point_jac(ba, ft[:3], d))
            h[i] = dist - c["self_margin_m"]
            i += 1
        return G, h

    @staticmethod
    def _critical(s: np.ndarray, act: float, k: int) -> np.ndarray:
        cand = np.flatnonzero(s < act)
        return cand[np.argsort(s[cand])][:k]

    def box(self, q, q1, fps: float, rho: float) -> tuple[np.ndarray, np.ndarray]:
        """Step bounds: joint limits, the trunk's height range, joint and trunk speeds (from q1) and the trust
        region's box; dx = 0 always inside."""
        r, d = self.robot, self.dofs
        lo, hi = np.full(self.n, -rho), np.full(self.n, rho)
        z, h = np.flatnonzero(d == r.groups["base"][2]), q[r.base_qadr + 2]   # the base's vertical translation
        lo[z], hi[z] = max(-rho, r.height_range[0] - h), min(rho, r.height_range[1] - h)
        j = r.dof_qadr[d] >= 0
        val = q[r.dof_qadr[d][j]]
        lo[j], hi[j] = np.maximum(lo[j], r.lower[d][j] - val), np.minimum(hi[j], r.upper[d][j] - val)
        if q1 is not None:                                              # |(q + dx) - q1| <= speed / fps
            v, sp = r.difference(q1, q, d), r.speed[d] / fps
            lo, hi = np.maximum(lo, -sp - v), np.minimum(hi, sp - v)
        return np.minimum(lo, 0.0), np.maximum(hi, 0.0)

    # ------------------------------------------------------------------ a clip
    def start(self, c: HOIClip) -> np.ndarray:
        """The trunk over the human's pelvis, facing the human (shoulder line x vertical), at the nominal height."""
        k = self.cfg["relation"]["human_smooth_s"]
        pel = smooth(c.joint("pelvis"), c.fps, k)[0]
        sh = smooth(c.joint("l_shoulder") - c.joint("r_shoulder"), c.fps, k)[0]
        return self.robot.placed(pel[:2], float(np.arctan2(-sh[0], sh[1])))

    def solve(self, c: HOIClip, task, relation, log=None) -> dict:
        """Solve every frame of a clip whose floor is at z = 0 (``hoi.leveled``). Returns the configurations and, per
        frame, the iterations, the last step, the largest slack and whether every QP solved."""
        r, sq = self.robot, self.cfg["sqp"]
        hull = ObjectHull.from_vertices(np.asarray(c.obj_verts, float))
        Ro, po = R.from_quat(c.obj_quat).as_matrix(), c.obj_pos
        T = c.n
        out = {"q": np.zeros((T, r.model.nq)), "iters": np.zeros(T, int), "step": np.zeros(T),
               "slack_max": np.zeros(T), "qp_ok": np.ones(T, bool)}
        t0 = time.time()
        q1 = q2 = None
        for t in range(T):
            if t == 0:
                q = self.start(c)
            else:
                v = r.difference(q2, q1, self.dofs) if q2 is not None else np.zeros(self.n)
                q = r.clip(r.integrate(q1, v, self.dofs))
            for it in range(sq["first_frame_iters"] if t == 0 else sq["max_iters"]):
                r.set(q)
                res, jac = self.objective(t, q, q1, q2, task, relation)
                G, h = self.constraints(t, hull, Ro[t], po[t])
                lo, hi = self.box(q, q1, c.fps, sq["trust_region"])
                dx, slack, ok = self._step_qp(len(res)).solve(jac, -res, G, h, lo, hi, sq["trust_region"])
                q = r.integrate(q, dx, self.dofs)
                out["slack_max"][t], out["qp_ok"][t] = slack, out["qp_ok"][t] and ok
                out["iters"][t], out["step"][t] = it + 1, float(np.linalg.norm(dx))
                if out["step"][t] < sq["tol"]:
                    break
            out["q"][t] = q
            q2, q1 = q1, q
            if log and (t % 50 == 0 or t == T - 1):
                log(f"    frame {t + 1}/{T}: {out['iters'][t]} iterations, {time.time() - t0:.1f} s")
        out["time_s"] = time.time() - t0
        return out
