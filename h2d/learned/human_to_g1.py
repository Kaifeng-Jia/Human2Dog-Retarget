"""Human (SMPL-X params) -> G1 with GMR at the pinned commit; writes an X-Morph-ready G1 motion file.

GMR's own loaders are used unchanged (load_smplx_file / get_smplx_data_offline_fast / retarget with
offset_to_ground=True), so the G1 files match what X-Morph's training data was built from.

Two facts about where the G1 ends up:

* SMPL-X adds its rest pelvis joint to ``trans`` unrotated, so ``trans`` is the recorded pelvis minus that joint
  (otherwise the human reaches GMR 0.35 m off along world -y);
* GMR scales the whole scene about the world origin by its pelvis scale (0.83 for the mean shape), which keeps the
  feet planted but leaves the G1 at 0.83 x the human's position next to an unscaled object. The scale is saved as
  ``world_scale``: the G1 shares a scene with the object scaled by it.

X-Morph sees neither: it reads joint angles, the root velocity in the heading frame and the turn rate, and
integrates its output from the origin (prior.py); the dog's placement comes from the human and the object.
"""

from __future__ import annotations

import pickle
import time
from pathlib import Path

import numpy as np

from h2d.common.data.omomo_new import BODY_INDEX, Clip

# SMPL-X joint indices (smplx.joint_names.JOINT_NAMES)
SMPLX_PELVIS, SMPLX_L_WRIST, SMPLX_R_WRIST = 0, 20, 21


def write_smplx_npz(params: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, **params)
    return path


def pelvis_rest(smplx_root: Path, gender: str) -> np.ndarray:
    """SMPL-X pelvis joint at zero pose, zero translation and mean shape."""
    import smplx

    return smplx.create(str(smplx_root), "smplx", gender=gender, use_pca=False)().joints[0, 0].detach().numpy()


def retarget_to_g1(clip: Clip, params: dict, smplx_root: Path, out_pkl: Path) -> dict:
    """Run GMR SMPL-X -> unitree_g1 and save {fps, root_pos, root_rot (xyzw), dof_pos, world_scale}.

    Returns info incl. two self-checks against the recorded skeleton: the SMPL-X pelvis (absolute) and the
    pelvis-relative wrist positions of the mean-shape reconstruction. Shape alone gives a few cm at the wrists; a
    wrong body-frame convention gives tens of cm.
    """
    from general_motion_retargeting import GeneralMotionRetargeting as GMR
    from general_motion_retargeting.utils.smpl import get_smplx_data_offline_fast, load_smplx_file

    params = {**params, "trans": (params["trans"] - pelvis_rest(smplx_root, str(params["gender"]))).astype(np.float32)}
    npz = write_smplx_npz(params, out_pkl.with_name(out_pkl.stem + "_smplx.npz"))
    smplx_data, body_model, smplx_output, height = load_smplx_file(str(npz), str(smplx_root))
    frames, fps = get_smplx_data_offline_fast(smplx_data, body_model, smplx_output, tgt_fps=30)

    t0 = time.perf_counter()
    gmr = GMR(actual_human_height=height, src_human="smplx", tgt_robot="unitree_g1")
    qs = np.array([gmr.retarget(f, offset_to_ground=True) for f in frames])
    runtime = time.perf_counter() - t0

    motion = {
        "fps": float(fps),
        "root_pos": qs[:, :3],
        "root_rot": qs[:, 3:7][:, [1, 2, 3, 0]],   # wxyz -> xyzw (as GMR's own saver)
        "dof_pos": qs[:, 7:],
        "world_scale": float(gmr.human_scale_table[gmr.human_root_name]),
        "local_body_pos": None,
        "link_body_list": None,
    }
    out_pkl.parent.mkdir(parents=True, exist_ok=True)
    with open(out_pkl, "wb") as f:
        pickle.dump(motion, f)

    joints = smplx_output.joints.detach().cpu().numpy()   # (T, J, 3), mean shape
    rec = clip.body_pos
    n = min(len(joints), clip.n)
    err = {}
    for name, js, jr in (("left_wrist", SMPLX_L_WRIST, BODY_INDEX["L_Wrist"]),
                         ("right_wrist", SMPLX_R_WRIST, BODY_INDEX["R_Wrist"])):
        a = joints[:n, js] - joints[:n, SMPLX_PELVIS]
        b = rec[:n, jr] - rec[:n, BODY_INDEX["Pelvis"]]
        e = np.linalg.norm(a - b, axis=1)
        err[name] = {"median_m": float(np.median(e)), "p95_m": float(np.percentile(e, 95))}
    pelvis_offset = joints[:n, SMPLX_PELVIS] - rec[:n, BODY_INDEX["Pelvis"]]
    return {
        "g1_pkl": str(out_pkl),
        "smplx_npz": str(npz),
        "frames_in": clip.n,
        "frames_g1": int(len(qs)),
        "fps": float(fps),
        "human_height_used_m": float(height),
        "world_scale": motion["world_scale"],
        "gmr_runtime_s": runtime,
        "convention_check_pelvis_relative_wrist_error": err,
        "pelvis_offset_smplx_minus_recorded_median_m": np.median(pelvis_offset, axis=0).tolist(),
    }
