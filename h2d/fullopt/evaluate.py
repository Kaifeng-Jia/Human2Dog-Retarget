"""Evaluation of a solved clip (fullopt spec v0.2 §8.1) with the learned line's definitions, so the two lines' numbers
compare (``scripts/learned/reach_diag.py``, ``h2d/learned/imesh.py``; thresholds in configs/fullopt/evaluation.yaml):

* reach, per contact frame: the contact point within ``pos_tol_m`` of the target, the tool axis within
  ``max_angle_deg`` of the approach target, and collision free (``Collision.check``: no self or arm-floor penetration
  and the arm outside the object, each within ``penetration_tol_m``). A task is reached when every contact frame is
  (the learned line's label "feasible" of its position + direction problem); the roll error is reported only;
* penetration on every frame: the body (trunk, legs, arm mount), the arm and the tool in the object's hull, the
  closest self pair, the arm's floor distance, and the feet below the floor (pass 1 keeps the legs at home);
* limits: joint range violations, joint and trunk speeds against the limits over consecutive frames;
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


def penetration(robot: Robot, coll: Collision, Q: np.ndarray, hull: ObjectHull, Ro, po, frames) -> dict:
    """Deepest values over ``frames``: body / arm / tool in the object, closest self pair, arm-floor distance, feet
    below the floor; and the frames of the deepest body point."""
    rows = []
    r_foot = robot.desc["foot_radius_m"]
    for t in frames:
        robot.set(Q[t])
        col = coll.check(hull, lambda P, t=t: (P - po[t]) @ Ro[t])
        feet = robot.data.xpos[robot.feet][:, 2] - r_foot
        rows.append([col["body_obj_depth_m"], col["arm_obj_depth_m"], col["tool_obj_depth_m"], col["self_min_dist_m"],
                     col["floor_min_dist_m"], max(0.0, -float(feet.min()))])
    x = np.array(rows)
    return {"body_in_object_m": float(x[:, 0].max()), "arm_in_object_m": float(x[:, 1].max()),
            "tool_in_object_m": float(x[:, 2].max()), "self_min_dist_m": float(x[:, 3].min()),
            "arm_floor_min_dist_m": float(x[:, 4].min()), "feet_below_floor_m": float(x[:, 5].max()),
            "body_in_object_frames": int(np.sum(x[:, 0] > 0.0)), "per_frame_body_in_object_m": x[:, 0]}


def limits(robot: Robot, Q: np.ndarray, fps: float, cfg: dict) -> dict:
    """Joint range violations [rad]; speeds against the limits (joints, and the trunk per axis) over consecutive
    frames, as ratios (above 1: too fast)."""
    j = np.flatnonzero((robot.dof_qadr >= 0) & np.isfinite(robot.lower))
    val = Q[:, robot.dof_qadr[j]]
    over = np.maximum(np.maximum(robot.lower[j] - val, val - robot.upper[j]), 0.0)
    d = np.flatnonzero(np.isfinite(robot.speed))
    V = np.array([robot.difference(Q[t - 1], Q[t], d) for t in range(1, len(Q))]).reshape(-1, len(d)) * fps
    ratio = np.abs(V) / robot.speed[d]
    xy = np.linalg.norm(np.diff(Q[:, robot.base_qadr:robot.base_qadr + 2], axis=0), axis=1) * fps
    return {"range_violation_max_rad": float(over.max()),
            "range_violation_frames": int(np.sum((over > cfg["joint_limit_tol_rad"]).any(1))),
            "speed_ratio_max": float(ratio.max(initial=0.0)),
            "speed_violation_frames": int(np.sum((ratio > 1.0 + 1e-6).any(1))),
            "trunk_speed_max_mps": float(xy.max(initial=0.0))}


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
    pen = penetration(robot, coll, Q, hull, Ro, po, range(c.n))
    arrays["body_in_object"] = pen.pop("per_frame_body_in_object_m")
    con = np.arange(*task.segment)
    return {"reach": rch, "penetration": pen,
            "body_in_object_contact_m": float(arrays["body_in_object"][con].max()),
            "limits": limits(robot, Q, c.fps, cfg), "relations": relations(c, task, Q, robot, corr, cfg)}, arrays
