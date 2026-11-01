# Push candidates (spec §7.1 step 1)

Run `R028_grasp_candidates` · code `v0.3.2-3-g04df1ca` (dirty=False) · omomo_new 4421 files, 4270 segments · force 398 files, 696 segments · 0 errors · 6.7 min

**Checks: PASS** — all_files_processed: pass, enough_candidates: pass, contact_proxy_on_surface: pass, force_data_pinned: pass

## Criteria (in order) and how many segments are left

| criterion | rule | meaning | omomo_new | force |
|---|---|---|---|---|
| all segments | | | 4270 | 696 |
| slid | `object_state == slid` | object slides on the floor (moves >= 0.10 m, not lifted or tilted) | 1037 | 146 |
| on_floor | `obj_lifted_frac <= 0.1` | object lowest point > 5 cm in at most 10 % of the frames | 1022 | 145 |
| one_mode | `hands in ('left', 'right', 'both')` | one hand, or both hands together, in >= 60 % of the contact frames (no switching) | 936 | 108 |
| long_enough | `duration_s >= 1.0` | contact lasts at least 1 s | 899 | 97 |
| small_tilt | `obj_tilt_max_deg < 10.0` | object tilts less than 10 deg | 791 | 95 |
| small_yaw | `obj_yaw_maxabs_deg < 360.0` | object turns less than 360 deg about z | 791 | 92 |
| hand_only | `frac_body < 0.05` | other body parts touch in < 5 % of the frames | 735 | 36 |
| same_face | `hands_face_angle_deg <= 30.0` | both hands on the same face (0 for one hand; squeeze fails) | 491 | 20 |
| on_surface | `contact_surface_dist_median_m <= 0.08` | hand contact proxy within 8 cm of the surface | 489 | 20 |
| interaction | `interaction in ('pull',)` | object moves away from (push) or towards (pull) the hand, abs(cos) >= 0.7: pull | 145 | 6 |
| contact_shape | `contact_shape_ok == True` | one flat face (press), or a grasp | 133 | 5 |
| grip | `grip in ('grasp',)` | robot grip: grasp | 129 | 5 |
| reach_band | `in_reach_band == True` | contact height within the arm's band (side 0.5-1.2 m, top 0.3-0.8 m, slant 0.4-1.2 m, grasp 0.15-1.2 m) | 129 | 5 |

Ranking: tier (A = approach and retreat observed and within 30° of the normal; B = within, but one is not observable; C = sideways), then a vertical face (tilt ≤ 30°), then duration × displacement; at most 2 per object, one per clip.

Passing segments by virtual-hand mode (R = right hand, L = left hand, B = both hands on one face): B 10, L 60, R 64

Passing segments by interaction / grip: force/pull/grasp 5, omomo_new/pull/grasp 129

Finger motion (median std of fingertips in the wrist frame; ~0 = fixed hand shape): omomo_new 0.0 mm, force 0.7 mm

## Candidates

![gallery](gallery.png)

