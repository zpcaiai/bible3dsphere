---
id: product_workflow_completeness
name: 产品与工作流完整性
version: 1.0.0
batch: 10
type: production-certification-pack
---

# Controls

- `PWC-001` [C3] Batch 01–09核心能力均有可调用入口
- `PWC-002` [C3] 所有高风险流程包含明确失败与人工升级状态
- `PWC-003` [C2] 用户可以暂停、纠正和退出长期工作流
- `PWC-004` [C2] 管理端、用户端和复核端关键流程有E2E测试

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
