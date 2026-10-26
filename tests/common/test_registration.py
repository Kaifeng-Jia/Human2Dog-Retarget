"""Scene registration (SE(2) per demonstration)."""

import numpy as np
from scipy.spatial.transform import Rotation as R

from h2d.common.registration import SE2, contact_fit, rot2, start_anchored


def test_start_anchored_maps_output_start_to_source_start():
    T = start_anchored([2.0, -1.0, 0.9], np.radians(30), [0.0, 0.0, 0.5], np.radians(10))
    assert np.isclose(np.degrees(T.psi), 20)
    p = T.apply_points(np.array([[0.0, 0.0, 0.5]]))
    assert np.allclose(p, [[2.0, -1.0, 0.5]])                 # xy to the source, height kept
    _, q = T.apply_root(np.zeros((1, 3)), R.from_euler("z", 10, degrees=True).as_quat()[None])
    assert np.isclose(R.from_quat(q[0]).as_euler("zyx", degrees=True)[0], 30)


def test_contact_fit_recovers_a_rigid_motion_and_respects_the_prior():
    rng = np.random.default_rng(0)
    t = np.linspace(0, 1, 60)
    p = np.stack([1.5 * t, 0.3 * np.sin(3 * t), np.full_like(t, 0.3)], 1)        # prior contact-site path
    true = SE2(np.radians(25), (0.4, -0.2))
    y = true.apply_points(p) + rng.normal(0, 0.002, p.shape)
    T = contact_fit(p, y, None, psi_anchor=np.radians(20), lambda_psi=0.0)
    assert abs(np.degrees(T.psi) - 25) < 0.3 and np.allclose(T.b, (0.4, -0.2), atol=0.01)
    assert T.info["residual_xy_rms_m"] < 0.005
    # a strong yaw prior pulls psi towards the anchor
    T2 = contact_fit(p, y, None, psi_anchor=np.radians(20), lambda_psi=100.0)
    assert abs(np.degrees(T2.psi) - 20) < 1.0
    # targets that do not move: yaw not identifiable, fixed to the anchor, b closes the mean offset
    still = np.tile([[1.0, 2.0, 0.3]], (30, 1))
    T3 = contact_fit(p[:30], still, None, psi_anchor=np.radians(5))
    assert T3.info["yaw_fixed_to_anchor"] and np.isclose(T3.psi, np.radians(5))
    pm = p[:30, :2].mean(0)
    assert np.allclose(rot2(T3.psi) @ pm + np.asarray(T3.b), [1.0, 2.0])
