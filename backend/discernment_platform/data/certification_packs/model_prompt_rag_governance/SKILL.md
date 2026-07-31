---
id: model_prompt_rag_governance
name: 模型、Prompt与RAG治理
version: 1.0.0
batch: 10
type: production-certification-pack
---

# Controls

- `MPR-001` [C3] 模型、Prompt、Policy和Pack版本固定且可追溯
- `MPR-002` [C4] Prompt Injection和恶意文档注入红队通过
- `MPR-003` [C3] 高风险输出使用结构化Schema和校验
- `MPR-004` [C4] 模型回退和降级不绕过安全门
- `MPR-005` [C3] 无证据时返回不足而非编造

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
