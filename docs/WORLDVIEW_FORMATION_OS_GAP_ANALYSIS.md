# Worldview Formation OS — 差距分析与落地计划

> 对照对象：`bible3dsphere/backend`（纯 Python / FastAPI 后端）
> 规格来源：用户提供的 "Worldview Formation OS / 世界观塑造系统" TypeScript 风格设计（10 Agent + 35 张表）
> 结论一句话：**后端已经实现了规格的 ~60%，只是没有统一在 "worldview" 这一层下。不要按 TS 规格重建；要做的是「在现有引擎之上补一层世界观编排 + 3 个全新 Agent + 补齐若干半成品」。**
> 实现语言：**Python / FastAPI，复用现有 `*_engine.py` + `routers/` + `migrations/00xx`。**

---

## 0. 执行摘要

| 维度 | 现状 |
|---|---|
| 后端语言 | Python 3.11 / FastAPI（规格写的是 TS，**不采用**，改用 Python） |
| 现有引擎 | 20+ 个 `*_engine.py`，60+ 个 `routers/`，~161 张表，迁移到 `0069` |
| 已有扩展 | `pgvector`、`pg_trgm`、`timescaledb`、`postgis`、`uuid-ossp`（**无 Neo4j**，图用 PG 表模拟） |
| 10 Agent 覆盖 | 已实现 2 · 强覆盖 2 · 部分 3 · 缺失 3 |
| 35 表覆盖 | 已存在 9 · 部分 6 · 缺失 20（其中 9 张是全新的 `worldview_*` 家族） |
| 安全关键 | **危机优先（crisis-first）路由已落地且稳健**，必须保留并复用，不要重写 |

**最重要的判断**：规格里真正"从零新建"的只有三块——
1. **统一的世界观诊断层**（`worldview_*` 家族 + Worldview Diagnoser）——目前完全不存在；
2. **Apologetics Lens（护教学）**——完全不存在；
3. **Narrative Rewriter（福音叙事重写）** 的"旧叙事→新叙事"闭环——只有零件，没有成品。

其余 7 个 Agent 都已有对应引擎，工作量是"扩展 + 补表 + 接线"，而非重建。

---

## 1. 关键认知：规格 vs 现实

规格是一份**绿地（greenfield）设计**，假设从零搭 TS 服务。现实是一个**成熟的 Python 后端**，已经把规格里的偶像识别、危机/苦难、属灵决策、操练计划、守护人、福音映射等都实现了，只是：

- 它们是**并列的独立引擎**（idolatry / crisis / decision / formation / gospel / discernment / guardian …），没有一个"世界观"上层概念把它们串起来；
- 没有 `worldview_*` schema，也没有"按 12 领域给底层信念打分并持久化画像"的诊断器；
- 命名不同（规格 `idol_patterns` ↔ 现实 `attachment_patterns`，规格 `crisis_risk_assessments` ↔ 现实 `crisis_events`，规格 `community_guardians` ↔ 现实 `guardian_profiles` + `crisis_guardian_contacts`）。

> **落地策略**：把 "Worldview Formation OS" 实现为一个**编排层（orchestrator）+ 诊断器**，复用既有引擎作为下游节点；只为真正缺失的能力新建引擎和表。规格第 8 节建议的内部名 **Kingdom Lens OS** 可作为该编排层的模块名（如 `worldview_orchestrator.py` / `routers/worldview.py`）。

---

## 2. 10 个 Agent 覆盖矩阵

