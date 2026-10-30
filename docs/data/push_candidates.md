# Push candidates for the first reachability diagnostic

Spec learned v0.6 §7.1 step 1: hand-confirmed segments, one virtual-hand mode (§5.1: one hand, or both hands on
the same face), same-face push, small change of object orientation, with every candidate and its exclusion reasons
recorded. Approach direction only ranks (v0.6 §5.2; v0.5 also required a near-normal approach and the right hand). The same record is
an input shared by both lines (spec §0.1), so the code lives in `common`.

Script: `scripts/common/push_candidates.py` (both datasets by default). Criteria and ranking:
`h2d/common/data/candidates.py`. Descriptors: `push_descriptors` in `h2d/common/data/describe.py`.

## Descriptors (per segment, for its virtual hand)

The segment's hand label gives the mode: `right` -> R, `left` -> L, `both` -> B; `mixed` (hands switching) is
excluded.

| descriptor | definition |
|---|---|
| contact proxy | R / L: mean of that hand's bodies flagged in contact, else its palm centre (wrist + 4 finger bases); joint centres, so a few cm off the skin. B: midpoint of the two hands' proxies where both touch (the touching hand's where one does); palm path = midpoint of the two palms |
| `hands_face_angle_deg` | B: median angle between the patch normals under the two hands while both touch (0 same face, 180 opposite faces = squeezing); 0 for one hand |
| `push_alignment` | mean over frames with object speed > 5 cm/s of cos(object horizontal velocity, object centre − contact proxy); +1 push, −1 pull |
| patch normal | closest surface point to the proxy; mean of the face normals of the surface samples within 3 cm, each signed towards the hand (handles thin parts and the meshes' inconsistent winding); `patch_coherence` = length before normalising (1 flat, low on edges and corners) |
| `normal_local` | segment mean of the patch normal in the object frame; `normal_spread_p90_deg` = spread of the per-frame normals around it; `normal_tilt_median_deg` = tilt from the horizontal in the world |
| `approach_angle_deg` / `retreat_angle_deg` | last 10 cm of palm path before first contact / first 10 cm after release, in the object frame (searched up to 2 s), angle to the inward / outward normal; NaN when not observable |

Mesh winding, checked on all 19 meshes: consistent and outward only for the closed boxes (largebox, smallbox,
suitcase, trashcan, box_huge); the chairs, tables and open boxes are thin or open, and FORCE's
`suitcase_flipped.ply` is inverted. Hence the hand-side signing. The largebox mesh's local axes are turned ~30°
against its faces, so "local −x" is not a face normal.

## Criteria (in order) and ranking

Segment criteria: slid; on the floor (lifted in ≤ 10 % of frames); one mode (left, right or both in ≥ 60 % of
contact frames; R005 used right only); ≥ 1 s; tilt < 10°; |yaw| < 20°; other body parts in < 5 % of frames.
Push criteria (computed only after the segment criteria pass): both hands on the same face (≤ 30°); proxy ≤ 8 cm
from the surface; push alignment ≥ 0.7; normal spread p90 ≤ 20°; patch coherence ≥ 0.8.

Ranking: tier A (approach and retreat observed, both ≤ 30° from the normal) before B (what is observed is
≤ 30°, the rest not observable; OMOMO_new clips usually start in contact) before C (sideways entry or exit, spec
§5.2 "not covered by the current path template"); then a vertical face (tilt ≤ 30°); then duration ×
displacement. At most 2 per (dataset, object), one per clip, 16 in total (R005: 12).

These are development initial values for proposing candidates, not evaluation thresholds (the tool-axis
threshold of the diagnostic is 15°, spec §5.2 / §7.1).

## Outputs

`candidates.csv`, `pool.csv` (every slid segment with the criteria it fails), `gallery.png` (one frame per
candidate), `candidates/<rank>_<clip>.png` (keyframes with the proxy and the normal; top view of object, root
and palm; the contact on the object seen from the hand and from the side with the approach and retreat paths;
timeline of contacts, speeds and push alignment; the numbers), `summary.json` (criteria, funnel per dataset,
candidates with frame ranges and source-file hashes).

## R005 result and the confirmed segments

R005 (`01985ab`): 11 segments pass all criteria (OMOMO_new 10, FORCE 1), 8 proposed after the caps, none in tier A.
People bring the hand down onto the face from above (30-75 deg from the normal), and single right-hand pushes of
low boxes are mostly on the top face; FORCE box / chair pushes are mostly two-handed or turn the object.
Kevin confirmed three OMOMO_new segments (one side-face, two top-face pushes; contact at 0.14, 0.17, 0.36 m),
recorded in `configs/push_candidates.yaml` with the deviation note; later runs read them from there.

## Task targets

`scripts/common/prepare_tasks.py` turns each confirmed segment (and, with `--candidates`, every candidate) into
`tasks/<id>.npz` (`h2d/common/data/tasks.py`, load with `load_task`): window of 1 s before and after the contact,
object pose per frame (unchanged), `in_contact`, `c_bar_local` (contact target on the surface, object frame),
`n_bar_local` (one normal, towards the hand), `d` (palm distance to the contact plane, zeroed by its median in
contact), `target_local` / `target_world` (c~_t = c_bar_ref + d_t n_bar, spec §5.2), `palm_world`.
