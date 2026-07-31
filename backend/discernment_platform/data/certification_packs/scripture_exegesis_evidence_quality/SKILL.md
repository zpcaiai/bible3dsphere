---
id: scripture_exegesis_evidence_quality
name: 圣经、释经与证据质量
version: 1.0.0
batch: 10
type: production-certification-pack
---

# Controls

- `SEE-001` [C3] 主要释经结论包含段落、全书和文体上下文
- `SEE-002` [C3] 原文字义不依赖Strong编号或词根谬误
- `SEE-003` [C4] 所有引文具有来源、版本和locator
- `SEE-004` [C3] RAG生成陈述可追溯到证据图谱
- `SEE-005` [C4] 版权与许可证过滤生效

# Decision Rules

- C4未通过：必须BLOCKED或立即REVOKED；
- C3未通过：不得Pilot或Production；
- C2未通过：不得Production，可在明确限制下Conditional Pilot；
- C1可进入有期限修复计划；
- 每项结论必须有有效证据；
- 证据过期后控制自动回到未评估；
- 人工复核不能覆盖C4技术或安全失败。

# Guardrails

- 不允许用总分掩盖关键阻断；
- 不允许空白人工签名；
- 不允许未经验证的风险接受；
- 不允许证书与实际构建不一致；
- 不允许发布后关闭持续复认证。
