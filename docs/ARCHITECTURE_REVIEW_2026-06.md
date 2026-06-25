# 属灵塑造平台 · 架构评估与整合路线图

> 范围:bible3dsphere(后端 ~70 路由 / ~35 引擎 / 4 编排层)+ bible3dsphere-frontend(~29 可导航面板 / 77 页面)。
> 方法:模块面 + API 面判读(非逐行审计)。日期:2026-06。

## 0. 结论速览

- **互补性**:强。模块拼成一条连贯的「觉察→辨识→重塑→操练→复盘→画像→共同体」旅程,神学骨架(罪—福音—身份—操练)扎实,危机优先护栏到位。
- **闭环**:单模块/单系统闭环成立(尤以 `worldview_orchestrator` 显式闭环为代表),但有 5–6 套并行闭环,**跨模块的「一个人长期成长闭环」没有合上**。
- **重复**:这是当前最大负债——「诊断/辨识」「谎言→福音重写」「每日反思记录」「决策」「情绪输入」「社区/祷告」「读经检索」各有多套重叠实现。
- **缺口**:主要不是缺新模块,而是缺**整合层**(统一成长闭环仪表盘 + 生活规则 + 节律引擎)与少数协同能力(牧者后台、小组层、跨模块 AI 记忆、成效度量)。

**最高性价比的下一步:收敛重复(尤其诊断内核)+ 建统一成长闭环。**

---

## 1. 模块清单矩阵(按功能域)

| 功能域 | 前端入口 | 后端路由 / 引擎 | 角色 |
|---|---|---|---|
| A 觉察/输入 | 情绪星球 sphere、签到 checkin、每日一问 soul-question、省察 examen、守护者 guardian | checkin? / daily_soul_question / examen / emotion_trajectory / guardian / mvfe_stats | 捕捉情绪、念头、处境 |
| B 辨识/诊断 | 世界观 worldview、属灵塑造 spiritual-formation、恩赐呼召 gift-calling、福音诊断 GospelDiagnostic | worldview(_diagnoser/_orchestrator) / idolatry / strongholds / stronghold_rag / gospel / checkup / discern / diagnosis(_hub) / gift_calling | 辨识偶像/谎言/营垒/恩赐/世界观 |
| C 重塑/真理 | 世界观·叙事重写、ThoughtCaptiveFlow | narrative / truth_mapper / gospel / worldview_lenses | 谎言→福音真理→新叙事 |
| D 操练/塑造 | 灵修操练 habits、操练中心 PracticeHub、门徒塑造 disciple、晨露 dew、燃料库 fuel | spiritual_formation / formation(_practice) / habit_behavior / virtues / disciple / dew / fuel / pilgrim / formation_pipeline | 把真理落成操练与习惯 |
| E 复盘/记录 | 灵修日记 journal/devotion、复盘 weekly_review、反思 reflection、感恩 gratitude | journal / reflection / weekly_review / gratitude / personal_notes / examen | 记录与周期复盘 |
| F 画像/进度 | 灵命图谱 growth-map、灵命成长 engineering、里程碑 | user_profile(_tag_system) / milestones_health / stats / mvfe_stats / weekly_review | 纵向画像与度量 |
| G 共同体/关系 | 圣徒相通 communion、社区 community、祷告墙 prayer、分享墙 sharewall、属灵伙伴 partner、聚会 meetings、语音 voice、传福音 evangelism | community(_feed) / communion / church / prayer / testimony / spiritual_partner / dating_priority / meetings / call_minutes / realtime / voice / evangelism / accountability / confession | 关系、代祷、问责、见证 |
| H 圣经/资源 | 读经查经 bible-reading、麦琴 mccheyne、检索 bible-search、记忆卡 memory-deck、地图集 bible-atlas、人物图谱 mirror-graph、镜鉴 mirror | bible_reading / reading / bible_search / semantic_search / verse / books / memory(sm2) / bible_map / geo / characters / film_studio | 圣经学习与资源 |
| I 危机/牧养安全 | 危机守护(SoulTabs)、关怀 | crisis / care / suffering / pastoral / theological_safety | 危机优先、安全护栏 |
| J 决策/呼召 | 决策支持 DecisionSupport、决策辨识、等候 waiting、恩赐呼召 | decision(_engine) / decision_formation / discern / waiting / vocation_worldview / gift_calling | 决策、呼召、等候 |
| K 基础设施/管理 | 导出 export-data、个人检索 personal-search、回收站 | admin_* / agent / push / export / personal_store / recycle_bin / user_tag_system | 数据、管理、Agent |

