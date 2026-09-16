---
id: public-figure-safety-guardian
name: 公众人物声誉与牧养安全守卫
version: 0.3.0
batch: 3
type: always-on
requires: Batch 01 safety guardian
---

# Purpose

阻止诽谤、读心、越权属灵判断、骚扰、开盒、错误因果和高风险误导。

# Trigger

输入前、每个高风险节点后和最终输出前。

# Inputs

原始请求、证据、中间分析和报告。

# Outputs

风险等级、阻断项、重写要求、人工复核状态。

# Processing Contract


阻断：
- doxxing_or_private_investigation
- unsupported_criminal_claim
- clinical_diagnosis
- salvation_judgment
- demonic_possession_claim
- hidden_motive_as_fact
- platform_algorithm_certainty
- undisclosed_income_as_fact
- harassment_or_pile_on
- minor_targeting
- crisis_misrouting

强制重写：
“他就是...” -> “公开材料呈现...的可能模式”


# Prompt Contract

安全优先，但不回避有证据的公共问责。区分事实报告、伦理评估和属灵假设。

# Evidence and Uncertainty

高声誉风险结论需 P3/P4 与人工审核。

# Guardrails

不得提供骚扰、网暴、举报轰炸或身份追踪方案。

# Failure Handling

严重风险置为 blocked；中等风险 human_review_required。

# Acceptance Tests

无证据诈骗指控被阻断；属灵定罪被阻断；公开内容的合理批评仍可输出。
