---
id: narrative-rhetoric-analyzer
name: 内容叙事与修辞分析
version: 0.3.0
batch: 3
type: llm-structured
requires: content-corpus-curator
---

# Purpose

识别内容中的英雄、敌人、危机、救主、身份承诺、情绪激活、证据习惯和行动号召。

# Trigger

语料策展完成后。

# Inputs

代表性内容语料。

# Outputs

主题矩阵、叙事模板、修辞策略、情绪谱、真实性习惯和证据片段。

# Processing Contract


抽取：
- hook
- problem_definition
- hero
- enemy
- victim
- functional_savior
- promised_identity
- action_call
- emotional_activation
- evidence_style
- rhetorical_devices
- omission_patterns

区分偶发修辞与重复模板。


# Prompt Contract

先公平复述，再分析风险。讽刺、角色扮演和幽默须降低字面解释置信度。

# Evidence and Uncertainty

重复模板需跨至少三个独立内容样本，或标记为单例。

# Guardrails

不从强烈修辞直接推断恶意。

# Failure Handling

语境缺失时标记 CONTEXT_MISSING。

# Acceptance Tests

能识别“你失败因为不够狠”中的问题定义和救主；不会把玩笑单例写成稳定价值观。
