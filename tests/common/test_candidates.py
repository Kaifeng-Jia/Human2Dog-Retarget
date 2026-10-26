"""Candidate criteria, ranking and the candidate sheet."""

import math

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
         "patch_coherence_median": 0.95, "normal_tilt_median_deg": 5.0, "obj_disp_xy_m": 0.3,
         "approach_angle_deg": 10.0, "retreat_angle_deg": 12.0}
    r.update(kw)
    r["passed"] = not cd.failed(r, cd.SEGMENT_CRITERIA + cd.PUSH_CRITERIA)
    return r


def test_failed_lists_every_criterion_and_nan_fails():
    r = _row(hands="both", push_alignment=float("nan"), obj_tilt_max_deg=12.0)
    assert cd.failed(r) == ["right_hand", "small_tilt"]
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
        _row("b3", obj="box_huge", ds="force", hands="left"),                  # fails
    ]
    rows.append(dict(rows[2], seg=1))                                          # same clip twice
    out = cd.select(rows, top=10, per_object=2)
    assert [r["name"] for r in out] == ["a4", "a3", "b2", "b1"]
    assert [r["rank"] for r in out] == [1, 2, 3, 4] and [r["tier"] for r in out] == ["A", "A", "A", "C"]
    assert len(cd.select(rows, top=1)) == 1


def test_funnel_counts_in_order():
    rows = [_row(), _row(hands="left"), _row(object_state="lifted"), _row(push_alignment=-0.9)]
    f = dict(cd.funnel(rows))
    assert f["all segments"] == 4 and f["slid"] == 3 and f["right_hand"] == 2 and f["push"] == 1
    assert f["flat_patch"] == 1
    names = [n for n, *_ in cd.SEGMENT_CRITERIA + cd.PUSH_CRITERIA]
    assert [n for n, _ in cd.funnel(rows)][1:] == names


@needs_mesh
@pytest.mark.parametrize("face", ["side", "top"])
def test_candidate_sheet_and_gallery(tmp_path, face):
    from synthetic_hoi import make_clip

    from h2d.common.data.describe import describe_clip, push_descriptors
    from h2d.common.viz_hoi import candidate_figure, gallery

    c = make_clip(push_face=face)
    seg = describe_clip(c, BOX)["segments"][0]
    r = {"dataset": "omomo_new", **seg, **push_descriptors(c, BOX, (seg["start"], seg["end"]), "R")}
    r["passed"] = not cd.failed(r, cd.SEGMENT_CRITERIA + cd.PUSH_CRITERIA)
    assert r["passed"], cd.failed(r, cd.SEGMENT_CRITERIA + cd.PUSH_CRITERIA)
    (cand,) = cd.select([r])
    assert cand["tier"] == "A" and not math.isnan(cand["approach_angle_deg"])
    candidate_figure(c, BOX, cand, tmp_path / "c.png")
    gallery([(c, BOX, cand)], tmp_path / "g.png")
    assert (tmp_path / "c.png").stat().st_size > 20_000 and (tmp_path / "g.png").stat().st_size > 5_000
