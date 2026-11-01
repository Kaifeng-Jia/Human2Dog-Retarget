# Changelog

Format: one section per version, newest first. Versioning rules: `docs/versioning.md`.

## [0.3.4] — 2026-11-01 (full-optimization line: grasp inventory)

### Added (Kevin: the gripper is done in the full-optimization line; the learned line stays as it is)
- `configs/fullopt/grasp_selection.yaml`: the line's own selection of grasp segments for `push_candidates.py`: pulls
  on a side or slant face only, no yaw limit (targets live in the object frame), the whole-body grasp height band
  0.15-1.2 m. Two hands on different faces stay out.
- `scripts/fullopt/grasp_reach.py`: whole-body reach map of a grasp (feet planted, trunk 0.40-0.58 m, nose down
  <= 15 deg, no collision, body behind the part) per contact height and approach angle. Cloud: level down to 0.40 m
  (0.65 m standing), 15 deg down 0.30 m, 30 deg down 0.20 m, 45-90 deg down 0.15 m.
- `scripts/fullopt/export_hoi.py --grasp`: grasp segments of a candidate pool as HOI clips, split by person (the
  people of the press dev split are dev; everyone else, and FORCE, held out); `meta` records grip and interaction;
  the report counts clips per object and split. `h2d/fullopt/tasks.py`: `grasp_rows`, `split_by_person`.
- `scripts/fullopt/contact_sheet.py`: one MuJoCo still per clip (person and object at mid contact, pelvis and object
  paths), 16 a page.
- Spec: the grasp inventory (R015 pool: 62 usable grasp pulls, 4 main part types), the grasp split, grasping moved
  into the line's scope (kinematics and the gripper's timing; forces stay out).

### Fixed (merging M1)
- `grasp_reach.py` maps the self pairs' geoms to their bodies (`Collision.self_distances` returns geoms since the
  R027b revision).

## [0.3.3] — 2026-11-01 (full-optimization line: M1, the solver and pass 1)

### Added (fullopt spec v0.2 §3 steps 1-3, §4, §5.1, §7, §8.1)
- Robot description `configs/fullopt/robots/b2z1.yaml` (model, trunk, feet, joints, home and nominal height, speed
  limits, tool, the dog points of the correspondence, collision groups) and the correspondence
  `configs/fullopt/correspondence.yaml`; `h2d/fullopt/robot.py` reads any robot from its description (FK of named
  points, point and axis Jacobians in MuJoCo's tangent space, limits, the learned line's collision rules). Only these
  files name B2-Z1 parts.
- `h2d/fullopt/task.py`: the learned line's task targets (contact, approach, tool pose, roll, height band, top pushes
  from the robot's side) from a `HOIClip` alone, and the task gate a c kappa; `task.compare` checks them against the
  learned line's task files.
