"""Collision and penetration checks of a B2-Z1 state against itself, the floor and an object (spec §7.1 "完整碰撞检查").

Robot geometry: the collision geoms of the full MuJoCo model (``B2Z1Robot``), distances from ``mj_geomDistance``
(negative = penetration). Pairs checked:

* moving arm (link01 ... gripperMover) against the trunk, legs, the arm mount and link00, and against its own
  links two or more joints away (adjacent links share a joint and always touch); pairs that already overlap in
  the folded home pose are excluded (``excluded``);
* moving arm against the floor plane.

Object: the object's convex hull (exact for the boxes and the trashcan used here, conservative for concave
objects), tested against sample points of the robot's collision geoms (primitive surfaces, hull vertices of mesh
geoms). The tool bodies (gripperStator, gripperMover) may touch the object at the front face, so their
penetration is reported apart from the rest of the arm; the frozen body's penetration says whether the scene is
feasible at all (an arm change cannot fix it).
"""

from __future__ import annotations

from dataclasses import dataclass

import mujoco
import numpy as np
from scipy.spatial import ConvexHull

from h2d.common.robot import B2Z1Robot

MOVING_ARM = ["link01", "link02", "link03", "link04", "link05", "link06", "gripperStator", "gripperMover"]
ARM_FIXED = ["z1_mount_computer", "link00"]


def _geom_samples(m: mujoco.MjModel, g: int) -> np.ndarray:
    """Sample points on a collision geom in its local frame."""
    t, s = int(m.geom_type[g]), m.geom_size[g]
    if t == mujoco.mjtGeom.mjGEOM_MESH:
        mid = int(m.geom_dataid[g])
        v = m.mesh_vert[m.mesh_vertadr[mid]:m.mesh_vertadr[mid] + m.mesh_vertnum[mid]].astype(np.float64)
        return v[ConvexHull(v).vertices] if len(v) > 4 else v
    if t == mujoco.mjtGeom.mjGEOM_BOX:
        g3 = np.array(np.meshgrid(*[[-1, 0, 1]] * 3)).reshape(3, -1).T
        g3 = g3[np.any(g3 != 0, axis=1)]
        return g3 * s[:3]
    if t == mujoco.mjtGeom.mjGEOM_CYLINDER or t == mujoco.mjtGeom.mjGEOM_CAPSULE:
        a = np.linspace(0, 2 * np.pi, 12, endpoint=False)
        ring = np.stack([s[0] * np.cos(a), s[0] * np.sin(a)], 1)
        pts = [np.c_[ring, np.full(12, z)] for z in (-s[1], 0.0, s[1])]
        pts.append(np.array([[0, 0, -s[1]], [0, 0, s[1]]]))
        if t == mujoco.mjtGeom.mjGEOM_CAPSULE:
            pts.append(np.array([[0, 0, -s[1] - s[0]], [0, 0, s[1] + s[0]]]))
        return np.concatenate(pts)
    if t == mujoco.mjtGeom.mjGEOM_SPHERE:
        d = np.array(np.meshgrid(*[[-1, 0, 1]] * 3)).reshape(3, -1).T
        d = d[np.any(d != 0, axis=1)]
        return s[0] * d / np.linalg.norm(d, axis=1, keepdims=True)
    return np.zeros((1, 3))


@dataclass
class ObjectHull:
    """Convex hull of an object mesh in its local frame: A x + b <= 0 inside."""
    A: np.ndarray
    b: np.ndarray

    @classmethod
    def from_vertices(cls, v: np.ndarray) -> "ObjectHull":
        eq = ConvexHull(v).equations
        return cls(eq[:, :3], eq[:, 3])

    def depth(self, p_local: np.ndarray) -> np.ndarray:
        """Penetration depth (>0 inside, 0 outside) of local points (n, 3)."""
        return np.maximum(-(p_local @ self.A.T + self.b).max(1), 0.0)


class RobotCollision:
    def __init__(self, robot: B2Z1Robot, tol_m: float = 0.002):
        self.robot, self.tol = robot, tol_m
        m = robot.model
        self.body_of = {g: robot.body_name(int(m.geom_bodyid[g])) for g in range(m.ngeom)}
        coll = [g for g in range(m.ngeom) if m.geom_contype[g] or m.geom_conaffinity[g]]
        self.floor = [g for g in coll if self.body_of[g] == "world"]
        self.arm = [g for g in coll if self.body_of[g] in MOVING_ARM]
        self.tool = [g for g in self.arm if self.body_of[g] in ("gripperStator", "gripperMover")]
        self.body = [g for g in coll if g not in self.arm and g not in self.floor]
        chain = {b: i for i, b in enumerate(ARM_FIXED[1:] + MOVING_ARM)}            # link00 = 0
        self.pairs = []
        for a in self.arm:
            for g in self.body:
                if not (self.body_of[g] == "link00" and self.body_of[a] == "link01"):
                    self.pairs.append((a, g))
            for g in self.arm:
                if g > a and abs(chain[self.body_of[a]] - chain[self.body_of[g]]) >= 2:
                    self.pairs.append((a, g))
        self.samples = {g: _geom_samples(m, g) for g in self.arm + self.body}
        # Pairs already overlapping in the model's folded home pose (qpos0) are primitive approximations of links
        # packed against each other (link02 against link05 / link06): excluded, as usual for self-collision.
        saved = robot.data.qpos.copy()
        q0 = m.qpos0.copy()
        q0[2] += 1.0
        robot.set_qpos(q0)
        fromto = np.zeros(6)
        self.excluded = [(self.body_of[a], self.body_of[g]) for a, g in self.pairs
                         if mujoco.mj_geomDistance(m, robot.data, a, g, 0.05, fromto) < tol_m]
        self.pairs = [(a, g) for a, g in self.pairs
                      if (self.body_of[a], self.body_of[g]) not in self.excluded]
        robot.set_qpos(saved)

    def _world_samples(self, geoms) -> np.ndarray:
        d = self.robot.data
        return np.concatenate([self.samples[g] @ d.geom_xmat[g].reshape(3, 3).T + d.geom_xpos[g] for g in geoms])

    def check(self, obj_hull: ObjectHull | None = None, to_local=None, distmax: float = 0.05) -> dict:
        """Check the robot's current state. ``to_local(points_world) -> points in the object frame``."""
        m, d = self.robot.model, self.robot.data
        fromto = np.zeros(6)
        self_min, worst = distmax, None
        for a, g in self.pairs:
            dist = mujoco.mj_geomDistance(m, d, a, g, distmax, fromto)
            if dist < self_min:
                self_min, worst = dist, (self.body_of[a], self.body_of[g])
        floor_min = min((mujoco.mj_geomDistance(m, d, a, f, distmax, fromto) for a in self.arm for f in self.floor),
                        default=distmax)
        out = {"self_min_dist_m": float(self_min), "self_worst_pair": worst, "floor_min_dist_m": float(floor_min)}
        if obj_hull is not None:
            arm_nt = [g for g in self.arm if g not in self.tool]
            dep = lambda geoms: float(obj_hull.depth(to_local(self._world_samples(geoms))).max())  # noqa: E731
            out.update({"arm_obj_depth_m": dep(arm_nt), "tool_obj_depth_m": dep(self.tool),
                        "body_obj_depth_m": dep(self.body)})
        out["collision_free"] = bool(self_min > -self.tol and floor_min > -self.tol
                                     and out.get("arm_obj_depth_m", 0.0) <= self.tol)
        return out
