---
id: identity-persona-separator
name: 人物—人设分离
version: 0.3.0
batch: 3
type: llm+rules
requires: public-figure-evidence-profiler
---

# Purpose

把可验证身份、自我宣称、表演性角色、粉丝象征和商业品牌分离，防止把内容人设等同于真实人格。

# Trigger

人物公开证据画像完成后。

# Inputs

人物画像、内容样本、粉丝与媒体描述。

# Outputs

PersonaProfile、差异点、稳定性、证据等级和未知项。

# Processing Contract


分类：
- verified_identity
- self_claimed_identity
- performed_persona
- audience_symbol
- commercial_brand
- analyst_hypothesis

检测跨场景一致与不一致，但不以不一致自动判定虚伪。


# Prompt Contract

使用“内容中呈现”“受众可能赋予”等措辞。禁止说系统已经识破真实人格。

# Evidence and Uncertainty

所有 analyst_hypothesis 最高 P2，并必须有替代解释。

# Guardrails

不以剪辑片段代表完整人格；不分析非公开家庭成员。

# Failure Handling

样本过少时只输出分层框架，不输出稳定人设结论。

# Acceptance Tests

可区分职业身份与“成功导师”人设；粉丝称号不写成真实身份。
