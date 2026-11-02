# M1, M1g: full optimization, pass 1, relation (a) (fullopt spec v0.2 §7, §8.1, §8.6)

Run `R030_fullopt_grasp` · code `v0.3.4-4-g87eeeac` (dirty=False) · 134 clips · relation (a) · **PASS** (dev only; held-out reported apart)

| split | check | pass | detail |
|---|---|---|---|
| dev grasp | all_clips_solved | True | n: 50, n_errors: 0, qp_failures: 0 |
| dev grasp | reached | True | reached: 45, of: 48, min: 44, not_reached: {'sub12_smalltable_072_51': {'e_a': 12, 'e_t': 16, 'angle': 16, 'pads_in_part': 12, 'jaws_in_part': 12}, 'sub12_smalltable_079_113': {'e_a': 1, 'e_t': 2, 'angle': 1, 'pads_in_part': 1}, 'sub6_woodchair_046_25': {'e_c': 12, 'e_a': 24, 'e_t': 61, 'angle': 50, 'pads_in_part': 61, 'jaws_in_part': 31}}, infeasible: {'sub1_suitcase_062_4': ['section 16.4 cm wider than the jaws open (7.0 cm)'], 'sub1_suitcase_085_90': ['section 14.6 cm wider than the jaws open (7.0 cm)']} |
| dev grasp | jaws_clear_of_part | True | frames: {} |
| dev grasp | collision_free_all_frames | True | frames: {} |
| dev grasp | body_in_object | True | max_m: 0.006072386360250037, not_reached: {'sub12_smalltable_072_51': 1.0777268920070249e-06, 'sub12_smalltable_079_113': 0.016464273030887877, 'sub6_woodchair_046_25': 6.141233527684475e-06} |
| dev grasp | object_under_body | True | frames: {}, not_reached: {'sub12_smalltable_072_51': 0, 'sub12_smalltable_079_113': 5, 'sub6_woodchair_046_25': 16} |
| dev grasp | feet_on_floor | True | sole_height_max_m: 0.0011963428960408973, not_reached: {'sub12_smalltable_072_51': 0.001182886095682567, 'sub12_smalltable_079_113': 0.009359771805767136, 'sub6_woodchair_046_25': 0.0011163810353392034} |
| dev grasp | trunk_within_limits | True | ratio_max: 1.016662617511423, not_reached: {'sub12_smalltable_072_51': 1.0033953006035163, 'sub12_smalltable_079_113': 1.0333271655990903, 'sub6_woodchair_046_25': 1.0003290077120113} |
| dev grasp | converged | – | unconverged_frames: {'sub12_plasticbox_045_32': 1, 'sub12_smalltable_073_89': 1, 'sub12_smalltable_079_113': 4, 'sub3_largetable_001_45': 1} |
| dev grasp | friction | – | limit: ['sub1_largetable_004_3', 'sub1_largetable_007_12', 'sub1_largetable_009_11', 'sub1_largetable_010_9', 'sub3_largetable_000_107', 'sub3_largetable_001_45', 'sub3_largetable_002_13', 'sub3_largetable_011_3', 'sub3_largetable_027_83', 'sub3_largetable_028_66'], beyond: [] |
| heldout grasp | all_clips_solved | True | n: 84, n_errors: 0, qp_failures: 0 |
| heldout grasp | reached | – | reached: 74, of: 78, min: None, not_reached: {'sub16_plasticbox_054_79': {'pads_in_part': 12}, 'sub4_whitechair_020_3': {'e_c': 133, 'e_a': 133, 'e_t': 133, 'angle': 133}, 'sub7_whitechair_041_121': {'e_t': 1, 'angle': 1, 'pads_in_part': 1}, 'sub9_smalltable_074_50': {'pads_in_part': 6}}, infeasible: {'260923_04_3_1_246': ['leading edge -7.3 cm from the contact', 'open jaws 8 mm into the part on the approach'], '260923_05_1_retake_4_102': ['no place along the part where the jaws hold it alone', 'section 21.7 cm wider than the jaws open (7.0 cm)'], '260923_06_2_3_89': ['no place along the part where the jaws hold it alone'], 'sub14_suitcase_020_5': ['section 12.8 cm wider than the jaws open (7.0 cm)', 'leading edge -3.4 cm from the contact'], 'sub4_whitechair_018_0': ['no place along the part where the jaws hold it alone', 'section 8.2 cm wider than the jaws open (7.0 cm)'], 'sub8_suitcase_050_109': ['section 14.1 cm wider than the jaws open (7.0 cm)']} |
| heldout grasp | jaws_clear_of_part | False | frames: {'sub4_whitechair_020_3': [0, 1, 2]} |
| heldout grasp | collision_free_all_frames | True | frames: {} |
| heldout grasp | body_in_object | False | max_m: 0.011818370368215592, not_reached: {'sub16_plasticbox_054_79': 3.340135530133237e-06, 'sub4_whitechair_020_3': 3.679937543077383e-06, 'sub7_whitechair_041_121': 1.5859670275397697e-06, 'sub9_smalltable_074_50': 0.0} |
| heldout grasp | object_under_body | False | frames: {'sub17_woodchair_021_0': 24, 'sub2_woodchair_010_0': 17, 'sub4_whitechair_039_107': 16}, not_reached: {'sub16_plasticbox_054_79': 0, 'sub4_whitechair_020_3': 0, 'sub7_whitechair_041_121': 0, 'sub9_smalltable_074_50': 0} |
| heldout grasp | feet_on_floor | True | sole_height_max_m: 0.0012991700291431207, not_reached: {'sub16_plasticbox_054_79': 0.001030185864633576, 'sub4_whitechair_020_3': 0.0010204662277565613, 'sub7_whitechair_041_121': 0.0010457377000224477, 'sub9_smalltable_074_50': 0.0011292344429196244} |
| heldout grasp | trunk_within_limits | True | ratio_max: 1.0147125033992355, not_reached: {'sub16_plasticbox_054_79': 1.005994349607703, 'sub4_whitechair_020_3': 1.0012670994962105, 'sub7_whitechair_041_121': 1.0124187371038922, 'sub9_smalltable_074_50': 1.0051232777199954} |
| heldout grasp | converged | – | unconverged_frames: {'sub9_smalltable_070_55': 1, 'sub9_smalltable_076_73': 1} |
| heldout grasp | friction | – | limit: ['260923_05_1_retake_4_102', '260923_06_2_3_186', '260923_06_2_3_89', '260923_06_3_2_243', 'sub14_suitcase_020_5', 'sub15_largetable_003_0', 'sub15_largetable_005_0', 'sub16_largebox_039_0', 'sub16_largebox_041_25', 'sub16_largetable_033_54', 'sub4_whitechair_017_7', 'sub4_whitechair_018_0', 'sub4_whitechair_020_3'], beyond: [] |

