# Human2Dog-Retarget

Transferring human–object interaction demonstrations (OMOMO) to a **Unitree B2 quadruped with a Z1 arm**, so that
the robot does the same task and keeps the human's relation to the object, not only the contact point.
CS 6758 (Cornell, Fall 2026) course project.

The repository holds two lines that share `h2d/common` (data adapters, task extraction, robot geometry, collision,
registration):

| | Learned line (done, `v0.3.0`) | Full-optimization line (in progress) |
|---|---|---|
| Body motion | frozen X-Morph prior (human → GMR → G1 → X-Morph → B2-Z1) | optimized |
| What we solve | where the body stands, frame by frame; the Z1 arm | the whole robot |
| Code | `h2d/learned/`, `scripts/learned/` | `h2d/fullopt/`, `scripts/fullopt/` |
| Spec | [`docs/spec/learned/v0.8_zh.md`](docs/spec/learned/v0.8_zh.md) | [`docs/spec/fullopt/v0.2_zh.md`](docs/spec/fullopt/v0.2_zh.md) |

## Learned line

1. **Prior.** A human clip is converted to SMPL-X (mean shape), retargeted to the G1 humanoid with GMR, and to the
   B2-Z1 with the frozen X-Morph model. X-Morph gives natural legs and gait but knows nothing about the object.
2. **Task targets from the human** (`h2d/common/data/tasks.py`, object frame): contact point and face normal of a
   virtual hand (left, right or both), approach and retreat distance, and the gripper pose: approach along the
   human forearm within 45° of the face normal, roll from the line across the knuckles. A push on a top face is
   moved to the face or edge on the robot's side.
3. **Body placement** (`h2d/learned/imesh.py`): an interaction mesh between the human (pelvis, chest, hand) and
   samples of the object; a per-frame planar pose of the dog keeps the mesh's edge directions and the human's
   heading, while the distance comes from the dog's arm. Solved over the window by sparse least squares.
4. **Arm** (`h2d/learned/reach.py`): multi-start, collision-aware Z1 IK to the contact target and approach.

The legs always follow the prior; the placement is compared with two baselines: the prior registered once
(`reach_fit`) and a script where the body follows the object (`reach_track`).

### Results (10 OMOMO pushes)

| | prior | script | interaction mesh |
|---|---|---|---|
| fully reached (position + direction, every contact frame) | 3/10 | 9/10 | **9/10** |
| relation to the human: edge direction error (median) | 8.5° | 10.4° | **6.0°** |
| heading error (median) | 8.6° | 8.6° | **2.6°** |
| body inside the object (max) | 13.0 cm | 4.5 cm | **0.8 cm** |
| extra foot slide (median of per-task max) | 0 | 0.29 m/s | 0.63 m/s |

Where the human stands beside the box or reaches across it, the script puts the dog on the other side (47–79°);
the mesh keeps it on the human's side (5–6°). The cost is foot slide: the body is moved while the legs keep the
prior's gait. Details, tuning and limitations: [`docs/results/learned_course_zh.md`](docs/results/learned_course_zh.md).
Method: [`docs/spec/learned/v0.8_zh.md`](docs/spec/learned/v0.8_zh.md) ("spec §x" in the code).

### Reproduce

Setup (data, licensed models, pinned third-party code, environment): [`docs/setup_ubuntu.md`](docs/setup_ubuntu.md).
Third-party commits are pinned in `configs/external.yaml`; every script records its provenance in
`outputs/<run-id>/summary.json` and refuses a dirty tree or an unpinned checkout.