- `h2d/fullopt/relation.py`: the relation interface and representation (a), vertex substitution (horizontal Laplacian
  coordinates on the robot vertices, the end effector's target is the contact target inside the task window); (b) is
  M2.
- `h2d/fullopt/solver.py`, `configs/fullopt/solver.yaml`: per-frame SQP, one QP with a second-order cone per iteration
  (cvxpy + Clarabel, compiled once with parameters), relation + gated task + nominal + smoothness, joint and trunk
  speed and height boxes, linearised object / floor / self constraints with L1 slacks, trust region 0.1.
- `h2d/fullopt/evaluate.py`, `configs/fullopt/evaluation.yaml`: reach, penetration, limits and the relation metrics
  (edge direction, heading, same side) with the learned line's definitions.
- `scripts/fullopt/solve.py` (dev and held-out apart, pass on dev: reach >= 9, body in object <= 1 cm, targets agree
  with the learned line's) and `scripts/fullopt/render.py` (MuJoCo, human | robot with one camera, mp4 + key-frame
  strip).
- Dependencies `cvxpy==1.7.5`, `clarabel==0.11.1` (extra `fullopt`; 1.7.5 is the newest cvxpy for Python 3.10 with
  numpy 1.x).

### Found on the cloud dry run (synthetic clips and the two real dev windows of R015, not a reported run)
- The palm's joint centre can lie inside a thin table top, where the patch normal points down: the face normal now
  points to the human's side (the elbow). The learned line's "flipped palm" on two-hand table pushes (R014) comes from
  this; the full-optimization line's roll target differs from it by 180 deg there (soft, does not decide reach).
- With the contact moved to the robot's side, the palm is still 10 cm from the edge the frame before contact: the
  approach target now closes in at most 0.5 m/s (contact frames unchanged).
- The trunk jumped where the task gate opens (8 m/s): trunk speed limits 1 m/s and 2 rad/s per axis.

### Changed after R027 (dev 6/10; lead decisions A-F, fullopt spec v0.2 revision table "R027 之后")
- Pass 1 moves the legs too (24 dofs): every sole within 1 mm of the floor (evaluation: 2 mm), sliding, pulled softly
  to its foothold under the hip; leg speed limits from the B2 URDF (23 / 23 / 14 rad/s); every geom but the soles
  3 cm above the floor; trunk roll and pitch within 15 deg. The evaluation reports foot slide instead of feet below
  the floor.
- The space under the trunk counts as body: a virtual box in the description (inside the hips, from the trunk's
  underside to the floor), its voxel grid outside the object's hull and the hull's vertices outside it; evaluated as
  the overlap of the box and the hull (an LP per frame); dev pass: 0 frames.
- The line's own task gate: rising from 1.5 s before the contact, 1 from 0.5 s before; targets over the whole rise.
  Trunk limits: 1 m/s horizontal, 0.3 m/s vertical, 1 rad/s; accelerations as hard step bounds, 5 m/s2 horizontal
  (friction), 3 m/s2 vertical, 15 rad/s2. Rows the trunk closes in on (object, under-body box, tilt, height range)
  cap the closing speed so that the trunk can still stop (`solver.held`); step bounds no longer force dx = 0 inside.
- `Collision.distance` cross-checks MuJoCo's negative distances: MuJoCo 3.11 gives -24 mm for two geoms 24 mm apart
  (R027 c10 frame 45, a test reproduces it), detected by witness points that are not |distance| apart; the pair is
  then measured by sample points.
- The face class (top or not) comes from the hand joints that touch the surface, not from the palm centre, which a
  lifted wrist holds over a table's edge (R027 c12: 1.48 -> 0.59 cm from the learned target).
- `solve.py` records cvxpy, clarabel and mujoco versions and the thread settings; every fullopt script sets one BLAS /
  OpenMP thread before numpy loads (R027: more system than user time).
- Evaluation pass adds: no object under the body, every sole on the floor, trunk within its speed and acceleration
  limits.

### Changed after R027b (dev 8/10 on Ubuntu, unconverged frames, order dependence; lead decisions A-G)
- Every QP starts from a fresh solver state (`warm_start=False`); the compiled problem is kept. Solving two clips in
  either order gives bitwise-identical q (tested).
- Globalised SQP (`Solver._frame`): L1 merit, step accepted at 0.1 of the predicted decrease, second-order
  correction, trust region from 0.1 (x1/4 on rejection, x2 on agreement, 1e-6 to 0.4), up to 150 iterations per
  frame and 200 on the first. The merit counts violations beyond 10 um (the QP still holds the rows exactly);
  velocity and acceleration rows use the exact rotation Jacobian. Per clip: unconverged frames, rejected steps and
  the final radius.
- `Collision.distance` also catches MuJoCo's distance of exactly 0 for a mesh and a box 24 mm apart, and re-measures
  inconsistent pairs with one geom moved by 0.1-10 um before falling back to sample points.
- New check, collision free on all frames (self pairs, every geom but the soles against the floor, 2 mm); dev pass
  needs 0 frames. The held-out `reached` row no longer applies the dev minimum.
- Tests run with one BLAS / OpenMP thread (`tests/conftest.py`).
- Kept as known (lead): c01's push start (contact frames 2-9) stays the one dev miss; reaching it needs both a
  higher trunk yaw rate and unbounded trunk accelerations, or a look-ahead on the object's motion. c07 / c08's
  trunk lunge on the approach (tilt at the 15 deg limit) stays until the gait (M3) lets the trunk walk up. So does
  the backpack's front-right sole sliding ~0.3 m out and back within 1-2 frames while the human swings it (before
  the task; the sole stays on the floor, no check covers its speed).

