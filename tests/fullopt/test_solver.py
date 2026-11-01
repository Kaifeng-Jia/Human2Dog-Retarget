"""Per-frame SQP (fullopt spec v0.2 §7): the step QP, rows the trunk can hold, and pass 1 on a short synthetic
push."""

import sys
from pathlib import Path

import numpy as np
import pytest

from h2d.fullopt.solver import StepQP, held
from h2d.paths import load_config

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from synthetic_hoi import make_clip  # noqa: E402

try:
    from h2d.common.data.omomo_objects import load_object
    from h2d.fullopt.robot import Robot

    BOX, ROBOT = load_object("largebox"), Robot()
except Exception:  # pragma: no cover - X-Morph checkout or meshes missing
    BOX = ROBOT = None


def test_step_qp_trust_region_and_slack():
    qp = StepQP(n=2, m=2, k=1, slack_weight=1e3)
    A, b, lo, hi = np.eye(2), np.array([1.0, 0.0]), -np.ones(2), np.ones(2)
    dx, slack, ok, val = qp.solve(A, b, np.zeros((1, 2)), np.ones(1), lo, hi, 0.1)   # inactive row
    assert ok and np.allclose(dx, [0.1, 0.0], atol=1e-6) and slack < 1e-8              # stops at the trust region
    assert val == pytest.approx(0.81, abs=1e-6)                                         # the model at the step
    dx, slack, ok, _ = qp.solve(A, b, np.array([[-1.0, 0.0]]), np.array([0.05]), lo, hi, 0.1)   # dx0 <= 0.05
    assert ok and np.allclose(dx, [0.05, 0.0], atol=1e-6) and slack < 1e-6
    dx, slack, ok, _ = qp.solve(A, b, np.array([[1.0, 0.0]]), np.array([-0.5]), lo, hi, 0.1)    # dx0 >= 0.5
    assert ok and slack == pytest.approx(0.4, abs=1e-4)                                 # ... so the slack takes it


@pytest.mark.parametrize("v0", [0.0, 0.01, 0.03])
def test_a_held_row_stops_before_its_bound(v0):
    """Approach a bound 0.2 away as fast as the row lets (closing speed v0 per frame at the start, deceleration a per
    frame^2): the value never goes below 0 and the speed never changes by more than a per frame."""
    a, x, v = 0.003, 0.2, -v0
    for _ in range(200):
        step = -held(x, v, a)                         # the most negative change the row allows
        step = max(step, v - a)                       # ... and the acceleration box
        assert step >= v - a - 1e-12 and x + step >= -1e-12
        x, v = x + step, step
    assert x < 0.01 and abs(v) < a                    # it gets there and stops


def push(start: int = 20, stop: int = 66, hands: str = "R"):
    """A short synthetic top push (the top's edge on the robot's side, 0.36 m high), its task and relation (a)."""
    from h2d.common.data.tasks import build_task
    from h2d.fullopt import task as tk
    from h2d.fullopt.hoi import HOIClip, from_common_clip
    from h2d.fullopt.relation import REPRESENTATIONS

    band = load_config("candidate_selection.yaml")["reach_band"]
    src = make_clip(carry=False, T=150, push_face="top", push_hands=hands)
    w = build_task(src, BOX, (30, 90), hands, band=band)["window"]
    full = from_common_clip(src, BOX)
    sl = slice(start, stop)
    c = HOIClip(fps=full.fps, joints=full.joints[sl], joint_names=full.joint_names, obj_verts=full.obj_verts,
                obj_faces=full.obj_faces, obj_pos=full.obj_pos[sl], obj_quat=full.obj_quat[sl],
                hand_contact=full.hand_contact[sl],
                meta={"id": "s", "mode": hands, "segment": [30 - start, stop - start],
                      "window": [0, min(stop - start, w[1] - start)]})
    cfg = load_config("fullopt/solver.yaml")
    task = tk.build(c, cfg["task"], band)
    corr = load_config("fullopt/correspondence.yaml")[ROBOT.name]
    return c, task, REPRESENTATIONS["a"](c, task, ROBOT, corr, cfg["relation"]), cfg, corr


@pytest.mark.skipif(BOX is None, reason="B2-Z1 model or object meshes not found")
def test_pass_one_reaches_a_reachable_push_and_stays_out_of_the_object():
    from h2d.fullopt.evaluate import evaluate
    from h2d.fullopt.robot import Collision
    from h2d.fullopt.solver import Solver

    c, task, relation, cfg, corr = push()                         # 10 frames before the contact, 36 in it
    coll = Collision(ROBOT)
    sol = Solver(ROBOT, cfg, coll=coll).solve(c, task, relation)
    ev, _ = evaluate(c, task, sol["q"], ROBOT, coll, corr, load_config("fullopt/evaluation.yaml"))
    assert sol["qp_ok"].all() and sol["converged"].all()
    assert ev["reach"]["reached"], ev["reach"]
    pe, li = ev["penetration"], ev["limits"]
    assert pe["body_in_object_m"] < 1e-3 and pe["arm_in_object_m"] < 2e-3 and pe["object_under_body_frames"] == 0
    assert li["range_violation_frames"] == 0 and li["speed_violation_frames"] == 0
    assert li["trunk_accel_ratio_max"] < 1.01 and li["trunk_tilt_max_deg"] < 15.01
    assert ev["feet"]["sole_height_max_m"] < 2e-3                  # the legs move, the soles stay on the floor
    assert ev["relations"]["contact"]["same_side_frac"] == 1.0