| # | 规格 Agent | 判定 | 现有实现 | 主要缺口 |
|---|---|---|---|---|
| 1 | Worldview Diagnoser 世界观诊断 | ❌ **缺失** | `formation_engine.py` 有 8 维"品格向量"(humility/fear/pride/…)，但那是性格倾向，不是世界观领域；无领域分类法、无信念抽取、无 `worldview_profiles` | 整个 12 领域诊断 + 0-100 打分 + 持久化画像 + 多源(日记/祷告/聊天)融合 |
| 2 | Idol Detector 偶像识别 | ✅ **已实现** | `idolatry_engine.py` + `routers/idolatry.py`；表 `attachment_patterns`/`attachment_sessions`(迁移 0021)；含依附强度指数、核心恐惧/渴望、福音破除原则、风险分级、非定罪措辞 | 仅 7 类偶像（规格要 13-14 类，缺 knowledge/technology/self_realization/national_political/victimhood/power）；无独立"证据观察"结构化字段 |
| 3 | Biblical Truth Mapper 圣经真理映射 | 🟡 **部分** | `gospel_engine.py`(6 偶像→福音真理+经文+默想+祷告+行动) + `stronghold_rag.py`/`stronghold_knowledge.py`(18 堡垒 + 19 教义标签 + 关键词/向量 RAG) + `dew_engine.py`(每日默想) | 两套(gospel 6 + stronghold 18)未合流；`biblical_characters` 图谱(迁移 0053-0067)**未接线**到"推荐圣经人物"；无 lie→truth 映射表 |
| 4 | Narrative Rewriter 福音叙事重写 | ❌ **缺失** | `gospel_engine.py` 有 emotion→idol→unbelief→gospel→action 的零件；`formation_engine` 有 trajectory_narrative(行为趋势,非生命故事) | 无"旧叙事模板"分类法、无旧叙事抽取、无 fear→idol→lie→truth→新叙事→操练 的统一闭环、无旧/新叙事持久化 |
| 5 | Apologetics Lens 护教学视角 | ❌ **缺失** | 无 `apologetics_engine.py`/路由；`stronghold_knowledge.py` 有科学主义/相对主义/技术弥赛亚等条目但**只是被动 RAG 语料** | 前提(presupposition)检测、世俗 vs 圣经框定、护教回应、教义标签、推荐资源——全缺 |
| 6 | Cultural Discernment 文化分辨 | 🟡 **部分** | ⚠️ `discernment_engine.py` 名字像，但做的是**决策分辨**(decision discernment)，不是文化时代精神；`stronghold_knowledge.py` 含 18 个文化堡垒(消费主义/数字分心/技术弥赛亚/政治偶像/虚无主义…)但被动 | 无主动的"时代精神"识别 Agent：隐藏应许/要求、文化礼仪、反文化操练；无 `cultural_discernment_cases` 表 |
| 7 | Vocation Worldview 职业使命世界观 | 🟡 **部分** | `gift_calling_engine.py`(1057 行,8 子 Agent) + `routers/gift_calling.py` + 迁移 0069 的 9 张表(strengths/gifts/fruit/calling_patterns/ministry/growth/feedback/misuse/review) | 缺：工作/金钱/成功观的**偶像诊断**、职业**伦理风险**、**国度机会**框定、金钱神学维度 |
| 8 | Suffering Theology 苦难神学（安全关键） | ✅ **已实现(部分)** | `crisis_engine.py`：5 级风险(green/yellow/orange/red)+11 类危机类型 + 安全问答状态机 + 守护人告警 + **crisis-first 路由**(高危先安全、暂停操练、温和重入 `formation_seed`)；8 类属灵苦难分类 + 安慰经文池(避免"你信心不够"等禁语) | 缺**结构化哀歌祷告模板**(呼求/控诉/肯定)；缺**圣经人物推荐器**(数据已在 `biblical_characters`,只差过滤层)；牧养回应较窄(仅 8 类) |
| 9 | Decision Formation 属灵决策塑造 | ✅ **已实现** | `decision_engine.py` + `decision_support.py`(1647 行) + `discernment_engine.py` V2 + `routers/discern.py`；表 `decision_discernments`(迁移 0032)/`decision_review_logs`；含动机(恐惧/骄傲/爱/渴望/责任/野心)、偶像、盲点、智慧问题、不替用户决定 | 仅缺显式"是否需要寻求牧者/属灵同伴建议"的 `counsel_recommended` 标志 |
| 10 | Formation Practice 世界观操练 | ✅ **已实现(部分)** | `spiritual_formation_engine.py`：`generate_transformation_plan(7/30/90 天 × light/standard/battle/deep)`；12 项通用操练 + 13 类模式专属操练；表 `spiritual_transformation_plans`；危机用户安全降级规则 | 缺**带时间戳的完成日志**(现仅 `completed_practice_ids` 数组)、缺**里程碑指标快照**(第 7/30/90 天)、缺 1/3 天微计划、缺 burnout 专属强度 |

**计分**：已实现 **2**（#2、#9）· 强覆盖 **2**（#8、#10）· 部分 **3**（#3、#6、#7）· 缺失 **3**（#1、#4、#5）。

---

## 3. 35 张表覆盖映射