### Changed after R027c (Ubuntu: every solve check passed; the synthetic push test's frame 1 stopped on its radius)
- Looser per-frame stop, after the references: a frame converges on the first of a step below 1e-3 inside the radius
  (was 1e-4), an accepted step changing the merit by at most 1e-5 of it (OmniRetarget's stop on the cost), or the
  radius below 1e-5 (scipy trust-constr's xtol) with no row violated beyond 1e-4 (IPOPT's constr_viol_tol). Before,
  a stop on the radius (floor 1e-6) was unconverged and fell on either side of the floor across machines (cloud
  1.6e-6, Ubuntu 8.0e-7). Per clip: `solver.stops` counts the frames by reason; `solutions/*.npz` has `stop`.
- Cloud dry run: dev passes with the same reached frames; every frame converges (9 did not); at most 79 iterations
  (was 150); 6:30 for 14 clips (was 8:03); soles <= 1.2 mm, trunk ratio <= 1.008.

### Changed (R026b follow-ups)
- M0: the run passes on the dev split only; held-out is reported apart; the leg length of a subject is also compared
  across the two splits (reported); "no double touchdowns" means the same foot twice within 0.2 s (alternating feet
  0.17 s apart are a real quick step); `signals.same_foot_gap_s`.
- Spec: FORCE's "subject" is a recording session, so a FORCE clip is held out by its object only; the M1 decisions in
  the revision table.

## [0.3.2] — 2026-11-01 (full-optimization line: one standard input; dev and held-out splits)

### Added (Kevin: the method must not fit only this dataset)
- `h2d/fullopt/hoi.py`: the line's only input, like OmniRetarget's: world joint positions under semantic names,
  the object mesh and its pose trajectory, optional hand contact labels; save / load as `.npz`, `validate` (joints,
  shapes, units, z up, floor), and the adapter from the common clip layout (OMOMO_new, FORCE).
- `configs/fullopt/formats.yaml`: joint mappings `common_clip` and `smpl` (SMPL, SMPL-H, SMPL-X names).
- `scripts/fullopt/export_hoi.py`: tasks of `prepare_tasks.py` runs -> HOI clips, split into dev (the tasks both
  lines solve) and held-out (every other passing press task, by a rule fixed before any result).
- Spec v0.2 (`docs/spec/fullopt/v0.2_zh.md`): generalization rules (§0.2), the input format (§2.1), the robot
  description (§7.4), dev and held-out evaluation (§8.5), milestone M0'.

### Changed
- `signals.py` and M0 read only HOI clips; M0 checks the inputs and reports the dev and held-out splits apart.

### Fixed (R026)
- `validate` checks z up and metres on the person's most upright 10 % of frames instead of the whole-clip median,
  which crouching over a box or bending over a low bin pulls down (head above the ankles 0.70-0.77 m in the median,
  1.47-1.49 m standing).
- `export_hoi.py` lists every skipped row with its reason, including segments already exported.

## [0.3.1] — 2026-10-31 (full-optimization line: spec v0.1 and M0)

### Added
- `docs/spec/fullopt/v0.1_zh.md`: the full-optimization line as discussed with Kevin. Per-frame whole-body solve
  in two passes; the human-object interaction network mapped as a whole to a dog-object network (topology transport
  and per-type edge maps), vertex substitution as the baseline; gait: when to move from the human, how from the dog
  (lateral-sequence walk by default, trot only in fast segments), bounded soft synchronisation with the human's steps
  (delta to be chosen by a sweep), single needed steps when the human shuffles; G1 bridge as a comparison;
  evaluation and milestones.
- M0 (`scripts/fullopt/m0_gait_stats.py`, `h2d/fullopt/{signals,gait}.py`, `configs/fullopt/gait.yaml`): human foot
  contacts, touchdowns and segments on the solvable tasks, leg length, step frequency against Alexander's relation,
  the B2 hip height from the model, and the dog's natural footfalls per human step with the share lockable per delta.
  It checks the measurement only (no double touchdowns, alternating feet, a leg length that does not depend on
  posture: bone lengths plus the flat-foot ankle height, the same across one subject's clips); step frequencies are data: R023 found people take short quick steps around objects (median 1.93 Hz
  at 0.53 m/s), so the dog/human ratio is mostly near 2, not 3.
- The full-optimization line is kept apart from the learned line (Kevin): its code is only in `*/fullopt/`, it
  does not change learned code, and it selects the same tasks with its own copy of the rule
  (`h2d/fullopt/tasks.py`).

## [0.3.0] — 2026-10-31 (learned line, cleaned for release; results unchanged)

### Removed
- One-off scripts of the development: `inspect_omomo_new.py` (data format), `profile_hoi.py` (data profile),
  `b01_check_tool_geometry.py` (tool geometry check; its conventions stay covered by
  `tests/common/test_tool_geometry.py`), `xmorph_smoke.py` (first X-Morph run), `workspace_map.py` (arm workspace
  map, now summarised in `configs/candidate_selection.yaml`), `render_layouts.py` (silhouettes, superseded by
  `render_mujoco.py`), and the helpers only they used.
- Compatibility with task files v1 (`load_task` now requires the current version) and the old contact fit of the
  prior's contact site in `reach_diag.py` (it only recorded the fit).
- Specs v0.5–v0.7 (in the git history; v0.8 is cumulative).

### Changed
- Comments, docstrings and configs give the reason for each choice without run ids or names; the history is here
  and in `docs/results/`. "spec §x" refers to `docs/spec/learned/v0.8_zh.md`.
- README: the learned line, its results and the commands that reproduce them.
- MIT licence for the code (Kevin); third-party data, models and code keep their own licences.

## [0.2.2] — 2026-10-31 (videos)

### Changed (Kevin)
- `render_mujoco.py --pipeline`: choose the pipeline tiles before the layouts (default human, G1, X-Morph);
  `--pipeline human g1 --layouts mesh` gives a 1 x 3 video (human, G1, dog).
- The G1 tile says the G1 is object-unaware and its hands are loosely tracked: GMR weights hand positions 0 / 10 against
  100 for the pelvis and feet, its arms are scaled 0.74 against 0.83 for the body, so the hands stay 11-18 cm above the
  scaled contact (R020 G1, all 10 tasks; horizontally 1-13 cm). Object-aware human -> G1 retargeting (OmniRetarget) is
  planned for the full-optimization line.

## [0.2.1] — 2026-10-30 (G1 placement; results of the course version unchanged)

### Fixed (Kevin, R018 videos: the G1 sank into the object by a near-constant amount)
- SMPL-X input to GMR: `trans` is the recorded pelvis minus the SMPL-X rest pelvis joint (`human_to_g1.pelvis_rest`).
  SMPL-X adds that joint unrotated, so the human reached GMR 0.35 m off along world -y; D0 reported the offset
  (`pelvis_offset_smplx_minus_recorded_median_m`) but did not check it. Now a D0 check (`pelvis_matches_recorded`,
  1 cm).
- GMR scales the human's scene about the world origin (0.83 for the mean shape: feet stay planted, but the G1 ends
  up at 0.83 x the human's position next to an unscaled object). The scale is saved in the G1 file (`world_scale`);
  `render_mujoco.py` shows the G1 with the object scaled the same way. The G1's arms are scaled 0.74 and GMR does not
  know the object, so its hands hover a few cm off the surface (R020, c01 / c08: median 4-8 cm).
- Start-anchored registration took the G1's start (0.2-0.6 m off from the human's, both causes above); it now takes
  the human's (`src_root_pos0` = G1 start xy / world_scale). Not used by the course comparison.

