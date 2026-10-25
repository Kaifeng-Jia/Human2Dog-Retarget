"""FORCE adapter on a tiny synthetic FORCE-layout folder with the stand-in body model (no dataset needed)."""

import pickle

import numpy as np
from scipy.spatial.transform import Rotation as R

from fake_smplh import fake_smplh
from h2d.common.data import force as fo
from h2d.common.data import omomo_new as om
from h2d.common.objectmesh import ObjectMesh, load_ply

BOX_HALF = np.array([0.30, 0.175, 0.30])      # local x, y (up in FORCE), z


def box_mesh():
    s = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], float) * BOX_HALF
    quads = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
    return s, quads


def write_ply_binary(path, v, polys):
    head = ("ply\nformat binary_little_endian 1.0\nelement vertex %d\nproperty float x\nproperty float y\n"
            "property float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\n"
            "element face %d\nproperty list uchar int vertex_indices\nend_header\n" % (len(v), len(polys)))
    vt = np.zeros(len(v), dtype=[("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("r", "u1"), ("g", "u1"), ("b", "u1")])
    vt["x"], vt["y"], vt["z"] = v.T
    with open(path, "wb") as f:
        f.write(head.encode())
        f.write(vt.tobytes())
        for p in polys:
            f.write(np.uint8(len(p)).tobytes() + np.asarray(p, "<i4").tobytes())


def write_ply_ascii(path, v, polys):
    lines = ["ply", "format ascii 1.0", f"element vertex {len(v)}", "property float x", "property float y",
             "property float z", f"element face {len(polys)}", "property list uchar uint vertex_indices", "end_header"]
    lines += [" ".join(f"{c:.6f}" for c in p) for p in v] + [f"{len(p)} " + " ".join(map(str, p)) for p in polys]
    path.write_text("\n".join(lines) + "\n")


def test_ply_binary_and_ascii(tmp_path):
    v, q = box_mesh()
    write_ply_binary(tmp_path / "b.ply", v + 1.0, q)
    write_ply_ascii(tmp_path / "a.ply", v + 1.0, q)
    for name in ("b.ply", "a.ply"):
        vv, ff = load_ply(tmp_path / name)
        assert vv.shape == (8, 3) and ff.shape == (12, 3) and np.allclose(vv, v + 1.0, atol=1e-6)
    m = ObjectMesh("box", v, load_ply(tmp_path / "a.ply")[1])
    assert abs(m.area - 2 * (0.6 * 0.35 + 0.6 * 0.6 + 0.35 * 0.6)) < 1e-6
    d = m.approx_distance(np.array([[0.32, 0.0, 0.0], [0.0, 0.0, 0.0], [2.0, 0.0, 0.0]]))
    assert abs(d[0] - 0.02) < 0.006 and abs(d[1] - 0.175) < 0.006 and d[2] > 1.6


def test_yup_to_zup_and_body_mapping():
    assert np.allclose(fo.C @ [0, 1, 0], [0, 0, 1]) and np.allclose(fo.C @ [0, 0, 1], [0, -1, 0])
    names = [om.smplx_to_omomo_name(fo.JOINT_NAMES[j]) for j in fo.SMPLH_OF_BODY]
    assert names == om.BODY_NAMES


def make_force_folder(root):
    (root / "assets").mkdir(parents=True)
    (root / "annotations_final").mkdir()
    (root / "force_npz").mkdir()
    v, q = box_mesh()
    write_ply_binary(root / "assets" / fo.MESH_FILES["box_huge"], v + 5.0, q)   # scans are not centred
    with open(root / "assets" / "betas.pkl", "wb") as f:
        pickle.dump({"beta": np.zeros(10), "gender": "male"}, f)
    for k, val in {"seqs": "s1", "objs": "5", "hands": "R", "dirs": "F", "weights": "10", "success": "1"}.items():
        (root / "annotations_final" / f"{k}.txt").write_text(val + "\n")
    model = fake_smplh()
    T = 60
    trans = np.tile([0.0, 1.0, 0.0], (T, 1))
    trans[:, 2] = np.linspace(0, 0.5, T)                       # walks 0.5 m along +z (its facing) in y-up
    out = model.forward(np.zeros((1, 156)), trans[:1] - model.rest_joints(np.zeros(10))[1][0], np.zeros(10))
    tip = out["joints"][0, fo.JOINT_NAMES.index("right_middle3")]
    obj_trans = np.tile(tip + [-(BOX_HALF[0] + 0.03), 0, 0], (T, 1))   # box +x face 5 mm beyond the fingertip joint
    obj_trans[:, 2] += trans[:, 2]
    np.savez(root / "force_npz" / "s1.npz", smpl_pose=np.zeros((T, 156), np.float32),
             smpl_trans=trans.astype(np.float32), obj_pose=np.zeros((T, 3), np.float32),
             obj_trans=obj_trans.astype(np.float32))
    return model


def test_load_sequence_contacts_and_frames(tmp_path):
    model = make_force_folder(tmp_path)
    betas, gender = fo.load_betas(tmp_path)
    clip, ex = fo.load_sequence(tmp_path / "force_npz" / "s1.npz", tmp_path, model, betas)
    assert clip.n == 30 and clip.fps == 30.0 and ex.stride == 2 and clip.obj == "box_huge"
    lw, rw = clip.body_pos[0, om.BODY_INDEX["L_Wrist"]], clip.body_pos[0, om.BODY_INDEX["R_Wrist"]]
    assert lw[0] > 0.5 and rw[0] < -0.5                       # subject's left = +x is kept (no mirror)
    toe = clip.body_pos[:, om.BODY_INDEX["L_Toe"], 2]
    assert (toe > 0).all() and (toe < 0.15).all()                              # floor (lowest sole points) at z = 0
    assert clip.body_pos[-1, 0, 1] < clip.body_pos[0, 0, 1] - 0.4             # +z (y-up) -> -y (z-up)
    assert (ex.hand_min_dist[:, 1] < 0.02).all() and (ex.hand_min_dist[:, 0] > 1.0).all()
    rh = clip.contact_body[:, om.HAND_BODIES["R"]].any(1)
    lh = clip.contact_body[:, om.HAND_BODIES["L"]].any(1)
    assert rh.all() and not lh.any()
    assert np.allclose(R.from_quat(clip.obj_rot_xyzw).as_matrix(), fo.C)    # identity y-up pose -> C
    expect = (fo.C @ np.array([0.0, 1.0, 0.0])) - [0, 0, ex.floor_raw_m]     # pelvis at smpl_trans (FORCE convention)
    assert np.allclose(clip.root_pos[0], expect, atol=1e-9)
