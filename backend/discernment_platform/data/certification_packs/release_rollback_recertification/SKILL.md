---
id: release_rollback_recertification
name: 发布、回滚与持续复认证
version: 1.0.0
batch: 10
type: production-certification-pack
---

# Controls

- `RRC-001` [C4] 证书与构建Hash绑定
- `RRC-002` [C3] Pilot和Production范围严格区分
- `RRC-003` [C3] 证书过期和变更触发复认证
- `RRC-004` [C4] C4事件自动挂起或撤销证书
- `RRC-005` [C3] Canary、Feature Flag和回滚策略验证

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
