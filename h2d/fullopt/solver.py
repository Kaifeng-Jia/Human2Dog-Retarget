"""Per-frame SQP of the full-optimization line (fullopt spec v0.2 §7).

Frame by frame, the robot configuration q_t minimises

    w_rel E_rel + w_task g_t E_task + E_nom + E_foot + |q_t - q_t-1|^2_Wv + |q_t - 2 q_t-1 + q_t-2|^2_Wa

* E_rel: the relation term (``h2d/fullopt/relation.py``);
* E_task: contact point, two-point direction (lever 0.05 m) and a soft roll (0.02 m), gated by the task's gate g_t
  (``h2d/fullopt/task.py``);
* E_nom: trunk roll and pitch to 0, trunk height to the nominal one (weak), joints to home (very weak);
* E_foot: each foot's horizontal position to its nominal foothold, the home stance under the hips (soft);

subject to, linearised at every iteration (spec §7.2):

* boxes on the step: joint limits, the trunk's height range, joint and trunk speeds, and the trunk's accelerations
  (configs/fullopt/robots/<robot>.yaml); a start (the previous frames extrapolated) outside one is brought back;
* rows with L1 slacks of a large weight (a frame always has a solution; a violation is measured afterwards, in
  ``evaluate.py``, never assumed away): robot samples outside the object's convex hull (the tool excepted: it
  pushes), the under-body box included, and the object's hull vertices outside that box; every geom but the soles at
  least ``floor_clearance_m`` above the floor; the arm clear of the trunk, the legs and itself (``Collision``); every
  sole within ``foot_band_m`` of the floor; trunk roll and pitch within the description's ``tilt_limit_deg``;
* the trust region |dx| <= rho.

A frame sees no later frame, so with bounded accelerations the trunk could run into a bound it cannot stop at. Rows
the trunk closes in on (the object, the under-body box, the tilt, the height range) therefore cap the closing speed
to what the trunk can still stop from (``held``).

Each iteration is one QP with a second-order cone (cvxpy + Clarabel), compiled once with parameters (DPP) and reused
for every frame and clip.

Pass 1 (spec §7.3): the trunk (6), the legs (12) and the arm (6) move; the soles stay on the floor and slide (no
contact schedule: the gait is milestone M3). The first frame starts at home with the trunk over the human's pelvis,
facing the human's facing (shoulder line x vertical), and iterates up to ``first_frame_iters``; every later frame
starts from the previous two, extrapolated.
"""

from __future__ import annotations

import time

import cvxpy as cp
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R

from h2d.common.collision import ObjectHull
from h2d.fullopt.hoi import HOIClip
from h2d.fullopt.robot import GROUPS, Collision, Robot
from h2d.fullopt.signals import smooth

EZ = np.array([0.0, 0.0, 1.0])