Not affected: X-Morph reads joint angles, the root velocity in the heading frame and the turn rate and integrates
from the origin, so the dog prior does not depend on where the G1 is; `reach_fit`, `reach_track` and `mesh` use the
human and the object (and only the yaw of the start anchor). Confirmed by R020 (#28): B2-Z1 prior within 0.08 rad and
5.5 mm of R015 (GMR IK numerics), reached / not reached identical to R017 for every task and layout, same foot slide;
the G1 no longer enters the object (c01 47/74 -> 0 frames, c08 13/36 -> 0).

## [0.2.0] — 2026-10-30 (learned line, course version; results: `docs/results/learned_course_zh.md`)

### Added (method: spec learned v0.8 §5.4–5.6, Kevin)
- Tool pose from the human forearm and hand (§5.4): approach = forearm (elbow -> wrist, the direction the human
  pushes along) within a 45 deg cone about the inward normal of the robot's contact; roll = the hand's roll (the
  mover's hinge follows the line across the knuckles), one rule for press and grasp (`describe.hand_frame`,
  `tasks.gripper_axes`, `tasks.clamp_cone`). Finger curl is not used (OMOMO_new keeps one hand shape per clip).
  No roll target when the palm faces away (e.g. a flipped hand). Task files v2.
- Arm IK: the approach target is the task's tool x; soft roll term on the jaw axis (`roll_weight_m` 0.02, does not
  decide feasibility); `roll_median_deg` in the reachability report. Jaw axis in `configs/b2z1.yaml`.
