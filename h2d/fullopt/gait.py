"""Dog gait: natural rhythm from dynamic similarity (fullopt spec §6.2-6.3).

Stride length lambda = 2.3 h Fr^0.3 (Alexander), Fr = v^2 / (g h), so one gait cycle has the natural frequency
f_nat = v / lambda = g^0.3 v^0.4 / (2.3 h^0.7). At equal speed a dog and a human therefore differ by the constant
factor (h_human / h_dog)^0.7, whatever the speed.
"""

from __future__ import annotations

import mujoco
import numpy as np

G = 9.81
FOOTFALLS_PER_CYCLE = {"walk": 4, "trot": 2}     # trot: two beats (diagonal pairs) per cycle
LEGS = ("FL", "FR", "RL", "RR")


def froude(v, h: float):
    return np.asarray(v, float) ** 2 / (G * h)


def stride_hz(v, h: float, clamp: tuple[float, float] | None = None):
    """Natural gait-cycle frequency at speed v for leg length h (one cycle = two human steps, four dog footfalls)."""
    v = np.maximum(np.asarray(v, float), 1e-6)
    f = v / (2.3 * h * froude(v, h) ** 0.3)
    return np.clip(f, *clamp) if clamp else f


def footfalls_per_step(step_hz, v, h_dog: float, gait: str = "walk"):
    """Dog footfalls (walk) or beats (trot) at its natural rhythm per measured human step, at the same speed."""
    return FOOTFALLS_PER_CYCLE[gait] * stride_hz(v, h_dog) / np.asarray(step_hz, float)


def lock_deviation(ratio, per: int = 1):
    """Relative frequency change the dog needs so that ``per`` human steps hold a whole number of footfalls.

    walk: per = 1 (n footfalls per step); trot: per = 2 (n beats per two steps).
    """
    r = np.asarray(ratio, float) * per
    n = np.maximum(np.round(r), 1)
    return n / r - 1.0


def hip_height(robot) -> dict:
    """Hip-joint height above the sole and the stance-sweep limit in the model's ``home`` pose (B2Z1Robot)."""
    m, d = robot.model, robot.data
    robot.set_qpos(m.key_qpos[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_KEY, "home")].copy())
    calf = robot._bid("FL_calf")
    r_foot = float(next(m.geom_size[g][0] for g in range(m.ngeom)
                        if m.geom_bodyid[g] == calf and m.geom_type[g] == mujoco.mjtGeom.mjGEOM_SPHERE))
    hips = np.array([d.xpos[robot._bid(f"{leg}_thigh")] for leg in LEGS])
    feet = np.array([d.xpos[robot._bid(f"{leg}_foot")] for leg in LEGS])
    thigh = float(np.linalg.norm(d.xpos[robot._bid("FL_calf")] - hips[0]))
    calf_len = float(np.linalg.norm(feet[0] - d.xpos[calf]))
    h = float(np.mean(hips[:, 2] - feet[:, 2])) + r_foot
    return {"hip_height_m": h, "thigh_m": thigh, "calf_m": calf_len, "foot_radius_m": r_foot,
            "home_base_z_m": float(d.qpos[2]), "home_feet_clearance_m": float(np.mean(feet[:, 2])) - r_foot}


def max_stride_m(leg_m: float, h: float, duty: float, reach: float = 0.9) -> float:
    """Longest stride whose stance sweep (duty x stride) keeps the hip-foot distance within ``reach`` x leg length."""
    return 2.0 * float(np.sqrt(max((reach * leg_m) ** 2 - h ** 2, 0.0))) / duty
