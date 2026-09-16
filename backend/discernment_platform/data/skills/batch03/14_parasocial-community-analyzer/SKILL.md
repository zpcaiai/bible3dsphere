---
id: parasocial-community-analyzer
name: 拟社会关系与粉丝共同体分析
version: 0.3.0
batch: 3
type: llm+network
requires: audience and interaction data
---

# Purpose

分析粉丝与公众人物之间的亲密感、身份归属、忠诚测试、边界和共同体规范。

# Trigger

存在粉丝称谓、会员群、直播互动或高依附社群时。

# Inputs

互动样本、社群规则、粉丝语言、创作者回应和商业层级。

# Outputs

亲密机制、归属价值、边界风险、批评处理、共同体果子和替代健康共同体路径。

# Processing Contract


分析：
- perceived_intimacy
- exclusivity
- identity_badges
- loyalty_tests
- access_tiers
- confession_or_disclosure_pressure
- criticism_norms
- mutual_aid
- dependency
- exit_cost


# Prompt Contract

拟社会关系不自动等于不健康；同时识别真实陪伴、教育和互助价值。

# Evidence and Uncertainty

动机推断最高 P2；社群规范可由公开规则和重复互动支持。

# Guardrails

不公开普通粉丝身份；对未成年人提高安全等级。

# Failure Handling

样本不足时只输出观察维度。

# Acceptance Tests

同时输出共同体益处与风险；不将会员制度自动判为控制。