> 现有 schema 散落在 `database_schema.sql` / `db_schema.py` / `crisis_schema.sql` / `habit_behavior_schema.sql` / `biblical_characters_schema.sql` / `sfds_*.sql` / `spiritual_formation_schema.sql` / `stronghold_*_schema.sql` / `migrations/0001-0069`。迁移命名规范 `NNNN_desc.sql`（4 位零填充，幂等 `IF NOT EXISTS`），**下一个可用编号 = 0070**。

### ✅ 已存在（9）— 直接复用/加别名视图，不要重建
| 规格表 | 现实等价 | 位置 |
|---|---|---|
| `users` | `users` | `database_schema.sql` |
| `idol_patterns` | `attachment_patterns` | 迁移 `0021` |
| `idol_observations` | `attachment_sessions` | 迁移 `0021` |
| `decision_cases` | `decision_discernments`（+ `sfds_decision_events`） | 迁移 `0032` / `sfds_schema_core.sql` |
| `bible_person_mappings` | `biblical_characters` + `biblical_graph_nodes` | `biblical_characters_schema.sql` / 迁移 `0056-0060` |
| `community_guardians` | `guardian_profiles` + `crisis_guardian_contacts`（**已碎片化，需统一**） | 迁移 `0044` / `crisis_schema.sql` |
| `community_feedback` | `community_feedback` | 迁移 `0069` |
| `agent_runs` | `agent_runs` | 迁移 `0037` |
| `review_logs` | `review_logs` | 迁移 `0069` |

### 🟡 部分（6）— 已有近似表/数据，缺关键列或缺"映射成表"
| 规格表 | 现实等价 | 缺什么 |
|---|---|---|
| `distorted_beliefs` | `stronghold_scans` / `sfds_user_patterns` | 无专门的"扭曲信念→严重度→悔改方向"表 |
| `biblical_truth_maps` | `gospel_engine` 内置逻辑 + `character_scriptures` + `biblical_graph_*` | 逻辑在代码里硬编码，未沉淀为 lie→truth 映射表；人物未接线 |
| `crisis_risk_assessments` | `crisis_events` | 字段是 JSONB 证据，缺规格要求的规范化评估结构（可加视图/列） |
| `formation_plans` | `spiritual_transformation_plans` | 操练以 JSONB 嵌在计划里，缺独立 plan/task 拆分 |
| `scripture_resources` | `stronghold_rag_documents`（+ bible CSV/向量 `.npy`） | 非以"经文资源"语义建表 |
| `knowledge_chunks` | `stronghold_rag_documents` + `sfds_spiritual_principles`(带 embedding) | RAG 已就绪，缺统一的 `knowledge_chunks` 表（沿用 pgvector 模式即可） |

### ❌ 缺失（20）— 需新建（0070+）
**世界观核心家族（9，全新）**：`worldview_domains`、`worldview_question_bank`、`worldview_profiles`、`worldview_assessments`、`worldview_dimension_scores`、`worldview_responses`、`worldview_beliefs`、`worldview_presuppositions`、`worldview_metric_snapshots`

**专项 Agent 案例表（5）**：`narrative_rewrites`、`apologetics_cases`、`cultural_discernment_cases`、`vocation_worldview_cases`、`suffering_cases`

**操练闭环补全（3）**：`formation_practice_library`、`formation_tasks`、`formation_task_logs`

**治理/合规（2）**：`guardian_alerts`、`agent_events`（注：`domain_events` 内部表已存在,可扩展）

**用户授权（1）**：`user_consents`（注：`crisis_*` 表上已有 `consent_enabled` 标志，但无中心化授权表）

---

## 4. 真正"全新"的工作清单（按价值排序）

1. **世界观诊断层 + `worldview_*` schema**（Agent 1）—— 这是整个 OS 的"上层认知操作系统"，目前 0 覆盖，价值最高。
2. **Apologetics Lens 引擎**（Agent 5）—— 完全缺失；可把 `stronghold_knowledge.py` 的被动语料升级为主动前提检测。
3. **Narrative Rewriter 闭环**（Agent 4）—— 复用 `gospel_engine` 的祷告/行动脚手架，补"旧叙事模板 + 抽取 + 重写 + 持久化"。
4. **Worldview Orchestrator 编排器**（"Kingdom Lens OS"）—— 串起 诊断→偶像→真理→叙事→操练，并在最前面挂 **crisis-first 守卫**。
5. **补半成品**：Cultural Discernment 主动化（#6）、Vocation 加偶像/伦理/金钱维度（#7）、Truth Mapper 合流 + 接线圣经人物（#3）。
6. **补操练闭环**：`formation_tasks` / `formation_task_logs` / `worldview_metric_snapshots`（#10）。
7. **补苦难层**：哀歌祷告模板 + 圣经人物推荐器（#8，**安全相关，优先于一般功能**）。