> 注:部分前端入口聚合在「心迹」SoulTabs(今日心镜/人格塑造/灵修操练/模式库/危机守护/决策支持)与「灵镜」SoulDashboard 之下。

---

## 2. 互补性 & 闭环评估

**互补**:A→J 形成完整链路,且「危机优先」横切所有诊断之前(`crisis_guard`)。神学上四步骨架清晰:看见罪/偶像 → 福音真理 → 新身份/新叙事 → 具体顺服操练。

**闭环现状**:
- ✅ `worldview_orchestrator` 显式闭环:输入 →[危机守卫]→ 世界观诊断 → 偶像 → 真理映射 → 福音叙事重写 → 领域重塑 → 操练任务 → 复盘快照。
- ✅ spiritual-formation 闭环:每日属灵扫描 → 罪模式辨识 → 夺回思想/恩典恢复 → 操练 → 复盘。
- ✅ diagnosis_hub 汇聚多源诊断;weekly_review + growth-map + user_profile 提供反馈。
- ❌ **全局未合上**:世界观 OS、属灵塑造、恩赐呼召、MVFE、守护者各跑各的循环,数据未汇入**同一个纵向成长视图**;`SoulDashboard` 想当总汇但只是入口之一,且并未消费全部信号源。

---

## 3. 重复项 & 合并建议

| 重复簇 | 涉及模块 | 问题 | 合并建议 |
|---|---|---|---|
| 诊断/辨识内核 | worldview_diagnoser、idolatry、strongholds/stronghold_rag、gospel(诊断)、checkup、spiritual-formation 罪模式、diagnosis_hub | 「核心谎言/隐藏偶像/福音真理」被 5–6 套各做一遍;营垒 vs 罪模式 vs 偶像三套重叠分类法 | 抽出**单一「辨识内核」服务**:一个诊断入口 + 多个「透镜(lens)」(偶像/营垒/世界观/恩赐),共享一套本体(谎言/偶像/真理/经文/操练)。各前端只切换透镜,不再各自实现 |
| 谎言→福音重写 | narrative_engine、truth_mapper_engine、gospel_engine、前端 ThoughtCaptiveFlow | 三套引擎产出近似的「谎言→真理→新叙事」 | 统一为 **reframe 服务**(truth_mapper 为核心,narrative 仅做叙事润色),ThoughtCaptiveFlow 改为调用它 |
| 决策流 | decision、decision_formation、discern、DecisionSupportPage、DecisionDiscernmentPage | 多条并行决策路径 | 收敛为**一个决策流**(觉察处境→辨识动机/偶像→真理→操练/等候),决策辨识作为其一步 |
| 每日反思/记录 | examen、weekly_review、reflection、soul-question、dew、gratitude、checkin、journal | 多个重叠「每日输入」;感恩散落 4–5 处 | 统一**「每日省察」intake**(签到+情绪+感恩+省察一站)写入**单一 journaling 存储**;weekly_review 仅做聚合视图 |
| 情绪/输入 | 情绪星球、checkin、guardian 情绪签到、MVFE、soul-question | 多个情绪捕捉入口 | 统一**情绪 intake**事件,各 UI 复用同一接口 |
| 社区/祷告 | community vs community_feed vs communion;prayer vs evangelism 祷告墙 vs sharewall | 概念重叠的三套社区/祷告墙 | 合并为**一个社区 + 一个祷告墙**(按标签区分代祷/传福音/见证) |
| 读经检索 | bible_search vs semantic_search | 两套检索 | 合并为一个检索服务(关键词 + 语义) |

> 副作用:重复直接抬高维护成本与用户「该用哪个入口」的困惑——本会话里同一控件/同类数据散布各处即是症状。

---

## 4. 缺口优先级路线图

