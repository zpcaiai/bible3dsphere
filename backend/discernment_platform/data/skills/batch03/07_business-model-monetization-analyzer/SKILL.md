---
id: business-model-monetization-analyzer
name: 商业模式与变现分析
version: 0.3.0
batch: 3
type: evidence+inference
requires: content and public evidence
---

# Purpose

识别内容背后的价值交换、收入渠道、转化漏斗、信任使用方式和激励冲突。

# Trigger

存在广告、产品、课程、会员、咨询、带货或品牌合作迹象时。

# Inputs

内容语料、公开披露、产品页面、广告标识、链接关系。

# Outputs

收入渠道候选、转化路径、利益相关方、激励冲突、披露质量和证据等级。

# Processing Contract


识别：
- platform_share
- advertising
- sponsorship
- affiliate
- commerce
- course
- membership
- donation
- consulting
- licensing
- agency
- offline_business
- data_or_lead_generation

区分“存在渠道”与“具体收入规模”。


# Prompt Contract

只分析公开可见的商业机制。不得猜测未披露收入、税务或合同。

# Evidence and Uncertainty

收入渠道可由公开页面支持；金额无披露时不得估算为事实。

# Guardrails

不得把商业化本身视为罪；重点评估披露、诚实、适配性和利用脆弱性的风险。

# Failure Handling

证据不足时输出 monetization_unknown。

# Acceptance Tests

能识别课程漏斗；不会因有商品链接断言诈骗；金额缺失时保持未知。
