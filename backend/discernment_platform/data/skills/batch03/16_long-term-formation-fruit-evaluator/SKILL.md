---
id: long-term-formation-fruit-evaluator
name: 长期生命塑造果子评估
version: 0.3.0
batch: 3
type: formation-model
requires: content, audience, longitudinal evidence
---

# Purpose

评估长期接触某人物、内容或社群可能如何塑造注意力、欲望、身份、关系与属灵开放性。

# Trigger

用户要求属灵或长期影响分析，且有足够内容或纵向材料时。

# Inputs

内容模板、受众段、互动模式、长期用户自述或行为指标。

# Outputs

FormationFruitProfile：积极果子、风险果子、证据等级、时间尺度、可逆性和护栏。

# Processing Contract


九维：
1. attention
2. truth_habits
3. desire
4. identity
5. emotional_regulation
6. relationships
7. work_and_money
8. body_and_sexuality
9. public_and_spiritual_life

区分：
- observed_fruit
- audience_reported_fruit
- projected_risk


# Prompt Contract

不能仅凭内容推断所有受众结果。说明个人差异、使用强度和现实共同体的调节作用。

# Evidence and Uncertainty

projected_risk 最高 P2；纵向自述与行为数据可提高等级。

# Guardrails

不得制造过度恐惧或把娱乐使用都罪化。

# Failure Handling

没有纵向证据时输出 formation_hypotheses，而非长期结论。

# Acceptance Tests

观察与预测分离；同时识别积极与负面果子；给出时间尺度。
