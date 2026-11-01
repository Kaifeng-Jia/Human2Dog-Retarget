"""Human gait signals on synthetic walking, and the dog's natural rhythm (fullopt spec §6.1-6.3)."""

import sys
from pathlib import Path

import numpy as np
import pytest

from h2d.common.data.omomo_new import BODY_INDEX
from h2d.fullopt import gait, signals
from h2d.paths import load_config

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from synthetic_hoi import standing_pose  # noqa: E402

FPS = 30.0
CFG = load_config("fullopt/gait.yaml")["human"]


def step(pose, side, td, xs, xe, swing_s=0.5):
    """Move one foot (ankle and toe) from x = xs to xe during the swing_s before touchdown td, 8 cm high."""
    t = np.arange(len(pose)) / FPS
    s = np.clip((t - (td - swing_s)) / swing_s, 0, 1)
    for j, dx in (("Ankle", 0.0), ("Toe", 0.12)):
        i = BODY_INDEX[f"{side}_{j}"]
        after = t >= td - swing_s
        pose[after, i, 0] = xs + (xe - xs) * s[after] + dx
        pose[:, i, 2] += 0.08 * np.sin(np.pi * s) * (s < 1)


def walking(T=300, v=0.8, t0=2.0, t1=8.0, step_s=0.625, lead=0.3):
    """Stand, walk along +x from t0 to t1 with alternating steps every step_s, stand. Returns body_pos, touchdowns."""
    t = np.arange(T) / FPS
    pose = np.repeat(standing_pose()[None], T, 0)
    pose[:, :, 0] += v * np.clip(t - t0, 0, t1 - t0)[:, None]
    for i in [BODY_INDEX[n] for n in signals.FEET["L"] + signals.FEET["R"]]:
        pose[:, i, 0] = standing_pose()[i, 0]
    tds = {"L": np.arange(t0 + 0.5, t1 + 0.2, 2 * step_s), "R": np.arange(t0 + 0.5 + step_s, t1 + 0.2, 2 * step_s)}
    for side, times in tds.items():
        xs = 0.0
        for td in times:
            xe = min(v * np.clip(td - t0, 0, t1 - t0) + lead, v * (t1 - t0))
            step(pose, side, td, xs, xe)
            xs = xe
    return pose, sorted([(int(round(td * FPS)), s) for s, ts in tds.items() for td in ts])


def test_steps_segments_and_leg_length_on_synthetic_walking():
    pose, truth = walking()
    con = signals.foot_contacts(pose, FPS, CFG)
    ev = signals.touchdowns(con)
    assert [s for _, s in ev] == [s for _, s in truth]
    assert np.abs(np.array([f for f, _ in ev]) - [f for f, _ in truth]).max() <= 2
    segs = signals.segments(pose, FPS, ev, CFG)
    assert [s["kind"] for s in segs] == ["walk"] and segs[0]["steps"] == len(truth)
    assert segs[0]["step_hz"] == pytest.approx(1.6, rel=0.05)
    assert signals.alternation(ev) == 1.0
    assert signals.leg_length(pose, con) == pytest.approx(0.85, abs=0.015)


def test_leg_length_does_not_drop_when_squatting():
    pose = np.repeat(standing_pose()[None], 90, 0)               # hips 0.30 m lower, knees forward, same bones
    for s in ("L", "R"):
        pose[:, BODY_INDEX[f"{s}_Hip"], 2] -= 0.30
        pose[:, BODY_INDEX[f"{s}_Knee"], [0, 2]] = (0.304, 0.340)
    con = signals.foot_contacts(pose, FPS, CFG)
    assert con.all() and signals.leg_length(pose, con) == pytest.approx(0.85, abs=0.02)


def test_one_step_is_a_shuffle():
    pose = np.repeat(standing_pose()[None], 180, 0)              # standing; the right foot steps 0.2 m forward
    step(pose, "R", 3.0, 0.0, 0.2)
    ev = signals.touchdowns(signals.foot_contacts(pose, FPS, CFG))
    segs = signals.segments(pose, FPS, ev, CFG)
    assert [s for _, s in ev] == ["R"] and [s["kind"] for s in segs] == ["shuffle"]


def test_dog_human_ratio_is_speed_independent():
    v = np.array([0.3, 0.6, 1.0, 1.4])
    r = gait.stride_hz(v, 0.54) / gait.stride_hz(v, 0.9)
    assert np.allclose(r, (0.9 / 0.54) ** 0.7)
    step_hz = 2 * gait.stride_hz(v, 0.9)                          # a human walking at the Alexander rhythm
    assert np.allclose(gait.footfalls_per_step(step_hz, v, 0.54), 2 * (0.9 / 0.54) ** 0.7)
    assert gait.lock_deviation(2.85) == pytest.approx(3 / 2.85 - 1)
    assert gait.lock_deviation(1.42, per=2) == pytest.approx(3 / 2.84 - 1)


try:
    from h2d.common.robot import B2Z1Robot

    ROBOT = B2Z1Robot()
except Exception:  # pragma: no cover - X-Morph checkout missing
    ROBOT = None


@pytest.mark.skipif(ROBOT is None, reason="B2-Z1 model not found (XMORPH_ROOT)")
def test_b2_hip_height():
    d = gait.hip_height(ROBOT)
    assert d["thigh_m"] == pytest.approx(0.35, abs=1e-3) and d["calf_m"] == pytest.approx(0.35, abs=1e-3)
    assert d["hip_height_m"] == pytest.approx(0.5435, abs=2e-3)
