# 给在本仓库工作的 Claude 的说明

## 项目

Human2Dog：把 OMOMO 的人-物示范迁移到 B2-Z1（Unitree B2 + Z1 机械臂）。本仓库容纳所有线：

- `common`：两条线共用的模块；
- `learned`：学习式线（冻结 X-Morph 先验 + 只修 Z1 机械臂），**当前在做**；
- `fullopt`：全优化线（不用 X-Morph），以后做。

方法规格见 `docs/spec/`（当前为 `docs/spec/learned/v0.5_zh.md`）。几何约定以 `configs/b2z1.yaml` 为准，第三方代码的固定提交以 `configs/external.yaml` 为准。**版本管理规则见 `docs/versioning.md`，所有人都必须遵守。**

## 分工

| 角色 | 谁 | 职责 |
|---|---|---|
| 主设计与主代码（lead） | 云端的 Claude 会话 | 写 `h2d/`、`scripts/`、`configs/`；在 `claude/<线>/<主题>` 分支上开 PR；写运行单（GitHub Issue，标签 `run`） |
| 运行与环境（runner） | Ubuntu（RTX 5070）上的 Claude Code | 配环境；按运行单跑；修环境相关问题；回传结果 |
| 审查 | GPT / Codex | 审方法、代码和结果 |
| 决策 | Kevin | 合并 PR、确定方向 |

## 如果你是 Ubuntu 上的 runner，请遵守

1. **只按运行单做事。** 运行单在 GitHub Issues 里（标签 `run`），写明提交、命令和通过标准。不要自行扩展研究内容，也不要改方法或通过标准。
2. **不要修改别人的分支。** 需要改代码时（路径、依赖、CUDA、明显的 bug），新建 `ubuntu/<线>/<主题>` 分支（例如 `ubuntu/env/cu128`），开 PR 并说明原因。环境上的经验写进 `docs/setup_ubuntu.md`（同样走 PR）。
3. **只在干净的提交上运行。** 运行前 `git status` 必须干净，并 checkout 到运行单指定的提交；第三方仓库必须在 `configs/external.yaml` 指定的提交上。脚本会自动检查，不满足时拒绝运行。不要用 `--allow-dirty` 或 `--allow-external-mismatch` 产出要回报的结果。
4. **回传结果：**
   - 完整输出留在本机的 `outputs/<运行编号>/`（不进 git）。
   - 把小文件（`summary.json`、`report.md`、单张不超过 1 MB 的图）复制到 `reports` 分支的 `<运行编号>/` 目录，提交并推送。提交信息写 `[report] <运行编号> on <代码提交号前 7 位>`。
   - 在对应 Issue 下评论：所用提交号、`summary.json` 里的 `provenance`（环境、X-Morph 提交、是否 dirty）、每项检查是否通过、所有异常和报错原文。
   - 视频、`npz`、`pkl` 等大文件放到 Google Drive 的 `Human2Dog/runs/<运行编号>/`，在评论里附链接。
5. **不提交受许可限制的文件**：OMOMO 数据、SMPL-X 模型、X-Morph checkpoint 和第三方仓库（`external/`、`data/` 已在 `.gitignore` 中）。
6. **结果和运行单不符时**（报错、数值对不上、想改阈值），先在 Issue 里写清楚现象和你的判断，等 lead 或 Kevin 回复，不要自行绕过。

## 如果你是 lead

- 每张运行单写清：提交号、完整命令（含 `--run-id`）、期望输出、通过标准，以及要回报的环境信息。
- 读取结果：`git fetch origin reports`，并读 Issue 评论（`gh api repos/Kaifeng-Jia/Human2Dog-Retarget/issues/<n>/comments`）。
- 合并到 `main` 用 merge commit；里程碑打 annotated tag；更新 `CHANGELOG.md`。

## 环境

见 `docs/setup_ubuntu.md`。
