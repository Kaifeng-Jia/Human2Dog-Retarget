"""B2-Z1 kinematics, tool frame, contact site and collision geometry.

One MuJoCo model (X-Morph's full ``b2_with_z1.xml``) is the single source of
kinematics *and* collision geometry, so the optimizer and the evaluator use the
same geometry convention (spec v0.5 section 2, Codex B01).

Conventions
-----------
* X-Morph motion files: ``root_pos`` (T,3), ``root_rot`` (T,4) in **xyzw**,
  ``dof_pos`` (T,19) in ``robot.joint_order``.
* MuJoCo qpos: [x y z, qw qx qy qz, 19 joints]; joint order identical to X-Morph
  (verified in B01).
* Tool frame = ``gripperStator`` body frame; contact site r_c expressed in it.
"""

from __future__ import annotations

from dataclasses import dataclass

import mujoco
import numpy as np

from h2d.paths import load_config, xmorph_path


def xyzw_to_wxyz(q: np.ndarray) -> np.ndarray:
    q = np.asarray(q)
    return q[..., [3, 0, 1, 2]]


@dataclass
class GeomInfo:
    geom_id: int
    body: str
    gtype: str
    collides: bool
    mesh_id: int


_GEOM_TYPES = {int(v): k for k, v in mujoco.mjtGeom.__members__.items()}


