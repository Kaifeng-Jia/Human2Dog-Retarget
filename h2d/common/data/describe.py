"""Descriptive interaction segments of OMOMO_new clips (what happens, no selection).

A *segment* is a maximal run of hand contact (either hand, wrist/palm or finger bodies) after removing
flicker: per-hand runs shorter than ``min_run_s`` are dropped, gaps shorter than ``max_gap_s`` between
runs are filled, and segments shorter than ``min_seg_s`` are dropped.

Each segment gets raw descriptors (hands, palm vs fingers, other body parts, object clearance above
the floor, horizontal object motion, tilt and yaw of the object relative to the segment start, human
root motion, heading change, crouch depth, contact height, two-hand geometry) and two coarse labels
whose thresholds live in ``DEFAULTS`` and are written into every report:

* ``object_state`` (first match): ``lifted`` (lowest point above ``lift_m`` for at least ``lift_frac`` of
  the segment), ``tilted`` (max tilt >= ``tilt_deg``), ``slid`` (horizontal displacement >=
  ``slide_m``), ``turned`` (|yaw change| >= ``yaw_deg``), else ``still``;
* ``human`` : ``walk`` if the root moves >= ``walk_m`` horizontally, else ``stand``.

The labels only summarize; the raw numbers are kept so any later choice can be made on them.
The floor is z = 0 (checked per clip through ``obj_lowest_z_start_m`` and ``toe_z_min_m``).
"""

from __future__ import annotations

import numpy as np
from scipy.spatial.transform import Rotation as R

from h2d.common.data.omomo_new import (
    BODY_GROUPS, BODY_INDEX, HAND_BODIES, MODES, NON_HAND_BODIES, Clip, contact_modes, intervals, no_data,
    remove_short_runs,
)
from h2d.common.data.omomo_objects import ObjectMesh, tilt_and_yaw

DEFAULTS = {
    "min_run_s": 0.2, "max_gap_s": 0.3, "min_seg_s": 0.3,
    "lift_m": 0.05, "lift_frac": 0.3, "tilt_deg": 15.0, "slide_m": 0.10, "yaw_deg": 20.0, "walk_m": 0.5,
}
OBJECT_STATES = ("lifted", "tilted", "slid", "turned", "still")
HAND_LABELS = ("left", "right", "both", "mixed")
WRIST = {"L": BODY_INDEX["L_Wrist"], "R": BODY_INDEX["R_Wrist"]}


# ------------------------------------------------------------------------------ segmentation
def close_gaps(mask: np.ndarray, max_gap: int) -> np.ndarray:
    """Fill False runs shorter than ``max_gap`` that lie between two True runs."""
    out = np.asarray(mask, bool).copy()
    runs = intervals(out)
    for (_, e0), (s1, _) in zip(runs[:-1], runs[1:]):
        if s1 - e0 < max_gap:
            out[e0:s1] = True
    return out


def hand_masks(clip: Clip, p: dict = DEFAULTS) -> tuple[np.ndarray, np.ndarray]:
    k = max(1, int(round(p["min_run_s"] * clip.fps)))
    c = clip.contact_body == 1
    return (remove_short_runs(c[:, HAND_BODIES["L"]].any(1), k),
            remove_short_runs(c[:, HAND_BODIES["R"]].any(1), k))


def segments(clip: Clip, p: dict = DEFAULTS) -> list[tuple[int, int]]:
    L, Rr = hand_masks(clip, p)
    m = close_gaps(L | Rr, max(1, int(round(p["max_gap_s"] * clip.fps))))
    kmin = max(1, int(round(p["min_seg_s"] * clip.fps)))
    return [(s, e) for s, e in intervals(m) if e - s >= kmin]