def held(value: np.ndarray, rate: np.ndarray, a: float) -> np.ndarray:
    """The offset h of a row G dx + h >= 0 (a value >= 0 that the step changes by G dx) that the trunk can still hold
    at deceleration ``a`` [per frame^2]: after the step the value v' and the closing speed w' per frame obey
    v' >= w'^2 / (2 a) + w' / 2 (stopping in whole frames). With the previous value v1 = value - rate, this caps the
    closing speed at w = a (sqrt(2.25 + 2 v1 / a) - 1.5), so h = rate + w (``value`` itself when a is infinite or
    v1 <= 0)."""
    value = np.asarray(value, float)
    v1 = value - rate
    if not np.isfinite(a):
        return value
    w = a * (np.sqrt(2.25 + 2.0 * np.maximum(v1, 0.0) / a) - 1.5)
    return np.where(v1 > 0, rate + w, value)       # (rate + w <= value; from inside the bound, only the bound)


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
    """``cfg``: configs/fullopt/solver.yaml. ``groups``: the robot's dof groups that move."""

    def __init__(self, robot: Robot, cfg: dict, groups=GROUPS, coll: Collision | None = None):
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
        self.floor_geoms = [g for g in c.body + c.arm if g not in c.feet]
        self.rows = dict(cfg["constraints"]["rows"], feet=2 * len(robot.feet), tilt=4)
        self.fps = 30.0                                          # set per clip in ``solve``
        braked = set(c.body)                                    # samples the trunk carries: body and under-body box
        n_cage = len(robot.cage["samples"]) if robot.cage else 0
        self._braked = np.concatenate([np.full(len(c.samples[g]), g in braked) for g in self.obj_geoms]
                                      + [np.ones(n_cage, bool)])
        self._cage = np.r_[np.zeros(len(self._braked) - n_cage, bool), np.ones(n_cage, bool)]
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
        feet, hold = r.data.xpos[r.feet], r.footholds()
        for f, p, h in zip(r.feet, feet, hold):
            J = r.body_point_jac(f, p, d) - r.body_point_jac(r.base, h, d)
            rows.append(((p - h)[:2], J[:2], np.sqrt(w["foothold"])))
        rows.append((r.difference(r.home, q, d), eye, self.sh))
        v = r.difference(q1, q, d) if q1 is not None else np.zeros(self.n)
        rows.append((v, eye, self.sv * (q1 is not None)))
        a = v - r.difference(q2, q1, d) if q2 is not None else np.zeros(self.n)
        rows.append((a, eye, self.sa * (q2 is not None)))
        res = np.concatenate([np.reshape(s, -1) * np.asarray(e) for e, _, s in rows])
        jac = np.vstack([np.reshape(s, (-1, 1)) * J for _, J, s in rows])
        return res, jac

    def _samples(self) -> tuple[np.ndarray, np.ndarray]:
        """World samples kept out of the object (body, arm without the tool, the under-body box) and their bodies."""
        r = self.robot
        P, B = self.coll.world_samples(self.obj_geoms)
        if r.cage is None:
            return P, B
        return np.vstack([P, r.cage_points()]), np.r_[B, np.full(len(r.cage["samples"]), r.cage["body"])]

    def constraints(self, hull: ObjectHull, verts: np.ndarray, Ro: np.ndarray, po: np.ndarray, q, q1):
        """G dx + h >= 0: the most critical object, under-body, floor and self rows, then every sole and the tilt
        (unused rows: 0 dx + 1 >= 0). ``verts``: the object's hull vertices (local frame). With the previous frame q1,
        the rows on what the trunk carries (body, under-body box) and the tilt are ``held`` at the trunk's
        accelerations, their rate being the change since q1 with the object held still."""
        r, d, c = self.robot, self.dofs, self.cfg["constraints"]
        act, k = c["activation_m"], self.rows
        G, h = np.zeros((sum(k.values()), self.n)), np.ones(sum(k.values()))
        at = np.cumsum([0] + list(k.values()))
        i0 = dict(zip(k, at))
        b = r.groups["base"]
        a_lin, a_ang = r.accel[b[0]] / self.fps**2, r.accel[b[3]] / self.fps**2

        def put(block: str, n: int, g: np.ndarray, v: float) -> int:
            G[i0[block] + n], h[i0[block] + n] = g, v
            return n + 1

        if q1 is not None:                                        # the rows' values on the previous frame
            r.set(q1)
            P1, tilt1 = self._samples()[0], r.tilt()
            sd1 = r.outside_cage(verts @ Ro.T + po)[0] if r.cage is not None else None
            r.set(q)
        P, B = self._samples()                                    # robot outside the object's hull ...
        S = ((P - po) @ Ro) @ hull.A.T + hull.b                   # (... the space under the trunk with it)
        f = S.argmax(1)
        margin = np.where(self._cage, c["cage_margin_m"], c["object_margin_m"])
        s = S[np.arange(len(P)), f] - margin
        if q1 is not None:
            s1 = np.sum(((P1 - po) @ Ro) * hull.A[f], 1) + hull.b[f] - margin
            s = np.where(self._braked, held(s, s - s1, a_lin), s)
        n = 0
        for j in self._critical(s, act, k["object"]):
            n = put("object", n, (Ro @ hull.A[f[j]]) @ r.body_point_jac(B[j], P[j], d), s[j])
        if r.cage is not None:                                    # the object's corners outside the under-body box
            V = verts @ Ro.T + po
            sd, nrm = r.outside_cage(V)
            sd = sd - c["cage_margin_m"]
            if q1 is not None:
                sd = held(sd, sd - (sd1 - c["cage_margin_m"]), a_lin)
            n = 0
            for j in self._critical(sd, act, k["cage"]):
                n = put("cage", n, -nrm[j] @ r.body_point_jac(r.cage["body"], V[j], d), sd[j])
        P, B = self.coll.world_samples(self.floor_geoms)          # above the floor
        z = P[:, 2] - c["floor_clearance_m"]
        n = 0
        for j in self._critical(z, act, k["floor"]):
            n = put("floor", n, r.body_point_jac(B[j], P[j], d)[2], z[j])
        near = sorted(self.coll.self_distances(act), key=lambda x: x[0])[: k["self"]]
        n = 0
        for dist, ft, ba, bg in near:                             # arm against itself and the body
            v = ft[3:] - ft[:3]
            if np.linalg.norm(v) < 1e-9:
                continue
            nn = v / np.linalg.norm(v) * (1.0 if dist >= 0 else -1.0)
            n = put("self", n, nn @ (r.body_point_jac(bg, ft[3:], d) - r.body_point_jac(ba, ft[:3], d)),
                    dist - c["self_margin_m"])
        band, n, x = c["foot_band_m"], 0, c["hard_rows_scale"]   # soles on the floor
        for f, z in zip(r.feet, r.soles()):
            Jz = r.body_point_jac(f, r.data.xpos[f], d)[2]
            n = put("feet", put("feet", n, x * Jz, x * (z + band)), -x * Jz, x * (band - z))
        lim, n = np.sin(r.tilt_limit), 0                          # |pitch|, |roll| (about) within the limit
        tilt = r.tilt()
        rate = tilt - tilt1 if q1 is not None else np.zeros(2)
        for axis, s_, w in zip(np.eye(3)[:2], tilt, rate):
            Ja = x * r.axis_jac(r.base, axis, d)[2]
            n = put("tilt", put("tilt", n, -Ja, x * held(lim - s_, -w, a_ang)), Ja, x * held(lim + s_, w, a_ang))
        return G, h

    @staticmethod
    def _critical(s: np.ndarray, act: float, k: int) -> np.ndarray:
        cand = np.flatnonzero(s < act)
        return cand[np.argsort(s[cand])][:k]

    def box(self, q, q1, q2, fps: float, rho: float) -> tuple[np.ndarray, np.ndarray]:
        """Step bounds: joint limits, the trunk's height range (with room to stop), speeds (from q1), the trunk's
        accelerations (from q1 and q2) and the trust region's box."""
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
            a = r.accel[r.groups["base"][2]] / fps**2                  # the height range: room to stop
            lo[z] = max(lo[z], -held(h - r.height_range[0], v[z][0], a))
            hi[z] = min(hi[z], held(r.height_range[1] - h, -v[z][0], a))
            if q2 is not None:                                          # |(q + dx - q1) - (q1 - q2)| <= accel / fps^2
                dv, ac = r.difference(q2, q1, d) - v, r.accel[d] / fps**2
                lo, hi = np.maximum(lo, dv - ac), np.minimum(hi, dv + ac)
        # The start (q1 extrapolated) can lie outside a bound, which the step then has to fix; where two bounds
        # disagree, the step closest to 0 between them.
        lo, hi = np.minimum(lo, rho), np.maximum(hi, -rho)
        bad = lo > hi
        lo[bad] = hi[bad] = np.clip(0.0, hi[bad], lo[bad])
        return lo, hi

    # ------------------------------------------------------------------ a clip
    def start(self, c: HOIClip) -> np.ndarray:
        """Home with the trunk over the human's pelvis, facing the human (shoulder line x vertical), at the nominal
        height (the soles on the floor)."""
        k = self.cfg["relation"]["human_smooth_s"]
        pel = smooth(c.joint("pelvis"), c.fps, k)[0]
        sh = smooth(c.joint("l_shoulder") - c.joint("r_shoulder"), c.fps, k)[0]
        return self.robot.placed(pel[:2], float(np.arctan2(-sh[0], sh[1])))

    def solve(self, c: HOIClip, task, relation, log=None) -> dict:
        """Solve every frame of a clip whose floor is at z = 0 (``hoi.leveled``). Returns the configurations and, per
        frame, the iterations, the last step, the largest slack and whether every QP solved."""
        r, sq = self.robot, self.cfg["sqp"]
        self.fps = c.fps
        ov = np.asarray(c.obj_verts, float)
        hull, verts = ObjectHull.from_vertices(ov), ov[ConvexHull(ov).vertices]
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
                G, h = self.constraints(hull, verts, Ro[t], po[t], q, q1)
                lo, hi = self.box(q, q1, q2, c.fps, sq["trust_region"])
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
