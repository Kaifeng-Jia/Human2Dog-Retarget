"""Task targets from the input clip alone (fullopt spec v0.2 §2): the learned line's semantics on a synthetic push."""

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from h2d.paths import load_config

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from synthetic_hoi import make_clip  # noqa: E402

try:
    from h2d.common.data.omomo_objects import load_object

    BOX = load_object("largebox")
except Exception:  # pragma: no cover - HOI-Retarget meshes missing
    BOX = None

pytestmark = pytest.mark.skipif(BOX is None, reason="object meshes not found (HOI_RETARGET_ROOT)")
CFG = load_config("fullopt/solver.yaml")["task"]
BAND = load_config("candidate_selection.yaml")["reach_band"]


def clips(hands: str = "R", face: str = "top"):
    """The common clip with the learned line's task of its push, and the same clip as the method's input."""
    from h2d.common.data.tasks import build_task
    from h2d.fullopt.hoi import from_common_clip

    src = make_clip(carry=False, T=150, push_face=face, push_hands=hands)
    learned = build_task(src, BOX, (30, 90), hands, band=BAND)
    c = from_common_clip(src, BOX, {"id": "s", "split": "dev", "mode": hands, "segment": learned["segment"],
                                    "window": learned["window"]})
    return src, learned, c


def test_palm_is_the_learned_palm_on_a_flat_hand():
    from h2d.common.data.describe import palm_point
    from h2d.fullopt import task as tk

    src, _, c = clips()
    fr = np.arange(30, 90)                     # wrist + four knuckles = wrist + index and pinky counted twice
    assert np.allclose(tk.palm(c, "R", fr), palm_point(src, "R", fr), atol=1e-9)


@pytest.mark.parametrize("hands", ["R", "B"])
def test_targets_match_the_learned_task(hands):
    from h2d.fullopt import task as tk

    _, learned, c = clips(hands)
    task = tk.build(c, CFG, BAND)
    cmp = tk.compare(task, learned)
    assert cmp["segment_same"] and cmp["mode_same"] and cmp["contact_moved_same"] and cmp["frames"] == 60
    assert task.record["height"]["contact_moved"] == "rear_edge" and not task.record["palm_flipped"]
    assert cmp["tool_x_deg"][1] < 0.1 and cmp["tool_z_deg"][1] < 0.1
    # The input has no finger contact flags: the proxy is the palm centre. The synthetic hand flags the wrist and the
    # index finger, 2.4 cm beside the palm centre for one hand; the two hands' offsets cancel.
    assert cmp["target_m"][0] < (0.03 if hands == "R" else 0.002)


def test_segment_mode_and_contacts_without_labels():
    from h2d.fullopt import task as tk

    _, learned, c = clips()
    bare = replace(c, hand_contact=None, meta={"id": "s"})
    task = tk.build(bare, CFG, BAND)
    assert task.record["source"] == "detected" and not task.record["contact_labels"] and task.mode == "R"
    assert abs(task.segment[0] - 30) <= 3 and abs(task.segment[1] - 90) <= 3


def test_gate_rises_before_contact_and_the_targets_cover_it():
    from h2d.fullopt import task as tk

    _, _, c = clips()
    task = tk.build(c, CFG, BAND)
    (s, e), (a0, a1), (w0, w1) = task.segment, task.span, task.window
    rise, full = (round(CFG[k] * c.fps) for k in ("gate_rise_s", "gate_full_s"))
    t, g = np.arange(c.n), task.gate
    assert np.all(g[(t <= s - rise) | (t >= e - 1 + rise)] == 0) and g.max() <= 1.0
    assert np.all(g[(t >= s - full) & (t <= e - 1 + full)] == 1.0)
    assert np.all(np.diff(g[:s]) >= -1e-12) and np.all(np.diff(g[e:]) <= 1e-12)
    assert (a0, a1) == (max(0, s - rise), min(c.n, e + rise)) and a0 <= w0 and w1 <= a1
    assert np.isfinite(task.target[a0:a1]).all() and np.isnan(task.target[a1:]).all() and a1 < c.n
    loc = task.local["target"]                               # no jump onto or off the face (object frame)
    for a, b in ((s - 1, s), (e - 1, e)):
        assert np.linalg.norm(loc[b - a0] - loc[a - a0]) <= CFG["approach_mps"] / c.fps + 1e-9
