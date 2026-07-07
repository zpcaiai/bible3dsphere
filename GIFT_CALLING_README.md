# 恩赐与呼召识别系统（Gift & Calling OS · GCOS v1.0）

把"识别天然优势 / 属灵恩赐 / 属灵果子 / 使命负担 / 误用风险 / 服事匹配 / 成长计划"
落成一个可计算、可复盘的闭环。系统**只做辅助辨识，不宣告最终呼召**——是属灵星球
连接 Identity OS、Worldview OS、Crisis OS、Formation OS、Church Knowledge Graph
的恩赐识别中枢。

> 闭环：问卷 → 优势/恩赐/果子/使命 → 误用风险 → 服事匹配 → 30/90/180 计划 → 共同体反馈 → 长期复盘。

---

## 1. 神学边界（贯穿前后端）

引擎与提示词强制以下 8 条护栏（见 `gift_calling_engine.GUARDRAIL_SYSTEM_PROMPT`）：

1. **不宣告最终呼召**——只给"可能倾向 / 可探索方向 / 需共同体确认"。
2. **恩赐分数不是属灵等级**——高分不代表更属灵，低分不代表没有价值。
3. **身份根基在基督里**——不在能力、表现、服事成果或他人认可（每份报告恒含 `identity_reminder`）。
4. **不鼓励**属灵骄傲、比较、操控、越权服事。
5. **危机转介**——涉及自伤 / 严重抑郁 / 创伤 / 成瘾 / 精神危机时，建议寻求可信赖牧者、
   专业辅导或当地紧急帮助（与 Crisis OS 衔接），不替代牧养与医疗。
6. **区分**天然优势 / 后天技能 / 属灵恩赐 / 属灵果子 / 使命负担 / 教会确认。
7. **语气**温柔、诚实、具体、非定罪，避免"神一定呼召你做……"的绝对化表达。
8. **一切导向**爱神爱人、建造教会、服事邻舍、荣耀基督、在真理中成长。

产品级体现：测评前必须勾选 `theological_boundary_ack`（"我已理解：这是辅助辨识，不是
最终呼召宣告"）；一个**强恩赐若缺乏对应果子，不会得到 A 级服事推荐**——果子成熟度会把
它降到"试验级"（"凭果子认树"在代码层强制）。

---

## 2. 架构总览

```
问卷输入
  → Strength Profiler        天然优势画像（10 维）
  → Spiritual Gifts          属灵恩赐辨识（15 类）
  → Fruit Verification       属灵果子验证（9 果子）← 防止只看"能力/恩赐"
  → Calling Pattern          使命负担模式（12 类）
  → Community Confirmation    共同体确认（反馈表 + 加权聚合）
  → Misuse Risk              恩赐误用风险（含福音重构 + 操练）
  → Ministry Matching        服事岗位匹配（A/B/C/D + 保护机制）
  → Growth Path Planner      30/90/180 天成长计划
  （Orchestrator: assess() 顺序聚合 → 完整报告）
```

工程取向（与 disciple / crisis / formation 各 OS 一致）：

- **确定性核心**：纯函数 + 关键词启发式，零依赖可跑，永远返回完整报告。
- **AI 增强**：复用 `waiting_engine.call_ai_provider`（OpenAI 兼容，Gemini/SiliconFlow），
  一次结构化 JSON 调用产出全部维度；失败回退确定性结果。
- **落库分层**：分数结构化入列，复杂解释入 JSONB；引擎不落库、不依赖 FastAPI（便于单测），
  落库与回流由 `routers/gift_calling.py` 负责。
- **用户以 `users.email` 标识**（不新建 users 表，不用 UUID）。

---

## 3. 后端文件（仓库 `bible3dsphere`）

| 文件 | 作用 |
| --- | --- |
| `backend/gift_calling_engine.py` | 8 Agent 确定性核心 + AI 增强 + Orchestrator `assess()` / `meta()` / `empty_profile()`。无库、无 FastAPI。 |
| `backend/routers/gift_calling.py` | `/api/gift` 路由：跑引擎 → 单事务落 8 张子表 → 聚合回报告。 |
| `backend/migrations/0069_gift_calling_os.sql` | 9 张表 + 索引（含 GIN）+ `updated_at` 触发器。幂等。 |
| `backend/tests/test_gift_calling_engine.py` | 10 个 `no_db` 单测。 |
| `backend/main.py` | 注入 + 注册路由（import / `init_gift_calling_router` / `include_router`）。 |

### 8 个 Agent（`gift_calling_engine.py`）

- 常量谱：`STRENGTHS`(10) / `GIFTS`(15) / `FRUITS`(9) / `CALLINGS`(12) / `RISKS`(8) / `MINISTRIES`(12)。
- 每个谱含中文标签 + 关键词信号；打分 `0~100`，证据取命中关键词。
- 关键风控：`align_gift_fruit()`（恩赐缺果子→标记风险与操练）、`match_ministries()`
  （能力 × 果子成熟度 × 风险共同决定 A/B/C/D 级）、`build_growth_plan()`（三阶段模板）。

### API 端点（`/api/gift`，均需登录，`email` 标识）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET  | `/api/gift/meta` | 维度/恩赐/果子/使命/风险/服事清单 + 反馈表 + 神学边界文案 |
| GET  | `/api/gift/profile` | 当前用户最近一次完整测评（聚合报告） |
| POST | `/api/gift/assess` | 提交问卷 → 跑 8 Agent → 落库 → 返回完整报告 |
| GET  | `/api/gift/history` | 历次测评列表 |
| GET  | `/api/gift/assessment/{id}` | 指定测评的完整报告（校验归属） |
| POST | `/api/gift/feedback` | 提交共同体反馈（牧者/同工/被服事者…） |
| GET  | `/api/gift/feedback` | 收到的反馈 + 加权聚合 |
| POST | `/api/gift/review` | 新增一条长期复盘 |
| GET  | `/api/gift/review` | 复盘记录列表 |

