#!/usr/bin/env python
"""D0: one OMOMO_new clip end to end through the learned-line prior (spec v0.5 §4 steps 1-2).

OMOMO_new clip -> contact modes and interaction descriptors (recorded skeleton + object)
               -> SMPL-X params (mean shape) -> GMR -> G1 -> X-Morph -> B2-Z1 (+ sidecar)
No object mesh, registration or arm refinement yet; this establishes the chain and gives a first look
at the human hand vs the prior's gripper.

Pass/fail per clip: chain completes; frame counts consistent; pelvis height z-up sane;
convention self-check (pelvis-relative wrist error, mean shape vs recorded) median <= 0.08 m.
The figure follows the clip's longest hand-contact segment (h2d/common/data/describe.py).
Clips are chosen explicitly, after looking at the data profile (scripts/common/profile_hoi.py).

Usage:
  python scripts/learned/d0_chain.py --run-id R00x_d0 --clips sub10_largebox_011 sub3_floorlamp_004
  python scripts/learned/d0_chain.py --run-id R00x_d0 --clips-file outputs/R00x_tasks/clips_omomo.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy.spatial.transform import Rotation as R  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from h2d.common.data.describe import describe_clip  # noqa: E402
from h2d.common.data.omomo_new import BODY_INDEX, HAND_BODIES, body_contact, hand_contact, load_clip, smplx_params  # noqa: E402
from h2d.common.data.omomo_objects import load_object  # noqa: E402
from h2d.common.robot import B2Z1Robot  # noqa: E402
from h2d.common.runinfo import ProvenanceError, add_run_args, start_run  # noqa: E402
from h2d.learned.human_to_g1 import retarget_to_g1  # noqa: E402
from h2d.learned.prior import load_motion, run_xmorph, yaw_from_xyzw  # noqa: E402
from h2d.paths import data_path  # noqa: E402

WRIST_TOL_M = 0.08


def hand_center(clip, side: str) -> np.ndarray:
    """Centroid of the finger bodies of one hand, world (T, 3)."""
    return clip.body_pos[:, HAND_BODIES[side]].mean(axis=1)


def to_object_frame(clip, p_world: np.ndarray) -> np.ndarray:
    Rinv = R.from_quat(clip.obj_rot_xyzw).inv()
    return Rinv.apply(p_world - clip.obj_pos)


def gripper_world(motion, robot: B2Z1Robot) -> np.ndarray:
    out = np.zeros((motion.n, 3))
    for t in range(motion.n):
        robot.set_qpos(robot.qpos_from_xmorph(motion.root_pos[t], motion.root_rot_xyzw[t], motion.dof_pos[t]))
        out[t] = robot.contact_site()
    return out


def run_clip(name: str, root: Path, smplx_root: Path, out: Path, device: str, robot: B2Z1Robot, ax_row) -> dict:
    clip = load_clip(root / f"{name}.pt")
    desc = describe_clip(clip, load_object(clip.obj))
    stats = desc["clip"]
    segs = desc["segments"]
    best = max(segs, key=lambda r: r["duration_s"]) if segs else None
    rec: dict = {"name": name, "object": clip.obj, "frames": clip.n, "dropped_first_frame": clip.dropped_first_frame,
                 "stats": stats}

    g1_pkl = out / f"{name}_g1.pkl"
    g1_info = retarget_to_g1(clip, smplx_params(clip), smplx_root, g1_pkl)
    rec["g1"] = g1_info
    b2_pkl = out / f"{name}_b2z1.pkl"
    side = run_xmorph(g1_pkl, b2_pkl, device=device, log_path=out / f"{name}_xmorph.log")
    rec["xmorph"] = {k: side[k] for k in ("src_n_frames", "out_n_frames_raw", "out_n_frames", "runtime_s")}

    g1, b2 = load_motion(g1_pkl), load_motion(b2_pkl)
    grip = gripper_world(b2, robot)
    hand_side = {"right": "R", "left": "L"}.get(best["hands"], "R") if best else "R"
    hc = hand_center(clip, hand_side)
    hc_obj = to_object_frame(clip, hc)
    if best:
        s, e = best["start"], best["end"]
        rec["contact_interval"] = {"hands": best["hands"], "object_state": best["object_state"],
                                   "human": best["human"], "drawn_hand": hand_side, "start": s, "end": e,
                                   "hand_height_m": [float(hc[s:e, 2].min()), float(hc[s:e, 2].max())],
                                   "gripper_height_prior_m": [float(grip[s:e, 2].min()), float(grip[s:e, 2].max())],
                                   "hand_in_object_frame_start_m": hc_obj[s].tolist()}
    g_yaw, b_yaw = np.unwrap(yaw_from_xyzw(g1.root_rot_xyzw)), np.unwrap(yaw_from_xyzw(b2.root_rot_xyzw))
    g_path = float(np.linalg.norm(np.diff(g1.root_pos[:, :2], axis=0), axis=1).sum())
    b_path = float(np.linalg.norm(np.diff(b2.root_pos[:, :2], axis=0), axis=1).sum())
    rec["prior"] = {"path_g1_m": g_path, "path_b2_m": b_path,
                    "turn_g1_deg": float(np.degrees(g_yaw[-1] - g_yaw[0])),
                    "turn_b2_deg": float(np.degrees(b_yaw[-1] - b_yaw[0])),
                    "gripper_height_range_m": [float(grip[:, 2].min()), float(grip[:, 2].max())]}

    wrist = g1_info["convention_check_pelvis_relative_wrist_error"]
    checks = {
        "frames_consistent": g1_info["frames_g1"] == clip.n and side["out_n_frames"] == g1_info["frames_g1"],
        "pelvis_z_sane": 0.6 <= stats["pelvis_stand_z_m"] <= 1.2,
        "convention_wrist_median_ok": max(w["median_m"] for w in wrist.values()) <= WRIST_TOL_M,
    }
    rec["checks"] = checks
    rec["pass"] = bool(all(checks.values()))

    # ---- figure row
    t = np.arange(clip.n) / clip.fps
    hcont = hand_contact(clip)
    ax = ax_row
    ax[0].fill_between(t, 0, hcont[:, 0], step="mid", alpha=0.5, label="left hand")
    ax[0].fill_between(t, 1.2, 1.2 + hcont[:, 1], step="mid", alpha=0.5, label="right hand")
    ax[0].fill_between(t, 2.4, 2.4 + body_contact(clip), step="mid", alpha=0.5, label="non-hand body")
    for r in segs:
        ax[0].axvspan(r["start"] / clip.fps, r["end"] / clip.fps, color="k", alpha=0.08)
    ax[0].set_yticks([])
    ax[0].set_title(f"{name}: contact flags", fontsize=9)
    ax[0].legend(fontsize=7, loc="upper right")
    ax[1].plot(hc_obj[:, 0], hc_obj[:, 1], lw=0.8, label=f"{hand_side} hand (object frame)")
    if best:
        ax[1].plot(hc_obj[s:e, 0], hc_obj[s:e, 1], lw=2.5, label="contact interval")
    ax[1].plot(0, 0, "ks", label="object origin")
    ax[1].set_aspect("equal")
    ax[1].set_title("hand path in object frame (top view) [m]", fontsize=9)
    ax[1].legend(fontsize=7)
    pel = clip.body_pos[:, BODY_INDEX["Pelvis"]]
    ax[2].plot(pel[:, 0] - pel[0, 0], pel[:, 1] - pel[0, 1], label="human pelvis")
    ax[2].plot(clip.obj_pos[:, 0] - pel[0, 0], clip.obj_pos[:, 1] - pel[0, 1], label="object")
    ax[2].plot(b2.root_pos[:, 0], b2.root_pos[:, 1], label="B2 base (X-Morph, own origin)")
    ax[2].set_aspect("equal")
    ax[2].set_title("paths from the human start [m]", fontsize=9)
    ax[2].legend(fontsize=7)
    ax[3].plot(t, hc[:, 2], label=f"human {hand_side} hand height")
    ax[3].plot(t, grip[:, 2], label="Z1 contact site height (prior)")
    ax[3].plot(t, clip.obj_pos[:, 2], label="object origin height")
    if best:
        ax[3].axvspan(s / clip.fps, e / clip.fps, color="k", alpha=0.08)
    ax[3].set_xlabel("time [s]")
    ax[3].set_title("heights [m]", fontsize=9)
    ax[3].legend(fontsize=7)
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    add_run_args(ap)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--clips", nargs="+")
    g.add_argument("--clips-file", help="text file, one clip name per line (e.g. prepare_tasks.py clips_omomo.txt)")
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--root", default=None)
    args = ap.parse_args()
    try:
        prov = start_run(args.run_id, needs=("xmorph", "gmr", "hoi_retarget"),
                         configs=("b2z1.yaml", "external.yaml", "learned/xmorph.yaml", "data.yaml"),
                         allow_dirty=args.allow_dirty, allow_external_mismatch=args.allow_external_mismatch)
    except ProvenanceError as e:
        print(f"[refused] {e}", file=sys.stderr)
        return 2
    names = list(args.clips) if args.clips else [ln.strip() for ln in Path(args.clips_file).read_text().splitlines()
                                                    if ln.strip()]
    root = Path(args.root).expanduser() if args.root else data_path("omomo_new")
    smplx_root = data_path("smplx_models")
    out = Path(args.out or f"outputs/{args.run_id}")
    out.mkdir(parents=True, exist_ok=True)

    robot = B2Z1Robot()
    fig, axes = plt.subplots(len(names), 4, figsize=(20, 3.8 * len(names)), squeeze=False)
    results = {"provenance": prov, "device": args.device, "smplx_root": str(smplx_root), "clips": {}}
    for i, name in enumerate(names):
        try:
            results["clips"][name] = run_clip(name, root, smplx_root, out, args.device, robot, axes[i])
        except Exception as e:  # noqa: BLE001 - report and continue
            import traceback

            results["clips"][name] = {"name": name, "pass": False, "error": traceback.format_exc()[-3000:]}
            print(f"[error] {name}: {e}", file=sys.stderr)
    fig.tight_layout()
    fig.savefig(out / "d0_chain.png", dpi=100)
    results["pass"] = all(r.get("pass") for r in results["clips"].values())
    (out / "summary.json").write_text(json.dumps(results, indent=2, default=float), encoding="utf-8")

    lines = [
        "# D0 chain: OMOMO_new -> GMR -> G1 -> X-Morph -> B2-Z1",
        "",
        f"Run `{prov['run_id']}` · code `{prov['git']['describe']}` (dirty={prov['git']['dirty']}) · device `{args.device}`",
        "",
        "| clip | frames | longest contact (hands, object, s) | wrist err median L/R [m] | hand height in contact [m] | Z1 site height (prior) in contact [m] | path G1/B2 [m] | turn G1/B2 [deg] | pass |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for name, r in results["clips"].items():
        if "error" in r:
            lines.append(f"| {name} | error (see summary.json) | | | | | | | False |")
            continue
        w = r["g1"]["convention_check_pelvis_relative_wrist_error"]
        ci = r.get("contact_interval", {})
        dur = (ci["end"] - ci["start"]) / 30.0 if ci else 0
        fmt = lambda v: f"{v[0]:.2f}–{v[1]:.2f}" if v else "–"  # noqa: E731
        lines.append(
            f"| {name} | {r['frames']} | {ci.get('hands', '–')}, {ci.get('object_state', '–')}, {dur:.1f} | {w['left_wrist']['median_m']:.3f} / "
            f"{w['right_wrist']['median_m']:.3f} | {fmt(ci.get('hand_height_m'))} | {fmt(ci.get('gripper_height_prior_m'))} | "
            f"{r['prior']['path_g1_m']:.2f} / {r['prior']['path_b2_m']:.2f} | {r['prior']['turn_g1_deg']:.0f} / "
            f"{r['prior']['turn_b2_deg']:.0f} | {r['pass']} |"
        )
    lines += ["", "![d0](d0_chain.png)", ""]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[4:-2]))
    return 0 if results["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
