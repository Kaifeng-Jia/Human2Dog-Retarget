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
    dx, slack, ok = qp.solve(A, b, np.zeros((1, 2)), np.ones(1), lo, hi, 0.1)        # inactive row
    assert ok and np.allclose(dx, [0.1, 0.0], atol=1e-6) and slack < 1e-8              # stops at the trust region
    dx, slack, ok = qp.solve(A, b, np.array([[-1.0, 0.0]]), np.array([0.05]), lo, hi, 0.1)   # dx0 <= 0.05
    assert ok and np.allclose(dx, [0.05, 0.0], atol=1e-6) and slack < 1e-6
    dx, slack, ok = qp.solve(A, b, np.array([[1.0, 0.0]]), np.array([-0.5]), lo, hi, 0.1)    # dx0 >= 0.5: infeasible
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


@pytest.mark.skipif(BOX is None, reason="B2-Z1 model or object meshes not found")
def test_pass_one_reaches_a_reachable_push_and_stays_out_of_the_object():
    from h2d.common.data.tasks import build_task
    from h2d.fullopt import task as tk
    from h2d.fullopt.evaluate import evaluate
    from h2d.fullopt.hoi import HOIClip, from_common_clip
    from h2d.fullopt.relation import REPRESENTATIONS
    from h2d.fullopt.robot import Collision
    from h2d.fullopt.solver import Solver

    band = load_config("candidate_selection.yaml")["reach_band"]
    src = make_clip(carry=False, T=150, push_face="top")         # the top's edge on the robot's side, 0.36 m high
    w = build_task(src, BOX, (30, 90), "R", band=band)["window"]
    full = from_common_clip(src, BOX)
    sl = slice(20, 66)                                            # a short clip: 10 frames before, 36 in contact
    c = HOIClip(fps=full.fps, joints=full.joints[sl], joint_names=full.joint_names, obj_verts=full.obj_verts,
                obj_faces=full.obj_faces, obj_pos=full.obj_pos[sl], obj_quat=full.obj_quat[sl],
                hand_contact=full.hand_contact[sl], meta={"id": "s", "mode": "R", "segment": [10, 46],
                                                          "window": [0, min(46, w[1] - 20)]})
    cfg = load_config("fullopt/solver.yaml")
    coll = Collision(ROBOT)
    corr = load_config("fullopt/correspondence.yaml")[ROBOT.name]
    task = tk.build(c, cfg["task"], band)
    relation = REPRESENTATIONS["a"](c, task, ROBOT, corr, cfg["relation"])
    sol = Solver(ROBOT, cfg, coll=coll).solve(c, task, relation)
    ev, _ = evaluate(c, task, sol["q"], ROBOT, coll, corr, load_config("fullopt/evaluation.yaml"))
    assert sol["qp_ok"].all() and np.mean(sol["step"] < cfg["sqp"]["tol"]) > 0.8
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
