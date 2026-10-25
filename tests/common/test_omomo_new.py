"""OMOMO_new adapter on synthetic clips (no dataset needed)."""

import numpy as np
from scipy.spatial.transform import Rotation as R

from h2d.common.data import omomo_new as om


def make_clip(T=60, zero_first=True, right=(10, 40), left=None, body=None, obj_dx=0.3):
    a = np.zeros((T + int(zero_first), om.DIM), np.float32)
    s = int(zero_first)
    a[s:, om.SLICES["root_rot_xyzw"]] = [0, 0, 0, 1]
    a[s:, om.SLICES["obj_rot_xyzw"]] = [0, 0, 0, 1]
    a[s:, om.SLICES["body_rot_xyzw"]] = np.tile([0, 0, 0, 1], 52)
    a[s:, om.SLICES["root_pos"]] = [0, 0, 0.9]
    bp = np.zeros((T, 52, 3), np.float32)
    bp[:, :, 2] = 0.9
    a[s:, om.SLICES["body_pos"]] = bp.reshape(T, -1)
    a[s:, 318] = np.linspace(1.0, 1.0 + obj_dx, T)
    flags = np.zeros((T, 52), np.float32)
    if right:
        flags[right[0]:right[1], om.HAND_BODIES["R"][0]] = 1
    if left:
        flags[left[0]:left[1], om.HAND_BODIES["L"][3]] = 1
    if body:
        flags[body[0]:body[1], om.BODY_INDEX["L_Toe"]] = 1
    a[s:, om.SLICES["contact_body"]] = flags
    return om.parse_array(a, "sub1_largebox_001")


def test_parse_drops_zero_first_frame_and_names():
    c = make_clip()
    assert c.dropped_first_frame and c.n == 60
    assert (c.subject, c.obj) == ("sub1", "largebox")
    assert c.body_pos.shape == (60, 52, 3) and c.contact_body.shape == (60, 52)


def test_intervals_and_short_runs():
    m = np.array([0, 1, 1, 0, 1, 0, 0, 1, 1, 1], bool)
    assert om.intervals(m) == [(1, 3), (4, 5), (7, 10)]
    assert om.intervals(om.remove_short_runs(m, 2)) == [(1, 3), (7, 10)]


def test_modes_single_right_and_body_override():
    c = make_clip(right=(10, 40), body=(30, 45))
    mode = om.contact_modes(c, min_sec=0.1)
    assert (mode[12:30] == "right").all()
    assert (mode[30:45] == "body").all()
    assert (mode[:10] == "none").all()


def test_modes_both_hands():
    c = make_clip(right=(10, 40), left=(20, 50))
    mode = om.contact_modes(c, min_sec=0.1)
    assert (mode[20:40] == "both").all() and (mode[40:50] == "left").all()


def test_clip_stats_longest_interval():
    s = om.clip_stats(make_clip(right=(10, 40), obj_dx=0.29))
    b = s["longest_single_hand"]
    assert b["side"] == "right" and (b["start"], b["end"]) == (10, 40)
    assert abs(b["duration_s"] - 1.0) < 1e-9
    assert 0.13 < b["obj_disp_xy_m"] < 0.15        # 30 of 60 frames of a 0.29 m ramp
    assert b["obj_dz_m"] == 0.0 and b["obj_max_rot_deg"] == 0.0


def test_smplx_params_root_frame_permutation():
    c = make_clip()
    p = om.smplx_params(c)
    assert p["pose_body"].shape == (60, 63) and p["betas"].shape == (10,)
    expect = (R.identity() * om._YUP_TO_ZUP).as_rotvec()
    assert np.allclose(p["root_orient"][0], expect, atol=1e-6)
    # per-joint reorder [1, 2, 0]: dof triple (a, b, c) -> (b, c, a)
    a = np.zeros((61, om.DIM), np.float32)
    a[1:, om.SLICES["root_rot_xyzw"]] = [0, 0, 0, 1]
    k = om.BODY_INDEX["L_Knee"] - 1
    a[1:, 9 + 3 * k: 9 + 3 * k + 3] = [0.1, 0.2, 0.3]
    p2 = om.smplx_params(om.parse_array(a, "x"))
    i = om.SMPLX_BODY_JOINTS.index("left_knee")
    assert np.allclose(p2["pose_body"][0, 3 * i:3 * i + 3], [0.2, 0.3, 0.1])
