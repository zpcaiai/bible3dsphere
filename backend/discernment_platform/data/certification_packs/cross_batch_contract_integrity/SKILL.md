---
id: cross_batch_contract_integrity
name: 跨Batch合同完整性
version: 1.0.0
batch: 10
type: production-certification-pack
---

# Controls

- `CBC-001` [C3] Batch依赖版本可解析且无循环依赖
- `CBC-002` [C3] 相邻Batch输入输出Schema兼容
- `CBC-003` [C4] 安全与同意状态跨Batch不丢失
- `CBC-004` [C2] Evidence和Trace ID可端到端关联

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
