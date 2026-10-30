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

from h2d.common.data.describe import contact_point, palm_point
from h2d.common.data.omomo_new import Clip
from h2d.common.objectmesh import ObjectMesh

TASK_VERSION = 1


def _smooth(x: np.ndarray, k: int) -> np.ndarray:
    k = min(k, len(x))
    k -= 1 - k % 2                                     # odd window, centred
    if k <= 1:
        return x.copy()
    pad = k // 2
    xp = np.pad(x, ((pad, pad), (0, 0)), mode="edge")
    c = np.cumsum(np.vstack([np.zeros((1, x.shape[1])), xp]), axis=0)
    return (c[k:] - c[:-k]) / k


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


def build_task(clip: Clip, obj: ObjectMesh, seg: tuple[int, int], mode: str, pre_s: float = 1.0,
               post_s: float = 1.0, smooth: int = 5, patch_m: float = 0.03, band: dict | None = None) -> dict:
    """``band`` ({face: [z_lo, z_hi]}): adapt the contact height to the arm (``adapt_height``)."""
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
    if band:
        c_bar, height = adapt_height(obj, c_bar, n_bar, pos[contact][0], rot[contact][0], z_human, band)
    fp = obj.face_points(np.median(c_bar, 0), n_bar)
    on_face = float(cKDTree(fp).query(c_bar)[0].max()) if len(fp) else float("nan")

    palm = palm_point(clip, mode, fr)
    palm_loc = obj.to_local(palm[:, None], pos, rot)[:, 0]
    ref = np.where(fr[:, None] < s, c_bar[0], c_bar[-1])
    ref[contact] = c_bar
    d_raw = np.sum((palm_loc - ref) * n_bar, 1)
    offset = float(np.median(d_raw[contact]))
    d = np.clip(d_raw - offset, 0.0, None)
    d[contact] = 0.0
    target_local = ref + d[:, None] * n_bar
    target_world = np.stack([obj.world_points(pos[i], rot[i], target_local[i][None])[0] for i in range(len(fr))])
    c_bar_w = np.full((len(fr), 3), np.nan)
    c_bar_w[contact] = c_bar
    return {
        "task_version": TASK_VERSION, "clip": clip.name, "object": clip.obj, "mode": mode, "fps": float(fps),
        "segment": [s, e], "window": [int(w0), int(w1)],
        "frames": fr, "in_contact": contact, "obj_pos": pos, "obj_rot_xyzw": rot,
        "c_bar_local": c_bar_w, "n_bar_local": n_bar, "d": d, "palm_offset_m": offset,
        "target_local": target_local, "target_world": target_world, "palm_world": palm,
        "proxy_surface_dist_m": dist, "patch_coherence": coh,
        "normal_spread_deg": np.degrees(np.arccos(np.clip(n @ n_bar, -1, 1))),
        "c_bar_human_local": c_human, "height": height, "target_on_face_m": on_face,
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