class B2Z1Robot:
    def __init__(self, cfg: dict | None = None):
        self.cfg = cfg or load_config("b2z1.yaml")
        xml = xmorph_path(self.cfg["xmorph"]["model_xml"])
        self.model = mujoco.MjModel.from_xml_path(str(xml))
        self.data = mujoco.MjData(self.model)

        m = self.model
        rc = self.cfg["robot"]
        self.joint_order = list(rc["joint_order"])
        self.joint_qadr = np.array([m.jnt_qposadr[self._jid(n)] for n in self.joint_order])
        self.arm_qadr = np.array([m.jnt_qposadr[self._jid(n)] for n in rc["arm_joints"]])
        self.arm_dofadr = np.array([m.jnt_dofadr[self._jid(n)] for n in rc["arm_joints"]])
        self.gripper_qadr = int(m.jnt_qposadr[self._jid(rc["gripper_joint"])])
        self.gripper_lock = float(rc["gripper_lock"])

        tc = self.cfg["tool"]
        self.tool_body = self._bid(tc["frame_body"])
        self.contact_body = self._bid(tc["contact_body"])
        self.r_c = np.asarray(tc["contact_site_local"], dtype=np.float64)
        self.approach_local = np.asarray(tc["approach_axis_local"], dtype=np.float64)
        self.jaw_local = np.asarray(tc["jaw_axis_local"], dtype=np.float64)

        jr = np.array([m.jnt_range[self._jid(n)] for n in self.joint_order])
        self.joint_lower, self.joint_upper = jr[:, 0], jr[:, 1]
        self.arm_lower = np.array([m.jnt_range[self._jid(n)][0] for n in rc["arm_joints"]])
        self.arm_upper = np.array([m.jnt_range[self._jid(n)][1] for n in rc["arm_joints"]])

        self.set_qpos(m.qpos0.copy())

    # ------------------------------------------------------------------ ids
    def _jid(self, name: str) -> int:
        i = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, name)
        if i < 0:
            raise KeyError(f"joint {name!r} not in model")
        return i

    def _bid(self, name: str) -> int:
        i = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, name)
        if i < 0:
            raise KeyError(f"body {name!r} not in model")
        return i

    def body_name(self, bid: int) -> str:
        return mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_BODY, bid)

    # ---------------------------------------------------------------- state
    def qpos_from_xmorph(self, root_pos, root_rot_xyzw, dof_pos, lock_gripper: bool = True) -> np.ndarray:
        """Convert one X-Morph frame to a MuJoCo qpos vector."""
        q = self.model.qpos0.copy()
        q[0:3] = root_pos
        q[3:7] = xyzw_to_wxyz(np.asarray(root_rot_xyzw, dtype=np.float64))
        q[self.joint_qadr] = dof_pos
        if lock_gripper:
            q[self.gripper_qadr] = self.gripper_lock
        return q

    def set_qpos(self, qpos: np.ndarray) -> None:
        self.data.qpos[:] = qpos
        mujoco.mj_kinematics(self.model, self.data)
        mujoco.mj_comPos(self.model, self.data)

    def set_arm(self, arm_q: np.ndarray) -> None:
        q = self.data.qpos.copy()
        q[self.arm_qadr] = arm_q
        self.set_qpos(q)

    # ----------------------------------------------------------------- tool
    def tool_pose(self) -> tuple[np.ndarray, np.ndarray]:
        """World rotation (3,3) and position (3,) of the tool frame."""
        R = self.data.xmat[self.tool_body].reshape(3, 3).copy()
        p = self.data.xpos[self.tool_body].copy()
        return R, p

    def contact_site(self) -> np.ndarray:
        R, p = self.tool_pose()
        return p + R @ self.r_c

    def tool_axis(self, local) -> np.ndarray:
        R, _ = self.tool_pose()
        return R @ np.asarray(local, dtype=np.float64)

    def approach_axis(self) -> np.ndarray:
        return self.tool_axis(self.approach_local)

    def contact_site_jacobian(self) -> np.ndarray:
        """(3, 6) translational Jacobian of the contact site w.r.t. the arm joints."""
        jacp = np.zeros((3, self.model.nv))
        mujoco.mj_jac(self.model, self.data, jacp, None, self.contact_site(), self.tool_body)
        return jacp[:, self.arm_dofadr]

    def tool_axis_jacobian(self, local) -> np.ndarray:
        """(3, 6) Jacobian of a world tool axis R a_local w.r.t. the arm joints: d(R a)/dq_k = omega_k x (R a)."""
        jacr = np.zeros((3, self.model.nv))
        mujoco.mj_jacBody(self.model, self.data, None, jacr, self.tool_body)
        return np.cross(jacr[:, self.arm_dofadr].T, self.tool_axis(local)).T

    def approach_axis_jacobian(self) -> np.ndarray:
        return self.tool_axis_jacobian(self.approach_local)

    # ------------------------------------------------------------- geometry
    def geoms(self, bodies: list[str] | None = None) -> list[GeomInfo]:
        m = self.model
        want = None if bodies is None else {self._bid(b) for b in bodies}
        out = []
        for g in range(m.ngeom):
            b = int(m.geom_bodyid[g])
            if want is not None and b not in want:
                continue
            out.append(
                GeomInfo(
                    geom_id=g,
                    body=self.body_name(b),
                    gtype=_GEOM_TYPES.get(int(m.geom_type[g]), str(m.geom_type[g])),
                    collides=bool(m.geom_contype[g] or m.geom_conaffinity[g]),
                    mesh_id=int(m.geom_dataid[g]) if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH else -1,
                )
            )
        return out

    def collision_geom_ids(self, bodies: list[str]) -> list[int]:
        return [g.geom_id for g in self.geoms(bodies) if g.collides]

    def mesh_world(self, geom_id: int) -> tuple[np.ndarray, np.ndarray]:
        """World-frame vertices and faces of a mesh geom at the current state.

        MuJoCo re-centres mesh vertices; geom_xpos/geom_xmat already include
        that offset, so this is the exact rendered/collided mesh placement.
        """
        m, d = self.model, self.data
        mid = int(m.geom_dataid[geom_id])
        if m.geom_type[geom_id] != mujoco.mjtGeom.mjGEOM_MESH or mid < 0:
            raise ValueError(f"geom {geom_id} is not a mesh")
        va, vn = m.mesh_vertadr[mid], m.mesh_vertnum[mid]
        fa, fn = m.mesh_faceadr[mid], m.mesh_facenum[mid]
        v = m.mesh_vert[va:va + vn].astype(np.float64)
        f = m.mesh_face[fa:fa + fn].astype(np.int64)
        R = d.geom_xmat[geom_id].reshape(3, 3)
        return v @ R.T + d.geom_xpos[geom_id], f

    def to_tool_frame(self, pts_world: np.ndarray) -> np.ndarray:
        R, p = self.tool_pose()
        return (pts_world - p) @ R
