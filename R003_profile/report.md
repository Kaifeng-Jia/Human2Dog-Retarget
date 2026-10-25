# OMOMO_new data profile

Run `R003_profile` · code `v0.1.1-3-g09ef090` (dirty=False) · 4421/4421 clips · 4270 hand-contact segments · 7.50 h · 460 clips without hand contact

## Checks

| check | value | pass |
|---|---|---|
| all files processed | 0 errors | True |
| mesh/pose convention: median distance of closest flagged hand body ≤ 0.08 m per object | overall 0.0029 m; failing [] | True |
| contact labels informative | contact 0.003 m vs free hand 0.503 m | True |
| floor at z = 0: abs(median object lowest point at start) ≤ 0.03 m per object | overall -0.0007 m, toe min +0.041 m; failing ['suitcase'] | False |

![checks](checks.png)

## Overview

![overview](overview.png)

Shares of segments, in % (hands: L / R / both / mixed; object: lifted / tilted / slid / turned / still).

| object | clips | subj | size [m] | clip s | seg/clip | coverage | hands L/R/both/mixed | object li/ti/sl/tu/st | walk | other body | contact z [m] |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tripod | 459 | 7 | 1.30x1.16x0.31 | 5.2 | 1.07 | 85 | 31/36/19/14 | 61/35/1/0/2 | 75 | 1 | 0.97 |
| whitechair | 449 | 7 | 0.92x0.81x0.68 | 5.6 | 0.91 | 79 | 22/26/41/11 | 57/22/18/0/3 | 58 | 17 | 0.80 |
| woodchair | 442 | 9 | 0.88x0.64x0.62 | 6.1 | 0.94 | 81 | 22/24/40/14 | 59/24/13/0/3 | 56 | 37 | 0.86 |
| smalltable | 355 | 6 | 0.37x0.35x0.35 | 6.1 | 0.94 | 79 | 20/19/53/8 | 34/27/37/0/2 | 83 | 1 | 0.37 |
| clothesstand | 344 | 6 | 1.50x1.23x0.53 | 5.9 | 1.08 | 85 | 27/35/24/14 | 55/37/6/0/2 | 77 | 6 | 1.08 |
| floorlamp | 336 | 8 | 1.72x0.78x0.54 | 5.8 | 0.96 | 86 | 23/34/35/7 | 52/24/23/0/2 | 74 | 4 | 1.14 |
| largetable | 334 | 7 | 0.56x0.56x0.46 | 6.3 | 0.93 | 76 | 8/11/77/5 | 33/27/40/0/0 | 91 | 3 | 0.51 |
| suitcase | 332 | 7 | 0.53x0.41x0.41 | 6.4 | 0.92 | 75 | 7/9/81/4 | 60/2/37/0/0 | 75 | 18 | 0.70 |
| largebox | 329 | 6 | 0.47x0.46x0.41 | 5.7 | 0.91 | 69 | 10/13/68/9 | 53/3/42/0/2 | 68 | 7 | 0.49 |
| trashcan | 319 | 7 | 0.37x0.33x0.31 | 5.7 | 0.92 | 69 | 21/27/40/12 | 66/11/22/0/1 | 55 | 0 | 0.77 |
| plasticbox | 304 | 6 | 0.56x0.39x0.28 | 5.9 | 0.98 | 70 | 14/14/61/10 | 51/10/38/0/1 | 74 | 4 | 0.49 |
| smallbox | 243 | 6 | 0.44x0.38x0.24 | 5.2 | 0.98 | 62 | 20/21/52/7 | 42/0/56/0/2 | 65 | 1 | 0.18 |
| monitor | 175 | 7 | 0.56x0.46x0.17 | 6.4 | 1.01 | 82 | 14/24/48/14 | 72/24/4/1/0 | 79 | 1 | 0.72 |

## Most common segment kinds per object (hands / object / human, share of the object's segments)

* **tripod**: right / lifted / walk 19 %; left / lifted / walk 15 %; right / tilted / walk 11 %; left / tilted / walk 9 %
* **whitechair**: both / lifted / walk 21 %; both / lifted / stand 10 %; left / lifted / stand 6 %; right / lifted / walk 6 %
* **woodchair**: both / lifted / walk 20 %; both / lifted / stand 9 %; right / lifted / walk 6 %; mixed / lifted / stand 6 %
* **smalltable**: both / lifted / walk 23 %; both / slid / walk 14 %; both / tilted / walk 10 %; left / slid / walk 9 %
* **clothesstand**: right / lifted / walk 13 %; right / tilted / walk 13 %; left / lifted / walk 11 %; both / lifted / walk 10 %
* **floorlamp**: both / lifted / walk 17 %; right / lifted / walk 10 %; right / tilted / walk 9 %; both / lifted / stand 8 %
* **largetable**: both / lifted / walk 27 %; both / slid / walk 26 %; both / tilted / walk 17 %; right / tilted / walk 6 %
* **suitcase**: both / lifted / walk 39 %; both / lifted / stand 20 %; both / slid / walk 19 %; right / slid / walk 7 %
* **largebox**: both / lifted / walk 31 %; both / lifted / stand 19 %; both / slid / walk 13 %; right / slid / walk 8 %
* **trashcan**: both / lifted / stand 17 %; both / lifted / walk 16 %; mixed / lifted / stand 9 %; right / lifted / walk 8 %
* **plasticbox**: both / lifted / walk 29 %; both / slid / walk 13 %; both / lifted / stand 13 %; right / slid / walk 7 %
* **smallbox**: both / lifted / walk 25 %; right / slid / walk 15 %; both / lifted / stand 14 %; left / slid / walk 10 %
* **monitor**: both / lifted / walk 34 %; right / tilted / walk 13 %; both / lifted / stand 11 %; right / lifted / walk 8 %

