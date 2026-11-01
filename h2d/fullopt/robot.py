"""A robot read from its description (fullopt spec v0.2 §7.4): the solver, the evaluation and the videos see the robot
only through this module and ``configs/fullopt/robots/<name>.yaml``.

Configuration ``q``: the MuJoCo qpos (free base [x y z, qw qx qy qz], then the joints). Increments ``dx`` live in the
tangent space as MuJoCo velocities: base translation (world frame), base rotation (base frame), joint angles.
``dofs("base", "arm")`` picks the variables of a solve (pass 1: base 6 + arm 6; pass 2: base 6 + legs 12 + arm 6,
spec §7.3); Jacobians are d(point) / d(dx) from ``mj_jac``, and ``integrate`` / ``difference`` are MuJoCo's
``mj_integratePos`` / ``mj_differentiatePos``, so a step and a Jacobian always agree.

``Collision`` applies the learned line's collision rules (``h2d/common/collision.py``: which pairs, which sample
points, which tolerance) to the groups the description names, so both lines measure penetration the same way.
"""

from __future__ import annotations

import mujoco
import numpy as np

from h2d.common.collision import _geom_samples
from h2d.paths import load_config, xmorph_path

GROUPS = ("base", "legs", "arm")


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
        lim = d["base_speed_limit"]
        self.speed[b[:3]], self.speed[b[3:]] = lim["linear_mps"], lim["angular_radps"]
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
        self._jp, self._jr = np.zeros((3, m.nv)), np.zeros((3, m.nv))
        self.set(self.home)

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


class Collision:
    """Collision groups of the description with the rules of ``h2d.common.collision.RobotCollision``:

    * arm: the collision geoms of the arm chain after its first (fixed) link; tool: those the description marks;
      floor: geoms of the world body; body: everything else (trunk, legs, the arm's mount);
    * self-collision pairs: arm against body and arm against arm, skipping links fewer than two apart in the chain
      and pairs that already overlap in the model's folded reference pose (qpos0, base lifted 1 m);
    * object: sample points of the geoms (primitive surfaces, hull vertices of meshes) against the object's convex
      hull; the tool may touch it, so its depth is reported apart.
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

    def world_samples(self, geoms) -> tuple[np.ndarray, np.ndarray]:
        """Sample points (n, 3) of the geoms at the current state and the body each belongs to (n,)."""
        d = self.robot.data
        P = [self.samples[g] @ d.geom_xmat[g].reshape(3, 3).T + d.geom_xpos[g] for g in geoms]
        b = [np.full(len(self.samples[g]), self.robot.model.geom_bodyid[g]) for g in geoms]
        return (np.concatenate(P), np.concatenate(b)) if geoms else (np.zeros((0, 3)), np.zeros(0, int))

    def self_distances(self, margin: float) -> list[tuple[float, np.ndarray, int, int]]:
        """(distance, fromto, body a, body g) of the self-collision pairs closer than ``margin`` (bounding spheres
        first)."""
        m, d = self.robot.model, self.robot.data
        P = np.array(self.pairs)
        gap = (np.linalg.norm(d.geom_xpos[P[:, 0]] - d.geom_xpos[P[:, 1]], axis=1)
               - m.geom_rbound[P[:, 0]] - m.geom_rbound[P[:, 1]])
        out = []
        for a, g in P[gap < margin]:
            ft = np.zeros(6)
            dist = mujoco.mj_geomDistance(m, d, int(a), int(g), margin, ft)
            if dist < margin:
                out.append((float(dist), ft, int(m.geom_bodyid[a]), int(m.geom_bodyid[g])))
        return out

    def check(self, hull=None, to_local=None, distmax: float = 0.05) -> dict:
        """The learned line's check (``RobotCollision.check``) at the current state: closest self pair, arm to floor,
        depth of the arm (without the tool), the tool and the body in the object's hull; collision free when no self
        or floor pair penetrates and the arm stays out of the object, each within ``tol``."""
        m, d = self.robot.model, self.robot.data
        ft = np.zeros(6)
        self_min, worst = distmax, None
        for a, g in self.pairs:
            dist = mujoco.mj_geomDistance(m, d, a, g, distmax, ft)
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
