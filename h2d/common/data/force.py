"""FORCE adapter: one sequence -> the same ``Clip`` the OMOMO_new adapter produces (z-up, 52 bodies in
InterMimic order, per-body contact flags), so ``describe.py`` and the profile work unchanged.

Source: Zhang et al., "FORCE: Dataset and Method for Intuitive Physics Guided Human-object Interaction",
3DV 2025; data repository github.com/xz6014/FORCE_dataset (pinned in configs/data.yaml). The release has no
licence file: use for research only, never commit or redistribute it.

What the release contains and how it is read (checked against the authors' ``visualize_force_dataset.py``):
* ``force_npz/<seq>.npz``: ``smpl_pose`` (T, 156) SMPL-H axis-angle (root + 21 body + 30 hand joints),
  ``smpl_trans`` (T, 3), ``obj_pose`` (T, 3) axis-angle, ``obj_trans`` (T, 3). World is y-up.
* ``assets/*.ply`` object scans; the pose applies to the scan centred at its bounding-box centre.
* ``assets/betas.pkl``: one shape (10 betas, male) used by the authors for every sequence.
* Root convention: the pelvis joint is at ``smpl_trans``. The authors' visualizer builds its body layer as
  ``SMPL_Layer('male', hands=True)``, whose first positional argument is ``normalise``: vertices and joints are
  made root-relative before ``trans`` is added. Standard SMPL (pelvis at ``J_rest[0] + trans``) would put the
  body ~0.22 m too low (the SMPL-H pelvis rest height), which shows up as every object floating 0.22 m
  above the floor found from the feet. (The same call also leaves the visualizer on the neutral model; we use the
  male model that ``betas.pkl`` names.)
* ``annotations_final/*.txt``: per sequence object id, hands (L / R / B), direction, added weight [kg],
  a success code (undocumented).
Not in the release: per-frame contact labels (derived here from the skinned hand mesh and the object
surface) and the frame rate (not documented; ``SRC_FPS`` is inferred from the walking step rhythm and
checked in every profile run).
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

from h2d.common.body.smplh import JOINT_NAMES, SMPLH, load_model
from h2d.common.data.omomo_new import BODY_INDEX, BODY_NAMES, Clip, smplx_to_omomo_name
from h2d.common.objectmesh import ObjectMesh, load_ply

SRC_FPS = 60.0                 # inferred, see module docstring
OBJECTS = {"0": "backpack", "1": "plasticcontainer", "2": "suitcase", "3": "laundrybasket", "4": "chair",
           "5": "box_huge"}
MESH_FILES = {"backpack": "backpack_closed_f1000.ply", "plasticcontainer": "container_closed_f1000.ply",
              "suitcase": "suitcase_flipped.ply", "laundrybasket": "laundrybasket.ply",
              "chair": "chairblack_pushpull.ply", "box_huge": "box_huge.ply"}
YUP_TO_ZUP = R.from_euler("x", 90, degrees=True)          # (x, y, z) -> (x, -z, y)
C = YUP_TO_ZUP.as_matrix()
# InterMimic body i <- SMPL-H joint SMPLH_OF_BODY[i]
SMPLH_OF_BODY = [[smplx_to_omomo_name(j) for j in JOINT_NAMES].index(n) for n in BODY_NAMES]
FOOT_BODIES = [BODY_INDEX[n] for n in ("L_Ankle", "L_Toe", "R_Ankle", "R_Toe")]


@dataclass
class ForceExtras:
    annotation: dict
    src_fps: float
    stride: int
    floor_raw_m: float                       # floor height found from the feet before shifting to z = 0
    hand_min_dist: np.ndarray                # (T, 2) closest hand vertex to the surface [m]: exact below 0.3, else a lower bound
    contact_thr_m: float
    smplh_pose: np.ndarray = field(repr=False, default=None)   # (T, 156), for the prior input later


def annotations(root: str | Path) -> dict[str, dict]:
    root = Path(root) / "annotations_final"
    cols = {k: [ln.rstrip("\n") for ln in open(root / f"{k}.txt", encoding="utf-8")]
            for k in ("seqs", "objs", "hands", "dirs", "weights", "success")}
    out = {}
    for s, o, h, d, w, ok in zip(*cols.values()):
        out[s.strip()] = {"object": OBJECTS.get(o.strip(), f"obj{o.strip()}"), "hands": h.strip(), "dir": d.strip(),
                          "weight_kg": float(w) if w.strip() else float("nan"), "success_code": ok.strip()}
    return out


def sequences(root: str | Path) -> list[Path]:
    return sorted((Path(root) / "force_npz").glob("*.npz"))


def load_betas(root: str | Path) -> tuple[np.ndarray, str]:
    with open(Path(root) / "assets" / "betas.pkl", "rb") as f:
        d = pickle.load(f, encoding="latin1")
    return np.asarray(d["beta"], float).reshape(-1), str(d.get("gender", "male"))


@lru_cache(maxsize=None)
def load_force_object(root: str, name: str) -> ObjectMesh:
    v, f = load_ply(Path(root) / "assets" / MESH_FILES[name])
    return ObjectMesh(name, v - 0.5 * (v.max(0) + v.min(0)), f)


@lru_cache(maxsize=4)
def load_smplh(path: str) -> SMPLH:
    return load_model(path)


def smplh_path(model_root: str | Path, gender: str) -> Path:
    root = Path(model_root)
    for cand in (root / f"SMPLH_{gender}.pkl", root / "models" / f"SMPLH_{gender}.pkl",
                 root / "mano_v1_2" / "models" / f"SMPLH_{gender}.pkl", root / f"SMPLH_{gender}.npz"):
        if cand.is_file():
            return cand
    raise FileNotFoundError(f"SMPLH_{gender}.pkl not found under {root}")


def load_sequence(path: str | Path, root: str | Path, model: SMPLH, betas: np.ndarray, target_fps: float = 30.0,
                  contact_thr_m: float = 0.02, hand_vertex_stride: int = 2) -> tuple[Clip, ForceExtras]:
    path, root = Path(path), Path(root)
    ann = annotations(root).get(path.stem, {"object": None, "hands": "", "dir": "", "weight_kg": float("nan"),
                                            "success_code": ""})
    obj = load_force_object(str(root), ann["object"])
    stride = max(1, int(round(SRC_FPS / target_fps)))
    d = np.load(path)
    pose = d["smpl_pose"][::stride].astype(np.float64)
    trans = d["smpl_trans"][::stride].astype(np.float64)
    o_rot = R.from_rotvec(d["obj_pose"][::stride].astype(np.float64))
    o_pos = d["obj_trans"][::stride].astype(np.float64)
    T = len(pose)

    root_rest = model.rest_joints(betas)[1][0]
    fk = model.forward(pose, trans - root_rest, betas)                # pelvis at smpl_trans (module docstring)
    joints = fk["joints"] @ C.T                                       # (T, 52, 3) z-up, SMPL-H order
    jrot = R.from_matrix(np.einsum("ab,tjbc->tjac", C, fk["rotations"]).reshape(-1, 3, 3))
    obj_rot = YUP_TO_ZUP * o_rot
    obj_pos = o_pos @ C.T
    rot_q = obj_rot.as_quat()
    vjoint = model.vertex_joint()                                    # dominant SMPL-H joint per vertex

    def verts_at(frames, ids):                                        # skinned, z-up, floor-shifted
        v = model.skin(fk, frames, ids) @ C.T
        v[..., 2] -= floor
        return v

    foot_v = np.flatnonzero(np.isin(vjoint, [SMPLH_OF_BODY[b] for b in FOOT_BODIES]))
    floor = 0.0
    all_t = np.arange(T)
    foot_min = np.concatenate([verts_at(all_t[s:s + 256], foot_v)[..., 2].min(1) for s in range(0, T, 256)])
    floor = float(np.percentile(foot_min, 5))                        # soles touch the floor most of the time
    joints[..., 2] -= floor
    obj_pos[:, 2] -= floor

    # Derived contact: a body touches the object if one of its vertices is within contact_thr of the surface.
    # A body's vertices are only skinned and queried in frames where its joint is closer to the surface than
    # the body's rest radius + contact_thr + margin, which leaves the decision unchanged and saves most work.
    dj = obj.approx_distance(obj.to_local(joints, obj_pos, rot_q).reshape(-1, 3)).reshape(T, -1)   # (T, 52)
    v_rest, j_rest = model.rest_joints(betas)
    radius = np.zeros(model.n_joints)
    for j in range(model.n_joints):
        vs = vjoint == j
        if vs.any():
            radius[j] = np.linalg.norm(v_rest[vs] - j_rest[j], axis=1).max()
    margin = 0.05
    hand_joints = {side: [i for i, n in enumerate(JOINT_NAMES)
                          if n.startswith(side) and (n.endswith("wrist") or n[-1].isdigit())]
                   for side in ("left", "right")}
    contact_s = np.zeros((T, model.n_joints), bool)                  # SMPL-H order
    for j in sorted(set(range(model.n_joints)) - set(sum(hand_joints.values(), []))):
        vs = np.flatnonzero(vjoint == j)
        fr = np.flatnonzero(dj[:, j] < radius[j] + contact_thr_m + margin)
        if len(vs) and len(fr):
            loc = obj.to_local(verts_at(fr, vs), obj_pos[fr], rot_q[fr])
            d = obj.approx_distance(loc.reshape(-1, 3), upper=contact_thr_m).reshape(len(fr), -1)
            contact_s[fr, j] = (d < contact_thr_m).any(1)
    hand_min = np.full((T, 2), np.inf)
    for k, side in enumerate(("left", "right")):                    # hands: one query gives contact + distance
        hj = hand_joints[side]
        hv = np.flatnonzero(np.isin(vjoint, hj))[::hand_vertex_stride]   # SMPL-H hand vertices are ~5-8 mm apart
        lower = np.clip(dj[:, hj] - radius[hj], 0, None).min(1)      # joint-based bound for far frames
        hand_min[:, k] = lower
        fr = np.flatnonzero(lower < 0.3)
        for s in range(0, len(fr), 256):
            f = fr[s:s + 256]
            loc = obj.to_local(verts_at(f, hv), obj_pos[f], rot_q[f])
            d = obj.approx_distance(loc.reshape(-1, 3), upper=0.3).reshape(len(f), -1)
            hand_min[f, k] = np.minimum(d.min(1), 0.3)
            for j in hj:
                sel = vjoint[hv] == j
                if sel.any():
                    contact_s[f, j] = (d[:, sel] < contact_thr_m).any(1)
    contact = contact_s[:, SMPLH_OF_BODY].astype(np.int32)

    body_pos = joints[:, SMPLH_OF_BODY]
    body_rot = jrot.as_quat().reshape(T, 52, 4)[:, SMPLH_OF_BODY]
    clip = Clip(
        name=path.stem, subject=f"session{path.stem.split('_')[0]}", obj=ann["object"],
        root_pos=body_pos[:, 0], root_rot_xyzw=body_rot[:, 0], dof_pos=np.full((T, 153), np.nan),
        body_pos=body_pos, body_rot_xyzw=body_rot, obj_pos=obj_pos, obj_rot_xyzw=obj_rot.as_quat(),
        contact_obj=contact.any(1).astype(np.int32), contact_body=contact, dropped_first_frame=False,
        fps=SRC_FPS / stride,
    )
    return clip, ForceExtras(annotation=ann, src_fps=SRC_FPS, stride=stride, floor_raw_m=floor,
                             hand_min_dist=hand_min, contact_thr_m=contact_thr_m, smplh_pose=pose)


def step_frequency_hz(clip: Clip) -> float:
    """Dominant pelvis bob frequency (one bob per step) over the clip's walking frames, NaN if it barely walks.
    A wrong frame rate shows up as a step frequency outside the human range (~1.2-2.5 Hz)."""
    z = clip.body_pos[:, BODY_INDEX["Pelvis"], 2]
    v = np.linalg.norm(np.gradient(clip.body_pos[:, BODY_INDEX["Pelvis"], :2], axis=0), axis=1) * clip.fps
    walk = v > 0.3
    if walk.sum() < 2 * clip.fps:
        return float("nan")
    k = max(3, int(clip.fps))                                          # 1 s moving average removes posture drift
    zd = (z - np.convolve(z, np.ones(k) / k, mode="same"))[walk]
    zd = zd - zd.mean()
    F = np.abs(np.fft.rfft(zd * np.hanning(len(zd))))
    f = np.fft.rfftfreq(len(zd), d=1.0 / clip.fps)
    band = (f > 0.7) & (f < 4.0)
    return float(f[band][np.argmax(F[band])]) if band.any() else float("nan")
