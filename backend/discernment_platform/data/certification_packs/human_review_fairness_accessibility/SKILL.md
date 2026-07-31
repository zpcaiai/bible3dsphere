---
id: human_review_fairness_accessibility
name: 人工复核、公平性与可访问性
version: 1.0.0
batch: 10
type: production-certification-pack
---

# Controls

- `HFA-001` [C3] 高风险案例达到规定人工复核覆盖率
- `HFA-002` [C3] 用户纠正和申诉可用
- `HFA-003` [C3] 不同信仰背景和宗派不会被错误定性
- `HFA-004` [C2] 语言、认知和残障可访问性有基线测试
- `HFA-005` [C2] Release Board包含独立与用户代表视角

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
