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
| R012_candidates | #18 | `e0b5d6e` | Ubuntu, CPU, SMPL-H male | pass=true; 16 candidates, all labelled grasp (9 pull, 7 push); 60 segments pass all criteria (6 omomo_new push/press among them); OMOMO finger motion 0.0 mm |
| R012_tasks | #18 | `e0b5d6e` | Ubuntu, CPU | pass=true; 19 tasks; confirmed 3 pass, 15 of 16 candidates fail task checks (patch coherence / normal spread) |
| R012_d0 | #18 | `e0b5d6e` | Ubuntu RTX 5070 (cuda:0) | **pass=false**: 18/19 clips pass; sub3_largetable_028 left-wrist convention median 0.0826 m > 0.08 m. d0_chain figure not pushed (JPG q80 still 1.33 MB > 1 MB) |
| R012_reach | #18 | `e0b5d6e` | Ubuntu, CPU | **pass=false**: 0/0 tasks selected (no passing press candidate; all candidates are grasp); see #18 |
