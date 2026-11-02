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

# A trial pose of the SQP on c10 frame 5 (R027b dry run), to the last bit.
C10_F5_TRIAL = [0.9039383830265142, 1.3181775745049666, 0.45377581974689307, 0.7270060369027478,
                0.015500679568232784, 0.02248660019445597, -0.6860876795655044, 0.009848382152119117,
                0.9463067474718839, -1.9079872951185441, 0.009729002176094436, 0.9439724791561526,
                -1.9044695324540326, 0.01263478085807596, 0.876082191406782, -1.7792820754808782,
                0.006538696899966947, 0.8738729773314065, -1.7760293402358753, 0.38267298789218995,
                2.1445833258498337, -0.5483453015502568, -0.4427371996573447, -0.2341914546956372,
                0.5219927165514191, 0.0]


def test_a_negative_distance_needs_consistent_witness_points():
    import mujoco

    coll, m = Collision(ROBOT), ROBOT.model
    a = next(x for x in coll.tool if coll.body_of[x] == "gripperStator")             # the stator's mesh
    g = next(x for x in coll.body if coll.body_of[x] == "base_link" and m.geom_pos[x][0] > 0.4)   # the front plate
    ROBOT.set(np.array(C10_Q45))
    ft = np.zeros(6)
    raw = mujoco.mj_geomDistance(ROBOT.model, ROBOT.data, a, g, 0.05, ft)
    dist, ft2 = coll.distance(a, g, 0.05)
    assert dist == pytest.approx(0.0241, abs=1e-4)              # apart by 24 mm
    if raw < 0:                                                  # the bug as R027 met it (fixed MuJoCo: no retry)
        assert abs(np.linalg.norm(ft[3:] - ft[:3]) - abs(raw)) > 0.01 and coll.retries == 1
        assert np.linalg.norm(ft2[3:] - ft2[:3]) == pytest.approx(dist, abs=1e-3)
    assert coll.check()["collision_free"] and coll.check()["self_min_dist_m"] > 0


def test_a_distance_of_zero_needs_consistent_witness_points():
    """R027b dry run: the gripper's mover and the trunk's front plate, 23.7 mm apart, come out as exactly 0 (witness
    points 32 mm apart) on a pose that steps of 1e-5 move in and out of."""
    import mujoco

    coll, m = Collision(ROBOT), ROBOT.model
    a = next(x for x in coll.tool if coll.body_of[x] == "gripperMover")
    g = next(x for x in coll.body if coll.body_of[x] == "base_link" and m.geom_pos[x][0] > 0.4)
    ROBOT.set(np.array(C10_F5_TRIAL))
    raw = mujoco.mj_geomDistance(m, ROBOT.data, a, g, 0.15, np.zeros(6))
    dist = coll.distance(a, g, 0.15)[0]
    assert dist == pytest.approx(0.02374, abs=1e-5) and coll.fallbacks == 0
    assert coll.retries == (1 if raw == 0.0 else 0)


@pytest.mark.parametrize("bogus_calls", [1, None])
def test_a_distance_of_zero_with_an_all_zero_fromto_is_measured_again(monkeypatch, bogus_calls):
    """R027d on Ubuntu, c09 frame 0: exactly 0 with fromto all zero for the gripper's mover and the front plate 25.9 mm
    apart (the old check passed: both are 0). Here on a pose where MuJoCo measures the pair right (13.7 mm), made bogus
    on the first call (the swapped order measures it) or on every call (the sample estimate)."""
    import mujoco

    coll, m = Collision(ROBOT), ROBOT.model
    a = next(x for x in coll.tool if coll.body_of[x] == "gripperMover")
    g = next(x for x in coll.body if coll.body_of[x] == "base_link" and m.geom_pos[x][0] > 0.4)
    ROBOT.set(np.array(C10_Q45))
    true = coll.distance(a, g, 0.15)[0]
    assert true == pytest.approx(0.0137, abs=1e-4) and coll.retries == coll.fallbacks == 0
    real, calls = mujoco.mj_geomDistance, []

    def bogus(model, data, g1, g2, distmax, fromto):
        calls.append((g1, g2))
        if {g1, g2} == {a, g} and (bogus_calls is None or len(calls) <= bogus_calls):
            fromto[:] = 0.0
            return 0.0
        return real(model, data, g1, g2, distmax, fromto)

    monkeypatch.setattr(mujoco, "mj_geomDistance", bogus)
    coll.retries = coll.fallbacks = 0
    dist, ft = coll.distance(a, g, 0.15)
    if bogus_calls:
        assert dist == true and len(calls) == 2 and coll.fallbacks == 0
    else:
        assert dist == pytest.approx(true, abs=0.005) and coll.fallbacks == 1
    assert np.linalg.norm(ft[3:] - ft[:3]) == pytest.approx(dist, abs=1e-3)


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


def test_the_difference_jacobian_matches_finite_differences():
    """d difference(q0, q + dx) / d dx: the identity but for the base's rotation (J_r^-1 of the rotation between)."""
    d, eps = ROBOT.dofs("base", "legs", "arm"), 1e-6
    q0, q = random_q(4), random_q(5)
    diff = lambda e: ROBOT.difference(q0, ROBOT.integrate(q, e, d), d)  # noqa: E731
    num = np.array([(diff(e) - diff(-e)) / (2 * eps) for e in eps * np.eye(len(d))]).T
    assert np.allclose(ROBOT.difference_jac(q0, q, d), num, atol=1e-6)
