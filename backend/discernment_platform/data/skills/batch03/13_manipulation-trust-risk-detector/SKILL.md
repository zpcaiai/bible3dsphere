---
id: manipulation-trust-risk-detector
name: 操纵与信任风险检测
version: 0.3.0
batch: 3
type: rules+llm
requires: content and business model
---

# Purpose

检测内容和商业路径中的注意力操纵、虚假稀缺、权威伪装、恐惧营销和脆弱性利用。

# Trigger

存在强转化、医疗/财务/关系承诺或社群控制信号时。

# Inputs

叙事、商业漏斗、披露、用户反馈和公开条款。

# Outputs

风险信号、证据、严重度、合理解释、保护建议和人工复核要求。

# Processing Contract


检测：
- false_scarcity
- guaranteed_outcome
- hidden_sponsorship
- authority_laundering
- shame_conversion
- fear_conversion
- dependency_escalation
- isolation_from_critics
- testimonial_overreach
- sunk_cost_pressure
- boundary_violation
- high_stakes_misinformation

风险不等于违法结论。


# Prompt Contract

使用“风险信号”而非“诈骗”“邪教”等定性，除非有权威结论。

# Evidence and Uncertainty

严重指控必须 P3/P4 或人工审核。

# Guardrails

高风险医疗、法律、财务内容进入专项安全流程。

# Failure Handling

证据不足时输出 review_needed。

# Acceptance Tests

隐藏广告可识别；普通促销不会自动判定操纵；违法标签被阻止。
