"""Grasp tasks (fullopt spec v0.2 §2.2, §7.5, §8.6): the jaws, the grasp frame from a part's geometry, the gripper's
schedule, and a short synthetic pull of a table solved end to end."""

import math
import sys
from pathlib import Path

import numpy as np
import pytest

from h2d.fullopt import grasp as gp
from h2d.paths import load_config

try:
    from h2d.fullopt.robot import Robot

    ROBOT = Robot()
    GRIPPER = gp.Gripper(ROBOT, load_config("fullopt/grasp.yaml"))
except Exception:  # pragma: no cover - X-Morph checkout missing
    ROBOT = GRIPPER = None
needs_model = pytest.mark.skipif(ROBOT is None, reason="B2-Z1 model not found")


def box(lo, hi):
    """A closed box mesh (verts, faces)."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    V = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    F = [[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4],
         [1, 5, 7], [1, 7, 3]]
    return V, np.array(F)


def merged(*parts):
    V, F, n = [], [], 0
    for v, f in parts:
        V.append(v)
        F.append(f + n)
        n += len(v)
    return np.concatenate(V), np.concatenate(F)


def table(top=(0.6, 0.4), z=(0.43, 0.47), leg=0.04):
    """A table on the floor: a 4 cm top, legs flush with the corners."""
    a, b = top[0] / 2, top[1] / 2
    legs = [box([sx * a - (leg if sx > 0 else 0), sy * b - (leg if sy > 0 else 0), 0.0],
                [sx * a + (0 if sx > 0 else leg), sy * b + (0 if sy > 0 else leg), z[0]])
            for sx in (-1, 1) for sy in (-1, 1)]
    return merged(box([-a, -b, z[0]], [a, b, z[1]]), *legs)


def open_bin(s=0.3):
    """An open box of single sheets (no top): four walls and a bottom, s wide and high."""
    h = s / 2
    V = np.array([[x, y, z] for z in (0.0, s) for x, y in ((-h, -h), (h, -h), (h, h), (-h, h))])
    F = [[0, 1, 2], [0, 2, 3]]
    for i in range(4):
        j = (i + 1) % 4
        F += [[i, j, j + 4], [i, j + 4, i + 4]]
    return V, np.array(F)


@needs_model
def test_the_pad_gap_follows_the_jaw_meshes():
    """The Z1 jaws, 2 cm inserted: 2.9 cm at 20 deg, 4.5 cm at 30, 6.4 cm at 40; the moving jaw's tip leaves the
    insertion beyond 42 deg (gap 6.9 cm), where the opening is capped."""
    g = GRIPPER
    gap = lambda deg: g.gap[np.searchsorted(g.deg, deg)]  # noqa: E731
    assert gap(20) == pytest.approx(0.029, abs=0.002) and gap(30) == pytest.approx(0.045, abs=0.002)
    assert gap(40) == pytest.approx(0.064, abs=0.002) and g.gap_max == pytest.approx(0.069, abs=0.002)
    assert g.opening_for(0.029) == pytest.approx(20, abs=1.0) and g.opening_for(0.08) == 45.0
    assert np.allclose(g.tool_point(0.04), [0.129, 0.0, 0.011])


@needs_model
def test_a_table_edge_is_taken_level_across_its_top_and_off_its_leg():
    V, F = table()
    up, height = np.array([0.0, 0.0, 1.0]), (lambda p: float(p[2]))
    n = np.array([1.0, 0.0, 0.5]) / np.linalg.norm([1.0, 0.0, 0.5])
    g = gp.choose(GRIPPER, V, F, np.array([0.3, 0.0, 0.47]), n, up, n, height, shell=False)
    f = g.frame
    assert g.feasible and (f.kind, f.beta) == ("edge", 0.0) and f.slide == 0.0
    assert f.w == pytest.approx(0.04, abs=0.002) and np.allclose(f.E, [0.3, 0.0, 0.45], atol=0.002)
    assert np.allclose(f.a, [-1, 0, 0], atol=1e-6) and np.allclose(f.c, [0, 0, 1], atol=1e-6)
    assert g.approach_depth <= 0.002 and abs(g.theta_c - g.theta_c_gap) <= 1.0     # a slab parallel to the pads
    assert g.mu_need == pytest.approx(math.tan(math.radians(g.theta_c) / 2))
    # next to a leg (flush at y 0.16-0.20): slid along the edge until the pads (+-3.4 cm) clear it
    g = gp.choose(GRIPPER, V, F, np.array([0.3, 0.17, 0.47]), n, up, n, height, shell=False)
    assert g.feasible and g.frame.w == pytest.approx(0.04, abs=0.002)
    assert 0.17 + g.frame.slide * g.frame.t[1] <= 0.16 - 0.034 + 1e-6


@needs_model
def test_a_bin_rim_is_taken_from_above_with_the_fixed_jaw_outside():
    V, F = open_bin()
    assert gp.odd_line_fraction(V, F) > 0.05 and gp.odd_line_fraction(*box([0, 0, 0], [1, 1, 1])) == 0.0
    up, height = np.array([0.0, 0.0, 1.0]), (lambda p: float(p[2]))
    n, side = np.array([0.6, 0.0, 0.8]), np.array([0.5, 0.0, 0.3])                # the human outside, at +x
    g = gp.choose(GRIPPER, V, F, np.array([0.15, 0.0, 0.3]), n, up, side, height, shell=True)
    f = g.frame
    assert g.feasible and f.kind == "top" and np.allclose(f.a, [0, 0, -1]) and f.c[0] < -0.99   # mover inside
    assert f.w < 0.003 and np.allclose(f.E, [0.15, 0.0, 0.3], atol=0.003)
    assert any("wider" in r for c in g.candidates if c["kind"] == "edge" for r in c["reasons"])  # the wall goes on


def test_the_schedule_opens_before_the_contact_and_reopens_before_the_retreat():
    fps, seg, out = 30.0, (40, 70), np.r_[np.full(40, 0.3), np.zeros(30), np.linspace(0, 0.4, 30)]
    th, ph = gp.schedule(100, seg, fps, 30.0, 12.0, 180.0, 0.3, out, 0.15)
    assert np.abs(np.diff(th)).max() <= 180.0 / fps + 1e-9                        # the gripper's speed
    assert th[ph["open_done"]] == 30.0 and ph["open_done"] == 40 - 9 and th[:ph["open_start"] + 1].max() == 0.0
    assert th[39] == 30.0 and th[40] < 30.0 and np.all(th[ph["closed"]:70] == 12.0) and ph["closed"] - 40 < 3
    assert th[ph["released"]] == 30.0 and ph["released"] - 70 < 3 and ph["reclose"] > ph["released"]
    assert th[-1] == 0.0
    th, ph = gp.schedule(100, (5, 70), fps, 30.0, 12.0, 180.0, 0.3, out, 0.15)  # the clip starts too late
    assert ph["late_start"] and np.all(th[:5] == 30.0)


@needs_model
def test_jaws_in_a_part_are_measured_from_their_meshes():
    """A 4 cm slab between the pads at the closing angle: touching; moved 5 mm along c: 5 mm in."""
    V, F = box([0.129, -0.05, -0.009], [0.2, 0.05, 0.031])
    P = gp.surface_points(V, F, spacing=0.0015)
    th = GRIPPER.opening_for(0.04)
    assert GRIPPER.depth(P, th + 1.0).max() <= 0.0015
    assert GRIPPER.depth(P - [0, 0, 0.005], th + 1.0).max() == pytest.approx(0.005, abs=0.0015)


def pull_clip(T: int = 75, seg=(30, 60)):
    """A person at the origin facing +x pulls a table (edge at x 0.45, top 0.43-0.47 m) 10 cm towards them with the
    right hand on the middle of the edge."""
    from h2d.common.data import omomo_new as om
    from h2d.fullopt.hoi import HOIClip, rename

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
    from synthetic_hoi import standing_pose

    J0, names = rename(standing_pose()[None], om.BODY_NAMES, "common_clip")
    J = np.repeat(J0, T, 0)
    V, F = table()
    pull = np.r_[np.zeros(seg[0]), np.linspace(0, 0.1, seg[1] - seg[0]), np.full(T - seg[1], 0.1)]
    pos = np.c_[0.75 - pull, np.zeros(T), np.zeros(T)]
    reach = np.clip((np.arange(T) - (seg[0] - 15)) / 15, 0, 1) * (np.arange(T) < seg[1] + 5)
    hand = np.c_[pos[:, 0] - 0.3 - 0.05, np.full(T, -0.15), np.full(T, 0.49)]       # palm just off the edge
    rest = J0[0, names.index("r_wrist")]
    idx = {k: names.index(k) for k in ("r_wrist", "r_index", "r_pinky", "r_elbow")}
    for k, off in (("r_wrist", [-0.07, 0, 0.02]), ("r_index", [0.02, 0.02, 0.0]), ("r_pinky", [0.02, -0.02, 0.0]),
                   ("r_elbow", [-0.3, -0.03, 0.15])):
        J[:, idx[k]] = (1 - reach[:, None]) * J0[0, idx[k]] + reach[:, None] * (hand + off)
    assert np.isfinite(rest).all()
    hc = np.zeros((T, 2), bool)
    hc[seg[0]:seg[1], 1] = True
    return HOIClip(fps=30.0, joints=J, joint_names=names, obj_verts=V, obj_faces=F, obj_pos=pos,
                   obj_quat=np.tile([0.0, 0.0, 0.0, 1.0], (T, 1)), hand_contact=hc,
                   meta={"id": "pull", "object": "table", "mode": "R", "segment": list(seg), "window": [0, T],
                         "grip": "grasp", "interaction": "pull"})


@needs_model
def test_a_synthetic_table_pull_is_grasped_and_reached():
    from h2d.fullopt import task as tk
    from h2d.fullopt.evaluate import evaluate
    from h2d.fullopt.relation import REPRESENTATIONS
    from h2d.fullopt.robot import Collision
    from h2d.fullopt.solver import Solver

    c = pull_clip()
    cfg, ecfg = load_config("fullopt/solver.yaml"), load_config("fullopt/evaluation.yaml")
    corr = load_config("fullopt/correspondence.yaml")[ROBOT.name]
    task = tk.build(c, cfg["task"], None, GRIPPER)
    g = task.record["grasp"]
    assert task.grip == "grasp" and g["feasible"] and (g["kind"], g["beta_deg"]) == ("edge", 0.0)
    assert task.theta[29] == g["theta_open_deg"] and task.theta[45] == g["theta_c_deg"]
    coll = Collision(ROBOT)
    rel = REPRESENTATIONS["a"](c, task, ROBOT, corr, cfg["relation"])
    sol = Solver(ROBOT, cfg, coll=coll).solve(c, task, rel)
    ev, _ = evaluate(c, task, sol["q"], ROBOT, coll, corr, ecfg, GRIPPER)
    rc = ev["reach"]
    assert rc["reached"], rc["fail_reasons"]
    assert not rc["clear"]["bad_frames"] and rc["timing"]["gripper_speed_max_deg_s"] <= 180.0 + 1e-6
    assert ev["penetration"]["collision_frames"] == 0 and ev["penetration"]["body_in_object_m"] < 1e-3
    q = sol["q"][45, ROBOT.qadr[ROBOT.desc["gripper"]["joint"]]]
    assert q == pytest.approx(-math.radians(g["theta_c_deg"]))                    # the solution carries the gripper


def test_the_body_checks_skip_the_clips_counted_as_not_reached():
    """A clip the reach check counts as failed is not failed again by the body checks (its values are listed apart);
    an infeasible grasp is outside the reach bar, so its body still counts."""
    import importlib.util

    path = Path(__file__).resolve().parents[2] / "scripts" / "fullopt" / "solve.py"
    spec = importlib.util.spec_from_file_location("fullopt_solve", path)
    sv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sv)
    crit = load_config("fullopt/evaluation.yaml")["pass"]

    def row(i, reached, feasible=True, body=0.0, sole=0.001, trunk=1.0):
        return {"id": i, "agreement": None, "solver": {"unconverged_frames": 0, "qp_failures": 0},
                "reach": {"reached": reached, "fail_reasons": {}, "clear": {"bad_frames": []}, "friction": "ok",
                          "grasp": {"feasible": feasible, "reasons": []}},
                "penetration": {"body_in_object_m": body, "object_under_body_frames": 0, "collision_frames": 0},
                "feet": {"sole_height_max_m": sole},
                "limits": {"trunk_speed_ratio_max": trunk, "trunk_accel_ratio_max": trunk}}

    rows = [row(f"r{i}", True, trunk=1.02) for i in range(9)] + [row("miss", False, body=0.05, sole=0.01, trunk=1.3)]
    for kind in ("grasp", "press"):
        ch = sv.checks_of(rows, 0, crit, "dev", kind)
        assert ch["reached"]["pass"] and ch["body_in_object"]["max_m"] == 0.0, kind      # 9/10, 90 %
        assert ch["body_in_object"]["pass"] and ch["feet_on_floor"]["pass"] and ch["trunk_within_limits"]["pass"]
        assert ch["body_in_object"]["not_reached"] == {"miss": 0.05}
    rows[-1] = row("off", True, feasible=False, body=0.05)
    ch = sv.checks_of(rows, 0, crit, "dev", "grasp")
    assert ch["reached"]["of"] == 9 and not ch["body_in_object"]["pass"] and not ch["body_in_object"]["not_reached"]
