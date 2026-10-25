#!/usr/bin/env python
"""B01: bind the tool frame, contact site and collision geometry, and check them.

Checks (spec v0.5 section 2, Codex review B01):
  A. r_c = (0.149, 0, 0) in the gripperStator frame lies on the gripperMover mesh
     when jointGripper = 0, and how far it is from the stator mesh.
  B. Real front-face triangles (vertices at tool x >= 0.149 - tol): owner link,
     y/z extents, area. Replaces the old "8 x 7 cm" bounding-box claim.
  C. MuJoCo collides mesh geoms through their convex hull: distance of r_c and of
     the front-face vertices to each hull.
  D. X-Morph's stripped FK model and the full model agree on body poses.
  E. Analytic contact-site / approach-axis Jacobians match finite differences.
  F. X-Morph dof_pos order equals MuJoCo qpos[7:26] order.
Also writes a collision-geometry inventory for the arm and a figure.

Usage:
  XMORPH_ROOT=/path/to/morph python scripts/common/b01_check_tool_geometry.py --run-id R001_b01
  (writes outputs/R001_b01/; refuses to run on a dirty tree or an unpinned X-Morph, see docs/versioning.md)
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
from scipy.spatial import ConvexHull  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from h2d.common.meshgeom import point_mesh_distance, triangle_areas  # noqa: E402
from h2d.common.robot import B2Z1Robot  # noqa: E402
from h2d.common.runinfo import ProvenanceError, add_run_args, start_run  # noqa: E402
from h2d.paths import xmorph_path  # noqa: E402

TOL_ON_SURFACE = 1e-5     # m
TOL_FK = 1e-6             # m / rad-equivalent
TOL_JAC_REL = 1e-4


def hull_signed_distance(points: np.ndarray, hull_pts: np.ndarray) -> np.ndarray:
    """Signed distance of points to the convex hull of hull_pts (>0 outside)."""
    hull = ConvexHull(hull_pts)
    eq = hull.equations  # n.x + d <= 0 inside, n unit
    s = points @ eq[:, :3].T + eq[:, 3]
    return s.max(axis=1)


def random_config(robot: B2Z1Robot, rng: np.random.Generator) -> np.ndarray:
    q = robot.model.qpos0.copy()
    q[0:3] = rng.uniform([-1, -1, 0.3], [1, 1, 0.8])
    quat = rng.normal(size=4)
    q[3:7] = quat / np.linalg.norm(quat)
    q[robot.joint_qadr] = rng.uniform(robot.joint_lower, robot.joint_upper)
    q[robot.gripper_qadr] = robot.gripper_lock
    return q


def main() -> int:
    ap = argparse.ArgumentParser()
    add_run_args(ap)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    try:
        prov = start_run(args.run_id, needs=("xmorph",), allow_dirty=args.allow_dirty,
                         allow_external_mismatch=args.allow_external_mismatch)
    except ProvenanceError as e:
        print(f"[refused] {e}", file=sys.stderr)
        return 2
    out = Path(args.out or f"outputs/{args.run_id}")
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    robot = B2Z1Robot()
    cfg = robot.cfg
    m = robot.model
    results: dict = {"provenance": prov, "checks": {}}

    # nominal state: default qpos0, gripper locked
    q = m.qpos0.copy()
    q[robot.gripper_qadr] = robot.gripper_lock
    robot.set_qpos(q)

    tool_bodies = cfg["collision"]["tool_bodies"]
    coll = {g.body: g.geom_id for g in robot.geoms(tool_bodies) if g.collides and g.mesh_id >= 0}
    p_c = robot.contact_site()

    # ---- A: contact site on the mover surface
    meshes_tool = {}
    dist = {}
    for body, gid in coll.items():
        v, f = robot.mesh_world(gid)
        meshes_tool[body] = (robot.to_tool_frame(v), f)
        dist[body] = point_mesh_distance(p_c, v, f)
    contact_body = cfg["tool"]["contact_body"]
    a_pass = dist[contact_body] <= TOL_ON_SURFACE
    results["checks"]["A_contact_site_on_surface"] = {
        "r_c_tool_frame": robot.r_c.tolist(),
        "distance_to_mesh_m": dist,
        "expected_owner": contact_body,
        "pass": bool(a_pass),
    }

    # ---- B: real front-face triangles
    x0, tol = cfg["tool"]["front_face_x"], cfg["tool"]["front_face_tol"]
    front = {}
    front_pts = []
    for body, (vt, f) in meshes_tool.items():
        sel = np.all(vt[f][:, :, 0] >= x0 - tol, axis=1)
        tris = f[sel]
        area = float(triangle_areas(vt, tris).sum()) if len(tris) else 0.0
        pts = vt[np.unique(tris)] if len(tris) else np.zeros((0, 3))
        front_pts.append(pts)
        front[body] = {
            "n_triangles": int(len(tris)),
            "area_cm2": area * 1e4,
            "y_range_m": [float(pts[:, 1].min()), float(pts[:, 1].max())] if len(pts) else None,
            "z_range_m": [float(pts[:, 2].min()), float(pts[:, 2].max())] if len(pts) else None,
        }
    allp = np.concatenate(front_pts) if front_pts else np.zeros((0, 3))
    results["checks"]["B_front_face"] = {
        "plane_x_m": x0,
        "vertex_tol_m": tol,
        "per_body": front,
        "union_y_range_m": [float(allp[:, 1].min()), float(allp[:, 1].max())] if len(allp) else None,
        "union_z_range_m": [float(allp[:, 2].min()), float(allp[:, 2].max())] if len(allp) else None,
    }
    fb = results["checks"]["B_front_face"]
    if len(allp):
        bbox_area = (fb["union_y_range_m"][1] - fb["union_y_range_m"][0]) * (fb["union_z_range_m"][1] - fb["union_z_range_m"][0])
        tri_area = sum(v["area_cm2"] for v in front.values()) * 1e-4
        fb["triangle_area_over_bbox_area"] = tri_area / bbox_area if bbox_area > 0 else None
        fb["note"] = "ratio ~1 means the front face fills its y-z extent (no holes)"

    # ---- C: convex-hull approximation used by MuJoCo collision
    hull = {}
    rc_tool = robot.r_c[None, :]
    for body, (vt, _f) in meshes_tool.items():
        sd_rc = float(hull_signed_distance(rc_tool, vt)[0])
        fp = front_pts[list(meshes_tool).index(body)]
        sd_front = hull_signed_distance(fp, vt) if len(fp) else np.zeros(0)
        hull[body] = {
            "r_c_signed_distance_to_hull_m": sd_rc,
            "front_vertices_max_abs_distance_to_hull_m": float(np.abs(sd_front).max()) if len(sd_front) else None,
        }
    results["checks"]["C_convex_hull"] = {
        "per_body": hull,
        "note": "MuJoCo mesh-mesh / mesh-primitive collision uses the convex hull; ~0 means the hull is exact on the front face",
    }

    # ---- D: X-Morph FK model vs full model
    fk = mujoco.MjModel.from_xml_path(str(xmorph_path(cfg["xmorph"]["fk_xml"])))
    fkd = mujoco.MjData(fk)
    fk_jnames = [mujoco.mj_id2name(fk, mujoco.mjtObj.mjOBJ_JOINT, j) for j in range(fk.njnt)]
    fk_bodies = [mujoco.mj_id2name(fk, mujoco.mjtObj.mjOBJ_BODY, b) for b in range(fk.nbody)]
    common = [b for b in fk_bodies if b not in (None, "world")]
    has_free = fk.jnt_type[0] == mujoco.mjtJoint.mjJNT_FREE if fk.njnt else False
    max_pos, max_rot = 0.0, 0.0
    n_cfg = 200
    for _ in range(n_cfg):
        qf = random_config(robot, rng)
        robot.set_qpos(qf)
        qfk = fk.qpos0.copy()
        for jn in robot.joint_order:
            if jn in fk_jnames:
                qfk[fk.jnt_qposadr[fk_jnames.index(jn)]] = qf[m.jnt_qposadr[robot._jid(jn)]]
        if has_free:
            qfk[0:7] = qf[0:7]
        fkd.qpos[:] = qfk
        mujoco.mj_kinematics(fk, fkd)
        # compare in base frame so a missing free joint in the FK file is not an error
        bb_full = robot._bid("base_link")
        bb_fk = fk_bodies.index("base_link")
        Rb_f, pb_f = robot.data.xmat[bb_full].reshape(3, 3), robot.data.xpos[bb_full]
        Rb_k, pb_k = fkd.xmat[bb_fk].reshape(3, 3), fkd.xpos[bb_fk]
        for b in common:
            i_f, i_k = robot._bid(b), fk_bodies.index(b)
            pf = Rb_f.T @ (robot.data.xpos[i_f] - pb_f)
            pk = Rb_k.T @ (fkd.xpos[i_k] - pb_k)
            Rf = Rb_f.T @ robot.data.xmat[i_f].reshape(3, 3)
            Rk = Rb_k.T @ fkd.xmat[i_k].reshape(3, 3)
            max_pos = max(max_pos, float(np.linalg.norm(pf - pk)))
            max_rot = max(max_rot, float(np.linalg.norm(Rf - Rk)))
    results["checks"]["D_fk_consistency"] = {
        "n_configs": n_cfg,
        "bodies_compared": len(common),
        "fk_has_free_joint": bool(has_free),
        "max_body_position_error_m": max_pos,
        "max_body_rotation_error_fro": max_rot,
        "pass": bool(max_pos <= TOL_FK and max_rot <= TOL_FK),
    }

    # ---- E: Jacobians vs finite differences
    eps = 1e-6
    worst = 0.0
    for _ in range(20):
        qf = random_config(robot, rng)
        robot.set_qpos(qf)
        Jp, Ja = robot.contact_site_jacobian(), robot.approach_axis_jacobian()
        p0, a0 = robot.contact_site(), robot.approach_axis()
        arm0 = qf[robot.arm_qadr].copy()
        Jp_fd, Ja_fd = np.zeros_like(Jp), np.zeros_like(Ja)
        for k in range(6):
            d = np.zeros(6)
            d[k] = eps
            robot.set_arm(arm0 + d)
            Jp_fd[:, k] = (robot.contact_site() - p0) / eps
            Ja_fd[:, k] = (robot.approach_axis() - a0) / eps
            robot.set_arm(arm0)
        for J, Jfd in ((Jp, Jp_fd), (Ja, Ja_fd)):
            worst = max(worst, float(np.abs(J - Jfd).max() / max(1.0, np.abs(Jfd).max())))
    results["checks"]["E_jacobians"] = {"max_rel_error": worst, "pass": bool(worst <= TOL_JAC_REL)}

    # ---- F: joint order
    qadr = robot.joint_qadr
    f_pass = bool(np.all(qadr == np.arange(7, 7 + len(qadr))))
    results["checks"]["F_joint_order"] = {"qpos_addresses": qadr.tolist(), "pass": f_pass}

    # ---- collision inventory (arm)
    robot.set_qpos(q)
    inv = [
        {"geom": g.geom_id, "body": g.body, "type": g.gtype, "collides": g.collides}
        for g in robot.geoms(cfg["collision"]["arm_bodies"])
        if g.collides
    ]
    results["collision_inventory_arm"] = inv

    passed = [k for k, v in results["checks"].items() if v.get("pass") is True]
    failed = [k for k, v in results["checks"].items() if v.get("pass") is False]
    results["passed"], results["failed"] = passed, failed
    (out / "summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    # ---- figure
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    colors = {"gripperStator": "#9aa5b1", "gripperMover": "#d8b25c"}
    for body, (vt, f) in meshes_tool.items():
        for ax, (i, j) in zip(axes, ((0, 2), (1, 2))):
            tri = vt[f][:, :, [i, j]]
            for t in tri:
                ax.fill(t[:, 0], t[:, 1], color=colors.get(body, "#bbb"), alpha=0.08, lw=0)
        sel = np.all(vt[f][:, :, 0] >= x0 - tol, axis=1)
        for t in vt[f[sel]][:, :, [1, 2]]:
            axes[1].fill(t[:, 0], t[:, 1], color=colors.get(body, "#bbb"), alpha=0.9, lw=0.3, ec="k")
    axes[0].plot(robot.r_c[0], robot.r_c[2], "o", color="#d62728", ms=7, label="contact site r_c")
    axes[0].annotate("", xy=(robot.r_c[0] + 0.04, robot.r_c[2]), xytext=(robot.r_c[0], robot.r_c[2]),
                     arrowprops=dict(arrowstyle="->", color="#d62728", lw=1.5))
    axes[0].axvline(x0, color="#d62728", lw=0.8, ls="--")
    axes[0].set_xlim(-0.02, x0 + 0.05)
    axes[0].text(x0 + 0.004, robot.r_c[2] + 0.004, "approach axis", color="#d62728", fontsize=8)
    axes[0].set_title("Side view in tool frame (x forward, z up)")
    axes[0].set_xlabel("x [m]")
    axes[0].set_ylabel("z [m]")
    axes[1].plot(robot.r_c[1], robot.r_c[2], "o", color="#d62728", ms=7)
    axes[1].set_title("Front face (x >= 0.149 m), viewed along -x")
    axes[1].set_xlabel("y [m]")
    axes[1].set_ylabel("z [m]")
    for ax in axes:
        ax.set_aspect("equal")
        ax.grid(alpha=0.3)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c, alpha=0.8) for c in colors.values()]
    axes[0].legend(handles + [axes[0].lines[0]], list(colors) + ["contact site r_c"],
                   loc="upper left", bbox_to_anchor=(0.0, -0.30), ncol=3, fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(out / "tool_geometry.png", dpi=160)

    # ---- report
    A, B, C = (results["checks"][k] for k in ("A_contact_site_on_surface", "B_front_face", "C_convex_hull"))
    D, E = results["checks"]["D_fk_consistency"], results["checks"]["E_jacobians"]
    lines = [
        "# B01 tool and collision geometry check",
        "",
        f"Run `{prov['run_id']}` · code `{prov['git']['describe']}` (dirty={prov['git']['dirty']}) · "
        f"X-Morph `{(prov['externals']['xmorph'].get('actual') or '?')[:7]}` "
        f"(pinned match={prov['externals']['xmorph'].get('match')}) · host `{prov['host']}`",
        "",
        "| Check | Result | Pass |",
        "|---|---|---|",
        f"| A. r_c on {contact_body} surface | distance to mover {A['distance_to_mesh_m'].get('gripperMover', float('nan')):.2e} m, "
        f"to stator {A['distance_to_mesh_m'].get('gripperStator', float('nan')):.2e} m | {A['pass']} |",
        f"| B. front face extents (union) | y [{B['union_y_range_m'][0]:+.4f}, {B['union_y_range_m'][1]:+.4f}] m, "
        f"z [{B['union_z_range_m'][0]:+.4f}, {B['union_z_range_m'][1]:+.4f}] m; "
        f"triangle area / extent area = {B.get('triangle_area_over_bbox_area', float('nan')):.3f} | info |",
        f"| C. r_c to convex hull | " + ", ".join(f"{b}: {h['r_c_signed_distance_to_hull_m']:+.2e} m" for b, h in C['per_body'].items()) + " | info |",
        f"| D. FK model vs full model | pos {D['max_body_position_error_m']:.2e} m, rot {D['max_body_rotation_error_fro']:.2e} | {D['pass']} |",
        f"| E. Jacobians vs finite diff | max rel err {E['max_rel_error']:.2e} | {E['pass']} |",
        f"| F. joint order | qpos[7:26] | {results['checks']['F_joint_order']['pass']} |",
        "",
        "## Front face per link",
        "",
        "| Link | triangles | area [cm^2] | y range [m] | z range [m] |",
        "|---|---|---|---|---|",
    ]
    for b, v in B["per_body"].items():
        lines.append(f"| {b} | {v['n_triangles']} | {v['area_cm2']:.2f} | {v['y_range_m']} | {v['z_range_m']} |")
    lines += ["", "## Arm collision geoms", "", "| geom | body | type |", "|---|---|---|"]
    lines += [f"| {g['geom']} | {g['body']} | {g['type']} |" for g in inv]
    lines += ["", "![tool geometry](tool_geometry.png)", ""]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({k: results["checks"][k].get("pass", "info") for k in results["checks"]}, indent=1))
    print("failed:", failed)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
