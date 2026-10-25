"""Matplotlib views of one OMOMO_new clip: skeleton + object mesh keyframes, timeline, optional MP4."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import animation  # noqa: E402

from h2d.common.data.describe import hand_masks  # noqa: E402
from h2d.common.data.omomo_new import BODY_INDEX, BODY_NAMES, BODY_PARENTS, NON_HAND_BODIES, Clip  # noqa: E402
from h2d.common.data.omomo_objects import ObjectMesh, tilt_and_yaw  # noqa: E402

# Categorical slots of the reference palette (fixed order) + neutral ink.
C_LEFT, C_RIGHT, C_THIRD, C_FOURTH = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
C_INK, C_MUTED, C_OBJ, C_CONTACT = "#2b2b2b", "#8a8a85", "#9a9a94", "#e34948"
SIDE = [n[0] if n[:2] in ("L_", "R_") else "" for n in BODY_NAMES]


def _limits(clip: Clip, obj: ObjectMesh, frames: np.ndarray, pad: float = 0.4):
    pts = [clip.body_pos[frames].reshape(-1, 3)]
    for t in frames[:: max(1, len(frames) // 8)]:
        pts.append(obj.world_points(clip.obj_pos[t], clip.obj_rot_xyzw[t], obj.hull_verts))
    P = np.concatenate(pts)
    lo, hi = P.min(0) - pad, P.max(0) + pad
    lo[2], hi[2] = 0.0, max(hi[2], 1.9)
    return lo, hi


def draw_frame(ax, clip: Clip, obj: ObjectMesh, t: int, sub_local: np.ndarray, lims, title: str = ""):
    ax.cla()
    w = obj.world_points(clip.obj_pos[t], clip.obj_rot_xyzw[t], sub_local)
    ax.scatter(w[:, 0], w[:, 1], w[:, 2], s=0.4, c=C_OBJ, alpha=0.35, linewidths=0, depthshade=False)
    bp = clip.body_pos[t]
    for j, pj in enumerate(BODY_PARENTS):
        if pj < 0:
            continue
        side = SIDE[j]
        col = C_LEFT if side == "L" else C_RIGHT if side == "R" else C_INK
        ax.plot(*np.stack([bp[pj], bp[j]]).T, color=col, lw=1.2)
    on = np.flatnonzero(clip.contact_body[t] == 1)
    if len(on):
        ax.scatter(*bp[on].T, s=14, c=C_CONTACT, depthshade=False, zorder=5)
    lo, hi = lims
    gx, gy = np.meshgrid([lo[0], hi[0]], [lo[1], hi[1]])
    ax.plot_surface(gx, gy, np.zeros_like(gx), color="#e9e8e3", alpha=0.35, linewidth=0)
    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect(tuple(hi - lo), zoom=1.35)
    ax.view_init(elev=18, azim=-60)
    ax.set_axis_off()
    ax.set_title(title, fontsize=8, color=C_INK)


def _timeline(axs, clip: Clip, obj: ObjectMesh, seg_rows: list[dict]):
    t = np.arange(clip.n) / clip.fps
    L, Rr = hand_masks(clip)
    body = (clip.contact_body[:, NON_HAND_BODIES] == 1).any(1)
    a0, a1, a2 = axs
    for k, (m, lab, col) in enumerate(((L, "left hand", C_LEFT), (Rr, "right hand", C_RIGHT),
                                       (body, "other body", C_FOURTH))):
        a0.fill_between(t, k + 0.1, k + 0.9, where=m, step="mid", color=col, linewidth=0)
    a0.set_yticks([0.5, 1.5, 2.5], ["left hand", "right hand", "other body"], fontsize=7)
    a0.set_ylim(0, 3)
    a0.set_title("contact flags (after flicker removal for hands)", fontsize=8, loc="left", color=C_INK)
    low = obj.lowest_z(clip.obj_pos, clip.obj_rot_xyzw)
    pel = clip.body_pos[:, BODY_INDEX["Pelvis"], :2]
    a1.plot(t, np.linalg.norm(clip.obj_pos[:, :2] - clip.obj_pos[0, :2], axis=1), color=C_LEFT, lw=1.5,
            label="object horizontal displacement")
    a1.plot(t, np.linalg.norm(pel - pel[0], axis=1), color=C_RIGHT, lw=1.5, label="human root horizontal displacement")
    a1.plot(t, low, color=C_THIRD, lw=1.5, label="object lowest point height")
    a1.set_ylabel("m", fontsize=7)
    a1.legend(fontsize=6.5, loc="upper left", frameon=False)
    tilt, yaw = tilt_and_yaw(clip.obj_rot_xyzw, 0)
    a2.plot(t, tilt, color=C_LEFT, lw=1.5, label="object tilt from start")
    a2.plot(t, yaw, color=C_RIGHT, lw=1.5, label="object yaw change from start")
    a2.set_ylabel("deg", fontsize=7)
    a2.set_xlabel("time [s]", fontsize=7)
    a2.legend(fontsize=6.5, loc="upper left", frameon=False)
    for a in axs:
        for r in seg_rows:
            a.axvspan(r["start"] / clip.fps, r["end"] / clip.fps, color="#000000", alpha=0.06, linewidth=0)
        a.tick_params(labelsize=7)
        a.grid(axis="y", color="#e4e3dd", lw=0.6)
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
    for r in seg_rows:
        a1.annotate(f"{r['hands']} / {r['object_state']} / {r['human']}", ((r["start"] + r["end"]) / 2 / clip.fps, 1.0),
                    xycoords=("data", "axes fraction"), ha="center", va="bottom", fontsize=6.5, color=C_INK)


def example_figure(clip: Clip, obj: ObjectMesh, seg_rows: list[dict], path: Path, n_keys: int = 5,
                   rng_seed: int = 0) -> None:
    rng = np.random.default_rng(rng_seed)
    sub = obj.verts[rng.choice(len(obj.verts), size=min(2500, len(obj.verts)), replace=False)]
    if seg_rows:
        r = max(seg_rows, key=lambda x: x["duration_s"])
        s, e = r["start"], r["end"]
        keys = np.linspace(max(0, s - 15), min(clip.n - 1, e + 15), n_keys).astype(int)
    else:
        keys = np.linspace(0, clip.n - 1, n_keys).astype(int)
    lims = _limits(clip, obj, np.arange(keys[0], keys[-1] + 1))
    fig = plt.figure(figsize=(16, 9))
    gs = fig.add_gridspec(4, n_keys, height_ratios=[4.2, 0.8, 1.0, 1.0], hspace=0.38, wspace=0.0,
                          left=0.07, right=0.99, top=0.95, bottom=0.06)
    for i, k in enumerate(keys):
        ax = fig.add_subplot(gs[0, i], projection="3d")
        draw_frame(ax, clip, obj, int(k), sub, lims, f"t = {k / clip.fps:.1f} s")
    axs = [fig.add_subplot(gs[1, :])]
    axs += [fig.add_subplot(gs[2, :], sharex=axs[0]), fig.add_subplot(gs[3, :], sharex=axs[0])]
    _timeline(axs, clip, obj, seg_rows)
    for k in keys:
        for a in axs:
            a.axvline(k / clip.fps, color=C_MUTED, lw=0.6, ls=":")
    fig.suptitle(f"{clip.name}  ·  {clip.n / clip.fps:.1f} s  ·  red dots = bodies flagged in contact; "
                 "shaded = hand-contact segments (label: hands / object / human)", fontsize=9, color=C_INK)
    fig.savefig(path, dpi=80)
    plt.close(fig)


def example_video(clip: Clip, obj: ObjectMesh, seg_rows: list[dict], path: Path, stride: int = 2) -> bool:
    if not animation.writers.is_available("ffmpeg"):
        return False
    sub = obj.verts[np.random.default_rng(0).choice(len(obj.verts), size=min(2500, len(obj.verts)), replace=False)]
    lims = _limits(clip, obj, np.arange(clip.n))
    fig = plt.figure(figsize=(10, 7))
    gs = fig.add_gridspec(2, 1, height_ratios=[4, 1])
    ax = fig.add_subplot(gs[0], projection="3d")
    at = fig.add_subplot(gs[1])
    L, Rr = hand_masks(clip)
    tt = np.arange(clip.n) / clip.fps
    at.fill_between(tt, 0.1, 0.9, where=L, step="mid", color=C_LEFT, linewidth=0)
    at.fill_between(tt, 1.1, 1.9, where=Rr, step="mid", color=C_RIGHT, linewidth=0)
    at.fill_between(tt, 2.1, 2.9, where=(clip.contact_body[:, NON_HAND_BODIES] == 1).any(1), step="mid",
                    color=C_FOURTH, linewidth=0)
    at.set_yticks([0.5, 1.5, 2.5], ["left hand", "right hand", "other body"], fontsize=7)
    at.set_xlabel("time [s]", fontsize=7)
    cursor = at.axvline(0, color=C_INK, lw=1)
    frames = list(range(0, clip.n, stride))

    def upd(t):
        lab = next((f"{r['hands']} / {r['object_state']} / {r['human']}" for r in seg_rows
                    if r["start"] <= t < r["end"]), "no hand contact")
        draw_frame(ax, clip, obj, t, sub, lims, f"{clip.name}  t = {t / clip.fps:.1f} s  ·  {lab}")
        cursor.set_xdata([t / clip.fps, t / clip.fps])
        return []

    anim = animation.FuncAnimation(fig, upd, frames=frames, blit=False)
    anim.save(path, writer=animation.FFMpegWriter(fps=clip.fps / stride, bitrate=1800), dpi=90)
    plt.close(fig)
    return True

