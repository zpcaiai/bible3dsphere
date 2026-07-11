# Batch 1 复用-缺口矩阵（身份、多租户、权限、隐私与同意）

> 方法：先审计现有 `mission_bridge_*` 与 `mission_os` 能力，再只实现缺口，避免重复建设。

| Skill | 主题 | 现状 | 复用来源 | 结论 |
|---|---|---|---|---|
| 08 | 多租户组织模型 | ✅ 已有 | `0152_mission_bridge_tenancy`（tenant_memberships / program_memberships）+ `0169_mission_os_organizations`（mission_organization_profiles/relationships/invitations）+ `mission_os/organizations.py` | 复用，无需新建 |
| 09 | 角色与权限矩阵（RBAC） | ✅ 已有 | `0152` `mission_bridge_roles` / `mission_bridge_permissions` / `mission_bridge_role_permissions`（platform_admin…guardian…auditor 等 14 角色）+ `core.tenancy.require_org_permission` | 复用 |
| 10 | PostgreSQL RLS 租户隔离 | ✅ 已有 | 多张表已 `ENABLE ROW LEVEL SECURITY` + `mission_tenant_isolation` 策略（`app.tenant_id`）：organizations、consent、audit、incident、outbox 等 | 复用同一模式；新表沿用 |
| 11 | 敏感字段分级（P0–P4）与字段级授权 | ❌ **缺口** | 仅有 `roles.sensitive_access` 布尔 + 日志/outbox 脱敏，无字段级 P0–P4 注册表与授权 | **本批新建** |
| 12 | 知情同意与撤回 | ✅ 已有 | `0153_mission_bridge_consent_lifecycle` `mission_bridge_consent_records`（granted/revoked_at、consent_type、data_categories、retention_days）| 复用 |
| 13 | 保留/导出/删除/匿名化 | ✅ 已有 | `0153` `mission_bridge_data_requests`（export/delete）+ `mission_bridge_retention_runs`（anonymized/deleted）+ `migrations/README_right_to_erasure.md` | 复用 |
| 14 | 未成年人/监护人/高脆弱群体 | ✅ 已有 | `0152` `mission_bridge_guardian_relationships`（verification_status、permissions、expires_at）| 复用 |
| 15 | 二次认证、敏感导出审批、安全会话 | 🟡 **部分** | `0160_mission_os_audit_lineage` 有 `mission_break_glass_access` + `mission_post_access_reviews`（紧急访问+事后审查）；缺敏感导出审批 + step-up 会话 + 一次性水印令牌 | **本批新建导出审批/step-up** |

## 本批新建（仅填补 Skill 11 与 15 的缺口）

- 迁移 `0186_mission_os_field_classification.sql`：`mission_field_classifications`（P0–P4 注册表）、`mission_field_access_grants`（限时字段级授权）+ RLS。
- 迁移 `0187_mission_os_sensitive_export.sql`：`mission_secure_sessions`（step-up 安全会话）、`mission_sensitive_export_requests`（申请→step-up→独立审批→水印一次性令牌→到期自动删除）+ RLS，含 `CHECK(approver_id<>requester_id)`。
- 领域不变式：`mission_os/classification.py`、`mission_os/sensitive_export.py`（纯 Python、无框架/DB 耦合）。
- API：`routers/mission_field_classification.py`（GET/PUT 分级、POST 授权）、`routers/mission_sensitive_export.py`（申请/step-up/审批/拒绝/下载/撤销）。
- 注册：`main.py` 导入 + init + include_router。
- 测试：`tests/test_mission_field_classification.py`、`tests/test_mission_sensitive_export.py`（`no_db` 纯不变式+契约+迁移文本断言，20 项全过）。
