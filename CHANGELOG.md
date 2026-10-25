# Changelog

Format: one section per version, newest first. Versioning rules: `docs/versioning.md`.

## [0.1.2] — unreleased

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
