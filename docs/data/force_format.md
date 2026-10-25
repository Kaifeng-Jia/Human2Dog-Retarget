# FORCE: what the public release contains

Zhang et al., *FORCE: Dataset and Method for Intuitive Physics Guided Human-object Interaction*, 3DV 2025.
Data repository: `github.com/xz6014/FORCE_dataset`, pinned at `695c8b8` (2025-01-21) in `configs/data.yaml`.
No licence file: research use only, never commit or redistribute.

Checked in the cloud on 2026-10-25 (repository files only; numbers below are from the release, not the paper).

| item | content |
|---|---|
| sequences | 398 `force_npz/*.npz` (the paper reports 450); `annotations_final/` lists 539 names, all 398 included |
| objects | backpack 33, plasticcontainer 57, suitcase 151, laundrybasket 37, chair 65, box_huge 55 (paper: 8 objects) |
| per frame | `smpl_pose` (T, 156) SMPL-H axis-angle (root + 21 body + 30 hand joints), `smpl_trans` (T, 3), `obj_pose` (T, 3) axis-angle, `obj_trans` (T, 3) |
| world | y-up (pelvis height ~0.95 m on y); the adapter rotates +90° about x into z-up |
| object meshes | `assets/*.ply` scans, 500-8000 vertices; the pose applies to the scan centred at its bounding-box centre (authors' `visualize_force_dataset.py`) |
| body shape | one `assets/betas.pkl` (10 betas, male), used for every sequence |
| per sequence | `objs`, `hands` (L / R / B), `dirs` (L / R / F / B / empty), `weights` (added kg: 0-30), `success` (1 / 2 / 3, undocumented) |
| frame rate | not documented. 60 fps assumed: 467,378 frames / 60 fps = 130 min, the paper's 141.5 min scaled to 398 of 450 sequences is 125 min |
| contact labels | not released; derived here from the skinned SMPL-H mesh (a body touches the object when one of its vertices is within 2 cm of the surface) |

Hands per sequence (release): box_huge 55 B; chair 63 B, 1 L, 1 R; suitcase 76 B, 38 L, 37 R; backpack 19 L, 14 R;
plasticcontainer 57 B; laundrybasket 37 B. On-floor motion (object height range < 0.1 m) is box_huge 54/55 and chair
65/65; the single-hand suitcase sequences on the floor barely move the case (0.1-0.2 m at 25-30 kg added).

Adapter: `h2d/common/data/force.py` (z-up `Clip` with the 52 bodies in InterMimic order, derived per-body contact,
floor from the soles). SMPL-H model: `h2d/common/body/smplh.py` (no chumpy).
