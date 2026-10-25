# OMOMO_new format

`OMOMO_new` is InterMimic's re-processing of OMOMO: one `*.pt` file per sequence, named
`sub<N>_<object>_<seq>.pt`. Inspected in run R002 (`reports/R002_omomo_new_format`): 4421 files,
17 subjects, 13 objects; each file loads with `torch.load(weights_only=True)` as a single float32 tensor
`[T, 591]` (no dict).

Column layout, taken from the open-source HOI-Retarget reader
(`hoi_retarget/datasets/intermimic.py`, BSD-3, commit `b341dad`); used here as a format description only:

| Columns | Field | Shape per frame | Notes |
|---|---|---|---|
| 0–2 | root position | 3 | world |
| 3–6 | root rotation | 4 | quaternion **xyzw** |
| 7–8 | (unused) | 2 | zeros in all R002 samples |
| 9–161 | joint rotations | 51 × 3 | 51 joints = body list below without the pelvis; HOI-Retarget reorders each triple `[1, 2, 0]` when converting to SMPL-X axis-angle |
| 162–317 | body positions | 52 × 3 | world, in the body order below |
| 318–320 | object position | 3 | world |
| 321–324 | object rotation | 4 | quaternion xyzw |
| 325–329 | (unused) | 5 | zeros in all R002 samples |
| 330 | object-in-contact flag | 1 | 0 / 1 |
| 331–382 | per-body contact flags | 52 | 1 = in contact with the object; −1 appears as a "no data" value |
| 383–590 | body rotations | 52 × 4 | quaternion xyzw, world |

Body order (52): Pelvis, L_Hip, L_Knee, L_Ankle, L_Toe, R_Hip, R_Knee, R_Ankle, R_Toe, Torso, Spine, Chest,
Neck, Head, L_Thorax, L_Shoulder, L_Elbow, L_Wrist, L_Index1–3, L_Middle1–3, L_Pinky1–3, L_Ring1–3,
L_Thumb1–3, R_Thorax, R_Shoulder, R_Elbow, R_Wrist, R_Index1–3, R_Middle1–3, R_Pinky1–3, R_Ring1–3,
R_Thumb1–3.

Known caveats (to verify on our side before use):

* Frame 0 is often all zeros; HOI-Retarget drops it.
* No SMPL-X betas are stored. Body positions (cols 162–317) come from the recorded subject; a SMPL-X
  reconstruction with mean shape will not match them exactly.
* Object meshes: we use the 13 InterMimic re-exports shipped by HOI-Retarget (`assets/objects/objects/
  <name>/<name>.obj`, MIT), which HOI-Retarget places with the recorded object pose directly
  (`world = R(obj_rot) · v + obj_pos`). The original OMOMO `captured_objects/` meshes may use another frame.
  The convention is checked on every clip by `scripts/common/profile_omomo.py` (flagged hand bodies must
  lie on the transformed surface).
* The body named after a joint is the segment distal to it: `L_Wrist` is the palm, `L_Elbow` the forearm,
  `L_Shoulder` the upper arm, `L_Hip` the thigh, `L_Knee` the shin. A hand = wrist (palm) + 15 finger
  bodies (`HAND_BODIES`).

How the learned line will use it (spec v0.5 §5): hand contact flags (L/R palm and finger bodies) give the
interaction mode and contact intervals directly; body positions + object pose give the object-local
contact targets; the G1 prior input comes from GMR.
