---
id: small_group_leader
name: 小组长
version: 0.8.0
batch: 8
type: pastoral-role-pack
---

# Permissions

- `view_group_support_summary`
- `prepare_checkin`
- `record_user-approved_note`
- `escalate_concern`

# Prohibitions

- `view_full_history`
- `investigate_abuse`
- `formal_discipline`
- `clinical_assessment`

# Default Scope

- `L0`
- `purpose-bound-L1`

# Notes

- 小组长主要承担关怀、连接和升级，不承担调查和正式治理。

# Guardrails

- 权限必须与具体目的和用户授权共同满足；
- 角色不自动获得全量档案；
- 所有敏感访问必须审计；
- 不得把AI假设视为事实或纪律证据；
- 涉及利益冲突时必须回避。
