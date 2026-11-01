"""Evaluation of a solved clip (fullopt spec v0.2 §8.1) with the learned line's definitions, so the two lines' numbers
compare (``scripts/learned/reach_diag.py``, ``h2d/learned/imesh.py``; thresholds in configs/fullopt/evaluation.yaml):

* reach, per contact frame: the contact point within ``pos_tol_m`` of the target, the tool axis within
  ``max_angle_deg`` of the approach target, and collision free (``Collision.check``: no self or arm-floor penetration
  and the arm outside the object, each within ``penetration_tol_m``). A task is reached when every contact frame is
  (the learned line's label "feasible" of its position + direction problem); the roll error is reported only;
* penetration on every frame: the body (trunk, legs, arm mount), the arm and the tool in the object's hull, the
  closest self pair, the arm's floor distance, and the object under the body: the overlap of the object's hull with
  the under-body box (an LP per frame), whose thickness is the diameter of the largest ball inside both;
* collision on every frame (reach's collision test covers the contact frames only): a self pair, or any geom but the
  soles through the floor, beyond the same tolerance;
* feet: the soles' height above the floor, and how far the feet slide (pass 1 has no contact schedule) and stray
  from their nominal footholds;
* limits: joint range violations, joint and trunk speeds and trunk accelerations against the description's limits
  over consecutive frames, the trunk's tilt, its vertical speed and its largest acceleration;
* relations on the fixed evaluation network: pelvis, chest and hand against the object's 24 samples, Delaunay per
  frame, edges from the pelvis or the chest to the hand or a sample with a horizontal length of at least 5 cm; the
  human points averaged over 1 s inside the task window; on the robot, the points phi gives the pelvis and the chest,
  and the contact target for the hand. Mean edge-direction error and heading error (trunk forward against the
  human's facing, shoulder line x vertical) over the contact frames, and the share of frames where the robot stands on
  the human's side of the object (horizontal directions from the object's centre within ``same_side_deg``).
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.optimize import linprog
from scipy.spatial import Delaunay
from scipy.spatial.transform import Rotation as R

from h2d.common.collision import ObjectHull
from h2d.fullopt import task as tk
from h2d.fullopt.hoi import HOIClip
from h2d.fullopt.relation import object_track
from h2d.fullopt.robot import Collision, Robot

MIN_EDGE_M = 0.05


def _deg(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.degrees(np.arccos(np.clip(np.sum(a * b, -1), -1.0, 1.0)))


def _unit2(v: np.ndarray) -> np.ndarray:
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)


def _stat(x) -> dict:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return {"median": float(np.median(x)), "max": float(x.max())} if x.size else {"median": None, "max": None}


def reach(robot: Robot, coll: Collision, task: tk.Task, Q: np.ndarray, hull: ObjectHull, Ro, po, cfg: dict):
    """Per contact frame: error, tool-axis angle, roll angle, collision check, reached. Returns (summary, arrays)."""
    fr = np.arange(*task.segment)
    a = {k: np.zeros(len(fr)) for k in ("err", "ang", "roll", "self", "floor", "arm_obj", "tool_obj")}
    a["ok"] = np.zeros(len(fr), bool)
    for i, t in enumerate(fr):
        robot.set(Q[t])
        a["err"][i] = np.linalg.norm(robot.tool_point() - task.target[t])
        a["ang"][i] = _deg(robot.axis(robot.tool_body, robot.approach_local), task.tool_x[t])
        a["roll"][i] = _deg(robot.axis(robot.tool_body, robot.jaw_local), task.tool_z[t])
        col = coll.check(hull, lambda P, t=t: (P - po[t]) @ Ro[t])
        a["self"][i], a["floor"][i] = col["self_min_dist_m"], col["floor_min_dist_m"]
        a["arm_obj"][i], a["tool_obj"][i] = col["arm_obj_depth_m"], col["tool_obj_depth_m"]
        a["ok"][i] = a["err"][i] <= cfg["pos_tol_m"] and a["ang"][i] <= cfg["max_angle_deg"] and col["collision_free"]
    tol, fail = cfg["penetration_tol_m"], ~a["ok"]
    out = {"reached": bool(a["ok"].all()), "reached_frac": float(a["ok"].mean()), "frames": int(len(fr)),
           "err_m": _stat(a["err"]), "angle_deg": _stat(a["ang"]), "roll_median_deg": _stat(a["roll"])["median"],
           "fail_reasons": {"pos_error": int(np.sum(fail & (a["err"] > cfg["pos_tol_m"]))),
                            "angle": int(np.sum(fail & (a["ang"] > cfg["max_angle_deg"]))),
                            "self_collision": int(np.sum(fail & (a["self"] <= -tol))),
                            "floor": int(np.sum(fail & (a["floor"] <= -tol))),
                            "arm_object": int(np.sum(fail & (a["arm_obj"] > tol)))}}
    return out, a


def under_body(robot: Robot, hull: ObjectHull, Ro: np.ndarray, po: np.ndarray) -> float:
    """Thickness of the overlap of the object's hull and the under-body box at the current state: twice the radius of
    the largest ball inside both (an LP in the object's frame), 0 when they do not overlap."""
    Rc, c = robot.cage_frame()
    U, cl, h = Ro.T @ Rc, Ro.T @ (c - po), robot.cage["half"]       # box axes and centre in the object's frame
    A = np.vstack([np.c_[hull.A, np.ones(len(hull.A))], np.c_[U.T, np.ones(3)], np.c_[-U.T, np.ones(3)]])
    b = np.r_[-hull.b, h + U.T @ cl, h - U.T @ cl]
    res = linprog([0, 0, 0, -1], A_ub=A, b_ub=b, bounds=[(None, None)] * 4, method="highs")
    return 2.0 * max(0.0, -float(res.fun)) if res.success else float("nan")


def penetration(robot: Robot, coll: Collision, Q: np.ndarray, hull: ObjectHull, Ro, po, frames, tol: float) -> dict:
    """Deepest values over ``frames``: body / arm / tool in the object, closest self pair, arm-floor distance, the
    object under the body; collision on any frame (a self pair, or any geom but the soles, through the floor by more
    than ``tol``, the tolerance of reach's collision test); and the per-frame body depth and under-body overlap."""
    rows, pairs, low = [], [], []
    for t in frames:
        robot.set(Q[t])
        col = coll.check(hull, lambda P, t=t: (P - po[t]) @ Ro[t])
        cage = under_body(robot, hull, Ro[t], po[t]) if robot.cage is not None else 0.0
        floor, body = coll.floor_distance()
        rows.append([col["body_obj_depth_m"], col["arm_obj_depth_m"], col["tool_obj_depth_m"], col["self_min_dist_m"],
                     col["floor_min_dist_m"], cage, floor])
        pairs.append(col["self_worst_pair"])
        low.append(body)
    x = np.array(rows)
    hit = (x[:, 3] < -tol) | (x[:, 6] < -tol)
    i, j = int(x[:, 3].argmin()), int(x[:, 6].argmin())
    fr = list(frames)
    return {"body_in_object_m": float(x[:, 0].max()), "arm_in_object_m": float(x[:, 1].max()),
            "tool_in_object_m": float(x[:, 2].max()), "self_min_dist_m": float(x[:, 3].min()),
            "arm_floor_min_dist_m": float(x[:, 4].min()), "body_in_object_frames": int(np.sum(x[:, 0] > 0.0)),
            "object_under_body_m": float(x[:, 5].max()), "object_under_body_frames": int(np.sum(x[:, 5] > tol)),
            "collision_frames": int(hit.sum()), "collision_frame_list": [fr[k] for k in np.flatnonzero(hit)],
            "self_worst": {"dist_m": float(x[i, 3]), "frame": fr[i], "pair": pairs[i]},
            "floor_worst": {"dist_m": float(x[j, 6]), "frame": fr[j], "body": low[j]},
            "per_frame_body_in_object_m": x[:, 0], "per_frame_object_under_body_m": x[:, 5]}


def feet(robot: Robot, Q: np.ndarray, fps: float) -> dict:
    """Soles above the floor (|height|, all frames and feet), and per foot the horizontal path, speed and distance from
    the nominal foothold (largest over the feet)."""
    P, F = np.zeros((len(Q), len(robot.feet), 3)), np.zeros((len(Q), len(robot.feet), 3))
    for t in range(len(Q)):
        robot.set(Q[t])
        P[t], F[t] = robot.data.xpos[robot.feet], robot.footholds()
    step = np.linalg.norm(np.diff(P[..., :2], axis=0), axis=-1)
    return {"sole_height_max_m": float(np.abs(P[..., 2] - robot.foot_radius).max()),
            "slide_path_max_m": float(step.sum(0).max()), "slide_speed_max_mps": float(step.max(initial=0.0) * fps),
            "foothold_offset_max_m": float(np.linalg.norm((P - F)[..., :2], axis=-1).max())}


def limits(robot: Robot, Q: np.ndarray, fps: float, cfg: dict) -> dict:
    """Joint range violations [rad]; speeds (joints, the trunk per axis) and the trunk's accelerations against the
    description's limits over consecutive frames, as ratios (above 1: too fast); the trunk's tilt, vertical speed and
    largest acceleration."""
    j = np.flatnonzero((robot.dof_qadr >= 0) & np.isfinite(robot.lower))
    val = Q[:, robot.dof_qadr[j]]
    over = np.maximum(np.maximum(robot.lower[j] - val, val - robot.upper[j]), 0.0)
    d = np.flatnonzero(np.isfinite(robot.speed))
    V = np.array([robot.difference(Q[t - 1], Q[t], d) for t in range(1, len(Q))]).reshape(-1, len(d)) * fps
    ratio = np.abs(V) / robot.speed[d]
    b = robot.groups["base"]
    Vb = np.array([robot.difference(Q[t - 1], Q[t], b) for t in range(1, len(Q))]).reshape(-1, 6) * fps
    Ab = np.diff(Vb, axis=0) * fps
    acc = np.abs(Ab) / robot.accel[b]
    tilt = []
    for q in Q:
        robot.set(q)
        tilt.append(np.degrees(np.arcsin(np.abs(robot.tilt()).max())))
    return {"range_violation_max_rad": float(over.max()),
            "range_violation_frames": int(np.sum((over > cfg["joint_limit_tol_rad"]).any(1))),
            "speed_ratio_max": float(ratio.max(initial=0.0)),
            "speed_violation_frames": int(np.sum((ratio > 1.0 + 1e-6).any(1))),
            "trunk_speed_ratio_max": float((np.abs(Vb) / robot.speed[b]).max(initial=0.0)),
            "trunk_accel_ratio_max": float(acc.max(initial=0.0)),
            "trunk_speed_max_mps": float(np.linalg.norm(Vb[:, :2], axis=1).max(initial=0.0)),
            "trunk_vertical_speed_max_mps": float(np.abs(Vb[:, 2]).max(initial=0.0)),
            "trunk_accel_max_mps2": float(np.abs(Ab[:, :3]).max(initial=0.0)),
            "trunk_vertical_accel_max_mps2": float(np.abs(Ab[:, 2]).max(initial=0.0)),
            "trunk_angular_accel_max_radps2": float(np.abs(Ab[:, 3:]).max(initial=0.0)),
            "trunk_tilt_max_deg": float(max(tilt))}


def relations(c: HOIClip, task: tk.Task, Q: np.ndarray, robot: Robot, corr: dict, cfg: dict, k: int = 24) -> dict:
    """The fixed evaluation network over the task window; means over the contact frames and over the window."""
    fr = task.frames
    sm = lambda x: uniform_filter1d(x, max(1, round(c.fps)) | 1, axis=0, mode="nearest")  # noqa: E731
    H = sm(np.stack([c.joint(n)[fr] for n in ("pelvis", "chest", "l_shoulder", "r_shoulder")], 1))
    objs = object_track(c, k)[fr]
    fix_h = np.concatenate([sm(tk.palm(c, task.mode, fr))[:, None], objs], 1)
    fix_d = np.concatenate([task.target[fr][:, None], objs], 1)
    ev = corr["evaluation"]
    P, fwd = np.zeros((len(fr), 2, 2)), np.zeros((len(fr), 2))
    for i, t in enumerate(fr):
        robot.set(Q[t])
        P[i] = [robot.point(ev["pelvis"])[:2], robot.point(ev["chest"])[:2]]
        fwd[i] = robot.heading()
    edge = []                                               # (frame, error deg)
    for i in range(len(fr)):
        pts = np.vstack([H[i, :2], fix_h[i]])
        pairs = {(a, b) for s in Delaunay(pts, qhull_options="QJ").simplices for a in s for b in s if a < b}
        for a, j in pairs:
            if a < 2 <= j and np.linalg.norm(pts[a, :2] - pts[j, :2]) >= MIN_EDGE_M:
                edge.append((i, float(_deg(_unit2(P[i, a] - fix_d[i, j - 2, :2]), _unit2(pts[a, :2] - pts[j, :2])))))
    edge = np.array(edge).reshape(-1, 2)
    sh = H[:, 2, :2] - H[:, 3, :2]
    heading = _deg(fwd, _unit2(np.stack([sh[:, 1], -sh[:, 0]], 1)))
    centre = R.from_quat(c.obj_quat[fr]).apply(0.5 * (c.obj_verts.min(0) + c.obj_verts.max(0))) + c.obj_pos[fr]
    side = _deg(_unit2(H[:, 0, :2] - centre[:, :2]), _unit2(P[:, 0] - centre[:, :2])) <= cfg["same_side_deg"]
    con = (fr >= task.segment[0]) & (fr < task.segment[1])
    out = {}
    for name, sel in (("contact", con), ("window", np.ones(len(fr), bool))):
        e = edge[np.isin(edge[:, 0], np.flatnonzero(sel)), 1]
        out[name] = {"edge_dir_err_deg": float(e.mean()) if e.size else None,
                     "heading_err_deg": float(heading[sel].mean()), "same_side_frac": float(side[sel].mean())}
    return out


def evaluate(c: HOIClip, task: tk.Task, Q: np.ndarray, robot: Robot, coll: Collision, corr: dict, cfg: dict):
    """All of §8.1 for one solved clip (floor at z = 0). Returns (summary, per contact frame arrays)."""
    hull = ObjectHull.from_vertices(np.asarray(c.obj_verts, float))
    Ro, po = R.from_quat(c.obj_quat).as_matrix(), c.obj_pos
    rch, arrays = reach(robot, coll, task, Q, hull, Ro, po, cfg)
    pen = penetration(robot, coll, Q, hull, Ro, po, range(c.n), cfg["penetration_tol_m"])
    arrays["body_in_object"] = pen.pop("per_frame_body_in_object_m")
    arrays["object_under_body"] = pen.pop("per_frame_object_under_body_m")
    con = np.arange(*task.segment)
    return {"reach": rch, "penetration": pen,
            "body_in_object_contact_m": float(arrays["body_in_object"][con].max()), "feet": feet(robot, Q, c.fps),
            "limits": limits(robot, Q, c.fps, cfg), "relations": relations(c, task, Q, robot, corr, cfg)}, arrays
