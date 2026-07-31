---
id: licensed_professional
name: 持证专业人员与外部专家
version: 0.8.0
batch: 8
type: pastoral-role-pack
---

# Permissions

- `receive_referral_summary`
- `professional_assessment`
- `return_minimum_summary`
- `recommend_care`

# Prohibitions

- `access_unrelated_church_data`
- `church_discipline_decision`
- `reshare_without_basis`

# Default Scope

- `purpose-bound-L2`

# Notes

- 系统只验证已登记资质信息，不声称自行判断执业合法性。

# Guardrails

- 权限必须与具体目的和用户授权共同满足；
- 角色不自动获得全量档案；
- 所有敏感访问必须审计；
- 不得把AI假设视为事实或纪律证据；
- 涉及利益冲突时必须回避。
