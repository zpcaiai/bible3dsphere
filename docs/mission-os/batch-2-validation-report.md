# Batch 2 验收报告 — 全球宣教禾场情报系统（Skill 16–27）

范围：Skill 16–27。方法：审计现有能力（仅有轻量 `mission_bridge_discovery`，无正式禾场情报模型）→ 净新建核心领域骨架 → 运行 no_db 测试。

## 1. 现状审计结论

Batch 2 核心（MissionField / 族群-语言-宗教图谱 / Source-Claim-Evidence / Field Assessment）**此前不存在**。`0154_mission_bridge_discovery` 仅有 group_proposals / observed_needs / community_assets 等轻量发现概念，不构成禾场情报系统。故 Batch 2 为净新建。

## 2. 每个 Skill 完成度

| Skill | 状态 | 依据 |
|---|---|---|
| 16 Mission Field 核心模型 | ✅ 骨架达标 | `0188` 迁移（fields/names/geographies/relationships，公开与敏感几何分列）+ `mission_os/field.py`（地理/非地理校验、public DTO 剥离）+ `mission_fields` 路由 |
| 17 族群/语言/宗教知识图谱 | ✅ 骨架达标 | `0189` 迁移（多对多 link 表，宗教 share 范围 CHECK）+ `knowledge_graph.py`（禁单一宗教绑定、禁点值 share、禁个体推断） |
| 18 侨民/人口流动 | 🟡 结构就绪 | `mission_field_relationships` 含 migration_source/destination、diaspora_of；`region_links` 含 diaspora_region/migration_corridor + 人口范围+as_of_date。专属 diaspora 表与路由为后续 UI 轮 |
| 19 圣经/语言资源可及性 | 🟡 规划 | 领域规则（资源存在≠当地使用、手语独立、last_verified）已在路线图；建表与路由为后续轮 |
| 20 当地教会成熟度与领袖缺口 | 🟡 规划 | 同上；本地反馈闭环为后续轮 |
| 21 需要/机会/进入条件/风险 | ✅ 规则达标 | `field.py` 硬阻塞集（no_legal_entry_path / no_local_partner / unmitigated_high_risk 等）；建独立表为后续轮 |
| 22 Source/Snapshot/Claim-Evidence | ✅ 骨架达标 | `0190` 迁移 + `claims.py`（AI 仅 candidate、统计需 as_of、快照不可覆盖）+ `mission_claims`/`mission_sources` 路由 |
| 23 冲突/可信度/数据质量 | ✅ 骨架达标 | `mission_claim_conflicts`（resolved_keep_both 等）+ `resolve_conflict`；冲突不静默覆盖 |
| 24 禾场优先级评分与可解释推荐 | ✅ 骨架达标 | `0191` 迁移（need/evidence/readiness 分列 + hard_blocks）+ `assess_field`（四信号独立、硬阻塞不可被高 Need 抵消）+ `/fields/{id}/assess` |
| 25 中国国内禾场模板 | 🟡 规划 | 模板版本化机制为后续轮 |
| 26 全球/侨民模板 | 🟡 规划 | 同上 |
| 27 地图/比较/研究/报告 | 🟡 规划 | 无障碍列表、公开地图去 P3/P4、报告审批为后续轮 |

## 3. 关键安全/伦理不变式（均有测试）

- 公开 field DTO 不得携带敏感几何/本地伙伴联系人（`public_field_dto` / `assert_public_dto_clean`）。
- 族群不得绑定单一宗教；宗教 share 必须为范围（DB CHECK + `validate_religion_link`）；个体信仰不得由族群标签推断。
- AI 只能创建 `ai_candidate`；`ai_candidate` 不能在无人工证据下升为 `supported`（`can_promote`）。
- 统计类 Claim 必须带 `as_of_date`（DB CHECK + `validate_new_claim`）；来源快照不可覆盖（`snapshot_is_immutable`）。
- Field Assessment 四信号独立；硬阻塞与高风险不可被高 Need 抵消（`assess_field` + 测试 `test_high_need_cannot_override_hard_block`）。

## 4. 测试执行结果

```
tests/test_mission_field_intelligence.py ....................  (20 passed)
# 与 Batch 1 合并：40 passed in 0.09s
```

- 4 个迁移（0188–0191）RLS 计数（4/6/5/3）、`app.tenant_id` 策略、CHECK、回滚注释均由测试文本断言校验。
- `main.py` + 2 路由 + 3 领域模块 `py_compile` 通过；路由独立导入通过（fields 3 + claims/sources 4）。

## 5. 已知限制

- 2026-07-11 真实 PostgreSQL smoke 已通过：空库执行完整迁移，代表表/RLS/policy 通过，非 owner 跨租户读取为 0。
- 本批交付「架构骨架 + 强不变式 + 迁移 + 代表性 API + 测试」。Skill 18/19/20/25/26/27 的专属表、地图/报告 UI 与模板引擎标注为后续 UI 轮，路线图状态相应标注。
- 前端：Mission OS 工作台已提供禾场创建与列表；地图、比较和研究报告仍需继续深化。

## 6. P0/P1/P2

- P0：无。
- P1：无。
- P2：Skill 18/19/20/25/26/27 的完整表与 UI 待后续轮；迁移 DB smoke 依赖 CI 测试库。

## 7. 放行结论

**READY FOR BATCH 3**（核心禾场情报骨架、Claim-Evidence 与四信号评估已落地并测试；资源可及性/教会成熟度/模板/地图 UI 作为增量在后续轮补齐）。未通过删除测试、关闭 RLS 或弱化不变式获得通过。
