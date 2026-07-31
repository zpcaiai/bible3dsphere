---
id: governance_review_panel
name: 治理与复核委员会
version: 0.8.0
batch: 8
type: pastoral-role-pack
---

# Permissions

- `review_governance_case`
- `check_due_process`
- `review_conflicts`
- `record_decision`
- `manage_appeal`
- `order_systemic_remediation`

# Prohibitions

- `use_ai_score_as_verdict`
- `bypass_external_authorities`
- `retaliate`
- `unlimited_data_access`

# Default Scope

- `case-specific-L3`

# Notes

- 成员必须进行利益冲突声明和必要回避。

# Guardrails

- 权限必须与具体目的和用户授权共同满足；
- 角色不自动获得全量档案；
- 所有敏感访问必须审计；
- 不得把AI假设视为事实或纪律证据；
- 涉及利益冲突时必须回避。
