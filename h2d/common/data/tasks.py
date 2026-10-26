"""Human-side task targets of one confirmed push segment (spec learned v0.6 §4 step 1, §5.1-5.2), shared by both lines.

For a segment [s, e) and its virtual-hand mode ("R", "L" or "B", ``describe.contact_point``), over a window that adds
``pre_s`` before and ``post_s`` after:

* ``c_bar`` (object frame, contact frames): the contact proxy projected onto the surface, lightly smoothed
  (centred moving average over ``smooth`` frames) and projected again, so the target lies on the mesh;
* ``n_bar`` (object frame, one per segment): the mean patch normal under the proxy, pointing to the hand. The
  candidates were selected for one flat face (spread p90 <= 20 deg, coherence >= 0.8), so one normal per
  segment (spec §5.2: an approximately planar patch keeps one normal);
* ``d`` (window): palm distance to the contact plane along ``n_bar``, zeroed by its median over the contact
  frames (palm thickness), clipped at 0, and 0 in contact (spec §5.2);
* ``target_local`` / ``target_world`` (window): c~_t = c_bar_ref + d_t n_bar, with c_bar_ref the first contact
  target before contact and the last after it, mapped to the world with the recorded object pose O_t.

The object trajectory is copied unchanged (it is fixed in the optimisation and moves with the demo time).
"""

from __future__ import annotations

import json

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as R

from h2d.common.data.describe import contact_point, hand_frame, palm_point
from h2d.common.data.omomo_new import BODY_INDEX, Clip
from h2d.common.objectmesh import ObjectMesh

TASK_VERSION = 2                     # 2: tool pose from the forearm and the hand (spec v0.8 §5.4), body points
BODY_POINTS = ("Pelvis", "Chest", "L_Shoulder", "R_Shoulder")


def _smooth(x: np.ndarray, k: int) -> np.ndarray:
    k = min(k, len(x))
    k -= 1 - k % 2                                     # odd window, centred
    if k <= 1:
        return x.copy()
    pad = k // 2
    xp = np.pad(x, ((pad, pad), (0, 0)), mode="edge")
    c = np.cumsum(np.vstack([np.zeros((1, x.shape[1])), xp]), axis=0)
    return (c[k:] - c[:-k]) / k


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def adapt_height(obj: ObjectMesh, c_bar: np.ndarray, n_bar: np.ndarray, pos0, rot0, z_human: float, band: dict,
                 margin: float = 0.05) -> tuple[np.ndarray, dict]:
    """Move the contact targets up or down the same flat face so the robot contacts it inside the arm's height band
    (spec v0.7 §5.1, Kevin: pushing a tall object at the human's chest height keeps its meaning lower down). Same
    face, same normal, same position along the face; a constant in-plane shift in the object frame. Top faces keep
    their height. Returns the shifted targets and a record."""
    from h2d.common.data.candidates import face_of

    Rm = R.from_quat(rot0).as_matrix()
    n_w = Rm @ n_bar
    tilt = float(np.degrees(np.arcsin(min(1.0, abs(n_w[2])))))
    face = face_of(tilt)
    fp = obj.face_points(np.median(c_bar, 0), n_bar)
    fz = (fp @ Rm.T + np.asarray(pos0))[:, 2] if len(fp) else np.zeros(1)
    rec = {"face": face, "face_z_range_m": [float(fz.min()), float(fz.max())], "human_contact_z_m": float(z_human),
           "height_shift_m": 0.0, "robot_contact_z_m": float(z_human), "height_adapted": False, "in_band": True}
    lo, hi = band.get(face, (-np.inf, np.inf))
    if face == "top":
        rec["in_band"] = bool(lo <= z_human <= hi)
        return c_bar, rec
    a, b = max(lo, fz.min() + margin), min(hi, fz.max() - margin)
    if a > b:
        rec["in_band"] = False
        return c_bar, rec
    z_star = float(min(max(z_human, a), b))
    if abs(z_star - z_human) < 1e-6:
        return c_bar, rec
    up_w = np.array([0.0, 0.0, 1.0]) - n_w[2] * n_w
    up_w /= np.linalg.norm(up_w)
    shift_local = Rm.T @ up_w * ((z_star - z_human) / up_w[2])
    c0 = np.median(c_bar, 0)
    moved = c_bar + shift_local
    moved -= np.outer((moved - c0) @ n_bar, n_bar)                  # stay on the face plane
    rec.update(height_shift_m=z_star - z_human, robot_contact_z_m=z_star, height_adapted=True)
    return moved, rec


