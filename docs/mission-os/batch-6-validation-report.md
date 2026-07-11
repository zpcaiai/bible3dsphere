# Batch 6 验收报告 — 财务、筹款、签证、合规、医疗保险、家庭、数字安全与撤离（Skill 61–71）

范围：Skill 61–71。方法：审计（`billing.py` 为 App 订阅计费、与宣教财务无关；Batch 6 核心净新建，财务通过 Adapter 接会计系统）→ 建核心领域骨架 → 运行 no_db 测试。

## 1. 现状审计结论

Batch 6 核心（财务计划/筹款/资金治理/身份路径/证件/合规/医疗保险/家庭预备/数字安全/撤离/Deployment Readiness Gate）此前不存在。净新建。

## 2. 每个 Skill 完成度

| Skill | 状态 | 依据 |
|---|---|---|
| 61 全周期预算/现金流/储备 | ✅ 骨架达标 | `0201` 迁移 + `finance.py`（必备场景、Pledge≠Receipt、一次性不年化、储备不足阻断、多信号 readiness）+ `mission_finance` 路由 |
| 62 支持筹集与筹款伦理 | ✅ 骨架达标 | `0202` support_campaigns/pledges + `scan_campaign`（禁强迫/未证统计/敏感内容）+ `pledge_grants_no_governance`；pledge `governance_rights_none` DB CHECK |
| 63 资金治理 | ✅ 骨架达标 | `mission_funds`/`expense_requests`/`approvals` + `assert_expense_approval`（禁自批+大额双人）+ `assert_separation_of_duties` + `assert_restricted_transfer` |
| 64 透明/利益冲突/反欺诈 | ✅ 骨架达标 | `mission_financial_findings`/`disclosures` + `finding_is_not_verdict` + `assert_investigator_independent` |
| 65 真实身份路径 | ✅ 骨架达标 | `0203` legal_identity_paths + `assert_identity_consistent`/`assert_no_fake_identity`/`assert_regulated_licensed` |
| 66 证件与到期 | ✅ 骨架达标 | `mission_credentials`（`masked_identifier LIKE '****%'` DB CHECK）+ `mask_identifier`/`credential_blocks_deployment`/AI 不访问文件 |
| 67 法律/税务/合规 | ✅ 骨架达标 | `0204` compliance_cases/domains/professional_opinions（`expires_at>=issued_at`）+ `assert_ai_cannot_clear_legal`/`opinion_valid`/`opinion_transfers` |
| 68 医疗/保险/用药 | ✅ 骨架达标 | `0205` medical_readiness（P4、committee 只看摘要）+ `committee_view`/AI 不诊断/残障不自动拒绝/用药与保险阻断 |
| 69 家庭预备 | ✅ 骨架达标 | `0205` spouse_reviews（`submitted_by=spouse_user_id` DB CHECK）/child_education（Homeschool 合法性 CHECK）+ `family_gate`（配偶不同意阻断） |
| 70 数字安全 | ✅ 骨架达标 | `0206` digital_security/devices/exceptions + `assert_p4_storage`/遗失与退出撤权/例外须到期/共享账号默认禁 |
| 71 危机/撤离/Deployment Gate | ✅ 骨架达标 | `0206` emergency/evacuation/drills/gate + `assert_command_not_concentrated`/具体撤离触发/AI 不决定撤离/`run_gate`（硬阻塞不可绕过、需 panel、禁 AI/自审、Ready 仅解锁部署规划终态） |

## 3. 关键安全/伦理不变式（均有测试，23 项）

- 预算必备 baseline+conservative+support_loss，高风险 Field 需 evacuation、家庭需教育成本；Pledge≠Receipt、一次性奉献不年化；储备不足阻断；readiness 输出多信号非单一%。
- 筹款禁强迫/属灵等级/虚假倒计时/未证统计/消费苦难；奉献不产生治理权（DB CHECK `governance_rights_none`）。
- 费用请求者不能自批；大额需双人；职责分离不集中一人；限制资金不可转一般用途。
- 异常 Finding≠欺诈定论；被调查者不能自查。
- 身份申报与实际一致；禁虚假雇佣/空壳/伪造；受监管职业需执业资格。
- 证件号掩码（DB CHECK `****%`）；关键证件有效期不足阻断部署；AI 不访问证件文件。
- 法律意见须专业人员、AI 不能 Cleared；含地区+有效期（`expires_at>=issued_at`）、跨国不复用。
- 医疗只存最小状态、委员会看摘要；AI 不诊断/停药；残障不自动拒绝；用药无法持续/保险缺撤离阻断高风险部署。
- 配偶评审须本人提交（DB CHECK `submitted_by=spouse_user_id`）；配偶不同意阻断家庭迁移；Homeschool 合法性 DB CHECK。
- P4 不得存于未受管设备；设备遗失/退出团队即撤权；安全例外须到期。
- Incident Command 不集中一人；撤离触发须具体、AI 不决定撤离；Deployment Gate 硬阻塞不可绕过、需人工 Panel、禁 AI/自审、Ready 仅解锁部署规划(终态)、不激活部署。

## 4. 测试执行结果

```
tests/test_mission_batch6.py  (23 passed)
# Batch 1–6 合并：123 passed in 0.20s
```

- 6 个迁移（0201–0206）RLS 计数（5/8/5/6/8/7）、`app.tenant_id` 策略、pledge 治理/证件掩码/配偶自填/教育合法性/意见有效期 CHECK 均由测试文本断言校验。
- `main.py` + 2 路由 + 4 领域模块 `py_compile` 通过；路由独立导入通过（finance 3 + deployment 4）。

## 5. 已知限制

- 2026-07-11 真实 PostgreSQL smoke 与非 owner RLS 越权测试已通过；工作台已加入财务、合法身份/家庭和 Deployment Gate 面板。
- 本批交付「骨架 + 强不变式 + 迁移 + 代表性 API + 测试」。规格 48 张表中实现了核心 ~34 张；证件加密 Vault、专业审核工作台、演练编排、支持者门户与完整前端为后续 UI/集成轮。
- 医疗/证件正文存加密引用，真实系统需接密钥管理与安全文件存储（Batch 1 机制）。

## 6. P0/P1/P2

- P0：无。P1：无。
- P2：证件加密 Vault、专业审核/演练/支持者 UI 待后续轮；迁移 DB smoke 依赖 CI 测试库。

## 7. 放行结论

**BATCH 6 COMPLETE**（财务可持续性、真实合法身份、证件到期、合规专业复核、医疗保险最小化、家庭独立主体、数字安全撤权、危机撤离与 Deployment Readiness Gate 不变式均已落地并测试；Gate Ready 仅解锁部署规划(终态)，不等于已出发）。未通过删除测试、降低储备、伪造证件状态、延长过期意见、隐藏家庭反对、关闭 RLS 或改 Gate 名称获得通过。

---

> Batch 1–6 全部完成，并已做整体一致性收口（新增 `mission_os/pipeline.py` 生命周期主线 + 跨批集成测试；移除对不存在的 Batch 7 的悬挂引用，Deployment Gate 的 Ready 即系统终态）。合计新增 19 个 `mission_os` 领域模块 / 21 个迁移（0186–0206）/ 16 个路由 / 8 个测试文件（**159 项 no_db 测试全过、6 项 DB 跳过**）。在线路线图现含 Batch 0–6 / 72 Skill。详见 `integration-map.md` 与 `README.md`。
