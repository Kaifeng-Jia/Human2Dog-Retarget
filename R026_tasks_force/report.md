# Task targets (spec §4 step 1)

Run `R026_tasks_force` · code `v0.3.1-1-g8877af2` (dirty=False) · 4/4 segments · 0 errors · **PASS**

| id | confirmed | hand | dataset / clip | frames | contact z human → robot [m] | face tilt [°] | proxy–surface [m] | coherence | spread p90 [°] | approach / retreat [°] | d max [m] | grip | forearm / palm vs face [°] (~ palm mirrored, ! not used) | pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| trashcan_side | True | R | omomo_new / sub6_trashcan_003 | 24–160 | 0.15 → 0.15 (out of band) | 5 | 0.036 | 0.97 | 7.6 | 74 / 45 | 0.45 | press | 78 / 68~! | True |
| smallbox_top | True | R | omomo_new / sub7_smallbox_041 | 41–120 | 0.16 → 0.15 (rear edge) | 84 | 0.021 | 0.99 | 2.0 | 31 / 24 | 0.63 | press | 54 / 62! | True |
| largebox_top | True | R | omomo_new / sub7_largebox_041 | 35–120 | 0.35 → 0.35 (rear edge) | 87 | 0.006 | 0.99 | 2.9 | 42 / 32 | 0.56 | press | 50 / 66! | True |
| c01_0630_61-2 | False | R | force / 0630_61-2 | 472–523 | 0.47 → 0.47 (out of band) | 57 | 0.032 | 0.87 | 17.2 | 128 / 58 | 0.16 | press | 47 / 39 | True |
