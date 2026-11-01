"""The robot description and its wrapper (fullopt spec v0.2 §7.4): the learned line's conventions and collision rules,
Jacobians that match finite differences."""

import numpy as np
import pytest

from h2d.paths import load_config

try:
    from h2d.fullopt.robot import Collision, Robot

    ROBOT = Robot()
except Exception:  # pragma: no cover - X-Morph checkout missing
    ROBOT = None

pytestmark = pytest.mark.skipif(ROBOT is None, reason="B2-Z1 model not found (XMORPH_ROOT)")


def random_q(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    d = ROBOT.dofs("base", "legs", "arm")
    q = ROBOT.integrate(ROBOT.placed(rng.uniform(-1, 1, 2), rng.uniform(-3, 3)), rng.normal(0, 0.3, len(d)), d)
    return ROBOT.clip(q)


def test_description_matches_the_global_conventions():
    tool, d = load_config("b2z1.yaml")["tool"], ROBOT.desc["tool"]
    assert d["body"] == tool["frame_body"] and d["contact_point"] == tool["contact_site_local"]
    assert d["approach_axis"] == tool["approach_axis_local"] and d["jaw_axis"] == tool["jaw_axis_local"]
    assert [len(ROBOT.groups[g]) for g in ("base", "legs", "arm")] == [6, 12, 6]
    ROBOT.set(ROBOT.home)                                        # the nominal height puts the soles on the floor
    soles = ROBOT.data.xpos[ROBOT.feet][:, 2] - ROBOT.desc["foot_radius_m"]
    assert np.abs(soles).max() < 1e-3
    assert np.allclose(ROBOT.point("gripper"), ROBOT.tool_point())
    assert ROBOT.point("support")[2] == 0.0


def test_collision_rules_match_the_learned_lines():
    from h2d.common.collision import ObjectHull, RobotCollision
    from h2d.common.robot import B2Z1Robot

    learned, coll = B2Z1Robot(), Collision(ROBOT)
    lc = RobotCollision(learned)
    assert sorted(coll.pairs) == sorted(lc.pairs) and coll.excluded == sorted(lc.excluded)
    assert set(coll.samples) == set(lc.samples)
    q = ROBOT.placed([0.0, 0.0], 0.0)
    q[[ROBOT.qadr[n] for n in ROBOT.desc["arm"]]] = [0.3, 1.2, -1.6, 0.4, 0.2, 0.0]
    ROBOT.set(q)
    learned.set_qpos(q)
    cube = np.array([[x, y, z] for x in (-0.2, 0.2) for y in (-0.2, 0.2) for z in (-0.2, 0.2)])
    hull = ObjectHull.from_vertices(cube)
    to_local = lambda p: p - ROBOT.tool_point()  # noqa: E731 - a box around the gripper and the forearm
    mine, theirs = coll.check(hull, to_local), lc.check(hull, to_local)
    assert mine == theirs and mine["tool_obj_depth_m"] > 0.1 and mine["arm_obj_depth_m"] > 0


@pytest.mark.parametrize("seed", [0, 1])
def test_jacobians_match_finite_differences(seed):
    d, eps = ROBOT.dofs("base", "legs", "arm"), 1e-6
    q = random_q(seed)

    def numeric(f):
        cols = []
        for k in range(len(d)):
            e = np.zeros(len(d))
            e[k] = eps
            ROBOT.set(ROBOT.integrate(q, e, d))
            a = f()
            ROBOT.set(ROBOT.integrate(q, -e, d))
            cols.append((a - f()) / (2 * eps))
        ROBOT.set(q)
        return np.array(cols).T

    ROBOT.set(q)
    for name in ROBOT.point_names:
        assert np.allclose(ROBOT.point_jac(name, d), numeric(lambda n=name: ROBOT.point(n)), atol=1e-6), name
    for local in (ROBOT.approach_local, ROBOT.jaw_local):
        J = ROBOT.axis_jac(ROBOT.tool_body, local, d)
        assert np.allclose(J, numeric(lambda a=local: ROBOT.axis(ROBOT.tool_body, a)), atol=1e-6)


def test_steps_and_differences_are_inverse():
    d = ROBOT.dofs("base", "arm")
    q0, dx = random_q(3), np.linspace(-0.05, 0.05, 12)
    assert np.allclose(ROBOT.difference(q0, ROBOT.integrate(q0, dx, d), d), dx, atol=1e-9)