Reached: contact point within 1 cm, tool axis within 15° and collision free on every contact frame (the learned line's definition). Body in object: deepest trunk or leg sample inside the object's hull, all frames / contact frames. Collision: frames where a self pair, or any geom but the soles through the floor, penetrates beyond 2 mm (all frames), and the closest self pair / geom to the floor. Under body: frames where the object's hull overlaps the box under the trunk (thicker than the penetration tolerance) and the thickest overlap. Feet: the largest horizontal path of a sole (they slide: no gait before M3); every sole is within 2 mm of the floor. Trunk: largest vertical speed, vertical and horizontal acceleration (limits 0.3 m/s, 3 and 5 m/s²) and tilt (15°). The body checks (body in object, under body, feet, trunk) are taken over the clips the reach check does not already count as failed; those clips' values are listed apart (not_reached). Relations: the fixed evaluation network on the contact frames. Unconverged: frames whose SQP stopped at the iteration cap, or on the trust-region floor with a row violated (reported, not a pass criterion).

Grasps (spec §8.6): a contact frame (the closing and the hold) is reached when the point between the pads is within 5 mm of the target along the closing axis c, 1 cm along the approach a and 2 cm along the part, both axes within 15°, collision free, the pads at most 5 mm and any other jaw part at most 2 mm (3 mm single-sheet meshes) in the part. Reached counts the feasible clips (a grasp the part's geometry allows at the contact); the others are listed with the reasons. Clear: frames from fully open to the closing, and from the release until 5 cm out, whose jaws are in the part. μ: tan(θc/2), the friction a wedge of the pads needs (limit: 0.25-0.35). Lead: fully open before the contact; closing: until θc; reopen: θc back to open at the release; release lag: robot minus human, 15 cm out.


| split | task | object | grasp | reached (frames) | e_c / e_a / e_t max [mm] | approach / closing axis max [°] | pads / jaws in part max [mm] | clear: bad frames, max [mm] | θc (gap table) / open [°], μ | lead / closing / reopen [s] | moved closing [cm] | release lag [s] | body in object [cm] | collision frames | foot slide [m] | trunk ratio | unconverged | ms / frame |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | sub1_largetable_004_3 | largetable | edge 0°, w 5.1 cm | True (100 %) | 0.4 / 1.3 / 12.7 | 10 / 5 | 3.0 / 0.0 | 0, 0.0 | 34.0 (33.8) / 45.0, 0.31 limit | 0.10* / 0.07 / 0.07 | 0.0 | 0.30 | 0.0 | 0 | 2.86 | 1.000 | 0 | 46 |
| dev | sub1_largetable_007_12 | largetable | edge 0°, w 5.2 cm | True (100 %) | 0.2 / 0.5 / 3.0 | 2 / 1 | 2.0 / 0.0 | 0, 0.0 | 34.0 (33.8) / 45.0, 0.31 limit | 0.40* / 0.07 / 0.07 | 0.0 | 0.27 | 0.0 | 0 | 2.82 | 1.000 | 0 | 33 |
| dev | sub1_largetable_009_11 | largetable | edge 0°, w 5.2 cm | True (100 %) | 0.4 / 1.2 / 4.2 | 3 / 2 | 2.0 / 0.0 | 0, 0.0 | 34.0 (34.0) / 45.0, 0.31 limit | 0.37* / 0.07 / 0.07 | 0.0 | 0.37 | 0.0 | 0 | 2.65 | 1.001 | 0 | 32 |
| dev | sub1_largetable_010_9 | largetable | edge 0°, w 5.2 cm | True (100 %) | 0.3 / 1.5 / 4.3 | 4 / 2 | 2.0 / 0.0 | 0, 0.0 | 34.5 (34.0) / 45.0, 0.31 limit | 0.30* / 0.07 / 0.07 | 0.0 | 0.37 | 0.0 | 0 | 2.59 | 1.000 | 0 | 31 |
| dev | sub3_largetable_000_107 | largetable | edge 0°, w 5.1 cm | True (100 %) | 0.3 / 1.1 / 3.7 | 3 / 2 | 2.0 / 0.0 | 0, 0.0 | 33.5 (33.8) / 45.0, 0.30 limit | 0.30 / 0.07 / 0.07 | 1.3 | 0.23 | 0.0 | 0 | 2.76 | 1.002 | 0 | 30 |
| dev | sub3_largetable_001_45 | largetable | edge 0°, w 5.1 cm | True (100 %) | 0.4 / 1.3 / 2.7 | 2 / 2 | 2.0 / 0.0 | 0, 0.0 | 33.5 (33.8) / 45.0, 0.30 limit | 0.30 / 0.07 / 0.07 | 0.4 | 0.20 | 0.0 | 0 | 3.41 | 1.007 | 1 | 38 |
| dev | sub3_largetable_002_13 | largetable | edge 0°, w 5.2 cm | True (100 %) | 0.4 / 1.3 / 13.1 | 10 / 5 | 4.0 / 0.0 | 0, 0.0 | 34.0 (34.0) / 45.0, 0.31 limit | 0.43* / 0.07 / 0.07 | 0.0 | 0.23 | 0.0 | 0 | 3.21 | 1.000 | 0 | 33 |
| dev | sub3_largetable_011_3 | largetable | edge 0°, w 5.2 cm | True (100 %) | 0.2 / 0.7 / 2.2 | 2 / 1 | 1.0 / 0.0 | 0, 0.0 | 34.5 (34.2) / 45.0, 0.31 limit | 0.10* / 0.07 / 0.07 | 0.0 | 0.23 | 0.0 | 0 | 2.07 | 1.000 | 0 | 30 |
| dev | sub3_largetable_027_83 | largetable | edge 0°, w 5.2 cm | True (100 %) | 0.2 / 1.0 / 7.3 | 5 / 3 | 2.0 / 0.0 | 0, 0.0 | 34.0 (34.0) / 45.0, 0.31 limit | 0.30 / 0.07 / 0.07 | 0.0 | 0.23 | 0.0 | 0 | 3.32 | 1.008 | 0 | 31 |
| dev | sub3_largetable_028_66 | largetable | edge 0°, w 5.2 cm | True (100 %) | 0.2 / 0.3 / 3.5 | 3 / 1 | 1.0 / 0.0 | 0, 0.0 | 34.5 (34.0) / 45.0, 0.31 limit | 0.30 / 0.07 / 0.07 | 0.0 | 0.27 | 0.0 | 0 | 3.34 | 1.005 | 0 | 32 |
| dev | sub12_plasticbox_043_23 | plasticbox | top 90°, w 1.5 cm | True (100 %) | 0.2 / 0.5 / 0.7 | 0 / 0 | 1.0 / 0.0 | 0, 0.0 | 9.5 (10.5) / 24.0, 0.08 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 2.16 | 1.005 | 0 | 32 |
| dev | sub12_plasticbox_045_32 | plasticbox | top 90°, w 1.5 cm | True (100 %) | 0.2 / 0.3 / 0.6 | 0 / 0 | 1.0 / 0.0 | 0, 0.0 | 9.5 (10.5) / 24.0, 0.08 ok | 0.30 / 0.10 / 0.10 | 0.0 | – | 0.0 | 0 | 4.28 | 1.017 | 1 | 36 |
| dev | sub12_plasticbox_048_34 | plasticbox | top 90°, w 1.5 cm | True (100 %) | 0.2 / 0.3 / 0.7 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 9.5 (10.5) / 24.0, 0.08 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 2.03 | 1.001 | 0 | 26 |
| dev | sub1_plasticbox_081_90 | plasticbox | top 90°, w 1.6 cm | True (100 %) | 0.2 / 0.6 / 1.1 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 10.0 (11.2) / 24.5, 0.09 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 2.98 | 1.008 | 0 | 33 |
| dev | sub1_plasticbox_088_69 | plasticbox | top 90°, w 1.5 cm | True (100 %) | 0.1 / 0.2 / 0.9 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 9.5 (10.5) / 24.0, 0.08 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 3.56 | 1.002 | 0 | 27 |
| dev | sub5_plasticbox_037_1 | plasticbox | top 90°, w 1.4 cm | True (100 %) | 0.1 / 0.3 / 1.7 | 1 / 1 | 2.0 / 0.0 | 0, 0.0 | 9.5 (10.5) / 24.0, 0.08 ok | 0.03* / 0.10 / 0.10 | 0.0 | 0.37 | 0.0 | 0 | 2.25 | 1.000 | 0 | 36 |
| dev | sub5_plasticbox_048_214 | plasticbox | top 90°, w 1.4 cm | True (100 %) | 0.2 / 0.3 / 0.8 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 9.8 (10.2) / 23.8, 0.09 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 5.02 | 1.002 | 0 | 24 |
| dev | sub5_plasticbox_050_178 | plasticbox | top 90°, w 1.4 cm | True (100 %) | 0.2 / 0.2 / 0.4 | 0 / 0 | 1.0 / 0.0 | 0, 0.0 | 9.8 (10.2) / 23.8, 0.09 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 3.27 | 1.000 | 0 | 21 |
| dev | sub12_smalltable_000_6 | smalltable | edge 15°, w 3.7 cm, slid -1.0 cm | True (100 %) | 0.3 / 0.6 / 3.6 | 2 / 2 | 2.0 / 0.0 | 0, 0.0 | 23.5 (25.2) / 36.5, 0.21 ok | 0.20* / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 2.16 | 1.001 | 0 | 36 |
| dev | sub12_smalltable_001_10 | smalltable | edge 15°, w 3.8 cm | True (100 %) | 0.3 / 0.8 / 2.3 | 2 / 1 | 2.0 / 0.0 | 0, 0.0 | 22.8 (26.5) / 37.2, 0.20 ok | 0.33* / 0.10 / 0.10 | 0.0 | – | 0.0 | 0 | 3.14 | 1.003 | 0 | 37 |
| dev | sub12_smalltable_002_20 | smalltable | edge 15°, w 4.2 cm | True (100 %) | 0.3 / 0.8 / 4.6 | 3 / 2 | 1.0 / 0.0 | 0, 0.0 | 25.0 (28.5) / 39.0, 0.22 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.33 | 0.0 | 0 | 3.52 | 1.000 | 0 | 33 |
| dev | sub12_smalltable_004_0 | smalltable | edge 15°, w 3.8 cm | True (100 %) | 0.2 / 0.5 / 3.1 | 2 / 1 | 2.0 / 0.0 | 0, 0.0 | 22.5 (26.2) / 37.0, 0.20 ok | 0.00* / 0.10 / 0.10 | 0.6 | 0.27 | 0.0 | 0 | 2.57 | 1.000 | 0 | 31 |
| dev | sub12_smalltable_005_24 | smalltable | edge 15°, w 3.6 cm, slid -2.0 cm | True (100 %) | 0.4 / 1.1 / 3.5 | 3 / 2 | 2.0 / 0.0 | 0, 0.0 | 23.2 (25.2) / 36.2, 0.21 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.33 | 0.0 | 0 | 2.96 | 1.001 | 0 | 27 |
| dev | sub12_smalltable_006_0 | smalltable | edge 15°, w 3.9 cm | True (100 %) | 0.6 / 0.6 / 12.2 | 8 / 5 | 2.0 / 0.0 | 0, 0.0 | 24.2 (26.5) / 37.2, 0.21 ok | 0.00* / 0.10 / 0.10 | 0.0 | 0.37 | 0.0 | 0 | 4.21 | 1.002 | 0 | 34 |
| dev | sub12_smalltable_007_0 | smalltable | edge 15°, w 3.9 cm | True (100 %) | 0.5 / 1.0 / 5.6 | 4 / 2 | 2.0 / 0.0 | 0, 0.0 | 23.0 (26.5) / 37.5, 0.20 ok | 0.00* / 0.10 / 0.10 | 0.2 | 0.30 | 0.0 | 0 | 2.45 | 1.001 | 0 | 30 |
| dev | sub12_smalltable_008_3 | smalltable | edge 15°, w 3.9 cm, slid -3.5 cm | True (100 %) | 0.5 / 1.3 / 6.4 | 4 / 3 | 3.0 / 0.0 | 0, 0.0 | 23.8 (26.8) / 37.8, 0.21 ok | 0.10* / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 4.78 | 1.001 | 0 | 40 |
| dev | sub12_smalltable_009_17 | smalltable | edge 15°, w 3.8 cm | True (100 %) | 0.3 / 0.8 / 6.3 | 4 / 3 | 3.0 / 0.0 | 0, 0.0 | 24.0 (26.2) / 37.0, 0.21 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.33 | 0.0 | 0 | 2.47 | 1.001 | 0 | 37 |
| dev | sub12_smalltable_072_51 | smalltable | edge 15°, w 3.8 cm | False (85 %) | 3.1 / 24.0 / 56.2 | 43 / 23 | 9.0 / 11.6 | 0, 0.0 | 24.0 (26.0) / 37.0, 0.21 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 4.80 | 1.003 | 0 | 31 |
| dev | sub12_smalltable_073_89 | smalltable | edge 15°, w 3.8 cm, slid -1.5 cm | True (100 %) | 0.3 / 0.7 / 2.8 | 2 / 1 | 1.0 / 0.0 | 0, 0.0 | 23.5 (26.2) / 37.0, 0.21 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 3.13 | 1.006 | 1 | 33 |
| dev | sub12_smalltable_074_126 | smalltable | edge 15°, w 4.0 cm | True (100 %) | 0.3 / 0.6 / 4.2 | 3 / 2 | 2.0 / 0.0 | 0, 0.0 | 24.0 (27.5) / 38.0, 0.21 ok | 0.30 / 0.10 / 0.10 | 0.0 | – | 0.6 | 0 | 4.68 | 1.003 | 0 | 27 |
| dev | sub12_smalltable_078_144 | smalltable | edge 15°, w 3.7 cm | True (100 %) | 0.3 / 0.7 / 2.8 | 2 / 1 | 2.0 / 0.0 | 0, 0.0 | 23.5 (25.2) / 36.5, 0.21 ok | 0.30 / 0.10 / 0.10 | 0.0 | -0.07 | 0.0 | 0 | 5.99 | 1.005 | 0 | 27 |
| dev | sub12_smalltable_079_113 | smalltable | edge 15°, w 3.9 cm | False (98 %) | 3.8 / 12.1 / 55.5 | 8 / 16 | 10.0 / 0.0 | 0, 0.0 | 23.2 (26.5) / 37.2, 0.21 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.30 | 1.6 | 0 | 4.94 | 1.033 | 4 | 57 |
| dev | sub1_suitcase_062_4 | suitcase | top 90°, w 16.4 cm, **infeasible**: section 16.4 cm wider than the jaws open (7.0 cm) | True (100 %) | 0.0 / 0.2 / 0.6 | 0 / 0 | 1.0 / 0.0 | 0, 1.0 | 21.0 (45.0) / 45.0, 0.19 ok | 0.13* / 0.13 / 0.13 | 0.0 | 0.30 | 0.0 | 0 | 2.33 | 1.001 | 0 | 50 |
| dev | sub1_suitcase_085_90 | suitcase | top 90°, w 14.6 cm, **infeasible**: section 14.6 cm wider than the jaws open (7.0 cm) | True (100 %) | 0.0 / 0.1 / 0.6 | 0 / 0 | 1.0 / 0.0 | 0, 0.0 | 24.5 (45.0) / 45.0, 0.22 ok | 0.30 / 0.13 / 0.13 | 0.0 | 0.37 | 0.0 | 0 | 3.51 | 1.001 | 0 | 42 |
| dev | sub6_trashcan_036_36 | trashcan | top 90°, w 1.4 cm | True (100 %) | 0.1 / 0.1 / 1.0 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 11.0 (10.0) / 23.5, 0.10 ok | 0.30 / 0.10 / 0.10 | 3.0 | 0.23 | 0.0 | 0 | 1.63 | 1.001 | 0 | 42 |
| dev | sub6_trashcan_037_13 | trashcan | top 90°, w 1.4 cm | True (100 %) | 0.1 / 0.2 / 1.0 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 11.0 (9.8) / 23.5, 0.10 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.23 | 0.0 | 0 | 2.28 | 1.001 | 0 | 48 |
| dev | sub6_trashcan_038_18 | trashcan | top 90°, w 1.4 cm | True (100 %) | 0.0 / 0.2 / 0.6 | 0 / 0 | 1.0 / 0.0 | 0, 0.0 | 9.2 (10.2) / 23.8, 0.08 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 1.50 | 1.000 | 0 | 47 |
| dev | sub6_trashcan_040_30 | trashcan | top 90°, w 1.4 cm | True (100 %) | 0.1 / 0.3 / 0.8 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 9.2 (10.2) / 23.8, 0.08 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 2.28 | 1.000 | 0 | 52 |
| dev | sub6_trashcan_041_28 | trashcan | top 90°, w 1.4 cm | True (100 %) | 0.1 / 0.2 / 0.5 | 0 / 0 | 1.0 / 0.0 | 0, 0.0 | 9.2 (10.2) / 23.8, 0.08 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 1.74 | 1.000 | 0 | 54 |
| dev | sub6_trashcan_048_76 | trashcan | top 90°, w 1.3 cm | True (100 %) | 0.3 / 1.0 / 0.7 | 1 / 1 | 1.0 / 0.0 | 0, 0.0 | 8.8 (9.2) / 22.8, 0.08 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 2.75 | 1.002 | 0 | 44 |
| dev | sub6_trashcan_049_114 | trashcan | top 90°, w 1.3 cm | True (100 %) | 0.3 / 0.7 / 0.9 | 1 / 1 | 1.0 / 0.0 | 0, 0.0 | 9.2 (9.2) / 22.8, 0.08 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 2.92 | 1.010 | 0 | 41 |
| dev | sub6_trashcan_050_107 | trashcan | top 90°, w 2.6 cm | True (100 %) | 0.3 / 0.5 / 0.9 | 1 / 1 | 1.0 / 0.0 | 0, 0.0 | 16.8 (18.2) / 30.8, 0.15 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 3.05 | 1.003 | 0 | 48 |
| dev | sub6_trashcan_051_86 | trashcan | top 90°, w 2.4 cm | True (100 %) | 0.7 / 2.3 / 1.7 | 2 / 1 | 1.0 / 0.0 | 0, 0.0 | 12.8 (17.2) / 29.8, 0.11 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 2.25 | 1.002 | 0 | 42 |
| dev | sub6_trashcan_052_95 | trashcan | top 90°, w 1.8 cm | True (100 %) | 0.1 / 0.3 / 0.6 | 0 / 0 | 1.0 / 0.0 | 0, 0.0 | 12.2 (13.0) / 26.2, 0.11 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.33 | 0.0 | 0 | 2.69 | 1.002 | 0 | 41 |
| dev | sub5_whitechair_019_1 | whitechair | top 90°, w 3.3 cm | True (100 %) | 0.3 / 0.4 / 1.7 | 1 / 1 | 2.0 / 0.0 | 0, 0.0 | 19.0 (22.8) / 34.5, 0.17 ok | 0.03* / 0.10 / 0.10 | 0.0 | 0.40 | 0.0 | 0 | 3.46 | 1.000 | 0 | 31 |
| dev | sub5_whitechair_036_210 | whitechair | edge 0°, w 2.7 cm | True (100 %) | 0.4 / 1.2 / 13.6 | 10 / 5 | 2.0 / 0.0 | 0, 0.0 | 17.8 (18.8) / 31.2, 0.16 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 4.51 | 1.004 | 0 | 29 |
| dev | sub6_whitechair_019_9 | whitechair | top 90°, w 3.3 cm | True (100 %) | 0.1 / 0.4 / 0.6 | 0 / 0 | 1.0 / 0.0 | 0, 0.0 | 19.2 (22.8) / 34.2, 0.17 ok | 0.30* / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 4.51 | 1.000 | 0 | 30 |
| dev | sub12_woodchair_004_17 | woodchair | top 90°, w 1.3 cm | True (100 %) | 0.2 / 0.9 / 2.6 | 2 / 1 | 1.0 / 0.0 | 0, 0.0 | 8.2 (9.8) / 23.2, 0.07 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.33 | 0.0 | 0 | 3.18 | 1.001 | 0 | 23 |
| dev | sub3_woodchair_013_4 | woodchair | post 0°, w 2.6 cm, slid -6.5 cm | True (100 %) | 0.1 / 0.3 / 2.4 | 2 / 1 | 1.0 / 0.0 | 0, 0.0 | 17.2 (18.2) / 30.8, 0.15 ok | 0.13* / 0.10 / 0.10 | 0.0 | 0.23 | 0.0 | 0 | 3.23 | 1.000 | 0 | 25 |
| dev | sub6_woodchair_046_25 | woodchair | top 90°, w 1.3 cm | False (46 %) | 6.0 / 20.4 / 56.1 | 42 / 25 | 12.1 / 10.4 | 0, 0.0 | 8.2 (9.8) / 23.2, 0.07 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 4.26 | 1.000 | 0 | 49 |
| heldout | 260923_06_2_3_186 | box_huge | edge 30°, w 6.0 cm | True (100 %) | 0.3 / 0.6 / 1.8 | 1 / 1 | 1.4 / 0.0 | 0, 0.0 | 32.5 (38.0) / 45.0, 0.29 limit | 0.30 / 0.10 / 0.10 | 3.8 | – | 0.7 | 0 | 16.65 | 1.001 | 0 | 21 |
| heldout | 260923_06_2_3_89 | box_huge | edge 30°, w 5.7 cm, **infeasible**: no place along the part where the jaws hold it alone | True (100 %) | 0.6 / 1.6 / 2.3 | 2 / 1 | 1.0 / 0.0 | 0, 0.0 | 30.0 (36.5) / 45.0, 0.27 limit | 0.30 / 0.10 / 0.10 | 0.0 | – | 1.2 | 0 | 17.01 | 1.002 | 0 | 21 |
| heldout | 260923_06_3_2_243 | box_huge | edge 30°, w 5.4 cm | True (100 %) | 0.0 / 0.2 / 1.1 | 1 / 1 | 2.0 / 0.0 | 0, 0.0 | 30.5 (35.0) / 45.0, 0.27 limit | 0.30 / 0.10 / 0.10 | 0.7 | – | 0.0 | 0 | 8.91 | 1.001 | 0 | 22 |
| heldout | 260923_04_3_1_246 | chair | edge 0°, w 2.2 cm, **infeasible**: leading edge -7.3 cm from the contact; open jaws 8 mm into the part on the approach | True (100 %) | 0.2 / 0.7 / 4.5 | 3 / 1 | 2.0 / 1.0 | 4, 8.1 | 27.8 (16.0) / 28.8, 0.25 ok | 0.30 / 0.03 / 0.03 | 0.0 | – | 0.8 | 0 | 11.33 | 1.012 | 0 | 20 |
| heldout | 260923_05_1_retake_4_102 | chair | post 0°, w 21.7 cm, **infeasible**: no place along the part where the jaws hold it alone; section 21.7 cm wider than the jaws open (7.0 cm) | True (100 %) | 0.6 / 1.4 / 3.0 | 2 / 2 | 2.8 / 0.0 | 0, 0.0 | 31.5 (45.0) / 45.0, 0.28 limit | 0.30 / 0.10 / 0.10 | 0.7 | – | 0.7 | 0 | 11.34 | 1.005 | 0 | 21 |
| heldout | sub16_largebox_039_0 | largebox | edge 30°, w 5.2 cm | True (100 %) | 0.2 / 0.6 / 2.9 | 2 / 1 | 1.0 / 0.0 | 0, 0.0 | 29.5 (34.0) / 45.0, 0.26 limit | 0.00* / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 3.05 | 1.000 | 0 | 39 |
| heldout | sub16_largebox_041_25 | largebox | edge 30°, w 5.5 cm | True (100 %) | 0.2 / 0.5 / 2.4 | 2 / 1 | 2.0 / 0.0 | 0, 0.0 | 30.5 (35.2) / 45.0, 0.27 limit | 0.30 / 0.10 / 0.10 | 0.0 | 0.33 | 0.0 | 0 | 3.03 | 1.000 | 0 | 31 |
| heldout | sub15_largetable_003_0 | largetable | edge 0°, w 5.4 cm | True (100 %) | 0.8 / 2.6 / 6.8 | 6 / 4 | 1.0 / 0.0 | 0, 0.0 | 33.5 (34.8) / 45.0, 0.30 limit | 0.00* / 0.07 / 0.07 | 1.1 | – | 0.0 | 0 | 1.71 | 1.000 | 0 | 43 |
| heldout | sub15_largetable_005_0 | largetable | edge 0°, w 5.4 cm | True (100 %) | 0.7 / 2.6 / 6.8 | 6 / 4 | 2.0 / 0.0 | 0, 0.0 | 32.5 (35.0) / 45.0, 0.29 limit | 0.00* / 0.10 / 0.10 | 2.8 | – | 0.0 | 0 | 1.56 | 1.000 | 0 | 44 |
| heldout | sub16_largetable_033_54 | largetable | edge 0°, w 5.2 cm, slid 0.5 cm | True (100 %) | 0.5 / 0.7 / 2.9 | 2 / 2 | 2.0 / 0.0 | 0, 0.0 | 34.0 (34.0) / 45.0, 0.31 limit | 0.30 / 0.07 / 0.07 | 0.0 | 0.33 | 0.0 | 0 | 5.03 | 1.002 | 0 | 37 |
| heldout | sub11_monitor_063_15 | monitor | top 90°, w 1.9 cm | True (100 %) | 0.0 / 0.1 / 0.6 | 0 / 0 | 1.0 / 0.0 | 0, 0.0 | 12.8 (13.8) / 26.8, 0.11 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.23 | 0.0 | 0 | 1.06 | 0.910 | 0 | 32 |
| heldout | sub11_monitor_072_23 | monitor | top 90°, w 2.0 cm | True (100 %) | 0.0 / 0.2 / 0.8 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 12.5 (14.0) / 27.0, 0.11 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 2.13 | 1.000 | 0 | 33 |
| heldout | sub11_monitor_077_19 | monitor | top 90°, w 1.8 cm | True (100 %) | 0.1 / 0.2 / 1.3 | 1 / 1 | 1.0 / 0.0 | 0, 0.0 | 12.5 (12.8) / 26.0, 0.11 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.23 | 0.0 | 0 | 2.20 | 1.000 | 0 | 42 |
| heldout | sub11_monitor_078_2 | monitor | top 90°, w 1.9 cm | True (100 %) | 0.1 / 0.3 / 0.6 | 0 / 1 | 1.0 / 0.0 | 0, 0.0 | 12.0 (13.2) / 26.5, 0.11 ok | 0.07* / 0.10 / 0.10 | 0.0 | 0.23 | 0.0 | 0 | 1.96 | 1.000 | 0 | 40 |
| heldout | sub15_plasticbox_047_32 | plasticbox | top 90°, w 1.5 cm | True (100 %) | 0.1 / 0.4 / 1.4 | 1 / 1 | 1.0 / 0.0 | 0, 0.0 | 9.5 (10.5) / 24.0, 0.08 ok | 0.30 / 0.10 / 0.10 | 0.0 | – | 0.0 | 0 | 2.32 | 1.000 | 0 | 33 |
| heldout | sub15_plasticbox_048_9 | plasticbox | top 90°, w 1.7 cm | True (100 %) | 0.1 / 0.3 / 3.2 | 2 / 1 | 1.0 / 0.0 | 0, 0.0 | 10.5 (12.2) / 25.5, 0.09 ok | 0.30* / 0.10 / 0.10 | 0.0 | – | 0.0 | 0 | 2.10 | 1.000 | 0 | 43 |
| heldout | sub15_plasticbox_050_38 | plasticbox | top 90°, w 1.6 cm | True (100 %) | 0.1 / 0.4 / 1.0 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 9.8 (11.2) / 24.8, 0.09 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.07 | 0.0 | 0 | 1.96 | 1.000 | 0 | 35 |
| heldout | sub16_plasticbox_050_77 | plasticbox | top 90°, w 1.4 cm | True (100 %) | 0.1 / 0.3 / 0.6 | 0 / 0 | 1.0 / 0.0 | 0, 0.0 | 9.8 (10.2) / 23.8, 0.09 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 3.25 | 1.002 | 0 | 28 |
| heldout | sub16_plasticbox_054_79 | plasticbox | top 90°, w 1.5 cm | False (86 %) | 1.7 / 4.6 / 11.4 | 5 / 12 | 7.0 / 0.0 | 0, 0.0 | 9.5 (10.5) / 24.0, 0.08 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.37 | 0.0 | 0 | 4.61 | 1.006 | 0 | 31 |
| heldout | sub8_plasticbox_038_10 | plasticbox | top 90°, w 1.4 cm | True (100 %) | 0.1 / 0.2 / 0.9 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 9.8 (10.2) / 23.8, 0.09 ok | 0.33* / 0.10 / 0.10 | 0.0 | 0.23 | 0.0 | 0 | 2.51 | 1.003 | 0 | 35 |
| heldout | sub8_plasticbox_040_11 | plasticbox | top 90°, w 1.5 cm | True (100 %) | 0.2 / 0.3 / 0.5 | 0 / 0 | 1.0 / 0.0 | 0, 0.0 | 10.2 (10.8) / 24.2, 0.09 ok | 0.37* / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 2.08 | 1.000 | 0 | 39 |
| heldout | sub8_plasticbox_050_101 | plasticbox | top 90°, w 1.4 cm | True (100 %) | 0.4 / 4.7 / 1.9 | 2 / 2 | 1.0 / 0.0 | 0, 0.0 | 9.2 (10.2) / 23.8, 0.08 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.23 | 0.0 | 0 | 4.05 | 1.014 | 0 | 30 |
| heldout | sub14_smalltable_000_0 | smalltable | edge 15°, w 3.7 cm | True (100 %) | 0.7 / 1.1 / 6.3 | 4 / 4 | 1.0 / 0.0 | 0, 0.0 | 24.5 (25.2) / 36.5, 0.22 ok | 0.00* / 0.07 / 0.07 | 1.1 | 0.33 | 0.0 | 0 | 1.93 | 1.000 | 0 | 36 |
| heldout | sub17_smalltable_001_1 | smalltable | edge 15°, w 3.8 cm | True (100 %) | 0.2 / 0.5 / 2.0 | 1 / 1 | 2.0 / 0.0 | 0, 0.0 | 24.2 (26.2) / 37.2, 0.21 ok | 0.03* / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 1.77 | 1.000 | 0 | 33 |
| heldout | sub17_smalltable_003_0 | smalltable | edge 15°, w 3.8 cm | True (100 %) | 0.3 / 0.5 / 1.5 | 1 / 1 | 1.0 / 0.0 | 0, 0.0 | 22.8 (26.2) / 37.2, 0.20 ok | 0.00* / 0.10 / 0.10 | 1.8 | 0.27 | 0.0 | 0 | 2.51 | 1.002 | 0 | 35 |
| heldout | sub17_smalltable_004_0 | smalltable | edge 15°, w 3.7 cm | True (100 %) | 0.3 / 0.5 / 2.5 | 2 / 1 | 2.0 / 0.0 | 0, 0.0 | 23.5 (25.2) / 36.5, 0.21 ok | 0.00* / 0.10 / 0.10 | 0.1 | 0.30 | 0.0 | 0 | 1.89 | 1.001 | 0 | 39 |
| heldout | sub17_smalltable_005_0 | smalltable | edge 15°, w 3.9 cm | True (100 %) | 1.0 / 1.6 / 7.9 | 6 / 4 | 2.0 / 0.0 | 0, 0.0 | 23.5 (26.8) / 37.5, 0.21 ok | 0.00* / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 6.25 | 1.001 | 0 | 31 |
| heldout | sub17_smalltable_006_0 | smalltable | edge 15°, w 3.8 cm, slid 0.5 cm | True (100 %) | 0.3 / 0.7 / 1.7 | 1 / 1 | 2.0 / 0.0 | 0, 0.0 | 24.0 (26.2) / 37.0, 0.21 ok | 0.00* / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 3.52 | 1.001 | 0 | 30 |
| heldout | sub17_smalltable_007_0 | smalltable | edge 15°, w 3.8 cm | True (100 %) | 0.4 / 1.2 / 4.1 | 3 / 2 | 2.0 / 0.0 | 0, 0.0 | 22.8 (26.2) / 37.2, 0.20 ok | 0.00* / 0.10 / 0.10 | 0.1 | 0.23 | 0.0 | 0 | 5.07 | 1.000 | 0 | 27 |
| heldout | sub17_smalltable_039_128 | smalltable | edge 15°, w 3.8 cm | True (100 %) | 0.2 / 0.6 / 3.5 | 2 / 1 | 1.0 / 0.0 | 0, 0.0 | 24.0 (26.2) / 37.0, 0.21 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 5.07 | 1.008 | 0 | 25 |
| heldout | sub17_smalltable_040_81 | smalltable | edge 15°, w 4.0 cm | True (100 %) | 0.2 / 0.5 / 1.7 | 1 / 1 | 1.0 / 0.0 | 0, 0.0 | 24.0 (27.2) / 38.0, 0.21 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 3.69 | 1.015 | 0 | 28 |
| heldout | sub9_smalltable_002_0 | smalltable | edge 15°, w 3.9 cm | True (100 %) | 0.6 / 1.1 / 6.3 | 4 / 3 | 1.0 / 0.0 | 0, 0.0 | 24.2 (26.5) / 37.2, 0.21 ok | 0.00* / 0.10 / 0.10 | 0.1 | 0.33 | 0.0 | 0 | 3.09 | 1.000 | 0 | 35 |
| heldout | sub9_smalltable_003_0 | smalltable | edge 15°, w 3.7 cm | True (100 %) | 0.2 / 0.5 / 4.1 | 3 / 2 | 1.0 / 0.0 | 0, 0.0 | 23.5 (25.2) / 36.5, 0.21 ok | 0.00* / 0.10 / 0.10 | 0.0 | – | 0.0 | 0 | 3.98 | 1.002 | 0 | 31 |
| heldout | sub9_smalltable_007_15 | smalltable | edge 15°, w 3.7 cm | True (100 %) | 0.3 / 0.8 / 3.8 | 3 / 2 | 2.0 / 0.0 | 0, 0.0 | 23.5 (25.2) / 36.5, 0.21 ok | 0.50* / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 2.02 | 1.000 | 0 | 35 |
| heldout | sub9_smalltable_070_55 | smalltable | edge 15°, w 3.9 cm | True (100 %) | 0.3 / 0.7 / 3.4 | 2 / 1 | 2.0 / 0.0 | 0, 0.0 | 23.5 (26.8) / 37.5, 0.21 ok | 0.30 / 0.10 / 0.10 | 1.2 | 0.10 | 0.0 | 0 | 3.43 | 1.008 | 1 | 37 |
| heldout | sub9_smalltable_074_50 | smalltable | edge 15°, w 3.7 cm | False (94 %) | 1.5 / 1.6 / 18.6 | 13 / 8 | 6.0 / 0.0 | 0, 0.0 | 23.2 (25.2) / 36.2, 0.21 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.37 | 0.0 | 0 | 5.58 | 1.005 | 0 | 34 |
| heldout | sub9_smalltable_076_73 | smalltable | edge 15°, w 3.9 cm | True (100 %) | 0.7 / 1.8 / 14.5 | 11 / 6 | 2.0 / 0.0 | 0, 0.0 | 23.8 (26.8) / 37.8, 0.21 ok | 0.30 / 0.10 / 0.10 | 8.3 | -0.37 | 0.0 | 0 | 5.13 | 1.001 | 1 | 36 |
| heldout | sub14_suitcase_020_5 | suitcase | top 90°, w 12.8 cm, **infeasible**: section 12.8 cm wider than the jaws open (7.0 cm); leading edge -3.4 cm from the contact | True (100 %) | 0.3 / 0.1 / 0.7 | 0 / 0 | 1.0 / 0.0 | 0, 1.0 | 29.5 (45.0) / 45.0, 0.26 limit | 0.17* / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 2.92 | 1.000 | 0 | 43 |
| heldout | sub8_suitcase_050_109 | suitcase | top 90°, w 14.1 cm, **infeasible**: section 14.1 cm wider than the jaws open (7.0 cm) | True (100 %) | 0.3 / 0.2 / 0.6 | 0 / 0 | 0.0 / 0.0 | 0, 0.0 | 24.0 (45.0) / 45.0, 0.21 ok | 0.30 / 0.13 / 0.13 | 0.0 | 0.33 | 0.0 | 0 | 4.35 | 1.001 | 0 | 44 |
| heldout | sub11_trashcan_046_21 | trashcan | top 90°, w 1.8 cm | True (100 %) | 0.1 / 0.3 / 0.7 | 0 / 0 | 1.0 / 0.0 | 0, 0.0 | 11.5 (12.8) / 26.0, 0.10 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.23 | 0.0 | 0 | 1.51 | 1.000 | 0 | 48 |
| heldout | sub11_trashcan_049_27 | trashcan | top 90°, w 1.7 cm | True (100 %) | 0.2 / 0.6 / 2.6 | 2 / 1 | 1.0 / 0.0 | 0, 0.0 | 12.0 (12.2) / 25.5, 0.11 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.20 | 0.0 | 0 | 1.72 | 1.000 | 0 | 66 |
| heldout | sub11_trashcan_050_18 | trashcan | top 90°, w 1.2 cm | True (100 %) | 0.1 / 0.3 / 0.9 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 9.5 (9.0) / 22.5, 0.08 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.23 | 0.0 | 0 | 1.64 | 1.001 | 0 | 56 |
| heldout | sub11_trashcan_052_18 | trashcan | top 90°, w 2.3 cm | True (100 %) | 0.1 / 0.2 / 0.8 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 15.0 (16.2) / 29.0, 0.13 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.10 | 0.0 | 0 | 1.23 | 1.001 | 0 | 60 |
| heldout | sub11_trashcan_055_11 | trashcan | top 90°, w 1.2 cm | True (100 %) | 0.1 / 0.2 / 0.6 | 0 / 0 | 1.0 / 0.0 | 0, 0.0 | 8.5 (8.5) / 22.0, 0.07 ok | 0.37* / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 1.86 | 1.000 | 0 | 54 |
| heldout | sub11_trashcan_056_21 | trashcan | top 90°, w 1.8 cm | True (100 %) | 0.1 / 0.2 / 1.4 | 1 / 1 | 1.0 / 0.0 | 0, 0.0 | 12.2 (13.2) / 26.2, 0.11 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.23 | 0.0 | 0 | 0.99 | 1.000 | 0 | 48 |
| heldout | sub11_trashcan_058_25 | trashcan | top 90°, w 1.1 cm | True (100 %) | 0.0 / 0.2 / 0.6 | 0 / 0 | 1.0 / 0.0 | 0, 0.0 | 8.5 (8.2) / 22.0, 0.07 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 1.49 | 1.000 | 0 | 44 |
| heldout | sub11_trashcan_059_18 | trashcan | top 90°, w 1.2 cm | True (100 %) | 0.1 / 0.2 / 0.7 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 8.0 (9.0) / 22.5, 0.07 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.20 | 0.0 | 0 | 1.31 | 1.000 | 0 | 51 |
| heldout | sub11_trashcan_060_17 | trashcan | top 90°, w 3.2 cm | True (100 %) | 0.0 / 0.1 / 0.6 | 0 / 0 | 1.0 / 0.0 | 0, 0.0 | 20.0 (22.2) / 34.0, 0.18 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.20 | 0.0 | 0 | 1.40 | 1.002 | 0 | 52 |
| heldout | sub15_trashcan_060_0 | trashcan | top 90°, w 2.4 cm | True (100 %) | 0.1 / 0.3 / 0.8 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 15.8 (17.0) / 29.8, 0.14 ok | 0.00* / 0.10 / 0.10 | 1.2 | – | 0.0 | 0 | 0.74 | 1.000 | 0 | 58 |
| heldout | sub16_trashcan_036_28 | trashcan | top 90°, w 2.3 cm | True (100 %) | 0.1 / 0.1 / 1.3 | 1 / 1 | 1.0 / 0.0 | 0, 0.0 | 16.0 (16.5) / 29.0, 0.14 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.33 | 0.0 | 0 | 2.07 | 1.000 | 0 | 39 |
| heldout | sub7_trashcan_039_16 | trashcan | top 90°, w 2.5 cm | True (100 %) | 0.3 / 0.8 / 1.7 | 1 / 1 | 1.0 / 0.0 | 0, 0.0 | 16.5 (18.0) / 30.5, 0.14 ok | 0.30 / 0.10 / 0.10 | 0.1 | 0.27 | 0.0 | 0 | 1.36 | 1.001 | 0 | 52 |
| heldout | sub8_trashcan_043_113 | trashcan | top 90°, w 3.0 cm | True (100 %) | 0.1 / 0.3 / 2.1 | 1 / 1 | 1.0 / 0.0 | 0, 0.0 | 17.5 (21.2) / 33.0, 0.15 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 4.18 | 1.005 | 0 | 40 |
| heldout | sub8_trashcan_043_20 | trashcan | top 90°, w 1.7 cm | True (100 %) | 0.2 / 0.3 / 0.8 | 1 / 2 | 2.0 / 0.0 | 0, 0.0 | 12.2 (12.5) / 25.8, 0.11 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.37 | 0.0 | 0 | 3.89 | 1.000 | 0 | 45 |
| heldout | sub8_trashcan_044_124 | trashcan | top 90°, w 2.0 cm | True (100 %) | 0.1 / 0.4 / 0.8 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 12.5 (14.8) / 27.5, 0.11 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 3.31 | 1.000 | 0 | 37 |
| heldout | sub8_trashcan_045_121 | trashcan | top 90°, w 2.4 cm | True (100 %) | 0.2 / 0.6 / 1.2 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 17.5 (17.2) / 30.0, 0.15 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 5.09 | 1.002 | 0 | 39 |
| heldout | sub8_trashcan_046_129 | trashcan | top 90°, w 2.4 cm | True (100 %) | 0.3 / 0.5 / 1.1 | 1 / 1 | 1.0 / 0.0 | 0, 0.0 | 13.0 (16.8) / 29.5, 0.11 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 4.65 | 1.003 | 0 | 46 |
| heldout | sub8_trashcan_047_109 | trashcan | top 90°, w 1.7 cm | True (100 %) | 0.1 / 0.4 / 1.3 | 1 / 1 | 1.0 / 0.0 | 0, 0.0 | 10.2 (12.0) / 25.2, 0.09 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.27 | 0.0 | 0 | 4.08 | 1.001 | 0 | 42 |
| heldout | sub10_whitechair_064_115 | whitechair | top 90°, w 3.3 cm | True (100 %) | 0.2 / 0.3 / 1.0 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 19.2 (22.8) / 34.2, 0.17 ok | 0.30 / 0.10 / 0.10 | 0.3 | 0.33 | 0.0 | 0 | 4.36 | 1.000 | 0 | 25 |
| heldout | sub13_whitechair_028_0 | whitechair | top 90°, w 3.3 cm | True (100 %) | 0.0 / 0.2 / 0.7 | 0 / 0 | 1.0 / 0.0 | 0, 0.0 | 19.0 (23.0) / 34.5, 0.17 ok | 0.00* / 0.10 / 0.10 | 3.0 | 0.20 | 0.0 | 0 | 3.26 | 1.000 | 0 | 35 |
| heldout | sub13_whitechair_029_0 | whitechair | top 90°, w 3.3 cm | True (100 %) | 0.1 / 0.5 / 0.7 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 18.8 (22.8) / 34.2, 0.17 ok | 0.00* / 0.10 / 0.10 | 0.0 | 0.40 | 0.0 | 0 | 2.58 | 1.000 | 0 | 33 |
| heldout | sub13_whitechair_045_35 | whitechair | top 90°, w 3.3 cm | True (100 %) | 0.1 / 0.6 / 1.2 | 1 / 1 | 1.0 / 0.0 | 0, 0.0 | 19.0 (22.8) / 34.5, 0.17 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.33 | 0.0 | 0 | 1.99 | 1.001 | 0 | 37 |
| heldout | sub4_whitechair_017_7 | whitechair | edge 0°, w 6.8 cm, slid -10.0 cm | True (100 %) | 2.7 / 9.2 / 5.8 | 6 / 5 | 2.0 / 0.0 | 0, 0.0 | 28.5 (41.8) / 45.0, 0.25 limit | 0.23* / 0.10 / 0.10 | 0.0 | 0.37 | 0.0 | 0 | 3.33 | 1.001 | 0 | 35 |
| heldout | sub4_whitechair_018_0 | whitechair | edge 0°, w 8.2 cm, **infeasible**: no place along the part where the jaws hold it alone; section 8.2 cm wider than the jaws open (7.0 cm) | True (100 %) | 2.6 / 8.4 / 14.9 | 11 / 8 | 3.0 / 0.0 | 0, 0.0 | 34.5 (45.0) / 45.0, 0.31 limit | 0.00* / 0.07 / 0.07 | 0.4 | 0.37 | 0.0 | 0 | 4.42 | 1.000 | 0 | 40 |
| heldout | sub4_whitechair_019_0 | whitechair | top 90°, w 3.3 cm | True (100 %) | 0.2 / 0.5 / 1.1 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 19.2 (22.8) / 34.2, 0.17 ok | 0.00* / 0.10 / 0.10 | 0.0 | – | 0.0 | 0 | 2.43 | 1.000 | 0 | 34 |
| heldout | sub4_whitechair_020_3 | whitechair | edge 0°, w 6.9 cm, slid -6.5 cm | False (0 %) | 6.7 / 97.0 / 64.8 | 87 / 40 | 0.0 / 0.0 | 3, 13.4 | 28.5 (42.2) / 45.0, 0.25 limit | 0.10* / 0.10 / 0.10 | 0.0 | – | 0.0 | 0 | 2.86 | 1.001 | 0 | 42 |
| heldout | sub4_whitechair_021_0 | whitechair | edge 0°, w 6.6 cm, slid -11.5 cm | True (100 %) | 2.5 / 8.5 / 10.6 | 9 / 6 | 2.0 / 0.0 | 0, 0.0 | 28.0 (40.8) / 45.0, 0.25 ok | 0.00* / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 2.52 | 1.000 | 0 | 42 |
| heldout | sub4_whitechair_036_199 | whitechair | top 90°, w 3.3 cm | True (100 %) | 0.1 / 0.2 / 1.5 | 1 / 1 | 1.0 / 0.0 | 0, 0.0 | 19.0 (22.8) / 34.5, 0.17 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 3.50 | 1.001 | 0 | 28 |
| heldout | sub4_whitechair_037_165 | whitechair | top 90°, w 3.3 cm | True (100 %) | 0.1 / 0.4 / 1.0 | 1 / 1 | 1.0 / 0.0 | 0, 0.0 | 19.2 (22.8) / 34.2, 0.17 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 4.79 | 1.001 | 0 | 27 |
| heldout | sub4_whitechair_038_125 | whitechair | top 90°, w 3.1 cm | True (100 %) | 0.0 / 0.4 / 1.2 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 18.2 (22.0) / 33.8, 0.16 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.23 | 0.0 | 0 | 3.45 | 1.001 | 0 | 26 |
| heldout | sub4_whitechair_039_107 | whitechair | top 90°, w 3.2 cm | True (100 %) | 0.0 / 0.2 / 1.5 | 1 / 1 | 1.0 / 0.0 | 0, 0.0 | 18.8 (22.5) / 34.2, 0.17 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.33 | 0.0 | 0 | 2.91 | 1.000 | 0 | 25 |
| heldout | sub4_whitechair_040_118 | whitechair | top 90°, w 3.3 cm | True (100 %) | 0.1 / 0.2 / 2.9 | 2 / 1 | 1.0 / 0.0 | 0, 0.0 | 18.8 (22.8) / 34.2, 0.17 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.40 | 0.0 | 0 | 2.88 | 1.000 | 0 | 24 |
| heldout | sub4_whitechair_043_0 | whitechair | top 90°, w 3.2 cm | True (100 %) | 0.1 / 0.3 / 0.5 | 0 / 0 | 1.0 / 0.0 | 0, 0.0 | 18.2 (22.2) / 33.8, 0.16 ok | 0.00* / 0.10 / 0.10 | 0.1 | 0.30 | 0.0 | 0 | 3.69 | 1.001 | 0 | 34 |
| heldout | sub4_whitechair_044_13 | whitechair | top 90°, w 3.3 cm | True (100 %) | 0.1 / 0.4 / 0.7 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 19.0 (23.0) / 34.5, 0.17 ok | 0.43* / 0.10 / 0.10 | 0.0 | 0.37 | 0.0 | 0 | 4.00 | 1.000 | 0 | 31 |
| heldout | sub4_whitechair_045_0 | whitechair | top 90°, w 3.1 cm | True (100 %) | 0.2 / 0.8 / 3.5 | 2 / 1 | 1.0 / 0.0 | 0, 0.0 | 18.2 (22.0) / 33.8, 0.16 ok | 0.00* / 0.10 / 0.10 | 0.0 | 0.37 | 0.0 | 0 | 2.91 | 1.000 | 0 | 30 |
| heldout | sub4_whitechair_047_0 | whitechair | top 90°, w 3.3 cm | True (100 %) | 0.0 / 0.2 / 1.1 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 19.2 (22.8) / 34.2, 0.17 ok | 0.00* / 0.10 / 0.10 | 0.0 | 0.37 | 0.0 | 0 | 1.90 | 1.000 | 0 | 34 |
| heldout | sub7_whitechair_018_12 | whitechair | top 90°, w 3.2 cm | True (100 %) | 0.1 / 0.3 / 0.9 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 18.2 (22.2) / 33.8, 0.16 ok | 0.40* / 0.10 / 0.10 | 0.0 | 0.33 | 0.0 | 0 | 4.70 | 1.001 | 0 | 34 |
| heldout | sub7_whitechair_021_18 | whitechair | top 90°, w 3.3 cm | True (100 %) | 0.1 / 0.4 / 0.6 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 19.0 (23.0) / 34.5, 0.17 ok | 0.30 / 0.10 / 0.10 | 0.1 | 0.40 | 0.0 | 0 | 6.51 | 1.000 | 0 | 28 |
| heldout | sub7_whitechair_022_0 | whitechair | top 90°, w 3.3 cm | True (100 %) | 0.1 / 0.3 / 0.9 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 19.2 (22.8) / 34.2, 0.17 ok | 0.00* / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 5.63 | 1.000 | 0 | 30 |
| heldout | sub7_whitechair_037_90 | whitechair | top 90°, w 3.3 cm | True (100 %) | 0.2 / 0.4 / 1.3 | 1 / 0 | 1.0 / 0.0 | 0, 0.0 | 19.0 (23.0) / 34.5, 0.17 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.33 | 0.0 | 0 | 4.78 | 1.001 | 0 | 27 |
| heldout | sub7_whitechair_041_121 | whitechair | edge 15°, w 2.8 cm | False (99 %) | 0.7 / 5.3 / 25.4 | 18 / 11 | 5.8 / 0.0 | 0, 0.0 | 18.8 (19.8) / 31.8, 0.17 ok | 0.30 / 0.10 / 0.10 | 0.0 | 0.30 | 0.0 | 0 | 8.62 | 1.012 | 0 | 36 |
| heldout | sub17_woodchair_021_0 | woodchair | top 90°, w 1.3 cm | True (100 %) | 0.4 / 2.0 / 6.2 | 4 / 2 | 2.0 / 0.0 | 0, 0.0 | 8.2 (9.5) / 23.2, 0.07 ok | 0.00* / 0.10 / 0.10 | 2.3 | 0.33 | 0.0 | 0 | 5.74 | 1.001 | 0 | 28 |
| heldout | sub2_woodchair_009_0 | woodchair | top 90°, w 1.3 cm | True (100 %) | 0.1 / 0.9 / 5.1 | 4 / 2 | 2.0 / 0.0 | 0, 0.0 | 8.2 (9.8) / 23.2, 0.07 ok | 0.00* / 0.10 / 0.10 | 0.6 | – | 0.0 | 0 | 2.41 | 1.006 | 0 | 29 |
| heldout | sub2_woodchair_010_0 | woodchair | top 90°, w 1.2 cm | True (100 %) | 0.1 / 0.3 / 0.6 | 0 / 0 | 1.0 / 0.0 | 0, 0.0 | 8.0 (8.8) / 22.5, 0.07 ok | 0.00* / 0.10 / 0.10 | 3.3 | – | 0.0 | 0 | 2.83 | 1.000 | 0 | 27 |
| heldout | sub2_woodchair_011_1 | woodchair | top 90°, w 1.3 cm | True (100 %) | 0.3 / 1.7 / 5.2 | 4 / 2 | 2.0 / 0.0 | 0, 0.0 | 8.8 (9.8) / 23.2, 0.08 ok | 0.03* / 0.10 / 0.10 | 0.0 | – | 0.0 | 0 | 3.92 | 1.001 | 0 | 27 |

\* the clip starts too late to open before the contact: open from its first frame.

![sub12_plasticbox_043_23](figures/sub12_plasticbox_043_23.png)
![sub12_plasticbox_045_32](figures/sub12_plasticbox_045_32.png)
![sub12_plasticbox_048_34](figures/sub12_plasticbox_048_34.png)
![sub12_smalltable_000_6](figures/sub12_smalltable_000_6.png)
![sub12_smalltable_001_10](figures/sub12_smalltable_001_10.png)
![sub12_smalltable_002_20](figures/sub12_smalltable_002_20.png)
![sub12_smalltable_004_0](figures/sub12_smalltable_004_0.png)
![sub12_smalltable_005_24](figures/sub12_smalltable_005_24.png)
![sub12_smalltable_006_0](figures/sub12_smalltable_006_0.png)
![sub12_smalltable_007_0](figures/sub12_smalltable_007_0.png)
![sub12_smalltable_008_3](figures/sub12_smalltable_008_3.png)
![sub12_smalltable_009_17](figures/sub12_smalltable_009_17.png)
![sub12_smalltable_072_51](figures/sub12_smalltable_072_51.png)
![sub12_smalltable_073_89](figures/sub12_smalltable_073_89.png)
![sub12_smalltable_074_126](figures/sub12_smalltable_074_126.png)
![sub12_smalltable_078_144](figures/sub12_smalltable_078_144.png)
![sub12_smalltable_079_113](figures/sub12_smalltable_079_113.png)
![sub12_woodchair_004_17](figures/sub12_woodchair_004_17.png)
![sub1_largetable_004_3](figures/sub1_largetable_004_3.png)
![sub1_largetable_007_12](figures/sub1_largetable_007_12.png)
![sub1_largetable_009_11](figures/sub1_largetable_009_11.png)
![sub1_largetable_010_9](figures/sub1_largetable_010_9.png)
![sub1_plasticbox_081_90](figures/sub1_plasticbox_081_90.png)
![sub1_plasticbox_088_69](figures/sub1_plasticbox_088_69.png)
![sub1_suitcase_062_4](figures/sub1_suitcase_062_4.png)
![sub1_suitcase_085_90](figures/sub1_suitcase_085_90.png)
![sub3_largetable_000_107](figures/sub3_largetable_000_107.png)
![sub3_largetable_001_45](figures/sub3_largetable_001_45.png)
![sub3_largetable_002_13](figures/sub3_largetable_002_13.png)
![sub3_largetable_011_3](figures/sub3_largetable_011_3.png)
![sub3_largetable_027_83](figures/sub3_largetable_027_83.png)
![sub3_largetable_028_66](figures/sub3_largetable_028_66.png)
![sub3_woodchair_013_4](figures/sub3_woodchair_013_4.png)
![sub5_plasticbox_037_1](figures/sub5_plasticbox_037_1.png)
![sub5_plasticbox_048_214](figures/sub5_plasticbox_048_214.png)
![sub5_plasticbox_050_178](figures/sub5_plasticbox_050_178.png)
![sub5_whitechair_019_1](figures/sub5_whitechair_019_1.png)
![sub5_whitechair_036_210](figures/sub5_whitechair_036_210.png)
![sub6_trashcan_036_36](figures/sub6_trashcan_036_36.png)
![sub6_trashcan_037_13](figures/sub6_trashcan_037_13.png)
![sub6_trashcan_038_18](figures/sub6_trashcan_038_18.png)
![sub6_trashcan_040_30](figures/sub6_trashcan_040_30.png)
![sub6_trashcan_041_28](figures/sub6_trashcan_041_28.png)
![sub6_trashcan_048_76](figures/sub6_trashcan_048_76.png)
![sub6_trashcan_049_114](figures/sub6_trashcan_049_114.png)
![sub6_trashcan_050_107](figures/sub6_trashcan_050_107.png)
![sub6_trashcan_051_86](figures/sub6_trashcan_051_86.png)
![sub6_trashcan_052_95](figures/sub6_trashcan_052_95.png)
![sub6_whitechair_019_9](figures/sub6_whitechair_019_9.png)
![sub6_woodchair_046_25](figures/sub6_woodchair_046_25.png)
![260923_04_3_1_246](figures/260923_04_3_1_246.png)
![260923_05_1_retake_4_102](figures/260923_05_1_retake_4_102.png)
![260923_06_2_3_186](figures/260923_06_2_3_186.png)
![260923_06_2_3_89](figures/260923_06_2_3_89.png)
![260923_06_3_2_243](figures/260923_06_3_2_243.png)
![sub10_whitechair_064_115](figures/sub10_whitechair_064_115.png)
![sub11_monitor_063_15](figures/sub11_monitor_063_15.png)
![sub11_monitor_072_23](figures/sub11_monitor_072_23.png)
![sub11_monitor_077_19](figures/sub11_monitor_077_19.png)
![sub11_monitor_078_2](figures/sub11_monitor_078_2.png)
![sub11_trashcan_046_21](figures/sub11_trashcan_046_21.png)
![sub11_trashcan_049_27](figures/sub11_trashcan_049_27.png)
![sub11_trashcan_050_18](figures/sub11_trashcan_050_18.png)
![sub11_trashcan_052_18](figures/sub11_trashcan_052_18.png)
![sub11_trashcan_055_11](figures/sub11_trashcan_055_11.png)
![sub11_trashcan_056_21](figures/sub11_trashcan_056_21.png)
![sub11_trashcan_058_25](figures/sub11_trashcan_058_25.png)
![sub11_trashcan_059_18](figures/sub11_trashcan_059_18.png)
![sub11_trashcan_060_17](figures/sub11_trashcan_060_17.png)
![sub13_whitechair_028_0](figures/sub13_whitechair_028_0.png)
![sub13_whitechair_029_0](figures/sub13_whitechair_029_0.png)
![sub13_whitechair_045_35](figures/sub13_whitechair_045_35.png)
![sub14_smalltable_000_0](figures/sub14_smalltable_000_0.png)
![sub14_suitcase_020_5](figures/sub14_suitcase_020_5.png)
![sub15_largetable_003_0](figures/sub15_largetable_003_0.png)
![sub15_largetable_005_0](figures/sub15_largetable_005_0.png)
![sub15_plasticbox_047_32](figures/sub15_plasticbox_047_32.png)
![sub15_plasticbox_048_9](figures/sub15_plasticbox_048_9.png)
![sub15_plasticbox_050_38](figures/sub15_plasticbox_050_38.png)
![sub15_trashcan_060_0](figures/sub15_trashcan_060_0.png)
![sub16_largebox_039_0](figures/sub16_largebox_039_0.png)
![sub16_largebox_041_25](figures/sub16_largebox_041_25.png)
![sub16_largetable_033_54](figures/sub16_largetable_033_54.png)
![sub16_plasticbox_050_77](figures/sub16_plasticbox_050_77.png)
![sub16_plasticbox_054_79](figures/sub16_plasticbox_054_79.png)
![sub16_trashcan_036_28](figures/sub16_trashcan_036_28.png)
![sub17_smalltable_001_1](figures/sub17_smalltable_001_1.png)
![sub17_smalltable_003_0](figures/sub17_smalltable_003_0.png)
![sub17_smalltable_004_0](figures/sub17_smalltable_004_0.png)
![sub17_smalltable_005_0](figures/sub17_smalltable_005_0.png)
![sub17_smalltable_006_0](figures/sub17_smalltable_006_0.png)
![sub17_smalltable_007_0](figures/sub17_smalltable_007_0.png)
![sub17_smalltable_039_128](figures/sub17_smalltable_039_128.png)
![sub17_smalltable_040_81](figures/sub17_smalltable_040_81.png)
![sub17_woodchair_021_0](figures/sub17_woodchair_021_0.png)
![sub2_woodchair_009_0](figures/sub2_woodchair_009_0.png)
![sub2_woodchair_010_0](figures/sub2_woodchair_010_0.png)
![sub2_woodchair_011_1](figures/sub2_woodchair_011_1.png)
![sub4_whitechair_017_7](figures/sub4_whitechair_017_7.png)
![sub4_whitechair_018_0](figures/sub4_whitechair_018_0.png)
![sub4_whitechair_019_0](figures/sub4_whitechair_019_0.png)
![sub4_whitechair_020_3](figures/sub4_whitechair_020_3.png)
![sub4_whitechair_021_0](figures/sub4_whitechair_021_0.png)
![sub4_whitechair_036_199](figures/sub4_whitechair_036_199.png)
![sub4_whitechair_037_165](figures/sub4_whitechair_037_165.png)
![sub4_whitechair_038_125](figures/sub4_whitechair_038_125.png)
![sub4_whitechair_039_107](figures/sub4_whitechair_039_107.png)
![sub4_whitechair_040_118](figures/sub4_whitechair_040_118.png)
![sub4_whitechair_043_0](figures/sub4_whitechair_043_0.png)
![sub4_whitechair_044_13](figures/sub4_whitechair_044_13.png)
![sub4_whitechair_045_0](figures/sub4_whitechair_045_0.png)
![sub4_whitechair_047_0](figures/sub4_whitechair_047_0.png)
![sub7_trashcan_039_16](figures/sub7_trashcan_039_16.png)
![sub7_whitechair_018_12](figures/sub7_whitechair_018_12.png)
![sub7_whitechair_021_18](figures/sub7_whitechair_021_18.png)
![sub7_whitechair_022_0](figures/sub7_whitechair_022_0.png)
![sub7_whitechair_037_90](figures/sub7_whitechair_037_90.png)
![sub7_whitechair_041_121](figures/sub7_whitechair_041_121.png)
![sub8_plasticbox_038_10](figures/sub8_plasticbox_038_10.png)
![sub8_plasticbox_040_11](figures/sub8_plasticbox_040_11.png)
![sub8_plasticbox_050_101](figures/sub8_plasticbox_050_101.png)
![sub8_suitcase_050_109](figures/sub8_suitcase_050_109.png)
![sub8_trashcan_043_113](figures/sub8_trashcan_043_113.png)
![sub8_trashcan_043_20](figures/sub8_trashcan_043_20.png)
![sub8_trashcan_044_124](figures/sub8_trashcan_044_124.png)
![sub8_trashcan_045_121](figures/sub8_trashcan_045_121.png)
![sub8_trashcan_046_129](figures/sub8_trashcan_046_129.png)
![sub8_trashcan_047_109](figures/sub8_trashcan_047_109.png)
![sub9_smalltable_002_0](figures/sub9_smalltable_002_0.png)
![sub9_smalltable_003_0](figures/sub9_smalltable_003_0.png)
![sub9_smalltable_007_15](figures/sub9_smalltable_007_15.png)
![sub9_smalltable_070_55](figures/sub9_smalltable_070_55.png)
![sub9_smalltable_074_50](figures/sub9_smalltable_074_50.png)
![sub9_smalltable_076_73](figures/sub9_smalltable_076_73.png)
