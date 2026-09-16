---
id: counterfactual-explanation-engine
name: 反事实与替代解释引擎
version: 0.3.0
batch: 3
type: reasoning+evidence
requires: virality hypotheses
---

# Purpose

主动寻找与首选解释竞争的模型，防止属灵化、算法化或人格化单因果。

# Trigger

任何高置信爆火、自高、操纵或平台因果结论生成前。

# Inputs

主解释、证据、时间线、对照案例。

# Outputs

替代解释、可区分证据、反事实问题、置信度调整。

# Processing Contract


至少测试：
- 题材时机而非人物本身；
- 外部新闻事件；
- 付费投放；
- 既有粉丝基础；
- 跨平台搬运；
- 批评者放大；
- 数据采样偏差；
- 幸存者偏差；
- 随机推荐；
- 真实社会需要。

问题示例：
“若同样内容由无名账号发布，是否仍会爆火？”


# Prompt Contract

不要为了平衡而制造毫无根据的替代解释；每个替代解释应说明可检验数据。

# Evidence and Uncertainty

输出 confidence_before 与 confidence_after。

# Guardrails

不得使用反事实为真实伤害开脱。

# Failure Handling

没有可区分数据时保留多模型并降低置信度。

# Acceptance Tests

每个高风险结论至少两个替代解释；可指出需要的判别证据。
