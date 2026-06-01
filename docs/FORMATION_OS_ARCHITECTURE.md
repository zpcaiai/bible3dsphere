# 属灵形成 OS — 司布真 × 钟马田 双引擎架构映射

> 来源：用户上传《司布真钟马田灵修》愿景。核心：把情感星球从「灵修内容平台」转为
> **AI Spiritual Formation OS**——内容只是养料，真正的产品是「状态→识别→引导→行动→
> 复盘→人格形成」的循环。司布真 = Heart Engine（看见基督），钟马田 = Mind Engine（福音诊断）。

## 一、核心循环（已闭环）
经历 → 情绪 → 欲望 → 恐惧 → 偶像 → 不信 →（福音）→ 基督 → 祷告 → 行动 → 习惯 → 品格 → 更像基督

- 前半段「行为→情绪→欲望→偶像→不信」= **钟马田 Mind Engine**（属灵诊断）
- 后半段「福音→基督→祷告→行动」= **司布真 Heart Engine**（牧养）
- 终点「信望爱 + 谦卑顺服圣洁智慧勇气忍耐」= **Formation Layer（八维 / 像基督引擎）**

## 二、愿景 → 现状映射（大量已实现，避免重写）

| 愿景模块 | 现状 | 说明 |
|---|---|---|
| 福音诊断室 Gospel Diagnostic | ✅ **本轮新增** `gospel_engine`/`routers/gospel` | 双引擎核心循环，连接所有系统 |
| 偶像监测 Idol Detection | ✅ 已建 `idolatry_engine` | 7 类功能性偶像 + 依附强度 |
| 等候上帝 Waiting for God | ✅ 已建 `waiting_engine` | 第四大陆 |
| 品格塑造 / 信望爱 | ✅ 已建 formation 八维 + 回流 | 所有模块写 formation 事件 |
| 每日属灵循环（司布真） | ✅ 部分：今日灵修 + Examen + 感恩 | 缺「清晨甘露 AI」生成器 |
| 属灵低潮体检（钟马田） | ⬜ 未建 | 《属灵低潮》症状→根源→福音 |
| 内容按「问题」组织 | ⬜ 未建 | 现按 tab；可加「按困扰检索养料」 |
| 天路客游戏化 Pilgrim | ⬜ 未建 | 状态→疑惑谷/虚荣集市… |
| 属灵星球地图（统一 IA） | ⬜ 未建（重构级） | 七大陆地图作为首页，收编分散入口 |

## 三、本轮已实施：福音诊断室（双引擎核心）
- 迁移 `0028_gospel_diagnoses.sql`；`gospel_engine.py`（确定性双引擎 + 内嵌司布真/钟马田
  技能 Prompt 的 AI 增强，失败回退；6 类偶像→不信→福音真理→经文→默想→祷告→行动）；
  `routers/gospel.py`（meta/diagnose/history，回流 formation）；`GospelDiagnosticPage.jsx`
  （5 问引导 → 属灵病历，分「🔬钟马田·诊断」+「🕊司布真·牧养」两栏）。
- 入口：今日心镜紫金卡「福音诊断室 · 从情绪挖到福音」。

## 四、建议的后续阶段（按价值/成本，非一次重写）
1. **清晨甘露 AI**（司布真默想生成器，5/10/15 分钟三版）—— 复用 gospel_engine 的 AI 通道。
2. **属灵低潮体检**（钟马田症状诊断）—— 复用诊断框架，症状→根源→福音操练。
3. **统一「属灵星球」首页 / 信息架构重构**—— 七大陆地图，把现有分散入口（9 Tab + 多卡片）
   收编为「认识自己 / 回到福音 / 与神同行 / 等候上帝 / 人格塑造」五条主线。这是真正的「重构」，
   建议作为独立大阶段，先做信息架构与导航，再逐步迁移既有页面，避免一次性破坏在跑的功能。
4. 内容养料库按「用户困扰」检索（焦虑/低潮/罪的捆绑/等候…→ 自动组装经文+作者片段）。

> 原则：现有在跑的功能（9 Tab、formation 引擎、MVFE）保持稳定；新增与重构以「增量 + 可回退」
> 推进，每步迁移走 `migrations/00NN_*.sql`，前端沿用深色玻璃风并逐步引入统一导航。

---

## 五、第二批已实施（清晨甘露 / 属灵低潮 / 属灵星球首页）

- ✅ **清晨甘露 AI**（司布真默想 5/10/15 分钟）：`dew_engine.py`（经文池 + 主题模板默想，
  AI 走司布真默想技能 Prompt）+ 迁移 `0029_daily_dew`（全站按日缓存）+ `routers/dew.py` +
  `MorningDewPage.jsx`。入口：灵修 tab 子 tab「🌅 清晨甘露」。
- ✅ **属灵低潮体检**（钟马田《属灵低潮》）：`checkup_engine.py`（8 症状自评 → 根源/福音欠缺/
  经文/操练/祷告 +「向自己传讲福音」）+ 迁移 `0030_spiritual_checkups` + `routers/checkup.py` +
  `SpiritualCheckupPage.jsx`，回流 formation。入口：今日心镜「🩺 属灵低潮体检」。
- ✅ **属灵星球首页（IA v1，增量可回退）**：`PlanetHome.jsx` 五大陆成长地图（认识自己 /
  回到福音 / 与神同行 / 等候上帝 / 人格塑造），作为今日心镜 overlay 路由到现有功能——
  **不删除任何现有 tab/卡片**，只新增一个「成长地图」聚合入口。入口：今日心镜顶部 🪐 卡片。

> IA 完整迁移（把九个 Tab 真正收编进五大陆、改默认落地页）仍是后续大阶段；本批先以
> 「地图聚合入口」落地愿景，零风险、可回退。

---

## 六、第三批已实施（天路客 / 信望爱 / 决策辨识 / 养料库 / 双Agent）
- ✅ 第六大陆 **天路客**：`pilgrim_engine.py`(11 地点+状态定位)+迁移0031+`routers/pilgrim.py`+`PilgrimJourneyPage.jsx`。
- ✅ 第七大陆 **信望爱星系**：`virtues_engine.py`(信/望/爱/像基督4指数+9品格,由八维推导,Skill7)+`routers/virtues.py`+`FaithHopeLovePage.jsx`。
- ✅ **决策辨识(司布真版,Skill6)**：`decision_engine.py`+迁移0032+`routers/discern.py`+`DecisionDiscernmentPage.jsx`。
- ✅ **养料库**：`fuel_engine.py`(8困扰×多传统意译洞见)+`routers/fuel.py`+`FuelLibraryPage.jsx`。
- ✅ **双属灵Agent对话**：`routers/agent.py`(司布真牧养/钟马田诊断系统prompt,复用LLM provider,优雅降级)+`AgentChatPage.jsx`。
- 入口统一收进 **属灵星球地图(PlanetHome)** 的对应大陆，并在今日心镜可达。
- 见 `docs/SPIRITUAL_SKILLS.md`：7 大 Skill → 引擎映射；Neo4j/状态机/完整IA迁移的诚实说明。