- A push on a top face is done from the robot's side (§5.6, R013: pressing down on a low top was infeasible for all
  three tasks): the vertical face facing the robot when it reaches the side band, else the edge between that face
  and the top (`tasks.from_behind`; `contact_moved` in the task and the reports).
- Candidate selection: `grips: [press]` (side pulls need a grasp, out of scope for 11/1).
- Found in R014: the palm side is the side that touches (`palm_flipped`: the hand's points gave the palm facing
  away, 149-173 deg, on all two-hand pushes); mesh smoothness counts the trunk's actual step (the placement turns
  about the world origin, so parameter differences under-weighted turns: extra foot slide 0.4-0.7 m/s).
- Found in R015: the mesh's foot slide stayed at 0.4-0.65 m/s (the human's gait sway reached the dog), and a far
  reach (0.67-0.76 m, the human reaching across the box) lost the direction on a third of the frames: human points
  smoothed over 1 s, reach preference 5 -> 20 and r_max 0.80 -> 0.75 m. D0 wrist check 0.10 -> 0.12 m (sub3 mean
  shape: 9.7 and 10.7 cm).
- Found in R016 (mesh 9/10 fully reached, = script; relations still closer to the human): the stronger reach
  preference outweighed the clearance (c04: body 2.8 cm into the box, foot slide up to 1.56 m/s). Clearance weight
  10 -> 40 (twice the reach preference; light contact tolerated), body samples per geom 8 -> 16, smoothness 30 -> 60.
- Gripper open / close schedule in the spec (open when approaching or leaving within 0.15 m, closed in contact).
- Videos: `scripts/learned/render_layouts.py` (silhouettes, no OpenGL) and `scripts/learned/render_mujoco.py` (Kevin:
  MuJoCo, X-Morph-demo style 2 x 3 grid: human, G1, B2-Z1 straight out of X-Morph; the three body layouts with the
  arm IK; camera across the human-object line, panning with the object). `reach_diag.py` saves the body placement
  of every layout in the solution files.
- Results of the course version: `docs/results/learned_course_zh.md` (R017: mesh 9/10 fully reached like the
  script, relations closer to the human, about twice the extra foot slide).
