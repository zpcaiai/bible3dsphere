---
id: virality-trigger-decomposer
name: 爆火触发因素分解
version: 0.3.0
batch: 3
type: causal-hypothesis
requires: multiple upstream analyses
---

# Purpose

把爆火分解为人物能力、内容适配、情绪激活、平台可供性、网络种子、争议、时机和随机性。

# Trigger

人物、内容、平台和受众分析至少部分完成后。

# Inputs

persona、content、platform、audience、metrics、timeline。

# Outputs

因素清单、方向、证据等级、交互作用、未知残差和替代模型。

# Processing Contract


建议因素：
- creator_capability
- persona_legibility
- narrative_fit
- emotional_activation
- format_fit
- platform_affordance
- network_seeding
- controversy_lift
- audience_need_fit
- external_event_timing
- paid_distribution
- randomness

不得把评分当作精确因果贡献率。


# Prompt Contract

输出“支持证据、反证、替代解释、仍未知”。禁止单因果结论。

# Evidence and Uncertainty

没有实验或自然实验时使用 causal_hypothesis，不使用 proven_cause。

# Guardrails

不得把爆火解释为神认可或神审判的直接证据。

# Failure Handling

时间序列缺失则不做 lead-lag 结论。

# Acceptance Tests

至少包含一个随机性或未知项；每个主因有替代解释；不输出虚假精确百分比。
