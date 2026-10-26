# Frozen-body reachability (spec learned v0.6 §7.1)

Run `R013_reach` · code `v0.1.3-14-gfa9ae09` (dirty=False) · 3/3 tasks · reach bound 0.940 m (sampled max 0.939 m) · 23.8 min

| task | layout | registration (psi, residual RMS) | scene body in object [m] | target–shoulder [m] | problem | label | feasible | err max [cm] | angle median / max [°] | arm change max / RMS [°] | speed ratio max |
|---|---|---|---|---|---|---|---|---|---|---|---|
| c14_sub6_largetable_033 | reach_fit | 0.0°, 0.25 m | 0.068 | 0.28–0.86 | pos | no_feasible_solution_within_budget | 88 % | 1.8 | 122 / 147 | 168 / 88 | 48.50 |
| c14_sub6_largetable_033 | reach_fit | 0.0°, 0.25 m | 0.068 | 0.28–0.86 | pos_dir | no_feasible_solution_within_budget | 0 % | 12.5 | 98 / 161 | – / – | – |
| c14_sub6_largetable_033 | reach_fit | 0.0°, 0.25 m | 0.068 | 0.28–0.86 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 40.5 | 127 / 145 | – / – | – |
| c14_sub6_largetable_033 | reach_track | 0.0°, 0.03 m, body +0.35 m | 0.000 | 0.48–0.53 | pos | feasible | 100 % | 0.0 | 145 / 149 | 174 / 72 | 0.39 |
| c14_sub6_largetable_033 | reach_track | 0.0°, 0.03 m, body +0.35 m | 0.000 | 0.48–0.53 | pos_dir | no_feasible_solution_within_budget | 0 % | 4.4 | 81 / 117 | – / – | – |
| c14_sub6_largetable_033 | reach_track | 0.0°, 0.03 m, body +0.35 m | 0.000 | 0.48–0.53 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 27.5 | 129 / 151 | – / – | – |
| c14_sub6_largetable_033 | start_anchored | 0.3°, 0.61 m | 0.221 | 0.22–0.45 | pos | no_feasible_solution_within_budget | 42 % | 9.0 | 134 / 180 | 209 / 87 | 29.78 |
| c14_sub6_largetable_033 | start_anchored | 0.3°, 0.61 m | 0.221 | 0.22–0.45 | pos_dir | no_feasible_solution_within_budget | 0 % | 35.5 | 109 / 179 | – / – | – |
| c14_sub6_largetable_033 | start_anchored | 0.3°, 0.61 m | 0.221 | 0.22–0.45 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 91.4 | 120 / 145 | – / – | – |
| c15_sub12_largebox_000 | reach_fit | -3.6°, 0.07 m | 0.160 | 0.48–0.84 | pos | no_feasible_solution_within_budget | 16 % | 44.0 | 164 / 176 | 168 / 76 | 27.36 |
| c15_sub12_largebox_000 | reach_fit | -3.6°, 0.07 m | 0.160 | 0.48–0.84 | pos_dir | no_feasible_solution_within_budget | 0 % | 16.4 | 158 / 171 | – / – | – |
| c15_sub12_largebox_000 | reach_fit | -3.6°, 0.07 m | 0.160 | 0.48–0.84 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 110.9 | 129 / 154 | – / – | – |
| c15_sub12_largebox_000 | reach_track | -3.6°, 0.02 m, body +0.13 m | 0.105 | 0.55–0.79 | pos | no_feasible_solution_within_budget | 16 % | 44.9 | 166 / 172 | 170 / 75 | 28.65 |
| c15_sub12_largebox_000 | reach_track | -3.6°, 0.02 m, body +0.13 m | 0.105 | 0.55–0.79 | pos_dir | no_feasible_solution_within_budget | 0 % | 31.8 | 160 / 170 | – / – | – |
| c15_sub12_largebox_000 | reach_track | -3.6°, 0.02 m, body +0.13 m | 0.105 | 0.55–0.79 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 114.0 | 129 / 154 | – / – | – |
| c15_sub12_largebox_000 | start_anchored | -0.8°, 0.59 m | 0.132 | 0.33–0.64 | pos | no_feasible_solution_within_budget | 7 % | 33.6 | 150 / 178 | 182 / 73 | 4.55 |
| c15_sub12_largebox_000 | start_anchored | -0.8°, 0.59 m | 0.132 | 0.33–0.64 | pos_dir | no_feasible_solution_within_budget | 0 % | 30.8 | 147 / 176 | – / – | – |
| c15_sub12_largebox_000 | start_anchored | -0.8°, 0.59 m | 0.132 | 0.33–0.64 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 116.0 | 129 / 173 | – / – | – |
| c16_sub5_largetable_030 | reach_fit | 0.0°, 0.18 m | 0.123 | 0.23–0.77 | pos | no_feasible_solution_within_budget | 83 % | 7.9 | 151 / 170 | 201 / 87 | 2.75 |
| c16_sub5_largetable_030 | reach_fit | 0.0°, 0.18 m | 0.123 | 0.23–0.77 | pos_dir | no_feasible_solution_within_budget | 0 % | 7.8 | 88 / 139 | – / – | – |
| c16_sub5_largetable_030 | reach_fit | 0.0°, 0.18 m | 0.123 | 0.23–0.77 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 40.5 | 123 / 139 | – / – | – |
| c16_sub5_largetable_030 | reach_track | 0.0°, 0.03 m, body +0.30 m | 0.000 | 0.45–0.52 | pos | feasible | 100 % | 0.0 | 133 / 135 | 165 / 71 | 0.75 |
| c16_sub5_largetable_030 | reach_track | 0.0°, 0.03 m, body +0.30 m | 0.000 | 0.45–0.52 | pos_dir | no_feasible_solution_within_budget | 0 % | 3.5 | 79 / 92 | – / – | – |
| c16_sub5_largetable_030 | reach_track | 0.0°, 0.03 m, body +0.30 m | 0.000 | 0.45–0.52 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 38.7 | 125 / 142 | – / – | – |
| c16_sub5_largetable_030 | start_anchored | 0.1°, 0.53 m | 0.168 | 0.13–0.39 | pos | no_feasible_solution_within_budget | 32 % | 5.7 | 152 / 178 | 165 / 86 | 33.16 |
| c16_sub5_largetable_030 | start_anchored | 0.1°, 0.53 m | 0.168 | 0.13–0.39 | pos_dir | no_feasible_solution_within_budget | 0 % | 6.6 | 100 / 177 | – / – | – |
| c16_sub5_largetable_030 | start_anchored | 0.1°, 0.53 m | 0.168 | 0.13–0.39 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 80.8 | 114 / 142 | – / – | – |