- Test clip: the pushing hands are flat, palm on the face (the contact proxy stays where it was).
- Interaction-mesh body placement (spec v0.8 §5.5, `h2d/learned/imesh.py`, `configs/learned/mesh.yaml`): per-frame
  SE(2) of the prior's body from the human's body-object mesh (pelvis -> trunk, chest -> Z1 base, hand -> contact
  target; edge directions and heading from the human, the distance from the dog's arm), solved over the window by
  sparse least squares. `reach_diag.py`: layout `mesh` next to the script baseline (`reach_track`) and the prior
  (`reach_fit`), `--layouts`, relation metrics for every layout (edge / heading error, extra foot slide). Task
  files carry the human pelvis, chest and shoulders. Course scope for 11/1: OMOMO pushes and top-face drags.

## [0.1.5] — 2026-10-30 (released together with 0.2.0)

### Changed (method: spec learned v0.6)
- Virtual hand restored (Kevin; it was in the first method draft and narrowed to "right hand only" in v0.5):
  one hand (left or right) uses that hand; both hands on the same face use the midpoint of the two contacts;
  squeezing (opposite faces) and hand switching are excluded. Spec `docs/spec/learned/v0.6_zh.md` (Codex review
  pending); approach direction no longer required, it only ranks (no near-normal right-hand push in R005).
- `describe.contact_point` / `palm_point` take side "B"; `push_descriptors` reports `hands_face_angle_deg`.
- Candidates: `right_hand` -> `one_mode` (left / right / both), new push criterion `same_face`; mode shown in the
  tables, sheets (both hands drawn behind the midpoint) and gallery; 16 candidates by default.
- Test clip: `push_hands` = R / B (both on one face) / squeeze (opposite faces).

### Fixed (found in R007)
- SMPL-X export for GMR: 16 betas (mean shape) instead of 10; smplx builds SMPL-X with 16 betas plus 10
  expression coefficients, so 10 betas failed in `blend_shapes` for every clip.

- Reachability diagnostic (found in R008): a large contact-fit residual (the prior's path drift, spec O2) no
  longer turns every problem into `coordinate_or_tool_offset_error`; it is a note. IK is regularised towards the
  previous frame's solution (0.01 m/rad) to keep the arm on one branch between frames.

### Changed (found in R012)
- Robot grip from the interaction and the face, not from the human's fingers: OMOMO_new carries a fixed hand shape
  (finger motion 0.0 mm), and its thumb / finger contacts marked every R012 candidate a grasp. Push, and pull on a
  top face (drag): press with the closed gripper; pull on a side / slant face: grasp. The finger-based label stays
  as `human_grip` (information only).
- D0 chain: one small figure per clip (`figures/<clip>.png`; the joint figure of 19 clips exceeded 1 MB); wrist
  convention tolerance 0.10 m (a large subject reached 8.3 cm with the mean shape; convention errors are tens of cm).

### Added
- Pulls (Kevin): `interactions: [push, pull]` in `configs/candidate_selection.yaml`; `describe.grip_descriptors`
  (grasp = thumb and fingers on opposite-facing patches, else press), `finger_motion_std_m` (is there real finger
  capture? FORCE: none on chair / box_huge, ~0.02 rad on suitcase), `candidates.interaction_of / contact_shape_ok`,
  `reach_band.grasp`; caps per (dataset, object, interaction); tasks carry interaction / grip; `reach_diag` skips
  grasps until the jaw site exists.
- Reach-point registration and body tracking (found in R010; Kevin: the dog's body has to move with the
  interaction): `registration.reach_points / track / SE2Track`, `configs/registration.yaml` (reach point 0.6 /
  0.75 / 0.7 m ahead for top / side / slant faces; 1 s smoothing). Fitting the prior's contact site placed the
  body too close (the X-Morph arm stays raised), so the tool could reach top faces but not point down at them.
  `reach_diag.py` layouts: reach_fit, reach_track (extra base motion reported), start_anchored.
- Contact height adaptation (spec v0.7 §5.1, Kevin): on side / slant faces the robot's contact moves up or down the
  same face into the arm's band (same face, normal and position along the face); `tasks.adapt_height`,
  `prepare_tasks.py --selection`, `ObjectMesh.face_points`, descriptors `face_z_min_m / face_z_max_m`,
  `candidates.adapted_height` (selection uses the adapted height).
- Candidate selection for reachable cases (Kevin: low objects are out): `configs/candidate_selection.yaml` (yaw
  limit 45 deg; contact-height band per face class: side 0.5-1.2 m, top 0.3-0.8 m), `push_candidates.py
  --selection`, `candidates.criteria / face_of / in_band`; `scripts/learned/workspace_map.py` (where the Z1 can
  push around a level B2), `reach_diag.py --tasks-csv --max-tasks`.
- [common] Task targets (`h2d/common/data/tasks.py`, `scripts/common/prepare_tasks.py`; spec v0.6 §4 step 1,
  §5.2): per segment the object trajectory, contact frames, object-local contact target on the surface, one
  normal, approach / retreat distance d_t (palm-thickness zeroed) and the world target path; `tasks/<id>.npz`,
  a sheet per task, checks; also for every candidate of a candidates.csv, so a later confirmation needs no rerun.
- `configs/push_candidates.yaml`: per-segment `mode`.
- [learned] `d0_chain.py --clips-file` (e.g. `clips_omomo.txt` from `prepare_tasks.py`).
- [common] Scene registration (`h2d/common/registration.py`, `configs/registration.yaml`; spec §4 step 3):
  start-anchored and contact-fitted SE(2) of the robot root trajectory (grid + bounded refine over yaw with a
  prior towards the anchor, closed-form translation, yaw fixed when the targets barely move).
- [common] Collision checks (`h2d/common/collision.py`): moving arm vs body / itself / floor from MuJoCo geom
  distances (pairs overlapping in the folded home pose excluded), robot sample points vs the object's convex
  hull (arm, tool and frozen body reported apart).
- [learned] Frozen-body reachability diagnostic (`h2d/learned/reach.py`, `scripts/learned/reach_diag.py`,
  `configs/learned/reach.yaml`; spec §7.1): per contact frame, position / position + direction / budgeted IK
  with avoidance residuals and multi-start; failure labels with a rigorous reach bound (sum of segment lengths);
  joint speed vs the Z1 limit (180 deg/s), arm change, scene feasibility; both registrations.

## [0.1.4] — 2026-10-25 (merge `8dfde27`)

### Added
- [common] Push candidates for the reachability diagnostic (spec §7.1 step 1; `docs/data/push_candidates.md`):
  `h2d/common/data/candidates.py` (criteria in order, exclusion reasons, tiers by approach / retreat direction,
  ranking with per-object and per-clip caps, funnel) and `scripts/common/push_candidates.py` (OMOMO_new + FORCE;
  `candidates.csv`, `pool.csv` with reasons, gallery, one sheet per candidate, source-file hashes).
- [common] Push descriptors in `describe.py`: contact proxy, per-frame push alignment, patch normal of the touched
  face (spread, tilt, coherence), proxy-to-surface distance, approach / retreat angle to the normal from the palm
  path in the object frame.
- [common] `ObjectMesh.center`, `face_normals`, `closest_face`, `patch_normals` (normals signed towards the query
  point: the meshes' winding is inconsistent).
- [common] `viz_hoi.candidate_figure`, `viz_hoi.gallery`.
- `configs/push_candidates.yaml`: the three segments confirmed by Kevin from R005, with the deviation from §7.1 step 1.

### Fixed (found in R005)
- Candidate sheet: the side view of a top-face contact looked along the normal (the object collapsed to a line);
  it now looks across the push. Numbers unchanged. Test clip gained a top-face push variant.

### Changed
- Dataset sources (`OmomoSource`, `ForceSource`) moved from `profile_hoi.py` to `h2d/common/data/sources.py`;
  CSV / JSON helpers to `h2d/common/tables.py`.
- Test clip: the box is yawed so its faces are perpendicular to the world axes, the hands sit near face centres,
  and the pushing hand comes in and leaves straight along the normal.

## [0.1.3] — 2026-10-25 (merge `3e42e9b`)

### Added
- [common] SMPL-H body model in numpy (`h2d/common/body/smplh.py`): loads MANO `SMPLH_*.pkl` without chumpy
  (stub unpickler; also old-scipy sparse matrices) or an `.npz`; forward kinematics; skinning with pose blend shapes.
- [common] FORCE adapter (`h2d/common/data/force.py`, format notes in `docs/data/force_format.md`): sequence ->
  z-up `Clip` with the 52 bodies in InterMimic order; object scans from PLY; floor from the soles; per-body
  contact derived from the skinned mesh (2 cm). Frame rate 60 fps (inferred from the paper's total duration).
- [common] Generic object meshes (`h2d/common/objectmesh.py`): OBJ and PLY (ascii / binary) loading; surface
  queries through area-weighted surface samples (works for coarse scans), two-level fast approximate distance.
- Data locations `force` (pinned commit) and `smplh_models` in `configs/data.yaml`.

### Fixed (found in R004)
- SMPL-H loader: old scipy sparse pickles are rebuilt by their fields (csc/csr/coo/dia/lil); chumpy reordering
  objects (`Select` for `shapedirs` in mano_v1_2) are evaluated without chumpy; unused unconvertible entries are
  tolerated and reported.
- FORCE root convention: the pelvis is at `smpl_trans` (authors' layer is root-relative); standard SMPL put the
  body ~0.22 m too low and every object appeared to float (R004); R004b passes.

### Changed
- `scripts/common/profile_omomo.py` -> `scripts/common/profile_hoi.py --dataset {omomo_new,force}`; FORCE checks:
  data at the pinned commit, derived hand contact vs the per-sequence hand annotation, contact found; frame-rate
  information (duration vs paper, step frequency).
- `ObjectMesh` moved from `omomo_objects.py` to `h2d/common/objectmesh.py` (re-exported); exact surface
  distance now takes candidate faces from surface samples instead of nearest vertices.

## [0.1.2] — 2026-10-25 (merge `8ab1e9b`)

### Added
- [common] OMOMO_new adapter (`h2d/common/data/omomo_new.py`): typed clip, per-hand / non-hand contact
  (a hand = wrist/palm + 15 finger bodies), per-frame contact modes (none / left / right / both / body /
  unknown) with short-run removal, contact intervals, skeleton parents and body groups, SMPL-X parameters
  (y-up -> z-up body-frame permutation and per-joint `[1, 2, 0]` reorder as in the HOI-Retarget reader, BSD-3).
- [common] Object meshes (`h2d/common/data/omomo_objects.py`): the 13 InterMimic meshes shipped by
  HOI-Retarget (MIT; new pinned external `hoi_retarget`, assets only), lowest point per frame (convex hull),
  surface distance (exact point-triangle near the surface), tilt / yaw split relative to a reference frame.
- [common] Descriptive interaction segments (`h2d/common/data/describe.py`): hand-contact segments with raw
  descriptors (hands, palm vs fingers, other body parts, object clearance, displacement, tilt, yaw, human
  root motion, heading, crouch, contact height, two-hand geometry) and coarse labels
  (object: lifted / tilted / slid / turned / still; human: walk / stand) with thresholds in `DEFAULTS`.
- [common] `scripts/common/profile_omomo.py`: data profile of all clips, no selection: per-clip and
  per-segment CSVs, per-object aggregates, body-part heatmap, distributions, mesh/pose and floor checks,
  per-object example keyframes (+ optional MP4). `h2d/common/viz_hoi.py` draws them.
- [learned] `h2d/learned/human_to_g1.py`: GMR SMPL-X -> G1 with a convention self-check
  (mean-shape vs recorded pelvis-relative wrists).
- [learned] `scripts/learned/d0_chain.py`: first end-to-end chain OMOMO_new -> GMR -> G1 -> X-Morph -> B2-Z1
  on explicitly given clips (not run yet; clips are chosen after the data profile).

### Fixed
- `.gitignore`: `data/` also matched `h2d/common/data/` and `docs/data/`, so `docs/data/omomo_new_format.md`
  (listed under 0.1.1) never reached `main`, and the OMOMO_new adapter was missing from the PR branch.
  Now only the top-level `/data/` and `/outputs/` are ignored.

### Changed
- Candidate screening for single-hand floor pushes was dropped before it ran: the data is profiled
  first (R003), selection criteria come after.

## [0.1.1] — 2026-10-25 (merge `e7a7f5e`)

### Fixed
- [env] Pin `mujoco==3.11.0` instead of 3.17.0. pytorch-kinematics 0.10.0, which X-Morph inference uses to
  build its FK chain, cannot parse MJCF joint types from MuJoCo ≥ 3.12 (`KeyError: 3`); 3.11.0 is the
  newest compatible release (checked 3.4–3.16). B01 under 3.11.0 matches the 3.3.7 reference
  (mover distance 8.36e-10 m); GMR + mink 1.3.0 install and initialize with it.

### Added
- [learned] X-Morph prior wrapper (`h2d/learned/prior.py`): runs the pinned checkout via `PYTHONPATH`
  (never pip-installed), truncates X-Morph's padded output (e.g. 281 → 284 frames) back to the input
  length, writes a source sidecar (start pose, lengths, command, runtime).
- [learned] `scripts/learned/xmorph_smoke.py`: inference check with pipeline alignment test (root-speed
  lag) and recorded X-Morph behaviour (arm timing lag, path-length ratio, heading drift).
- [common] `scripts/common/inspect_omomo_new.py`: read-only structure report for OMOMO_new `*.pt`.
- Configs: `configs/learned/xmorph.yaml`, `configs/data.yaml`; extras `[xmorph]` in `pyproject.toml`.
- [env] `constraints.txt` (numpy<2, opencv-python<4.12, mujoco 3.11.0, pytorch-kinematics 0.10.0): GMR's
  unpinned opencv pulled numpy 2.x on Ubuntu (R002).
- [docs] `docs/data/omomo_new_format.md`: OMOMO_new column layout, incl. per-body contact flags.

## [0.1.0] — 2026-10-25 (merge `752eaaa`)

### Added
- [common] B2-Z1 robot model wrapper (`h2d/common/robot.py`): one MuJoCo model for kinematics and collision,
  tool frame, contact site, analytic Jacobians.
- [common] Exact point-to-mesh distance (`h2d/common/meshgeom.py`).
- [common] Run provenance and refusal rules (`h2d/common/runinfo.py`).
- [common] B01 tool / collision geometry check (`scripts/common/b01_check_tool_geometry.py`).
- Configs: `configs/b2z1.yaml`, `configs/external.yaml` (X-Morph `a9f4a77`, GMR `25f56db`).
- Docs: learned-line spec v0.5, versioning rules, Ubuntu setup, collaboration protocol (`CLAUDE.md`).

### Changed
- Pin `mujoco==3.17.0` (was `>=3.1`) after R001 showed float32-level mesh differences across versions.
  Superseded in 0.1.1 (3.17.0 breaks X-Morph inference).
