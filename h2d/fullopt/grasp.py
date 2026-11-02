"""Grasp tasks (fullopt spec v0.2 §2.2, §7.5): where the gripper takes the part, how it opens and closes, and how far
its jaws are inside the part. A kinematic grasp: the arm's pose and the gripper's timing, no forces.

* ``Gripper``: the jaws of a robot description (``gripper`` in configs/fullopt/robots/<robot>.yaml), from the
  model's collision meshes in the tool frame (x approach, z closing; the fixed jaw's pad at ``pad_z``, the moving jaw
  turning about its joint): the pad gap at the insertion per opening angle, and voxel signed distances of both jaws.
  MuJoCo collides meshes by their convex hulls, and the fixed jaw's hull covers the throat where the part goes, so the
  jaws are checked against the part with their own meshes.
* ``choose``: the grasp frame from the part's geometry at the human's contact (configs/fullopt/grasp.yaml): candidate
  grasps (along an edge pitched down by beta, from above, across a post), each with an approach axis a, a closing
  axis c and the jaw width along t = c x a; the part's section between the pads (``envelope``) gives its thickness w
  and the grasp point E, on the leading edge at mid-section. The human's forearm only picks the side.
* ``schedule``: the opening angle per frame: open by ``open_before_s`` before the contact, close to theta_c (the
  moving jaw's first touch on the part) at it, hold, reopen at the release, retreat, close again.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import mujoco
import numpy as np
from scipy import ndimage


def _unit(v: np.ndarray) -> np.ndarray:
    return v / max(float(np.linalg.norm(v)), 1e-12)


def _rot(axis: np.ndarray, ang: float) -> np.ndarray:
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * K @ K


def _grid_chunks(tri: np.ndarray, spacing: float):
    """Points on the triangles (barycentric grid, at most ``spacing`` apart), in chunks of bounded size."""
    e = np.linalg.norm(tri[:, [1, 2, 0]] - tri, axis=2).max(1) if len(tri) else np.zeros(0)
    ks = np.maximum(1, np.ceil(e / spacing).astype(int))
    for k in np.unique(ks):
        T = tri[ks == k]
        i, j = np.meshgrid(np.arange(k + 1), np.arange(k + 1), indexing="ij")
        m = (i + j) <= k
        u, v = i[m] / k, j[m] / k
        step = max(1, 200_000 // len(u))
        for s in range(0, len(T), step):
            B = T[s:s + step]
            yield (u[None, :, None] * B[:, None, 0] + v[None, :, None] * B[:, None, 1]
                   + (1 - u - v)[None, :, None] * B[:, None, 2]).reshape(-1, 3)


def surface_points(verts: np.ndarray, faces: np.ndarray, center=None, radius: float = np.inf,
                   spacing: float = 0.0015) -> np.ndarray:
    """Points on the mesh (at most ``spacing`` apart), within ``radius`` of ``center``."""
    tri = np.asarray(verts, float)[np.asarray(faces)]
    if center is None:
        return np.concatenate([np.zeros((0, 3)), *_grid_chunks(tri, spacing)])
    mid = tri.mean(1)                                          # triangles whose bounding sphere meets the ball
    tri = tri[np.linalg.norm(mid - center, axis=1) - np.linalg.norm(tri - mid[:, None], axis=2).max(1) < radius]
    return np.concatenate([np.zeros((0, 3))] + [P[np.linalg.norm(P - center, axis=1) < radius]
                                                for P in _grid_chunks(tri, spacing)])


def odd_line_fraction(verts: np.ndarray, faces: np.ndarray, n: int = 200, seed: int = 0) -> float:
    """Share of random lines through the bounding box that cross the surface an odd number of times (crossings within
    0.3 mm are one): about 0 for a closed solid, large for an open single sheet (a bin, a box with thin walls)."""
    T = np.asarray(verts, float)[np.asarray(faces)]
    e1, e2 = T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
    lo, hi = T.reshape(-1, 3).min(0), T.reshape(-1, 3).max(0)
    rng = np.random.default_rng(seed)
    odd = 0
    for _ in range(n):
        o, d = lo + rng.random(3) * (hi - lo), _unit(rng.normal(size=3))
        p = np.cross(d, e2)
        det = np.einsum("ij,ij->i", e1, p)
        ok = np.abs(det) > 1e-12
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        s = o - T[:, 0]
        u = np.einsum("ij,ij->i", s, p) * inv
        qv = np.cross(s, e1)
        v = (qv @ d) * inv
        t = np.einsum("ij,ij->i", e2, qv) * inv
        t = np.sort(t[ok & (u >= 0) & (v >= 0) & (u + v <= 1)])
        odd += (len(t) - int(np.sum(np.diff(t) < 3e-4))) % 2
    return odd / n


class VoxelSDF:
    """Signed distance (< 0 inside) of a closed triangle mesh on a voxel grid: the surface voxelised, filled, and
    distance-transformed both ways."""

    def __init__(self, tris: np.ndarray, pitch: float, margin: float = 0.03):
        self.p = pitch
        self.lo = tris.reshape(-1, 3).min(0) - margin
        self.shape = np.ceil((tris.reshape(-1, 3).max(0) + margin - self.lo) / pitch).astype(int) + 1
        occ, keep = np.zeros(self.shape, bool), []
        for P in _grid_chunks(tris, 0.4 * pitch):
            idx = np.floor((P - self.lo) / pitch).astype(np.int32)
            occ[idx[:, 0], idx[:, 1], idx[:, 2]] = True
            keep.append(P[::50])
        P = np.concatenate(keep)
        occ = ndimage.binary_fill_holes(occ)
        self.sdf = ((ndimage.distance_transform_edt(~occ) - ndimage.distance_transform_edt(occ)) * pitch).astype(
            np.float32)
        self.samples = P[:: max(1, len(P) // 20000)]

    def __call__(self, P: np.ndarray) -> np.ndarray:
        idx = np.floor((np.asarray(P) - self.lo) / self.p).astype(int)
        ok = ((idx >= 0) & (idx < self.shape)).all(1)
        out = np.full(len(idx), np.inf)
        out[ok] = self.sdf[idx[ok, 0], idx[ok, 1], idx[ok, 2]]
        return out


class Gripper:
    """The jaws of ``robot`` (its description's ``gripper``) with the grasp settings ``cfg`` (grasp.yaml)."""

    def __init__(self, robot, cfg: dict):
        g = robot.desc["gripper"]
        self.robot, self.cfg = robot, cfg
        self.sign, self.speed, self.max_open = float(g["open_sign"]), float(g["speed_deg_s"]), float(g["max_open_deg"])
        self.tip_x, self.pad_z, self.pad_half = float(g["tip_x"]), float(g["pad_z"]), float(g["pad_half_width"])
        self.ins = float(cfg["insertion_m"])
        m, d = robot.model, mujoco.MjData(robot.model)
        mujoco.mj_kinematics(m, d)                                    # qpos0: the gripper closed
        tool = robot.body_id(g["bodies"][0])
        Rs, ps = d.xmat[tool].reshape(3, 3), d.xpos[tool]
        tris = []
        for b in g["bodies"]:
            bid, out = robot.body_id(b), []
            for k in range(m.ngeom):
                if m.geom_bodyid[k] == bid and m.geom_type[k] == mujoco.mjtGeom.mjGEOM_MESH and m.geom_contype[k]:
                    i = m.geom_dataid[k]
                    v = m.mesh_vert[m.mesh_vertadr[i]:m.mesh_vertadr[i] + m.mesh_vertnum[i]]
                    f = m.mesh_face[m.mesh_faceadr[i]:m.mesh_faceadr[i] + m.mesh_facenum[i]]
                    out.append(((v @ d.geom_xmat[k].reshape(3, 3).T + d.geom_xpos[k] - ps) @ Rs)[f])
            tris.append(np.concatenate(out))
        j = robot._jid(g["joint"])
        self.axis, self.anchor = d.xaxis[j] @ Rs, (d.xanchor[j] - ps) @ Rs
        self.stator, self.mover = (VoxelSDF(t, float(cfg["voxel_m"])) for t in tris)
        # the pad gap at the insertion per opening angle: the moving jaw's lowest point over the inserted length
        self.deg = np.arange(0.0, self.max_open + 1e-9, 0.25)
        M, x_e = self.mover.samples, self.tip_x - self.ins
        gap = []
        for th in self.deg:
            Q = self._mover_pose(M, th)
            Q = Q[Q[:, 0] >= x_e]
            gap.append(Q[:, 2].min() - self.pad_z if len(Q) else np.inf)
        self.gap = np.maximum.accumulate(np.array(gap))
        self.jaw_half = float(max(np.abs(self.stator.samples[:, 1]).max(), np.abs(M[:, 1]).max()))
        self.gap_max = float(self.gap[np.isfinite(self.gap)].max())

    def _mover_pose(self, P: np.ndarray, deg: float) -> np.ndarray:
        """Points of the closed moving jaw (tool frame) moved to the opening ``deg``."""
        return (P - self.anchor) @ _rot(self.axis, self.sign * math.radians(deg)).T + self.anchor

    def opening_for(self, gap: float) -> float:
        """Smallest opening whose pad gap at the insertion is at least ``gap`` (the cap beyond the widest gap)."""
        if gap > self.gap_max:
            return float(self.cfg["open_max_deg"])
        return float(min(self.deg[np.searchsorted(self.gap, gap)], self.cfg["open_max_deg"]))

    def tool_point(self, w: float) -> np.ndarray:
        """r_g: between the pads at the insertion, mid-gap for a section w (tool frame)."""
        return np.array([self.tip_x - self.ins, 0.0, self.pad_z + 0.5 * w])

    def sdf(self, P_tool: np.ndarray, deg: float) -> tuple[np.ndarray, np.ndarray]:
        """Signed distances (fixed jaw, moving jaw) of tool-frame points with the gripper opened by ``deg``."""
        back = (P_tool - self.anchor) @ _rot(self.axis, self.sign * math.radians(deg)) + self.anchor
        return self.stator(P_tool), self.mover(back)

    def depth(self, P_tool: np.ndarray, deg: float) -> np.ndarray:
        """How far each point is inside a jaw (0 outside)."""
        return np.maximum(-np.minimum(*self.sdf(P_tool, deg)), 0.0)


# ------------------------------------------------------------------------------------------------- the grasp frame
@dataclass
class Frame:
    kind: str
    beta: float
    a: np.ndarray                 # approach, object frame
    c: np.ndarray                 # closing axis (fixed jaw -> moving jaw)
    t: np.ndarray                 # jaw width, c x a
    E: np.ndarray = None          # grasp point: leading edge, mid-section
    w: float = float("nan")       # the part's section between the pads
    slide: float = 0.0            # along t, past a leg or a rail
    h_rc: float = float("nan")    # world height of r_c at the contact's start
    reasons: list = field(default_factory=list)

    @property
    def feasible(self) -> bool:
        return not self.reasons


def axes(kind: str, beta: float, up: np.ndarray, n: np.ndarray, side: np.ndarray, P: np.ndarray, C: np.ndarray):
    """(a, c, t) of a candidate. ``up``: the part's up at rest; ``n``: the outward normal at the contact; ``side``:
    the human's side (elbow - contact); ``P``: surface samples near the contact."""
    e_h = _unit(n - (n @ up) * up)
    if kind in ("edge", "post"):            # square to the part's outline there, not to the palm's direction
        H = (P - C) - np.outer((P - C) @ up, up)
        near = H[(np.linalg.norm(H, axis=1) < 0.06) & (np.abs((P - C) @ up) < 0.03)]
        rim = near[near @ e_h > (near @ e_h).max(initial=0.0) - 0.01] if len(near) else near
        if len(rim) > 10:
            X = rim - rim.mean(0)
            w, v = np.linalg.eigh(X.T @ X)
            if w[-1] > 4 * w[-2]:               # a line, not a corner
                e = _unit(np.cross(v[:, -1], up))
                e_h = e if e @ e_h > 0 else -e
    if kind == "edge":
        b = math.radians(beta)
        a, c = math.cos(b) * -e_h - math.sin(b) * up, math.sin(b) * -e_h + math.cos(b) * up
    elif kind == "post":
        a = -e_h
        c = np.cross(up, a)
    else:                                  # from above: c across the lip's local direction, the fixed jaw on the
        a = -up                            # human's side
        Q = P[np.abs((P - C) @ up) < 0.03]
        H = (Q - C) - np.outer((Q - C) @ up, up)
        X = H[np.linalg.norm(H, axis=1) < 0.05]
        X = X - X.mean(0)
        c = _unit(np.cross(up, np.linalg.eigh(X.T @ X)[1][:, -1]))
        c = -c if c @ side > 0 else c
    return a, c, np.cross(c, a)


def bands(v: np.ndarray, gap: float) -> list[tuple[float, float]]:
    """Connected intervals of values (a gap wider than ``gap`` splits them)."""
    v = np.sort(v)
    cut = np.flatnonzero(np.diff(v) > gap)
    return [(float(v[i]), float(v[j])) for i, j in zip(np.r_[0, cut + 1], np.r_[cut, len(v) - 1])]


def envelope(U: np.ndarray, half_w: float, ins: float, reach: float, gap: float):
    """(lead, lo, hi) of the part in coordinates U = (along a, along t, along c) from the contact: the first material
    the jaws meet within their width, and the extent along c of the connected section through the contact over the
    insertion (another part farther than ``gap`` along c is not in it; ``reach`` bounds the first look)."""
    foot = np.abs(U[:, 1]) <= half_w
    lo, hi = -reach, reach
    for _ in range(3):
        win = foot & (U[:, 2] >= lo - 0.005) & (U[:, 2] <= hi + 0.005)
        if not win.any():
            return None
        lead = U[win, 0].min()
        sl = foot & (U[:, 0] >= lead) & (U[:, 0] <= lead + ins)
        mid = 0.5 * (lo + hi)
        lo, hi = min(bands(U[sl, 2], gap), key=lambda b: 0.0 if b[0] <= mid <= b[1] else min(abs(b[0]), abs(b[1])))
    return lead, lo, hi


def candidate(kind, beta, gr: Gripper, P, C, n, up, side, height) -> Frame:
    """One candidate grasp at contact C: its frame, section, slide, reach (``height``: object-frame point -> world
    height at the contact's start) and the reasons it is not feasible (the clearance is ``choose``'s)."""
    cfg = gr.cfg
    a, c, t = axes(kind, beta, up, n, side, P, C)
    f = Frame(kind, beta, a, c, t)
    U0 = np.c_[(P - C) @ a, (P - C) @ t, (P - C) @ c]
    env = lambda off, half: envelope(U0 - [0.0, off, 0.0], half, gr.ins, gr.gap_max + 0.01,  # noqa: E731
                                     cfg["band_gap_m"])
    step, top = cfg["slide_step_m"], cfg["slide_max_m"]
    offs = sorted(np.round(np.arange(-top, top + step / 2, step), 6) + 0.0, key=abs) if kind != "top" else [0.0]
    if env(0.0, gr.pad_half) is None:
        f.reasons.append("no part within the jaws")
        return f
    off = 0.0
    if len(offs) > 1:          # straight parts: slide until the pads and their clearance hold the part alone (off a
        wide = gr.pad_half + cfg["clearance_m"]                 # leg or a rail), the pads wholly on it
        lead0, ok = env(0.0, gr.pad_half)[0], {}
        for o in offs:
            e, e_w = env(o, gr.pad_half), env(o, wide)
            edge = np.abs(U0[:, 0] - (e[0] if e else 0.0)) < 0.005
            on = e is not None and e_w is not None and abs(e[0] - lead0) <= 0.015 and \
                (U0[edge, 1] - o).min(initial=0.0) <= -gr.pad_half + 0.005 <= gr.pad_half - 0.005 <= \
                (U0[edge, 1] - o).max(initial=0.0)
            if on:
                ok[o] = (e[2] - e[1], e_w[2] - e_w[1])
        w_part = min((w for w, _ in ok.values()), default=np.inf)
        alone = [o for o in offs if o in ok and max(ok[o]) <= min(w_part + cfg["band_gap_m"], gr.gap_max)]
        if 0.0 not in alone:
            if alone:
                off = alone[0]
            else:
                f.reasons.append("no place along the part where the jaws hold it alone")
    lead, lo, hi = env(off, gr.pad_half)
    f.w, f.slide = hi - lo, off
    f.E = C + off * t + lead * a + 0.5 * (lo + hi) * c
    r_c = f.E + gr.ins * a - (gr.pad_z + 0.5 * f.w) * c                     # (r_c - r_g in the tool frame)
    f.h_rc = float(height(r_c))
    lo_h, hi_h = cfg["reach_band_m"][int(beta) if kind != "post" else 0]
    if not lo_h <= f.h_rc <= hi_h:
        f.reasons.append(f"r_c at {f.h_rc:.2f} m, outside {lo_h:.2f}-{hi_h:.2f} m")
    if f.w > gr.gap_max:
        f.reasons.append(f"section {100 * f.w:.1f} cm wider than the jaws open ({100 * gr.gap_max:.1f} cm)")
    if abs(lead) > cfg["max_shift_m"]:
        f.reasons.append(f"leading edge {100 * lead:.1f} cm from the contact")
    return f


def to_tool(gr: Gripper, f: Frame, P: np.ndarray) -> np.ndarray:
    """Object-frame points in the tool frame of grasp ``f`` (r_g on E)."""
    Rt = np.c_[f.a, f.t, f.c]
    return (P - (f.E - Rt @ gr.tool_point(f.w))) @ Rt


@dataclass
class Grasp:
    frame: Frame
    theta_open: float
    theta_c: float                # the moving jaw's first touch closing on the part
    theta_c_gap: float            # the gap table's angle for w (a slab parallel to the pads)
    mu_need: float
    approach_depth: float         # jaws in the part on the last approach_check_m, open, the part centred
    shell: bool
    candidates: list              # every candidate's (kind, beta, w, h_rc, reasons)

    @property
    def feasible(self) -> bool:
        return self.frame.feasible


def choose(gr: Gripper, verts, faces, C, n, up, side, height, shell: bool) -> Grasp:
    """The grasp at contact C (object frame). Edges are taken at the lowest pitch that is feasible (near level, the
    pads parallel to the part's faces); between the kinds, the thinnest section wins (the pads across the part's
    thickness, not its height; least friction needed). Without a feasible candidate: the one nearest to feasible
    (at the contact and reachable first), flagged."""
    cfg = gr.cfg
    P = surface_points(verts, faces, C, cfg["surface_radius_m"], cfg["surface_spacing_m"])
    tol = 0.003 if shell else 0.002
    cands, best, kinds_done = [], None, set()
    for kind, beta in cfg["candidates"]:
        f = candidate(kind, float(beta), gr, P, C, n, up, side, height)
        depth = float("nan")
        if f.E is not None and f.w <= gr.gap_max:
            th = gr.opening_for(f.w + 2 * cfg["clearance_m"])
            Pt = to_tool(gr, f, P)
            depth = max(float(gr.depth(Pt + [s, 0.0, cfg["clearance_m"]], th).max(initial=0.0))
                        for s in cfg["approach_check_m"])
            if depth > tol:
                f.reasons.append(f"open jaws {1000 * depth:.0f} mm into the part on the approach")
        cands.append((f, depth))
        if f.feasible and kind not in kinds_done:
            kinds_done.add(kind)
            if best is None or f.w < best[0].w - 1e-6:
                best = (f, depth)
    if best is None:
        rank = lambda x: (x[0].E is None, any(r.startswith("leading") for r in x[0].reasons),  # noqa: E731
                          any(r.startswith("r_c") for r in x[0].reasons), len(x[0].reasons))
        best = min(cands, key=rank)
    f, depth = best
    if f.E is None:
        raise ValueError("no part within the jaws at the contact")
    th_open = gr.opening_for(f.w + 2 * cfg["clearance_m"])
    Pt = to_tool(gr, f, P)
    th_c = 0.0
    for th in np.arange(th_open, -1e-9, -0.5):                   # close until the moving jaw touches
        if gr.sdf(Pt, th)[1].min() < -cfg["touch_m"]:
            th_c = min(th + 0.5, th_open)
            break
    return Grasp(f, th_open, float(th_c), gr.opening_for(f.w),
                 math.tan(math.radians(th_c) / 2), depth, shell,
                 [{"kind": x.kind, "beta": x.beta, "w_m": x.w, "h_rc_m": x.h_rc, "slide_m": x.slide,
                   "reasons": x.reasons} for x, _ in cands])


# ------------------------------------------------------------------------------------------------------ the timing
def schedule(n: int, seg: tuple[int, int], fps: float, theta_open: float, theta_c: float, speed: float,
             before_s: float, out_dist: np.ndarray, reclose_m: float) -> tuple[np.ndarray, dict]:
    """Opening angle per frame [deg] and the phase frames. Open by ``before_s`` before the contact segment [s, e)
    (from the first frame if the clip starts too late), close at s, hold, reopen at e, close again once the target
    is ``reclose_m`` out (``out_dist``, per frame: the approach and retreat distance of the target)."""
    s, e = seg
    step = speed / fps
    n_open, n_close = math.ceil(theta_open / step), math.ceil(max(theta_open - theta_c, 0.0) / step)
    done = s - round(before_s * fps)
    start = done - n_open
    th = np.zeros(n)
    k = np.arange(n)
    if start < 0:
        th[:s] = theta_open
    else:
        th[:s] = np.clip((k[:s] - start) * step, 0.0, theta_open)
    th[s:e] = np.maximum(theta_c, theta_open - (k[s:e] - s + 1) * step)
    th[e:] = np.minimum(theta_open, theta_c + (k[e:] - e + 1) * step)
    released = e + n_close - 1
    far = np.flatnonzero((k > released) & (out_dist >= reclose_m))
    if len(far):
        th[far[0]:] = np.maximum(0.0, theta_open - (k[far[0]:] - far[0] + 1) * step)
    return th, {"open_start": max(start, 0), "open_done": max(done, 0), "closed": s + n_close - 1,
                "released": released, "reclose": int(far[0]) if len(far) else None, "late_start": start < 0}
