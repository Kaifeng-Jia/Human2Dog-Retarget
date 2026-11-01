"""Which grasp segments the full-optimization line takes, and their split by person (fullopt spec v0.2 §8.5)."""

import csv

from h2d.fullopt.tasks import grasp_rows, split_by_person


def test_grasp_rows_are_the_passing_grasps(tmp_path):
    rows = [{"name": "a", "subject": "sub1", "passed": "True", "grip": "grasp"},
            {"name": "b", "subject": "sub1", "passed": "False", "grip": "grasp"},     # failed a criterion
            {"name": "c", "subject": "sub2", "passed": "True", "grip": "press"},      # a top-face drag presses
            {"name": "d", "subject": "sub9", "passed": "True", "grip": "grasp"}]
    with open(tmp_path / "pool.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    assert [r["name"] for r in grasp_rows(tmp_path / "pool.csv")] == ["a", "d"]


def test_split_by_person():
    people = {"sub1", "sub6"}
    assert split_by_person("sub6", people) == "dev"
    assert split_by_person("sub9", people) == "heldout"
    assert split_by_person("session260923", people) == "heldout"        # FORCE: a recording session, never dev


def test_grasp_selection_keeps_turned_pulls_that_need_a_grasp():
    from h2d.common.data import candidates as cd
    from h2d.paths import load_config

    sel = load_config("fullopt/grasp_selection.yaml")
    seg, push = cd.criteria(sel["max_yaw_deg"], sel["reach_band"], tuple(sel["interactions"]), tuple(sel["grips"]))
    row = {"interaction": "pull", "normal_tilt_median_deg": 5.0, "obj_yaw_maxabs_deg": 120.0}
    row["grip"] = cd.robot_grip(row)
    yaw = [c for c in seg if c[0] == "small_yaw"]
    assert row["grip"] == "grasp" and not cd.failed(row, yaw)
    assert not cd.failed(row, [c for c in push if c[0] in ("interaction", "grip")])
    drag = {"interaction": "pull", "normal_tilt_median_deg": 85.0}                  # top face: the gripper presses
    assert cd.robot_grip(drag) == "press"
    assert sel["reach_band"]["grasp"][0] <= 0.25                                    # bin rims and box lips
