"""A robot read from its description (fullopt spec v0.2 §7.4): the solver, the evaluation and the videos see the robot
only through this module and ``configs/fullopt/robots/<name>.yaml``.

Configuration ``q``: the MuJoCo qpos (free base [x y z, qw qx qy qz], then the joints). Increments ``dx`` live in the
tangent space as MuJoCo velocities: base translation (world frame), base rotation (base frame), joint angles.
``dofs("base", "legs", "arm")`` picks the variables of a solve (spec §7.3); Jacobians are d(point) / d(dx) from
``mj_jac``, and ``integrate`` / ``difference`` are MuJoCo's ``mj_integratePos`` / ``mj_differentiatePos``, so a step
and a Jacobian always agree. The description also gives the feet (soles, home stance in the trunk frame) and the
under-body box, a virtual volume on the trunk that the object may not enter.

``Collision`` applies the learned line's collision rules (``h2d/common/collision.py``: which pairs, which sample
points, which tolerance) to the groups the description names, so both lines measure penetration the same way, and
cross-checks MuJoCo's negative distances (``Collision.distance``).
"""

from __future__ import annotations

import mujoco
import numpy as np
from scipy.spatial import ConvexHull

from h2d.common.collision import _geom_samples
from h2d.paths import load_config, xmorph_path

GROUPS = ("base", "legs", "arm")
WITNESS_TOL_M = 1e-3   # mj_geomDistance's witness points (fromto): |distance| apart, on their geoms
JITTER_M = (1e-7, 1e-6, 1e-5)