# ------------------------------------------------------------------------------ helpers
def heading(clip: Clip) -> np.ndarray:
    """Unwrapped facing angle [deg] from the hip axis (convention-free), (T,)."""
    v = clip.body_pos[:, BODY_INDEX["L_Hip"], :2] - clip.body_pos[:, BODY_INDEX["R_Hip"], :2]
    fwd = np.stack([v[:, 1], -v[:, 0]], 1)            # forward = left x up (hip axis rotated -90 deg)
    return np.degrees(np.unwrap(np.arctan2(fwd[:, 1], fwd[:, 0])))


def _path(xy: np.ndarray) -> float:
    return float(np.linalg.norm(np.diff(xy, axis=0), axis=1).sum()) if len(xy) > 1 else 0.0


def object_state(d: dict, p: dict = DEFAULTS) -> str:
    if d["obj_lifted_frac"] >= p["lift_frac"]:
        return "lifted"
    if d["obj_tilt_max_deg"] >= p["tilt_deg"]:
        return "tilted"
    if d["obj_disp_xy_m"] >= p["slide_m"]:
        return "slid"
    if abs(d["obj_yaw_end_deg"]) >= p["yaw_deg"]:
        return "turned"
    return "still"


def _hand_label(left_only: float, right_only: float, both: float) -> str:
    tot = left_only + right_only + both
    if tot <= 0:
        return "mixed"
    shares = {"left": left_only / tot, "right": right_only / tot, "both": both / tot}
    lab = max(shares, key=shares.get)
    return lab if shares[lab] >= 0.6 else "mixed"


