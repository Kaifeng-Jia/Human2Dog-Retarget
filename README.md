# Human2Dog-Retarget

Retargeting human–object interaction demonstrations (OMOMO) to a **Unitree B2 quadruped with a Z1 arm**.
CS 6758 (Cornell, Fall 2026) course project. All project lines live in this repository.

## Lines

| | Learned line (in progress) | Full-optimization line (later) |
|---|---|---|
| Body motion | frozen X-Morph prior (human → GMR → G1 → X-Morph → B2-Z1) | optimized from scratch |
| What may change (course version) | **only the 6 Z1 arm joints**; base, legs, gripper and object trajectory are fixed | whole body |
| Transferred relations | hand → gripper contact, approach direction, timing | full part-role correspondence |
| Code | `h2d/learned/`, `scripts/learned/` | `h2d/fullopt/`, `scripts/fullopt/` |

Both lines share `h2d/common` (robot geometry, data adapters, contact extraction, scene registration,
evaluation) and are compared on the same data and metrics. Specs: [`docs/spec/`](docs/spec/README.md).

## Layout

```
configs/b2z1.yaml          robot / tool / collision conventions (single source of truth)
configs/external.yaml      pinned third-party commits (X-Morph, GMR)
h2d/common/                shared modules: robot.py, meshgeom.py, runinfo.py (provenance)
h2d/learned/  h2d/fullopt/ line-specific solvers
scripts/<line>/            runnable steps; each writes outputs/<run-id>/ with summary.json + report.md
tests/<line>/              fast regression tests
docs/                      setup_ubuntu.md, versioning.md, spec/
```

Kinematics and collision use **one** MuJoCo model (X-Morph's full `b2_with_z1.xml`), so the optimizer and
the evaluator share the same geometry. torch is only needed inside X-Morph inference.

## Versioning, runs and results

See [`docs/versioning.md`](docs/versioning.md): `main` is merged only through PRs; work branches are
`<who>/<line>/<topic>`; results go to the `reports` branch, never into `main`; every run records its commit
and refuses to run on a dirty tree or unpinned third-party code. Collaboration roles: [`CLAUDE.md`](CLAUDE.md).

## Quick start

See [`docs/setup_ubuntu.md`](docs/setup_ubuntu.md), then:

```bash
export XMORPH_ROOT=$PWD/external/morph
pytest -q
python scripts/common/b01_check_tool_geometry.py --run-id R001_b01
```

## Status

| Step (spec v0.5 §8) | State |
|---|---|
| B01 tool frame, contact site, collision geometry | done (v0.1.0) |
| X-Morph prior wrapper + source-origin sidecar | done (v0.1.1), GPU check in R002 |
| OMOMO_new format inspection, GMR install | R002 |
| Scene registration (start-anchored / contact-fitted) | next |
| Frozen-body reachability diagnostic (§7.1) → tag `m1-reachability` | next |
| B1 / B2 / M arm refinement and evaluation | later |

### B01 result (X-Morph `a9f4a77`)

* Tool frame = `gripperStator`. Contact site `r_c = (0.149, 0, 0)` lies on the **gripperMover** front face
  at `jointGripper = 0` (distance 8e-10 m), 9 mm from the stator mesh.
* Front face (x ≥ 0.149 m): y ∈ [−0.0269, 0.0269] m, z ∈ [−0.0200, 0.0047] m, about 5.4 × 2.5 cm and
  filled (triangle area / extent area = 0.99); upper part on the mover, lower part on the stator.
* MuJoCo collides the gripper meshes through their convex hulls; front-face vertices lie on the hulls
  (≤ 6e-9 m), so the hull approximation is exact on the contact face.
* X-Morph's FK model agrees with the full model to 1e-15; X-Morph `dof_pos` order = MuJoCo `qpos[7:26]`.
