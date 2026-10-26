# Frozen-body reachability (spec learned v0.6 §7.1)

Run `R010_reach` · code `v0.1.3-11-gf6899c2` (dirty=False) · 5/5 tasks · reach bound 0.940 m (sampled max 0.939 m) · 20.9 min

| task | layout | registration (psi, residual RMS) | scene body in object [m] | target–shoulder [m] | problem | label | feasible | err max [cm] | angle median / max [°] | arm change max / RMS [°] | speed ratio max |
|---|---|---|---|---|---|---|---|---|---|---|---|
| c01_sub6_largetable_033 | contact_fit | 0.4°, 0.26 m | 0.045 | 0.32–0.93 | pos | no_feasible_solution_within_budget | 78 % | 6.4 | 115 / 164 | 169 / 61 | 27.79 |
| c01_sub6_largetable_033 | contact_fit | 0.4°, 0.26 m | 0.045 | 0.32–0.93 | pos_dir | no_feasible_solution_within_budget | 0 % | 6.9 | 96 / 134 | – / – | – |
| c01_sub6_largetable_033 | contact_fit | 0.4°, 0.26 m | 0.045 | 0.32–0.93 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 44.7 | 126 / 148 | – / – | – |
| c01_sub6_largetable_033 | start_anchored | 0.3°, 0.61 m | 0.221 | 0.22–0.45 | pos | no_feasible_solution_within_budget | 43 % | 13.3 | 133 / 180 | 209 / 81 | 11.23 |
| c01_sub6_largetable_033 | start_anchored | 0.3°, 0.61 m | 0.221 | 0.22–0.45 | pos_dir | no_feasible_solution_within_budget | 0 % | 13.5 | 109 / 179 | – / – | – |
| c01_sub6_largetable_033 | start_anchored | 0.3°, 0.61 m | 0.221 | 0.22–0.45 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 91.9 | 121 / 145 | – / – | – |
| c02_sub12_largebox_000 | contact_fit | -1.1°, 0.16 m | 0.063 | 0.59–0.93 | pos | no_feasible_solution_within_budget | 8 % | 48.2 | 155 / 166 | 198 / 116 | 1.08 |
| c02_sub12_largebox_000 | contact_fit | -1.1°, 0.16 m | 0.063 | 0.59–0.93 | pos_dir | no_feasible_solution_within_budget | 0 % | 20.2 | 150 / 160 | – / – | – |
| c02_sub12_largebox_000 | contact_fit | -1.1°, 0.16 m | 0.063 | 0.59–0.93 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 115.7 | 129 / 149 | – / – | – |
| c02_sub12_largebox_000 | start_anchored | -0.8°, 0.59 m | 0.132 | 0.33–0.64 | pos | no_feasible_solution_within_budget | 9 % | 35.3 | 150 / 176 | 219 / 71 | 35.49 |
| c02_sub12_largebox_000 | start_anchored | -0.8°, 0.59 m | 0.132 | 0.33–0.64 | pos_dir | no_feasible_solution_within_budget | 0 % | 42.9 | 146 / 176 | – / – | – |
| c02_sub12_largebox_000 | start_anchored | -0.8°, 0.59 m | 0.132 | 0.33–0.64 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 117.4 | 129 / 173 | – / – | – |
| c03_sub5_largetable_030 | contact_fit | 1.7°, 0.19 m | 0.042 | 0.30–0.86 | pos | no_feasible_solution_within_budget | 98 % | 1.7 | 155 / 173 | 201 / 67 | 5.95 |
| c03_sub5_largetable_030 | contact_fit | 1.7°, 0.19 m | 0.042 | 0.30–0.86 | pos_dir | no_feasible_solution_within_budget | 0 % | 6.5 | 87 / 109 | – / – | – |
| c03_sub5_largetable_030 | contact_fit | 1.7°, 0.19 m | 0.042 | 0.30–0.86 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 35.6 | 123 / 140 | – / – | – |
| c03_sub5_largetable_030 | start_anchored | 0.1°, 0.53 m | 0.168 | 0.13–0.39 | pos | no_feasible_solution_within_budget | 34 % | 5.2 | 145 / 178 | 160 / 77 | 4.03 |
| c03_sub5_largetable_030 | start_anchored | 0.1°, 0.53 m | 0.168 | 0.13–0.39 | pos_dir | no_feasible_solution_within_budget | 0 % | 7.8 | 101 / 177 | – / – | – |
| c03_sub5_largetable_030 | start_anchored | 0.1°, 0.53 m | 0.168 | 0.13–0.39 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 80.8 | 111 / 142 | – / – | – |
| c04_sub12_largebox_065 | contact_fit | -5.2°, 0.13 m | 0.047 | 0.48–0.69 | pos | feasible | 100 % | 0.6 | 55 / 72 | 203 / 113 | 28.25 |
| c04_sub12_largebox_065 | contact_fit | -5.2°, 0.13 m | 0.047 | 0.48–0.69 | pos_dir | no_feasible_solution_within_budget | 99 % | 0.8 | 1 / 17 | 181 / 83 | 0.70 |
| c04_sub12_largebox_065 | contact_fit | -5.2°, 0.13 m | 0.047 | 0.48–0.69 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 44.0 | 40 / 57 | – / – | – |
| c04_sub12_largebox_065 | start_anchored | 1.9°, 0.60 m | 0.029 | 0.57–0.72 | pos | feasible | 100 % | 0.0 | 21 / 37 | 231 / 117 | 0.34 |
| c04_sub12_largebox_065 | start_anchored | 1.9°, 0.60 m | 0.029 | 0.57–0.72 | pos_dir | feasible | 100 % | 0.6 | 1 / 12 | 181 / 93 | 1.47 |
| c04_sub12_largebox_065 | start_anchored | 1.9°, 0.60 m | 0.029 | 0.57–0.72 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 69.4 | 46 / 60 | – / – | – |
| c05_sub1_suitcase_008 | contact_fit | 12.7°, 0.23 m | 0.000 | 0.47–0.84 | pos | feasible | 100 % | 0.1 | 105 / 129 | 174 / 77 | 0.82 |
| c05_sub1_suitcase_008 | contact_fit | 12.7°, 0.23 m | 0.000 | 0.47–0.84 | pos_dir | no_feasible_solution_within_budget | 0 % | 4.4 | 86 / 124 | – / – | – |
| c05_sub1_suitcase_008 | contact_fit | 12.7°, 0.23 m | 0.000 | 0.47–0.84 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 41.1 | 129 / 146 | – / – | – |
| c05_sub1_suitcase_008 | start_anchored | -0.6°, 0.54 m | 0.131 | 0.20–0.72 | pos | no_feasible_solution_within_budget | 85 % | 5.2 | 149 / 176 | 171 / 65 | 5.99 |
| c05_sub1_suitcase_008 | start_anchored | -0.6°, 0.54 m | 0.131 | 0.20–0.72 | pos_dir | no_feasible_solution_within_budget | 0 % | 7.4 | 89 / 160 | – / – | – |
| c05_sub1_suitcase_008 | start_anchored | -0.6°, 0.54 m | 0.131 | 0.20–0.72 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 55.6 | 130 / 145 | – / – | – |
