"""A synthetic OMOMO_new-layout clip with a real object mesh (largebox), for tests and dry runs.

Timeline (30 fps, 240 frames): stand; right hand moves 0.25 m straight in along +x (0.5-1 s) and pushes the
box 0.3 m along +x (1-3 s); release and 0.25 m straight out along -x (3-3.5 s); both hands lift the box 0.3 m and the human walks 1 m along +x carrying it (4-6.5 s); set down.
Human faces +x, left = +y. The box is yawed so that its faces are perpendicular to the world axes (the mesh's
local frame is turned ~30 deg against its faces). Contact bodies are placed 12 mm outside the surface (near the
middle of the -x face for the pushing palm and of the side faces for the lifting hands).
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R

from h2d.common.data import omomo_new as om
from h2d.common.data.omomo_objects import load_object


def support(d, obj: str = "largebox") -> np.ndarray:
    v = load_object(obj).verts
    return v[np.argmax(v @ np.asarray(d, float))]


def face_yaw_deg(obj: str = "largebox") -> float:
    """Yaw that turns the object's footprint (minimum-area rectangle of the horizontal hull) onto the world axes."""
    xy = load_object(obj).verts[:, :2]
    h = xy[ConvexHull(xy).vertices]
    best = (np.inf, 0.0)
    for a, b in zip(h, np.roll(h, -1, 0)):
        th = np.arctan2(*(b - a)[::-1])
        u = np.array([np.cos(th), np.sin(th)])
        w = np.array([-u[1], u[0]])
        area = np.ptp(h @ u) * np.ptp(h @ w)
        best = min(best, (area, th))
    th = np.degrees(best[1]) % 90.0
    return -(th if th <= 45 else th - 90)


def face_point(d, obj: str = "largebox") -> np.ndarray:
    """Surface point near the middle of the face in direction d (the support point can sit on a bevel)."""
    m = load_object(obj)
    d = np.asarray(d, float)
    p = m.center + d * (0.5 * float(np.ptp(m.verts @ d)) + 0.05)
    return m.closest_face(p[None])[1][0]


def standing_pose() -> np.ndarray:
    P = {"Pelvis": (0, 0, 0.93), "Torso": (0, 0, 1.03), "Spine": (0, 0, 1.15), "Chest": (0, 0, 1.28),
         "Neck": (0, 0, 1.48), "Head": (0, 0, 1.60)}
    for s, y in (("L", 1.0), ("R", -1.0)):
        P.update({f"{s}_Hip": (0, 0.09 * y, 0.85), f"{s}_Knee": (0, 0.10 * y, 0.48), f"{s}_Ankle": (0, 0.10 * y, 0.08),
                  f"{s}_Toe": (0.12, 0.10 * y, 0.03), f"{s}_Thorax": (0, 0.08 * y, 1.42),
                  f"{s}_Shoulder": (0, 0.18 * y, 1.42), f"{s}_Elbow": (0, 0.20 * y, 1.15),
                  f"{s}_Wrist": (0, 0.20 * y, 0.90)})
        for fi, f in enumerate(("Index", "Middle", "Pinky", "Ring", "Thumb")):
            for k in (1, 2, 3):
                P[f"{s}_{f}{k}"] = (0.02 * (fi - 2), 0.20 * y, 0.90 - 0.03 * k)
    return np.array([P[n] for n in om.BODY_NAMES], float)


def hand_offsets(side: str) -> np.ndarray:
    base = standing_pose()
    idx = om.HAND_BODIES[side]
    return base[idx] - base[om.BODY_INDEX[f"{side}_Wrist"]]


def make_array(T: int = 240, obj: str = "largebox", push: bool = True, carry: bool = True) -> np.ndarray:
    t = np.arange(T) / 30.0
    a = np.zeros((T + 1, om.DIM), np.float32)            # + an all-zero first frame, as in the dataset
    pose = standing_pose()
    human_x = np.where(t < 4, 0.0, np.clip((t - 4) / 2.5, 0, 1) * 1.0) * carry
    rest_z = -load_object(obj).verts[:, 2].min()      # lowest point on the floor
    box = np.zeros((T, 3))
    box[:, 0] = 0.75 + np.clip((t - 1.0) / 2.0, 0, 1) * 0.30 * push + human_x
    box[:, 2] = rest_z + 0.30 * np.clip(np.minimum(t - 4.0, 6.5 - t) / 0.5, 0, 1) * carry
    q = R.from_euler("z", face_yaw_deg(obj), degrees=True)
    body = np.repeat(pose[None], T, 0)
    body[:, :, 0] += human_x[:, None]
    flags = np.zeros((T, 52))
    rpush = (t >= 1.0) & (t < 3.0) & push
    lift = (t >= 4.0) & (t < 6.5) & carry
    rh = om.HAND_BODIES["R"]
    on_face = lambda i: box[i] + q.apply(face_point(q.inv().apply([-1, 0, 0]), obj)) + [-0.012, 0, 0]  # noqa: E731
    hand = lambda p: p + hand_offsets("R") * np.array([1, 1, -1]) * 0.8              # noqa: E731
    for i in np.flatnonzero(rpush):
        # palm on the box's -x face, fingers pointing up
        body[i, rh] = hand(on_face(i))
        flags[i, rh[:4]] = 1
    if push:                                     # straight in along the inward normal (+x), straight out after
        i0, i1 = int(np.flatnonzero(rpush)[0]), int(np.flatnonzero(rpush)[-1])
        for i in np.flatnonzero((t >= 0.5) & (t < 1.0)):
            body[i, rh] = hand(on_face(i0) - [0.25 * (i0 - i) / 15, 0, 0])
        for i in np.flatnonzero((t >= 3.0) & (t < 4.0)):
            body[i, rh] = hand(on_face(i1) - [0.25 * min(1.0, (i - i1) / 15), 0, 0])
    for i in np.flatnonzero(lift):
        for side, y in (("L", 1), ("R", -1)):
            idx = om.HAND_BODIES[side]
            target = box[i] + q.apply(face_point(q.inv().apply([0, y, 0]), obj)) + np.array([0.0, y * 0.012, 0.0])
            body[i, idx] = target + hand_offsets(side) * np.array([1, 0, 1]) * 0.6
            flags[i, idx[:4]] = 1
    s = slice(1, None)
    a[s, om.SLICES["root_pos"]] = body[:, om.BODY_INDEX["Pelvis"]]
    a[s, om.SLICES["root_rot_xyzw"]] = [0, 0, 0, 1]
    a[s, om.SLICES["body_pos"]] = body.reshape(T, -1)
    a[s, om.SLICES["body_rot_xyzw"]] = np.tile([0, 0, 0, 1], 52)
    a[s, om.SLICES["obj_pos"]] = box
    a[s, om.SLICES["obj_rot_xyzw"]] = q.as_quat()
    a[s, om.SLICES["contact_body"]] = flags
    a[s, om.SLICES["contact_obj"]] = flags.any(1)[:, None]
    return a


def make_clip(name: str = "sub1_largebox_001", **kw) -> om.Clip:
    return om.parse_array(make_array(**kw), name)
