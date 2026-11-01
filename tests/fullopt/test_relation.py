"""Relation term (fullopt spec v0.2 §5): representation (a), vertex substitution, and the slot for (b)."""

import numpy as np
import pytest

from h2d.fullopt.relation import REPRESENTATIONS, VertexSubstitution, object_samples

try:
    from h2d.fullopt.robot import Robot

    ROBOT = Robot()
except Exception:  # pragma: no cover - X-Morph checkout missing
    ROBOT = None

needs_robot = pytest.mark.skipif(ROBOT is None, reason="B2-Z1 model not found (XMORPH_ROOT)")
BOX = np.array([[x, y, z] for x in (0.6, 1.0) for y in (-0.3, 0.3) for z in (0.0, 0.6)])


def setup(q_seed: int = 0):
    rng = np.random.default_rng(q_seed)
    d = ROBOT.dofs("base", "arm")
    q = ROBOT.integrate(ROBOT.placed([0.0, 0.0], 0.2), rng.normal(0, 0.2, len(d)), d)
    ROBOT.set(q)
    P = np.array([ROBOT.point(k) for k in ROBOT.point_names])
    objects = np.vstack([BOX, BOX.mean(0) + rng.normal(0, 0.1, (16, 3))])
    return q, d, P, objects


def test_object_samples_are_spread():
    s = object_samples(BOX, 8)
    assert len({tuple(p) for p in s}) == 8 and np.allclose(s[0], BOX[0])


@needs_robot
def test_residual_is_zero_on_the_targets_shape():
    q, d, P, objects = setup()
    for dz in (0.0, 0.4):                    # horizontal transfer: the targets' heights do not matter (spec §5.1)
        rel = VertexSubstitution(ROBOT.point_names, (P + [0, 0, dz])[None], objects[None])
        r, J = rel.residual(0, ROBOT, d)
        assert rel.n_rows == 2 * len(P) and r.shape == (rel.n_rows,) and J.shape == (rel.n_rows, len(d))
        assert np.abs(r).max() < 1e-12
    moved = P.copy()
    moved[0, :2] += [0.2, -0.1]                                  # the trunk's target moved: a residual appears
    r = VertexSubstitution(ROBOT.point_names, moved[None], objects[None]).residual(0, ROBOT, d)[0]
    assert np.abs(r).max() > 0.05


@needs_robot
def test_residual_jacobian_matches_finite_differences():
    q, d, P, objects = setup(1)
    rel = VertexSubstitution(ROBOT.point_names, (P + np.random.default_rng(2).normal(0, 0.1, P.shape))[None],
                             objects[None])
    ROBOT.set(q)
    J = rel.residual(0, ROBOT, d)[1]
    eps, cols = 1e-6, []
    for k in range(len(d)):
        e = np.zeros(len(d))
        e[k] = eps
        ROBOT.set(ROBOT.integrate(q, e, d))
        a = rel.residual(0, ROBOT, d)[0]
        ROBOT.set(ROBOT.integrate(q, -e, d))
        cols.append((a - rel.residual(0, ROBOT, d)[0]) / (2 * eps))
    assert np.allclose(J, np.array(cols).T, atol=1e-6)


def test_whole_network_mapping_is_m2():
    with pytest.raises(NotImplementedError):
        REPRESENTATIONS["b"](None, None, None, None, None)
