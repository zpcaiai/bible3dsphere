---
id: privacy_consent_data_rights
name: 隐私、同意与数据权利
version: 1.0.0
batch: 10
type: production-certification-pack
---

# Controls

- `PCD-001` [C4] 敏感数据有目的、分类和最小化
- `PCD-002` [C4] 用户可访问、纠正、导出、撤回和删除
- `PCD-003` [C4] L2/L3共享需要授权或记录的安全/法律依据
- `PCD-004` [C3] 保留和删除策略可执行并有审计
- `PCD-005` [C2] 部署法域有适配器和合格法律复核状态

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
