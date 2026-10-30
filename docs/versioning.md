# 版本管理约定

本仓库容纳整个项目的所有线：公共模块、学习式线、全优化线，以及以后可能加入的 RL。下面的规则保证**报告里的每个数字都能追溯到一次具体的代码提交和运行**。

## 1. 代码按“线”分目录

| 线 | 代码 | 脚本 | 测试 | 方法规格 |
|---|---|---|---|---|
| 公共（两条线共用） | `h2d/common/` | `scripts/common/` | `tests/common/` | 各线规格中的公共部分 |
| 学习式线 | `h2d/learned/` | `scripts/learned/` | `tests/learned/` | `docs/spec/learned/` |
| 全优化线 | `h2d/fullopt/` | `scripts/fullopt/` | `tests/fullopt/` | `docs/spec/fullopt/` |

- 一条线的代码只能依赖 `h2d/common`，不能依赖另一条线的代码，两条线才能独立演进、公平比较。
- 两条线都要用的东西（几何、数据、接触提取、场景注册、评价）放进 `common`。
- 配置：`configs/b2z1.yaml`（机器人、工具、碰撞约定）和 `configs/external.yaml`（第三方代码的固定提交）是全局唯一来源；各线自己的配置放在 `configs/<线>/`。

## 2. 分支

| 分支 | 用途 | 规则 |
|---|---|---|
| `main` | 稳定主干 | 只通过 PR 合并（使用 merge commit，不要 squash，保留提交号），保证合并后 `pytest` 通过 |
| `<谁>/<线>/<主题>` | 开发分支，例如 `claude/learned/prior-wrapper`、`ubuntu/env/cu128` | 一个分支只有一个写入者；完成后开 PR，合并后删除 |
| `reports` | 运行结果日志 | 长期存在，**永不合并进 `main`**；每次运行一个目录 `R###_<主题>/` |

`<谁>` 取 `claude`（云端 lead）、`ubuntu`（Ubuntu runner）、`kevin`、`gpt`；`<线>` 取 `common`、`learned`、`fullopt`、`env`、`docs`。

## 3. 提交信息

开发阶段的提交信息、PR 和 Issue 都用中文（Kevin，2026-10-30），以线作前缀，例如 `[common] 加入场景注册`、`[learned] 交互网格放置身体`、`[env] torch cu128 说明`、`[docs] 规格 v0.6`。此前的英文提交保持原样。代码里的标识符、注释和文档字符串仍用英文。

项目完成后，另建一个整理过的仓库作为最终结果（只放最终方法、复现说明和结果），本仓库保留为开发记录。

## 4. 版本号和标签

- **代码版本**：`vMAJOR.MINOR.PATCH`，写在 `h2d/__init__.py` 和 `CHANGELOG.md` 中。开发期为 `0.x`：每完成一个里程碑升 MINOR；里程碑之间每合并一个 PR 升 PATCH。修改 `configs/external.yaml` 中的固定提交也算版本变更。
- **里程碑标签**（annotated tag，打在 `main` 上，指向产出报告数字的那次提交）：

| 标签 | 内容 | 计划日期 |
|---|---|---|
| `learned-course` | 学习式线课程版：可达性诊断与三种身体布局对比（R017，`docs/results/learned_course_zh.md`）；取代原计划的 m1 / m2 / m3 | 10/30 |
| `spotlight` | spotlight 所用结果 | 12 月初 |
| `final-report` | 期末报告所用结果 | 12/13 |

- **方法规格**：`docs/spec/<线>/v<版本>_zh.md`。一个版本被取代后不再修改，修订时新建文件；当前版本在 `docs/spec/README.md` 中标明。

## 5. 运行与结果

- **运行编号**：`R###_<主题>`，对应一张运行单（GitHub Issue，标签 `run`）。
- **溯源**：每个脚本都通过 `h2d/common/runinfo.py` 在 `summary.json` 的 `provenance` 中记录：提交号、`git describe`、工作区是否有未提交改动、第三方仓库的实际提交及是否与固定提交一致、配置文件哈希、命令行、主机和软件版本。
- **默认拒绝不可追溯的运行**：工作区有未提交改动，或第三方仓库不在固定提交上时，脚本拒绝运行。调试时可以加 `--allow-dirty` / `--allow-external-mismatch`，但这样的结果会被标记，不能写进报告。
- **结果存放**：
  - 完整输出：本机 `outputs/<运行编号>/`（不进 git）；
  - 小文件（`summary.json`、`report.md`、单张不超过 1 MB 的图）：`reports` 分支的 `<运行编号>/` 目录；
  - 大文件（视频、`npz`、`pkl`）：Google Drive `Human2Dog/runs/<运行编号>/`。
- 报告和论文中的数字只能引用：运行在 `main` 的提交（或里程碑标签）上、且 `dirty=false`、第三方提交一致的结果。

## 6. 数据与第三方代码

- 不提交 OMOMO 数据、SMPL-X 模型、X-Morph checkpoint 或第三方仓库（许可原因，`external/`、`data/` 已在 `.gitignore` 中）。
- 用到的数据片段，在运行的 `summary.json` 中记录序列 ID、帧区间和文件哈希。
