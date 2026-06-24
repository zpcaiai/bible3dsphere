# Worldview Formation OS — 实现说明 (Kingdom Lens OS)

> 在 `bible3dsphere/backend`（Python / FastAPI）上实现，复用既有引擎，迁移续编自 `0070`。
> 全部 10 个 Agent 已落地；闭环 = 危机守卫 → 诊断 → 偶像 → 真理映射 → 叙事重写 →
> 专项领域（护教/文化/职业/苦难）→ 决策 → 操练 → 复盘快照。
> 配套回归测试 `backend/tests/test_worldview_os.py` —— **15 个用例全部通过**。

## 1. 新增引擎（10）

| 文件 | 对应 Agent | 说明 |
|---|---|---|
| `worldview_orchestrator.py` | 编排层 | **crisis-first 守卫** + 闭环管线；high/imminent 跳过一切神学分析 |
| `worldview_diagnoser_engine.py` | 1 诊断 | 12 领域检测 + 底层信念抽取 + 0–100 打分 + 画像 |
| `idolatry_engine.py`（扩展）| 2 偶像 | 7 → **13** 类（+knowledge/technology/self_realization/national_political/victimhood/power）|
| `truth_mapper_engine.py` | 3 真理映射 | 谎言→圣经真理→福音重构→经文→圣经人物→操练 |
| `narrative_engine.py` | 4 叙事重写 | 7 旧叙事模板 → 福音新叙事 + 操练计划 |
| `apologetics_engine.py` | 5 护教学 | 预设检测 + 世俗/圣经框定（AI/科学/政治/宗教/经济）|
| `cultural_engine.py` | 6 文化分辨 | 10 时代精神 + 假应许/假要求 + 反文化操练 |
| `vocation_worldview_engine.py` | 7 职业使命 | 工作/金钱/成功观 + 偶像/伦理风险/国度机会 |
| `suffering_engine.py` | 8 苦难神学 | **先危机分级**；哀歌祷告模板 + 圣经人物推荐 |
| `decision_formation_engine.py` | 9 决策塑造 | 10 维省察 + `counselNeeded` + 下一步忠心行动 |
| `formation_practice_engine.py` | 10 操练 | 1/3/7/30/90 天计划 + 安全降级（危机/羞耻/枯竭）|

## 2. 新增路由（2，前缀 `/api/worldview`）

`routers/worldview.py`（核心闭环）：`POST /diagnose`、`/truth/map`、`/narrative/rewrite`、
`/decision/discern`、`/practice/plan`、`/practice/tasks/{id}/complete`、`/metrics/snapshot`、
`POST /guardians`、`GET /profile /assessments /metrics /guardians /meta`。

`routers/worldview_lenses.py`（专项透镜）：`POST /apologetics/ask`、`/culture/discern`、
`/vocation/analyze`、`/suffering/analyze`、`GET /lenses/meta`。

均已在 `main.py` 注册（import + init + include_router 三处），键以 `email` 为准。

## 3. 新增迁移（0070–0075，幂等，开机自动应用）

- `0070_worldview_core` — 9 张 `worldview_*` 表 + 12 领域 / 6 问题种子
- `0071_worldview_truth_narrative` — `distorted_beliefs` `biblical_truth_maps` `narrative_rewrites`
- `0072_worldview_lenses` — `apologetics_cases` `cultural_discernment_cases` `vocation_worldview_cases`
- `0073_worldview_suffering` — `crisis_risk_assessments` `suffering_cases` `user_consents`
- `0090_worldview_decision_formation` — `decision_cases` `formation_practice_library`(种子) `formation_plans` `formation_tasks` `formation_task_logs`
- `0091_worldview_governance` — `community_guardians` `guardian_alerts` `agent_events`

> 注：decision/governance 两个迁移从 0074/0075 **改号为 0090/0091**，以避让团队同期新增的
> `0074_agent_runs_observability` … `0079_advanced_batch_phase2_seed` 等迁移（版本号唯一化）。
> `0073_worldview_suffering` 保留——团队的 `0078_suffering_care` 以 `ALTER TABLE suffering_cases ADD COLUMN`
> 在其之上扩展，二者互补，不冲突。

共 **27 张新表**。`agent_runs` `review_logs` `community_feedback`（已存在）直接复用；
`idol_patterns≡attachment_patterns`、`bible_person_mappings≡biblical_characters`（接线于 `/truth/map`）。

## 4. 安全（务必保留）

- 所有 `diagnose` / `suffering` 入口先调 `crisis_engine.triage()`；`orange/red` 或需人工升级时
  **跳过神学分析**，转 `suffering_theology` 安全路由，并草拟 `guardian_alerts`(drafted)。
