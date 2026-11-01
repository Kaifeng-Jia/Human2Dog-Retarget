"""Human-side gait signals from the input clip (fullopt spec §6.1).

Foot contacts, touchdown events, stand / shuffle / walk segments and the leg length, from the semantic joints of a
``HOIClip`` (h2d/fullopt/hoi.py), whatever dataset it came from. Thresholds come from ``configs/fullopt/gait.yaml``
(``human``), in physical units.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import uniform_filter1d

from h2d.common.data.describe import close_gaps
from h2d.common.data.omomo_new import intervals, remove_short_runs
from h2d.fullopt.hoi import HOIClip

FEET = {"L": ("l_ankle", "l_toe"), "R": ("r_ankle", "r_toe")}


def smooth(x: np.ndarray, fps: float, sec: float) -> np.ndarray:
    """Centred moving average over ``sec`` along time."""
    return uniform_filter1d(np.asarray(x, float), max(1, int(round(sec * fps))), axis=0, mode="nearest")


def speed_xy(p: np.ndarray, fps: float) -> np.ndarray:
    return np.linalg.norm(np.gradient(p[:, :2], axis=0), axis=1) * fps


def foot_contacts(c: HOIClip, cfg: dict) -> np.ndarray:
    """(T, 2) bool, left / right: ankle or toe low (relative to its own floor percentile) and slow.

    Contact and lift runs shorter than ``min_run_s`` are merged into their neighbours (instead of a hysteresis).
    """
    k = max(1, int(round(cfg["min_run_s"] * c.fps)))
    out = []
    for side in ("L", "R"):
        on = np.zeros(c.n, bool)
        for name in FEET[side]:
            p = smooth(c.joint(name), c.fps, cfg["smooth_s"])
            low = p[:, 2] - np.percentile(p[:, 2], cfg["floor_percentile"]) <= cfg["height_m"]
            on |= low & (speed_xy(p, c.fps) <= cfg["speed_mps"])
        out.append(remove_short_runs(close_gaps(on, k), k))
    return np.stack(out, axis=1)


def touchdowns(contact: np.ndarray) -> list[tuple[int, str]]:
    """(frame, side) at the start of every contact run, time-ordered; a run starting at frame 0 is no touchdown."""
    ev = [(s, side) for j, side in enumerate("LR") for s, _ in intervals(contact[:, j]) if s > 0]
    return sorted(ev)


def segments(c: HOIClip, events: list[tuple[int, str]], cfg: dict) -> list[dict]:
    """Moving intervals (pelvis faster than ``move_speed_mps`` or a touchdown within ``event_window_s``), labelled by
    the touchdowns inside: walk (>= ``walk_min_steps``), shuffle (>= 1). Frames outside are standing."""
    v = speed_xy(smooth(c.joint("pelvis"), c.fps, cfg["speed_smooth_s"]), c.fps)
    moving = v > cfg["move_speed_mps"]
    w = int(round(cfg["event_window_s"] * c.fps))
    for f, _ in events:
        moving[max(0, f - w):min(c.n, f + w + 1)] = True
    out = []
    for s, e in intervals(moving):
        steps = [f for f, _ in events if s <= f < e]
        if not steps:
            continue
        a, b = (steps[0], steps[-1]) if len(steps) >= 2 else (s, e)     # speed between the first and last step
        seg = {"start": s, "end": e, "steps": len(steps), "speed_mps": float(v[a:b].mean()),
               "kind": "walk" if len(steps) >= cfg["walk_min_steps"] else "shuffle"}
        if len(steps) >= 2:
            seg["step_hz"] = (len(steps) - 1) / ((steps[-1] - steps[0]) / c.fps)
        out.append(seg)
    return out


def alternation(events: list[tuple[int, str]]) -> float:
    """Fraction of consecutive touchdowns made by different feet (1 for clean walking)."""
    sides = [s for _, s in events]
    return float(np.mean([a != b for a, b in zip(sides[:-1], sides[1:])])) if len(sides) > 1 else float("nan")


def leg_length(c: HOIClip, contact: np.ndarray, flat_pct: float = 5.0) -> float:
    """Hip-joint height of the straightened leg, averaged over both legs: thigh + shank (bone lengths, fixed per
    person) + the ankle's height above the floor with the foot flat. A lifted heel (squatting, pushing) only raises the
    ankle, so the flat-foot height is a low percentile of the ankle height over stance frames. Independent of
    posture."""
    out = []
    for j, s in enumerate("lr"):
        hip, knee, ankle = (c.joint(f"{s}_{n}") for n in ("hip", "knee", "ankle"))
        az = (ankle[contact[:, j], 2] if contact[:, j].any() else ankle[:, 2]) - c.floor_z
        out.append(np.median(np.linalg.norm(hip - knee, axis=1)) + np.median(np.linalg.norm(knee - ankle, axis=1))
                   + np.percentile(az, flat_pct))
    return float(np.mean(out))
