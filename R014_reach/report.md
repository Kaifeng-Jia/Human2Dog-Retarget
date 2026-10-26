# Frozen-body reachability (spec learned v0.6 §7.1)

Run `R014_reach` · code `v0.1.3-17-g0872d25` (dirty=False) · 5/5 tasks · reach bound 0.940 m (sampled max 0.939 m) · 26.9 min

| task | layout | registration (psi, residual RMS) | relations: edge / heading [°], foot slide [m/s] | scene body in object [m] | target–shoulder [m] | problem | label | feasible | err max [cm] | angle median / max [°] | roll median [°] | arm change max / RMS [°] | speed ratio max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_sub6_largetable_033 | mesh | -8.1°, – m | 7 / 2, 0.55 | 0.000 | 0.44–0.63 | pos | feasible | 100 % | 0.0 | 31 / 35 | – | 174 / 73 | 0.90 |
| c01_sub6_largetable_033 | mesh | -8.1°, – m | 7 / 2, 0.55 | 0.000 | 0.44–0.63 | pos_dir | feasible | 100 % | 0.0 | 0 / 1 | – | 174 / 73 | 0.68 |
| c01_sub6_largetable_033 | mesh | -8.1°, – m | 7 / 2, 0.55 | 0.000 | 0.44–0.63 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 27.2 | 35 / 41 | – | – / – | – |
| c01_sub6_largetable_033 | reach_track | 0.6°, 0.03 m, body +0.35 m | 11 / 10, 0.33 | 0.000 | 0.57–0.63 | pos | feasible | 100 % | 0.0 | 33 / 40 | – | 174 / 72 | 0.34 |
| c01_sub6_largetable_033 | reach_track | 0.6°, 0.03 m, body +0.35 m | 11 / 10, 0.33 | 0.000 | 0.57–0.63 | pos_dir | feasible | 100 % | 0.1 | 0 / 1 | – | 174 / 78 | 0.71 |
| c01_sub6_largetable_033 | reach_track | 0.6°, 0.03 m, body +0.35 m | 11 / 10, 0.33 | 0.000 | 0.57–0.63 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 25.3 | 36 / 41 | – | – / – | – |
| c01_sub6_largetable_033 | reach_fit | 0.6°, 0.25 m | 9 / 10, 0.00 | 0.032 | 0.34–0.96 | pos | no_feasible_solution_within_budget | 66 % | 9.5 | 37 / 61 | – | 173 / 86 | 3.46 |
| c01_sub6_largetable_033 | reach_fit | 0.6°, 0.25 m | 9 / 10, 0.00 | 0.032 | 0.34–0.96 | pos_dir | no_feasible_solution_within_budget | 53 % | 9.5 | 11 / 49 | – | 95 / 40 | 0.95 |
| c01_sub6_largetable_033 | reach_fit | 0.6°, 0.25 m | 9 / 10, 0.00 | 0.032 | 0.34–0.96 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 49.3 | 37 / 66 | – | – / – | – |
| c02_sub12_largebox_000 | mesh | -11.5°, – m | 1 / 1, 0.00 | 0.000 | 0.54–0.71 | pos | no_feasible_solution_within_budget | 20 % | 34.8 | 45 / 58 | – | 194 / 74 | 27.84 |
| c02_sub12_largebox_000 | mesh | -11.5°, – m | 1 / 1, 0.00 | 0.000 | 0.54–0.71 | pos_dir | no_feasible_solution_within_budget | 4 % | 39.7 | 39 / 48 | – | 176 / 79 | 0.87 |
| c02_sub12_largebox_000 | mesh | -11.5°, – m | 1 / 1, 0.00 | 0.000 | 0.54–0.71 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 113.0 | 12 / 135 | – | – / – | – |
| c02_sub12_largebox_000 | reach_track | -4.6°, 0.02 m, body +0.15 m | 6 / 8, 0.00 | 0.000 | 0.64–0.85 | pos | no_feasible_solution_within_budget | 9 % | 51.2 | 24 / 45 | – | 167 / 66 | 1.57 |
| c02_sub12_largebox_000 | reach_track | -4.6°, 0.02 m, body +0.15 m | 6 / 8, 0.00 | 0.000 | 0.64–0.85 | pos_dir | no_feasible_solution_within_budget | 7 % | 17.6 | 21 / 34 | – | 166 / 77 | 1.10 |
| c02_sub12_largebox_000 | reach_track | -4.6°, 0.02 m, body +0.15 m | 6 / 8, 0.00 | 0.000 | 0.64–0.85 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 118.7 | 11 / 134 | – | – / – | – |
| c02_sub12_largebox_000 | reach_fit | -4.6°, 0.07 m | 7 / 8, 0.00 | 0.046 | 0.57–0.93 | pos | no_feasible_solution_within_budget | 9 % | 56.5 | 26 / 49 | – | 147 / 61 | 4.93 |
| c02_sub12_largebox_000 | reach_fit | -4.6°, 0.07 m | 7 / 8, 0.00 | 0.046 | 0.57–0.93 | pos_dir | no_feasible_solution_within_budget | 4 % | 19.8 | 21 / 38 | – | 164 / 79 | 0.94 |
| c02_sub12_largebox_000 | reach_fit | -4.6°, 0.07 m | 7 / 8, 0.00 | 0.046 | 0.57–0.93 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 115.3 | 12 / 155 | – | – / – | – |
| c03_sub5_largetable_030 | mesh | -7.5°, – m | 5 / 1, 0.59 | 0.000 | 0.55–0.66 | pos | feasible | 100 % | 0.0 | 14 / 37 | – | 165 / 69 | 0.72 |
| c03_sub5_largetable_030 | mesh | -7.5°, – m | 5 / 1, 0.59 | 0.000 | 0.55–0.66 | pos_dir | feasible | 100 % | 0.1 | 0 / 3 | – | 165 / 70 | 1.20 |
| c03_sub5_largetable_030 | mesh | -7.5°, – m | 5 / 1, 0.59 | 0.000 | 0.55–0.66 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 26.0 | 18 / 29 | – | – / – | – |
| c03_sub5_largetable_030 | reach_track | 0.4°, 0.04 m, body +0.28 m | 7 / 8, 0.27 | 0.000 | 0.55–0.61 | pos | feasible | 100 % | 0.0 | 40 / 54 | – | 165 / 73 | 0.71 |
| c03_sub5_largetable_030 | reach_track | 0.4°, 0.04 m, body +0.28 m | 7 / 8, 0.27 | 0.000 | 0.55–0.61 | pos_dir | feasible | 100 % | 0.1 | 0 / 1 | – | 165 / 70 | 0.87 |
| c03_sub5_largetable_030 | reach_track | 0.4°, 0.04 m, body +0.28 m | 7 / 8, 0.27 | 0.000 | 0.55–0.61 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 21.3 | 18 / 29 | – | – / – | – |
| c03_sub5_largetable_030 | reach_fit | 0.4°, 0.18 m | 6 / 8, 0.00 | 0.000 | 0.34–0.87 | pos | feasible | 100 % | 1.0 | 66 / 80 | – | 183 / 83 | 26.84 |
| c03_sub5_largetable_030 | reach_fit | 0.4°, 0.18 m | 6 / 8, 0.00 | 0.000 | 0.34–0.87 | pos_dir | no_feasible_solution_within_budget | 69 % | 1.7 | 1 / 33 | – | 159 / 70 | 3.31 |
| c03_sub5_largetable_030 | reach_fit | 0.4°, 0.18 m | 6 / 8, 0.00 | 0.000 | 0.34–0.87 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 41.6 | 23 / 44 | – | – / – | – |
| c04_sub12_largebox_065 | mesh | -11.2°, – m | 4 / 2, 0.68 | 0.012 | 0.60–0.69 | pos | feasible | 100 % | 0.0 | 44 / 57 | – | 181 / 89 | 0.47 |
| c04_sub12_largebox_065 | mesh | -11.2°, – m | 4 / 2, 0.68 | 0.012 | 0.60–0.69 | pos_dir | feasible | 100 % | 0.1 | 1 / 3 | – | 181 / 91 | 1.03 |
| c04_sub12_largebox_065 | mesh | -11.2°, – m | 4 / 2, 0.68 | 0.012 | 0.60–0.69 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 50.8 | 40 / 52 | – | – / – | – |
| c04_sub12_largebox_065 | reach_track | -5.6°, 0.02 m, body +0.15 m | 80 / 8, 0.16 | 0.000 | 0.63–0.70 | pos | feasible | 100 % | 0.1 | 18 / 42 | – | 181 / 80 | 0.64 |
| c04_sub12_largebox_065 | reach_track | -5.6°, 0.02 m, body +0.15 m | 80 / 8, 0.16 | 0.000 | 0.63–0.70 | pos_dir | feasible | 100 % | 0.5 | 4 / 11 | – | 181 / 83 | 0.80 |
| c04_sub12_largebox_065 | reach_track | -5.6°, 0.02 m, body +0.15 m | 80 / 8, 0.16 | 0.000 | 0.63–0.70 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 43.3 | 31 / 45 | – | – / – | – |
| c04_sub12_largebox_065 | reach_fit | -5.6°, 0.10 m | 80 / 8, 0.00 | 0.000 | 0.53–0.77 | pos | no_feasible_solution_within_budget | 90 % | 0.7 | 29 / 51 | – | 181 / 80 | 0.60 |
| c04_sub12_largebox_065 | reach_fit | -5.6°, 0.10 m | 80 / 8, 0.00 | 0.000 | 0.53–0.77 | pos_dir | no_feasible_solution_within_budget | 57 % | 1.3 | 6 / 25 | – | 181 / 80 | 0.66 |
| c04_sub12_largebox_065 | reach_fit | -5.6°, 0.10 m | 80 / 8, 0.00 | 0.000 | 0.53–0.77 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 47.8 | 32 / 44 | – | – / – | – |
| c05_sub1_suitcase_008 | mesh | 29.6°, – m | 3 / 2, 0.38 | 0.000 | 0.56–0.64 | pos | feasible | 100 % | 0.0 | 70 / 80 | – | 174 / 78 | 0.32 |
| c05_sub1_suitcase_008 | mesh | 29.6°, – m | 3 / 2, 0.38 | 0.000 | 0.56–0.64 | pos_dir | feasible | 100 % | 0.1 | 0 / 1 | – | 174 / 77 | 0.63 |
| c05_sub1_suitcase_008 | mesh | 29.6°, – m | 3 / 2, 0.38 | 0.000 | 0.56–0.64 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 29.5 | 33 / 53 | – | – / – | – |
| c05_sub1_suitcase_008 | reach_track | 12.5°, 0.04 m, body +0.32 m | 7 / 19, 0.33 | 0.000 | 0.55–0.60 | pos | feasible | 100 % | 0.0 | 80 / 85 | – | 174 / 91 | 0.24 |
| c05_sub1_suitcase_008 | reach_track | 12.5°, 0.04 m, body +0.32 m | 7 / 19, 0.33 | 0.000 | 0.55–0.60 | pos_dir | feasible | 100 % | 0.0 | 0 / 1 | – | 174 / 73 | 0.47 |
| c05_sub1_suitcase_008 | reach_track | 12.5°, 0.04 m, body +0.32 m | 7 / 19, 0.33 | 0.000 | 0.55–0.60 | pos_dir_budget | no_feasible_solution_within_budget | 7 % | 23.0 | 21 / 30 | – | 20 / 17 | 0.18 |
| c05_sub1_suitcase_008 | reach_fit | 12.5°, 0.21 m | 4 / 19, 0.00 | 0.000 | 0.45–0.80 | pos | feasible | 100 % | 0.0 | 37 / 53 | – | 111 / 48 | 0.39 |
| c05_sub1_suitcase_008 | reach_fit | 12.5°, 0.21 m | 4 / 19, 0.00 | 0.000 | 0.45–0.80 | pos_dir | feasible | 100 % | 0.6 | 1 / 13 | – | 174 / 79 | 0.84 |
| c05_sub1_suitcase_008 | reach_fit | 12.5°, 0.21 m | 4 / 19, 0.00 | 0.000 | 0.45–0.80 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 39.9 | 26 / 57 | – | – / – | – |

## Flags and notes

- `c01_sub6_largetable_033`: palm faces away (149°): no roll target
- `c02_sub12_largebox_000`: palm faces away (170°): no roll target
- `c03_sub5_largetable_030`: palm faces away (173°): no roll target
- `c04_sub12_largebox_065`: palm faces away (66°): no roll target
- `c05_sub1_suitcase_008`: palm faces away (143°): no roll target