---

## 4. 前端文件（仓库 `bible3dsphereWeb`）

| 文件 | 作用 |
| --- | --- |
| `src/GiftCallingView.jsx` | 主视图：概览/测评/反馈/复盘/历史 五个二级标签，完整 8 段报告渲染。 |
| `src/api.js` | 末尾"Gift & Calling OS"块：`fetchGiftMeta` / `fetchGiftProfile` / `assessGift` / `fetchGiftHistory` / `fetchGiftAssessment` / `submitGiftFeedback` / `fetchGiftFeedback` / `submitGiftReview` / `fetchGiftReviews`。 |
| `src/PrayerWallPage.jsx` | 接线点：新增 `🎁 恩赐呼召` 子标签（与"门徒塑造"并列）。 |

### 接线点

挂在代祷/成长中枢 `PrayerWallPage` 的子标签下（与 `DiscipleFormationView` 同级）：

```jsx
import GiftCallingView from './GiftCallingView'
// 子标签按钮
<button className={`ev-subtab ${subTab === 'gift' ? 'active' : ''}`}
        onClick={() => setSubTab('gift')}>🎁 恩赐呼召</button>
// 挂载
{subTab === 'gift' && <GiftCallingView user={user} token={token} />}
```

视觉：暖金主题（`#f5b53f`），与门徒塑造（紫）区分；登录/加载有兜底；测评前强制勾选神学边界。

---

## 5. 数据模型（`migrations/0069_gift_calling_os.sql`）

`gift_assessments` 为聚合根（主记录），8 张子表按 `assessment_id` 挂其下；
共同体反馈与复盘可独立收集。

```
gift_assessments  （主记录；spiritual_gifts 与 community_confirmation 入 agent_outputs）
  ├── strength_profiles      天然优势（10 分数列 + JSONB 明细）
  ├── fruit_scores           圣灵果子（9 分数列 + gift_fruit_alignment）
  ├── calling_patterns       使命模式（pattern_scores / crossroads / mission_sentence）
  ├── misuse_risks           误用风险（top_risks / risk_profile / gospel_reframes）
  ├── ministry_matches       服事匹配（recommended / experimental / not_recommended_now）
  └── growth_plans           30/90/180 计划（plan_json）
community_feedback           共同体反馈（支持匿名，可挂 assessment 或独立）
review_logs                  长期复盘（自我/牧者/共同体/月度/里程碑）
```

约定：邮箱键（`email VARCHAR(255)`）、`VARCHAR`+注释代替 PG ENUM、分数 `INT CHECK(0..100)`、
复杂结构 `JSONB`、`update_updated_at_column()` 触发器、全部 `IF NOT EXISTS` 幂等。
迁移在后端启动时由 `core/migrations.py` 自动应用（追踪于 `schema_migrations`）。

---

## 6. 测试与验证

- **迁移语法**：`pglast`（真实 PostgreSQL 语法）解析通过，56 条语句。
- **引擎单测**：`tests/test_gift_calling_engine.py` 10/10 通过（`no_db`）——
  报告形状、分数边界、恩赐×果子风险标记、误用风险含福音重构、服事 A 级被果子门槛、
  三阶段计划、共同体加权聚合、确定性可复现、身份提醒恒在。
- **路由↔库契约（静态审计）**：21 个 `cur.execute` 的 `%s` 数 == 参数数；
  每个 INSERT 列名都存在于迁移；`_assemble` 的列重建顺序与引擎键序一致。
- **编译**：`gift_calling_engine.py` / `routers/gift_calling.py` / `main.py` 全部 `py_compile` 通过。
- **前端**：`api.js` / `GiftCallingView.jsx` / `PrayerWallPage.jsx` esbuild(JSX) 语法校验通过。

```bash
# 后端引擎单测（无需数据库）
cd backend && python3 -m pytest tests/test_gift_calling_engine.py --noconftest -q
```

> 注：沙箱无法安装 Postgres，故未做"真实建库 + 跑迁移"的端到端验证——后端首次连上
> Neon 启动时会自动应用 0069。

---

## 7. MVP 优先级落地情况

| 模块 | 状态 |
| --- | --- |
| 问卷 → 优势 / 恩赐 / 果子 / 使命 | ✅ |
| 误用风险（福音重构 + 操练） | ✅ |
| 服事推荐（A/B/C/D + 保护机制） | ✅ |
| 30/90/180 成长计划 | ✅ |
| 共同体反馈（提交 + 加权聚合） | ✅ |
| 长期复盘 | ✅ |
| AI 增强（失败回退确定性） | ✅ |
| 8 Agent 独立子表落库 | ✅ |
| 牧者独立填写入口 / 邀请链接 | ⬜ 后续（当前为登录用户自邀请收集） |
| Neo4j 图谱 / 教会事工需求匹配 | ⬜ 后续（`church_needs_alignment` 已留位） |

---

## 8. 一句话架构

> 用确定性引擎兜底、AI 增强提质，在 `users.email` 之上把"恩赐辨识—果子验证—风险守望—
> 服事匹配—成长复盘"做成一次可复盘的闭环；分数结构化、解释入 JSONB；**恩赐永远被果子、
> 共同体与基督里的身份所约束**——辅助辨识，而非宣告呼召。
