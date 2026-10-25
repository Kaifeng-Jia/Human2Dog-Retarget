# 给在本仓库工作的 Claude 的说明

## 项目

Human2Dog 学习式线：冻结 X-Morph 先验 + 只修 Z1 机械臂的交互修正，把 OMOMO 的人-物示范迁移到 B2-Z1。
方法规格：`docs/spec/learned_line_v0.5_zh.md`。几何约定以 `configs/b2z1.yaml` 为准。

## 分工

| 角色 | 谁 | 职责 |
|---|---|---|
| 主设计与主代码（lead） | 云端的 Claude 会话 | 写 `h2d/`、`scripts/`、`configs/`；在 `claude/*` 分支上开 PR；写运行单（GitHub Issue，标签 `run`） |
| 运行与环境（runner） | Ubuntu（RTX 5070）上的 Claude Code | 配环境；按运行单跑；修环境相关问题；回传结果 |
| 审查 | GPT / Codex | 审方法、代码和结果 |
| 决策 | Kevin | 合并 PR、确定方向 |

## 如果你是 Ubuntu 上的 runner，请遵守

1. **只按运行单做事。** 运行单在 GitHub Issues 里（标签 `run`），写明分支、命令、通过标准。不要自行扩展研究内容，也不要改方法或通过标准。
2. **不要直接修改 `claude/*` 分支。** 需要改代码时（路径、依赖、CUDA、明显的 bug），在 `ubuntu/<主题>` 分支上改，开 PR 并说明原因。环境上的经验写进 `docs/setup_ubuntu.md`（同样走 PR）。
3. **回传结果：**
   - 完整输出留在本机的 `outputs/<run_id>/`（不进 git）。
   - 把小文件（`summary.json`、`report.md`、单张不超过 1 MB 的图）复制到 `reports/<run_id>/`，提交到 `ubuntu/reports` 分支并推送。
   - 在对应 Issue 下评论：所用提交号、环境（`nvidia-smi` 摘要、torch 版本、`torch.cuda.is_available()`、X-Morph 提交号）、每项检查是否通过、所有异常和报错原文。
   - 视频、`npz`、`pkl` 等大文件放到 Google Drive 的 `Human2Dog/runs/<run_id>/`，在评论里附链接。
4. **不提交受许可限制的文件**：OMOMO 数据、SMPL-X 模型、X-Morph checkpoint 和第三方仓库（`external/` 已在 `.gitignore` 中）。
5. **结果和运行单不符时**（报错、数值对不上、想改阈值），先在 Issue 里写清楚现象和你的判断，等 lead 或 Kevin 回复，不要自行绕过。

## 如果你是 lead

- 每个运行单写清：分支和提交、完整命令、期望输出、通过标准，以及要回报的环境信息。
- 读取结果：`git fetch origin ubuntu/reports`，并读 Issue 评论（`gh api repos/Kaifeng-Jia/human2dog-retarget/issues/<n>/comments`）。

## 环境

见 `docs/setup_ubuntu.md`。`XMORPH_ROOT` 指向固定提交 `a9f4a7713ac9e593a1e40f77851ba5ba44c92d78` 的 X-Morph。
