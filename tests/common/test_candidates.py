"""Candidate criteria, ranking and the candidate sheet."""

import math

import numpy as np

import pytest

from h2d.common.data import candidates as cd
from h2d.common.data import omomo_objects as oo

try:
    BOX = oo.load_object("largebox")
except FileNotFoundError:  # pragma: no cover - meshes not cloned
    BOX = None
needs_mesh = pytest.mark.skipif(BOX is None, reason="object meshes not found (HOI_RETARGET_ROOT)")


def _row(name="sub1_largebox_001", obj="largebox", ds="omomo_new", **kw):
    r = {"dataset": ds, "object": obj, "name": name, "object_state": "slid", "obj_lifted_frac": 0.0, "hands": "right",
         "duration_s": 2.0, "obj_tilt_max_deg": 1.0, "obj_yaw_maxabs_deg": 2.0, "frac_body": 0.0,
         "contact_surface_dist_median_m": 0.03, "push_alignment": 0.95, "normal_spread_p90_deg": 3.0,
         "patch_coherence_median": 0.95, "hands_face_angle_deg": 0.0, "normal_tilt_median_deg": 5.0, "obj_disp_xy_m": 0.3,
         "approach_angle_deg": 10.0, "retreat_angle_deg": 12.0}
    r.update(kw)
    r["passed"] = not cd.failed(r, cd.SEGMENT_CRITERIA + cd.PUSH_CRITERIA)
    return r


def test_failed_lists_every_criterion_and_nan_fails():
    r = _row(hands="mixed", push_alignment=float("nan"), obj_tilt_max_deg=12.0)
    assert cd.failed(r) == ["one_mode", "small_tilt"]
    assert cd.failed(_row(hands="both")) == [] and cd.failed(_row(hands="left")) == []
    assert cd.failed(_row(hands_face_angle_deg=170.0), cd.PUSH_CRITERIA) == ["same_face"]
    assert cd.failed(r, cd.PUSH_CRITERIA) == ["push"]
    assert "on_surface" in cd.failed({k: v for k, v in r.items() if k != "contact_surface_dist_median_m"},
                                     cd.PUSH_CRITERIA)


def test_tier():
    assert cd.tier(_row()) == "A"
    assert cd.tier(_row(approach_angle_deg=float("nan"))) == "B"
    assert cd.tier(_row(approach_angle_deg=float("nan"), retreat_angle_deg=float("nan"))) == "B"
    assert cd.tier(_row(retreat_angle_deg=50.0)) == "C"


def test_select_ranks_and_caps():
    rows = [
        _row("a1", duration_s=5.0, approach_angle_deg=float("nan")),           # B, long
        _row("a2", duration_s=1.5),                                            # A
        _row("a3", duration_s=3.0),                                            # A, longer -> first
        _row("a4", duration_s=4.0),                                            # A, but third of the object
        _row("b1", obj="box_huge", ds="force", retreat_angle_deg=60.0),        # C
        _row("b2", obj="box_huge", ds="force", normal_tilt_median_deg=60.0),   # A, top face
        _row("b3", obj="box_huge", ds="force", hands="mixed"),                 # fails
    ]
    rows.append(dict(rows[2], seg=1))                                          # same clip twice
    out = cd.select(rows, top=10, per_object=2)
    assert [r["name"] for r in out] == ["a4", "a3", "b2", "b1"]
    assert [r["rank"] for r in out] == [1, 2, 3, 4] and [r["tier"] for r in out] == ["A", "A", "A", "C"]
    assert len(cd.select(rows, top=1)) == 1


def test_funnel_counts_in_order():
    rows = [_row(), _row(hands="mixed"), _row(object_state="lifted"), _row(push_alignment=-0.9)]
    f = dict(cd.funnel(rows))
    assert f["all segments"] == 4 and f["slid"] == 3 and f["one_mode"] == 2 and f["push"] == 1
    assert f["flat_patch"] == 1
    names = [n for n, *_ in cd.SEGMENT_CRITERIA + cd.PUSH_CRITERIA]
    assert [n for n, _ in cd.funnel(rows)][1:] == names


