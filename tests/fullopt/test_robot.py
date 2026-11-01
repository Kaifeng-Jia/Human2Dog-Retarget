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


# R027, clip c10 (sub1_largetable_074_5) frame 45, to the last bit (rounded to 1e-7 the sign comes out right): MuJoCo
# 3.11's mj_geomDistance gives the gripper's stator mesh and the trunk's front plate -24 mm, in both orders, with
# witness points 41 mm apart; neither has a vertex in the other.
C10_Q45 = [0.801445186668244, 0.8996163964105698, 0.521188608299796, 0.8265722360767332, -0.0017266115640159018,
           -0.005459862943291754, -0.5628015167501395, 0.0, 0.8, -1.5, 0.0, 0.8, -1.5, 0.0, 0.8, -1.5, 0.0, 0.8,
           -1.5, 0.6273133231986965, 2.7322807020793753, -0.146149997770955, -1.410770592909264,
           -0.24448283188305892, 0.6809764522319842, 0.0]


def test_a_negative_distance_needs_consistent_witness_points():
    import mujoco

    coll, m = Collision(ROBOT), ROBOT.model
    a = next(x for x in coll.tool if coll.body_of[x] == "gripperStator")             # the stator's mesh
    g = next(x for x in coll.body if coll.body_of[x] == "base_link" and m.geom_pos[x][0] > 0.4)   # the front plate
    ROBOT.set(np.array(C10_Q45))
    ft = np.zeros(6)
    raw = mujoco.mj_geomDistance(ROBOT.model, ROBOT.data, a, g, 0.05, ft)
    dist, ft2 = coll.distance(a, g, 0.05)
    assert dist > 0.02                                           # apart by 24 mm (the samples' estimate)
    if raw < 0:                                                  # the bug as R027 met it (fixed MuJoCo: no fallback)
        assert abs(np.linalg.norm(ft[3:] - ft[:3]) - abs(raw)) > 0.01 and coll.fallbacks == 1
        assert np.linalg.norm(ft2[3:] - ft2[:3]) == pytest.approx(dist, abs=1e-3)
    assert coll.check()["collision_free"] and coll.check()["self_min_dist_m"] > 0


def test_real_penetrations_keep_mujocos_distance():
    coll = Collision(ROBOT)
    q = ROBOT.placed([0.0, 0.0], 0.0)
    q[[ROBOT.qadr[n] for n in ROBOT.desc["arm"]]] = [0.0, 2.9, -0.4, -1.4, 0.0, 0.0]   # the gripper down into the trunk
    ROBOT.set(q)
    deep = [coll.distance(a, g, 0.05)[0] for a, g in coll.pairs]
    assert min(deep) < -0.005 and coll.fallbacks == 0


def test_feet_footholds_and_the_under_body_box():
    ROBOT.set(ROBOT.home)
    coll = Collision(ROBOT)
    assert len(coll.feet) == 4 and all(ROBOT.model.geom_type[g] == 2 for g in coll.feet)   # the sole spheres
    assert np.abs(ROBOT.soles()).max() < 1e-3
    assert np.allclose(ROBOT.footholds()[:, :2], ROBOT.data.xpos[ROBOT.feet][:, :2], atol=1e-9)
    P = ROBOT.cage_points()
    Rc, c = ROBOT.cage_frame()
    assert np.allclose(P.mean(0), c) and np.isclose(P[:, 2].min(), 0.0, atol=1e-3)   # down to the floor
    assert (P[:, 2].max() - ROBOT.data.xpos[ROBOT.base][2]) == pytest.approx(-0.075, abs=1e-3)   # trunk underside
    d, n = ROBOT.outside_cage(np.array([c, c + Rc[:, 0] * 0.5, c - Rc[:, 2] * 0.3]))
    assert d[0] < 0 and d[1] == pytest.approx(0.5 - 0.328) and np.allclose(n[1], Rc[:, 0])
    assert np.allclose(n[2], -Rc[:, 2])
