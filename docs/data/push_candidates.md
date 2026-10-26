# Push candidates for the first reachability diagnostic

Spec learned v0.5 §7.1 step 1: three hand-confirmed segments, "right hand, same-face push, near-normal approach,
small change of object orientation", with every candidate and its exclusion reasons recorded. The same record is
an input shared by both lines (spec §0.1), so the code lives in `common`.

Script: `scripts/common/push_candidates.py` (both datasets by default). Criteria and ranking:
`h2d/common/data/candidates.py`. Descriptors: `push_descriptors` in `h2d/common/data/describe.py`.

## Descriptors (per segment, right hand)

| descriptor | definition |
|---|---|
| contact proxy | mean of the hand bodies flagged in contact, else the palm centre (wrist + 4 finger bases); joint centres, so a few cm off the skin |
| `push_alignment` | mean over frames with object speed > 5 cm/s of cos(object horizontal velocity, object centre − contact proxy); +1 push, −1 pull |
| patch normal | closest surface point to the proxy; mean of the face normals of the surface samples within 3 cm, each signed towards the hand (handles thin parts and the meshes' inconsistent winding); `patch_coherence` = length before normalising (1 flat, low on edges and corners) |
| `normal_local` | segment mean of the patch normal in the object frame; `normal_spread_p90_deg` = spread of the per-frame normals around it; `normal_tilt_median_deg` = tilt from the horizontal in the world |
| `approach_angle_deg` / `retreat_angle_deg` | last 10 cm of palm path before first contact / first 10 cm after release, in the object frame (searched up to 2 s), angle to the inward / outward normal; NaN when not observable |

Mesh winding, checked on all 19 meshes: consistent and outward only for the closed boxes (largebox, smallbox,
suitcase, trashcan, box_huge); the chairs, tables and open boxes are thin or open, and FORCE's
`suitcase_flipped.ply` is inverted. Hence the hand-side signing. The largebox mesh's local axes are turned ~30°
against its faces, so "local −x" is not a face normal.

## Criteria (in order) and ranking

Segment criteria: slid; on the floor (lifted in ≤ 10 % of frames); right hand only (≥ 60 % of contact
frames); ≥ 1 s; tilt < 10°; |yaw| < 20°; other body parts in < 5 % of frames.
Push criteria (computed only after the segment criteria pass): proxy ≤ 8 cm from the surface; push alignment
≥ 0.7; normal spread p90 ≤ 20°; patch coherence ≥ 0.8.

Ranking: tier A (approach and retreat observed, both ≤ 30° from the normal) before B (what is observed is
≤ 30°, the rest not observable; OMOMO_new clips usually start in contact) before C (sideways entry or exit, spec
§5.2 "not covered by the current path template"); then a vertical face (tilt ≤ 30°); then duration ×
displacement. At most 2 per (dataset, object), one per clip, 12 in total.

These are development initial values for proposing candidates, not evaluation thresholds (the tool-axis
threshold of the diagnostic is 15°, spec §5.2 / §7.1).

## Outputs

`candidates.csv`, `pool.csv` (every slid segment with the criteria it fails), `gallery.png` (one frame per
candidate), `candidates/<rank>_<clip>.png` (keyframes with the proxy and the normal; top view of object, root
and palm; the contact on the object seen from the hand and from the side with the approach and retreat paths;
timeline of contacts, speeds and push alignment; the numbers), `summary.json` (criteria, funnel per dataset,
candidates with frame ranges and source-file hashes).

The three confirmed segments will be recorded in a config file, so later runs read them instead of re-ranking.