---

## 5. 落地计划（Python / FastAPI，分批）

> 原则：迁移续编 `0070+`；新引擎沿用 `xxx_engine.py` + `routers/xxx.py` 约定；下游复用既有引擎而非复制其逻辑；**任何苦难/世界观分析前先过 `crisis_engine.triage()`**。

### Batch 0 — 命名对齐与编排骨架（低风险，先做）
- 新建 `backend/worldview_orchestrator.py`（即 "Kingdom Lens OS"）：定义闭环管线，第一步强制调用 `crisis_engine.triage()`；high/imminent 直接走危机路由，跳过世界观分析。
- 新建 `backend/routers/worldview.py`，挂载规格第 6 节的 `/api/worldview/*` 端点（先做 stub + 路由表）。
- 文档化别名：`idol_patterns≡attachment_patterns`、`crisis_risk_assessments≡crisis_events`、`decision_cases≡decision_discernments`、`community_guardians≡guardian_profiles(+crisis_guardian_contacts)`，避免重复建表。

### Batch 1 — 世界观核心（最高价值，全新）
- 迁移 `0070_worldview_core.sql`：建 9 张 `worldview_*` 表 + 12 领域种子数据(`worldview_domains`) + 问题库种子(`worldview_question_bank`)。复用 `pgvector` 给 `worldview_responses.embedding`；`worldview_metric_snapshots` 可建 Timescale hypertable（已装 timescaledb）。
- 新建 `backend/worldview_diagnoser_engine.py`：领域识别 + 信念抽取 + 0-100 打分 + upsert `worldview_profiles`。**复用**：调用 `idolatry_engine` 取偶像信号、`formation_engine` 取品格向量作为辅助证据。
- 安全：诊断入口先过 `crisis_engine.triage()`；高危时 `recommendedNextAgents=["suffering_theology"]` 并停止复杂分析。

### Batch 2 — 诊断闭环（扩展 + 接线，复用为主）
- **Idol Detector（#2）**：扩 `idolatry_engine.py` 偶像类型 7→13（加 knowledge/technology/self_realization/national_political/victimhood/power）；迁移给 `attachment_patterns` 加缺失字段（core_lie/evidence 观察）。
- **Truth Mapper（#3）**：新建 `backend/truth_mapper_engine.py`，合并 `gospel_engine` + `stronghold_rag`，并**接线** `biblical_characters`/`biblical_graph_nodes` 产出"推荐圣经人物"；迁移 `0071` 建 `biblical_truth_maps` + `distorted_beliefs`。
- **Narrative Rewriter（#4）**：新建 `backend/narrative_engine.py`（或扩 `gospel_engine`）+ `routers/narrative.py`；迁移 `0071` 加 `narrative_rewrites`；复用 gospel 的祷告/行动模板。

### Batch 3 — 专项世界观 Agent（新建 + 补全）
- **Apologetics Lens（#5）**：新建 `backend/apologetics_engine.py` + `routers/apologetics.py`；前提检测复用 `stronghold_knowledge` 语料 + `stronghold_rag` 检索；迁移 `0072` 建 `apologetics_cases`。
- **Cultural Discernment（#6）**：把 `stronghold_knowledge` 的 18 文化堡垒升级为主动 Agent `backend/cultural_engine.py` + `routers/culture.py`（**勿与决策版 `discernment_engine.py` 混淆**）；迁移 `0072` 建 `cultural_discernment_cases`。
- **Vocation Worldview（#7）**：扩 `gift_calling_engine.py`，加 vocation_idols / ethical_risks / kingdom_opportunities / money_theology 维度；迁移 `0072` 建 `vocation_worldview_cases`。

