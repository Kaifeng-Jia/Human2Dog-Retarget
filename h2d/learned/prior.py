"""Learned-line prior: run X-Morph (G1 -> B2-Z1) and load its output with a source sidecar.

Spec v0.5 section 4 step 2. X-Morph is run as a subprocess from the pinned checkout
($XMORPH_ROOT, configs/external.yaml) with PYTHONPATH=$XMORPH_ROOT/src, so the checkout is
never pip-installed or modified.

Two facts handled here (both verified on the released B2-Z1 mixed checkpoint):
* The output root trajectory starts at xy = 0 (X-Morph integrates velocities), so the source
  start pose is stored in a sidecar for start-anchored registration (spec O1). GMR scales the G1's scene about the
  world origin (human_to_g1.py), so the source start is taken back to the human's scene (xy / world_scale).
* The strided-conv encoder can return a few extra frames (281 -> 284); we keep the first n_in
  frames and record the raw length.
"""

from __future__ import annotations

import json
import os
import pickle
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from h2d.paths import load_config, xmorph_root


@dataclass
class Motion:
    fps: float
    root_pos: np.ndarray       # (T, 3)
    root_rot_xyzw: np.ndarray  # (T, 4)
    dof_pos: np.ndarray        # (T, n)
    world_scale: float = 1.0   # G1 from GMR: its scene is the human's scaled by this about the world origin

    @property
    def n(self) -> int:
        return int(self.root_pos.shape[0])

    def head(self, n: int) -> "Motion":
        return Motion(self.fps, self.root_pos[:n], self.root_rot_xyzw[:n], self.dof_pos[:n], self.world_scale)


def load_motion(pkl: str | Path) -> Motion:
    with open(pkl, "rb") as f:
        d = pickle.load(f)
    return Motion(
        fps=float(d.get("fps", 30.0)),
        root_pos=np.asarray(d["root_pos"], dtype=np.float64),
        root_rot_xyzw=np.asarray(d["root_rot"], dtype=np.float64),
        dof_pos=np.asarray(d["dof_pos"], dtype=np.float64),
        world_scale=float(d.get("world_scale", 1.0)),
    )


def yaw_from_xyzw(q: np.ndarray) -> np.ndarray:
    x, y, z, w = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    return np.arctan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def xmorph_command(src_pkl: Path, out_pkl: Path, device: str, cfg: dict) -> list[str]:
    cmd = [
        sys.executable, "-m", "csmt.pipelines.infer_teacher",
        "--output-root", ".",
        "--processed-dir", cfg["processed_dir"],
        "--task-family", cfg["task_family"],
        "--pair-id", cfg["pair_id"],
        "--teacher-dir", cfg["teacher_dir"],
        "--input-pkl", str(src_pkl),
        "--output-pkl", str(out_pkl),
        "--device", device,
        "--dst-start-height-mode", cfg["dst_start_height_mode"],
        "--dst-start-height", str(cfg["dst_start_height"]),
        "--root-rotation-mode", cfg["root_rotation_mode"],
        "--no-save-src-debug",
    ]
    if cfg.get("corrector_ckpt"):
        cmd += ["--corrector-ckpt", cfg["corrector_ckpt"]]
    if cfg.get("apply_root_skate_comp"):
        cmd += ["--apply-root-skate-comp"]
    return cmd


def run_xmorph(src_pkl: str | Path, out_pkl: str | Path, device: str = "cuda:0",
               cfg: dict | None = None, log_path: str | Path | None = None) -> dict:
    """Run X-Morph teacher (+corrector) on one G1 motion file and write a sidecar.

    Returns the sidecar dict (also written to ``<out_pkl>.sidecar.json``). The motion file
    at ``out_pkl`` is truncated to the input length when configured.
    """
    cfg = cfg or load_config("learned/xmorph.yaml")
    src_pkl, out_pkl = Path(src_pkl).resolve(), Path(out_pkl).resolve()
    out_pkl.parent.mkdir(parents=True, exist_ok=True)
    root = xmorph_root()
    env = dict(os.environ)
    env["XMORPH_ROOT"] = str(root)
    env["PYTHONPATH"] = str(root / "src") + os.pathsep + env.get("PYTHONPATH", "")
    cmd = xmorph_command(src_pkl, out_pkl, device, cfg)

    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True)
    runtime = time.perf_counter() - t0
    if log_path is not None:
        Path(log_path).write_text(proc.stdout + "\n--- stderr ---\n" + proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"X-Morph failed (exit {proc.returncode}):\n{proc.stderr[-3000:]}")

    src = load_motion(src_pkl)
    out_raw = load_motion(out_pkl)
    out = out_raw
    truncated = False
    if cfg.get("truncate_to_input_length", True) and out_raw.n > src.n:
        out = out_raw.head(src.n)
        truncated = True
        with open(out_pkl, "rb") as f:
            payload = pickle.load(f)
        for k in ("root_pos", "root_rot", "dof_pos"):
            payload[k] = np.asarray(payload[k])[: src.n]
        with open(out_pkl, "wb") as f:
            pickle.dump(payload, f)

    sidecar = {
        "src_pkl": str(src_pkl),
        "src_n_frames": src.n,
        "src_fps": src.fps,
        "src_root_pos0": np.r_[src.root_pos[0, :2] / src.world_scale, src.root_pos[0, 2]].tolist(),
        "src_world_scale": src.world_scale,
        "src_yaw0": float(yaw_from_xyzw(src.root_rot_xyzw[0])),
        "out_pkl": str(out_pkl),
        "out_fps": out.fps,
        "out_n_frames_raw": out_raw.n,
        "out_n_frames": out.n,
        "truncated_to_input_length": truncated,
        "out_root_pos0": out.root_pos[0].tolist(),
        "out_yaw0": float(yaw_from_xyzw(out.root_rot_xyzw[0])),
        "device": device,
        "runtime_s": runtime,
        "xmorph_root": str(root),
        "xmorph_cfg": cfg,
        "command": " ".join(cmd[1:]),
    }
    Path(str(out_pkl) + ".sidecar.json").write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
    return sidecar
