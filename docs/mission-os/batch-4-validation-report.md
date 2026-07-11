# Batch 4 验收报告 — 宣教装备、课程、语言文化与本地实习（Skill 37–49）

范围：Skill 37–49。方法：审计（`mission_bridge_training` 已有 mentor/cohort/facilitator 认证 → 复用 Skill 48；formation/disciple 引擎供课程内容）→ 建缺口领域骨架 → 运行 no_db 测试。

## 1. 现状审计结论

- Skill 48 导师/Cohort：**复用** `0159_mission_bridge_training`（mentor_profiles 含 capacity + safeguarding_trained_at、mentor_assignments 含 participant_consented_at、mentor_supervisions、cohorts/sessions/attendance、facilitator_certifications）。不重建。
- 课程内容：复用 `formation_engine.py` / `disciple_engine.py`。
- Skill 37/43/44/45/46/47/49：正式 Mission OS 模型净新建。

## 2. 每个 Skill 完成度

| Skill | 状态 | 依据 |
|---|---|---|
| 37 个性化装备计划 | ✅ 骨架达标 | `0195` 迁移 + `training.py`（gap→module、hard block 不能仅靠课程解除、habits 需用户确认）+ `mission_training` 路由 |
| 38 圣经宣教神学课程 | 🟡 复用+规划 | 课程内容复用 formation；审核矩阵/实践证据为后续内容轮 |
| 39 教会论/门训/植堂课程 | 🟡 规划 | 同上；植堂能力需真实观察（规则见 Skill 49） |
| 40 世界宗教/跨宗教沟通 | 🟡 规划 | 内容与对话模拟为后续内容轮 |
| 41 处境化/文化人类学 | ✅ 规则达标 | `mission_cultural_observations`（observation/interpretation 分列，无 local_explanation 不得 high confidence，DB CHECK）+ `cultural_observation_confidence` |
| 42 团队/冲突/权力边界课程 | 🟡 规划 | 模拟与举报机制在 Batch 5 团队健康补强 |
| 43 Safeguarding 与转介 | ✅ 骨架达标 | `0197` `mission_safeguarding_training_records`（需人工情景、过期自动停接触，DB CHECK）+ `safeguarding_contact_allowed` |
| 44 语言学习与文化观察 | ✅ 骨架达标 | `0195` `mission_language_plans/assessments`（self/AI/native/authorized 分离、L4/L5 需 native、DB CHECK）+ `can_certify_language_level` |
| 45 职业能力与真实身份 | ✅ 骨架达标 | `mission_professional_verifications`（受监管职业需 verified、过期无效、按国家）+ `assert_no_fake_identity` / `professional_qualification_ok` |
| 46 本地跨文化实习 | ✅ 骨架达标 | `0196` `mission_practicums/placements`（Host+Supervisor+Safeguarding 门禁、allowed/prohibited、拒绝信仰不减服务）+ `assert_can_start_practicum` |
| 47 短期观察 vs 长期实习 | ✅ 骨架达标 | `mission_exposure_programs`（non_objectives 必填 DB CHECK、short≠long）+ `evidence_weight_for_exposure`/`assert_not_overstated` |
| 48 导师/督导/Cohort | ✅ 复用达标 | `mission_bridge_training`（capacity/safeguarding/consent/更换/督导） |
| 49 测验/观察/阶段认证 | ✅ 骨架达标 | `0197` + `certification.py`（knowledge/simulation/real 分离、rubric 拒模糊属灵词、高风险多证据+第二 reviewer、Batch 4 不签发 deployment approval，DB CHECK）+ `mission_certification` 路由 |

## 3. 关键安全/伦理不变式（均有测试，19 项）

- 每个 Readiness Gap 必须映射模块；Hard Block 不能仅靠 course/quiz 解除；habits 需用户确认。
- 语言 self/AI/native/authorized 分离；L4/L5 需 native 或 authorized（DB CHECK）；官方语言≠心灵语言。
- 文化观察 observation 与 interpretation 分列，无 local_explanation 不得 high confidence（DB CHECK）。
- 受监管职业需当前 verified，过期无效，按国家；禁虚假身份。
- 实习需 Host+Supervisor+Safeguarding 才能开始；核心禁止活动始终强制；拒绝信仰活动不减服务。
- 短期观察永不计为长期经验（DB CHECK non_objectives 必填）。
- 认证：quiz-only / simulation-only 不能认证真实能力；rubric 拒「很属灵/有恩膏」等模糊词；高风险需 ≥2 证据类别 + 第二 reviewer（DB CHECK）；观察者≠被观察者；**Batch 4 不签发 deployment approval**（枚举 CHECK 排除）。
- Safeguarding 需人工情景评估，过期自动停止接触权限（DB CHECK）。

## 4. 测试执行结果

```
tests/test_mission_training_certification.py  (19 passed)
# Batch 1+2+3+4 合并：82 passed in 0.87s
```

- 3 个迁移（0195–0197）RLS 计数（7/5/5）、`app.tenant_id` 策略、语言/文化/实习/认证 CHECK 均由测试文本断言校验。
- `main.py` + 2 路由 + 3 领域模块 `py_compile` 通过；路由独立导入通过。

## 5. 已知限制

- 2026-07-11 真实 PostgreSQL smoke 与非 owner RLS 越权测试已通过；工作台已加入装备计划操作面板。
- 本批交付「骨架 + 强不变式 + 迁移 + 代表性 API + 测试」；课程内容体（Skill 38/39/40/42）、完整实习/认证 UI 与对话模拟为后续内容/UI 轮。
- 前端：本批为后端。

## 6. P0/P1/P2

- P0：无。P1：无。
- P2：课程内容体与实习/认证 UI 待后续轮；迁移 DB smoke 依赖 CI 测试库。

## 7. 放行结论

**READY FOR BATCH 5**（装备计划、语言/文化、职业资格、实习门禁与阶段认证不变式均已落地并测试；Batch 4 明确不签发差派批准）。未通过删除测试、降低证据要求、取消人工审核或关闭 RLS 获得通过。
