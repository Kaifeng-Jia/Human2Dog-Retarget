"""The full-optimization line's input format (fullopt spec v0.2 §2.1): mappings, file round trip, validation."""

import sys
from pathlib import Path

import numpy as np

from h2d.common.data.omomo_new import BODY_NAMES
from h2d.fullopt.hoi import OPTIONAL, REQUIRED, HOIClip, mapping, rename, validate

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from synthetic_hoi import standing_pose  # noqa: E402

T = 20


def clip(joints=None, names=None) -> HOIClip:
    if joints is None:
        joints, names = rename(np.repeat(standing_pose()[None], T, 0), BODY_NAMES, "common_clip")
    return HOIClip(fps=30.0, joints=joints, joint_names=names, obj_verts=np.eye(3), obj_faces=np.array([[0, 1, 2]]),
                   obj_pos=np.zeros((T, 3)), obj_quat=np.tile([0.0, 0.0, 0.0, 1.0], (T, 1)),
                   hand_contact=np.zeros((T, 2), bool), meta={"id": "x", "split": "dev"})


def test_mappings_cover_the_semantic_joints():
    for fmt in ("common_clip", "smpl"):
        assert set(mapping(fmt)) == set(REQUIRED) | set(OPTIONAL)
    joints, names = rename(np.zeros((2, 3, 3)), ["left_wrist", "pelvis", "head"], "smpl")
    assert names == ("pelvis", "head", "l_wrist") and joints.shape == (2, 3, 3)


def test_round_trip_and_a_valid_clip(tmp_path):
    c = clip()
    assert validate(c) == []
    c.save(tmp_path / "c.npz")
    d = HOIClip.load(tmp_path / "c.npz")
    assert d.joint_names == c.joint_names and np.array_equal(d.joints, c.joints) and d.meta == c.meta
    assert d.hand_contact.shape == (T, 2)


def test_validation_catches_axes_units_and_missing_joints():
    c = clip()
    y_up = clip(c.joints[..., [0, 2, 1]], c.joint_names)              # y up
    cm = clip(100 * c.joints, c.joint_names)                          # centimetres
    no_head = clip(c.joints[:, 1:], c.joint_names[1:]) if c.joint_names[0] == "pelvis" else None
    assert any("z-up" in p for p in validate(y_up))
    assert any("metres" in p for p in validate(cm))
    assert validate(no_head) == ["missing joint pelvis"]


try:
    from h2d.common.data.omomo_objects import load_object

    BOX = load_object("largebox")
except Exception:  # pragma: no cover - HOI-Retarget meshes missing
    BOX = None


def test_adapter_for_the_common_clip_layout():
    import pytest

    if BOX is None:
        pytest.skip("object meshes not found (HOI_RETARGET_ROOT)")
    from synthetic_hoi import make_clip

    from h2d.common.data.omomo_new import BODY_INDEX
    from h2d.fullopt.hoi import from_common_clip

    src = make_clip()
    c = from_common_clip(src, BOX, {"id": "s", "split": "dev"})
    assert validate(c) == [] and c.meta["subject"] == "sub1" and c.meta["split"] == "dev"
    assert np.allclose(c.joint("l_wrist"), src.body_pos[:, BODY_INDEX["L_Wrist"]])
    assert c.hand_contact is not None and c.hand_contact[:, 1].any()       # the right hand pushes the box
