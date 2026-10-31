"""Matplotlib views of one clip (OMOMO_new layout): skeleton + object mesh keyframes, timeline, optional MP4;
a push-candidate sheet (``candidate_figure``) and a candidate overview (``gallery``)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import animation  # noqa: E402
from scipy.spatial import ConvexHull  # noqa: E402
from scipy.spatial.transform import Rotation as R  # noqa: E402

from h2d.common.data.describe import alignment_series, contact_point, hand_masks, palm_point  # noqa: E402
from h2d.common.data.omomo_new import BODY_INDEX, BODY_NAMES, BODY_PARENTS, NON_HAND_BODIES, Clip  # noqa: E402
from h2d.common.data.omomo_objects import ObjectMesh  # noqa: E402

# Categorical slots of the reference palette (fixed order) + neutral ink.
C_LEFT, C_RIGHT, C_THIRD, C_FOURTH = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
C_INK, C_MUTED, C_OBJ, C_CONTACT = "#2b2b2b", "#8a8a85", "#9a9a94", "#e34948"
SIDE = [n[0] if n[:2] in ("L_", "R_") else "" for n in BODY_NAMES]


def _subsample(obj: ObjectMesh, n: int = 2500, seed: int = 0) -> np.ndarray:
    pts = obj._samples()[0]                                  # surface samples (coarse meshes have few vertices)
    return pts[np.random.default_rng(seed).choice(len(pts), size=min(n, len(pts)), replace=False)]


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



def example_video(clip: Clip, obj: ObjectMesh, seg_rows: list[dict], path: Path, stride: int = 2) -> bool:
    if not animation.writers.is_available("ffmpeg"):
        return False
    sub = _subsample(obj)
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


# ------------------------------------------------------------------------------ push candidates
def _clean_axes(a, grid_axis="y"):
    a.tick_params(labelsize=7)
    if grid_axis:
        a.grid(axis=grid_axis, color="#e4e3dd", lw=0.6)
    for sp in ("top", "right"):
        a.spines[sp].set_visible(False)


def _fmt(v, nd=1, unit=""):
    return "–" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.{nd}f}{unit}"


def _keyframes(clip: Clip, cand: dict) -> list[tuple[int, str]]:
    s, e, fps = int(cand["start"]), int(cand["end"]), clip.fps
    a_t, r_t = cand.get("approach_time_s"), cand.get("retreat_time_s")
    a = s - round(a_t * fps) if a_t is not None and not np.isnan(a_t) else max(0, s - int(0.5 * fps))
    r = e - 1 + round(r_t * fps) if r_t is not None and not np.isnan(r_t) else min(clip.n - 1, e - 1 + int(0.5 * fps))
    keys = [(a, "approach"), (s, "first contact"), ((s + e - 1) // 2, "middle"), (e - 1, "last contact"), (r, "retreat")]
    out, seen = [], set()
    for k, lab in keys:
        k = int(np.clip(k, 0, clip.n - 1))
        if k not in seen:
            seen.add(k)
            out.append((k, lab))
    return out


def _face_basis(n_w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    u = np.cross([0.0, 0.0, 1.0], n_w)
    if np.linalg.norm(u) < 0.2:                                # top / bottom face: use world x
        u = np.array([1.0, 0.0, 0.0]) - n_w * n_w[0]
    u /= np.linalg.norm(u)
    return u, np.cross(n_w, u)


def candidate_figure(clip: Clip, obj: ObjectMesh, cand: dict, path: Path, side: str = "R", title: str = "",
                     criteria: list[dict] | None = None) -> None:
    """One sheet per candidate segment: keyframes with the contact proxy and the patch normal; top view of the
    object, root and palm paths; the contact on the object seen from the hand and from the side (object frame at
    first contact, with the palm's approach and retreat paths); timeline of contacts, object speed and push
    alignment; the numbers behind the selection."""
    s, e, fps = int(cand["start"]), int(cand["end"]), clip.fps
    n_loc = np.asarray(cand["normal_local"], float)
    keys = _keyframes(clip, cand)
    w0, w1 = max(0, s - int(2 * fps)), min(clip.n, e + int(1.5 * fps))
    win = np.arange(w0, w1)
    sub = _subsample(obj)
    lims = _limits(clip, obj, np.arange(keys[0][0], keys[-1][0] + 1))
    fig = plt.figure(figsize=(17, 12.5))
    gs = fig.add_gridspec(3, 1, height_ratios=[3.6, 3.4, 2.6], hspace=0.22, left=0.05, right=0.99, top=0.94,
                          bottom=0.05)
    g0 = gs[0].subgridspec(1, len(keys), wspace=0.0)
    for i, (k, lab) in enumerate(keys):
        ax = fig.add_subplot(g0[0, i], projection="3d")
        draw_frame(ax, clip, obj, k, sub, lims, f"{lab}  ·  t = {k / fps:.2f} s")
        c = contact_point(clip, side, slice(k, k + 1))[0] if s <= k < e else palm_point(clip, side, [k])[0]
        nw = R.from_quat(clip.obj_rot_xyzw[k]).apply(n_loc)
        ax.scatter(*c, s=60, marker="*", c=C_THIRD, depthshade=False, zorder=6)
        ax.quiver(*c, *(-nw), length=0.3, color=C_THIRD, lw=1.5, arrow_length_ratio=0.25)

    g1 = gs[1].subgridspec(1, 4, wspace=0.28, width_ratios=[1.15, 1, 1, 0.95])
    # ---- top view
    a = fig.add_subplot(g1[0, 0])
    for t, col, lab in ((s, C_MUTED, "object at first contact"), (e - 1, C_INK, "object at last contact")):
        xy = obj.world_points(clip.obj_pos[t], clip.obj_rot_xyzw[t], obj.hull_verts)[:, :2]
        h = xy[ConvexHull(xy).vertices]
        a.fill(h[:, 0], h[:, 1], facecolor="none", edgecolor=col, lw=1.2, label=lab)
    cen = R.from_quat(clip.obj_rot_xyzw[win]).apply(obj.center) + clip.obj_pos[win]
    seg = (win >= s) & (win < e)
    pel = clip.body_pos[win, BODY_INDEX["Pelvis"], :2]
    palm = palm_point(clip, side, win)
    a.plot(cen[:, 0], cen[:, 1], color=C_LEFT, lw=0.8, ls=":")
    a.plot(cen[seg, 0], cen[seg, 1], color=C_LEFT, lw=2.0, label="object centre")
    a.plot(pel[:, 0], pel[:, 1], color=C_INK, lw=0.8, ls="--", label="human root (window)")
    a.plot(palm[:, 0], palm[:, 1], color=C_RIGHT, lw=0.8, ls=":")
    a.plot(palm[seg, 0], palm[seg, 1], color=C_RIGHT, lw=2.0, label={"R": "right palm", "L": "left palm", "B": "palm midpoint"}[side])
    nw0 = R.from_quat(clip.obj_rot_xyzw[s]).apply(n_loc)
    c0 = contact_point(clip, side, slice(s, s + 1))[0]
    a.annotate("", xy=(c0[0] - 0.25 * nw0[0], c0[1] - 0.25 * nw0[1]), xytext=(c0[0], c0[1]),
               arrowprops={"arrowstyle": "-|>", "color": C_THIRD, "lw": 1.5})
    a.set_aspect("equal", adjustable="datalim")
    a.set_title(f"top view, t = {w0 / fps:.1f}–{w1 / fps:.1f} s (thick = in contact; green = into the face)",
                fontsize=8, loc="left")
    a.legend(fontsize=6.5, frameon=False, loc="best")
    a.set_xlabel("x [m]", fontsize=7)
    a.set_ylabel("y [m]", fontsize=7)
    _clean_axes(a, "both")
    # ---- contact on the object, object frame at first contact
    P = obj.world_points(clip.obj_pos[s], clip.obj_rot_xyzw[s], sub)
    cs = clip.obj_pos[s] + R.from_quat(clip.obj_rot_xyzw[s]).apply(obj.center)
    u, v = _face_basis(nw0)

    def to_s(pts_world, frames):          # world points at their own frames -> world at the object pose of frame s
        loc = obj.to_local(pts_world[:, None], clip.obj_pos[frames], clip.obj_rot_xyzw[frames])[:, 0]
        return obj.world_points(clip.obj_pos[s], clip.obj_rot_xyzw[s], loc)

    cp = to_s(contact_point(clip, side, slice(s, e)), np.arange(s, e))
    ka = keys[0][0]
    kr = keys[-1][0]
    pa = to_s(palm_point(clip, side, np.arange(ka, s + 1)), np.arange(ka, s + 1))
    pr = to_s(palm_point(clip, side, np.arange(e - 1, kr + 1)), np.arange(e - 1, kr + 1))
    depth = (P - cs) @ nw0
    zz = np.array([0.0, 0.0, 1.0])
    hn = nw0 - zz * nw0[2]
    if np.linalg.norm(hn) > 0.3:                               # side face: look along it
        h, h_name = hn / np.linalg.norm(hn), "horizontal, out of the face towards the hand [m]"
    else:                                                      # top / bottom face: look across the push
        dv = np.r_[cen[seg][-1, :2] - cen[seg][0, :2], 0.0] if seg.sum() > 1 else u
        h = dv / np.linalg.norm(dv) if np.linalg.norm(dv) > 1e-6 else u
        h_name = "horizontal, along the push [m]"
    vertical = abs(nw0[2]) < 0.7
    views = (("contact seen from the hand (object frame at first contact)", u, v, "along the face [m]",
              "up along the face [m]" if vertical else "across the face [m]"),
             ("seen from the side (green = outward normal)", h, zz, h_name, "up [m]"))
    for j, (ttl, ax_u, ax_v, xl, yl) in enumerate(views):
        a = fig.add_subplot(g1[0, 1 + j])
        X, Y = (P - cs) @ ax_u, (P - cs) @ ax_v
        if j == 0:                                         # darker = closer to the hand
            order = np.argsort(depth)
            a.scatter(X[order], Y[order], s=1.0, c=depth[order], cmap="Greys", alpha=0.5, linewidths=0)
        else:
            a.scatter(X, Y, s=1.0, c=C_OBJ, alpha=0.4, linewidths=0)

        def f(Q, ax_u=ax_u, ax_v=ax_v):
            return (Q - cs) @ ax_u, (Q - cs) @ ax_v

        a.plot(*f(pa), color=C_RIGHT, lw=1.2, ls=":", label="palm, approach")
        a.plot(*f(pr), color=C_FOURTH, lw=1.2, ls=":", label="palm, retreat")
        if side == "B":                                   # the two hands behind the midpoint
            for hs, col, lab in (("L", C_LEFT, "left hand"), ("R", C_RIGHT, "right hand")):
                a.scatter(*f(to_s(contact_point(clip, hs, slice(s, e)), np.arange(s, e))), s=3, c=col, alpha=0.5,
                          linewidths=0, label=lab)
        sc = a.scatter(*f(cp), s=6, c=np.arange(len(cp)) / fps, cmap="viridis", linewidths=0,
                       label="contact proxy" if side != "B" else "midpoint (virtual hand)")
        if j == 1:
            x0, y0 = f(cp[:1])
            a.annotate("", xy=(x0[0] + 0.25 * nw0 @ ax_u, y0[0] + 0.25 * nw0 @ ax_v), xytext=(x0[0], y0[0]),
                       arrowprops={"arrowstyle": "-|>", "color": C_THIRD, "lw": 1.5})
            fig.colorbar(sc, ax=a, fraction=0.04, pad=0.01).set_label("time in contact [s]", fontsize=7)
        a.set_aspect("equal", adjustable="datalim")
        a.set_xlabel(xl, fontsize=7)
        a.set_ylabel(yl, fontsize=7)
        a.set_title(ttl, fontsize=8, loc="left")
        if j == 0:
            a.legend(fontsize=6.5, frameon=False, loc="lower left", markerscale=3)
        _clean_axes(a, "both")
    # ---- numbers
    a = fig.add_subplot(g1[0, 3])
    a.axis("off")
    rows = [
        ("tier / hand", f"{cand.get('tier', '')} / " + {"R": "right", "L": "left", "B": "both (midpoint)"}[side]),
        ("segment", f"{s / fps:.2f}–{e / fps:.2f} s ({cand['duration_s']:.1f} s)"),
        ("object moves", f"{_fmt(cand['obj_disp_xy_m'], 2, ' m')} (path {_fmt(cand['obj_path_xy_m'], 2, ' m')})"),
        ("tilt / yaw", f"{_fmt(cand['obj_tilt_max_deg'])}° / {_fmt(cand['obj_yaw_maxabs_deg'])}°"),
        ("push alignment", _fmt(cand.get("push_alignment"), 2)),
        ("normal spread p90", f"{_fmt(cand.get('normal_spread_p90_deg'))}°"),
        ("face tilt from vertical", f"{_fmt(cand.get('normal_tilt_median_deg'))}°"),
        ("patch coherence", _fmt(cand.get("patch_coherence_median"), 2)),
        *([("faces under the hands", f"{_fmt(cand.get('hands_face_angle_deg'))}° apart")] if side == "B" else []),
        ("approach / retreat angle", f"{_fmt(cand.get('approach_angle_deg'))}° / {_fmt(cand.get('retreat_angle_deg'))}°"),
        ("contact height", _fmt(cand.get("contact_z_median_m"), 2, " m")),
        ("proxy to surface", _fmt(cand.get("contact_surface_dist_median_m"), 3, " m")),
        ("human root moves", _fmt(cand.get("root_disp_xy_m"), 2, " m")),
        ("other body parts", f"{100 * cand.get('frac_body', float('nan')):.0f} % of frames"),
    ]
    for key in ("ann_dir", "ann_hands", "ann_weight_kg"):
        if key in cand and cand[key] not in (None, ""):
            rows.append((key.replace("ann_", "annotation: "), str(cand[key])))
    for i, (k, val) in enumerate(rows):
        a.text(0.0, 1 - i * 0.068, k, fontsize=8, color=C_MUTED, transform=a.transAxes, va="top")
        a.text(0.52, 1 - i * 0.068, val, fontsize=8, color=C_INK, transform=a.transAxes, va="top")

    # ---- timeline (window)
    g2 = gs[2].subgridspec(3, 1, hspace=0.15, height_ratios=[0.8, 1, 1])
    tt = win / fps
    L, Rr = hand_masks(clip)
    body = (clip.contact_body[:, NON_HAND_BODIES] == 1).any(1)
    a0 = fig.add_subplot(g2[0])
    for k, (m, lab, col) in enumerate(((L[win], "left hand", C_LEFT), (Rr[win], "right hand", C_RIGHT),
                                       (body[win], "other body", C_FOURTH))):
        a0.fill_between(tt, k + 0.1, k + 0.9, where=m, step="mid", color=col, linewidth=0)
    a0.set_yticks([0.5, 1.5, 2.5], ["left hand", "right hand", "other body"], fontsize=7)
    a0.set_ylim(0, 3)
    a1 = fig.add_subplot(g2[1], sharex=a0)
    vel = np.linalg.norm(np.gradient(clip.obj_pos[win, :2], axis=0), axis=1) * fps
    pv = np.linalg.norm(np.gradient(palm, axis=0), axis=1) * fps
    a1.plot(tt, vel, color=C_LEFT, lw=1.5, label="object horizontal speed [m/s]")
    a1.plot(tt, pv, color=C_RIGHT, lw=1.0, label="palm speed [m/s]")
    a1.legend(fontsize=6.5, frameon=False, loc="upper left")
    a2 = fig.add_subplot(g2[2], sharex=a0)
    al = alignment_series(clip, obj, slice(w0, w1), side)
    a2.plot(tt, np.where(seg, al, np.nan), color=C_THIRD, lw=1.5, label="push alignment (in contact, object moving)")
    for y0 in (0.0, 0.7):
        a2.axhline(y0, color=C_MUTED, lw=0.6, ls="--")
    a2.set_ylim(-1.05, 1.05)
    a2.set_xlabel("time [s]", fontsize=7)
    a2.legend(fontsize=6.5, frameon=False, loc="lower left")
    for a in (a0, a1, a2):
        a.axvspan(s / fps, e / fps, color="#000000", alpha=0.06, linewidth=0)
        for k, _ in keys:
            a.axvline(k / fps, color=C_MUTED, lw=0.6, ls=":")
        _clean_axes(a)
    fig.suptitle(title or f"{clip.name}  ·  segment {s / fps:.2f}–{e / fps:.2f} s", fontsize=10, color=C_INK)
    fig.savefig(path, dpi=72)
    plt.close(fig)


def gallery(items: list[tuple[Clip, ObjectMesh, dict]], path: Path, ncols: int = 4) -> None:
    """One frame (middle of the segment) per candidate, with its rank, tier, dataset and clip."""
    n = max(1, len(items))
    nrows = int(np.ceil(n / ncols))
    fig = plt.figure(figsize=(4.2 * ncols, 3.9 * nrows))
    for i, (clip, obj, c) in enumerate(items):
        ax = fig.add_subplot(nrows, ncols, i + 1, projection="3d")
        s, e = int(c["start"]), int(c["end"])
        k = (s + e - 1) // 2
        draw_frame(ax, clip, obj, k, _subsample(obj, 1500), _limits(clip, obj, np.arange(s, e)),
                   f"#{c['rank']} · tier {c['tier']} · {c.get('mode', '')} · {c['dataset']} · {c['object']}\n{clip.name}  "
                   f"{s / clip.fps:.1f}–{e / clip.fps:.1f} s")
    fig.tight_layout()
    fig.savefig(path, dpi=72)
    plt.close(fig)