| # | tier | mode | interaction / grip | dataset / object | clip | segment [s] | moves [m] | push | spread p90 [°] | face tilt [°] | approach / retreat [°] | contact z [m] | figure |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | A | L | pull / grasp | omomo_new / woodchair | sub12_woodchair_004 | 0.6–9.2 | 1.43 | -0.93 | 179.4 | 10.8 | 26.6 / 24.9 | 0.85 | [png](candidates/01_sub12_woodchair_004.png) |
| 2 | A | R | pull / grasp | omomo_new / whitechair | sub4_whitechair_036 | 6.6–8.4 | 0.66 | -0.93 | 150.8 | 24.0 | 21.5 / 29.8 | 0.75 | [png](candidates/02_sub4_whitechair_036.png) |
| 3 | B | R | pull / grasp | omomo_new / woodchair | sub2_woodchair_009 | 0.0–4.4 | 2.05 | -0.99 | 1.3 | 10.8 | – / – | 0.85 | [png](candidates/03_sub2_woodchair_009.png) |
| 4 | B | R | pull / grasp | omomo_new / largebox | sub16_largebox_039 | 0.0–3.3 | 1.01 | -0.91 | 23.7 | 14.0 | – / 7.6 | 0.33 | [png](candidates/04_sub16_largebox_039.png) |
| 5 | B | R | pull / grasp | omomo_new / smalltable | sub9_smalltable_003 | 0.0–2.1 | 1.40 | -0.98 | 47.5 | 3.0 | – / – | 0.33 | [png](candidates/05_sub9_smalltable_003.png) |
| 6 | B | B | pull / grasp | omomo_new / largetable | sub15_largetable_003 | 0.0–3.6 | 0.75 | -0.78 | 44.6 | 10.4 | – / – | 0.51 | [png](candidates/06_sub15_largetable_003.png) |
| 7 | B | B | pull / grasp | omomo_new / largetable | sub15_largetable_005 | 0.0–3.6 | 0.71 | -0.98 | 45.1 | 8.6 | – / – | 0.51 | [png](candidates/07_sub15_largetable_005.png) |
| 8 | B | L | pull / grasp | omomo_new / whitechair | sub4_whitechair_043 | 0.0–4.1 | 0.56 | -0.86 | 161.5 | 19.0 | – / 14.8 | 0.77 | [png](candidates/08_sub4_whitechair_043.png) |
| 9 | B | R | pull / grasp | omomo_new / trashcan | sub15_trashcan_060 | 0.0–1.9 | 0.47 | -0.89 | 12.5 | 19.1 | – / – | 0.36 | [png](candidates/09_sub15_trashcan_060.png) |
| 10 | C | B | pull / grasp | omomo_new / smalltable | sub12_smalltable_079 | 3.8–8.7 | 2.25 | -0.70 | 31.1 | 11.3 | 95.4 / 29.4 | 0.33 | [png](candidates/10_sub12_smalltable_079.png) |
| 11 | C | B | pull / grasp | omomo_new / plasticbox | sub5_plasticbox_037 | 0.0–6.2 | 1.51 | -0.92 | 54.6 | 6.7 | – / 84.5 | 0.30 | [png](candidates/11_sub5_plasticbox_037.png) |
| 12 | C | B | pull / grasp | omomo_new / suitcase | sub14_suitcase_020 | 0.2–6.0 | 1.35 | -0.94 | 9.3 | 0.7 | 67.3 / 82.9 | 0.48 | [png](candidates/12_sub14_suitcase_020.png) |
| 13 | C | L | pull / grasp | omomo_new / plasticbox | sub12_plasticbox_048 | 1.1–9.2 | 0.97 | -0.88 | 15.2 | 5.1 | 38.0 / 22.1 | 0.27 | [png](candidates/13_sub12_plasticbox_048.png) |
| 14 | C | L | pull / grasp | omomo_new / trashcan | sub8_trashcan_045 | 4.0–7.2 | 1.67 | -0.98 | 24.9 | 2.7 | 127.7 / 128.6 | 0.33 | [png](candidates/14_sub8_trashcan_045.png) |
| 15 | C | L | pull / grasp | omomo_new / suitcase | sub1_suitcase_062 | 0.1–3.4 | 1.39 | -0.74 | 44.4 | 16.9 | 53.3 / 40.4 | 0.53 | [png](candidates/15_sub1_suitcase_062.png) |
| 16 | C | R | pull / grasp | omomo_new / largebox | sub16_largebox_041 | 0.8–3.4 | 1.09 | -0.95 | 146.8 | 7.3 | 66.4 / 143.5 | 0.32 | [png](candidates/16_sub16_largebox_041.png) |

## Slid segments per object (passed / slid, most common first failure)

| dataset / object | slid | passed | first failure |
|---|---|---|---|
| omomo_new/clothesstand | 23 | 0 | interaction 7, hand_only 5, small_tilt 3, on_floor 2 |
| omomo_new/floorlamp | 73 | 0 | interaction 29, hand_only 18, same_face 9, on_floor 7 |
| omomo_new/largebox | 126 | 2 | interaction 61, same_face 29, one_mode 21, long_enough 9 |
| omomo_new/largetable | 124 | 13 | same_face 53, small_tilt 28, interaction 17, one_mode 9 |
| omomo_new/monitor | 7 | 4 | small_tilt 3 |
| omomo_new/plasticbox | 114 | 16 | interaction 38, same_face 24, small_tilt 16, one_mode 11 |
| omomo_new/smallbox | 132 | 0 | interaction 91, same_face 15, one_mode 10, hand_only 8 |
| omomo_new/smalltable | 123 | 29 | same_face 37, interaction 24, small_tilt 13, one_mode 9 |
| omomo_new/suitcase | 115 | 4 | interaction 44, same_face 43, one_mode 9, hand_only 7 |
| omomo_new/trashcan | 65 | 28 | small_tilt 14, interaction 12, same_face 10, one_mode 1 |
| omomo_new/tripod | 7 | 0 | small_tilt 3, on_floor 2, same_face 1, long_enough 1 |
| omomo_new/whitechair | 74 | 26 | interaction 16, same_face 11, small_tilt 9, one_mode 7 |
| omomo_new/woodchair | 54 | 7 | hand_only 12, small_tilt 12, same_face 10, interaction 5 |
| force/backpack | 3 | 0 | interaction 2, small_tilt 1 |
| force/box_huge | 56 | 3 | one_mode 16, interaction 12, same_face 9, hand_only 8 |
| force/chair | 86 | 2 | hand_only 48, one_mode 21, same_face 7, long_enough 4 |
| force/plasticcontainer | 1 | 0 | on_floor 1 |
