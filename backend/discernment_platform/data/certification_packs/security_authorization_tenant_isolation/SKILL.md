---
id: security_authorization_tenant_isolation
name: 安全、授权与租户隔离
version: 1.0.0
batch: 10
type: production-certification-pack
---

# Controls

- `SAT-001` [C4] RBAC+ABAC默认拒绝
- `SAT-002` [C4] 跨租户访问测试全部失败关闭
- `SAT-003` [C4] 敏感数据静态和传输加密
- `SAT-004` [C3] Break-glass访问有理由、审计和事后复核
- `SAT-005` [C3] 秘密管理、依赖与供应链扫描通过

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
