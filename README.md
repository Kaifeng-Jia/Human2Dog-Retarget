# Human2Dog-Retarget

Retargeting human–object interaction demonstrations (OMOMO) to a **Unitree B2 quadruped with a Z1 arm**.
CS 6758 (Cornell, Fall 2026) course project.

## Two lines

| | Learned line (in progress) | Full-optimization line (later) |
|---|---|---|
| Body motion | frozen X-Morph prior (human → GMR → G1 → X-Morph → B2-Z1) | optimized from scratch |
| What may change (course version) | **only the 6 Z1 arm joints**; base, legs, gripper and object trajectory are fixed | whole body |
| Transferred relations | hand → gripper contact, approach direction, timing | full part-role correspondence |

Both lines share `h2d/common` (robot geometry, data adapters, contact extraction, scene registration,
evaluation) so they can be compared on the same data and metrics.
The learned-line method spec is in [`docs/spec/learned_line_v0.5_zh.md`](docs/spec/learned_line_v0.5_zh.md).

## Layout

```
configs/b2z1.yaml          robot / tool / collision conventions (single source of truth)
h2d/common/robot.py        B2-Z1 kinematics, tool frame, contact site, Jacobians, collision geoms (MuJoCo)
h2d/common/meshgeom.py     exact point-to-mesh distance helpers
h2d/learned/               learned-line solvers (next: X-Morph wrapper, arm refinement)
scripts/                   runnable checks and pipelines; each writes a self-contained outputs/<run>/ folder
tests/                     fast regression tests
docs/setup_ubuntu.md       environment setup (RTX 5070)
```

Kinematics and collision use **one** MuJoCo model (X-Morph's full `b2_with_z1.xml`), so the optimizer and
the evaluator share the same geometry. torch is only needed inside X-Morph inference.

## Quick start

See [`docs/setup_ubuntu.md`](docs/setup_ubuntu.md), then:

```bash
export XMORPH_ROOT=$PWD/external/morph      # or your existing X-Morph checkout at the pinned commit
pytest -q
python scripts/b01_check_tool_geometry.py --out outputs/b01_tool_geometry
```

## Status

| Step (spec v0.5 §8) | State |
|---|---|
| B01 tool frame, contact site, collision geometry | done, see below |
| X-Morph prior wrapper + source-origin sidecar | next |
| Scene registration (start-anchored / contact-fitted) | next |
| Frozen-body reachability diagnostic (§7.1) | next |
| B1 / B2 / M arm refinement and evaluation | later |

### B01 result (X-Morph `a9f4a77`)

* Tool frame = `gripperStator`. Contact site `r_c = (0.149, 0, 0)` lies on the **gripperMover** front face
  at `jointGripper = 0` (distance 8e-10 m), 9 mm from the stator mesh.
* Front face (x ≥ 0.149 m): y ∈ [−0.0269, 0.0269] m, z ∈ [−0.0200, 0.0047] m, i.e. about 5.4 × 2.5 cm,
  filled (triangle area / extent area = 0.99); upper part on the mover, lower part on the stator.
* MuJoCo collides the gripper meshes through their convex hulls; front-face vertices lie on the hulls
  (≤ 6e-9 m), so the hull approximation is exact on the contact face.
* X-Morph's FK model agrees with the full model to 1e-15; X-Morph `dof_pos` order = MuJoCo `qpos[7:26]`.
