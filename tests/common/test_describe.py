"""Object meshes and descriptive segments on a synthetic clip (needs the pinned HOI-Retarget meshes)."""

import numpy as np
import pytest
from scipy.spatial.transform import Rotation as R

from h2d.common.data import omomo_objects as oo
from h2d.common.data.describe import alignment_series, close_gaps, describe_clip, segments

try:
    BOX = oo.load_object("largebox")
except FileNotFoundError:  # pragma: no cover - meshes not cloned
    BOX = None
needs_mesh = pytest.mark.skipif(BOX is None, reason="object meshes not found (HOI_RETARGET_ROOT)")


def test_close_gaps():
    m = np.array([1, 1, 0, 0, 1, 0, 0, 0, 0, 1], bool)
    assert close_gaps(m, 3).tolist() == [1, 1, 1, 1, 1, 0, 0, 0, 0, 1]


def test_tilt_and_yaw_split():
    q = R.from_euler("zx", [[0, 0], [40, 0], [40, 25]], degrees=True).as_quat()
    tilt, yaw = oo.tilt_and_yaw(q, 0)
    assert np.allclose(tilt, [0, 0, 25], atol=1e-6)
    assert np.allclose(yaw[:2], [0, 40], atol=1e-6)


@needs_mesh
def test_mesh_lowest_point_and_distance():
    assert BOX.faces.max() < len(BOX.verts)
    z = BOX.lowest_z(np.array([[0, 0, 0.198]]), np.array([[0, 0, 0, 1.0]]))
    assert abs(z[0] - (0.198 + BOX.verts[:, 2].min())) < 1e-9
    # 45 deg about x: lowest point = hull support in direction -z
    q = R.from_euler("x", 45, degrees=True)
    z2 = BOX.lowest_z(np.zeros((1, 3)), q.as_quat()[None])
    assert abs(z2[0] - q.apply(BOX.verts)[:, 2].min()) < 1e-9
    from h2d.common.meshgeom import point_mesh_distance

    p = np.array([[BOX.verts[:, 0].min() - 0.02, 0.0, 0.0], BOX.verts[100] + 0.003, [0.0, 0.0, 2.0]])
    d = BOX.surface_distance(p)
    ref = [point_mesh_distance(x, BOX.verts, BOX.faces) for x in p[:2]]
    assert np.allclose(d[:2], ref, atol=1e-9) and d[1] <= 0.003 * 3 ** 0.5 + 1e-9 and d[2] > 1.5
    assert abs(BOX.min_surface_distance(p) - min(d)) < 1e-12


@needs_mesh
def test_describe_synthetic_push_then_carry():
    from synthetic_hoi import make_clip

    c = make_clip()
    segs = segments(c)
    assert len(segs) == 2
    d = describe_clip(c, BOX)
    a, b = d["segments"]
    assert (a["hands"], a["object_state"], a["human"]) == ("right", "slid", "stand")
    assert abs(a["obj_disp_xy_m"] - 0.30) < 0.02 and a["obj_clear_max_m"] < 0.01
    assert a["frac_palm"] == 1.0
    assert (b["hands"], b["object_state"], b["human"]) == ("both", "lifted", "walk")
    assert b["two_hand_angle_deg"] > 150
    assert np.nanmax(d["check"]["contact_hand_min_m"]) < 0.02
    assert np.nanmin(d["check"]["free_hand_min_m"]) > 0.1
    row = d["clip"]
    assert row["n_segments"] == 2 and abs(row["obj_lowest_z_start_m"]) < 1e-6


@needs_mesh
def test_push_descriptors_on_synthetic_push():
    from synthetic_hoi import make_clip

    from h2d.common.data.describe import push_descriptors

    c = make_clip()
    s, e = segments(c)[0]
    d = push_descriptors(c, BOX, (s, e), "R")
    assert d["push_alignment"] > 0.9                          # box moves away from the hand (+x, hand on -x face)
    assert d["normal_spread_p90_deg"] < 5 and d["normal_tilt_median_deg"] < 5 and d["patch_coherence_median"] > 0.9
    n_world = R.from_quat(c.obj_rot_xyzw[s]).apply(d["normal_local"])
    assert n_world[0] < -0.99                                 # the face the palm is on, pointing to the hand
    assert abs(d["approach_available_s"] - 1.0) < 0.05
    assert d["approach_angle_deg"] < 3 and d["retreat_angle_deg"] < 3      # straight in, straight out
    assert abs(d["approach_time_s"] - 0.2) < 0.05                        # last 0.10 m of a 0.25 m / 0.5 s path
    assert d["contact_surface_dist_median_m"] < 0.05
    a = alignment_series(c, BOX, slice(s, e), "R")
    assert len(a) == e - s and np.nanmin(a) > 0.9


@needs_mesh
def test_push_descriptors_time_reversed_is_a_pull():
    from synthetic_hoi import make_array

    from h2d.common.data import omomo_new as om
    from h2d.common.data.describe import push_descriptors

    a = make_array()
    a[1:] = a[1:][::-1].copy()                  # the box now moves towards the hand on its -x face
    c = om.parse_array(a, "sub1_largebox_002")
    seg = next(r for r in describe_clip(c, BOX)["segments"] if r["hands"] == "right")
    d = push_descriptors(c, BOX, (seg["start"], seg["end"]), "R")
    assert d["push_alignment"] < -0.9
    assert d["approach_angle_deg"] < 3 and d["retreat_angle_deg"] < 3   # in and out swap, both along the normal