# ------------------------------------------------------------------------------ per clip
def describe_clip(clip: Clip, obj: ObjectMesh, p: dict = DEFAULTS, mesh_check_frames: int = 10) -> dict:
    """Return {"clip": row, "segments": [rows], "check": distances} for one clip."""
    T, fps = clip.n, clip.fps
    flags = clip.contact_body == 1
    L, Rr = hand_masks(clip, p)
    segs = segments(clip, p)
    low = obj.lowest_z(clip.obj_pos, clip.obj_rot_xyzw)                     # (T,) floor clearance
    centroid_local = 0.5 * (obj.verts.min(0) + obj.verts.max(0))
    centroid = R.from_quat(clip.obj_rot_xyzw).apply(centroid_local) + clip.obj_pos
    pelvis = clip.body_pos[:, BODY_INDEX["Pelvis"]]
    stand_z = float(np.percentile(pelvis[:, 2], 90))
    head = heading(clip)
    hand_c = {s: clip.body_pos[:, HAND_BODIES[s]].mean(1) for s in "LR"}
    tilt0, yaw0 = tilt_and_yaw(clip.obj_rot_xyzw, 0)

    seg_rows = []
    for i, (s, e) in enumerate(segs):
        sl = slice(s, e)
        any_hand = L[sl] | Rr[sl]
        n_hand = max(1, int(any_hand.sum()))
        lo, ro, bo = (float((L[sl] & ~Rr[sl]).sum()) / n_hand, float((Rr[sl] & ~L[sl]).sum()) / n_hand,
                      float((L[sl] & Rr[sl]).sum()) / n_hand)
        palm = (flags[sl][:, [WRIST["L"], WRIST["R"]]].any(1) & any_hand).sum() / n_hand
        fing_idx = [j for s_ in "LR" for j in HAND_BODIES[s_][1:]]
        fing = (flags[sl][:, fing_idx].any(1) & any_hand).sum() / n_hand
        tilt, yaw = tilt_and_yaw(clip.obj_rot_xyzw[sl], 0)
        op = clip.obj_pos[sl]
        hand_flags = flags[sl][:, HAND_BODIES["L"] + HAND_BODIES["R"]]
        hz = clip.body_pos[sl][:, HAND_BODIES["L"] + HAND_BODIES["R"], 2][hand_flags]
        rel = (clip.body_pos[sl][:, HAND_BODIES["L"] + HAND_BODIES["R"], 2] - pelvis[sl, 2:3])[hand_flags]
        both = L[sl] & Rr[sl]
        if both.sum() >= 3:
            a = (hand_c["L"][sl] - centroid[sl])[both, :2]
            b = (hand_c["R"][sl] - centroid[sl])[both, :2]
            cosang = np.sum(a * b, 1) / np.maximum(np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1), 1e-9)
            two_angle = float(np.median(np.degrees(np.arccos(np.clip(cosang, -1, 1)))))
            two_sep = float(np.median(np.linalg.norm(hand_c["L"][sl][both] - hand_c["R"][sl][both], axis=1)))
        else:
            two_angle = two_sep = float("nan")
        root_disp = float(np.linalg.norm(pelvis[e - 1, :2] - pelvis[s, :2]))
        d = {
            "name": clip.name, "object": clip.obj, "subject": clip.subject, "seg": i,
            "start": s, "end": e, "start_s": s / fps, "duration_s": (e - s) / fps,
            "frac_left_only": lo, "frac_right_only": ro, "frac_both": bo,
            "frac_palm": float(palm), "frac_fingers": float(fing),
            "frac_body": float(flags[sl][:, NON_HAND_BODIES].any(1).mean()),
            **{f"frac_{g}": float(flags[sl][:, idx].any(1).mean()) for g, idx in BODY_GROUPS.items()
               if g not in ("L_hand", "R_hand")},
            "obj_clear_start_m": float(low[s]), "obj_clear_median_m": float(np.median(low[sl])),
            "obj_clear_max_m": float(low[sl].max()), "obj_lifted_frac": float((low[sl] > p["lift_m"]).mean()),
            "obj_dz_origin_m": float(op[:, 2].max() - op[:, 2].min()),
            "obj_disp_xy_m": float(np.linalg.norm(op[-1, :2] - op[0, :2])), "obj_path_xy_m": _path(op[:, :2]),
            "obj_tilt_max_deg": float(tilt.max()), "obj_yaw_end_deg": float(yaw[-1]),
            "obj_yaw_maxabs_deg": float(np.abs(yaw).max()),
            "root_disp_xy_m": root_disp, "root_path_xy_m": _path(pelvis[sl, :2]),
            "heading_change_deg": float(head[e - 1] - head[s]),
            "crouch_m": float(stand_z - pelvis[sl, 2].min()),
            "contact_z_median_m": float(np.median(hz)) if hz.size else float("nan"),
            "contact_z_min_m": float(hz.min()) if hz.size else float("nan"),
            "contact_z_rel_pelvis_median_m": float(np.median(rel)) if rel.size else float("nan"),
            "two_hand_angle_deg": two_angle, "two_hand_sep_m": two_sep,
            "obj_vs_root_disp": float(np.linalg.norm(op[-1, :2] - op[0, :2]) / root_disp) if root_disp > 0.1
            else float("nan"),
        }
        d["hands"] = _hand_label(lo, ro, bo)
        d["object_state"] = object_state(d, p)
        d["human"] = "walk" if root_disp >= p["walk_m"] else "stand"
        seg_rows.append(d)

    # ---- mesh / contact-label check: distance of flagged hand bodies to the transformed object surface
    check = {"contact_hand_min_m": [], "free_hand_min_m": [], "contact_body_min_m": []}
    cand = np.flatnonzero(L | Rr)
    if len(cand):
        pick = cand[np.unique(np.linspace(0, len(cand) - 1, min(mesh_check_frames, len(cand))).astype(int))]
        for t in pick:
            loc = obj.to_local(clip.body_pos[t][None], clip.obj_pos[t], clip.obj_rot_xyzw[t])[0]
            for side, m in (("L", L), ("R", Rr)):
                idx = np.asarray(HAND_BODIES[side])
                on = flags[t, idx]
                if m[t] and on.any():
                    check["contact_hand_min_m"].append(obj.min_surface_distance(loc[idx[on]]))
                elif not m[t]:
                    check["free_hand_min_m"].append(obj.min_surface_distance(loc[idx]))
            nb = np.asarray(NON_HAND_BODIES)[flags[t, NON_HAND_BODIES]]
            if len(nb):
                check["contact_body_min_m"].append(obj.min_surface_distance(loc[nb]))

    mode = contact_modes(clip, p["min_run_s"])
    any_flag = flags.any(1)
    toe = clip.body_pos[:, [BODY_INDEX["L_Toe"], BODY_INDEX["R_Toe"]], 2]
    longest = max(seg_rows, key=lambda r: r["duration_s"]) if seg_rows else None
    seg_frames = sum(e - s for s, e in segs)
    row = {
        "name": clip.name, "object": clip.obj, "subject": clip.subject, "frames": T, "duration_s": T / fps,
        "dropped_first_frame": clip.dropped_first_frame,
        **{f"mode_{m}": float(np.mean(mode == m)) for m in MODES},
        "n_segments": len(segs), "contact_coverage": seg_frames / T,
        "first_contact_s": segs[0][0] / fps if segs else float("nan"),
        "last_release_s": segs[-1][1] / fps if segs else float("nan"),
        **{f"n_{st}": sum(r["object_state"] == st for r in seg_rows) for st in OBJECT_STATES},
        "longest_hands": longest["hands"] if longest else "",
        "longest_state": longest["object_state"] if longest else "",
        "longest_human": longest["human"] if longest else "",
        "longest_duration_s": longest["duration_s"] if longest else 0.0,
        "obj_disp_xy_m": float(np.linalg.norm(clip.obj_pos[-1, :2] - clip.obj_pos[0, :2])),
        "obj_path_xy_m": _path(clip.obj_pos[:, :2]), "obj_clear_max_m": float(low.max()),
        "obj_tilt_max_deg": float(tilt0.max()), "obj_yaw_end_deg": float(yaw0[-1]),
        "root_path_xy_m": _path(pelvis[:, :2]),
        "root_disp_xy_m": float(np.linalg.norm(pelvis[-1, :2] - pelvis[0, :2])),
        "heading_change_deg": float(head[-1] - head[0]), "pelvis_stand_z_m": stand_z,
        **{f"clipfrac_{g}": float(flags[:, idx].any(1).mean()) for g, idx in BODY_GROUPS.items()},
        "frac_no_data": float(no_data(clip).mean()),
        "frac_contact_obj": float((clip.contact_obj == 1).mean()), "frac_any_body_flag": float(any_flag.mean()),
        "contact_obj_agreement": float(np.mean((clip.contact_obj == 1) == any_flag)),
        "obj_lowest_z_start_m": float(low[0]), "obj_lowest_z_min_m": float(low.min()),
        "toe_z_min_m": float(toe.min()),
        "check_contact_hand_median_m": float(np.median(check["contact_hand_min_m"])) if check["contact_hand_min_m"]
        else float("nan"),
        "check_free_hand_median_m": float(np.median(check["free_hand_min_m"])) if check["free_hand_min_m"]
        else float("nan"),
    }
    return {"clip": row, "segments": seg_rows, "check": check}


