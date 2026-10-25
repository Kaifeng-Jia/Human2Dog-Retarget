"""SMPL-H numpy model on a synthetic model file (no licensed files needed)."""

import pickle
import sys
import types

import numpy as np
import scipy.sparse as sp
from scipy.spatial.transform import Rotation as R

from h2d.common.body import smplh

PARENTS = [-1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14, 16, 17, 18, 19]
for _w in (20, 21):
    for _f in range(5):
        PARENTS += [_w, len(PARENTS), len(PARENTS) + 1]


def fake_model(V=300, seed=0):
    rng = np.random.default_rng(seed)
    J = 52
    vt = rng.normal(size=(V, 3)) * 0.3
    Wt = np.zeros((V, J))
    Wt[np.arange(V), np.arange(V) % J] = 1.0
    Jreg = sp.csc_matrix(Wt.T / Wt.sum(0)[:, None])          # joint = mean of its vertices (csc, as in MANO)
    kt = np.array([[2 ** 32 - 1 if p < 0 else p for p in PARENTS], list(range(J))], dtype=np.int64)
    return {"v_template": vt, "shapedirs": rng.normal(size=(V, 3, 10)) * 0.01,
            "posedirs": rng.normal(size=(V, 3, 9 * (J - 1))) * 0.001, "J_regressor": Jreg, "weights": Wt,
            "kintree_table": kt, "f": np.array([[0, 1, 2]])}


def chumpy_pickle(d, path):
    """Pickle ``d`` with shapedirs wrapped in a class that pickles as chumpy.ch.Ch (its __dict__ holds x)."""
    mod_ch = types.ModuleType("chumpy.ch")
    pkg = types.ModuleType("chumpy")

    class Ch:
        def __init__(self, x):
            self.x = x
            self.dterms = ["x"]

    Ch.__module__, Ch.__qualname__ = "chumpy.ch", "Ch"
    mod_ch.Ch = Ch
    sys.modules["chumpy"], sys.modules["chumpy.ch"] = pkg, mod_ch
    try:
        d = dict(d, shapedirs=Ch(d["shapedirs"]))
        with open(path, "wb") as f:
            pickle.dump(d, f, protocol=2)
    finally:
        del sys.modules["chumpy"], sys.modules["chumpy.ch"]


def test_load_chumpy_pickle_without_chumpy(tmp_path):
    d = fake_model()
    p = tmp_path / "SMPLH_fake.pkl"
    chumpy_pickle(d, p)
    assert "chumpy" not in sys.modules
    m = smplh.load_model(p)
    assert np.allclose(m.shapedirs, d["shapedirs"]) and m.parents[0] == -1 and m.n_joints == 52
    assert np.allclose(m.J_regressor.toarray(), d["J_regressor"].toarray())
    assert m.parents.tolist()[1:] == PARENTS[1:]
    info = smplh.describe_file(p)
    assert info["shapedirs"]["shape"] == [300, 3, 10]


def _model(tmp_path):
    p = tmp_path / "m.npz"
    d = fake_model()
    np.savez(p, **{k: (v.toarray() if sp.issparse(v) else v) for k, v in d.items()})
    return smplh.load_model(p)


def test_rest_pose_and_root_rotation(tmp_path):
    m = _model(tmp_path)
    betas = np.linspace(-1, 1, 10)
    v0, J0 = m.rest_joints(betas)
    out = m.forward(np.zeros((1, 156)), np.zeros((1, 3)), betas, vertices=True)
    assert np.allclose(out["joints"][0], J0) and np.allclose(out["vertices"][0], v0)
    pose = np.zeros((2, 156))
    pose[1, :3] = [0, 0, np.pi / 2]
    tr = np.array([[0, 0, 0], [1.0, 2.0, 3.0]])
    out = m.forward(pose, tr, betas, vertices=True, chunk=1)
    Rz = R.from_rotvec([0, 0, np.pi / 2])
    assert np.allclose(out["joints"][1], Rz.apply(J0 - J0[0]) + J0[0] + tr[1])
    assert np.allclose(out["vertices"][1], Rz.apply(v0 - J0[0]) + J0[0] + tr[1])


def test_elbow_moves_only_descendants(tmp_path):
    m = _model(tmp_path)
    j = smplh.JOINT_NAMES.index("left_elbow")
    pose = np.zeros((1, 156))
    pose[0, 3 * j:3 * j + 3] = [0.0, 0.8, 0.0]
    J1 = m.forward(pose, np.zeros((1, 3)), np.zeros(10))["joints"][0]
    J0 = m.rest_joints(np.zeros(10))[1]
    desc = {j}
    for k, p in enumerate(m.parents):
        if p in desc:
            desc.add(k)
    moved = {k for k in range(52) if not np.allclose(J1[k], J0[k])}
    assert moved and moved <= desc - {j}
    assert smplh.JOINT_NAMES[20] == "left_wrist" and smplh.JOINT_NAMES[22] == "left_index1"