def gripper_axes(x: np.ndarray, across: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Tool x (approach, given) and tool z (jaw closing) from the hand's roll (spec v0.8 §5.4, Kevin): the Z1 mover
    turns about tool y, which follows the line across the knuckles; z = x cross y. One rule for press and grasp: a
    flat palm pushing along the forearm gets z along the fingers, a hand wrapping a rim gets z across the palm."""
    y = _unit(across - np.sum(across * x, -1, keepdims=True) * x)
    return x, np.cross(x, y)


def clamp_cone(v: np.ndarray, axis: np.ndarray, max_deg: float) -> np.ndarray:
    """Rotate unit vectors v (n, 3) towards the unit axis until they are within max_deg of it."""
    c = v @ axis
    t = _unit(v - c[:, None] * axis)
    lim = np.radians(max_deg)
    return np.where((c < np.cos(lim))[:, None], np.cos(lim) * axis + np.sin(lim) * t, v)


def from_behind(obj: ObjectMesh, c_bar: np.ndarray, pos: np.ndarray, rot: np.ndarray, band: dict | None,
                below_m: float = 0.08) -> tuple[np.ndarray, np.ndarray, dict]:
    """A push on a top face is done from the robot's side (spec v0.8 §5.6, Kevin, R013: pressing down on a low top
    is out of the arm's reach and pushes only by friction). Same push direction, same position across the object:
    the contact moves onto the vertical face that faces the robot when that face reaches the arm's side band
    (``adapt_height``), else onto the edge between that face and the top, pushed 45 deg down and forward. Returns
    the contact targets (object frame, contact frames), the outward approach normal and a record."""
    Rm = R.from_quat(rot[0]).as_matrix()
    up = Rm.T @ np.array([0.0, 0.0, 1.0])
    v = Rm.T @ (pos[-1] - pos[0])
    u = -_unit(v - (v @ up) * up)                                   # towards the robot, against the push
    rim = obj.hull_verts[np.abs(obj.hull_verts @ up - np.median(c_bar @ up)) < 0.03]
    rim = rim if len(rim) else obj.hull_verts
    edge = obj.closest_face(c_bar + np.outer((rim @ u).max() - c_bar @ u, u))[1]
    z = lambda pts: float(np.median((pts @ Rm.T + pos[0])[:, 2]))  # noqa: E731
    q, dist, n, _ = obj.patch_normals(edge + 0.03 * u - below_m * up, 0.03)
    if band and np.median(dist) < 0.06 and np.median(n @ u) > np.cos(np.radians(30)):   # a face below the edge
        n_f = _unit(n.mean(0))
        moved, rec = adapt_height(obj, q, n_f, pos[0], rot[0], z(q), band)
        if rec["in_band"]:
            return moved, n_f, dict(rec, contact_moved="rear_face")
    return edge, _unit(u + up), {"face": "edge", "robot_contact_z_m": z(edge), "contact_moved": "rear_edge",
                                 "in_band": True}


def build_task(clip: Clip, obj: ObjectMesh, seg: tuple[int, int], mode: str, pre_s: float = 1.0,
               post_s: float = 1.0, smooth: int = 5, patch_m: float = 0.03, band: dict | None = None,
               grip: str = "press", interaction: str = "push", tool_max_deg: float = 45.0,
               palm_max_deg: float = 60.0) -> dict:
    """``band`` ({face: [z_lo, z_hi]}): adapt the contact height to the arm (``adapt_height``). A push on a top face
    is moved to the robot's side (``from_behind``). Tool pose (spec v0.8 §5.4): the approach is the human forearm
    (elbow -> wrist, the direction the human pushes along), turned into a ``tool_max_deg`` cone about the inward
    normal of the robot's contact (the inward normal itself if the forearm points away from the object); the roll
    follows the hand (``gripper_axes``) when the palm faces the human's contact within ``palm_max_deg`` (else, e.g.
    a flipped hand, no roll target). The palm side is the side that touches: a hand whose points give the palm
    facing away (> 90 deg) is mirrored first (``palm_flipped``)."""
    s, e = int(seg[0]), int(seg[1])
    fps = clip.fps
    w0, w1 = max(0, s - round(pre_s * fps)), min(clip.n, e + round(post_s * fps))
    fr = np.arange(w0, w1)
    contact = (fr >= s) & (fr < e)
    pos, rot = clip.obj_pos[fr], clip.obj_rot_xyzw[fr]

    cp = contact_point(clip, mode, fr[contact])
    loc = obj.to_local(cp[:, None], pos[contact], rot[contact])[:, 0]
    q, dist, n, coh = obj.patch_normals(loc, patch_m)
    n_bar = n.mean(0)
    n_bar /= max(float(np.linalg.norm(n_bar)), 1e-12)
    c_bar = obj.closest_face(_smooth(q, smooth))[1]
    c_human = c_bar.copy()
    z_human = float(np.median([obj.world_points(pos[contact][i], rot[contact][i], c_bar[i][None])[0, 2]
                               for i in range(len(c_bar))]))
    height = {"face": "", "human_contact_z_m": z_human, "robot_contact_z_m": z_human, "height_shift_m": 0.0,
              "height_adapted": False, "in_band": True}
    n_robot = n_bar
    top = abs(R.from_quat(rot[contact][0]).apply(n_bar)[2]) > np.sin(np.radians(60))
    if interaction == "push" and grip == "press" and top:
        c_bar, n_robot, rec = from_behind(obj, c_bar, pos[contact], rot[contact], band)
        height.update({k: v for k, v in rec.items() if k != "human_contact_z_m"},
                      height_shift_m=rec["robot_contact_z_m"] - z_human)
        on_face = float(obj.surface_distance(c_bar).max())
    else:
        if band:
            c_bar, height = adapt_height(obj, c_bar, n_bar, pos[contact][0], rot[contact][0], z_human, band)
        fp = obj.face_points(np.median(c_bar, 0), n_bar)
        on_face = float(cKDTree(fp).query(c_bar)[0].max()) if len(fp) else float("nan")

    palm = palm_point(clip, mode, fr)
    palm_loc = obj.to_local(palm[:, None], pos, rot)[:, 0]
    ref = np.where(fr[:, None] < s, c_bar[0], c_bar[-1])
    ref[contact] = c_bar
    d_raw = np.sum((palm_loc - ref) * n_robot, 1)
    offset = float(np.median(d_raw[contact]))
    d = np.clip(d_raw - offset, 0.0, None)
    d[contact] = 0.0
    target_local = ref + d[:, None] * n_robot
    target_world = np.stack([obj.world_points(pos[i], rot[i], target_local[i][None])[0] for i in range(len(fr))])
    c_bar_w = np.full((len(fr), 3), np.nan)
    c_bar_w[contact] = c_bar

    to_obj = R.from_quat(rot).inv()
    palm_n, across, fore = (_unit(_smooth(to_obj.apply(v), smooth)) for v in hand_frame(clip, mode, fr))
    deg = lambda a, b: float(np.degrees(np.arccos(np.clip(np.median(a @ b), -1, 1))))  # noqa: E731
    palm_face, fore_face = deg(palm_n[contact], -n_bar), deg(fore[contact], -n_robot)
    palm_flipped = palm_face > 90.0         # the palm is the side that touches (R014: 149-173 deg on all two-hand
    if palm_flipped:                        # pushes, a mirrored hand convention in the data or flipped hands)
        palm_n, across, palm_face = -palm_n, -across, 180.0 - palm_face
    palm_used, fore_used = palm_face <= palm_max_deg, fore_face <= 90.0
    tool_x = clamp_cone(fore, -n_robot, tool_max_deg) if fore_used else np.tile(-n_robot, (len(fr), 1))
    tool_z = gripper_axes(tool_x, across)[1] if palm_used else np.full((len(fr), 3), np.nan)
    return {
        "task_version": TASK_VERSION, "clip": clip.name, "object": clip.obj, "mode": mode, "fps": float(fps),
        "segment": [s, e], "window": [int(w0), int(w1)],
        "frames": fr, "in_contact": contact, "obj_pos": pos, "obj_rot_xyzw": rot,
        "c_bar_local": c_bar_w, "n_bar_local": n_robot, "n_bar_human_local": n_bar, "d": d, "palm_offset_m": offset,
        "target_local": target_local, "target_world": target_world, "palm_world": palm,
        "proxy_surface_dist_m": dist, "patch_coherence": coh,
        "normal_spread_deg": np.degrees(np.arccos(np.clip(n @ n_bar, -1, 1))),
        "c_bar_human_local": c_human, "height": height, "target_on_face_m": on_face,
        "grip": grip, "palm_normal_local": palm_n, "palm_face_deg": palm_face, "palm_used": bool(palm_used),
        "palm_flipped": bool(palm_flipped),
        "forearm_local": fore, "forearm_face_deg": fore_face, "forearm_used": bool(fore_used),
        "tool_x_local": tool_x, "tool_z_local": tool_z,
        "body_world": clip.body_pos[fr][:, [BODY_INDEX[b] for b in BODY_POINTS]],     # interaction mesh (spec §5.5)
        "skeleton_world": clip.body_pos[fr],                                             # for the videos
    }


def task_checks(task: dict) -> dict:
    """Sanity of the extracted targets (all must hold for the diagnostic to use the task)."""
    c = task["in_contact"]
    on_surface = float(np.nanmax(np.linalg.norm(task["target_local"][c] - task["c_bar_local"][c], axis=1)))
    step = np.linalg.norm(np.diff(task["target_world"], axis=0), axis=1)
    return {
        "contact_frames": int(c.sum()),
        "proxy_surface_dist_median_m": float(np.median(task["proxy_surface_dist_m"])),
        "patch_coherence_median": float(np.median(task["patch_coherence"])),
        "normal_spread_p90_deg": float(np.percentile(task["normal_spread_deg"], 90)),
        "target_equals_c_bar_in_contact_m": on_surface,
        "d_max_m": float(task["d"].max()),
        "target_step_max_m": float(step.max()) if step.size else 0.0,
        "palm_offset_m": task["palm_offset_m"],
        "target_on_face_m": task.get("target_on_face_m", 0.0),
        "height_shift_m": task.get("height", {}).get("height_shift_m", 0.0),
        "robot_contact_z_m": task.get("height", {}).get("robot_contact_z_m", float("nan")),
        "in_band": task.get("height", {}).get("in_band", True),
        "contact_moved": task.get("height", {}).get("contact_moved", ""),
        "palm_face_deg": task.get("palm_face_deg", float("nan")),
        "palm_used": task.get("palm_used", False),
        "palm_flipped": task.get("palm_flipped", False),
        "forearm_face_deg": task.get("forearm_face_deg", float("nan")),
        "forearm_used": task.get("forearm_used", False),
    }


def save_task(task: dict, path) -> None:
    arrays = {k: np.asarray(v) for k, v in task.items() if isinstance(v, np.ndarray)}
    meta = {k: v for k, v in task.items() if not isinstance(v, np.ndarray)}
    np.savez_compressed(path, meta=np.array(json.dumps(meta)), **arrays)


def load_task(path) -> dict:
    z = np.load(path)
    out = json.loads(str(z["meta"]))
    out.update({k: z[k] for k in z.files if k != "meta"})
    return out
