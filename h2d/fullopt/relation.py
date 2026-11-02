"""Relation term of the solver (fullopt spec v0.2 §5): one interface, exchangeable representations.

A representation is built once per clip from the human points, the object samples and the correspondence phi
(configs/fullopt/correspondence.yaml), and gives per frame t a residual r_t(q) and its Jacobian with respect to the
solver's increment, through the forward kinematics of the robot points (``Robot.point`` / ``Robot.point_jac``). The
solver does not know which representation it uses (``REPRESENTATIONS``).

(a) vertex substitution (spec §5.1, the OmniRetarget-style baseline): the robot's target points are the mapped human
points, d~_k = sum_i W_ki h_i (W from phi: 1 one-to-one, the mean many-to-one; Delta = 0 at level L0). Per frame, a
Delaunay tetrahedralisation of the targets and the object samples, uniform-weight Laplacian coordinates, and the
residual L_k(V(q)) - L_k(V~) on the robot vertices' rows. As in (b) (spec §5.2 point 3), v0.2 transfers the
horizontal part only: the human's heights mean nothing for the dog's trunk, whose height comes from E_nom, and the
hand's height comes from the task. The robot's end effector stands in for the virtual hand; inside the task window its
target is the task's contact target, blended in with the task gate (the learned line's mesh does the same, spec
v0.8 §5.5), so the relation and the task do not pull the gripper apart; for a grasp the end effector is the task's
tool point between the pads.

(b) whole-network mapping (spec §5.2) is milestone M2.
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import ConvexHull, Delaunay
from scipy.spatial.transform import Rotation as R

from h2d.fullopt import task as tk
from h2d.fullopt.hoi import HOIClip
from h2d.fullopt.signals import smooth


def object_samples(verts: np.ndarray, k: int) -> np.ndarray:
    """Farthest-point samples of the object's hull vertices (local frame), starting from the first one; the learned
    line's evaluation network uses the same samples."""
    idx, d = [0], np.linalg.norm(verts - verts[0], axis=1)
    for _ in range(min(k, len(verts)) - 1):
        idx.append(int(d.argmax()))
        d = np.minimum(d, np.linalg.norm(verts - verts[idx[-1]], axis=1))
    return verts[idx]


def human_points(c: HOIClip, mode: str, smooth_s: float) -> dict[str, np.ndarray]:
    """Human side of the network, (T, 3) each: the semantic joints, the virtual hand ("hand") and the task elbow
    ("elbow"), averaged over ``smooth_s`` (spec §6.1: the relation is transferred, not the sway of the gait)."""
    pts = {n: c.joint(n) for n in c.joint_names}
    pts.update(hand=tk.palm(c, mode), elbow=tk.elbow(c, mode))
    return {n: smooth(p, c.fps, smooth_s) for n, p in pts.items()}


def robot_targets(corr: dict, human: dict, task: tk.Task) -> np.ndarray:
    """d~ (T, K, 3) in the order of ``corr["points"]``; the end effector blends to the task's contact target."""
    D = np.stack([np.mean([human[h] for h in hs], axis=0) for hs in corr["points"].values()], 1)
    k = list(corr["points"]).index(corr["end_effector"])
    g = task.gate[:, None]
    D[:, k] = np.where(g > 0, (1 - g) * D[:, k] + g * np.nan_to_num(task.target), D[:, k])
    return D


class VertexSubstitution:
    """Representation (a). ``targets`` (T, K, 3) robot target points, ``objects`` (T, S, 3) world object samples."""

    def __init__(self, names: list[str], targets: np.ndarray, objects: np.ndarray, offsets: dict | None = None):
        self.names, self.K = list(names), len(names)
        self.offsets = offsets or {}            # robot points at another offset on their body (a grasp's tool point)
        self.n_rows = 2 * self.K
        self.targets, self.objects = targets, objects
        self.nbrs, self.lap = [], np.zeros((len(targets), self.K, 3))
        for t in range(len(targets)):
            V = np.vstack([targets[t], objects[t]])
            nb = [set() for _ in range(self.K)]
            for s in Delaunay(V, qhull_options="QJ").simplices:
                for a in s:
                    if a < self.K:
                        nb[a].update(int(b) for b in s if b != a)
            self.nbrs.append([np.array(sorted(x)) for x in nb])
            self.lap[t] = [V[k] - V[n].mean(0) for k, n in enumerate(self.nbrs[t])]

    def edges(self, t: int) -> list[tuple[int, int]]:
        """Robot-vertex edges of frame t (indices into targets + objects), for figures."""
        return sorted({(k, int(j)) for k, n in enumerate(self.nbrs[t]) for j in n if k < j or j >= self.K})

    def residual(self, t: int, robot, dofs: np.ndarray, floor_z: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
        P = np.vstack([[robot.point(k, floor_z, self.offsets.get(k)) for k in self.names], self.objects[t]])
        J = np.stack([robot.point_jac(k, dofs, self.offsets.get(k)) for k in self.names])
        r, Jr = np.zeros((self.K, 2)), np.zeros((self.K, 2, len(dofs)))
        for k, n in enumerate(self.nbrs[t]):
            r[k] = (P[k] - P[n].mean(0) - self.lap[t, k])[:2]
            Jr[k] = (J[k] - J[n[n < self.K]].sum(0) / len(n))[:2]
        return r.ravel(), Jr.reshape(self.n_rows, -1)


def vertex_substitution(c: HOIClip, task: tk.Task, robot, corr: dict, cfg: dict) -> VertexSubstitution:
    """Representation (a) of a clip; ``cfg``: configs/fullopt/solver.yaml ``relation``."""
    targets = robot_targets(corr, human_points(c, task.mode, cfg["human_smooth_s"]), task)
    offsets = {corr["end_effector"]: task.tool_offset} if task.tool_offset is not None else None
    return VertexSubstitution(list(corr["points"]), targets, object_track(c, cfg["object_samples"]), offsets)


def object_track(c: HOIClip, k: int) -> np.ndarray:
    """(T, k, 3) world positions of the object's ``k`` samples."""
    v = np.asarray(c.obj_verts, float)
    local = object_samples(v[ConvexHull(v).vertices], k)
    return np.einsum("tij,kj->tki", R.from_quat(c.obj_quat).as_matrix(), local) + c.obj_pos[:, None]


def whole_network(*_, **__):
    raise NotImplementedError("representation (b), whole-network mapping (fullopt spec §5.2), is milestone M2")


REPRESENTATIONS = {"a": vertex_substitution, "b": whole_network}
