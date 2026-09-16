---
id: public-figure-evidence-profiler
name: 公众人物公开证据画像
version: 0.3.0
batch: 3
type: retrieval+structured
requires: viral-case-normalizer
---

# Purpose

建立仅基于公开、相关和必要信息的人物证据画像。

# Trigger

主体包含公众人物、组织或公开账号时。

# Inputs

规范化主体、公开材料、来源元数据。

# Outputs

公开经历、技能证据、历史言论、组织关系、公开披露、证据冲突和覆盖度。

# Processing Contract


1. 优先一手内容和官方披露；
2. 对新闻转载按 independence_group 去重；
3. 记录时间，避免用早期言论代表当前立场；
4. 将事实与评价分开；
5. 生成 coverage map：时间、平台、内容类型。


# Prompt Contract

只能陈述公开材料支持的事实。不得从政治、宗教或消费偏好推导完整人格。

# Evidence and Uncertainty

每一项事实绑定 EvidenceRef；冲突材料并列呈现。

# Guardrails

禁止临床诊断、违法指控和隐藏收入推断。

# Failure Handling

覆盖不足则降低后续分析置信度。

# Acceptance Tests

一手与二手来源可区分；相互转载不虚增证据等级；过时材料有时间标签。
