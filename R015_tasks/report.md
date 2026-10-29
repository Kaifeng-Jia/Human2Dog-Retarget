# Task targets (spec learned v0.6 §4 step 1)

Run `R015_tasks` · code `v0.1.3-18-g1fd1edb` (dirty=False) · 14/14 segments · 0 errors · **PASS**

| id | confirmed | hand | dataset / clip | frames | contact z human → robot [m] | face tilt [°] | proxy–surface [m] | coherence | spread p90 [°] | approach / retreat [°] | d max [m] | grip | forearm / palm vs face [°] (~ palm mirrored, ! not used) | pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| trashcan_side | True | R | omomo_new / sub6_trashcan_003 | 24–160 | 0.15 → 0.15 (out of band) | 5 | 0.036 | 0.97 | 7.6 | 74 / 45 | 0.45 | press | 78 / 68~! | True |
| smallbox_top | True | R | omomo_new / sub7_smallbox_041 | 41–120 | 0.16 → 0.15 (rear edge) | 84 | 0.021 | 0.99 | 2.0 | 31 / 24 | 0.63 | press | 54 / 62! | True |
| largebox_top | True | R | omomo_new / sub7_largebox_041 | 35–120 | 0.35 → 0.35 (rear edge) | 87 | 0.006 | 0.99 | 2.9 | 42 / 32 | 0.56 | press | 50 / 66! | True |
| c01_sub6_largetable_033 | False | B | omomo_new / sub6_largetable_033 | 3–150 | 0.48 → 0.46 (rear edge) | 89 | 0.016 | 1.00 | 0.7 | – / 148 | 0.47 | press | 30 / 31~ | True |
| c02_sub12_largebox_000 | False | B | omomo_new / sub12_largebox_000 | 0–234 | 0.35 → 0.35 (rear edge) | 86 | 0.019 | 0.99 | 1.4 | – / 145 | 0.82 | press | 8 / 10~ | True |
| c03_sub5_largetable_030 | False | B | omomo_new / sub5_largetable_030 | 17–136 | 0.47 → 0.47 (rear edge) | 87 | 0.012 | 1.00 | 2.9 | 134 / 140 | 0.55 | press | 12 / 7~ | True |
| c04_sub12_largebox_065 | False | R | omomo_new / sub12_largebox_065 | 23–176 | 0.36 → 0.35 (rear edge) | 88 | 0.019 | 1.00 | 3.8 | 20 / 65 | 0.34 | press | 66 / 66! | True |
| c06_sub1_suitcase_008 | False | R | omomo_new / sub1_suitcase_008 | 5–89 | 0.55 → 0.53 (rear edge) | 84 | 0.020 | 0.99 | 1.4 | 126 / 131 | 0.57 | press | 8 / 37~ | True |
| c07_sub3_largebox_032 | False | L | omomo_new / sub3_largebox_032 | 80–160 | 0.35 → 0.34 (rear edge) | 86 | 0.026 | 0.98 | 2.8 | 43 / 63 | 0.18 | press | 74 / 51 | True |
| c08_sub3_largebox_031 | False | L | omomo_new / sub3_largebox_031 | 80–152 | 0.35 → 0.34 (rear edge) | 88 | 0.016 | 1.00 | 1.2 | 63 / 65 | 0.45 | press | 75 / 53 | True |
| c09_sub12_largebox_089 | False | B | omomo_new / sub12_largebox_089 | 16–85 | 0.34 → 0.34 (rear edge) | 89 | 0.007 | 0.99 | 3.0 | 34 / 86 | 0.44 | press | 24 / 60 | True |
| c10_sub1_largetable_074 | False | B | omomo_new / sub1_largetable_074 | 5–51 | 0.46 → 0.46 (rear edge) | 83 | 0.013 | 0.91 | 6.6 | 13 / 100 | 0.20 | press | 17 / 37 | True |
| c11_0630_61-2 | False | R | force / 0630_61-2 | 472–523 | 0.47 → 0.47 (out of band) | 57 | 0.032 | 0.87 | 17.2 | 128 / 58 | 0.16 | press | 47 / 39 | True |
| c12_sub1_largetable_073 | False | B | omomo_new / sub1_largetable_073 | 6–44 | 0.46 → 0.46 (rear edge) | 83 | 0.010 | 0.84 | 5.6 | 21 / 56 | 0.30 | press | 14 / 32 | True |
