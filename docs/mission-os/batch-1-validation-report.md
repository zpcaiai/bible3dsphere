# Batch 1 验收报告 — 身份、多租户、权限、隐私与同意

范围：Skill 08–15。方法：审计现有能力 → 只补齐缺口 → 运行可用测试。

## 1. 每个 Skill 完成度

| Skill | 状态 | 依据 |
|---|---|---|
| 08 多租户组织模型 | ✅ 复用达标 | `mission_organization_profiles` + `mission_bridge_tenant_memberships`；`mission_os/organizations.py` 不变式测试通过 |
| 09 角色与权限矩阵 | ✅ 复用达标 | `mission_bridge_roles/permissions/role_permissions`；后端 `require_org_permission` 强制校验 |
| 10 RLS 租户隔离 | ✅ 复用达标 | 现有表 + 本批 4 张新表均 `ENABLE ROW LEVEL SECURITY` + `app.tenant_id` 策略 |
| 11 字段分级 P0–P4 与字段级授权 | ✅ 新建达标 | `0186` 迁移 + `classification.py` + 路由；10 项测试通过 |
| 12 知情同意与撤回 | ✅ 复用达标 | `mission_bridge_consent_records`（granted/revoked_at） |
| 13 保留/导出/删除/匿名化 | ✅ 复用达标 | `mission_bridge_data_requests` + `mission_bridge_retention_runs` |
| 14 未成年人/监护人 | ✅ 复用达标 | `mission_bridge_guardian_relationships`（verification/expiry） |
| 15 step-up/敏感导出审批/安全会话 | ✅ 新建达标 | `0187` 迁移 + `sensitive_export.py` + 路由；10 项测试通过；紧急访问复用现有 break-glass |

## 2. 关键安全不变式（均有测试）

- 公开/研究 DTO 不得携带 P3/P4（`assert_dto_safe`）。
- 通用 AI 模型不得接收 P3/P4（`ai_input_allowed`）；服务账号不得被授予 P3/P4 字段级授权（路由 403）。
- 字段级授权限时、可撤销、失效即 fail-closed（`FieldAccessGrant.is_active`）。
- 敏感导出：申请人 ≠ 审批人（DB CHECK + `can_approve`）；审批需 15 分钟内的 step-up；下载令牌高熵、仅哈希入库、一次性、带水印、短时到期；越权/过期/撤销一律 fail-closed。
- 审计不记录令牌原文、不记录敏感字段名（复用 `mission_os.audit` 的 `FORBIDDEN_FIELD_NAMES`）。

## 3. 测试执行结果

```
tests/test_mission_field_classification.py .......... (10)
tests/test_mission_sensitive_export.py    .......... (10)
20 passed in 0.07s
```

- 迁移 `0186`/`0187`：tenant_id + RLS(每文件 2 张表) + 回滚注释 + 索引，均由测试文本断言校验。
- `main.py` / 两个路由 / 两个领域模块：`py_compile` 通过；路由独立导入通过（分级 3 路由 + 导出 6 路由）。

## 4. 已知限制（环境相关，非本批代码问题）

- 沙箱无 PostgreSQL：迁移的实际 apply/rollback smoke 未在此环境运行，需在带测试库的 CI 执行 `run_migrations`。RLS 越权的真实 DB 测试同理需测试库。
- 沙箱缺 `httpx2`/`pytest-asyncio`：仓库既有 5 个无关测试文件（test_security、test_speech_router、test_batch7_13_backend、test_holy_life_api、test_community_heatmap_resilience）collection 报错——为环境依赖缺失，与本批改动无关。
- 前端：本批为后端能力，未新增前端页面（Skill 11/15 的管理界面可在 Batch 后续或专门 UI 轮补齐）。

## 5. P0/P1/P2 问题

- P0：无。
- P1：无。
- P2：Skill 11/15 尚无前端管理页；迁移 DB smoke 依赖 CI 测试库。

## 6. 放行结论

**READY FOR BATCH 2**（条件：在带测试库的 CI 补跑迁移 smoke 与 RLS 越权 DB 测试）。

未通过删除测试、关闭 RLS、弱化权限或降低敏感级别来获得通过。
