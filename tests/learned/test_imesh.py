"""Interaction-mesh body placement on the synthetic push (no robot model: a box-shaped stand-in for the prior)."""

import sys
from pathlib import Path

import numpy as np
import pytest
import yaml
from scipy.spatial.transform import Rotation as R

from h2d.common.data import omomo_objects as oo
from h2d.paths import REPO_ROOT

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))          # synthetic_hoi

try:
    BOX = oo.load_object("largebox")
except FileNotFoundError:  # pragma: no cover - meshes not cloned
    BOX = None
needs_mesh = pytest.mark.skipif(BOX is None, reason="object meshes not found (HOI_RETARGET_ROOT)")


def stand_in_prior(n: int):
    """A dog at the raw origin facing +x: trunk 0.5 m up, Z1 base 0.3 m ahead and 0.65 m up, feet under the hips,
    the trunk as a 0.9 x 0.3 x 0.25 m box of samples."""
    from h2d.learned.imesh import PriorPoints

    g = np.stack(np.meshgrid(np.linspace(-0.45, 0.45, 7), [-0.15, 0.15], [0.38, 0.62]), -1).reshape(-1, 3)
    feet = np.array([[0.35, 0.15, 0.0], [0.35, -0.15, 0.0], [-0.35, 0.15, 0.0], [-0.35, -0.15, 0.0]])
    rep = lambda a: np.repeat(np.asarray(a, float)[None], n, 0)  # noqa: E731
    return PriorPoints(rep([0, 0, 0.5]), rep([0.3, 0, 0.65]), rep([1.0, 0]), rep(feet), rep(g))


@needs_mesh
def test_mesh_places_the_body_where_the_human_stands_relative_to_the_box():
    from synthetic_hoi import make_clip

    from h2d.common.collision import ObjectHull
    from h2d.common.data.describe import segments
    from h2d.common.data.tasks import build_task
    from h2d.learned.imesh import InteractionMesh, object_samples

    c = make_clip()                                     # human at x = 0 facing +x, right palm on the box's -x face
    s, e = segments(c)[0]
    task = build_task(c, BOX, (s, e), "R")
    n = len(task["frames"])
    cfg = yaml.safe_load((REPO_ROOT / "configs" / "learned" / "mesh.yaml").read_text())
    m = InteractionMesh(task, stand_in_prior(n), object_samples(BOX.hull_verts, cfg["object_samples"]),
                        ObjectHull.from_vertices(BOX.hull_verts), cfg)
    psi0, b0 = np.pi / 2, np.array([0.75, -1.2])        # start wrong: beside the box, facing +y
    before = m.metrics(np.full(n, psi0), np.tile(b0, (n, 1)))
    psi, b, info = m.place(psi0, b0)
    after = m.metrics(psi, b)
    assert info["n_edges"] > n and after["edge_dir_err_deg"] < before["edge_dir_err_deg"] / 3
    assert after["heading_err_deg"] < 10 and after["body_in_object_m"] < 0.01
    box_min_x = np.array([(R.from_quat(q).apply(BOX.hull_verts) + p)[:, 0].min()
                          for p, q in zip(task["obj_pos"], task["obj_rot_xyzw"])])
    assert np.all(b[:, 0] < box_min_x)                  # the trunk stays behind the face the human pushes
    assert after["reach_m"][1] < cfg["r_max_m"] + 0.05


@needs_mesh
def test_smoothness_counts_the_trunk_step_not_the_parameters():
    from synthetic_hoi import make_clip

    from h2d.common.collision import ObjectHull
    from h2d.common.data.describe import segments
    from h2d.common.data.tasks import build_task
    from h2d.learned.imesh import InteractionMesh, object_samples

    c = make_clip()
    s, e = segments(c)[0]
    task = build_task(c, BOX, (s, e), "R")
    n = len(task["frames"])
    pp = stand_in_prior(n)
    pp.trunk[:, 0] += 3.0                               # the raw prior has walked 3 m from the origin
    cfg = yaml.safe_load((REPO_ROOT / "configs" / "learned" / "mesh.yaml").read_text())
    m = InteractionMesh(task, pp, object_samples(BOX.hull_verts, 24), ObjectHull.from_vertices(BOX.hull_verts), cfg)
    x0 = np.zeros((n, 3))
    x = x0.copy()
    x[n // 2:, 0] = 0.01                                # turn by 0.01 rad half-way: the trunk steps ~3 cm
    r = m._residual(x.ravel(), x0) - m._residual(x0.ravel(), x0)
    k = len(r) - 3 * n - 3 * (n - 1) + 3 * (n // 2 - 1)   # the smoothness rows of that frame pair
    assert abs(np.linalg.norm(r[k:k + 2]) / cfg["w_smooth"] - 0.03) < 0.002
