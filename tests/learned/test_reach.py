"""Arm IK with collision checks on the B2-Z1 model (needs the pinned X-Morph checkout for the MuJoCo model)."""

import numpy as np
import pytest

try:
    from h2d.common.robot import B2Z1Robot

    ROBOT = B2Z1Robot()
except Exception:  # pragma: no cover - X-Morph checkout missing
    ROBOT = None
needs_model = pytest.mark.skipif(ROBOT is None, reason="B2-Z1 model not found (XMORPH_ROOT)")


@needs_model
def test_collision_home_pose_and_ik_in_free_space():
    from h2d.common.collision import ObjectHull, RobotCollision
    from h2d.learned.reach import ArmIK, ObjectPose, reach_bound, shoulder

    q = ROBOT.model.qpos0.copy()
    q[2] = 0.55
    ROBOT.set_qpos(q)
    coll = RobotCollision(ROBOT)
    assert coll.check()["collision_free"] and ("link02", "link06") in coll.excluded
    bound, sampled = reach_bound(ROBOT)
    assert sampled <= bound + 1e-9 and 0.8 < bound < 1.1
    ik = ArmIK(ROBOT, coll, n_random=8)
    y = shoulder(ROBOT) + np.array([0.35, 0.15, 0.10])          # in front of and above the shoulder
    r = ik.solve(y, np.array([-1.0, 0, 0]), np.zeros(6), use_dir=True)
    assert r.feasible and r.pos_err_m < 0.01 and r.angle_deg < 15
    # a box right at the target makes the arm keep its links out (tool may touch)
    v = np.array(np.meshgrid([-1, 1], [-1, 1], [-1, 1])).reshape(3, -1).T * 0.1
    op = ObjectPose(ObjectHull.from_vertices(v), y + np.array([0.1 + 0.005, 0, 0]), np.eye(3))
    r2 = ik.solve(y, np.array([-1.0, 0, 0]), np.zeros(6), use_dir=True, obj=op)
    assert r2.collision["arm_obj_depth_m"] <= 0.002
    far = shoulder(ROBOT) + np.array([bound + 0.2, 0, 0])
    assert not ik.solve(far, np.array([-1.0, 0, 0]), np.zeros(6), full=False).feasible
