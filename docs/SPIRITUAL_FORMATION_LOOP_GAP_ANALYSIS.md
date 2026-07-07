# 属灵星球 · Spiritual Formation Loop — 规格 vs. 现有代码 缺口分析

> 对比对象：你粘贴的《Spiritual Formation Loop Engine》规格（38 张表 / 12 个 Skill / FastAPI+pgvector+Next.js MVP）
> 与现有 `bible3dsphere/backend`（73+ 迁移、~70 routers、数十个 engine）。
> 日期：2026-06-24

---

## 0. 一句话结论

**这套规格描述的系统，现有代码库里已经实现了约 80–90%**，只是架构命名不同。
规格假设“从零开始”，但你的后端早已是一个成熟系统。因此：

- **选项 1（缺口分析）** ← 本文档，是后续一切的前提。
- **选项 2（实现缺失部分）** ← 推荐路径。真正缺的只有 **3 张表 + 若干字段**，按现有约定补齐即可。
- **选项 3（全新脚手架）** ← **不推荐照搬**。在成熟系统旁重建 `app/models + app/services` 会产生两套真相、重复维护。下面给出更务实的折中。

---

## 1. 根本性架构差异（必须先决策）

| 维度 | 规格要求 | 现有代码库 | 影响 |
|---|---|---|---|
| 主键 | `UUID gen_random_uuid()` | `BIGSERIAL` | 全表 ID 风格不同 |
| 用户标识 | `user_id UUID FK` | **`email VARCHAR`** 贯穿 `agent_runs`/`review_logs`/`formation_*` 等 | 规格的 `user_id` 外键模式与现状冲突 |
| 代码组织 | `app/models/` + `app/services/` + `app/api/v1/` | **单文件 engine（`*_engine.py`）+ `routers/*.py`** | 规格的目录结构与现状是两套范式 |
| 迁移 | Alembic | **手写编号 SQL（`migrations/0001..0073`）+ `db_schema.py`** | 新表应延续 `0074_*.sql` |
| 诊断方式 | 通用 `diagnostic_templates/questions` 问卷引擎 | **按领域分散的 engine**（checkup / gospel / disciple / worldview） | 规格想要“统一诊断管线”，现状是“多条专用管线” |

> **结论**：现有库是 email-keyed、engine+router、手写 SQL 迁移的成熟系统。
> 任何“实现缺失”都应**延续这套约定**，而不是引入规格里的 UUID/Alembic/app-services 范式（除非你决定做一次大重构）。

---

## 2. 38 张规格表 → 现有 schema 映射

图例：✅ 已存在（有直接对应） · 🟡 部分/分散（按领域已实现，但无统一表或缺字段） · ❌ 缺失（无实质对应）

### 域 1 Identity & Church
| # | 规格表 | 状态 | 现有对应 |
|---|---|---|---|
| 1 | users | ✅ | `users`（+ `sfds_users`） |
| 2 | churches | ✅ | `churches` |
| 3 | church_memberships | ✅ | `church_members` |
| 4 | community_groups | 🟡 | `voice_groups`、`seekers_class_courses`（无通用小组表） |
| 5 | group_memberships | 🟡 | `voice_group_members` |

### 域 2 Spiritual Profile
| # | 规格表 | 状态 | 现有对应 |
|---|---|---|---|
| 6 | spiritual_profiles | 🟡 | 分散于 `disciple_profiles` / `worldview_profiles` / `guardian_profiles` / `strength_profiles` / `personality_profile_snapshots`（**无单一统一画像表**） |
| 7 | privacy_permissions | 🟡 | `user_consents` + `crisis_care_shares`（无通用“按对象 × share_level”矩阵） |

### 域 3 Diagnosis
| # | 规格表 | 状态 | 现有对应 |
|---|---|---|---|
| 8 | diagnostic_templates | ❌ | 仅 `worldview_question_bank`（仅 worldview） |
| 9 | diagnostic_questions | 🟡 | `worldview_question_bank` |
| 10 | diagnostic_sessions | 🟡 | `spiritual_checkups` / `gospel_diagnoses` / `disciple_assessments` / `worldview_assessments`（按领域，无统一 session） |
| 11 | diagnostic_answers | 🟡 | `worldview_responses`（按领域） |
| 12 | diagnostic_findings | 🟡 | `gospel_diagnoses` / `distorted_beliefs` / `worldview_dimension_scores`（按领域，无统一 findings） |
| 13 | sin_patterns | ✅ | `attachment_patterns` / `guardian_behavior_patterns` / `guardian_idol_signals` / `distorted_beliefs`（`idolatry_engine` / strongholds） |
| 14 | worldview_beliefs | ✅ | `worldview_beliefs` |