- 苦难高危：不输出 `sufferingTypes`、`shouldCreateFormationPlan=False`、`shouldNotifyCrisisSystem=True`。
- 操练：危机/羞耻/枯竭用户自动降级为温和陪伴（gentle），不发高强度计划。
- 偶像/信念输出保持非定罪措辞，与既有 `idolatry_engine` 一致。

## 5. 运行测试

```bash
cd backend
../.venv/bin/python -m pytest tests/test_worldview_os.py -m no_db
# 沙箱无完整依赖时：python3 -m pytest tests/test_worldview_os.py --noconftest -o addopts=""
```

## 6. OpenAI 语义增强层（已接入）

确定性引擎之上叠加了**可选的 OpenAI 语义润色**，统一入口 `worldview_llm.py`：

- **委托既有 `llm_provider`**（OpenAI / Gemini / DeepSeek / Anthropic 兼容 + `MockLLMProvider` +
  agent-run 日志），与 `suffering_engine` 共用同一套配置（`settings.llm_*` / `OPENAI_*` / `AGENT_MODE`）。
- **开关**：请求体 `use_ai`（缺省时按 `worldview_llm.available()` 自动决定——配了真实 key 即默认开启）。
  未配置（`AGENT_MODE!=real` 或无 key）→ 走 `MockLLMProvider` / 返回 None → **纯确定性输出**。
- **两档增强**：
  - **结构化（schema 校验）** — `diagnoser` → `WorldviewAgentOutput`、`truth_mapper` → `DiagnosisAgentOutput`，
    经 `worldview_llm.generate_structured()` → `llm_provider.generate_json()`。AI 产出**结构化内容**
    （信念 findings、扭曲、福音真理、severity 等），按序映射进既有输出契约；离线/未配置 → 自动回退
    prose 润色 → 再回退确定性。
  - **prose 润色** — `narrative`(`newNarrative`/`gospelTruth`)、`apologetics`(`biblicalFraming`/`apologeticsResponse`)、
    `cultural`(`biblicalDiscernment`)、`vocation`(`biblicalVocationFrame`)、`decision`(`discernmentSummary`/`nextFaithfulStep`)。
- **经文 canonical-first**：结构化模式下，AI 的 `scripture_anchors` 仅**并入**确定性 canonical 经文之后（去重、不覆盖、不前置）；
  圣经人物、教义标签、0–100 评分、危机判定**永不**由 AI 产生。
- **铁律**：经文引用、教义标签、评分、危机判定**绝不**交给 LLM（`merge_fields` 白名单合并）；
  **苦难高危分支绝不调用 LLM**。`suffering_engine` 已改用团队的 `llm_provider.generate_json` +
  `theological_safety`（schema 校验 + 安全复审 + 危机兜底），`/suffering/analyze` 委托其 `run_and_persist`。
- 启用方式：`.env` 设 `AGENT_MODE=real` + `LLM_PROVIDER=openai` + `LLM_API_KEY=sk-...`（或 `OPENAI_API_KEY`），
  可选 `LLM_MODEL=gpt-4o-mini`。
- 回归测试 `tests/test_worldview_llm.py`：离线降级一致性、prose-only 合并、经文受保护、suffering 不经本层。

## 7. 仍可深化（非阻塞）

- diagnoser/truth_mapper 的结构化迁移**已完成**（§6）。后续可把 `apologetics`/`cultural`/`vocation`/`decision`
  也从 prose 润色升级为 schema 化输出（需各自新增 `llm_schemas` 模型）。
- 结构化 AI 富信息持久化**已完成**：`worldview_beliefs.biblical_evaluation`←`biblicalCounterTruth`、
  `worldview_beliefs.related_scripture_refs`←`scriptureAnchors`（列在 0070 已存在）；
  `distorted_beliefs.severity`/`gospel_reframe`/`scripture_refs`/`requires_pastor_attention`/`possible_root`
  ←truth-map AI 输出（`severity` 在 0071，其余由 **`0092_worldview_belief_enrichment.sql`** 补列）。
  验证见 `tests/test_worldview_persistence.py`（假 DB 游标断言 SQL 列与参数）。
- `biblical_truth_maps` / `formation_practice_library` 已有种子；可把引擎内置映射全量回填入库。
- `community_guardians` 可日后从 `guardian_profiles` + `crisis_guardian_contacts` 回填统一。
- `agent_events` 目前由 diagnose 写入 `recommend_next`，可加异步消费者真正驱动跨 Agent 编排。
