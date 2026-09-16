---
id: audience-desire-segmenter
name: 受众欲望与处境分群
version: 0.3.0
batch: 3
type: llm+clustering
requires: comments or audience evidence
---

# Purpose

识别不同受众为何被吸引，包括合理需要、社会压力、身份愿望、恐惧和潜在辖制。

# Trigger

有评论样本、粉丝自述、搜索词或受众统计时。

# Inputs

评论样本、互动行为、内容主题、可用人口统计和文化上下文。

# Outputs

AudienceSegment 列表、证据、相互重叠、未知群体和健康替代路径。

# Processing Contract


每个 Segment 必须包含：
- legitimate_needs
- pressures
- attraction_drivers
- identity_aspirations
- possible_fears
- risks
- healthy_alternatives

允许同一用户属于多个 Segment。


# Prompt Contract

禁止把粉丝统一描述为愚昧、贪婪或被洗脑。评论区不等于全部受众。

# Evidence and Uncertainty

受众内心动机最高 P2，除非是明确自述。

# Guardrails

敏感人口属性只能在用户提供或合法公开聚合数据中使用。

# Failure Handling

评论样本偏差大时只输出 tentative segments。

# Acceptance Tests

每个分群有合理需要和健康替代；不把批评者自动视为仇恨群体。
