# Push candidates (spec §7.1 step 1)

Run `R026_candidates_force` · code `v0.3.1-1-g8877af2` (dirty=False) · force 398 files, 696 segments · 0 errors · 5.1 min

**Checks: FAIL** — all_files_processed: pass, enough_candidates: FAIL, contact_proxy_on_surface: pass, force_data_pinned: pass

## Criteria (in order) and how many segments are left

| criterion | rule | meaning | force |
|---|---|---|---|
| all segments | | | 696 |
| slid | `object_state == slid` | object slides on the floor (moves >= 0.10 m, not lifted or tilted) | 146 |
| on_floor | `obj_lifted_frac <= 0.1` | object lowest point > 5 cm in at most 10 % of the frames | 145 |
| one_mode | `hands in ('left', 'right', 'both')` | one hand, or both hands together, in >= 60 % of the contact frames (no switching) | 108 |
| long_enough | `duration_s >= 1.0` | contact lasts at least 1 s | 97 |
| small_tilt | `obj_tilt_max_deg < 10.0` | object tilts less than 10 deg | 95 |
| small_yaw | `obj_yaw_maxabs_deg < 45.0` | object turns less than 45 deg about z | 15 |
| hand_only | `frac_body < 0.05` | other body parts touch in < 5 % of the frames | 14 |
| same_face | `hands_face_angle_deg <= 30.0` | both hands on the same face (0 for one hand; squeeze fails) | 7 |
| on_surface | `contact_surface_dist_median_m <= 0.08` | hand contact proxy within 8 cm of the surface | 7 |
| interaction | `interaction in ('push', 'pull')` | object moves away from (push) or towards (pull) the hand, abs(cos) >= 0.7: push/pull | 5 |
| contact_shape | `contact_shape_ok == True` | one flat face (press), or a grasp | 3 |
| grip | `grip in ('press',)` | robot grip: press | 1 |
| reach_band | `in_reach_band == True` | contact height within the arm's band (side 0.5-1.2 m, top 0.3-0.8 m, slant 0.4-1.2 m, grasp 0.3-1.2 m) | 1 |

Ranking: tier (A = approach and retreat observed and within 30° of the normal; B = within, but one is not observable; C = sideways), then a vertical face (tilt ≤ 30°), then duration × displacement; at most 6 per object, one per clip.

Passing segments by virtual-hand mode (R = right hand, L = left hand, B = both hands on one face): R 1

Passing segments by interaction / grip: force/push/press 1

Finger motion (median std of fingertips in the wrist frame; ~0 = fixed hand shape): force 0.7 mm

## Candidates

![gallery](gallery.png)

| # | tier | mode | interaction / grip | dataset / object | clip | segment [s] | moves [m] | push | spread p90 [°] | face tilt [°] | approach / retreat [°] | contact z [m] | figure |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | C | R | push / press | force / backpack | 0630_61-2 | 15.7–17.4 | 0.19 | 0.99 | 17.2 | 57.0 | 127.9 / 57.6 | 0.49 | [png](candidates/01_0630_61-2.png) |

## Slid segments per object (passed / slid, most common first failure)

| dataset / object | slid | passed | first failure |
|---|---|---|---|
| force/backpack | 3 | 1 | small_tilt 1, contact_shape 1 |
| force/box_huge | 56 | 0 | small_yaw 25, one_mode 16, long_enough 7, same_face 4 |
| force/chair | 86 | 0 | small_yaw 55, one_mode 21, long_enough 4, same_face 3 |
| force/plasticcontainer | 1 | 0 | on_floor 1 |
