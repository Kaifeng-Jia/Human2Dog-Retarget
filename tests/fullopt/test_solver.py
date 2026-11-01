"""Per-frame SQP (fullopt spec v0.2 §7): the step QP, and pass 1 on a short synthetic push."""

import sys
from pathlib import Path

import numpy as np
import pytest

from h2d.fullopt.solver import StepQP
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
    assert ev["penetration"]["body_in_object_m"] < 1e-3 and ev["penetration"]["arm_in_object_m"] < 2e-3
    assert ev["limits"]["range_violation_frames"] == 0
    assert ev["relations"]["contact"]["same_side_frac"] == 1.0
