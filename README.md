# reports branch

Run results log. **Never merged into `main`.** One folder per run: `R###_<topic>/` containing
`summary.json` (with `provenance`: code commit, dirty flag, external commits, environment),
`report.md` and figures ≤ 1 MB. Large files (videos, npz, pkl) go to Google Drive `Human2Dog/runs/<run-id>/`.

Commit message: `[report] <run-id> on <code commit, first 7 chars>`. Rules: `docs/versioning.md` on `main`.

| Run | Ticket | Code | Machine | Result |
|---|---|---|---|---|
| R000_cloud_b01 | — (lead reference run) | `2ed93af` | cloud CPU, MuJoCo 3.3.7 | B01 all checks pass |
| R000b_cloud_b01_mujoco317 | #2 (version check) | `2ed93af` | cloud CPU, MuJoCo 3.17.0 | reproduces R001 exactly (mover distance 1.7328e-9 m) |
