# Batch 5 验收报告 — 差派教会、机构、团队、本地伙伴与正式差派（Skill 50–60）

范围：Skill 50–60。方法：审计（org 模型已覆盖教会/差会/团队/资助方 + sending/receiving 关系需 local_leadership 决策权 → 复用 Skill 51）→ 建缺口领域骨架 → 运行 no_db 测试。

## 1. 现状审计结论

- Skill 51 机构能力：**复用** `mission_os/organizations.py` + `0169`（ORGANIZATION_KINDS 含 church/mission_agency/receiving_church/team/funding_partner；sending/receiving 关系强制 approvals+local_leadership 决策权）。
- 教会确认多人审核 / 候选人申请 / 委员会 quorum+CoI+投票+决定 / 团队+契约+健康+投诉 / 伙伴+尽调+协议 / 支持+代祷：净新建。

## 2. 每个 Skill 完成度

| Skill | 状态 | 依据 |
|---|---|---|
| 50 差派教会与教会确认 | ✅ 骨架达标 | `0198` + `sending.py`（≥2 非家属 reviewer、观察期、支持≠差派）+ `mission_sending` 路由 |
| 51 宣教/接收机构能力 | ✅ 复用达标 | `organizations.py` + `0169` org profiles/relationships |
| 52 候选人申请与完整性 | ✅ 骨架达标 | `mission_candidate_applications`/`_sections` + `assert_can_submit`（过期 Readiness/缺伙伴阻断、核心变更→新版本） |
| 53 多方审批与委员会 | ✅ 骨架达标 | `0198` committees/members/meetings/votes/decisions + `assert_quorum`/`eligible_voters`（候选人+AI+CoI 排除）/`assert_can_approve`（配偶/伙伴反对阻断）/条件批准需 owner+deadline/批准仅解锁 Batch 6 |
| 54 团队组建与生命周期 | ✅ 骨架达标 | `0199` teams/memberships + `assert_membership_approval`（禁自批）/`assert_spouse_not_auto_member`/退出关闭访问 |
| 55 团队能力与容量 | ✅ 骨架达标 | `mission_team_role_slots` + `detect_single_point_of_failure`（安全关键单点）/`team_capacity_hours`（含语言/家庭/休息）/高 Need 不绕过缺口 |
| 56 团队契约 | ✅ 骨架达标 | `mission_team_covenants` + `validate_covenant`（禁绝对服从/禁退出，必含本地伙伴权利/申诉/退出） |
| 57 团队健康与投诉 | ✅ 骨架达标 | `mission_team_complaints`（被指控者≠调查者 DB CHECK）+ `critical_health_blocks_sending`/匿名阈值 |
| 58 本地伙伴与尽调 | ✅ 骨架达标 | `0200` local_partner_profiles/due_diligence + `assert_can_approve_partner`（需双向评估）/伙伴否决阻断/资助方无控制权 |
| 59 合作协议与决策权 | ✅ 骨架达标 | `mission_partnership_agreements`/`_data_terms` + `assert_agreement_complete`（须退出计划+本地决策权）/Safeguarding 不可被资助方否决/数据访问需协议未过期+个人同意 |
| 60 代祷与支持网络 | ✅ 骨架达标 | `mission_support_networks`/`prayer_updates`（P0–P2 CHECK）+ `assert_update_clean`（禁敏感位置/联系人）/危机暂停预定通讯/资助方无治理权 |

## 3. 关键安全/伦理不变式（均有测试，18 项）

- 单一牧者不能独立完成教会确认（≥2 非家属 reviewer + 观察期）。
- 申请不能绕过完整性；过期 Readiness、缺当地伙伴阻断进入委员会；核心字段变更→新版本。
- 委员会需 quorum；候选人、AI、利益冲突成员不计入合格投票；配偶/当地伙伴反对阻断批准；条件批准须 owner+deadline；**批准仅解锁 Batch 6，非"立即出发"**。
- 团队领袖不能自批入队；配偶不自动成为成员；退出关闭访问。
- 安全关键能力单点故障可识别；容量含语言/家庭/休息；高 Need 不绕过关键缺口。
- 契约禁绝对服从/禁退出，必含本地伙伴权利/申诉/退出。
- 被指控者不能调查针对自己的投诉（DB CHECK）；Critical 团队健康阻断差派。
- 伙伴需双向评估才能长期批准；资助方无 decide/veto；Safeguarding 不可被资助方否决；数据共享需协议未过期+个人同意；协议须含退出计划+本地决策权。
- 代祷更新不得含 P3/P4（位置/联系人，DB CHECK P0–P2）；危机暂停预定通讯；资助方无治理权。

## 4. 测试执行结果

```
tests/test_mission_sending_partnership.py  (18 passed)
# Batch 1+2+3+4+5 合并：100 passed in 0.15s
```

- 3 个迁移（0198–0200）RLS 计数（9/6/6）、`app.tenant_id` 策略、投诉/批准解锁/代祷敏感级 CHECK 均由测试文本断言校验。
- `main.py` + 2 路由 + 3 领域模块 `py_compile` 通过；路由独立导入通过（sending 3 + teams/partners/support 4）。

## 5. 已知限制

- 2026-07-11 真实 PostgreSQL smoke 与非 owner RLS 越权测试已通过；工作台已加入差派申请、团队与本地伙伴面板。
- 本批交付「骨架 + 强不变式 + 迁移 + 代表性 API + 测试」；委员会会议编排、团队健康匿名聚合、协议签署 Step-up、代祷发布审批 UI 为后续 UI/集成轮。
- 前端：本批为后端。

## 6. P0/P1/P2

- P0：无。P1：无。
- P2：委员会/团队健康/协议/代祷 UI 与签署编排待后续轮；迁移 DB smoke 依赖 CI 测试库。

## 7. 放行结论

**BATCH 5 COMPLETE**（差派治理不变式：多人教会确认、委员会 quorum+CoI、配偶/伙伴否决、团队单点故障、契约禁操控条款、伙伴双向评估、资助方无控制、代祷去敏感——均已落地并测试；Batch 5 批准仅解锁 Batch 6，不等于出发）。未通过删除测试、降低 quorum、取消伙伴否决、隐藏配偶意见或关闭 RLS 获得通过。

---

> Batch 1–5 全部完成。合计新增 14 个 `mission_os` 领域模块 / 15 个迁移（0186–0200）/ 12 个路由 / 6 个测试文件（100 项 no_db 测试全过）。完整清单见 `docs/mission-os/roadmap.md` 与各批验收报告。