### 域 4 Practice
| # | 规格表 | 状态 | 现有对应 |
|---|---|---|---|
| 15 | practice_catalog | ✅ | `formation_practice_library` |
| 16 | practice_plans | ✅ | `formation_plans`（+ `growth_plans` / `spiritual_transformation_plans`） |
| 17 | practice_tasks | ✅ | `formation_tasks` |
| 18 | practice_task_completions | ✅ | `formation_task_logs` |

### 域 5 Feedback
| # | 规格表 | 状态 | 现有对应 |
|---|---|---|---|
| 19 | daily_checkins | ✅ | `user_checkins`（+ `guardian_spiritual_checkins` / `daily_dew`） |
| 20 | reflection_logs | 🟡 | `examen_entries` / `devotion_journals` / `personal_journals` / `spiritual_daily_examens`（**多表，且多数无 embedding 列**） |
| 21 | weekly_reviews | ❌ | 仅通用 `review_logs`（gift-calling 作用域）+ `spiritual_formation` router 内联逻辑（**无专用周复盘表**） |
| 22 | feedback_summaries | 🟡 | `feedback.py` router + `formation_task_logs`（无专用摘要表） |

### 域 6 Community Accountability
| # | 规格表 | 状态 | 现有对应 |
|---|---|---|---|
| 23 | accountability_partners | ✅ | `friendships` + `spiritual_partners` + `accountability_goals/checkins` |
| 24 | shared_reports | 🟡 | `crisis_care_shares` / `sharing_wall`（无通用“成长摘要分享”表） |
| 25 | prayer_requests | ✅ | `prayers` / `prayer_commitments` / `prayer_updates` |
| 26 | community_feedback | ✅ | `community_feedback` |

### 域 7 Formation
| # | 规格表 | 状态 | 现有对应 |
|---|---|---|---|
| 27 | formation_cycles | ✅ | `formation_plans`（含周期类型）+ `growth_plans` |
| 28 | formation_milestones | ✅ | `milestone_events` |
| 29 | fruit_scores | ✅ | `fruit_scores` |
| 30 | formation_memory_events | 🟡 | `guardian_memories` / `sfds_user_spiritual_timeline`（embedding 待确认） |

### 域 8 Calling & Gifts
| # | 规格表 | 状态 | 现有对应 |
|---|---|---|---|
| 31 | gift_profiles | ✅ | `gift_assessments` + `strength_profiles` + `calling_patterns` + `misuse_risks` |
| 32 | calling_experiments | 🟡 | `ministry_matches` / `vocation_worldview_cases`（无显式“呼召实验”表） |

### 域 9 Crisis & Escalation
| # | 规格表 | 状态 | 现有对应 |
|---|---|---|---|
| 33 | crisis_contacts | ✅ | `crisis_guardian_contacts` |
| 34 | crisis_events | ✅ | `crisis_events` |
| 35 | escalation_logs | 🟡 | `crisis_followups` / `crisis_share_views`（`crisis_engine` 内有升级逻辑，无专用日志表） |

### 域 10 AI Orchestration & Audit
| # | 规格表 | 状态 | 现有对应 |
|---|---|---|---|
| 36 | ai_agent_runs | 🟡 | `agent_runs`（**email-keyed；缺 `skill_name` / `prompt_version` / `model_name` / `latency_ms` / `token_usage` / `error_message`**） |
| 37 | theological_review_logs | ❌ | **无表**（最多 engine 内联）— 规格 Skill 9 的产物缺落地 |
| 38 | audit_logs | 🟡 | `admin_audit_log` / `security_audit` / `sfds_audit_log` / `crisis_share_views`（分散，无统一审计表） |

**统计**：✅ 约 19 · 🟡 约 16 · ❌ 3（`diagnostic_templates`、`weekly_reviews`、`theological_review_logs`）。

> 注：pgvector 基础设施**已在用**（`sfds_schema_core.sql` / `database_indexes.sql` 含 `vector(...)`，圣经双语向量也在跑）。规格的 pgvector 需求在“基建层”已满足；只差给 `reflection_logs`/`formation_memory_events` 等表补 embedding 列与检索 API。

