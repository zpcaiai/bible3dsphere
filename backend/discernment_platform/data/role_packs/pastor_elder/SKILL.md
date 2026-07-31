---
id: pastor_elder
name: 牧者与长老
version: 0.8.0
batch: 8
type: pastoral-role-pack
---

# Permissions

- `pastoral_review`
- `doctrine_review`
- `meeting_prep`
- `approve_team_access`
- `refer_professional`
- `initiate_governance_intake`

# Prohibitions

- `automatic_discipline_from_ai`
- `ignore_conflict_of_interest`
- `withhold_user_correction`

# Default Scope

- `L0`
- `authorized-L1`
- `limited-L2`

# Notes

- 对L2访问必须有具体目的，并优先转介具资质人员。

# Guardrails

- 权限必须与具体目的和用户授权共同满足；
- 角色不自动获得全量档案；
- 所有敏感访问必须审计；
- 不得把AI假设视为事实或纪律证据；
- 涉及利益冲突时必须回避。
