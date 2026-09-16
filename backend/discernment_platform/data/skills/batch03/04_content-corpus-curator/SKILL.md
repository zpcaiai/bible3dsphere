---
id: content-corpus-curator
name: 内容语料策展
version: 0.3.0
batch: 3
type: deterministic+sampling
requires: identity-persona-separator
---

# Purpose

从大量内容中建立时间、题材、表现和平台分布均衡的分析语料，避免只挑争议片段。

# Trigger

有多个内容样本或长时间序列时。

# Inputs

ContentArtifact 列表、时间窗口、采样预算。

# Outputs

核心语料、对照语料、争议语料、商业语料、缺口报告和采样日志。

# Processing Contract


分层采样：
- 爆火前/爆火期/爆火后；
- 高互动/中互动/低互动；
- 原创/转载/直播/广告；
- 正面/中性/争议；
- 不同平台；
- 不同主题。

必须保留选择理由和被排除内容统计。


# Prompt Contract

无。

# Evidence and Uncertainty

抽样不能证明全部内容；报告必须说明覆盖率。

# Guardrails

不得只采样最极端内容制造结论。

# Failure Handling

样本偏斜超过阈值时标记 CORPUS_BIAS。

# Acceptance Tests

采样包含时间与互动层；争议内容占比不能无理由过高；结果可复现。
