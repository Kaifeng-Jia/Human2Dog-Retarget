"""Fast regression tests for the B01 tool / collision geometry conventions."""

import os
from pathlib import Path

import numpy as np
import pytest

from h2d.paths import REPO_ROOT

xmorph = os.environ.get("XMORPH_ROOT") or str(REPO_ROOT / "external" / "morph")
pytestmark = pytest.mark.skipif(
    not (Path(xmorph) / "assets").is_dir(), reason="X-Morph checkout not available (set XMORPH_ROOT)"
)


@pytest.fixture(scope="module")
def robot():
    from h2d.common.robot import B2Z1Robot

    r = B2Z1Robot()
    q = r.model.qpos0.copy()
    q[r.gripper_qadr] = r.gripper_lock
    r.set_qpos(q)
    return r


def _tool_meshes(robot):
    tool = robot.cfg["collision"]["tool_bodies"]
    return {g.body: robot.mesh_world(g.geom_id) for g in robot.geoms(tool) if g.collides and g.mesh_id >= 0}


def test_joint_order_matches_qpos(robot):
    assert np.array_equal(robot.joint_qadr, np.arange(7, 26))


def test_contact_site_lies_on_mover_front_face(robot):
    from h2d.common.meshgeom import point_mesh_distance

    meshes = _tool_meshes(robot)
    p = robot.contact_site()
    assert point_mesh_distance(p, *meshes["gripperMover"]) < 1e-5
    assert point_mesh_distance(p, *meshes["gripperStator"]) > 5e-3


def test_xmorph_frame_conversion_roundtrip(robot):
    q = robot.qpos_from_xmorph([0.1, 0.2, 0.5], [0.0, 0.0, 0.0, 1.0], np.zeros(19))
    assert np.allclose(q[3:7], [1, 0, 0, 0])
    assert q[robot.gripper_qadr] == robot.gripper_lock


def test_contact_jacobian_matches_finite_difference(robot):
    rng = np.random.default_rng(1)
    q = robot.model.qpos0.copy()
    q[robot.arm_qadr] = rng.uniform(robot.arm_lower, robot.arm_upper)
    robot.set_qpos(q)
    J = robot.contact_site_jacobian()
    p0 = robot.contact_site()
    arm0 = q[robot.arm_qadr].copy()
    eps = 1e-6
    for k in range(6):
        d = np.zeros(6)
        d[k] = eps
        robot.set_arm(arm0 + d)
        assert np.allclose((robot.contact_site() - p0) / eps, J[:, k], atol=1e-4)
        robot.set_arm(arm0)


def test_closest_point_on_triangle_regions():
    from h2d.common.meshgeom import closest_points_on_triangles

    tri = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], dtype=float)
    cases = {
        (0.2, 0.2, 1.0): (0.2, 0.2, 0.0),   # face
        (-1.0, -1.0, 0.0): (0.0, 0.0, 0.0),  # vertex A
        (2.0, -0.5, 0.0): (1.0, 0.0, 0.0),   # vertex B
        (0.5, -1.0, 0.0): (0.5, 0.0, 0.0),   # edge AB
        (1.0, 1.0, 0.0): (0.5, 0.5, 0.0),    # edge BC
    }
    for p, expect in cases.items():
        assert np.allclose(closest_points_on_triangles(np.array(p), tri)[0], expect)
