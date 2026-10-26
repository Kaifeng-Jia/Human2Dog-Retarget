"""Candidate segments for the first reachability diagnostic (spec learned v0.5 §7.1 step 1; shared input of both
lines, spec §0.1 "实验输入"): right hand, the object pushed along the floor through one face, near-normal approach
and retreat, small change of object orientation. The script only proposes; three are confirmed by hand.

Criteria are applied in order to every segment from ``describe_clip``; the first group needs only the segment
row, the second the push descriptors (``push_descriptors``, computed only for segments that pass the first group).
Every segment that fails is kept with all failed criteria, as the spec asks for the exclusion reasons.

Ranking of the passing segments: tier first, then a vertical contact face, then duration x displacement.

* tier A: approach and retreat both observed (``path_m`` of palm path in the object frame) and within
  ``NEAR_NORMAL_DEG`` of the normal;
* tier B: what is observed is within ``NEAR_NORMAL_DEG``, but approach or retreat is not observable (OMOMO_new
  clips usually start in contact);
* tier C: approach or retreat observed at more than ``NEAR_NORMAL_DEG`` (sliding in or out sideways: spec §5.2
  "当前路径模板未覆盖"; kept, ranked last).

At most ``per_object`` candidates per (dataset, object) and one per clip.
"""

from __future__ import annotations

import math
import operator

# (name, key, op, value, meaning). Values are development initial values for the selection, not evaluation
# thresholds (the evaluation's tool-axis threshold is 15 deg, spec §5.2 / §7.1).
SEGMENT_CRITERIA = [
    ("slid", "object_state", "==", "slid", "object slides on the floor (moves >= 0.10 m, not lifted or tilted)"),
    ("on_floor", "obj_lifted_frac", "<=", 0.10, "object lowest point > 5 cm in at most 10 % of the frames"),
    ("right_hand", "hands", "==", "right", "right hand only in >= 60 % of the contact frames"),
    ("long_enough", "duration_s", ">=", 1.0, "contact lasts at least 1 s"),
    ("small_tilt", "obj_tilt_max_deg", "<", 10.0, "object tilts less than 10 deg"),
    ("small_yaw", "obj_yaw_maxabs_deg", "<", 20.0, "object turns less than 20 deg about z"),
    ("hand_only", "frac_body", "<", 0.05, "other body parts touch in < 5 % of the frames"),
]
PUSH_CRITERIA = [
    ("on_surface", "contact_surface_dist_median_m", "<=", 0.08, "hand contact proxy within 8 cm of the surface"),
    ("push", "push_alignment", ">=", 0.7, "object moves away from the hand (cos >= 0.7; pull is negative)"),
    ("one_face", "normal_spread_p90_deg", "<=", 20.0, "contact stays on one face (normal spread p90 <= 20 deg)"),
    ("flat_patch", "patch_coherence_median", ">=", 0.8, "contact patch is flat (no edge / corner)"),
]
NEAR_NORMAL_DEG = 30.0
VERTICAL_FACE_DEG = 30.0
_OPS = {"==": operator.eq, "<=": operator.le, ">=": operator.ge, "<": operator.lt, ">": operator.gt}


def _ok(v, op: str, ref) -> bool:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return False
    return bool(_OPS[op](v, ref))


def failed(row: dict, criteria=SEGMENT_CRITERIA) -> list[str]:
    """Names of the criteria the row fails (a missing or NaN value fails)."""
    return [name for name, key, op, ref, _ in criteria if not _ok(row.get(key), op, ref)]


def tier(row: dict, near: float = NEAR_NORMAL_DEG) -> str:
    angs = [row.get("approach_angle_deg"), row.get("retreat_angle_deg")]
    seen = [a for a in angs if a is not None and not math.isnan(a)]
    if any(a > near for a in seen):
        return "C"
    return "A" if len(seen) == 2 else "B"


def rank_key(row: dict) -> tuple:
    vertical = _ok(row.get("normal_tilt_median_deg"), "<=", VERTICAL_FACE_DEG)
    return (row["tier"], not vertical, -row["duration_s"] * row["obj_disp_xy_m"], row["dataset"], row["name"])


def select(rows: list[dict], top: int = 12, per_object: int = 2) -> list[dict]:
    """Rank the passing rows and take the best, at most ``per_object`` per (dataset, object) and one per clip."""
    ok = sorted((dict(r, tier=tier(r)) for r in rows if r.get("passed")), key=rank_key)
    out, n_obj, clips = [], {}, set()
    for r in ok:
        k = (r["dataset"], r["object"])
        if n_obj.get(k, 0) >= per_object or (r["dataset"], r["name"]) in clips:
            continue
        n_obj[k] = n_obj.get(k, 0) + 1
        clips.add((r["dataset"], r["name"]))
        out.append(dict(r, rank=len(out) + 1))
        if len(out) >= top:
            break
    return out


def funnel(rows: list[dict]) -> list[tuple[str, int]]:
    """Segments left after each criterion in order (all criteria, both groups)."""
    left, out = list(rows), [("all segments", len(rows))]
    for name, key, op, ref, _ in SEGMENT_CRITERIA + PUSH_CRITERIA:
        left = [r for r in left if _ok(r.get(key), op, ref)]
        out.append((name, len(left)))
    return out


def criteria_table() -> list[dict]:
    return [{"name": n, "key": k, "op": op, "value": v, "meaning": m}
            for n, k, op, v, m in SEGMENT_CRITERIA + PUSH_CRITERIA]