## Distributions and body parts

![distributions](distributions.png)

![bodies](bodies.png)

## Examples

Per object: most common and second most common (hands, object) of the clip's longest segment; the clip with the median duration in that group.

### tripod #1: right / lifted (24 % of its clips) — `sub10_tripod_004`

![sub10_tripod_004](examples/sub10_tripod_004.png)

### tripod #2: left / lifted (18 % of its clips) — `sub10_tripod_042`

![sub10_tripod_042](examples/sub10_tripod_042.png)

### whitechair #1: both / lifted (34 % of its clips) — `sub13_whitechair_014`

![sub13_whitechair_014](examples/sub13_whitechair_014.png)

### whitechair #2: left / lifted (11 % of its clips) — `sub7_whitechair_045`

![sub7_whitechair_045](examples/sub7_whitechair_045.png)

### woodchair #1: both / lifted (33 % of its clips) — `sub3_woodchair_010`

![sub3_woodchair_010](examples/sub3_woodchair_010.png)

### woodchair #2: mixed / lifted (12 % of its clips) — `sub14_woodchair_066`

![sub14_woodchair_066](examples/sub14_woodchair_066.png)

### smalltable #1: both / lifted (28 % of its clips) — `sub14_smalltable_017`

![sub14_smalltable_017](examples/sub14_smalltable_017.png)

### smalltable #2: both / slid (15 % of its clips) — `sub14_smalltable_037`

![sub14_smalltable_037](examples/sub14_smalltable_037.png)

### clothesstand #1: right / lifted (18 % of its clips) — `sub10_clothesstand_048`

![sub10_clothesstand_048](examples/sub10_clothesstand_048.png)

### clothesstand #2: both / lifted (15 % of its clips) — `sub10_clothesstand_049`

![sub10_clothesstand_049](examples/sub10_clothesstand_049.png)

### floorlamp #1: both / lifted (25 % of its clips) — `sub1_floorlamp_061`

![sub1_floorlamp_061](examples/sub1_floorlamp_061.png)

### floorlamp #2: right / lifted (12 % of its clips) — `sub8_floorlamp_001`

![sub8_floorlamp_001](examples/sub8_floorlamp_001.png)

### largetable #1: both / lifted (32 % of its clips) — `sub1_largetable_040`

![sub1_largetable_040](examples/sub1_largetable_040.png)

### largetable #2: both / slid (28 % of its clips) — `sub6_largetable_035`

![sub6_largetable_035](examples/sub6_largetable_035.png)

### suitcase #1: both / lifted (62 % of its clips) — `sub17_suitcase_022`

![sub17_suitcase_022](examples/sub17_suitcase_022.png)

### suitcase #2: both / slid (20 % of its clips) — `sub14_suitcase_022`

![sub14_suitcase_022](examples/sub14_suitcase_022.png)

### largebox #1: both / lifted (53 % of its clips) — `sub16_largebox_010`

![sub16_largebox_010](examples/sub16_largebox_010.png)

### largebox #2: both / slid (14 % of its clips) — `sub3_largebox_024`

![sub3_largebox_024](examples/sub3_largebox_024.png)

### trashcan #1: both / lifted (35 % of its clips) — `sub11_trashcan_002`

![sub11_trashcan_002](examples/sub11_trashcan_002.png)

### trashcan #2: mixed / lifted (13 % of its clips) — `sub16_trashcan_021`

![sub16_trashcan_021](examples/sub16_trashcan_021.png)

### plasticbox #1: both / lifted (47 % of its clips) — `sub16_plasticbox_013`

![sub16_plasticbox_013](examples/sub16_plasticbox_013.png)

### plasticbox #2: both / slid (15 % of its clips) — `sub12_plasticbox_003`

![sub12_plasticbox_003](examples/sub12_plasticbox_003.png)

### smallbox #1: both / lifted (46 % of its clips) — `sub7_smallbox_027`

![sub7_smallbox_027](examples/sub7_smallbox_027.png)

### smallbox #2: right / slid (19 % of its clips) — `sub10_smallbox_098`

![sub10_smallbox_098](examples/sub10_smallbox_098.png)

### monitor #1: both / lifted (45 % of its clips) — `sub11_monitor_121`

![sub11_monitor_121](examples/sub11_monitor_121.png)

### monitor #2: mixed / lifted (14 % of its clips) — `sub17_monitor_031`

![sub17_monitor_031](examples/sub17_monitor_031.png)

## Label thresholds

```
{"min_run_s": 0.2, "max_gap_s": 0.3, "min_seg_s": 0.3, "lift_m": 0.05, "lift_frac": 0.3, "tilt_deg": 15.0, "slide_m": 0.1, "yaw_deg": 20.0, "walk_m": 0.5}
```