class Robot:
    def __init__(self, name: str = "b2z1"):
        d = load_config(f"fullopt/robots/{name}.yaml")
        self.desc, self.name = d, d["name"]
        self.model = mujoco.MjModel.from_xml_path(str(xmorph_path(load_config("b2z1.yaml")["xmorph"][d["model_xml"]])))
        self.data = mujoco.MjData(self.model)
        m = self.model
        self.base = self.body_id(d["base_body"])
        free = int(m.body_jntadr[self.base])
        self.base_qadr = int(m.jnt_qposadr[free])           # [x y z, qw qx qy qz] of the floating base
        jid = {n: self._jid(n) for n in d["legs"] + d["arm"] + list(d["locked"])}
        self.groups = {"base": np.arange(m.jnt_dofadr[free], m.jnt_dofadr[free] + 6),
                       "legs": np.array([m.jnt_dofadr[jid[n]] for n in d["legs"]], int),
                       "arm": np.array([m.jnt_dofadr[jid[n]] for n in d["arm"]], int)}
        self.qadr = {n: int(m.jnt_qposadr[j]) for n, j in jid.items()}
        self.lower, self.upper = np.full(m.nv, -np.inf), np.full(m.nv, np.inf)
        self.speed = np.full(m.nv, np.inf)
        self.dof_qadr = np.full(m.nv, -1)                 # qpos index of each joint dof (-1: the free base)
        for n in d["legs"] + d["arm"]:
            self.lower[m.jnt_dofadr[jid[n]]], self.upper[m.jnt_dofadr[jid[n]]] = m.jnt_range[jid[n]]
            self.dof_qadr[m.jnt_dofadr[jid[n]]] = self.qadr[n]
        for n, v in d.get("speed_limit_rad_s", {}).items():
            self.speed[m.jnt_dofadr[jid[n]]] = v
        b = self.groups["base"]
        self.accel = np.full(m.nv, np.inf)                 # trunk only (the description's base_accel_limit)
        for lim, k, arr in (("base_speed_limit", "mps", self.speed), ("base_accel_limit", "mps2", self.accel)):
            if lim in d:
                arr[b[:3]], arr[b[3:]] = d[lim][f"linear_{k}"], d[lim][f"angular_rad{k[1:]}"]
        self.tilt_limit = np.radians(float(d.get("tilt_limit_deg", 90.0)))
        self.forward = np.asarray(d["forward_axis"], float)
        self.nominal_height = float(d["nominal_base_height_m"])
        self.height_range = tuple(float(x) for x in d["base_height_range_m"])
        home = m.key_qpos[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_KEY, d["home_key"])].copy()
        for n, v in d["locked"].items():
            home[self.qadr[n]] = v
        home[self.base_qadr + 2] = self.nominal_height
        self.home = home
        t = d["tool"]
        self.tool_body = self.body_id(t["body"])
        self.r_c, self.approach_local, self.jaw_local = (np.asarray(t[k], float) for k in
                                                         ("contact_point", "approach_axis", "jaw_axis"))
        self.points = {}
        for k, p in d["points"].items():
            if "mean_of" in p:
                self.points[k] = ([self.body_id(b) for b in p["mean_of"]], None, bool(p.get("on_floor")))
            else:
                self.points[k] = ([self.body_id(p["body"])], np.asarray(p.get("offset", [0, 0, 0]), float), False)
        self.point_names = list(self.points)
        self.feet = [self.body_id(b) for b in d["feet"].values()]
        self.foot_radius = float(d["foot_radius_m"])
        self._jp, self._jr = np.zeros((3, m.nv)), np.zeros((3, m.nv))
        self.set(self.home)
        Rb, xb = self.base_rot(), self.data.xpos[self.base]
        self.foot_home = (self.data.xpos[self.feet] - xb) @ Rb      # home stance in the trunk frame, (4, 3)
        ub = d.get("under_body")
        self.cage = None
        if ub:
            c, h = np.asarray(ub["center"], float), np.asarray(ub["half_size"], float)
            axes = [np.linspace(-hi, hi, max(2, int(np.ceil(2 * hi / ub["spacing_m"])) + 1)) for hi in h]
            grid = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3) + c
            self.cage = {"body": self.body_id(ub["body"]), "center": c, "half": h, "samples": grid}

    # ------------------------------------------------------------------ ids
    def body_id(self, name: str) -> int:
        i = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, name)
        if i < 0:
            raise KeyError(f"body {name!r} not in the model")
        return i

    def body_name(self, i: int) -> str:
        return mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_BODY, int(i))

    def _jid(self, name: str) -> int:
        i = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, name)
        if i < 0:
            raise KeyError(f"joint {name!r} not in the model")
        return i

    def dofs(self, *groups: str) -> np.ndarray:
        return np.concatenate([self.groups[g] for g in groups])

    # ---------------------------------------------------------------- state
    def set(self, q: np.ndarray) -> None:
        self.data.qpos[:] = q
        mujoco.mj_kinematics(self.model, self.data)
        mujoco.mj_comPos(self.model, self.data)

    def integrate(self, q: np.ndarray, dx: np.ndarray, dofs: np.ndarray) -> np.ndarray:
        v = np.zeros(self.model.nv)
        v[dofs] = dx
        out = np.array(q, float)
        mujoco.mj_integratePos(self.model, out, v, 1.0)
        return out

    def difference(self, q0: np.ndarray, q1: np.ndarray, dofs: np.ndarray) -> np.ndarray:
        """q1 - q0 in the tangent space (the increment that takes q0 to q1)."""
        v = np.zeros(self.model.nv)
        mujoco.mj_differentiatePos(self.model, v, 1.0, np.asarray(q0, float), np.asarray(q1, float))
        return v[dofs]

    def difference_jac(self, q0: np.ndarray, q1: np.ndarray, dofs: np.ndarray) -> np.ndarray:
        """d difference(q0, q1 + dx) / d dx at dx = 0: the identity but for the base's rotation, J_r^-1(phi) with phi
        the rotation from q0 to q1 (local frame, as ``mj_integratePos`` steps it)."""
        J = np.eye(len(dofs))
        rot = self.groups["base"][3:]
        idx = np.flatnonzero(np.isin(dofs, rot))
        if len(idx) == 3:
            phi = self.difference(q0, q1, rot)
            th, K = float(np.linalg.norm(phi)), np.array([[0, -phi[2], phi[1]], [phi[2], 0, -phi[0]],
                                                          [-phi[1], phi[0], 0]])
            c = 1.0 / 12.0 if th < 1e-6 else 1.0 / th**2 - (1.0 + np.cos(th)) / (2.0 * th * np.sin(th))
            J[np.ix_(idx, idx)] = np.eye(3) + 0.5 * K + c * K @ K
        return J

    def clip(self, q: np.ndarray) -> np.ndarray:
        """q with every joint inside its range and the trunk inside its height range."""
        j = self.dof_qadr >= 0
        out = np.array(q, float)
        out[self.dof_qadr[j]] = np.clip(out[self.dof_qadr[j]], self.lower[j], self.upper[j])
        out[self.base_qadr + 2] = np.clip(out[self.base_qadr + 2], *self.height_range)
        return out

    def placed(self, xy, yaw: float, z: float | None = None) -> np.ndarray:
        """The home configuration with the base at (x, y, z) turned by yaw about the vertical."""
        q, b = self.home.copy(), self.base_qadr
        q[b:b + 2], q[b + 2] = xy, self.nominal_height if z is None else z
        q[b + 3:b + 7] = [np.cos(yaw / 2), 0.0, 0.0, np.sin(yaw / 2)]
        return q

    # ---------------------------------------------------------- kinematics
    def base_rot(self) -> np.ndarray:
        return self.data.xmat[self.base].reshape(3, 3).copy()

    def heading(self) -> np.ndarray:
        """Horizontal unit heading of the trunk."""
        f = (self.base_rot() @ self.forward)[:2]
        return f / max(float(np.linalg.norm(f)), 1e-12)

    def point(self, name: str, floor_z: float = 0.0) -> np.ndarray:
        bodies, off, on_floor = self.points[name]
        if off is not None:
            return self.data.xpos[bodies[0]] + self.data.xmat[bodies[0]].reshape(3, 3) @ off
        p = self.data.xpos[bodies].mean(0)
        if on_floor:
            p[2] = floor_z
        return p

    def body_point_jac(self, body: int, p: np.ndarray, dofs: np.ndarray) -> np.ndarray:
        mujoco.mj_jac(self.model, self.data, self._jp, None, np.asarray(p, float), int(body))
        return self._jp[:, dofs].copy()

    def point_jac(self, name: str, dofs: np.ndarray) -> np.ndarray:
        bodies, off, on_floor = self.points[name]
        if off is not None:
            return self.body_point_jac(bodies[0], self.point(name), dofs)
        J = np.mean([self.body_point_jac(b, self.data.xpos[b], dofs) for b in bodies], axis=0)
        if on_floor:
            J[2] = 0.0
        return J

    def axis(self, body: int, local: np.ndarray) -> np.ndarray:
        return self.data.xmat[body].reshape(3, 3) @ local

    def axis_jac(self, body: int, local: np.ndarray, dofs: np.ndarray) -> np.ndarray:
        """d(R a) / d(dx) = omega x (R a), omega = J_rot dx."""
        mujoco.mj_jacBody(self.model, self.data, None, self._jr, int(body))
        return np.cross(self._jr[:, dofs].T, self.axis(body, local)).T

    def tool_point(self) -> np.ndarray:
        return self.data.xpos[self.tool_body] + self.data.xmat[self.tool_body].reshape(3, 3) @ self.r_c

    def soles(self, floor_z: float = 0.0) -> np.ndarray:
        """Height of each sole above the floor, (4,)."""
        return self.data.xpos[self.feet][:, 2] - self.foot_radius - floor_z

    def footholds(self) -> np.ndarray:
        """Nominal footholds (4, 3) on the trunk: the home stance in the trunk frame at the trunk's level (z = 0 there),
        so their horizontal position is the stance under the hips, little changed by roll and pitch."""
        return self.data.xpos[self.base] + (self.foot_home * [1, 1, 0]) @ self.base_rot().T

    def tilt(self) -> np.ndarray:
        """Vertical components of the trunk's forward and lateral axes (sin of pitch and, about, of roll), (2,)."""
        return self.base_rot()[2, :2].copy()

    def cage_frame(self) -> tuple[np.ndarray, np.ndarray]:
        """World rotation and centre of the under-body box."""
        b = self.cage["body"]
        Rb = self.data.xmat[b].reshape(3, 3).copy()
        return Rb, self.data.xpos[b] + Rb @ self.cage["center"]

    def cage_points(self) -> np.ndarray:
        """World sample grid of the under-body box, (n, 3)."""
        b = self.cage["body"]
        return self.data.xpos[b] + self.cage["samples"] @ self.data.xmat[b].reshape(3, 3).T

    def outside_cage(self, P: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Signed distance of world points to the under-body box by its face planes (n,) (> 0 outside; exact inside, a
        lower bound outside) and the world normal of the face that decides it (n, 3)."""
        Rc, c = self.cage_frame()
        loc = (P - c) @ Rc
        s = np.abs(loc) - self.cage["half"]
        i = s.argmax(1)
        n = Rc[:, i].T * np.sign(loc[np.arange(len(P)), i])[:, None]
        return s.max(1), n


class Collision:
    """Collision groups of the description with the rules of ``h2d.common.collision.RobotCollision``:

    * arm: the collision geoms of the arm chain after its first (fixed) link; tool: those the description marks;
      floor: geoms of the world body; body: everything else (trunk, legs, the arm's mount);
    * self-collision pairs: arm against body and arm against arm, skipping links fewer than two apart in the chain
      and pairs that already overlap in the model's folded reference pose (qpos0, base lifted 1 m);
    * object: sample points of the geoms (primitive surfaces, hull vertices of meshes) against the object's convex
      hull; the tool may touch it, so its depth is reported apart;
    * feet: the leg geoms centred on a foot body (the sole spheres), which stand on the floor.

    MuJoCo 3.11's ``mj_geomDistance`` can return a wrong distance for a mesh and a box: negative for two that do not
    touch (R027, clip c10 frame 45: the gripper's stator mesh and the trunk's front plate, -24 mm with witness points
    41 mm apart, the same in both orders, while no vertex of either lies in the other), or exactly 0 for two 24 mm
    apart (R027b dry runs, the gripper's mover and the same plate, witness points 32 mm apart; R027d on Ubuntu, c09
    frame 0, 25.9 mm apart with an all-zero fromto), switching on and off with steps of 1e-5. ``distance`` keeps a
    distance only when its witness points are |distance| apart and each lies on its geom's surface, in one order or
    the other; else it measures again with one geom moved by 0.1, 1 or 10 um (the error the move adds), and only
    then estimates the pair by sample points, as the object check does (an estimate a few mm off would make the
    distance jump as the pose moves in and out of the bug).
    """

    def __init__(self, robot: Robot, tol_m: float = 0.002):
        self.robot, self.tol = robot, tol_m
        m, c = robot.model, robot.desc["collision"]
        coll = [g for g in range(m.ngeom) if m.geom_contype[g] or m.geom_conaffinity[g]]
        self.body_of = {g: robot.body_name(m.geom_bodyid[g]) for g in coll}
        chain = {b: i for i, b in enumerate(c["arm_chain"])}
        self.floor = [g for g in coll if m.geom_bodyid[g] == 0]
        self.arm = [g for g in coll if self.body_of[g] in c["arm_chain"][1:]]
        self.tool = [g for g in self.arm if self.body_of[g] in c["tool"]]
        self.body = [g for g in coll if g not in self.arm and g not in self.floor]
        self.legs = [g for g in self.body if self.body_of[g] in c["leg_bodies"]]
        self.feet = [g for g in self.legs for f in robot.feet if m.geom_bodyid[g] == m.body_parentid[f]
                     and np.linalg.norm(m.geom_pos[g] - m.body_pos[f]) < 1e-3]
        apart = lambda a, g: abs(chain[self.body_of[a]] - chain.get(self.body_of[g], -9)) >= 2  # noqa: E731
        pairs = [(a, g) for a in self.arm for g in self.body if apart(a, g)]
        pairs += [(a, g) for a in self.arm for g in self.arm if g > a and apart(a, g)]
        saved = robot.data.qpos.copy()
        q0 = m.qpos0.copy()
        q0[2] += 1.0
        robot.set(q0)
        ft = np.zeros(6)
        self.excluded = sorted({(self.body_of[a], self.body_of[g]) for a, g in pairs
                                if mujoco.mj_geomDistance(m, robot.data, a, g, 0.05, ft) < tol_m})
        self.pairs = [(a, g) for a, g in pairs if (self.body_of[a], self.body_of[g]) not in self.excluded]
        robot.set(saved)
        self.samples = {g: _geom_samples(m, g) for g in self.arm + self.body}
        self._planes = {g: ConvexHull(self.samples[g]).equations for g in self.samples
                        if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH}
        self.retries = self.fallbacks = 0                     # distances ``distance`` re-measured / estimated

    def _sdf(self, g: int, P: np.ndarray) -> np.ndarray:
        """Signed distance (< 0 inside) of points in geom g's frame; a mesh by the planes of its convex hull."""
        m, T = self.robot.model, mujoco.mjtGeom
        t, s = m.geom_type[g], m.geom_size[g]
        if t == T.mjGEOM_SPHERE:
            return np.linalg.norm(P, axis=1) - s[0]
        if t == T.mjGEOM_CAPSULE:
            return np.linalg.norm(P - np.c_[0 * P[:, :2], np.clip(P[:, 2], -s[1], s[1])], axis=1) - s[0]
        if t == T.mjGEOM_CYLINDER:
            q = np.stack([np.linalg.norm(P[:, :2], axis=1) - s[0], np.abs(P[:, 2]) - s[1]], 1)
        elif t == T.mjGEOM_BOX:
            q = np.abs(P) - s
        elif t == T.mjGEOM_MESH:
            return (P @ self._planes[g][:, :3].T + self._planes[g][:, 3]).max(1)
        else:
            raise NotImplementedError(f"geom type {t}")
        return np.linalg.norm(np.maximum(q, 0.0), axis=1) + np.minimum(q.max(1), 0.0)

    def _by_samples(self, a: int, g: int) -> tuple[float, np.ndarray]:
        """Distance of a pair from each geom's sample points against the other's signed distance (< 0: the deepest
        sample), with witness points on a and on g as ``mj_geomDistance`` orders them."""
        d, best = self.robot.data, None
        for p_geom, o_geom in ((a, g), (g, a)):
            Ro, po = d.geom_xmat[o_geom].reshape(3, 3), d.geom_xpos[o_geom]
            P = (self.samples[p_geom] @ d.geom_xmat[p_geom].reshape(3, 3).T + d.geom_xpos[p_geom] - po) @ Ro
            sd = self._sdf(o_geom, P)
            j = int(sd.argmin())
            if best is None or sd[j] < best[0]:
                e = 1e-6 * np.eye(3)                          # the other geom's surface point: along the SDF gradient
                n = np.array([self._sdf(o_geom, P[j] + e[k:k + 1])[0] - self._sdf(o_geom, P[j] - e[k:k + 1])[0]
                              for k in range(3)])
                n /= max(float(np.linalg.norm(n)), 1e-12)
                pw, qw = po + Ro @ P[j], po + Ro @ (P[j] - sd[j] * n)
                best = (float(sd[j]), np.r_[pw, qw] if p_geom == a else np.r_[qw, pw])
        return best

    def _consistent(self, a: int, g: int, dist: float, ft: np.ndarray, distmax: float) -> bool:
        """At or beyond ``distmax``, or witness points (on a, on g) |dist| apart and each on its geom's surface."""
        if dist >= distmax:
            return True
        d = self.robot.data
        off = [self._sdf(x, ((p - d.geom_xpos[x]) @ d.geom_xmat[x].reshape(3, 3))[None])[0]
               for x, p in ((a, ft[:3]), (g, ft[3:]))]
        return abs(np.linalg.norm(ft[3:] - ft[:3]) - abs(dist)) <= WITNESS_TOL_M and max(map(abs, off)) <= WITNESS_TOL_M

    def distance(self, a: int, g: int, distmax: float) -> tuple[float, np.ndarray]:
        """``mj_geomDistance`` (distance and fromto) cross-checked (see the class): a distance below ``distmax`` is
        kept only when its witness points are |distance| apart and on the two geoms, in one order or the other."""
        m, d = self.robot.model, self.robot.data
        ft = np.zeros(6)
        dist = mujoco.mj_geomDistance(m, d, a, g, distmax, ft)
        if self._consistent(a, g, dist, ft, distmax):
            return float(dist), ft
        ft2 = np.zeros(6)
        dist2 = mujoco.mj_geomDistance(m, d, g, a, distmax, ft2)
        if self._consistent(g, a, dist2, ft2, distmax):
            return float(dist2), np.r_[ft2[3:], ft2[:3]]
        x0 = d.geom_xpos[a].copy()                    # the bug sits on isolated poses: geom a moved by 0.1-10 um
        for e in np.concatenate([np.vstack([np.eye(3), -np.eye(3)]) * k for k in JITTER_M]):
            d.geom_xpos[a] = x0 + e
            dist = mujoco.mj_geomDistance(m, d, a, g, distmax, ft)
            ok = self._consistent(a, g, dist, ft, distmax)
            d.geom_xpos[a] = x0
            if ok:
                self.retries += 1
                return float(dist), np.r_[ft[:3] - e, ft[3:]]
        self.fallbacks += 1
        dist, ft = self._by_samples(a, g)
        return min(dist, distmax), ft

    def world_samples(self, geoms) -> tuple[np.ndarray, np.ndarray]:
        """Sample points (n, 3) of the geoms at the current state and the body each belongs to (n,)."""
        d = self.robot.data
        P = [self.samples[g] @ d.geom_xmat[g].reshape(3, 3).T + d.geom_xpos[g] for g in geoms]
        b = [np.full(len(self.samples[g]), self.robot.model.geom_bodyid[g]) for g in geoms]
        return (np.concatenate(P), np.concatenate(b)) if geoms else (np.zeros((0, 3)), np.zeros(0, int))

    def self_distances(self, margin: float, pairs=None) -> list[tuple[float, np.ndarray, int, int]]:
        """(distance, fromto, geom a, geom g) of the self-collision pairs closer than ``margin`` (bounding spheres
        first), or of the given ``pairs`` whatever their distance (capped at ``margin``)."""
        m, d = self.robot.model, self.robot.data
        given = pairs is not None
        if not given:
            P = np.array(self.pairs)
            gap = (np.linalg.norm(d.geom_xpos[P[:, 0]] - d.geom_xpos[P[:, 1]], axis=1)
                   - m.geom_rbound[P[:, 0]] - m.geom_rbound[P[:, 1]])
            pairs = P[gap < margin]
        out = []
        for a, g in pairs:
            dist, ft = self.distance(int(a), int(g), margin)
            out.append((float(dist), ft, int(a), int(g)))
        return out if given else [x for x in out if x[0] < margin]

    def check(self, hull=None, to_local=None, distmax: float = 0.05) -> dict:
        """The learned line's check (``RobotCollision.check``) at the current state: closest self pair, arm to floor,
        depth of the arm (without the tool), the tool and the body in the object's hull; collision free when no self
        or floor pair penetrates and the arm stays out of the object, each within ``tol``."""
        m, d = self.robot.model, self.robot.data
        ft = np.zeros(6)
        self_min, worst = distmax, None
        for a, g in self.pairs:
            dist = self.distance(a, g, distmax)[0]
            if dist < self_min:
                self_min, worst = dist, (self.body_of[a], self.body_of[g])
        floor_min = min((mujoco.mj_geomDistance(m, d, a, f, distmax, ft) for a in self.arm for f in self.floor),
                        default=distmax)
        out = {"self_min_dist_m": float(self_min), "self_worst_pair": worst, "floor_min_dist_m": float(floor_min)}
        if hull is not None:
            dep = lambda geoms: float(hull.depth(to_local(self.world_samples(geoms)[0])).max())  # noqa: E731
            out.update({"arm_obj_depth_m": dep([g for g in self.arm if g not in self.tool]),
                        "tool_obj_depth_m": dep(self.tool), "body_obj_depth_m": dep(self.body)})
        out["collision_free"] = bool(self_min > -self.tol and floor_min > -self.tol
                                     and out.get("arm_obj_depth_m", 0.0) <= self.tol)
        return out

    def floor_distance(self, distmax: float = 0.05) -> tuple[float, str | None]:
        """Closest geom other than the soles (trunk, legs, arm) to the floor, and its body."""
        m, d = self.robot.model, self.robot.data
        ft, best = np.zeros(6), (distmax, None)
        for a in self.body + self.arm:
            if a in self.feet:
                continue
            for f in self.floor:
                dist = mujoco.mj_geomDistance(m, d, a, f, distmax, ft)
                if dist < best[0]:
                    best = (float(dist), self.body_of[a])
        return best