@pytest.mark.skipif(BOX is None, reason="B2-Z1 model or object meshes not found")
def test_object_under_the_body_is_measured_by_the_overlap():
    from scipy.spatial.transform import Rotation as R

    from h2d.common.collision import ObjectHull
    from h2d.fullopt.evaluate import under_body

    ROBOT.set(ROBOT.home)
    Rc, c = ROBOT.cage_frame()
    cube = np.array([[x, y, z] for x in (-0.1, 0.1) for y in (-0.1, 0.1) for z in (-0.1, 0.1)])
    hull, Ro = ObjectHull.from_vertices(cube), R.from_euler("z", 0.3).as_matrix()
    assert under_body(ROBOT, hull, Ro, c) == pytest.approx(0.2, abs=1e-6)            # a cube under the belly
    edge = c + Rc[:, 0] * (0.328 + 0.1 - 0.03)                                       # 3 cm into the box's front
    assert under_body(ROBOT, hull, np.eye(3), edge) == pytest.approx(0.03, abs=1e-6)
    assert under_body(ROBOT, hull, np.eye(3), c + Rc[:, 0] * 0.6) == 0.0             # in front of it
    assert under_body(ROBOT, hull, np.eye(3), c + Rc[:, 0] * 5.0) == 0.0             # far away


@pytest.mark.skipif(BOX is None, reason="B2-Z1 model or object meshes not found")
def test_the_order_of_the_clips_does_not_matter():
    """Every QP starts from a fresh solver state (R027b: cvxpy's warm start carried Clarabel's state across clips)."""
    from h2d.fullopt.robot import Collision
    from h2d.fullopt.solver import Solver

    a, b = push(20, 40, "R"), push(24, 44, "B")
    q = {}
    for order in ((a, b), (b, a)):
        sv = Solver(ROBOT, a[3], coll=Collision(ROBOT))
        q[order[0] is a] = [sv.solve(c, task, rel)["q"] for c, task, rel, *_ in order]
    assert np.array_equal(q[True][0], q[False][1]) and np.array_equal(q[True][1], q[False][0])


@pytest.mark.skipif(BOX is None, reason="B2-Z1 model or object meshes not found")
def test_a_step_the_merit_does_not_confirm_is_rejected():
    """Trust region on the L1 merit: a QP step blown up 20x is rejected, the radius shrinks, the frame still
    converges, and every accepted step lowers the merit."""
    from scipy.spatial import ConvexHull
    from scipy.spatial.transform import Rotation as R

    from h2d.common.collision import ObjectHull
    from h2d.fullopt.robot import Collision
    from h2d.fullopt.solver import Solver

    c, task, rel, cfg, _ = push(20, 40)
    sv = Solver(ROBOT, cfg, coll=Collision(ROBOT))
    sv.fps = c.fps
    ov = np.asarray(c.obj_verts, float)
    frame = (ObjectHull.from_vertices(ov), ov[ConvexHull(ov).vertices], R.from_quat(c.obj_quat[0]).as_matrix(),
             c.obj_pos[0])
    merits, lin = [], sv._linearise
    sv._linearise = lambda *x: merits.append(lin(*x)["merit"]) or lin(*x)
    qp, calls = sv._step_qp, []

    def blown(m):
        p = qp(m)
        solve = p.solve

        def once(*args):
            dx, *rest = solve(*args)
            calls.append(1)
            return (20.0 * dx if len(calls) == 1 else dx), *rest
        p.solve = once
        return p

    sv._step_qp = blown
    q, rec = sv._frame(0, sv.start(c), None, None, task, rel, frame, 200)
    assert rec["rejected"] >= 1 and rec["converged"] and np.isfinite(merits).all()
    assert merits[-1] < merits[0]


@pytest.mark.skipif(BOX is None, reason="B2-Z1 model or object meshes not found")
def test_collision_is_checked_on_every_frame():
    from h2d.common.collision import ObjectHull
    from h2d.fullopt.evaluate import penetration
    from h2d.fullopt.robot import Collision

    coll = Collision(ROBOT)
    clean = ROBOT.placed([0.0, 0.0], 0.0)
    folded = clean.copy()
    folded[[ROBOT.qadr[n] for n in ROBOT.desc["arm"]]] = [0.0, 2.9, -0.4, -1.4, 0.0, 0.0]   # gripper into the trunk
    low = clean.copy()
    low[ROBOT.base_qadr + 2] = 0.25                                                       # legs through the floor
    Q = np.stack([clean, folded, clean, low])
    hull = ObjectHull.from_vertices(np.array([[x, y, z] for x in (9, 10) for y in (9, 10) for z in (0, 1)], float))
    pe = penetration(ROBOT, coll, Q, hull, np.tile(np.eye(3), (4, 1, 1)), np.zeros((4, 3)), range(4), 0.002)
    assert pe["collision_frames"] == 2 and pe["collision_frame_list"] == [1, 3]
    assert pe["self_worst"]["frame"] == 1 and pe["self_worst"]["dist_m"] < -0.005
    assert pe["floor_worst"]["frame"] == 3 and pe["floor_worst"]["dist_m"] < -0.05