# ------------------------------------------------------------------------------ push descriptors
PALM = ("Wrist", "Index1", "Middle1", "Pinky1", "Ring1")
# Virtual hand (spec v0.6 §5.1): "L" / "R" = that hand; "B" = both hands on the same face, midpoint of the two.
MODE_OF_HANDS = {"left": "L", "right": "R", "both": "B"}


def palm_point(clip: Clip, side: str, frames) -> np.ndarray:
    """Palm centre (n, 3): mean of the wrist and the four finger base bodies; for "B" the midpoint of both palms."""
    if side == "B":
        return 0.5 * (palm_point(clip, "L", frames) + palm_point(clip, "R", frames))
    return clip.body_pos[frames][:, [BODY_INDEX[f"{side}_{n}"] for n in PALM]].mean(1)


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def hand_frame(clip: Clip, side: str, frames) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Palm normal (out of the palm), across the knuckles (index - pinky for the right hand, mirrored for the left so
    that both hands map alike) and forearm direction (elbow -> wrist), (n, 3) each, world frame; "B": both hands
    averaged. OMOMO_new keeps one hand shape per clip, but where the hand and the forearm are and which way they face
    are captured per frame (spec v0.8 §5.4)."""
    if side == "B":
        return tuple(_unit(a + b) for a, b in zip(hand_frame(clip, "L", frames), hand_frame(clip, "R", frames)))
    e, w, i, k = (clip.body_pos[frames][:, BODY_INDEX[f"{side}_{b}"]] for b in ("Elbow", "Wrist", "Index1", "Pinky1"))
    sgn = 1.0 if side == "R" else -1.0
    return _unit(np.cross(i - w, k - w) * sgn), _unit((i - k) * sgn), _unit(w - e)


def _hand_proxy(clip: Clip, side: str, frames) -> tuple[np.ndarray, np.ndarray]:
    idx = HAND_BODIES[side]
    pos = clip.body_pos[frames][:, idx]
    fl = (clip.contact_body[frames][:, idx] == 1).astype(float)
    k = fl.sum(1, keepdims=True)
    return np.where(k > 0, (pos * fl[..., None]).sum(1) / np.maximum(k, 1), palm_point(clip, side, frames)), k[:, 0] > 0


def contact_point(clip: Clip, side: str, frames) -> np.ndarray:
    """Per-frame contact proxy (n, 3) of the virtual hand: for "L" / "R" the mean of that hand's flagged bodies,
    else its palm centre; for "B" the midpoint of the two hands' proxies where both touch, the touching hand's
    proxy where one does, the palm midpoint where none does."""
    if side != "B":
        return _hand_proxy(clip, side, frames)[0]
    (pl, fl), (pr, fr) = _hand_proxy(clip, "L", frames), _hand_proxy(clip, "R", frames)
    out = 0.5 * (pl + pr)
    out[fl & ~fr] = pl[fl & ~fr]
    out[fr & ~fl] = pr[fr & ~fl]
    return out


def alignment_series(clip: Clip, obj: ObjectMesh, frames: slice, side: str, min_speed: float = 0.05) -> np.ndarray:
    """Per frame: cos(object horizontal velocity, object centre - hand contact point), horizontal. +1 = the object
    moves away from the hand (push), -1 = towards it (pull); NaN where the object moves slower than ``min_speed``."""
    pos = clip.obj_pos[frames]
    n = len(pos)
    if n < 2:
        return np.full(n, np.nan)
    cp = contact_point(clip, side, frames)
    cen = R.from_quat(clip.obj_rot_xyzw[frames]).apply(obj.center) + pos
    v = np.gradient(pos[:, :2], axis=0) * clip.fps
    d = cen[:, :2] - cp[:, :2]
    sp = np.linalg.norm(v, axis=1)
    cos = np.sum(v * d, 1) / np.maximum(sp * np.linalg.norm(d, axis=1), 1e-9)
    return np.where(sp > min_speed, cos, np.nan)


def push_descriptors(clip: Clip, obj: ObjectMesh, seg: tuple[int, int], side: str, min_speed: float = 0.05,
                     path_m: float = 0.10, search_s: float = 2.0, patch_m: float = 0.03) -> dict:
    """How the virtual hand (``side`` "L", "R" or "B", see ``contact_point``) moves the object in a segment: push vs
    pull, which face, how the hand came in.

    * ``push_alignment``: mean of ``alignment_series`` over the segment frames where the object moves faster than
      ``min_speed`` (``moving_frac`` of the segment).
    * ``normal_*``: normal of the surface patch (radius ``patch_m``) under the contact proxy, pointing to the
      hand (``ObjectMesh.patch_normals``); ``normal_local`` = its segment mean in the object frame, spread of
      the per-frame normals around it (one face or several), tilt of the mean from the horizontal (0 = vertical
      face, 90 = top face); ``patch_coherence_median`` (1 = flat patch, low = edge / corner);
      ``hands_face_angle_deg``: for "B", median angle between the patch normals under the two hands while both
      touch (0 = same face, 180 = opposite faces, i.e. squeezing); 0 for one hand; ``face_z_min_m`` /
      ``face_z_max_m``: height range of the touched flat face in the world at first contact.
      ``contact_surface_dist_*``: distance of the contact proxy to the surface (body positions are joint
      centres, so a few cm is normal; tens of cm means the proxy is not on the object).
    * ``approach_*`` / ``retreat_*``: the last ``path_m`` of palm path before first contact and the first
      ``path_m`` after release, in the object frame (searched up to ``search_s``); angle to the inward
      (approach) or outward (retreat) normal: 0 = straight in / out along the normal, 90 = sliding in sideways.
      NaN when not observable (the clip starts or ends too close to the contact, or the palm moves less).
    """
    s, e = seg
    sl = slice(s, e)
    fps = clip.fps
    cosv = alignment_series(clip, obj, sl, side, min_speed)
    mov = ~np.isnan(cosv)
    cp = contact_point(clip, side, sl)
    loc = obj.to_local(cp[:, None], clip.obj_pos[sl], clip.obj_rot_xyzw[sl])[:, 0]
    _, dist, n_loc, coh = obj.patch_normals(loc, patch_m)
    n_mean = n_loc.mean(0)
    n_mean /= max(np.linalg.norm(n_mean), 1e-9)
    spread = np.degrees(np.arccos(np.clip(n_loc @ n_mean, -1, 1)))
    faces_deg = 0.0                                    # one hand: one face by definition
    if side == "B":                                    # angle between the faces under the two hands, both touching
        (pl, fl), (pr, fr) = _hand_proxy(clip, "L", sl), _hand_proxy(clip, "R", sl)
        both = np.flatnonzero(fl & fr)
        if both.size:
            nl = obj.patch_normals(obj.to_local(pl[both, None], clip.obj_pos[sl][both], clip.obj_rot_xyzw[sl][both])[:, 0],
                                   patch_m)[2]
            nr = obj.patch_normals(obj.to_local(pr[both, None], clip.obj_pos[sl][both], clip.obj_rot_xyzw[sl][both])[:, 0],
                                   patch_m)[2]
            faces_deg = float(np.median(np.degrees(np.arccos(np.clip(np.sum(nl * nr, 1), -1, 1)))))
        else:
            faces_deg = float("nan")
    n_world = R.from_quat(clip.obj_rot_xyzw[sl]).apply(n_mean)
    tilt = np.degrees(np.arcsin(np.clip(np.abs(n_world[:, 2]), 0, 1)))
    out = {
        "push_alignment": float(np.mean(cosv[mov])) if mov.any() else float("nan"), "moving_frac": float(mov.mean()),
        "normal_spread_median_deg": float(np.median(spread)), "normal_spread_p90_deg": float(np.percentile(spread, 90)),
        "normal_tilt_median_deg": float(np.median(tilt)), "normal_local": n_mean.tolist(),
        "patch_coherence_median": float(np.median(coh)), "hands_face_angle_deg": faces_deg,
        "contact_surface_dist_median_m": float(np.median(dist)), "contact_surface_dist_max_m": float(dist.max()),
        "approach_available_s": s / fps, "retreat_available_s": (clip.n - e) / fps,
    }
    # extent of the touched face in the world at first contact (height adaptation, spec v0.7 §5.1)
    fp = obj.face_points(np.median(loc, 0), n_mean)
    fz = obj.world_points(clip.obj_pos[s], clip.obj_rot_xyzw[s], fp)[:, 2] if len(fp) else np.zeros(0)
    out["face_z_min_m"] = float(fz.min()) if fz.size else float("nan")
    out["face_z_max_m"] = float(fz.max()) if fz.size else float("nan")
    k = int(round(search_s * fps))
    for name, fr, ref, nrm in (("approach", np.arange(s - 1, max(-1, s - 1 - k), -1), s, -n_mean),
                               ("retreat", np.arange(e, min(clip.n, e + k)), e - 1, n_mean)):
        ang, dt = float("nan"), float("nan")
        if len(fr):
            pl = obj.to_local(palm_point(clip, side, np.r_[ref, fr])[:, None], clip.obj_pos[np.r_[ref, fr]],
                              clip.obj_rot_xyzw[np.r_[ref, fr]])[:, 0]
            far = np.flatnonzero(np.linalg.norm(pl[1:] - pl[0], axis=1) >= path_m)
            if far.size:
                j = int(far[0]) + 1
                d = pl[j] - pl[0] if name == "retreat" else pl[0] - pl[j]
                ang = float(np.degrees(np.arccos(np.clip(d @ nrm / np.linalg.norm(d), -1, 1))))
                dt = j / fps
        out[f"{name}_angle_deg"], out[f"{name}_time_s"] = ang, dt
    return out



# ------------------------------------------------------------------------------ grip (push / press vs grasp)
THUMB = ("Thumb1", "Thumb2", "Thumb3")
FINGERS4 = tuple(f"{f}{k}" for f in ("Index", "Middle", "Ring", "Pinky") for k in (1, 2, 3))
TIPS = ("Index3", "Middle3", "Ring3", "Pinky3", "Thumb3")


def finger_motion_std_m(clip: Clip, side: str = "R") -> float:
    """Mean over the fingertips of the std of the tip position in the wrist frame (m). ~0 when the data carries a
    fixed hand shape (no finger capture), several mm to cm with real finger motion."""
    w = BODY_INDEX[f"{side}_Wrist"]
    Rw = R.from_quat(clip.body_rot_xyzw[:, w])
    out = []
    for tip in TIPS:
        rel = clip.body_pos[:, BODY_INDEX[f"{side}_{tip}"]] - clip.body_pos[:, w]
        out.append(np.linalg.norm(Rw.inv().apply(rel).std(0)))
    return float(np.mean(out))


def grip_descriptors(clip: Clip, obj: ObjectMesh, seg: tuple[int, int], side: str, patch_m: float = 0.03) -> dict:
    """Does the hand wrap the object (grasp) or lie on it (press)? Per contact frame of each hand of the mode, the
    thumb and the other fingers both flagged, on surface patches whose normals point apart by more than 90 deg
    (thumb and fingers on opposite sides of a handle or an edge) = grasp. ``grasp_frac``: share of the segment's
    frames where some hand of the mode grasps; ``grip`` = "grasp" when >= 0.5, else "press"."""
    s, e = seg
    sides = ("L", "R") if side == "B" else (side,)
    fl = clip.contact_body[s:e] == 1
    grasp = np.zeros(e - s, bool)
    for sd in sides:
        th = [BODY_INDEX[f"{sd}_{b}"] for b in THUMB]
        fi = [BODY_INDEX[f"{sd}_{b}"] for b in FINGERS4]
        both = fl[:, th].any(1) & fl[:, fi].any(1)
        for i in np.flatnonzero(both):
            t = s + i
            pt = clip.body_pos[t, th][fl[i, th]].mean(0)
            pf = clip.body_pos[t, fi][fl[i, fi]].mean(0)
            loc = obj.to_local(np.stack([pt, pf])[None], clip.obj_pos[t], clip.obj_rot_xyzw[t])[0]
            n = obj.patch_normals(loc, patch_m)[2]
            grasp[i] |= bool(n[0] @ n[1] < 0.0)
    frac = float(grasp.mean()) if e > s else 0.0
    return {"grasp_frac": frac, "grip": "grasp" if frac >= 0.5 else "press"}
