"""Scene registration: one constant SE(2) per demonstration (spec §4 step 3).

The robot root trajectory is mapped by T(psi, b): p -> R_z(psi) p + b (xy; z unchanged), q -> R_z(psi) q. The object
trajectory is never changed.

* start-anchored (no dependence on any method's output beyond the prior's own start): the output start goes back to
  the source origin and the yaw follows the source, psi_a = yaw_src0 - yaw_out0, b_a = xy_src0 - R(psi_a) xy_out0;
* contact-fitted (main result): min over psi, b of the weighted mean of |R(psi) p_t + b - y_t|^2 over contact frames
  (p_t: the prior's contact site, y_t: the object-frame contact target in the world, both xy) plus
  lambda_psi wrap(psi - psi_a)^2. For fixed psi the best b is closed form; psi is found on a grid and refined.
  If the targets barely move, psi is not identifiable and is fixed to psi_a.
* reach point (``reach_points``): the same fit with p_t a nominal reach point fixed in the base frame instead of the
  prior's contact site (the prior's arm stays raised and is not informative);
* tracking (``track``): on top of a constant fit, a smoothed per-frame translation b_t that keeps the reach point on
  the target (the body follows the object); the robot's base path then differs from the prior by b_t - b.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.spatial.transform import Rotation as R


def wrap(a):
    return (np.asarray(a) + np.pi) % (2 * np.pi) - np.pi


def rot2(psi: float) -> np.ndarray:
    c, s = np.cos(psi), np.sin(psi)
    return np.array([[c, -s], [s, c]])


@dataclass
class SE2:
    psi: float
    b: tuple[float, float]
    kind: str = ""
    info: dict | None = None

    def apply_points(self, p: np.ndarray) -> np.ndarray:
        p = np.array(p, dtype=np.float64)
        p[..., :2] = p[..., :2] @ rot2(self.psi).T + np.asarray(self.b)
        return p

    def apply_root(self, root_pos: np.ndarray, root_rot_xyzw: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        q = (R.from_euler("z", self.psi) * R.from_quat(root_rot_xyzw)).as_quat()
        return self.apply_points(root_pos), q

    def to_dict(self) -> dict:
        d = asdict(self)
        d["psi_deg"] = float(np.degrees(self.psi))
        return d


def start_anchored(src_xy0, src_yaw0: float, out_xy0, out_yaw0: float) -> SE2:
    psi = float(wrap(src_yaw0 - out_yaw0))
    b = np.asarray(src_xy0, float)[:2] - rot2(psi) @ np.asarray(out_xy0, float)[:2]
    return SE2(psi, (float(b[0]), float(b[1])), "start_anchored")


def contact_fit(p: np.ndarray, y: np.ndarray, w: np.ndarray | None, psi_anchor: float, lambda_psi: float = 0.08,
                min_spread_m: float = 0.05, grid_deg: float = 0.25) -> SE2:
    """p, y: (n, 2+) robot contact site (prior, untransformed) and world targets over the contact frames."""
    p, y = np.asarray(p, float)[:, :2], np.asarray(y, float)[:, :2]
    w = np.ones(len(p)) if w is None else np.asarray(w, float)
    w = w / w.sum()
    pm, ym = w @ p, w @ y
    P, Y = p - pm, y - ym
    spread = float(np.sqrt(w @ np.sum(Y ** 2, 1)))

    def cost(psi):
        return float(w @ np.sum((P @ rot2(psi).T - Y) ** 2, 1)) + lambda_psi * float(wrap(psi - psi_anchor)) ** 2

    if spread < min_spread_m:
        psi, fixed = float(psi_anchor), True
    else:
        grid = np.radians(np.arange(-180.0, 180.0, grid_deg))
        c = np.array([cost(g) for g in grid])
        g0 = grid[int(np.argmin(c))]
        step = np.radians(grid_deg)
        r = minimize_scalar(cost, bounds=(g0 - step, g0 + step), method="bounded", options={"xatol": 1e-7})
        psi, fixed = float(wrap(r.x)), False
    b = ym - rot2(psi) @ pm
    res = np.linalg.norm(p @ rot2(psi).T + b - y, axis=1)
    info = {"target_spread_m": spread, "yaw_fixed_to_anchor": fixed, "lambda_psi": lambda_psi,
            "psi_minus_anchor_deg": float(np.degrees(wrap(psi - psi_anchor))),
            "residual_xy_rms_m": float(np.sqrt(w @ res ** 2)), "residual_xy_max_m": float(res.max()),
            "n_frames": int(len(p))}
    return SE2(psi, (float(b[0]), float(b[1])), "contact_fit", info)


def reach_points(root_pos: np.ndarray, root_rot_xyzw: np.ndarray, ahead_m: float) -> np.ndarray:
    """Nominal reach point per frame: ``ahead_m`` along the base heading (horizontal), at the base height."""
    yaw = R.from_quat(root_rot_xyzw).as_euler("zyx")[:, 0]
    p = np.array(root_pos, dtype=np.float64)
    p[:, 0] += ahead_m * np.cos(yaw)
    p[:, 1] += ahead_m * np.sin(yaw)
    return p


@dataclass
class SE2Track:
    """Per-frame translation and a constant or per-frame rotation (contact frames only)."""
    psi: float | np.ndarray       # () or (n,)
    b: np.ndarray                 # (n, 2)
    kind: str = "track"
    info: dict | None = None

    def apply_root_at(self, i: int, root_pos: np.ndarray, root_rot_xyzw: np.ndarray):
        psi = float(np.broadcast_to(self.psi, len(self.b))[i])
        return SE2(psi, tuple(self.b[i])).apply_root(root_pos, root_rot_xyzw)

    def to_dict(self) -> dict:
        psi = np.degrees(np.asarray(self.psi, float))
        return {"psi": float(np.radians(psi.mean())), "psi_deg": float(psi.mean()),
                "psi_range_deg": [float(psi.min()), float(psi.max())], "kind": self.kind, "info": self.info}


def track(p: np.ndarray, y: np.ndarray, base: SE2, fps: float, smooth_s: float = 1.0) -> SE2Track:
    """Per-frame translation keeping R(psi) p_t + b_t on y_t (xy), moving average over ``smooth_s``."""
    p, y = np.asarray(p, float)[:, :2], np.asarray(y, float)[:, :2]
    b = y - p @ rot2(base.psi).T
    k = max(1, int(round(smooth_s * fps)))
    k -= 1 - k % 2
    if k > 1 and len(b) > 2:
        k = min(k, len(b) - (1 - len(b) % 2))
        pad = k // 2
        bp = np.pad(b, ((pad, pad), (0, 0)), mode="edge")
        c = np.cumsum(np.vstack([np.zeros((1, 2)), bp]), axis=0)
        b = (c[k:] - c[:-k]) / k
    dev = np.linalg.norm(b - np.asarray(base.b), axis=1)
    speed = np.linalg.norm(np.diff(b, axis=0), axis=1) * fps if len(b) > 1 else np.zeros(1)
    res = np.linalg.norm(p @ rot2(base.psi).T + b - y, axis=1)
    info = {"extra_base_shift_max_m": float(dev.max()), "extra_base_speed_max_mps": float(speed.max()),
            "residual_xy_rms_m": float(np.sqrt(np.mean(res ** 2))), "residual_xy_max_m": float(res.max()),
            "smooth_s": smooth_s}
    return SE2Track(base.psi, b, "track", info)