### Batch 4 — 苦难与危机优先（安全关键，可与 Batch 2 并行提前）
- **Suffering Theology（#8）**：在 `crisis_engine.py`/新 `suffering_engine.py` 加 `lament_prayer_template(type)`（呼求/控诉/肯定）与 `recommend_bible_persons(type)`（数据已在 `biblical_characters`，建过滤层）。
- 迁移 `0073`：`suffering_cases`、`user_consents`；`crisis_risk_assessments` 以视图/补列方式对齐 `crisis_events`。
- **保留并复用现有 crisis-first 路由**（`crisis_engine.triage` → 安全问答状态机 → `guardian_alert_text` → `formation_seed` 温和重入）。**不要重写。**

### Batch 5 — 决策与操练闭环
- **Decision（#9）**：给 `decision_support` 的 intervention 输出加 `counsel_recommended: bool`。
- **Formation（#10）**：迁移 `0074` 建 `formation_practice_library`、`formation_tasks`、`formation_task_logs`；把 `spiritual_transformation_plans` 的 JSONB 操练拆成 task 行；加第 7/30/90 天 `worldview_metric_snapshots` 触发。

### Batch 6 — 群体协作与治理
- 迁移 `0075`：统一 `community_guardians`（合并 `guardian_profiles` + `crisis_guardian_contacts`）、建 `guardian_alerts`、`agent_events`（或扩 `domain_events`）。`agent_runs`/`review_logs`/`community_feedback` 已存在，仅接线。

---

## 6. MVP 建议（最短闭环）

复用现状，最快跑通规格第 7 节的 MVP Core 只需 **Batch 0 + 1 + Narrative(部分 Batch 2)**：

```
日记/祷告/决策输入
 → [新] Worldview Diagnoser（crisis-first 守卫）
 → [已有] idolatry_engine 识别偶像
 → [已有] gospel_engine + stronghold_rag 给圣经真理
 → [新] narrative_engine 重写旧叙事
 → [已有] spiritual_formation_engine 生成 7 天操练
 → [新] worldview_metric_snapshots 输出雷达图
```

MVP 必建表：`worldview_*`(9) + `narrative_rewrites`。其余全部复用既有表（`attachment_patterns`、`gospel_diagnoses`、`stronghold_rag_documents`、`spiritual_transformation_plans`、`agent_runs`）。

---

## 7. 安全与合规须知（务必遵守）

- **危机优先是硬约束**：现有 `crisis_engine.triage()` 已实现 5 级风险 + 11 类危机 + 禁语清单 + 安全问答 + 守护人告警。任何 `worldview/suffering/decision` 入口都必须**先调用它**，high/imminent 时跳过一切神学分析。参见 `CRISIS_CARE_README.md`、`CRISIS_COMPLIANCE_REVIEW.md`。
- 苦难/羞耻/枯竭用户**不得**生成高强度操练计划（沿用 `formation_seed` 的 light/30 天降级 + 非定罪声明）。
- 偶像/扭曲信念输出保持**非定罪措辞**（"可能/似乎/值得在神面前省察"），现有 `idolatry_engine` 已是此风格，扩展时保持一致。

---

## 8. 给 Claude Code / Codex 的执行提示

- **不要**按 TS 规格新建 `src/worldview/*.ts`。按本文件的 Python 落地计划走。
- 新引擎文件名：`worldview_diagnoser_engine.py` / `truth_mapper_engine.py` / `narrative_engine.py` / `apologetics_engine.py` / `cultural_engine.py` / `suffering_engine.py`（或并入 `crisis_engine`）/ `worldview_orchestrator.py`。
- 新路由：`routers/worldview.py` / `narrative.py` / `apologetics.py` / `culture.py`，遵循现有 `routers/` 注册方式（见 `main.py` 与 `routers/__init__.py`）。
- 迁移从 `0070` 续编，幂等 `IF NOT EXISTS`，与现有约定一致。
- 复用而非复制：偶像→`idolatry_engine`，福音→`gospel_engine`，RAG→`stronghold_rag`，决策→`decision_support`，操练→`spiritual_formation_engine`，危机→`crisis_engine`，圣经人物→`biblical_characters`/`biblical_graph_*`。

---

*附：本分析基于对 `backend/` 的只读勘察（idolatry/gospel/stronghold/checkup/dew、discernment/decision/gift_calling、crisis/pastoral/formation/guardian 引擎，及 `database_schema.sql`/`db_schema.py`/各 `*_schema.sql`/`migrations 0001-0069` 的 CREATE TABLE 全量 grep）。已确认 `worldview` 在后端无任何出现。*
