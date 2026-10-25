---
name: 运行单
about: 交给 Ubuntu runner 执行的一次运行
labels: run
---

## 运行单 R___：<标题>

**分支 / 提交**：

**目的**：

### 步骤
1.

### 期望输出
`outputs/<run_id>/` 里应当包含：

### 通过标准

### 需要回报
- 提交号；`nvidia-smi` 摘要；torch 版本与 `torch.cuda.is_available()`；X-Morph 提交号
- 每项检查是否通过，以及报错原文
- `reports/<run_id>/` 已推送到 `ubuntu/reports` 分支