---

## 3. 12 个规格 Skill → 现有 engine/router 映射

| Skill | 规格意图 | 现有实现 | 覆盖 |
|---|---|---|---|
| 1 数据库迁移/模型 | 38 表 migration | `migrations/0001..0073` + `db_schema.py` | ✅ 大部分 |
| 2 诊断 Agent | 属灵诊断 | `checkup_engine` / `gospel_engine` / `disciple_engine` / `discernment_engine` | ✅ 分散实现 |
| 3 操练处方 Agent | 7/30/90 天计划 | `formation_engine` / `formation_pipeline` / `formation_practice_library` | ✅ |
| 4 每日反馈 Agent | 打卡反馈 | `routers/feedback.py` / `daily_dew` / `dew_engine` | ✅ |
| 5 每周复盘 Agent | 周趋势复盘 | `spiritual_formation` router 内联 + 通用 `review_logs` | 🟡 无专用周复盘 |
| 6 群体监督/隐私 | 同伴/分享/权限 | `accountability` / `community` / `spiritual_partner` / `crisis_care_shares` | ✅ |
| 7 长期塑造周期 | 90 天周期 | `formation_engine` / `growth_plans` / `milestone_events` | ✅ |
| 8 危机&牧者升级 | 危机识别 | `crisis_engine`（1021 行 router！）/ `guardian_engine` / `pastoral_engine` | ✅ 很完整 |
| 9 神学安全审查 | 输出福音中心审查 | **无专用模块/表** | ❌ 真缺口 |
| 10 API 层 | REST 端点 | ~70 个 `routers/*.py` | ✅ |
| 11 前端页面 | 7 大页面 | `bible3dsphereWeb`（Vite+React，非 Next.js） | ✅ 不同栈 |
| 12 端到端 MVP | 整闭环 | 已上线（Vercel + Neon） | ✅ |

---

## 4. 真正值得做的事（按优先级）

**P0 — 真缺口（无对应，价值高，架构中立）**
1. `theological_review_logs` 表 + 轻量 **Theological Safety** 审查模块（Skill 9）。规格反复强调，但代码里没有落地。最该补。
2. `weekly_reviews` 专用表 + 聚合服务（Skill 5）。现状靠通用 `review_logs` + 内联逻辑，难以稳定查询趋势。
3. `agent_runs` 补可观测性字段：`skill_name` / `prompt_version` / `model_name` / `latency_ms` / `token_usage` / `error_message`（ALTER TABLE，向后兼容）。

**P1 — 统一化（已分散实现，统一后收益大）**
4. `diagnostic_templates` / `diagnostic_questions` / `diagnostic_sessions` 统一诊断管线（把 checkup/gospel/disciple/worldview 收口到一层）。
5. 统一 `audit_logs`（现 4 套审计分散）。
6. `reflection_logs` / `formation_memory_events` 补 `embedding vector(1536)` 列 + 语义检索 API（基建已就绪）。

**P2 — 锦上添花**
7. 通用 `community_groups` 小组表；统一 `spiritual_profiles` 画像视图；`calling_experiments` 显式表；通用 `shared_reports`。

---

## 5. 关于选项 2 vs 选项 3 的建议

你同时勾选了 2（在现有库实现缺失）和 3（全新脚手架）——这两者方向相反。基于上面的事实：

- **强烈建议走选项 2**：按现有约定（`0074_*.sql` 迁移、`*_engine.py` + `routers/*.py`、email-keyed）补齐 P0/P1。投入小、不破坏已上线系统。
- **选项 3 的合理价值** = 只在**新子系统**上采用规格的干净分层（service 层、统一 schema 命名），而不是整体重写。把规格当“目标架构参考”，渐进收口，而非推倒重来。
- 若你**确实想要一次大重构**（统一到 UUID + app/services + Alembic），那是一个独立的大项目，应单独立项评估迁移成本（73 迁移 + email→UUID 数据迁移风险很高）。

---

## 6. 建议的下一步

我可以立即开始 **P0 #1**：按现有 SQL 迁移约定新增 `0074_theological_review_logs.sql`，并写一个 `theological_safety_engine.py` + `routers/` 端点（沿用 email-keyed、engine+router 风格），把规格 Skill 9 落地。

也可以改从 P0 #2（周复盘表）或 P0 #3（agent_runs 字段）开始 —— 看你优先级。
