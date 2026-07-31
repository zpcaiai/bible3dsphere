---
id: self_user
name: 用户本人
version: 0.8.0
batch: 8
type: pastoral-role-pack
---

# Permissions

- `view_own_data`
- `correct_own_data`
- `export_own_data`
- `grant_access`
- `revoke_access`
- `request_deletion`
- `choose_meeting_focus`

# Prohibitions

- `alter_audit_history`
- `access_other_people_private_data`

# Default Scope

- `L0`
- `L1-own`

# Notes

- 用户拥有最高的自身数据可见权，但安全调查中可能存在依法受限的证人或第三方数据。

# Guardrails

- 权限必须与具体目的和用户授权共同满足；
- 角色不自动获得全量档案；
- 所有敏感访问必须审计；
- 不得把AI假设视为事实或纪律证据；
- 涉及利益冲突时必须回避。
