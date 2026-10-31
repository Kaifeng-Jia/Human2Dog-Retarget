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
| root convention | the pelvis joint is at `smpl_trans` (the authors' `SMPL_Layer('male', hands=True)` passes `'male'` as `normalise`, i.e. root-relative body + trans; standard SMPL would put the body ~0.22 m too low) |
| per sequence | `objs`, `hands` (L / R / B), `dirs` (L / R / F / B / empty), `weights` (added kg: 0-30), `success` (1 / 2 / 3, undocumented) |
| frame rate | not documented. 60 fps assumed: 467,378 frames / 60 fps = 130 min, the paper's 141.5 min scaled to 398 of 450 sequences is 125 min |
| contact labels | not released; derived here from the skinned SMPL-H mesh (a body touches the object when one of its vertices is within 2 cm of the surface) |

Hands per sequence (release): box_huge 55 B; chair 63 B, 1 L, 1 R; suitcase 76 B, 38 L, 37 R; backpack 19 L, 14 R;
plasticcontainer 57 B; laundrybasket 37 B. On-floor motion (object height range < 0.1 m) is box_huge 54/55 and chair
65/65; the single-hand suitcase sequences on the floor barely move the case (0.1-0.2 m at 25-30 kg added).

Adapter: `h2d/common/data/force.py` (z-up `Clip` with the 52 bodies in InterMimic order, derived per-body contact,
floor from the soles). SMPL-H model: `h2d/common/body/smplh.py` (no chumpy).

## Profile (real SMPL-H male)

All checks pass: floor at z = 0 for the pushed objects (box_huge −0.012 m, chair −0.017 m lowest point over the
clip), derived contact found in 99 % of box/chair sequences, single-hand annotation agreement 0.88.

* **Push / pull on the floor**: box_huge 56 "slid" segments (both 18, left 7, right 15, mixed 16), chair 86
  (both 52, left 6, right 7, mixed 21). Hand contact at 0.62 m (box) and 0.79 m (chair backrest). Slid segments
  last 2.2 / 4.7 / 8.9 s (quartiles); first hand contact at 2.8 / 4.1 / 6.5 s (10/50/90 %), so the approach
  phase is in the data, unlike OMOMO_new.
* Other objects are mostly lifted and carried. Single-hand suitcase sequences: derived contact in 76 %; the
  annotated hand stays ~1.3 cm from the scan (handle not modelled), so suitcase contacts are not reliable.
  laundrybasket: annotated hand ~6 cm from the scan.
* "Other body parts" (forearm, torso, pelvis, thigh within 2 cm) are frequent for carried objects (suitcase,
  container, basket held against the body) and rare for box_huge.
