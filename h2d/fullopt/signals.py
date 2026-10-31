"""Human-side gait signals from a recorded skeleton (fullopt spec §6.1).

Foot contacts, touchdown events, stand / shuffle / walk segments and the leg length, from OMOMO_new ``body_pos``
(floor at z = 0). Thresholds come from ``configs/fullopt/gait.yaml`` (``human``).
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import uniform_filter1d

from h2d.common.data.describe import close_gaps
from h2d.common.data.omomo_new import BODY_INDEX, intervals, remove_short_runs

FEET = {"L": ("L_Ankle", "L_Toe"), "R": ("R_Ankle", "R_Toe")}
HIPS = ("L_Hip", "R_Hip")


def smooth(x: np.ndarray, fps: float, sec: float) -> np.ndarray:
    """Centred moving average over ``sec`` along time."""
    return uniform_filter1d(np.asarray(x, float), max(1, int(round(sec * fps))), axis=0, mode="nearest")


def speed_xy(p: np.ndarray, fps: float) -> np.ndarray:
    return np.linalg.norm(np.gradient(p[:, :2], axis=0), axis=1) * fps


def foot_contacts(body_pos: np.ndarray, fps: float, cfg: dict) -> np.ndarray:
    """(T, 2) bool, left / right: ankle or toe low (relative to its own floor percentile) and slow.

    Contact and lift runs shorter than ``min_run_s`` are merged into their neighbours (instead of a hysteresis).
    """
    k = max(1, int(round(cfg["min_run_s"] * fps)))
    out = []
    for side in ("L", "R"):
        on = np.zeros(len(body_pos), bool)
        for name in FEET[side]:
            p = smooth(body_pos[:, BODY_INDEX[name]], fps, cfg["smooth_s"])
            low = p[:, 2] - np.percentile(p[:, 2], cfg["floor_percentile"]) <= cfg["height_m"]
            on |= low & (speed_xy(p, fps) <= cfg["speed_mps"])
        out.append(remove_short_runs(close_gaps(on, k), k))
    return np.stack(out, axis=1)


def touchdowns(contact: np.ndarray) -> list[tuple[int, str]]:
    """(frame, side) at the start of every contact run, time-ordered; a run starting at frame 0 is no touchdown."""
    ev = [(s, side) for j, side in enumerate("LR") for s, _ in intervals(contact[:, j]) if s > 0]
    return sorted(ev)


def segments(body_pos: np.ndarray, fps: float, events: list[tuple[int, str]], cfg: dict) -> list[dict]:
    """Moving intervals (pelvis faster than ``move_speed_mps`` or a touchdown within ``event_window_s``), labelled by
    the touchdowns inside: walk (>= ``walk_min_steps``), shuffle (>= 1). Frames outside are standing."""
    T = len(body_pos)
    v = speed_xy(smooth(body_pos[:, BODY_INDEX["Pelvis"]], fps, cfg["speed_smooth_s"]), fps)
    moving = v > cfg["move_speed_mps"]
    w = int(round(cfg["event_window_s"] * fps))
    for f, _ in events:
        moving[max(0, f - w):min(T, f + w + 1)] = True
    out = []
    for s, e in intervals(moving):
        steps = [f for f, _ in events if s <= f < e]
        if not steps:
            continue
        a, b = (steps[0], steps[-1]) if len(steps) >= 2 else (s, e)     # speed between the first and last step
        seg = {"start": s, "end": e, "steps": len(steps), "speed_mps": float(v[a:b].mean()),
               "kind": "walk" if len(steps) >= cfg["walk_min_steps"] else "shuffle"}
        if len(steps) >= 2:
            seg["step_hz"] = (len(steps) - 1) / ((steps[-1] - steps[0]) / fps)
        out.append(seg)
    return out


def alternation(events: list[tuple[int, str]]) -> float:
    """Fraction of consecutive touchdowns made by different feet (1 for clean walking)."""
    sides = [s for _, s in events]
    return float(np.mean([a != b for a, b in zip(sides[:-1], sides[1:])])) if len(sides) > 1 else float("nan")


def leg_length(body_pos: np.ndarray, contact: np.ndarray, fps: float, still_mps: float = 0.1) -> float:
    """Hip-joint height above the floor, median over frames with both feet down and the pelvis still."""
    v = speed_xy(smooth(body_pos[:, BODY_INDEX["Pelvis"]], fps, 0.5), fps)
    sel = contact.all(1) & (v < still_mps)
    z = body_pos[:, [BODY_INDEX[h] for h in HIPS], 2].mean(1)
    return float(np.median(z[sel] if sel.any() else z))
