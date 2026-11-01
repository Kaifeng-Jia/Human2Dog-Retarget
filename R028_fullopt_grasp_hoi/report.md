# HOI clips for the full-optimization line, grasp tasks (fullopt spec v0.2 §2.1, §8.5)

Run `R028_fullopt_grasp_hoi` · code `v0.3.2-3-g04df1ca` (dirty=False) · dev 50 · held-out 84 · 0 errors · **PASS**

Dev people (the press dev split): sub1, sub12, sub3, sub5, sub6

| object | dev | held-out |
|---|---|---|
| box_huge | 0 | 3 |
| chair | 0 | 2 |
| largebox | 0 | 2 |
| largetable | 10 | 3 |
| monitor | 0 | 4 |
| plasticbox | 8 | 8 |
| smalltable | 14 | 15 |
| suitcase | 2 | 2 |
| trashcan | 10 | 18 |
| whitechair | 3 | 23 |
| woodchair | 3 | 4 |

| split | id | dataset | task (run) | object | subject | hand | frames | fps | hand contact labels | problems |
|---|---|---|---|---|---|---|---|---|---|---|
| dev | sub12_plasticbox_043_23 | omomo_new | – (R028_grasp_candidates) | plasticbox | sub12 | B | 239 | 30 | True |  |
| dev | sub12_plasticbox_045_32 | omomo_new | – (R028_grasp_candidates) | plasticbox | sub12 | R | 277 | 30 | True |  |
| dev | sub12_plasticbox_048_34 | omomo_new | – (R028_grasp_candidates) | plasticbox | sub12 | L | 304 | 30 | True |  |
| dev | sub12_smalltable_000_6 | omomo_new | – (R028_grasp_candidates) | smalltable | sub12 | L | 133 | 30 | True |  |
| dev | sub12_smalltable_001_10 | omomo_new | – (R028_grasp_candidates) | smalltable | sub12 | R | 128 | 30 | True |  |
| dev | sub12_smalltable_002_20 | omomo_new | – (R028_grasp_candidates) | smalltable | sub12 | L | 153 | 30 | True |  |
| dev | sub12_smalltable_004_0 | omomo_new | – (R028_grasp_candidates) | smalltable | sub12 | L | 118 | 30 | True |  |
| dev | sub12_smalltable_005_24 | omomo_new | – (R028_grasp_candidates) | smalltable | sub12 | L | 155 | 30 | True |  |
| dev | sub12_smalltable_006_0 | omomo_new | – (R028_grasp_candidates) | smalltable | sub12 | L | 154 | 30 | True |  |
| dev | sub12_smalltable_007_0 | omomo_new | – (R028_grasp_candidates) | smalltable | sub12 | R | 142 | 30 | True |  |
| dev | sub12_smalltable_008_3 | omomo_new | – (R028_grasp_candidates) | smalltable | sub12 | L | 139 | 30 | True |  |
| dev | sub12_smalltable_009_17 | omomo_new | – (R028_grasp_candidates) | smalltable | sub12 | L | 125 | 30 | True |  |
| dev | sub12_smalltable_072_51 | omomo_new | – (R028_grasp_candidates) | smalltable | sub12 | R | 182 | 30 | True |  |
| dev | sub12_smalltable_073_89 | omomo_new | – (R028_grasp_candidates) | smalltable | sub12 | L | 211 | 30 | True |  |
| dev | sub12_smalltable_074_126 | omomo_new | – (R028_grasp_candidates) | smalltable | sub12 | R | 242 | 30 | True |  |
| dev | sub12_smalltable_078_144 | omomo_new | – (R028_grasp_candidates) | smalltable | sub12 | R | 330 | 30 | True |  |
| dev | sub12_smalltable_079_113 | omomo_new | – (R028_grasp_candidates) | smalltable | sub12 | B | 285 | 30 | True |  |
| dev | sub12_woodchair_004_17 | omomo_new | – (R028_grasp_candidates) | woodchair | sub12 | L | 292 | 30 | True |  |
| dev | sub1_largetable_004_3 | omomo_new | – (R028_grasp_candidates) | largetable | sub1 | R | 124 | 30 | True |  |
| dev | sub1_largetable_007_12 | omomo_new | – (R028_grasp_candidates) | largetable | sub1 | R | 170 | 30 | True |  |
| dev | sub1_largetable_009_11 | omomo_new | – (R028_grasp_candidates) | largetable | sub1 | R | 168 | 30 | True |  |
| dev | sub1_largetable_010_9 | omomo_new | – (R028_grasp_candidates) | largetable | sub1 | L | 167 | 30 | True |  |
| dev | sub1_plasticbox_081_90 | omomo_new | – (R028_grasp_candidates) | plasticbox | sub1 | L | 208 | 30 | True |  |
| dev | sub1_plasticbox_088_69 | omomo_new | – (R028_grasp_candidates) | plasticbox | sub1 | L | 197 | 30 | True |  |
| dev | sub1_suitcase_062_4 | omomo_new | – (R028_grasp_candidates) | suitcase | sub1 | L | 143 | 30 | True |  |
| dev | sub1_suitcase_085_90 | omomo_new | – (R028_grasp_candidates) | suitcase | sub1 | L | 201 | 30 | True |  |
| dev | sub3_largetable_000_107 | omomo_new | – (R028_grasp_candidates) | largetable | sub3 | L | 179 | 30 | True |  |
| dev | sub3_largetable_001_45 | omomo_new | – (R028_grasp_candidates) | largetable | sub3 | R | 197 | 30 | True |  |
| dev | sub3_largetable_002_13 | omomo_new | – (R028_grasp_candidates) | largetable | sub3 | L | 219 | 30 | True |  |
| dev | sub3_largetable_011_3 | omomo_new | – (R028_grasp_candidates) | largetable | sub3 | R | 172 | 30 | True |  |
| dev | sub3_largetable_027_83 | omomo_new | – (R028_grasp_candidates) | largetable | sub3 | L | 202 | 30 | True |  |
| dev | sub3_largetable_028_66 | omomo_new | – (R028_grasp_candidates) | largetable | sub3 | L | 182 | 30 | True |  |
| dev | sub3_woodchair_013_4 | omomo_new | – (R028_grasp_candidates) | woodchair | sub3 | L | 166 | 30 | True |  |
| dev | sub5_plasticbox_037_1 | omomo_new | – (R028_grasp_candidates) | plasticbox | sub5 | B | 223 | 30 | True |  |
| dev | sub5_plasticbox_048_214 | omomo_new | – (R028_grasp_candidates) | plasticbox | sub5 | B | 310 | 30 | True |  |
| dev | sub5_plasticbox_050_178 | omomo_new | – (R028_grasp_candidates) | plasticbox | sub5 | L | 269 | 30 | True |  |
| dev | sub5_whitechair_019_1 | omomo_new | – (R028_grasp_candidates) | whitechair | sub5 | L | 222 | 30 | True |  |
| dev | sub5_whitechair_036_210 | omomo_new | – (R028_grasp_candidates) | whitechair | sub5 | R | 300 | 30 | True |  |
| dev | sub6_trashcan_036_36 | omomo_new | – (R028_grasp_candidates) | trashcan | sub6 | R | 146 | 30 | True |  |
| dev | sub6_trashcan_037_13 | omomo_new | – (R028_grasp_candidates) | trashcan | sub6 | R | 146 | 30 | True |  |
| dev | sub6_trashcan_038_18 | omomo_new | – (R028_grasp_candidates) | trashcan | sub6 | R | 156 | 30 | True |  |
| dev | sub6_trashcan_040_30 | omomo_new | – (R028_grasp_candidates) | trashcan | sub6 | R | 188 | 30 | True |  |
| dev | sub6_trashcan_041_28 | omomo_new | – (R028_grasp_candidates) | trashcan | sub6 | R | 182 | 30 | True |  |
| dev | sub6_trashcan_048_76 | omomo_new | – (R028_grasp_candidates) | trashcan | sub6 | L | 170 | 30 | True |  |
| dev | sub6_trashcan_049_114 | omomo_new | – (R028_grasp_candidates) | trashcan | sub6 | L | 202 | 30 | True |  |
| dev | sub6_trashcan_050_107 | omomo_new | – (R028_grasp_candidates) | trashcan | sub6 | L | 203 | 30 | True |  |
| dev | sub6_trashcan_051_86 | omomo_new | – (R028_grasp_candidates) | trashcan | sub6 | R | 192 | 30 | True |  |
| dev | sub6_trashcan_052_95 | omomo_new | – (R028_grasp_candidates) | trashcan | sub6 | R | 203 | 30 | True |  |
| dev | sub6_whitechair_019_9 | omomo_new | – (R028_grasp_candidates) | whitechair | sub6 | R | 201 | 30 | True |  |
| dev | sub6_woodchair_046_25 | omomo_new | – (R028_grasp_candidates) | woodchair | sub6 | L | 175 | 30 | True |  |
| heldout | sub10_whitechair_064_115 | omomo_new | – (R028_grasp_candidates) | whitechair | sub10 | R | 255 | 30 | True |  |
| heldout | sub11_monitor_063_15 | omomo_new | – (R028_grasp_candidates) | monitor | sub11 | R | 161 | 30 | True |  |
| heldout | sub11_monitor_072_23 | omomo_new | – (R028_grasp_candidates) | monitor | sub11 | L | 148 | 30 | True |  |
| heldout | sub11_monitor_077_19 | omomo_new | – (R028_grasp_candidates) | monitor | sub11 | R | 125 | 30 | True |  |
| heldout | sub11_monitor_078_2 | omomo_new | – (R028_grasp_candidates) | monitor | sub11 | L | 112 | 30 | True |  |
| heldout | sub11_trashcan_046_21 | omomo_new | – (R028_grasp_candidates) | trashcan | sub11 | R | 141 | 30 | True |  |
| heldout | sub11_trashcan_049_27 | omomo_new | – (R028_grasp_candidates) | trashcan | sub11 | L | 134 | 30 | True |  |
| heldout | sub11_trashcan_050_18 | omomo_new | – (R028_grasp_candidates) | trashcan | sub11 | R | 125 | 30 | True |  |
| heldout | sub11_trashcan_052_18 | omomo_new | – (R028_grasp_candidates) | trashcan | sub11 | R | 110 | 30 | True |  |
| heldout | sub11_trashcan_055_11 | omomo_new | – (R028_grasp_candidates) | trashcan | sub11 | R | 119 | 30 | True |  |
| heldout | sub11_trashcan_056_21 | omomo_new | – (R028_grasp_candidates) | trashcan | sub11 | R | 110 | 30 | True |  |
| heldout | sub11_trashcan_058_25 | omomo_new | – (R028_grasp_candidates) | trashcan | sub11 | R | 131 | 30 | True |  |
| heldout | sub11_trashcan_059_18 | omomo_new | – (R028_grasp_candidates) | trashcan | sub11 | R | 113 | 30 | True |  |
| heldout | sub11_trashcan_060_17 | omomo_new | – (R028_grasp_candidates) | trashcan | sub11 | L | 119 | 30 | True |  |
| heldout | sub13_whitechair_028_0 | omomo_new | – (R028_grasp_candidates) | whitechair | sub13 | R | 136 | 30 | True |  |
| heldout | sub13_whitechair_029_0 | omomo_new | – (R028_grasp_candidates) | whitechair | sub13 | R | 131 | 30 | True |  |
| heldout | sub13_whitechair_045_35 | omomo_new | – (R028_grasp_candidates) | whitechair | sub13 | L | 125 | 30 | True |  |
| heldout | sub14_smalltable_000_0 | omomo_new | – (R028_grasp_candidates) | smalltable | sub14 | R | 125 | 30 | True |  |
| heldout | sub14_suitcase_020_5 | omomo_new | – (R028_grasp_candidates) | suitcase | sub14 | B | 204 | 30 | True |  |
| heldout | sub15_largetable_003_0 | omomo_new | – (R028_grasp_candidates) | largetable | sub15 | B | 109 | 30 | True |  |
| heldout | sub15_largetable_005_0 | omomo_new | – (R028_grasp_candidates) | largetable | sub15 | B | 107 | 30 | True |  |
| heldout | sub15_plasticbox_047_32 | omomo_new | – (R028_grasp_candidates) | plasticbox | sub15 | B | 122 | 30 | True |  |
| heldout | sub15_plasticbox_048_9 | omomo_new | – (R028_grasp_candidates) | plasticbox | sub15 | R | 116 | 30 | True |  |
| heldout | sub15_plasticbox_050_38 | omomo_new | – (R028_grasp_candidates) | plasticbox | sub15 | B | 119 | 30 | True |  |
| heldout | sub15_trashcan_060_0 | omomo_new | – (R028_grasp_candidates) | trashcan | sub15 | R | 77 | 30 | True |  |
| heldout | sub16_largebox_039_0 | omomo_new | – (R028_grasp_candidates) | largebox | sub16 | R | 127 | 30 | True |  |
| heldout | sub16_largebox_041_25 | omomo_new | – (R028_grasp_candidates) | largebox | sub16 | R | 135 | 30 | True |  |
| heldout | sub16_largetable_033_54 | omomo_new | – (R028_grasp_candidates) | largetable | sub16 | L | 149 | 30 | True |  |
| heldout | sub16_plasticbox_050_77 | omomo_new | – (R028_grasp_candidates) | plasticbox | sub16 | L | 165 | 30 | True |  |
| heldout | sub16_plasticbox_054_79 | omomo_new | – (R028_grasp_candidates) | plasticbox | sub16 | L | 204 | 30 | True |  |
| heldout | sub16_trashcan_036_28 | omomo_new | – (R028_grasp_candidates) | trashcan | sub16 | R | 127 | 30 | True |  |
| heldout | sub17_smalltable_001_1 | omomo_new | – (R028_grasp_candidates) | smalltable | sub17 | L | 93 | 30 | True |  |
| heldout | sub17_smalltable_003_0 | omomo_new | – (R028_grasp_candidates) | smalltable | sub17 | L | 114 | 30 | True |  |
| heldout | sub17_smalltable_004_0 | omomo_new | – (R028_grasp_candidates) | smalltable | sub17 | R | 100 | 30 | True |  |
| heldout | sub17_smalltable_005_0 | omomo_new | – (R028_grasp_candidates) | smalltable | sub17 | L | 172 | 30 | True |  |
| heldout | sub17_smalltable_006_0 | omomo_new | – (R028_grasp_candidates) | smalltable | sub17 | R | 175 | 30 | True |  |
| heldout | sub17_smalltable_007_0 | omomo_new | – (R028_grasp_candidates) | smalltable | sub17 | R | 194 | 30 | True |  |
| heldout | sub17_smalltable_039_128 | omomo_new | – (R028_grasp_candidates) | smalltable | sub17 | R | 244 | 30 | True |  |
| heldout | sub17_smalltable_040_81 | omomo_new | – (R028_grasp_candidates) | smalltable | sub17 | R | 175 | 30 | True |  |
| heldout | sub17_woodchair_021_0 | omomo_new | – (R028_grasp_candidates) | woodchair | sub17 | L | 181 | 30 | True |  |
| heldout | sub2_woodchair_009_0 | omomo_new | – (R028_grasp_candidates) | woodchair | sub2 | R | 133 | 30 | True |  |
| heldout | sub2_woodchair_010_0 | omomo_new | – (R028_grasp_candidates) | woodchair | sub2 | L | 147 | 30 | True |  |
| heldout | sub2_woodchair_011_1 | omomo_new | – (R028_grasp_candidates) | woodchair | sub2 | R | 128 | 30 | True |  |
| heldout | sub4_whitechair_017_7 | omomo_new | – (R028_grasp_candidates) | whitechair | sub4 | R | 204 | 30 | True |  |
| heldout | sub4_whitechair_018_0 | omomo_new | – (R028_grasp_candidates) | whitechair | sub4 | L | 163 | 30 | True |  |
| heldout | sub4_whitechair_019_0 | omomo_new | – (R028_grasp_candidates) | whitechair | sub4 | R | 141 | 30 | True |  |
| heldout | sub4_whitechair_020_3 | omomo_new | – (R028_grasp_candidates) | whitechair | sub4 | L | 153 | 30 | True |  |
| heldout | sub4_whitechair_021_0 | omomo_new | – (R028_grasp_candidates) | whitechair | sub4 | R | 136 | 30 | True |  |
| heldout | sub4_whitechair_036_199 | omomo_new | – (R028_grasp_candidates) | whitechair | sub4 | R | 278 | 30 | True |  |
| heldout | sub4_whitechair_037_165 | omomo_new | – (R028_grasp_candidates) | whitechair | sub4 | R | 290 | 30 | True |  |
| heldout | sub4_whitechair_038_125 | omomo_new | – (R028_grasp_candidates) | whitechair | sub4 | L | 241 | 30 | True |  |
| heldout | sub4_whitechair_039_107 | omomo_new | – (R028_grasp_candidates) | whitechair | sub4 | R | 219 | 30 | True |  |
| heldout | sub4_whitechair_040_118 | omomo_new | – (R028_grasp_candidates) | whitechair | sub4 | L | 240 | 30 | True |  |
| heldout | sub4_whitechair_043_0 | omomo_new | – (R028_grasp_candidates) | whitechair | sub4 | L | 184 | 30 | True |  |
| heldout | sub4_whitechair_044_13 | omomo_new | – (R028_grasp_candidates) | whitechair | sub4 | R | 215 | 30 | True |  |
| heldout | sub4_whitechair_045_0 | omomo_new | – (R028_grasp_candidates) | whitechair | sub4 | L | 194 | 30 | True |  |
| heldout | sub4_whitechair_047_0 | omomo_new | – (R028_grasp_candidates) | whitechair | sub4 | L | 170 | 30 | True |  |
| heldout | sub7_trashcan_039_16 | omomo_new | – (R028_grasp_candidates) | trashcan | sub7 | R | 114 | 30 | True |  |
| heldout | sub7_whitechair_018_12 | omomo_new | – (R028_grasp_candidates) | whitechair | sub7 | R | 176 | 30 | True |  |
| heldout | sub7_whitechair_021_18 | omomo_new | – (R028_grasp_candidates) | whitechair | sub7 | L | 231 | 30 | True |  |
| heldout | sub7_whitechair_022_0 | omomo_new | – (R028_grasp_candidates) | whitechair | sub7 | R | 189 | 30 | True |  |
| heldout | sub7_whitechair_037_90 | omomo_new | – (R028_grasp_candidates) | whitechair | sub7 | B | 219 | 30 | True |  |
| heldout | sub7_whitechair_041_121 | omomo_new | – (R028_grasp_candidates) | whitechair | sub7 | L | 290 | 30 | True |  |
| heldout | sub8_plasticbox_038_10 | omomo_new | – (R028_grasp_candidates) | plasticbox | sub8 | R | 143 | 30 | True |  |
| heldout | sub8_plasticbox_040_11 | omomo_new | – (R028_grasp_candidates) | plasticbox | sub8 | R | 120 | 30 | True |  |
| heldout | sub8_plasticbox_050_101 | omomo_new | – (R028_grasp_candidates) | plasticbox | sub8 | L | 215 | 30 | True |  |
| heldout | sub8_suitcase_050_109 | omomo_new | – (R028_grasp_candidates) | suitcase | sub8 | L | 210 | 30 | True |  |
| heldout | sub8_trashcan_043_20 | omomo_new | – (R028_grasp_candidates) | trashcan | sub8 | R | 221 | 30 | True |  |
| heldout | sub8_trashcan_043_113 | omomo_new | – (R028_grasp_candidates) | trashcan | sub8 | L | 221 | 30 | True |  |
| heldout | sub8_trashcan_044_124 | omomo_new | – (R028_grasp_candidates) | trashcan | sub8 | L | 236 | 30 | True |  |
| heldout | sub8_trashcan_045_121 | omomo_new | – (R028_grasp_candidates) | trashcan | sub8 | L | 245 | 30 | True |  |
| heldout | sub8_trashcan_046_129 | omomo_new | – (R028_grasp_candidates) | trashcan | sub8 | L | 254 | 30 | True |  |
| heldout | sub8_trashcan_047_109 | omomo_new | – (R028_grasp_candidates) | trashcan | sub8 | L | 230 | 30 | True |  |
| heldout | sub9_smalltable_002_0 | omomo_new | – (R028_grasp_candidates) | smalltable | sub9 | L | 135 | 30 | True |  |
| heldout | sub9_smalltable_003_0 | omomo_new | – (R028_grasp_candidates) | smalltable | sub9 | R | 157 | 30 | True |  |
| heldout | sub9_smalltable_007_15 | omomo_new | – (R028_grasp_candidates) | smalltable | sub9 | L | 125 | 30 | True |  |
| heldout | sub9_smalltable_070_55 | omomo_new | – (R028_grasp_candidates) | smalltable | sub9 | L | 158 | 30 | True |  |
| heldout | sub9_smalltable_074_50 | omomo_new | – (R028_grasp_candidates) | smalltable | sub9 | R | 183 | 30 | True |  |
| heldout | sub9_smalltable_076_73 | omomo_new | – (R028_grasp_candidates) | smalltable | sub9 | R | 183 | 30 | True |  |
| heldout | 260923_04_3_1_246 | force | – (R028_grasp_candidates) | chair | session260923 | L | 586 | 30 | True |  |
| heldout | 260923_05_1_retake_4_102 | force | – (R028_grasp_candidates) | chair | session260923 | R | 469 | 30 | True |  |
| heldout | 260923_06_2_3_89 | force | – (R028_grasp_candidates) | box_huge | session260923 | R | 582 | 30 | True |  |
| heldout | 260923_06_2_3_186 | force | – (R028_grasp_candidates) | box_huge | session260923 | R | 582 | 30 | True |  |
| heldout | 260923_06_3_2_243 | force | – (R028_grasp_candidates) | box_huge | session260923 | L | 425 | 30 | True |  |
