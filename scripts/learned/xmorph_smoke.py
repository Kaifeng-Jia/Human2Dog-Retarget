#!/usr/bin/env python
"""X-Morph prior smoke test: run G1 -> B2-Z1 inference and check the output.

For each input G1 clip (default: two clips shipped with X-Morph) this checks:
  * X-Morph exits cleanly on the requested device; runtime.
  * output length (raw and after truncation to the input length), finiteness,
    quaternion norms, joint-limit violations against the MuJoCo model.
  * pipeline time alignment (pass/fail): lag (frames) maximizing the correlation between G1 and
    B2-Z1 root horizontal speeds, which X-Morph's velocity matching ties together; |lag| <= 2.
  * X-Morph behaviour (recorded, not pass/fail): arm timing lag between the G1 right hand
    (rel. pelvis) and the Z1 contact site (rel. base); path-length ratio; heading drift.
Writes outputs/<run-id>/{summary.json, report.md, xmorph_smoke.png, <clip>_b2z1.pkl(+sidecar), logs}.

Usage:
  python scripts/learned/xmorph_smoke.py --run-id R002_xmorph_smoke --device cuda:0
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mujoco  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from h2d.common.robot import B2Z1Robot, xyzw_to_wxyz  # noqa: E402
from h2d.common.runinfo import ProvenanceError, add_run_args, start_run  # noqa: E402
from h2d.learned.prior import load_motion, run_xmorph, yaw_from_xyzw  # noqa: E402
from h2d.paths import xmorph_root  # noqa: E402

DEFAULT_CLIPS = [
    "data/raw/g1/manip_slow/General_A5_-_Pick_Up_Box_stageii.pkl",
    "data/raw/g1/manip_slow/B20_-__Walk_with_box_stageii.pkl",
]
G1_XML = "assets/robots/unitree_g1/g1_mocap_29dof.xml"
MAX_LAG = 15


def g1_hand_local(motion, model: mujoco.MjModel) -> np.ndarray:
    """Right-hand position in the pelvis frame for each frame (T, 3)."""
    d = mujoco.MjData(model)
    hand = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "right_rubber_hand")
    pelvis = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "pelvis")
    out = np.zeros((motion.n, 3))
    for t in range(motion.n):
        d.qpos[0:3] = motion.root_pos[t]
        d.qpos[3:7] = xyzw_to_wxyz(motion.root_rot_xyzw[t])
        d.qpos[7:7 + motion.dof_pos.shape[1]] = motion.dof_pos[t]
        mujoco.mj_kinematics(model, d)
        R = d.xmat[pelvis].reshape(3, 3)
        out[t] = R.T @ (d.xpos[hand] - d.xpos[pelvis])
    return out


def b2_contact_local(motion, robot: B2Z1Robot) -> tuple[np.ndarray, np.ndarray]:
    """Contact-site position in the base frame and world, per frame."""
    base = robot._bid("base_link")
    loc, world = np.zeros((motion.n, 3)), np.zeros((motion.n, 3))
    for t in range(motion.n):
        robot.set_qpos(robot.qpos_from_xmorph(motion.root_pos[t], motion.root_rot_xyzw[t], motion.dof_pos[t]))
        p = robot.contact_site()
        R = robot.data.xmat[base].reshape(3, 3)
        world[t] = p
        loc[t] = R.T @ (p - robot.data.xpos[base])
    return loc, world


def speed(x: np.ndarray, fps: float) -> np.ndarray:
    v = np.gradient(x, 1.0 / fps, axis=0)
    return np.linalg.norm(v, axis=1)


def best_lag(a: np.ndarray, b: np.ndarray, max_lag: int = MAX_LAG) -> tuple[int | None, float | None]:
    """Lag k maximizing corr(a[t], b[t+k]); None when a signal is ~constant."""
    if a.std() < 1e-3 or b.std() < 1e-3:
        return None, None
    a = (a - a.mean()) / a.std()
    b = (b - b.mean()) / b.std()
    best, best_c = 0, -np.inf
    for k in range(-max_lag, max_lag + 1):
        if k >= 0:
            x, y = a[: len(a) - k], b[k:]
        else:
            x, y = a[-k:], b[: len(b) + k]
        c = float(np.mean(x * y))
        if c > best_c:
            best, best_c = k, c
    return best, best_c


def main() -> int:
    ap = argparse.ArgumentParser()
    add_run_args(ap)
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--clips", nargs="*", default=DEFAULT_CLIPS, help="G1 pkl paths (relative to XMORPH_ROOT ok)")
    args = ap.parse_args()
    try:
        prov = start_run(args.run_id, needs=("xmorph",), configs=("b2z1.yaml", "external.yaml", "learned/xmorph.yaml"),
                         allow_dirty=args.allow_dirty, allow_external_mismatch=args.allow_external_mismatch)
    except ProvenanceError as e:
        print(f"[refused] {e}", file=sys.stderr)
        return 2
    out = Path(args.out or f"outputs/{args.run_id}")
    out.mkdir(parents=True, exist_ok=True)

    xr = xmorph_root()
    robot = B2Z1Robot()
    g1 = mujoco.MjModel.from_xml_path(str(xr / G1_XML))
    results = {"provenance": prov, "device": args.device, "clips": {}}
    fig, axes = plt.subplots(len(args.clips), 3, figsize=(14, 3.6 * len(args.clips)), squeeze=False)

    all_pass = True
    for i, clip in enumerate(args.clips):
        src = Path(clip) if Path(clip).is_absolute() else xr / clip
        name = src.stem
        out_pkl = out / f"{name}_b2z1.pkl"
        rec: dict = {"src": str(src)}
        try:
            side = run_xmorph(src, out_pkl, device=args.device, log_path=out / f"{name}_xmorph.log")
        except Exception as e:  # noqa: BLE001 - report every failure in the summary
            rec["error"] = str(e)[-2000:]
            rec["pass"] = False
            results["clips"][name] = rec
            all_pass = False
            continue
        g = load_motion(src)
        b = load_motion(out_pkl)
        rec.update({k: side[k] for k in ("src_n_frames", "out_n_frames_raw", "out_n_frames",
                                          "truncated_to_input_length", "runtime_s", "out_root_pos0",
                                          "src_root_pos0", "src_yaw0", "out_yaw0")})
        finite = bool(np.isfinite(b.root_pos).all() and np.isfinite(b.root_rot_xyzw).all() and np.isfinite(b.dof_pos).all())
        qn = np.abs(np.linalg.norm(b.root_rot_xyzw, axis=1) - 1.0).max()
        lo, hi = robot.joint_lower, robot.joint_upper
        viol = np.maximum(lo - b.dof_pos, b.dof_pos - hi)
        viol_frames = (viol > 1e-3).sum(axis=0)
        hand_loc = g1_hand_local(g, g1)
        grip_loc, grip_world = b2_contact_local(b, robot)
        lag_arm, c_arm = best_lag(speed(hand_loc, g.fps), speed(grip_loc, b.fps))
        g_root_v = speed(g.root_pos[:, :2], g.fps)
        b_root_v = speed(b.root_pos[:, :2], b.fps)
        lag_root, c_root = best_lag(g_root_v, b_root_v)
        g_yaw = np.unwrap(yaw_from_xyzw(g.root_rot_xyzw))
        b_yaw = np.unwrap(yaw_from_xyzw(b.root_rot_xyzw))
        g_path = float(np.sum(np.linalg.norm(np.diff(g.root_pos[:, :2], axis=0), axis=1)))
        b_path = float(np.sum(np.linalg.norm(np.diff(b.root_pos[:, :2], axis=0), axis=1)))
        rec.update({
            "finite": finite,
            "max_quat_norm_error": float(qn),
            "joint_limit_violation_frames": {robot.joint_order[j]: int(viol_frames[j]) for j in range(len(lo)) if viol_frames[j]},
            "max_joint_limit_violation_rad": float(max(0.0, viol.max())),
            "base_height_range_m": [float(b.root_pos[:, 2].min()), float(b.root_pos[:, 2].max())],
            "contact_site_height_range_m": [float(grip_world[:, 2].min()), float(grip_world[:, 2].max())],
            "lag_arm_frames": lag_arm, "corr_arm": c_arm,
            "lag_root_frames": lag_root, "corr_root": c_root,
            "g1_root_path_len_m": g_path,
            "b2_root_path_len_m": b_path,
            "path_length_ratio_b2_over_g1": b_path / g_path if g_path > 1e-6 else None,
            "g1_total_turn_deg": float(np.degrees(g_yaw[-1] - g_yaw[0])),
            "b2_total_turn_deg": float(np.degrees(b_yaw[-1] - b_yaw[0])),
            "heading_drift_deg": float(np.degrees((b_yaw[-1] - b_yaw[0]) - (g_yaw[-1] - g_yaw[0]))),
        })
        ok = (finite and qn < 1e-4 and side["out_n_frames"] == side["src_n_frames"]
              and (lag_root is None or abs(lag_root) <= 2))
        rec["pass"] = bool(ok)
        all_pass &= ok
        results["clips"][name] = rec

        t_g = np.arange(g.n) / g.fps
        ax = axes[i]
        ax[0].plot(g.root_pos[:, 0] - g.root_pos[0, 0], g.root_pos[:, 1] - g.root_pos[0, 1], label="G1 (from its start)")
        ax[0].plot(b.root_pos[:, 0], b.root_pos[:, 1], label="B2-Z1 (X-Morph)")
        ax[0].set_aspect("equal")
        ax[0].set_title(f"{name}: root path [m]", fontsize=9)
        ax[0].legend(fontsize=7)
        ax[1].plot(t_g, g_root_v, label="G1 root speed")
        ax[1].plot(t_g, b_root_v, label="B2 root speed")
        ax[1].set_title(f"root xy speed [m/s] (lag {lag_root})", fontsize=9)
        ax[1].legend(fontsize=7)
        ax[2].plot(t_g, speed(hand_loc, g.fps), label="G1 right hand rel. pelvis")
        ax[2].plot(t_g, speed(grip_loc, b.fps), label="Z1 contact site rel. base")
        ax[2].set_title(f"arm speed [m/s] (lag {lag_arm})", fontsize=9)
        ax[2].legend(fontsize=7)
        for a in ax[1:]:
            a.set_xlabel("time [s]")
    fig.tight_layout()
    fig.savefig(out / "xmorph_smoke.png", dpi=120)

    results["pass"] = bool(all_pass)
    (out / "summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    lines = [
        "# X-Morph prior smoke test",
        "",
        f"Run `{prov['run_id']}` · code `{prov['git']['describe']}` (dirty={prov['git']['dirty']}) · "
        f"X-Morph match={prov['externals']['xmorph'].get('match')} · device `{args.device}` · "
        f"torch {prov['packages'].get('torch')} cuda={prov['packages'].get('cuda_available')} · mujoco {prov['packages'].get('mujoco')}",
        "",
        "Pass/fail uses length, finiteness, quaternions and the root-speed lag (pipeline alignment). "
        "Arm lag, path ratio and heading drift describe X-Morph itself and are recorded only.",
        "",
        "| clip | frames in / raw out / kept | runtime [s] | quat err | joint-limit viol. [rad] | lag root (corr) | "
        "arm lag, info (corr) | path G1 / B2 [m] | turn G1 / B2 [deg] | pass |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, r in results["clips"].items():
        if "error" in r:
            lines.append(f"| {name} | error | | | | | | | | False |")
            continue
        fmt = lambda k, c: "n/a" if r[k] is None else f"{r[k]} ({r[c]:.2f})"  # noqa: E731
        lines.append(
            f"| {name} | {r['src_n_frames']} / {r['out_n_frames_raw']} / {r['out_n_frames']} | {r['runtime_s']:.1f} | "
            f"{r['max_quat_norm_error']:.1e} | {r['max_joint_limit_violation_rad']:.3f} | {fmt('lag_root_frames', 'corr_root')} | "
            f"{fmt('lag_arm_frames', 'corr_arm')} | {r['g1_root_path_len_m']:.2f} / {r['b2_root_path_len_m']:.2f} | "
            f"{r['g1_total_turn_deg']:.0f} / {r['b2_total_turn_deg']:.0f} | {r['pass']} |"
        )
    lines += ["", "![smoke](xmorph_smoke.png)", ""]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[4:-2]))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
