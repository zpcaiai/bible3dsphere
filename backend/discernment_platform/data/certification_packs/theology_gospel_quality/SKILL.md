---
id: theology_gospel_quality
name: 神学与福音质量
version: 1.0.0
batch: 10
type: production-certification-pack
---

# Controls

- `TGQ-001` [C4] 完整福音包含基督、十架、复活、恩典和信心
- `TGQ-002` [C4] 称义与成圣清楚区分
- `TGQ-003` [C4] 律法主义、廉价恩典和成功神学红队通过
- `TGQ-004` [C3] D2/D3宗派观点不会作为得救标准
- `TGQ-005` [C4] 福音推进尊重同意且不操纵

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
