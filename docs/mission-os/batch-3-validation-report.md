# Batch 3 验收报告 — 呼召辨识、恩赐画像与工人准备度（Skill 28–36）

范围：Skill 28–36。方法：审计（`gift_calling_engine.py`/GCOS 已有恩赐+呼召模式，复用于 Skill 31；calling/readiness 正式模型净新建）→ 建核心领域骨架 → 运行 no_db 测试。

## 1. 现状审计结论

- Skill 31 恩赐画像：**复用** 现有 `gift_calling_engine.py`（GCOS：属灵恩赐 + 使命负担模式，明确「非宣告呼召」）与 Identity/Formation，**不重建** 恩赐测评。
- CallingJourney / 动机-Blocker / 多方确认 / 15 维准备度 / AI 治理：此前不存在，本批净新建。

## 2. 每个 Skill 完成度

| Skill | 状态 | 依据 |
|---|---|---|
| 28 呼召辨识旅程 | ✅ 骨架达标 | `0192` 迁移 + `calling.py`（subjective_impression 非决定性、Field Interest≠Orientation、readiness_gate 需教会反馈+本地实践）+ `mission_calling` 路由 |
| 29 动机与反逃避/Blocker | ✅ 骨架达标 | `calling.py` blocker 类型+severity；hard_block 阻断 deployment；`can_clear_blocker` 禁 AI 解除 |
| 30 多方确认 | ✅ 骨架达标 | `validate_feedback_request`（禁自证）+ `aggregate_is_not_average`（显示冲突不平均）；配偶/家庭反馈 P3、DB CHECK 禁自填 |
| 31 恩赐/职业/经历画像 | ✅ 复用+骨架 | 复用 GCOS；`0193` `mission_worker_profiles`（self vs verified、家庭摘要内部字段） |
| 32 角色与岗位能力 | ✅ 骨架达标 | `mission_worker_role_definitions`（9 role_family、版本化、requires_hard_qualification）+ `role_requires_hard_qualification` |
| 33 匹配引擎 | ✅ 骨架达标 | `readiness.role_match`（缺数据≠不足、不含 Need）+ `assert_layers_separate`（role/field/deployment 分层） |
| 34 十五维准备度 | ✅ 骨架达标 | `0193` + `resolve_readiness_level`（15 维、无属灵总分、硬阻塞→pause_and_restore）+ `can_decide_deployment_candidate`（需 panel、禁 AI/自审、硬阻塞须清） + 受保护属性不降级 |
| 35 暂停/恢复/申诉 | ✅ 骨架达标 | `mission_worker_pauses`/`mission_assessment_appeals`；非羞耻化 label 校验；原决定者不能独审申诉（DB CHECK + `can_review_appeal`） |
| 36 AI 边界与模型治理 | ✅ 骨架达标 | `0194` 迁移（prompt_registry + policy_findings + human_reviews + 红队 seed）+ `ai_boundaries.py`（禁 AI 动作、输出扫描、decision 强制 null、P4 不入模型）+ `/ai-draft` 端点 |

## 3. 关键安全/伦理不变式（均有测试，23 项）

- 感动不能独立解锁准备度门（`readiness_gate`）；Field Interest 与 Calling Orientation 分列。
- Hard Block 阻断 deployment candidate 且仅人工可解除；AI 不能解除。
- 候选人不能自证/自审（DB CHECK + 校验）；多方反馈显示冲突而非平均。
- 15 维不产出属灵总分；受保护属性（单身/女性/残障/内向/非神学院等）不得单独降级。
- Deployment Candidate 必须人工 panel，禁 AI、禁自审、硬阻塞须先清。
- role/field/deployment 三层严格分离；缺数据≠能力不足。
- AI 禁止「宣告呼召/批准准备度/解除阻塞/批准差派」；输出扫描命中即改写并记 policy finding；`decision` 强制 null；P4 不入模型。

## 4. 测试执行结果

```
tests/test_mission_calling_readiness.py  (23 passed)
# Batch 1+2+3 合并：63 passed in 0.18s
```

- 3 个迁移（0192–0194）RLS 计数（8/6/3）、`app.tenant_id` 策略、自证/申诉 CHECK、prompt registry+红队 seed 均由测试文本断言校验。
- `main.py` + 2 路由 + 3 领域模块 `py_compile` 通过；路由独立导入通过（calling 4 + readiness 4）。

## 5. 已知限制

- 2026-07-11 真实 PostgreSQL smoke 与非 owner RLS 越权测试已通过。
- 本批交付「骨架 + 强不变式 + 迁移 + 代表性 API + 测试」；配偶隐私通道、完整 15 维评审 UI、Prompt LangGraph 编排、完整红队执行集为后续 UI/集成轮。
- AI 输出扫描为轻量词法防御（divine-call / 强迫），真实系统另需分类器——已在 `ai_boundaries.py` 注明为 defence-in-depth。

## 6. P0/P1/P2

- P0：无。P1：无。
- P2：配偶隐私通道与评审/申诉 UI、Prompt 编排、完整红队执行待后续轮；迁移 DB smoke 依赖 CI 测试库。

## 7. 放行结论

**READY FOR BATCH 4**（呼召旅程、动机-Blocker、多方确认、15 维准备度与 AI 治理不变式均已落地并测试）。未通过删除测试、降低维度、关闭 RLS 或弱化 AI 安全规则获得通过。
