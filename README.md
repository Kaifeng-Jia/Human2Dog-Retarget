# reports branch

Run results log. **Never merged into `main`.** One folder per run: `R###_<topic>/` containing
`summary.json` (with `provenance`: code commit, dirty flag, external commits, environment),
`report.md` and figures ≤ 1 MB. Large files (videos, npz, pkl) go to Google Drive `Human2Dog/runs/<run-id>/`.

Commit message: `[report] <run-id> on <code commit, first 7 chars>`. Rules: `docs/versioning.md` on `main`.

| Run | Ticket | Code | Machine | Result |
|---|---|---|---|---|
| R000_cloud_b01 | — (lead reference run) | `2ed93af` | cloud CPU, MuJoCo 3.3.7 | B01 all checks pass |
| R000b_cloud_b01_mujoco317 | #2 (version check) | `2ed93af` | cloud CPU, MuJoCo 3.17.0 | reproduces R001 exactly (mover distance 1.7328e-9 m) |
| R001_b01 | #2 | `2ed93af` | Ubuntu RTX 5070, MuJoCo 3.17.0 | B01 all checks pass; matches R000b (A mover distance 1.7328e-9 m differs from R000 only by MuJoCo version) |
| R000c_cloud_b01_mujoco311 | #3 reference | `2c616eb` | cloud CPU, MuJoCo 3.11.0 | B01 pass; mover distance 8.36e-10 m (same as 3.3.7) |
| R000d_cloud_xmorph_smoke_cpu | #3 reference | `2c616eb` | cloud CPU, MuJoCo 3.11.0 | X-Morph smoke pass on 2 clips; arm lag −13 / 6 frames, B2/G1 path 0.66 / 0.83, turn G1 25° vs B2 14° |
| R002_b01_mj311 | #4 | `2c616eb` | Ubuntu RTX 5070, MuJoCo 3.11.0 | B01 all checks pass; max diff vs R000c 8.9e-16 (mover distance 8.36e-10 m) |
| R002_xmorph_smoke | #4 | `2c616eb` | Ubuntu RTX 5070 (cuda:0), MuJoCo 3.11.0 | X-Morph smoke pass on 2 clips; frames and root lag (2 / 0) same as R000d; path / turn rel. diff vs R000d ≤ 5.4e-5; 2.0 s per clip |
| R002_omomo_new_format | #4 | `2c616eb` | Ubuntu, read-only | 4421 files, 17 subjects, 13 objects; each file one float32 tensor [T, 591] (weights_only=True) |
| R003_profile | #6 | `09ef090` | Ubuntu, CPU | pass=false：suitcase 网格底部比记录高约 3 cm，其余检查通过；作为数据概况保留，见 #6 |
| R004_force_profile | #8 | `14a7154` | Ubuntu, CPU, SMPL-H male | **pass=false**: floor_at_zero fails for chair (0.219 m) and box_huge (0.224 m); all 6 objects sit ~0.2 m above z=0 while toes are at ~0.015 m; other checks pass. Only summary.json, checks.png, per_object.csv pushed, awaiting lead |
| R004b_force_profile | #8 | `5c1e1a6` | Ubuntu, CPU, SMPL-H male | pass=true after pelvis-at-smpl_trans fix; chair / box_huge lowest point −0.018 / −0.013 m, mostly slid (0.96 / 0.72); single-hand agreement 0.88; suitcase hand contact found in 0.76 of clips |
| R005_push_candidates | #10 | `01985ab` | Ubuntu, CPU, SMPL-H male | pass=true; 8 candidates (1 tier B, 7 tier C; 11 segments pass all criteria: omomo_new 10, force 1); proxy-to-surface median 0.016 m |
| R007_candidates | #13 | `04e7eab` | Ubuntu, CPU, SMPL-H male | pass=true; 13 candidates (virtual hand: 5 R, 2 L, 6 B; 1 tier A), 37 segments pass all criteria |
| R007_tasks | #13 | `04e7eab` | Ubuntu, CPU | pass=true; 15 tasks (3 confirmed + 12 candidates), 0 errors |
| R007_d0 | #13 | `04e7eab` | Ubuntu RTX 5070 (cuda:0) | **failed**: all 14 OMOMO_new clips stop in GMR load_smplx_file (einsum shape 26 vs 20; exported betas are 10-dim); see #13 |
| R008_d0 | #14 | `80c2a7a` | Ubuntu RTX 5070 (cuda:0) | pass=true; X-Morph prior for all 14 OMOMO_new clips (16 SMPL-X betas); prior Z1 site 0.74–1.24 m vs human hand 0.09–0.62 m in contact |
| R008_reach | #14 | `80c2a7a` | Ubuntu, CPU | pass=true (4/4 tasks, 0 errors); feasible only for largebox_top contact_fit pos / pos_dir; smallbox_top and c07 labelled coordinate_or_tool_offset_error |
| R010_workspace | #16 | `f6899c2` | Ubuntu, CPU | reachable contact z (root 0.5 m): side 0.5–1.3 m, top 0.3–0.8 m (y 0) / 0.2–0.8 m (y 0.2 m); summary.json has no `pass` field |
| R010_candidates | #16 | `f6899c2` | Ubuntu, CPU, SMPL-H male | pass=true; 6 candidates (all tier C; 5 top-face pushes), 12 segments pass all criteria |
| R010_tasks | #16 | `f6899c2` | Ubuntu, CPU | pass=true; 9 tasks (3 confirmed + 6 candidates), 0 errors |
| R010_d0 | #16 | `f6899c2` | Ubuntu RTX 5070 (cuda:0) | pass=true; X-Morph prior for 8 OMOMO_new clips |
| R010_reach | #16 | `f6899c2` | Ubuntu, CPU | pass=true (5/5 tasks, 0 errors); feasible: c04 sub12_largebox_065 (contact_fit pos; start_anchored pos, pos_dir), c05 sub1_suitcase_008 (contact_fit pos) |
| R012_candidates | #18 | `e0b5d6e` | Ubuntu, CPU, SMPL-H male | pass=true; 16 candidates, all labelled grasp (8 pull, 8 push); 60 segments pass all criteria (6 omomo_new push/press among them); OMOMO finger motion 0.0 mm |
| R012_tasks | #18 | `e0b5d6e` | Ubuntu, CPU | pass=true; 19 tasks; confirmed 3 pass, 15 of 16 candidates fail task checks (patch coherence / normal spread) |
| R012_d0 | #18 | `e0b5d6e` | Ubuntu RTX 5070 (cuda:0) | **pass=false**: 18/19 clips pass; sub3_largetable_028 left-wrist convention median 0.0826 m > 0.08 m. d0_chain figure not pushed (JPG q80 still 1.33 MB > 1 MB) |
| R012_reach | #18 | `e0b5d6e` | Ubuntu, CPU | **pass=false**: 0/0 tasks selected (no passing press candidate; all candidates are grasp); see #18 |
| R013_candidates | #19 | `fa9ae09` | Ubuntu, CPU, SMPL-H male | pass=true; 16 candidates (13 pull/grasp, 3 push/press), 67 segments pass all criteria |
| R013_tasks | #19 | `fa9ae09` | Ubuntu, CPU | pass=true; 19 tasks; confirmed 3/3 pass, candidates 5/16 pass task checks |
| R013_d0 | #19 | `fa9ae09` | Ubuntu RTX 5070 (cuda:0) | **pass=false**: 17/18 clips pass; sub1_suitcase_085 X-Morph aborted (exit -6, PyTorch c10 ApproximateClock "getCount is non-monotonic"); see #19 |
| R013_reach | #19 | `fa9ae09` | Ubuntu, CPU | pass=true (3/3 tasks, 0 errors); feasible only reach_track/pos for c14 sub6_largetable_033 and c16 sub5_largetable_030 |
| R014_candidates | #21 | `0872d25` | Ubuntu, CPU, SMPL-H male | pass=true; 6 candidates, all push/press (5 omomo_new, 1 force); 12 segments pass all criteria |
| R014_tasks | #21 | `0872d25` | Ubuntu, CPU | pass=true; 9 tasks, all 9 pass task checks |
| R014_d0 | #21 | `0872d25` | Ubuntu RTX 5070 (cuda:0) | pass=true; 8/8 clips |
| R014_reach | #21 | `0872d25` | Ubuntu, CPU | pass=true (5/5 tasks, 0 errors); feasible pos / pos_dir: mesh 4/4 of 5, reach_track 4/4 of 5, reach_fit 2/1 of 5; pos_dir_budget 0 everywhere; layout videos rendered (mp4 on Drive) |
| R015_candidates | #22 | `1fd1edb` | Ubuntu, CPU, SMPL-H male | pass=true; 12 candidates, all push/press (11 omomo_new, 1 force) |
| R015_tasks | #22 | `1fd1edb` | Ubuntu, CPU | pass=true; 14 tasks, all 14 pass task checks (candidate 5 = confirmed largebox_top) |
| R015_d0 | #22 | `1fd1edb` | Ubuntu RTX 5070 (cuda:0) | **pass=false**: 12/13 clips pass; sub3_largebox_032 left-wrist convention median 0.107 m > 0.10 m; see #22 |
| R015_reach | #22 | `1fd1edb` | Ubuntu, CPU | pass=true (10/10 tasks, 0 errors); feasible pos / pos_dir / pos_dir_budget: mesh 9/7/0, reach_track 9/9/0, reach_fit 6/3/0; layout videos rendered (mp4 on Drive) |
| R016_reach | #23 | `6af8c5f` | Ubuntu, CPU | pass=true (10/10 tasks, 0 errors; tasks and priors from R015); feasible pos / pos_dir / pos_dir_budget: mesh 9/9/0, reach_track 9/9/0, reach_fit 6/3/0; mesh foot slide median 0.68 m/s (R015 0.54); layout videos rendered (mp4 on Drive) |
| R017_reach | #24 | `bff364c` | Ubuntu, CPU (render: RTX 5070, MUJOCO_GL=egl) | pass=true (10/10 tasks, 0 errors; tasks and priors from R015); feasible pos / pos_dir / pos_dir_budget: mesh 9/9/0, reach_track 9/9/0, reach_fit 6/3/0; mesh foot slide median 0.64 m/s (R016 0.68), scene body in object > 0 on 1/10 (R016 4/10); MuJoCo videos for R017 (10) and R016 c04/c08 (mp4 on Drive) |
| R018_videos | #24, #25 | `ad74410` | Ubuntu RTX 5070 (MUJOCO_GL=egl) | render only (R017_reach results, new camera across the human–object line); 10/10 clips with mp4 + png, no errors; mp4 on Drive |
| R020_d0 | #28 | `c0e785b` | Ubuntu RTX 5070 (cuda:0) | pass=true: 13/13 clips (incl. new pelvis_matches_recorded); G1 shift (-0.003, +0.292) m vs R015, world_scale 0.830; B2-Z1 dof diff ≤ 0.076 rad |
| R020_reach | #28 | `c0e785b` | Ubuntu, CPU (render: RTX 5070, MUJOCO_GL=egl) | pass=true (10/10 tasks, 0 errors; 4 layouts); feasible pos / pos_dir / pos_dir_budget: mesh 9/9/0, reach_track 9/9/0, reach_fit 6/3/0 (all labels = R017), start_anchored 3/1/0; MuJoCo videos (mp4 on Drive) |
| R021_cleanup | #29 | `d2758cb` | Ubuntu | tag v0.2.1 → d2758cb pushed; Drive staging verified (734 files, 103,815,492 bytes); deleted outputs/_drive_upload + 27 archived run dirs (1768 files, 232.2 MB); kept R015_candidates, R015_tasks, R020_d0, R020_reach, R001–R005 |
| R022_candidates | #32 | `22536df` | Ubuntu, CPU | pass=true, 12 candidates (from scratch per README); columns 1–9 = R015 |
| R022_tasks | #32 | `22536df` | Ubuntu, CPU | pass=true, 14 tasks; tasks.csv columns 1–10 = R015, task npz max diff 0, meta same |
| R022_d0 | #32 | `22536df` | Ubuntu RTX 5070 (cuda:0) | pass=true, 13/13 clips; G1 and B2-Z1 identical to R020 (diff 0) |
| R022_reach | #32 | `22536df` | Ubuntu, CPU (render: RTX 5070, MUJOCO_GL=egl) | pass=true (10/10 tasks, 4 layouts); report rows identical to R020 (0 lines differ), solutions npz identical; videos 2 x 3 and 1 x 3 (mp4 on Drive) |
| R023_fullopt_m0 | #34 | `40242b6` | Ubuntu, CPU | **pass=false**: 3/5 checks pass; step_hz_in_human_range fails (c12 2.78 Hz > 2.6), leg_length_in_range fails (c02 h_h 0.33 m < 0.70); 10 tasks (= R022_reach), 10 walk segments |
| R024_fullopt_m0 | #35 | `a4adfc1` | Ubuntu, CPU | script pass=true (5/5 checks), segments/δ table = R023; **ticket criterion not met**: c02 h_h 1.01 m (want 0.85–0.95; stance ankle height 0.20/0.17 m vs 0.12 in c04/c09, same bones) |
| R025_fullopt_m0 | #36 | `488a421` | Ubuntu, CPU | pass=true (6/6 checks incl. leg_length_same_per_subject: spread sub12 1.4 cm, sub1 2.2 cm, sub3 0.5 cm); c02 h_h 0.94 m (c04/c09 0.93); segments and δ table = R023/R024 |
| R026_candidates_force | #38 | `8877af2` | Ubuntu, CPU | **pass=false**: enough_candidates 1 < 3 (FORCE only; same single candidate 0630_61-2 as R022); run stopped here per ticket, steps 5–7 not run |
| R026_tasks_force | #38 | `8877af2` | Ubuntu, CPU | pass=true, 4 tasks (0630_61-2 + 3 tool tasks) |
| R026_candidates_omomo | #38 | `8877af2` | Ubuntu, CPU | pass=true, 11 candidates (= R022's 11 OMOMO candidates; only 11 segments pass the funnel, --top 32 not binding) |
| R026_tasks_omomo | #38 | `8877af2` | Ubuntu, CPU | pass=true, 13 tasks (10 = dev clips + 3 tool tasks) |
| R026_fullopt_hoi | #38 | `8877af2` | Ubuntu, CPU | **pass=false**: dev 10, held-out 4 (trashcan_side, smallbox_top, largebox_top, 0630_61-2; 27 duplicate rows skipped); input check fails on dev sub12_largebox_000 (head above ankles 0.77 m, squatting) and held-out sub6_trashcan_003 (not z-up / 0.70 m, bent over); steps 6–7 (M0, compare) not run per ticket |
| R026b_fullopt_hoi | #38 | `112f9a8` | Ubuntu, CPU | pass=true: dev 10, held-out 4 (trashcan_side, smallbox_top, largebox_top, 0630_61-2), all 14 clips pass the input check (most upright 10 % of frames); 27 rows skipped as duplicates (R022_tasks 10, R026_tasks_force 4, R026_tasks_omomo 13) |
| R026b_fullopt_m0 | #38 | `112f9a8` | Ubuntu, CPU | dev 6/6 checks pass, dev = R025 (same walk segments, five columns same, leg diff 0.0); held-out fails no_double_touchdowns (0630_61-2 0.07 s, sub7_smallbox 0.17 s) and feet_alternate (0630_61-2 0.78) — reported, not a run error |
| R027_fullopt_m1 | #40 | `29c4830` | Ubuntu, CPU (cvxpy 1.7.5 + Clarabel); videos EGL | **pass=false** (dev): reached 6/10 < 9 (sub12_largebox_065 2 fr, sub1_largetable_074 1 fr, sub3_largebox_031 2 fr, sub3_largebox_032 3 fr unreached contact frames); targets_agree_with_learned fails on sub1_largetable_073 (1.48 cm); all 10 solved, 0 QP failures, body in object 0.74 cm; held-out reached 2/4; 14 figures and key-frame strips here; mp4 and npz go to Drive runs/R027/ |
| R027_fullopt_m0 | #40 | `29c4830` | Ubuntu, CPU | pass=true (dev only, 6/6 checks); dev identical to R026b (per-clip numbers, walk segments, aggregate and δ table); held-out no_double_touchdowns True (same foot), feet_alternate False (0630_61-2_472); leg length across splits: sub12 1.4 cm, sub1 2.2 cm, sub3 0.5 cm, sub6 0.3 cm, sub7 0.3 cm |
| R028_grasp_candidates | #42 | `04df1ca` | Ubuntu, CPU | pass=true (4/4 checks), grasp selection (configs/fullopt/grasp_selection.yaml) over 4421 OMOMO_new + 398 FORCE files, 6.7 min: 134 passing segments, all pull/grasp (omomo_new/pull/grasp 129, force/pull/grasp 5), 16 ranked candidates |
| R028_fullopt_grasp_hoi | #42 | `04df1ca` | Ubuntu, CPU; sheets EGL | pass=true: grasp clips split by person, dev 50 (people sub1, sub12, sub3, sub5, sub6), held-out 84, 0 skipped, 0 errors, 0 input problems; 10 contact sheets (4 dev, 6 held-out); clips .npz go to Drive runs/R028/clips/ |
| R028_grasp_reach | #42 | `04df1ca` | Ubuntu, CPU | whole-body grasp reach map (data-free): lowest_m {"0": 0.4, "15": 0.3, "30": 0.2, "45": 0.15, "60": 0.15, "90": 0.15}, same as the cloud |
| R027b_fullopt_m1 | #43 | `3ae9f7a` | Ubuntu, CPU (cvxpy 1.7.5 + Clarabel 0.11.1, 1 thread); videos EGL | **pass=false** (dev): reached 8/10 < 9 (sub1_largetable_074 3 fr, sub6_largetable_033 6 fr unreached contact frames, at the push onset); feet_on_floor 3.46 mm > 2 mm (sub6_largetable_033); trunk_within_limits 1.0106 > 1.01 (sub6_largetable_033); all 10 solved, 0 QP failures, body in object 0.11 cm, object under body 0 frames, targets agree with the learned line's; held-out reached 4/4; 14 figures and key-frame strips here; mp4 and npz go to Drive runs/R027b/ |
| R027c_fullopt_m1 | #44 | `170c9e4` | Ubuntu, CPU (cvxpy 1.7.5 + Clarabel 0.11.1, 1 thread); videos EGL | **pass=true** (dev); **pytest 98 passed, 1 failed** (test_pass_one_reaches_a_reachable_push…: frame 1 of the synthetic push stops unconverged, radius below 1e-6); reached 9/10 (sub6_largetable_033 9 contact frames unreached); collision frames 0; sole 1.01 mm; trunk ratio 1.0006; unconverged frames 10 (sub12_largebox_089 1, sub5_largetable_030 1, sub6_largetable_033 8); c01 solved alone vs in the full run: array_equal True, max |Δq| 0.0; held-out reached 4/4, failing body_in_object, object_under_body, targets_agree_with_learned; 14 figures and key-frame strips here; mp4 and npz go to Drive runs/R027c/ |
