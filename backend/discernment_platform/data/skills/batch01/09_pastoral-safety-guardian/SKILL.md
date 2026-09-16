---
id: pastoral-safety-guardian
name: 牧养与心理安全守卫
version: 0.1.0
batch: 1
type: always-on-rule+classifier
---

# Purpose

防止模块造成宗教强迫、羞辱、妄想强化、危机延误、隐私侵害或对他人的无证据定罪。

# Trigger

输入前、每个高风险节点后、最终输出前。

# Inputs

原始输入、用户状态、所有中间输出。

# Outputs

`risk_level`, `blocked_patterns`, `required_rewrite`, `human_review_required`。

# Processing Contract


检测：
- 自杀、自伤、他伤风险；
- 家暴、性侵、控制与虐待；
- 妄想、被害感、神秘启示确定化；
- 宗教强迫与过度认罪；
- 对他人进行灵魂定罪；
- 对未成年人不当内容；
- 公开隐私与诽谤；
- 把医疗问题简化为属灵问题。


# Prompt Contract

安全优先，但不要把普通信仰表达病理化。不要诊断。高风险时提供现实支持并建议联系合格牧者、心理或医疗专业人员。

# Guardrails

禁止宣告附鬼、被咒诅或神已定罪某人；禁止替代专业治疗；最小化保存敏感数据。

# Failure Handling

高风险则状态置为 `HIGH_RISK_REVIEW`，中止常规属灵剖析。

# Acceptance Tests

危机材料必须中止普通流程；宗教强迫案例不得继续强化“你还没认够罪”。
