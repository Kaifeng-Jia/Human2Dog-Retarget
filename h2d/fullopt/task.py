"""Task targets from the input clip alone (fullopt spec v0.2 §2, §3 step 1).

The semantics are the learned line's (``h2d/common/data/tasks.py``, learned spec v0.8 §5.1-5.2, §5.4, §5.6), so both
lines solve the same task: contact target on the surface under the virtual hand, one face normal per segment, the
approach and retreat distance of the palm, the height adapted to the arm's band, a push on a top face moved to the
robot's side, the tool approach along the forearm within a 45 deg cone and the roll from the hand. The common
helpers are imported where they need no dataset ``Clip`` (``adapt_height``, ``from_behind``, ``clamp_cone``,
``gripper_axes``); what the common code reads from the dataset is re-derived from the semantic joints of a
``HOIClip``:

* palm: the wrist and the index and pinky knuckles, (w + 2 (i + p)) / 5. The learned line averages the wrist and four
  knuckles; the middle and ring knuckles lie between the index and the pinky, so their sum is i + p. Without finger
  joints the palm is ``PALM_FROM_WRIST_M`` beyond the wrist along the forearm and the hand has no roll;
* contact proxy of the virtual hand: the palm (the dataset's finger contact flags are not part of the input);
* contact frames: ``hand_contact`` when the clip has it, else the palm within ``CONTACT_M`` of the surface;
* segment, virtual-hand mode and push / pull: from ``meta`` when the exporter wrote them, else from the contacts;
* which face the hand pushes (a top face or not): the patch under the hand's joints that touch the surface (the
  learned line's flagged hand bodies), not under the palm centre, which a wrist lifted at a table's edge holds over
  the edge.

The task gate weights the task terms of the solver. It is this line's own (the learned gate, 1 within 0.25 s of
contact, left the arm too little time, R027): 0 until ``gate_rise_s`` before the first contact frame, 1 from
``gate_full_s`` before it (smoothstep), mirrored after the last. The targets cover the gate's span, the frames where
it is not 0; the task window (the learned line's, from ``meta``) stays what the evaluation and the relation metrics
use.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.spatial.transform import Rotation as R

from h2d.common.data.describe import DEFAULTS, MODE_OF_HANDS, _hand_label, close_gaps
from h2d.common.data.omomo_new import intervals, remove_short_runs
from h2d.common.data.tasks import adapt_height, clamp_cone, from_behind, gripper_axes
from h2d.common.objectmesh import ObjectMesh
from h2d.fullopt.hoi import HOIClip

PALM_FROM_WRIST_M = 0.07   # palm centre beyond the wrist without finger joints: 0.8 x an adult's 8-9 cm to the knuckles
# Palm centre to the surface for a touching hand without contact labels: skin contact within 2 cm (FORCE's derived
# labels use the same) plus about half a hand's thickness from the joint centres to the palm skin.
CONTACT_M = 0.04


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def _smooth(x: np.ndarray, k: int) -> np.ndarray:
    """Centred moving average over an odd window of at most ``k`` frames, edges held (as the learned line's)."""
    k = min(k, len(x))
    k -= 1 - k % 2
    return uniform_filter1d(np.asarray(x, float), k, axis=0, mode="nearest") if k > 1 else np.array(x, float)


# ------------------------------------------------------------------------------ the human hand from joints
def palm(c: HOIClip, side: str, frames=slice(None)) -> np.ndarray:
    """Palm centre (n, 3) of hand "L" / "R"; "B": the midpoint of both palms."""
    if side == "B":
        return 0.5 * (palm(c, "L", frames) + palm(c, "R", frames))
    s = side.lower()
    w = c.joint(f"{s}_wrist")[frames]
    if c.has(f"{s}_index") and c.has(f"{s}_pinky"):
        return 0.2 * w + 0.4 * (c.joint(f"{s}_index")[frames] + c.joint(f"{s}_pinky")[frames])
    return w + PALM_FROM_WRIST_M * _unit(w - c.joint(f"{s}_elbow")[frames])


def hand_frame(c: HOIClip, side: str, frames=slice(None)):
    """Palm normal, across the knuckles (index - pinky, mirrored for the left hand) and forearm (elbow -> wrist), world
    frame, (n, 3) each, as ``describe.hand_frame``; "B": both hands averaged. Palm normal and across are None
    without finger joints."""
    if side == "B":
        a, b = hand_frame(c, "L", frames), hand_frame(c, "R", frames)
        return tuple(None if x is None or y is None else _unit(x + y) for x, y in zip(a, b))
    s = side.lower()
    e, w = c.joint(f"{s}_elbow")[frames], c.joint(f"{s}_wrist")[frames]
    if not (c.has(f"{s}_index") and c.has(f"{s}_pinky")):
        return None, None, _unit(w - e)
    i, k = c.joint(f"{s}_index")[frames], c.joint(f"{s}_pinky")[frames]
    sgn = 1.0 if side == "R" else -1.0
    return _unit(np.cross(i - w, k - w) * sgn), _unit((i - k) * sgn), _unit(w - e)


def elbow(c: HOIClip, side: str, frames=slice(None)) -> np.ndarray:
    if side == "B":
        return 0.5 * (elbow(c, "L", frames) + elbow(c, "R", frames))
    return c.joint(f"{side.lower()}_elbow")[frames]


def hand_contacts(c: HOIClip, obj: ObjectMesh) -> np.ndarray:
    """(T, 2) left / right: the clip's labels, else the palm within ``CONTACT_M`` of the object's surface."""
    if c.hand_contact is not None:
        return np.asarray(c.hand_contact, bool)
    out = []
    for side in "LR":
        loc = obj.to_local(palm(c, side)[:, None], c.obj_pos, c.obj_quat)[:, 0]
        out.append(obj.approx_distance(loc, upper=0.5) <= CONTACT_M)
    return np.stack(out, 1)


def detect_segment(contact: np.ndarray, fps: float, p: dict = DEFAULTS) -> tuple[tuple[int, int], str]:
    """The longest hand-contact segment (the learned line's flicker rules, ``describe.segments``) and its virtual-hand
    mode: the hand(s) touching for >= 60 % of it, else the hand touching longer."""
    k = max(1, int(round(p["min_run_s"] * fps)))
    L, Rr = remove_short_runs(contact[:, 0], k), remove_short_runs(contact[:, 1], k)
    m = close_gaps(L | Rr, max(1, int(round(p["max_gap_s"] * fps))))
    segs = [(s, e) for s, e in intervals(m) if e - s >= max(1, int(round(p["min_seg_s"] * fps)))]
    if not segs:
        raise ValueError("no hand contact segment")
    s, e = max(segs, key=lambda se: se[1] - se[0])
    lab = _hand_label(*((x[s:e]).sum() for x in (L & ~Rr, Rr & ~L, L & Rr)))
    return (int(s), int(e)), MODE_OF_HANDS.get(lab, "L" if L[s:e].sum() > Rr[s:e].sum() else "R")


def touching(c: HOIClip, side: str, frames, obj: ObjectMesh) -> np.ndarray:
    """Mean of the hand's joints (wrist, index and pinky bases) within ``CONTACT_M`` of the surface, else the nearest
    one, (n, 3): the learned line's "flagged hand bodies" with the joints the input has."""
    s = side.lower()
    names = [f"{s}_wrist"] + [f"{s}_{k}" for k in ("index", "pinky") if c.has(f"{s}_{k}")]
    P = np.stack([c.joint(n)[frames] for n in names], 1)
    loc = obj.to_local(P, c.obj_pos[frames], c.obj_quat[frames])
    d = obj.surface_distance(loc.reshape(-1, 3)).reshape(len(P), -1)
    flag = d <= CONTACT_M
    flag[np.arange(len(P)), d.argmin(1)] = True
    return (P * flag[..., None]).sum(1) / flag.sum(1, keepdims=True)


def contact_proxy(c: HOIClip, mode: str, frames, contact: np.ndarray, point=None) -> np.ndarray:
    """The virtual hand's contact proxy: ``point(c, side, frames)`` (default the palm) of that hand; "B": both hands'
    midpoint where both touch, the touching hand's where one does (``describe.contact_point``)."""
    point = point or palm
    if mode != "B":
        return point(c, mode, frames)
    pl, pr = point(c, "L", frames), point(c, "R", frames)
    fl, fr = contact[frames, 0], contact[frames, 1]
    out = 0.5 * (pl + pr)
    out[fl & ~fr], out[fr & ~fl] = pl[fl & ~fr], pr[fr & ~fl]
    return out


def is_push(c: HOIClip, obj: ObjectMesh, mode: str, seg, min_speed: float = 0.05) -> bool:
    """The object moves away from the hand (``describe.alignment_series``); a still object counts as a push."""
    fr = np.arange(*seg)
    v = np.gradient(c.obj_pos[fr, :2], axis=0) * c.fps
    d = (R.from_quat(c.obj_quat[fr]).apply(obj.center) + c.obj_pos[fr])[:, :2] - palm(c, mode, fr)[:, :2]
    sp = np.linalg.norm(v, axis=1)
    cos = np.sum(v * d, 1) / np.maximum(sp * np.linalg.norm(d, axis=1), 1e-9)
    return bool(not (sp > min_speed).any() or np.mean(cos[sp > min_speed]) >= 0.0)


# ------------------------------------------------------------------------------ the task
@dataclass
class Task:
    mode: str                     # virtual hand "L", "R" or "B"
    segment: tuple[int, int]      # contact frames [s, e) of the clip
    window: tuple[int, int]       # [w0, w1): the segment with the approach and the retreat (evaluation)
    span: tuple[int, int]         # [a0, a1): the frames with targets, the window and the gate's support
    gate: np.ndarray              # (T,) task weight
    target: np.ndarray            # (T, 3) world contact target (NaN outside the span)
    tool_x: np.ndarray            # (T, 3) world approach target (NaN outside the span)
    tool_z: np.ndarray            # (T, 3) world jaw axis target (NaN outside the span or without a roll target)
    local: dict = field(default_factory=dict)   # object-frame arrays over the span: target, tool_x, tool_z
    record: dict = field(default_factory=dict)

    @property
    def frames(self) -> np.ndarray:
        """The task window's frames."""
        return np.arange(*self.window)

    @property
    def contact(self) -> np.ndarray:
        """(T,) contact frames."""
        out = np.zeros(len(self.gate), bool)
        out[slice(*self.segment)] = True
        return out


def build(c: HOIClip, cfg: dict, band: dict | None = None) -> Task:
    """``cfg``: configs/fullopt/solver.yaml ``task``; ``band``: configs/candidate_selection.yaml ``reach_band``."""
    obj = ObjectMesh(str(c.meta.get("object", "object")), np.asarray(c.obj_verts, float), np.asarray(c.obj_faces))
    contact = hand_contacts(c, obj)
    if "segment" in c.meta and "mode" in c.meta:
        (s, e), mode, source = tuple(int(x) for x in c.meta["segment"]), c.meta["mode"], "meta"
    else:
        (s, e), mode = detect_segment(contact, c.fps)
        source = "detected"
    w0, w1 = (tuple(int(x) for x in c.meta["window"]) if "window" in c.meta and source == "meta" else
              (max(0, s - round(cfg["pre_s"] * c.fps)), min(c.n, e + round(cfg["post_s"] * c.fps))))
    interaction = c.meta.get("interaction") or ("push" if is_push(c, obj, mode, (s, e)) else "pull")
    rise, full = round(cfg["gate_rise_s"] * c.fps), round(cfg["gate_full_s"] * c.fps)
    a0, a1 = max(0, min(w0, s - rise)), min(c.n, max(w1, e + rise))
    fr = np.arange(a0, a1)
    con = (fr >= s) & (fr < e)
    pos, rot = c.obj_pos[fr], c.obj_quat[fr]
    k = int(cfg["smooth_frames"])

    loc = obj.to_local(contact_proxy(c, mode, fr[con], contact)[:, None], pos[con], rot[con])[:, 0]
    q, dist, n, coh = obj.patch_normals(loc, cfg["patch_m"])
    n_bar = _unit(n.mean(0))
    # The normal points to the human's side (the elbow's): a palm's joint centre can lie a few mm inside a thin top,
    # where the patch normal would point down (the dataset's touching bodies lie outside).
    elb = obj.to_local(elbow(c, mode, fr[con])[:, None], pos[con], rot[con])[:, 0]
    n_bar *= 1.0 if np.median((elb - q) @ n_bar) >= 0 else -1.0
    c_bar = obj.closest_face(_smooth(q, k))[1]
    z_human = float(np.median((R.from_quat(rot[con]).apply(c_bar) + pos[con])[:, 2]))
    height = {"face": "", "human_contact_z_m": z_human, "robot_contact_z_m": z_human, "height_shift_m": 0.0,
              "height_adapted": False, "in_band": True, "contact_moved": ""}
    n_robot = n_bar
    # Which face the hand pushes (top or not) from the joints that touch it: at a table's edge the palm centre, lifted
    # by the wrist, lies over the edge and its patch tilts half way (R027 c12: 51 deg against the learned line's 83).
    near = contact_proxy(c, mode, fr[con], contact, lambda c_, sd, f: touching(c_, sd, f, obj))
    n_face = obj.patch_normals(obj.to_local(near[:, None], pos[con], rot[con])[:, 0], cfg["patch_m"])[2].mean(0)
    top = abs(R.from_quat(rot[con][0]).apply(_unit(n_face))[2]) > np.sin(np.radians(60))
    if interaction == "push" and top:              # every task is a press (the closed gripper)
        c_bar, n_robot, rec = from_behind(obj, c_bar, pos[con], rot[con], band)
        height.update({k_: v for k_, v in rec.items() if k_ != "human_contact_z_m"},
                      height_shift_m=rec["robot_contact_z_m"] - z_human)
    elif band:
        c_bar, rec = adapt_height(obj, c_bar, n_bar, pos[con][0], rot[con][0], z_human, band)
        height.update(rec)

    to_obj = R.from_quat(rot).inv()
    palm_loc = to_obj.apply(palm(c, mode, fr) - pos)
    ref = np.where(fr[:, None] < s, c_bar[0], c_bar[-1])
    ref[con] = c_bar
    d_raw = np.sum((palm_loc - ref) * n_robot, 1)
    offset = float(np.median(d_raw[con]))
    d = np.clip(d_raw - offset, 0.0, None)
    d[con] = 0.0
    # The gripper closes in on the face and leaves it at most approach_mps fast: the palm's distance can drop by 10 cm
    # in the frame before a segment starts (a contact moved to the robot's side: the palm was on the top), which no
    # arm follows. Contact frames are unchanged.
    d = np.minimum(d, cfg["approach_mps"] * np.where(fr < s, s - fr, np.maximum(fr - e + 1, 0)) / c.fps)
    target_local = ref + d[:, None] * n_robot

    palm_n, across, fore = (None if v is None else _unit(_smooth(to_obj.apply(v), k)) for v in hand_frame(c, mode, fr))
    deg = lambda a, b: float(np.degrees(np.arccos(np.clip(np.median(a @ b), -1, 1))))  # noqa: E731
    fore_face = deg(fore[con], -n_robot)
    palm_face = deg(palm_n[con], -n_bar) if palm_n is not None else float("nan")
    palm_flipped = bool(palm_face > 90.0)          # the palm is the side that touches (as the learned line)
    if palm_flipped:
        palm_n, across, palm_face = -palm_n, -across, 180.0 - palm_face
    palm_used, fore_used = bool(palm_face <= cfg["palm_max_deg"]), bool(fore_face <= 90.0)
    tool_x = clamp_cone(fore, -n_robot, cfg["tool_max_deg"]) if fore_used else np.tile(-n_robot, (len(fr), 1))
    tool_z = gripper_axes(tool_x, across)[1] if palm_used else np.full((len(fr), 3), np.nan)

    Rw = R.from_quat(rot)

    def world(local: np.ndarray, offset=0.0) -> np.ndarray:            # span arrays -> (T, 3) world, NaN outside
        out = np.full((c.n, 3), np.nan)
        out[fr] = Rw.apply(local) + offset
        return out

    t = np.arange(c.n)
    x = np.clip(np.minimum(t - (s - rise), (e - 1 + rise) - t) / max(rise - full, 1), 0.0, 1.0)
    gate = x * x * (3.0 - 2.0 * x)
    return Task(mode=mode, segment=(s, e), window=(w0, w1), span=(a0, a1), gate=gate, target=world(target_local, pos),
                tool_x=world(tool_x), tool_z=world(tool_z),
                local={"target": target_local, "tool_x": tool_x, "tool_z": tool_z, "n_robot": n_robot},
                record={"source": source, "interaction": interaction, "contact_labels": c.hand_contact is not None,
                        "height": height, "palm_offset_m": offset,
                        "proxy_surface_dist_median_m": float(np.median(dist)),
                        "patch_coherence_median": float(np.median(coh)), "palm_face_deg": palm_face,
                        "palm_used": palm_used, "palm_flipped": palm_flipped, "forearm_face_deg": fore_face,
                        "forearm_used": fore_used})


def compare(task: Task, learned: dict) -> dict:
    """Agreement with a learned-line task file of the same segment (``h2d.common.data.tasks.load_task``): contact
    target (object frame) and tool axes on the contact frames both have."""
    fr = np.asarray(learned["frames"])
    lc = fr[np.asarray(learned["in_contact"], bool)]
    both = np.intersect1d(lc, np.arange(*task.segment))
    mine = both - task.span[0]
    theirs = np.searchsorted(fr, both)
    ang = lambda a, b: np.degrees(np.arccos(np.clip(np.sum(a * b, 1), -1, 1)))  # noqa: E731
    dp = np.linalg.norm(task.local["target"][mine] - learned["target_local"][theirs], axis=1)
    ax = ang(task.local["tool_x"][mine], learned["tool_x_local"][theirs])
    az = ang(task.local["tool_z"][mine], learned["tool_z_local"][theirs])
    az = az[np.isfinite(az)]
    stat = lambda x: [float(np.median(x)), float(x.max())] if x.size else [None, None]  # noqa: E731
    return {"frames": int(len(both)), "segment_same": [int(x) for x in learned["segment"]] == list(task.segment),
            "mode_same": learned["mode"] == task.mode,
            "contact_moved_same": learned["height"].get("contact_moved", "") == task.record["height"]["contact_moved"],
            "target_m": stat(dp), "tool_x_deg": stat(ax), "tool_z_deg": stat(az),
            "roll_target_same": bool(learned["palm_used"]) == task.record["palm_used"]}