```bash
pytest -q

# 1. push candidates (OMOMO_new + FORCE) and their task targets
python scripts/common/push_candidates.py --run-id cands --selection configs/candidate_selection.yaml \
  --top 16 --per-object 6
python scripts/common/prepare_tasks.py --run-id tasks --candidates outputs/cands/candidates.csv \
  --selection configs/candidate_selection.yaml

# 2. the X-Morph prior for the OMOMO_new clips (GPU)
python scripts/learned/d0_chain.py --run-id d0 --clips-file outputs/tasks/clips_omomo.txt

# 3. body layouts + arm IK on the passing OMOMO_new tasks
python scripts/learned/reach_diag.py --run-id reach --tasks-dir outputs/tasks/tasks --d0-dir outputs/d0 \
  --tasks-csv outputs/tasks/tasks.csv --max-tasks 12 --layouts mesh reach_track reach_fit start_anchored

# 4. MuJoCo videos: 2 x 3 (human, G1, X-Morph / three layouts) and 1 x 3 (human, G1, dog)
MUJOCO_GL=egl python scripts/learned/render_mujoco.py --reach-dir outputs/reach \
  --tasks-dir outputs/tasks/tasks --d0-dir outputs/d0
MUJOCO_GL=egl python scripts/learned/render_mujoco.py --reach-dir outputs/reach \
  --tasks-dir outputs/tasks/tasks --d0-dir outputs/d0 --pipeline human g1 --layouts mesh --out outputs/reach/videos_1x3
```

Each step writes `outputs/<run-id>/` with `summary.json` and `report.md`.

## Full-optimization line (in progress)

No learned prior: the B2-Z1's whole body is solved frame by frame (SQP, cvxpy + Clarabel) from one standard input, a
human-object clip of world joint positions with the object's mesh and poses (`h2d/fullopt/hoi.py`); the robot enters
only through its description (`configs/fullopt/robots/b2z1.yaml`). Milestones and their status: spec §10. M1 is
pass 1: the whole body with the soles on the floor (they slide; the gait is M3), the relation term (a) (vertex
substitution), the learned line's task targets and evaluation.

```bash
pip install -e ".[dev,fullopt]" -c constraints.txt
python scripts/fullopt/export_hoi.py --run-id hoi --dev outputs/tasks --heldout outputs/tasks_force outputs/tasks_omomo
python scripts/fullopt/m0_gait_stats.py --run-id m0 --clips outputs/hoi/clips
python scripts/fullopt/solve.py --run-id m1 --clips outputs/hoi/clips --learned-root outputs \
  --learned-reach outputs/reach/summary.json
MUJOCO_GL=egl python scripts/fullopt/render.py --solve-dir outputs/m1 --clips outputs/hoi/clips
```

## Layout

```
configs/      b2z1.yaml (robot, tool, collision conventions), external.yaml (pinned third-party code),
              data.yaml (dataset paths), candidate selection, registration, learned/ (prior, IK, mesh),
              fullopt/ (input formats, robot descriptions, correspondence, gait, solver, evaluation)
h2d/common/   data adapters (OMOMO_new, FORCE), contact description, candidates, task targets, robot model,
              collision, registration, provenance
h2d/learned/  GMR wrapper, X-Morph prior, interaction-mesh placement, arm IK
h2d/fullopt/  standard input, gait signals, task targets, robot description, relation term, SQP solver, evaluation
scripts/      runnable steps, one folder per line
tests/        fast regression tests (synthetic clip; X-Morph assets when available)
docs/         setup, data formats, method spec, results, versioning
```

One MuJoCo model (X-Morph's `b2_with_z1.xml`) provides both kinematics and collision geometry. Data, body models,
checkpoints and third-party repositories are not included (licences); see the setup guide.

## Development

Branches, run tickets, the `reports` branch for small result files and the milestone tags are described in
[`docs/versioning.md`](docs/versioning.md); changes per version in [`CHANGELOG.md`](CHANGELOG.md).

## License

The code in this repository is released under the [MIT License](LICENSE). The datasets (OMOMO, FORCE), body models
(SMPL-X, SMPL-H), X-Morph and its checkpoints, GMR and the HOI-Retarget object meshes are not part of it and keep
their own licences.
