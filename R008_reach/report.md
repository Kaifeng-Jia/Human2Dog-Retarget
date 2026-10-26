# Frozen-body reachability (spec learned v0.6 §7.1)

Run `R008_reach` · code `v0.1.3-8-g80c2a7a` (dirty=False) · 4/4 tasks · reach bound 0.940 m (sampled max 0.939 m) · 15.9 min

| task | layout | registration (psi, residual RMS) | scene body in object [m] | target–shoulder [m] | problem | label | feasible | err max [cm] | angle median / max [°] | arm change max / RMS [°] | speed ratio max |
|---|---|---|---|---|---|---|---|---|---|---|---|
| trashcan_side | contact_fit | 4.0°, 0.29 m | 0.006 | 0.49–1.07 | pos | no_feasible_solution_within_budget | 7 % | 28.8 | 73 / 111 | 188 / 117 | 35.42 |
| trashcan_side | contact_fit | 4.0°, 0.29 m | 0.006 | 0.49–1.07 | pos_dir | no_feasible_solution_within_budget | 0 % | 31.9 | 65 / 104 | – / – | – |
| trashcan_side | contact_fit | 4.0°, 0.29 m | 0.006 | 0.49–1.07 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 71.3 | 50 / 59 | – / – | – |
| trashcan_side | start_anchored | 0.7°, 0.67 m | 0.060 | 0.48–0.67 | pos | no_feasible_solution_within_budget | 22 % | 26.7 | 85 / 139 | 206 / 120 | 49.62 |
| trashcan_side | start_anchored | 0.7°, 0.67 m | 0.060 | 0.48–0.67 | pos_dir | no_feasible_solution_within_budget | 0 % | 31.3 | 77 / 124 | – / – | – |
| trashcan_side | start_anchored | 0.7°, 0.67 m | 0.060 | 0.48–0.67 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 104.6 | 63 / 74 | – / – | – |
| smallbox_top | contact_fit | -24.9°, 0.30 m | 0.041 | 0.61–0.80 | pos | coordinate_or_tool_offset_error | 19 % | 42.7 | 19 / 58 | 204 / 121 | 29.98 |
| smallbox_top | contact_fit | -24.9°, 0.30 m | 0.041 | 0.61–0.80 | pos_dir | coordinate_or_tool_offset_error | 14 % | 6.1 | 15 / 34 | 172 / 87 | 1.87 |
| smallbox_top | contact_fit | -24.9°, 0.30 m | 0.041 | 0.61–0.80 | pos_dir_budget | coordinate_or_tool_offset_error | 0 % | 62.4 | 47 / 58 | – / – | – |
| smallbox_top | start_anchored | 1.5°, 0.81 m | 0.000 | 0.88–1.53 | pos | coordinate_or_tool_offset_error | 0 % | 67.7 | 54 / 70 | – / – | – |
| smallbox_top | start_anchored | 1.5°, 0.81 m | 0.000 | 0.88–1.53 | pos_dir | coordinate_or_tool_offset_error | 0 % | 67.7 | 52 / 68 | – / – | – |
| smallbox_top | start_anchored | 1.5°, 0.81 m | 0.000 | 0.88–1.53 | pos_dir_budget | coordinate_or_tool_offset_error | 0 % | 118.9 | 54 / 64 | – / – | – |
| largebox_top | contact_fit | 4.8°, 0.20 m | 0.071 | 0.45–0.66 | pos | feasible | 100 % | 0.7 | 50 / 71 | 220 / 121 | 30.92 |
| largebox_top | contact_fit | 4.8°, 0.20 m | 0.071 | 0.45–0.66 | pos_dir | feasible | 100 % | 0.5 | 0 / 8 | 179 / 80 | 43.12 |
| largebox_top | contact_fit | 4.8°, 0.20 m | 0.071 | 0.45–0.66 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 39.6 | 38 / 45 | – / – | – |
| largebox_top | start_anchored | 1.2°, 0.62 m | 0.110 | 0.28–0.57 | pos | no_feasible_solution_within_budget | 48 % | 14.2 | 27 / 69 | 188 / 96 | 32.04 |
| largebox_top | start_anchored | 1.2°, 0.62 m | 0.110 | 0.28–0.57 | pos_dir | no_feasible_solution_within_budget | 44 % | 13.2 | 13 / 69 | 172 / 93 | 3.13 |
| largebox_top | start_anchored | 1.2°, 0.62 m | 0.110 | 0.28–0.57 | pos_dir_budget | no_feasible_solution_within_budget | 0 % | 65.9 | 40 / 53 | – / – | – |
| c07_sub7_largebox_001 | contact_fit | 43.4°, 0.32 m | 0.005 | 0.57–0.91 | pos | coordinate_or_tool_offset_error | 48 % | 18.4 | 68 / 115 | 188 / 77 | 37.71 |
| c07_sub7_largebox_001 | contact_fit | 43.4°, 0.32 m | 0.005 | 0.57–0.91 | pos_dir | coordinate_or_tool_offset_error | 0 % | 10.8 | 46 / 96 | – / – | – |
| c07_sub7_largebox_001 | contact_fit | 43.4°, 0.32 m | 0.005 | 0.57–0.91 | pos_dir_budget | coordinate_or_tool_offset_error | 0 % | 62.3 | 48 / 73 | – / – | – |
| c07_sub7_largebox_001 | start_anchored | -0.0°, 1.16 m | 0.159 | 0.39–1.71 | pos | coordinate_or_tool_offset_error | 23 % | 84.0 | 56 / 132 | 186 / 84 | 52.96 |
| c07_sub7_largebox_001 | start_anchored | -0.0°, 1.16 m | 0.159 | 0.39–1.71 | pos_dir | coordinate_or_tool_offset_error | 0 % | 84.0 | 49 / 110 | – / – | – |
| c07_sub7_largebox_001 | start_anchored | -0.0°, 1.16 m | 0.159 | 0.39–1.71 | pos_dir_budget | coordinate_or_tool_offset_error | 0 % | 162.2 | 43 / 72 | – / – | – |
