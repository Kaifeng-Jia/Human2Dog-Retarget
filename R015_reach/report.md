# Frozen-body reachability (spec learned v0.6 §7.1)

Run `R015_reach` · code `v0.1.3-18-g1fd1edb` (dirty=False) · 10/10 tasks · reach bound 0.940 m (sampled max 0.939 m) · 34.9 min

| task | layout | registration (psi, residual RMS) | relations: edge / heading [°], foot slide [m/s] | scene body in object [m] | target–shoulder [m] | problem | label | feasible | err max [cm] | angle median / max [°] | roll median [°] | arm change max / RMS [°] | speed ratio max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_sub6_largetable_033 | mesh | -8.3°, – m | 8 / 1, 0.56 | 0.000 | 0.44–0.63 | pos | feasible | 100 % | 0.0 | 31 / 35 | – | 174 / 73 | 0.90 |
| c01_sub6_largetable_033 | mesh | -8.3°, – m | 8 / 1, 0.56 | 0.000 | 0.44–0.63 | pos_dir | feasible | 100 % | 0.1 | 1 / 2 | 17 | 174 / 73 | 0.66 |
| c01_sub6_largetable_033 | mesh | -8.3°, – m | 8 / 1, 0.56 | 0.000 | 0.44–0.63 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 27.3 | 35 / 41 | 140 | – / – | – |
| c01_sub6_largetable_033 | reach_track | 0.6°, 0.03 m, body +0.35 m | 11 / 10, 0.33 | 0.000 | 0.57–0.63 | pos | feasible | 100 % | 0.0 | 33 / 40 | – | 174 / 72 | 0.34 |
| c01_sub6_largetable_033 | reach_track | 0.6°, 0.03 m, body +0.35 m | 11 / 10, 0.33 | 0.000 | 0.57–0.63 | pos_dir | feasible | 100 % | 0.1 | 1 / 2 | 14 | 160 / 74 | 0.72 |
| c01_sub6_largetable_033 | reach_track | 0.6°, 0.03 m, body +0.35 m | 11 / 10, 0.33 | 0.000 | 0.57–0.63 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 25.3 | 36 / 45 | 137 | – / – | – |
| c01_sub6_largetable_033 | reach_fit | 0.6°, 0.25 m | 9 / 10, 0.00 | 0.032 | 0.34–0.96 | pos | no_feasible_solution_within_budget | 67 % | 9.4 | 43 / 69 | – | 162 / 82 | 3.46 |
| c01_sub6_largetable_033 | reach_fit | 0.6°, 0.25 m | 9 / 10, 0.00 | 0.032 | 0.34–0.96 | pos_dir | no_feasible_solution_within_budget | 52 % | 9.5 | 12 / 48 | 41 | 174 / 79 | 0.78 |
| c01_sub6_largetable_033 | reach_fit | 0.6°, 0.25 m | 9 / 10, 0.00 | 0.032 | 0.34–0.96 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 47.3 | 37 / 41 | 135 | – / – | – |
| c02_sub12_largebox_000 | mesh | -11.4°, – m | 1 / 1, 0.00 | 0.000 | 0.55–0.71 | pos | no_feasible_solution_within_budget | 21 % | 44.8 | 44 / 55 | – | 170 / 70 | 27.86 |
| c02_sub12_largebox_000 | mesh | -11.4°, – m | 1 / 1, 0.00 | 0.000 | 0.55–0.71 | pos_dir | no_feasible_solution_within_budget | 4 % | 37.0 | 38 / 46 | 41 | 197 / 95 | 0.81 |
| c02_sub12_largebox_000 | mesh | -11.4°, – m | 1 / 1, 0.00 | 0.000 | 0.55–0.71 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 113.1 | 12 / 135 | 157 | – / – | – |
| c02_sub12_largebox_000 | reach_track | -4.6°, 0.02 m, body +0.15 m | 6 / 8, 0.00 | 0.000 | 0.64–0.85 | pos | no_feasible_solution_within_budget | 9 % | 25.9 | 24 / 45 | – | 167 / 66 | 1.57 |
| c02_sub12_largebox_000 | reach_track | -4.6°, 0.02 m, body +0.15 m | 6 / 8, 0.00 | 0.000 | 0.64–0.85 | pos_dir | no_feasible_solution_within_budget | 7 % | 18.0 | 20 / 36 | 30 | 166 / 78 | 1.05 |
| c02_sub12_largebox_000 | reach_track | -4.6°, 0.02 m, body +0.15 m | 6 / 8, 0.00 | 0.000 | 0.64–0.85 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 114.6 | 11 / 128 | 155 | – / – | – |
| c02_sub12_largebox_000 | reach_fit | -4.6°, 0.07 m | 7 / 8, 0.00 | 0.046 | 0.57–0.93 | pos | no_feasible_solution_within_budget | 9 % | 48.6 | 25 / 49 | – | 129 / 60 | 4.96 |
| c02_sub12_largebox_000 | reach_fit | -4.6°, 0.07 m | 7 / 8, 0.00 | 0.046 | 0.57–0.93 | pos_dir | no_feasible_solution_within_budget | 4 % | 20.0 | 21 / 40 | 31 | 177 / 79 | 0.67 |
| c02_sub12_largebox_000 | reach_fit | -4.6°, 0.07 m | 7 / 8, 0.00 | 0.046 | 0.57–0.93 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 115.4 | 12 / 134 | 154 | – / – | – |
| c03_sub5_largetable_030 | mesh | -7.4°, – m | 5 / 1, 0.57 | 0.000 | 0.55–0.67 | pos | feasible | 100 % | 0.0 | 14 / 37 | – | 165 / 69 | 0.71 |
| c03_sub5_largetable_030 | mesh | -7.4°, – m | 5 / 1, 0.57 | 0.000 | 0.55–0.67 | pos_dir | feasible | 100 % | 0.1 | 1 / 3 | 21 | 165 / 70 | 1.23 |
| c03_sub5_largetable_030 | mesh | -7.4°, – m | 5 / 1, 0.57 | 0.000 | 0.55–0.67 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 26.3 | 19 / 29 | 153 | – / – | – |
| c03_sub5_largetable_030 | reach_track | 0.4°, 0.04 m, body +0.28 m | 7 / 8, 0.27 | 0.000 | 0.55–0.61 | pos | feasible | 100 % | 0.0 | 40 / 54 | – | 165 / 73 | 0.71 |
| c03_sub5_largetable_030 | reach_track | 0.4°, 0.04 m, body +0.28 m | 7 / 8, 0.27 | 0.000 | 0.55–0.61 | pos_dir | feasible | 100 % | 0.1 | 1 / 2 | 13 | 161 / 69 | 0.87 |
| c03_sub5_largetable_030 | reach_track | 0.4°, 0.04 m, body +0.28 m | 7 / 8, 0.27 | 0.000 | 0.55–0.61 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 21.3 | 19 / 32 | 149 | – / – | – |
| c03_sub5_largetable_030 | reach_fit | 0.4°, 0.18 m | 6 / 8, 0.00 | 0.000 | 0.34–0.87 | pos | feasible | 100 % | 1.0 | 66 / 80 | – | 183 / 83 | 26.84 |
| c03_sub5_largetable_030 | reach_fit | 0.4°, 0.18 m | 6 / 8, 0.00 | 0.000 | 0.34–0.87 | pos_dir | no_feasible_solution_within_budget | 69 % | 1.7 | 2 / 32 | 14 | 159 / 70 | 3.45 |
| c03_sub5_largetable_030 | reach_fit | 0.4°, 0.18 m | 6 / 8, 0.00 | 0.000 | 0.34–0.87 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 38.3 | 22 / 36 | 146 | – / – | – |
| c04_sub12_largebox_065 | mesh | -11.5°, – m | 4 / 2, 0.64 | 0.013 | 0.60–0.69 | pos | feasible | 100 % | 0.0 | 59 / 62 | – | 181 / 85 | 0.55 |
| c04_sub12_largebox_065 | mesh | -11.5°, – m | 4 / 2, 0.64 | 0.013 | 0.60–0.69 | pos_dir | feasible | 100 % | 0.1 | 1 / 3 | – | 181 / 91 | 1.11 |
| c04_sub12_largebox_065 | mesh | -11.5°, – m | 4 / 2, 0.64 | 0.013 | 0.60–0.69 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 51.2 | 41 / 52 | – | – / – | – |
| c04_sub12_largebox_065 | reach_track | -5.6°, 0.02 m, body +0.15 m | 80 / 8, 0.16 | 0.000 | 0.63–0.70 | pos | feasible | 100 % | 0.1 | 18 / 42 | – | 181 / 80 | 0.64 |
| c04_sub12_largebox_065 | reach_track | -5.6°, 0.02 m, body +0.15 m | 80 / 8, 0.16 | 0.000 | 0.63–0.70 | pos_dir | feasible | 100 % | 0.5 | 4 / 11 | – | 181 / 83 | 0.80 |
| c04_sub12_largebox_065 | reach_track | -5.6°, 0.02 m, body +0.15 m | 80 / 8, 0.16 | 0.000 | 0.63–0.70 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 43.3 | 31 / 45 | – | – / – | – |
| c04_sub12_largebox_065 | reach_fit | -5.6°, 0.10 m | 80 / 8, 0.00 | 0.000 | 0.53–0.77 | pos | no_feasible_solution_within_budget | 90 % | 0.7 | 29 / 51 | – | 181 / 80 | 0.60 |
| c04_sub12_largebox_065 | reach_fit | -5.6°, 0.10 m | 80 / 8, 0.00 | 0.000 | 0.53–0.77 | pos_dir | no_feasible_solution_within_budget | 57 % | 1.3 | 6 / 25 | – | 181 / 80 | 0.66 |
| c04_sub12_largebox_065 | reach_fit | -5.6°, 0.10 m | 80 / 8, 0.00 | 0.000 | 0.53–0.77 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 47.8 | 32 / 44 | – | – / – | – |
| c06_sub1_suitcase_008 | mesh | 30.2°, – m | 3 / 2, 0.39 | 0.000 | 0.56–0.65 | pos | feasible | 100 % | 0.0 | 69 / 79 | – | 174 / 78 | 0.38 |
| c06_sub1_suitcase_008 | mesh | 30.2°, – m | 3 / 2, 0.39 | 0.000 | 0.56–0.65 | pos_dir | feasible | 100 % | 0.1 | 0 / 2 | 4 | 174 / 74 | 0.67 |
| c06_sub1_suitcase_008 | mesh | 30.2°, – m | 3 / 2, 0.39 | 0.000 | 0.56–0.65 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 30.3 | 34 / 53 | 147 | – / – | – |
| c06_sub1_suitcase_008 | reach_track | 12.5°, 0.04 m, body +0.32 m | 7 / 19, 0.33 | 0.000 | 0.55–0.60 | pos | feasible | 100 % | 0.0 | 80 / 85 | – | 174 / 91 | 0.24 |
| c06_sub1_suitcase_008 | reach_track | 12.5°, 0.04 m, body +0.32 m | 7 / 19, 0.33 | 0.000 | 0.55–0.60 | pos_dir | feasible | 100 % | 0.1 | 1 / 2 | 9 | 174 / 72 | 0.62 |
| c06_sub1_suitcase_008 | reach_track | 12.5°, 0.04 m, body +0.32 m | 7 / 19, 0.33 | 0.000 | 0.55–0.60 | pos_dir_budget | no_feasible_solution_within_budget | 7 % | 22.9 | 21 / 26 | 149 | 20 / 17 | 0.18 |
| c06_sub1_suitcase_008 | reach_fit | 12.5°, 0.21 m | 4 / 19, 0.00 | 0.000 | 0.45–0.80 | pos | feasible | 100 % | 0.0 | 37 / 53 | – | 111 / 48 | 0.39 |
| c06_sub1_suitcase_008 | reach_fit | 12.5°, 0.21 m | 4 / 19, 0.00 | 0.000 | 0.45–0.80 | pos_dir | feasible | 100 % | 0.6 | 3 / 13 | 28 | 159 / 74 | 1.03 |
| c06_sub1_suitcase_008 | reach_fit | 12.5°, 0.21 m | 4 / 19, 0.00 | 0.000 | 0.45–0.80 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 39.9 | 26 / 57 | 141 | – / – | – |
| c07_sub3_largebox_032 | mesh | -10.8°, – m | 2 / 10, 0.52 | 0.000 | 0.67–0.76 | pos | feasible | 100 % | 0.0 | 59 / 63 | – | 165 / 90 | 0.41 |
| c07_sub3_largebox_032 | mesh | -10.8°, – m | 2 / 10, 0.52 | 0.000 | 0.67–0.76 | pos_dir | no_feasible_solution_within_budget | 69 % | 1.0 | 14 / 21 | 14 | 169 / 79 | 0.53 |
| c07_sub3_largebox_032 | mesh | -10.8°, – m | 2 / 10, 0.52 | 0.000 | 0.67–0.76 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 57.3 | 50 / 58 | 52 | – / – | – |
| c07_sub3_largebox_032 | reach_track | -7.9°, 0.02 m, body +0.32 m | 47 / 13, 0.37 | 0.017 | 0.62–0.67 | pos | feasible | 100 % | 0.0 | 33 / 39 | – | 165 / 83 | 0.20 |
| c07_sub3_largebox_032 | reach_track | -7.9°, 0.02 m, body +0.32 m | 47 / 13, 0.37 | 0.017 | 0.62–0.67 | pos_dir | feasible | 100 % | 0.2 | 1 / 5 | 1 | 157 / 66 | 0.40 |
| c07_sub3_largebox_032 | reach_track | -7.9°, 0.02 m, body +0.32 m | 47 / 13, 0.37 | 0.017 | 0.62–0.67 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 49.6 | 43 / 59 | 58 | – / – | – |
| c07_sub3_largebox_032 | reach_fit | -7.9°, 0.22 m | 50 / 13, 0.00 | 0.130 | 0.45–0.94 | pos | no_feasible_solution_within_budget | 72 % | 9.4 | 32 / 58 | – | 156 / 79 | 1.48 |
| c07_sub3_largebox_032 | reach_fit | -7.9°, 0.22 m | 50 / 13, 0.00 | 0.130 | 0.45–0.94 | pos_dir | no_feasible_solution_within_budget | 35 % | 9.6 | 23 / 61 | 20 | 137 / 55 | 0.99 |
| c07_sub3_largebox_032 | reach_fit | -7.9°, 0.22 m | 50 / 13, 0.00 | 0.130 | 0.45–0.94 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 75.2 | 43 / 65 | 61 | – / – | – |
| c08_sub3_largebox_031 | mesh | -2.5°, – m | 2 / 7, 0.61 | 0.013 | 0.64–0.74 | pos | feasible | 100 % | 0.0 | 57 / 62 | – | 139 / 66 | 0.37 |
| c08_sub3_largebox_031 | mesh | -2.5°, – m | 2 / 7, 0.61 | 0.013 | 0.64–0.74 | pos_dir | no_feasible_solution_within_budget | 64 % | 0.9 | 13 / 19 | 13 | 159 / 84 | 0.48 |
| c08_sub3_largebox_031 | mesh | -2.5°, – m | 2 / 7, 0.61 | 0.013 | 0.64–0.74 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 53.7 | 52 / 58 | 53 | – / – | – |
| c08_sub3_largebox_031 | reach_track | 0.5°, 0.03 m, body +0.22 m | 52 / 10, 0.31 | 0.045 | 0.60–0.64 | pos | feasible | 100 % | 0.0 | 54 / 59 | – | 165 / 88 | 0.24 |
| c08_sub3_largebox_031 | reach_track | 0.5°, 0.03 m, body +0.22 m | 52 / 10, 0.31 | 0.045 | 0.60–0.64 | pos_dir | feasible | 100 % | 0.1 | 1 / 3 | 154 | 165 / 93 | 0.55 |
| c08_sub3_largebox_031 | reach_track | 0.5°, 0.03 m, body +0.22 m | 52 / 10, 0.31 | 0.045 | 0.60–0.64 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 44.5 | 47 / 61 | 64 | – / – | – |
| c08_sub3_largebox_031 | reach_fit | 0.5°, 0.16 m | 55 / 10, 0.00 | 0.089 | 0.45–0.76 | pos | feasible | 100 % | 0.1 | 37 / 58 | – | 165 / 82 | 0.83 |
| c08_sub3_largebox_031 | reach_fit | 0.5°, 0.16 m | 55 / 10, 0.00 | 0.089 | 0.45–0.76 | pos_dir | no_feasible_solution_within_budget | 58 % | 1.3 | 8 / 29 | 5 | 134 / 56 | 1.04 |
| c08_sub3_largebox_031 | reach_fit | 0.5°, 0.16 m | 55 / 10, 0.00 | 0.089 | 0.45–0.76 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 57.1 | 47 / 64 | 66 | – / – | – |
| c09_sub12_largebox_089 | mesh | -14.5°, – m | 6 / 2, 0.65 | 0.000 | 0.52–0.65 | pos | feasible | 100 % | 0.0 | 24 / 41 | – | 174 / 78 | 0.93 |
| c09_sub12_largebox_089 | mesh | -14.5°, – m | 6 / 2, 0.65 | 0.000 | 0.52–0.65 | pos_dir | feasible | 100 % | 0.1 | 0 / 2 | 0 | 80 / 31 | 1.04 |
| c09_sub12_largebox_089 | mesh | -14.5°, – m | 6 / 2, 0.65 | 0.000 | 0.52–0.65 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 41.9 | 24 / 40 | 21 | – / – | – |
| c09_sub12_largebox_089 | reach_track | -2.6°, 0.03 m, body +0.21 m | 12 / 12, 0.28 | 0.000 | 0.61–0.67 | pos | feasible | 100 % | 0.0 | 20 / 39 | – | 174 / 78 | 0.37 |
| c09_sub12_largebox_089 | reach_track | -2.6°, 0.03 m, body +0.21 m | 12 / 12, 0.28 | 0.000 | 0.61–0.67 | pos_dir | feasible | 100 % | 0.1 | 0 / 1 | 0 | 88 / 37 | 0.75 |
| c09_sub12_largebox_089 | reach_track | -2.6°, 0.03 m, body +0.21 m | 12 / 12, 0.28 | 0.000 | 0.61–0.67 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 42.4 | 24 / 42 | 24 | – / – | – |
| c09_sub12_largebox_089 | reach_fit | -2.6°, 0.14 m | 12 / 12, 0.00 | 0.000 | 0.48–0.79 | pos | feasible | 100 % | 0.8 | 32 / 53 | – | 174 / 98 | 27.86 |
| c09_sub12_largebox_089 | reach_fit | -2.6°, 0.14 m | 12 / 12, 0.00 | 0.000 | 0.48–0.79 | pos_dir | no_feasible_solution_within_budget | 99 % | 0.8 | 1 / 16 | 1 | 92 / 38 | 0.69 |
| c09_sub12_largebox_089 | reach_fit | -2.6°, 0.14 m | 12 / 12, 0.00 | 0.000 | 0.48–0.79 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 41.7 | 24 / 49 | 24 | – / – | – |
| c10_sub1_largetable_074 | mesh | 5.1°, – m | 5 / 1, 0.35 | 0.000 | 0.51–0.61 | pos | feasible | 100 % | 0.0 | 22 / 25 | – | 167 / 73 | 0.50 |
| c10_sub1_largetable_074 | mesh | 5.1°, – m | 5 / 1, 0.35 | 0.000 | 0.51–0.61 | pos_dir | feasible | 100 % | 0.1 | 1 / 2 | 1 | 71 / 28 | 0.92 |
| c10_sub1_largetable_074 | mesh | 5.1°, – m | 5 / 1, 0.35 | 0.000 | 0.51–0.61 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 26.6 | 10 / 19 | 10 | – / – | – |
| c10_sub1_largetable_074 | reach_track | 5.1°, 0.05 m, body +0.14 m | 9 / 4, 0.30 | 0.000 | 0.56–0.67 | pos | feasible | 100 % | 0.0 | 19 / 29 | – | 167 / 73 | 0.42 |
| c10_sub1_largetable_074 | reach_track | 5.1°, 0.05 m, body +0.14 m | 9 / 4, 0.30 | 0.000 | 0.56–0.67 | pos_dir | feasible | 100 % | 0.1 | 1 / 1 | 1 | 78 / 29 | 0.76 |
| c10_sub1_largetable_074 | reach_track | 5.1°, 0.05 m, body +0.14 m | 9 / 4, 0.30 | 0.000 | 0.56–0.67 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 30.9 | 12 / 21 | 11 | – / – | – |
| c10_sub1_largetable_074 | reach_fit | 5.1°, 0.11 m | 7 / 4, 0.00 | 0.000 | 0.53–0.71 | pos | feasible | 100 % | 0.0 | 12 / 18 | – | 167 / 74 | 0.51 |
| c10_sub1_largetable_074 | reach_fit | 5.1°, 0.11 m | 7 / 4, 0.00 | 0.000 | 0.53–0.71 | pos_dir | feasible | 100 % | 0.1 | 0 / 1 | 0 | 81 / 30 | 0.97 |
| c10_sub1_largetable_074 | reach_fit | 5.1°, 0.11 m | 7 / 4, 0.00 | 0.000 | 0.53–0.71 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 33.8 | 12 / 20 | 11 | – / – | – |
| c12_sub1_largetable_073 | mesh | 0.9°, – m | 5 / 1, 0.39 | 0.000 | 0.53–0.63 | pos | feasible | 100 % | 0.0 | 4 / 14 | – | 167 / 69 | 0.42 |
| c12_sub1_largetable_073 | mesh | 0.9°, – m | 5 / 1, 0.39 | 0.000 | 0.53–0.63 | pos_dir | feasible | 100 % | 0.0 | 0 / 1 | 0 | 62 / 24 | 0.66 |
| c12_sub1_largetable_073 | mesh | 0.9°, – m | 5 / 1, 0.39 | 0.000 | 0.53–0.63 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 25.8 | 12 / 19 | 11 | – / – | – |
| c12_sub1_largetable_073 | reach_track | 0.4°, 0.03 m, body +0.07 m | 6 / 1, 0.18 | 0.000 | 0.56–0.64 | pos | feasible | 100 % | 0.0 | 9 / 15 | – | 65 / 27 | 0.35 |
| c12_sub1_largetable_073 | reach_track | 0.4°, 0.03 m, body +0.07 m | 6 / 1, 0.18 | 0.000 | 0.56–0.64 | pos_dir | feasible | 100 % | 0.0 | 0 / 1 | 0 | 61 / 23 | 0.56 |
| c12_sub1_largetable_073 | reach_track | 0.4°, 0.03 m, body +0.07 m | 6 / 1, 0.18 | 0.000 | 0.56–0.64 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 26.2 | 11 / 18 | 11 | – / – | – |
| c12_sub1_largetable_073 | reach_fit | 0.4°, 0.06 m | 6 / 1, 0.00 | 0.000 | 0.52–0.67 | pos | feasible | 100 % | 0.0 | 15 / 25 | – | 167 / 70 | 0.42 |
| c12_sub1_largetable_073 | reach_fit | 0.4°, 0.06 m | 6 / 1, 0.00 | 0.000 | 0.52–0.67 | pos_dir | feasible | 100 % | 0.0 | 0 / 1 | 0 | 66 / 24 | 0.68 |
| c12_sub1_largetable_073 | reach_fit | 0.4°, 0.06 m | 6 / 1, 0.00 | 0.000 | 0.52–0.67 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 27.9 | 12 / 19 | 11 | – / – | – |

## Flags and notes

- `c01_sub6_largetable_033`: palm side taken from the contact (the hand's points gave it mirrored)
- `c02_sub12_largebox_000`: palm side taken from the contact (the hand's points gave it mirrored)
- `c03_sub5_largetable_030`: palm side taken from the contact (the hand's points gave it mirrored)
- `c04_sub12_largebox_065`: palm 66° off the contact: no roll target
- `c06_sub1_suitcase_008`: palm side taken from the contact (the hand's points gave it mirrored)
