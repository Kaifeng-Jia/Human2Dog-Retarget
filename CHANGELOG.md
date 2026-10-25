# Changelog

Format: one section per version, newest first. Versioning rules: `docs/versioning.md`.

## [0.1.1] — unreleased

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
