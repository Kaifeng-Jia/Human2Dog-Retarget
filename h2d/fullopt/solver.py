"""Per-frame SQP of the full-optimization line (fullopt spec v0.2 §7).

Frame by frame, the robot configuration q_t minimises

    w_rel E_rel + w_task g_t E_task + E_nom + E_foot + |q_t - q_t-1|^2_Wv + |q_t - 2 q_t-1 + q_t-2|^2_Wa

* E_rel: the relation term (``h2d/fullopt/relation.py``);
* E_task: contact point, two-point direction (lever 0.05 m) and a soft roll (0.02 m), gated by the task's gate g_t
  (``h2d/fullopt/task.py``); a grasp: the point between the pads (its error along the closing axis weighted by
  ``grasp_c``), the approach and closing axes as two-point rows, the arm at rest until the gate rises, the gripper on
  its schedule;
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
for every frame and clip; every solve starts from a fresh solver state, so a frame's result does not depend on what
was solved before it. The SQP is globalised (``Solver._frame``): an L1 merit (the objective plus the slack weight
times the rows' violation), a step accepted only when the merit drops by a share of the predicted drop, a second-order
correction for steps along curved active rows, and a trust region that shrinks on a rejection and grows when the
model agrees. A frame is converged when the QP's step falls below ``tol`` inside the trust region; the frame's
output is its last accepted iterate.

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
    """min |A dx - b|^2 + w sum(s)  s.t.  G dx + h + s >= 0,  s >= 0,  lo <= dx <= hi,  |dx| <= rho.

    Compiled once (DPP); every solve starts from a fresh Clarabel state (cvxpy's default warm start keeps the solver of
    the previous call, so a frame's result depended on what was solved before it, R027b)."""

    def __init__(self, n: int, m: int, k: int, slack_weight: float):
        self.A, self.b, self.G, self.h = cp.Parameter((m, n)), cp.Parameter(m), cp.Parameter((k, n)), cp.Parameter(k)
        self.lo, self.hi, self.rho = cp.Parameter(n), cp.Parameter(n), cp.Parameter(nonneg=True)
        self.dx, self.s = cp.Variable(n), cp.Variable(k, nonneg=True)
        cost = cp.sum_squares(self.A @ self.dx - self.b) + slack_weight * cp.sum(self.s)
        self.problem = cp.Problem(cp.Minimize(cost), [self.G @ self.dx + self.h + self.s >= 0, self.dx >= self.lo,
                                                      self.dx <= self.hi, cp.SOC(self.rho, self.dx)])

    def solve(self, A, b, G, h, lo, hi, rho) -> tuple[np.ndarray, float, bool, float]:
        """Step, largest slack, solved, the model's value at the step."""
        for p, v in zip((self.A, self.b, self.G, self.h, self.lo, self.hi, self.rho), (A, b, G, h, lo, hi, rho)):
            p.value = v
        try:
            self.problem.solve(solver=cp.CLARABEL, warm_start=False)
        except cp.SolverError:
            return np.zeros(self.dx.shape), float("nan"), False, float("nan")
        if self.dx.value is None:
            return np.zeros(self.dx.shape), float("nan"), False, float("nan")
        return np.asarray(self.dx.value), float(np.max(self.s.value, initial=0.0)), True, float(self.problem.value)


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
        self.s_rest = np.sqrt(w["grasp_arm_rest"]) * np.isin(self.dofs, robot.groups["arm"])
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
        if task.grip == "grasp":
            rows += self._grasp_rows(t, task, g)
        elif g > 0:
            sw, lev, rm = np.sqrt(w["task"] * g), w["lever_m"], w["roll_m"]
            p = r.tool_point(task.tool_offset)
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
        if task.grip == "grasp":       # the arm rests at home until the gate rises (it would fold against its limits
            rows.append((r.difference(r.home, q, d), eye, self.s_rest * np.sqrt(1.0 - g)))   # chasing the hand)
        v = r.difference(q1, q, d) if q1 is not None else np.zeros(self.n)
        Jv = r.difference_jac(q1, q, d) if q1 is not None else eye   # (rotations: exact, not the identity)
        rows.append((v, Jv, self.sv * (q1 is not None)))
        a = v - r.difference(q2, q1, d) if q2 is not None else np.zeros(self.n)
        rows.append((a, Jv, self.sa * (q2 is not None)))
        res = np.concatenate([np.reshape(s, -1) * np.asarray(e) for e, _, s in rows])
        jac = np.vstack([np.reshape(s, (-1, 1)) * J for _, J, s in rows])
        return res, jac

    def _grasp_rows(self, t: int, task, g: float) -> list:
        """A grasp's task rows, gated: the point between the pads (its error along the closing axis weighted by
        ``grasp_c``) and the approach and closing axes as two-point rows (lever ``grasp_lever_m``)."""
        if g <= 0:
            return [(np.zeros(3), np.zeros((3, self.n)), 0.0)] * 3
        r, d, w = self.robot, self.dofs, self.cfg["weights"]
        lev, sw = w["grasp_lever_m"], np.sqrt(w["task"] * g)
        p, y, c = r.tool_point(task.tool_offset), task.target[t], task.tool_z[t]
        Jp = r.body_point_jac(r.tool_body, p, d)
        W = np.eye(3) + (np.sqrt(w["grasp_c"]) - 1.0) * np.outer(c, c)
        rows = [(W @ (p - y), W @ Jp, sw)]
        for local, ref in ((r.approach_local, task.tool_x[t]), (r.jaw_local, c)):
            rows.append((p + lev * r.axis(r.tool_body, local) - (y + lev * ref),
                         Jp + lev * r.axis_jac(r.tool_body, local, d), sw))
        return rows

    def _samples(self) -> tuple[np.ndarray, np.ndarray]:
        """World samples kept out of the object (body, arm without the tool, the under-body box) and their bodies."""
        r = self.robot
        P, B = self.coll.world_samples(self.obj_geoms)
        if r.cage is None:
            return P, B
        return np.vstack([P, r.cage_points()]), np.r_[B, np.full(len(r.cage["samples"]), r.cage["body"])]

    def constraints(self, hull: ObjectHull, verts: np.ndarray, Ro: np.ndarray, po: np.ndarray, q, q1, sel=None):
        """G dx + h >= 0: the most critical object, under-body, floor and self rows, then every sole and the tilt
        (unused rows: 0 dx + 1 >= 0). ``verts``: the object's hull vertices (local frame). With the previous frame q1,
        the rows on what the trunk carries (body, under-body box) and the tilt are ``held`` at the trunk's
        accelerations, their rate being the change since q1 with the object held still. Returns G, h and the rows'
        selection; given a selection (``sel``), the same rows are evaluated (the second-order correction)."""
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
            s1 = (((P1 - po) @ Ro) @ hull.A.T + hull.b).max(1) - margin     # (its own face: continuous)
            s = np.where(self._braked, held(s, s - s1, a_lin), s)
        out = {}
        n, out["object"] = 0, self._critical(s, act, k["object"]) if sel is None else sel["object"]
        for j in out["object"]:
            n = put("object", n, (Ro @ hull.A[f[j]]) @ r.body_point_jac(B[j], P[j], d), s[j])
        if r.cage is not None:                                    # the object's corners outside the under-body box
            V = verts @ Ro.T + po
            sd, nrm = r.outside_cage(V)
            sd = sd - c["cage_margin_m"]
            if q1 is not None:
                sd = held(sd, sd - (sd1 - c["cage_margin_m"]), a_lin)
            n, out["cage"] = 0, self._critical(sd, act, k["cage"]) if sel is None else sel["cage"]
            for j in out["cage"]:
                n = put("cage", n, -nrm[j] @ r.body_point_jac(r.cage["body"], V[j], d), sd[j])
        P, B = self.coll.world_samples(self.floor_geoms)          # above the floor
        z = P[:, 2] - c["floor_clearance_m"]
        n, out["floor"] = 0, self._critical(z, act, k["floor"]) if sel is None else sel["floor"]
        for j in out["floor"]:
            n = put("floor", n, r.body_point_jac(B[j], P[j], d)[2], z[j])
        near = (sorted(self.coll.self_distances(act), key=lambda x: x[0])[: k["self"]] if sel is None else
                self.coll.self_distances(act, sel["self"]))
        n, out["self"], body = 0, [], self.robot.model.geom_bodyid
        for dist, ft, a, g in near:                               # arm against itself and the body
            v = ft[3:] - ft[:3]
            out["self"].append((a, g))
            if np.linalg.norm(v) < 1e-9:                          # (a held slot: the rows keep their places)
                n += 1
                continue
            nn = v / np.linalg.norm(v) * (1.0 if dist >= 0 else -1.0)
            n = put("self", n, nn @ (r.body_point_jac(body[g], ft[3:], d) - r.body_point_jac(body[a], ft[:3], d)),
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
        self._tol = np.full(len(h), c["feasibility_tol"])       # the merit's tolerance per row, in its units
        self._tol[i0["feet"]:] *= x
        return G, h, out

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
        # disagree, the step closest to 0 between them. Outside by less than feasibility_tol counts as inside: a
        # rotation's step and its difference agree to first order only, and fixing that would force steps.
        tol = self.cfg["constraints"]["feasibility_tol"]
        lo, hi = np.where((lo > 0) & (lo < tol), 0.0, lo), np.where((hi < 0) & (hi > -tol), 0.0, hi)
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

    def _linearise(self, t, q, q1, q2, task, relation, frame) -> dict:
        """Residuals, constraint rows and the L1 merit (objective + slack weight x violation of the slacked rows, the
        hard rows' scale included) at q."""
        self.robot.set(q)
        res, jac = self.objective(t, q, q1, q2, task, relation)
        G, h, sel = self.constraints(*frame, q, q1)
        return {"q": q, "res": res, "jac": jac, "G": G, "h": h, "sel": sel, "merit": self._merit(res, h)}

    def _merit(self, res: np.ndarray, h: np.ndarray) -> float:
        """|res|^2 + slack weight x the rows' violation beyond ``feasibility_tol``. The QP holds the rows exactly (a
        row already within the tolerance as it stands), so the iterates keep that margin, and the distances' numerical
        noise (1e-9 m, times the weight) does not decide a step."""
        w = self.cfg["constraints"]["slack_weight"]
        return float(res @ res) + w * float(np.maximum(-(h + self._tol), 0.0).sum())

    def _corrected(self, t, cur, dx, trial, q1, q2, task, relation, frame, lo, hi, rad):
        """Second-order correction of a rejected step (Fletcher): the QP again, with the rows' offsets moved by what
        their linearisation missed at the trial point (the same rows), so a step along curved active rows (soles,
        tilt, self pairs) is not lost to the merit's large weights. Returns the corrected trial (None if its QP
        failed)."""
        self.robot.set(trial["q"])
        h_trial = self.constraints(*frame, trial["q"], q1, sel=cur["sel"])[1]
        dx2, _, ok, _ = self._step_qp(len(cur["res"])).solve(cur["jac"], -cur["res"], cur["G"],
                                                             h_trial - cur["G"] @ dx, lo, hi, rad)
        if not ok:
            return None
        return self._linearise(t, self.robot.integrate(cur["q"], dx2, self.dofs), q1, q2, task, relation, frame)

    def _frame(self, t, q, q1, q2, task, relation, frame, iters: int) -> dict:
        """Trust-region SQP on one frame from q: a step is accepted when the merit's actual decrease is at least
        ``accept`` of the decrease the QP predicts; the radius shrinks on a rejection and grows when the model agrees
        and the step reached it. A step the bounds force (the start outside one, ``box``) is taken without the test.
        The frame stops, converged, on the first of: a step below ``tol`` inside the radius; an accepted step that
        changes the merit by at most ``merit_rtol`` of it (OmniRetarget's stop on the cost); the radius shrunk below
        ``trust_region_min`` with no row violated beyond ``violation_max`` (scipy trust-constr's xtol stop, IPOPT's
        constr_viol_tol). Otherwise it stops at the iteration cap, unconverged. Returns the last accepted iterate and
        the frame's record."""
        sq, fps = self.cfg["sqp"], self.fps
        rad = sq["trust_region"]
        cur = self._linearise(t, q, q1, q2, task, relation, frame)
        rec = {"iters": 0, "rejected": 0, "corrections": 0, "converged": False, "stop": "cap", "step": 0.0,
               "slack": 0.0, "ok": True}
        for it in range(iters):
            rec["iters"] = it + 1
            lo, hi = self.box(cur["q"], q1, q2, fps, rad)
            h_qp = np.where((cur["h"] < 0) & (cur["h"] > -self._tol), 0.0, cur["h"])   # met within the tolerance
            dx, slack, ok, _ = self._step_qp(len(cur["res"])).solve(cur["jac"], -cur["res"], cur["G"], h_qp,
                                                                   lo, hi, rad)
            rec["ok"] &= ok
            step = float(np.linalg.norm(dx))
            pred = cur["merit"] - self._merit(cur["res"] + cur["jac"] @ dx, cur["h"] + cur["G"] @ dx)
            inside = step < 0.99 * rad
            if ok and inside and step < sq["tol"]:
                rec.update(converged=True, stop="step", step=step, slack=slack)
                break
            new = self._linearise(t, self.robot.integrate(cur["q"], dx, self.dofs), q1, q2, task, relation, frame) \
                if ok else None
            forced = bool(np.any(lo > 0) or np.any(hi < 0))
            if ok and not forced and pred > 0 and cur["merit"] - new["merit"] < sq["accept"] * pred:
                new = self._corrected(t, cur, dx, new, q1, q2, task, relation, frame, lo, hi, rad)
                rec["corrections"] += new is not None
            if ok and new is not None and (forced or (pred > 0 and cur["merit"] - new["merit"] >= sq["accept"] * pred)):
                if cur["merit"] - new["merit"] >= sq["expand_above"] * pred and not inside:
                    rad = min(2.0 * rad, sq["trust_region_max"])
                flat = not forced and cur["merit"] - new["merit"] <= sq["merit_rtol"] * abs(new["merit"]) + 1e-8
                cur = new
                rec.update(step=step, slack=slack)
                if flat:
                    rec.update(converged=True, stop="merit")
                    break
            else:                                           # (the radius from the QP's step, not the correction's)
                rec["rejected"] += 1
                rad = 0.25 * (step if ok else rad)
                if rad < sq["trust_region_min"]:
                    scale = self._tol / self.cfg["constraints"]["feasibility_tol"]     # (the hard rows' scale)
                    rec.update(converged=bool(np.all(cur["h"] >= -sq["violation_max"] * scale)), stop="radius")
                    break
        rec["radius"] = rad
        return cur["q"], rec

    def solve(self, c: HOIClip, task, relation, log=None) -> dict:
        """Solve every frame of a clip whose floor is at z = 0 (``hoi.leveled``). Returns the configurations and, per
        frame, the iterations, rejected steps, whether it converged and why it stopped (step, merit, radius, cap), the
        last accepted step, the final radius, the largest slack and whether every QP solved."""
        r, sq = self.robot, self.cfg["sqp"]
        self.fps = c.fps
        ov = np.asarray(c.obj_verts, float)
        hull, verts = ObjectHull.from_vertices(ov), ov[ConvexHull(ov).vertices]
        Ro, po = R.from_quat(c.obj_quat).as_matrix(), c.obj_pos
        T = c.n
        out = {"q": np.zeros((T, r.model.nq)), "iters": np.zeros(T, int), "rejected": np.zeros(T, int),
               "converged": np.zeros(T, bool), "stop": np.full(T, "", "<U6"), "step": np.zeros(T),
               "radius": np.zeros(T), "slack_max": np.zeros(T), "qp_ok": np.ones(T, bool)}
        t0 = time.time()
        q1 = q2 = None
        for t in range(T):
            if t == 0:
                q = self.start(c)
            else:
                v = r.difference(q2, q1, self.dofs) if q2 is not None else np.zeros(self.n)
                q = r.clip(r.integrate(q1, v, self.dofs))
            if task.theta is not None:                           # a grasp's gripper, on its schedule
                q = r.opened(q, task.theta[t])
            q, rec = self._frame(t, q, q1, q2, task, relation, (hull, verts, Ro[t], po[t]),
                                 sq["first_frame_iters"] if t == 0 else sq["max_iters"])
            out["q"][t] = q
            for k, key in (("iters", "iters"), ("rejected", "rejected"), ("converged", "converged"), ("stop", "stop"),
                           ("step", "step"), ("radius", "radius"), ("slack_max", "slack"), ("qp_ok", "ok")):
                out[k][t] = rec[key]
            q2, q1 = q1, q
            if log and (t % 50 == 0 or t == T - 1):
                log(f"    frame {t + 1}/{T}: {out['iters'][t]} iterations, {time.time() - t0:.1f} s")
        out["time_s"] = time.time() - t0
        return out
