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
