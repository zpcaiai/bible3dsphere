---
id: reliability_observability_incident
name: 可靠性、可观测性与事件响应
version: 1.0.0
batch: 10
type: production-certification-pack
---

# Controls

- `ROI-001` [C2] 关键SLI/SLO已定义并监控
- `ROI-002` [C3] Trace贯穿模型、工具、证据和人工复核
- `ROI-003` [C4] Kill switch和回滚演练通过
- `ROI-004` [C3] 事件响应Runbook和责任人已配置
- `ROI-005` [C3] 备份恢复和数据迁移回滚已验证

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
