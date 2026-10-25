"""X-Morph prior wrapper: runs inference on a shipped G1 clip, truncates and writes a sidecar."""

import json
import os
from pathlib import Path

import numpy as np
import pytest

from h2d.paths import REPO_ROOT

xmorph = Path(os.environ.get("XMORPH_ROOT") or REPO_ROOT / "external" / "morph")
CLIP = xmorph / "data/raw/g1/manip_slow/General_A5_-_Pick_Up_Box_stageii.pkl"

pytestmark = [
    pytest.mark.skipif(not CLIP.is_file(), reason="X-Morph checkout with sample data not available"),
]


def test_run_xmorph_truncates_and_writes_sidecar(tmp_path):
    pytest.importorskip("torch")
    pytest.importorskip("pytorch_kinematics")
    from h2d.learned.prior import load_motion, run_xmorph

    out = tmp_path / "pickup_b2z1.pkl"
    side = run_xmorph(CLIP, out, device="cpu")
    m = load_motion(out)
    src = load_motion(CLIP)
    assert m.n == src.n == side["out_n_frames"]
    assert side["out_n_frames_raw"] >= side["out_n_frames"]
    assert m.dof_pos.shape[1] == 19
    assert np.allclose(np.linalg.norm(m.root_rot_xyzw, axis=1), 1.0, atol=1e-4)
    assert np.allclose(m.root_pos[0, :2], 0.0, atol=1e-6)  # X-Morph output starts at the origin
    on_disk = json.loads(Path(str(out) + ".sidecar.json").read_text())
    assert on_disk["src_n_frames"] == src.n
    assert len(on_disk["src_root_pos0"]) == 3