| 优先级 | 缺口 | 影响 | 建议 |
|---|---|---|---|
| **P0** | 统一成长闭环 / 纵向画像(整合层) | 数据碎片,闭环合不上 | 见 §5 落地设计 |
| **P0** | 诊断内核收敛 | 重复负债、信号源过多 | 先收敛,减少「事件生产者」数量,为整合层铺路 |
| **P1** | 生活规则(Rule of Life):目标→操练→进度 | 有操练无目标牵引 | `rule_of_life` 表 + 仪表盘进度 |
| **P1** | 节律/触发引擎(在对的时间推对的操练) | orchestrator 有 next-agent 建议但无人「按时端到用户面前」 | 复用 recommendedNextAgents + 定时任务,生成「今日该做」 |
| **P1** | 牧者/导师协同后台(纵览群羊签到/危机旗标/成长) | 牧养可视性弱 | 在 CareDashboard 基础上做牧者视图(已有 care/feedback/accountability 数据) |
| **P2** | 小组/门徒倍增的群体层(课程/带领/进度) | disciple 偏个人 | 小组实体 + 课程进度 |
| **P2** | 跨模块 AI 记忆陪伴(记得你、主动引导) | agent 整合度不明 | 以整合层事件为记忆底座,接 agent |
| **P2** | 成效度量(客观成长/留存,而非纯自评) | 难评估真实果效 | 选定北极星指标 + 操练完成/复盘留存 |

---

## 5. 重点落地设计:统一成长闭环 + 生活规则 + 节律引擎

目标:把所有模块的信号合成**一个人的属灵成长操作系统**——单一真相源 + 时间轴 + 当前焦点 + 今日该做。

### 5.1 数据底座(单一事件流 + 当前状态)
- **`formation_events`(统一事件日志)**:每次诊断/重写/操练/复盘/危机旗标都 emit 一条
  `{user, ts, source(模块), type(diagnosis|reframe|practice|review|crisis|gift|...), domain, payload, refs(经文/操练), severity}`。
  现有 `diagnosis_hub`、`_audit`、`worldview_metric_snapshots` 已是雏形 → 统一规范化即可。
- **`growth_state`(当前画像快照)**:`{dominant_idols, active_themes, current_focus, maturity, risk_level, last_updated}`;
  由聚合器从 `formation_events` 滚动计算(复用 `user_profile_tag_system` + worldview profile)。

### 5.2 API
- `GET /api/formation/timeline` — 神的带领时间轴(按时间聚合事件,可按 domain 过滤)。
- `GET /api/formation/state` — 当前焦点画像。
- `GET /api/formation/next` — 节律引擎给出「今日 1–2 件该做的事」。
- `POST /api/formation/rule` / `GET /api/formation/rule` — 生活规则增改查。

### 5.3 生活规则(Rule of Life)
- **`rule_of_life`** 表:`{user, practice, cadence(daily/weekly/…), linked_focus(对应偶像/主题), scripture, active}`。
- 仪表盘显示每条规则的**连续天数/完成率**;操练完成回写 `formation_events`(practice)。

### 5.4 节律引擎
- 输入:`growth_state` + `rule_of_life` + 各操练 recency。
- 规则:当前焦点(如「骄傲」)→ 推荐对应美德操练 + 反谎言祷告 + 相关经文 + 复盘提醒;
  到期的生活规则优先;危机旗标 → 只出关怀,不出分析。
- 落地:直接复用 orchestrator 的 `recommendedNextAgents` + 已有定时任务能力,产出「今日该做」。

### 5.5 UI:让「灵镜 / SoulDashboard」成为真正的首页
- **今日**:节律引擎推荐的 1–2 件事(操练/复盘/经文)。
- **时间轴**:神的带领(formation_events 聚合,可点开任一节点回看)。
- **当前焦点**:偶像/主题/成长焦点 + 圣经一致性趋势。
- **生活规则**:各操练进度条。

### 5.6 分期实施
- **Phase 0**:落 `formation_events` 规范 + 让现有引擎/路由统一 emit(多数已有 audit,改造量小);建 `growth_state` 聚合器。
- **Phase 1**:`/timeline` + `/state` + SoulDashboard 时间轴与焦点卡。
- **Phase 2**:`rule_of_life` + 仪表盘进度。
- **Phase 3**:节律引擎 `/next` + 定时推送。
- **并行**:推进 §3 诊断内核收敛(减少事件生产者、统一本体),与 Phase 0 互为支撑。

---

## 6. 建议次序(总)

1. **收敛诊断内核 + reframe 服务**(§3 前两项)——降负债、统一本体。
2. **Phase 0–1 整合层**(§5)——把闭环合上、给用户一个统一首页。
3. **生活规则 + 节律引擎**(§5.3–5.4)——从「记录」走向「带领」。
4. 再视情况补**牧者后台 / 小组层 / 成效度量**。

> 一句话:**先合并、再合拢**——合并重复的诊断/重写/反思,合拢成一个统一成长闭环。新模块不是当务之急。