@needs_mesh
@pytest.mark.parametrize("face,hands", [("side", "R"), ("top", "R"), ("side", "B")])
def test_candidate_sheet_and_gallery(tmp_path, face, hands):
    from synthetic_hoi import make_clip

    from h2d.common.data.describe import describe_clip, push_descriptors
    from h2d.common.viz_hoi import candidate_figure, gallery

    c = make_clip(push_face=face, push_hands=hands)
    seg = describe_clip(c, BOX)["segments"][0]
    r = {"dataset": "omomo_new", **seg, "mode": hands, **push_descriptors(c, BOX, (seg["start"], seg["end"]), hands)}
    r["passed"] = not cd.failed(r, cd.SEGMENT_CRITERIA + cd.PUSH_CRITERIA)
    assert r["passed"], cd.failed(r, cd.SEGMENT_CRITERIA + cd.PUSH_CRITERIA)
    (cand,) = cd.select([r])
    assert cand["tier"] == "A" and not math.isnan(cand["approach_angle_deg"])
    candidate_figure(c, BOX, cand, tmp_path / "c.png", side=hands)
    gallery([(c, BOX, cand)], tmp_path / "g.png")
    assert (tmp_path / "c.png").stat().st_size > 20_000 and (tmp_path / "g.png").stat().st_size > 5_000


def test_criteria_with_yaw_limit_and_reach_band():
    band = {"side": [0.5, 1.2], "top": [0.3, 0.8], "slant": [0.4, 1.2]}
    seg, push = cd.criteria(45.0, band)
    assert [c for c in seg if c[0] == "small_yaw"][0][3] == 45.0 and push[-1][0] == "reach_band"
    assert cd.face_of(5.0) == "side" and cd.face_of(85.0) == "top" and cd.face_of(45.0) == "slant"
    low_side = _row(obj_yaw_maxabs_deg=30.0, contact_z_median_m=0.25, normal_tilt_median_deg=5.0)
    high_top = _row(obj_yaw_maxabs_deg=30.0, contact_z_median_m=0.45, normal_tilt_median_deg=85.0)
    for r in (low_side, high_top):
        r["in_reach_band"] = cd.in_band(r, band)
    assert cd.failed(low_side, seg + push) == ["reach_band"] and cd.failed(high_top, seg + push) == []
    assert "small_yaw" in cd.failed(high_top)                       # the default 20 deg limit still applies
    # a side contact at 0.25 m on a tall face (up to 1.0 m) moves up into the band; on a short face it cannot
    tall = dict(low_side, face_z_min_m=0.0, face_z_max_m=1.0)
    short = dict(low_side, face_z_min_m=0.0, face_z_max_m=0.4)
    assert cd.adapted_height(tall, band) == 0.5 and np.isnan(cd.adapted_height(short, band))
    assert cd.adapted_height(dict(tall, contact_z_median_m=1.4), band) == 0.95       # chest-high push lowered
    names = [n for n, _ in cd.funnel([low_side, high_top], (seg, push))]
    assert names[-1] == "reach_band" and [c["name"] for c in cd.criteria_table((seg, push))][-1] == "reach_band"


def test_pull_and_grasp_criteria():
    band = {"side": [0.5, 1.2], "top": [0.3, 0.8], "slant": [0.4, 1.2], "grasp": [0.3, 1.2]}
    seg, push = cd.criteria(45.0, band, ("push", "pull"))
    names = [c[0] for c in push]
    assert "push" not in names and "interaction" in names and "contact_shape" in names and "one_face" not in names
    pull = _row(push_alignment=-0.9, normal_spread_p90_deg=60.0, patch_coherence_median=0.4, grip="grasp",
                contact_z_median_m=0.55, normal_tilt_median_deg=40.0)
    pull["interaction"], pull["contact_shape_ok"] = cd.interaction_of(pull), cd.contact_shape_ok(pull)
    pull["in_reach_band"] = cd.in_band(pull, band)
    assert pull["interaction"] == "pull" and pull["contact_shape_ok"] and cd.failed(pull, seg + push) == []
    assert cd.adapted_height(pull, band) == 0.55                     # a grasped part keeps its height
    press = dict(pull, grip="press")
    press["contact_shape_ok"] = cd.contact_shape_ok(press)
    assert "contact_shape" in cd.failed(press, push)                 # a press still needs one flat face
    assert cd.interaction_of(_row(push_alignment=0.2)) == ""
