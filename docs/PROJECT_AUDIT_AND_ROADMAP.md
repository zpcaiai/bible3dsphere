# 属灵星球 / 属灵感知系统 — 全面体检与改进路线图

> 体检范围：前端 ~22,500 行（9 个底部 Tab + 多入口）、后端 formation/graph/MVFE/
> discernment/idolatry/waiting 等引擎。评估维度：功能合理性、逻辑闭环、UI/UX、工程质量、
> 灵修进深的新功能空间。标注：✅ 良好 ｜ ⚠️ 可改进 ｜ ❌ 缺口。

---

## 一、总体印象

项目非常有野心也很完整：从 3D 情绪球、人物镜鉴、讲道笔记、宣教地图、代祷诗歌、灵修书库、
到心迹（决策/人格/操练/偶像监测/等候之路）、圣徒相通（好友+语音），覆盖了「认识情绪 →
辨识内心 → 操练成长 → 群体相通」的全链路。核心引擎（formation 八维、graph 回路、MVFE）
设计有学术深度（PAPER.md / HIDOS）。

**最大的结构性问题不是缺功能，而是：(1) 功能太多、导航碎片化，进深路径不清晰；
(2) 各子系统是「数据孤岛」，没有回流到统一的属灵成长档案，HIDOS 闭环没真正闭上；
(3) 缺日常节奏引擎（提醒/连续性），灵修「进深」缺少持续的推力。**

---

## 二、功能盘点与逻辑闭环评估

| Tab / 模块 | 现状 | 评估 |
|---|---|---|
| 情绪球 (sphere) | 3D 情绪可视化 + 选词 → 经文/牧养 | ✅ 亮点；⚠️ 作为落地页对新用户偏重、上手门槛高 |
| 镜鉴 (mirror) | 231 位人物效法/警戒 | ✅ 内容扎实；⚠️ 与「我的处境」无关联，纯浏览 |
| 分享 / 主日 / 代祷 | 墙 + 讲道笔记 + 诗歌 | ✅ 功能闭环；⚠️ 之间无串联 |
| 宣教 | 圣经地图 + 慕道班 | ✅ 内容好 |
| 灵修 | 今日灵修 + 书库 + 日记 | ✅ 核心；❌ 无读经计划/连续性/提醒 |
| 心迹 | 今日心镜 + 人格 + 操练 + 偶像监测 + 等候之路 | ✅ 最深；❌ 新两模块**不回流 formation/graph** |
| 相通 | 好友 + 1对1聊天/语音 | ✅ 技术强；⚠️ 未用于「灵修问责」等属灵场景 |

**逻辑闭环关键缺口 ❌**：`idolatry_engine` 与 `waiting_engine` 只**读**信号、不**写**
formation 事件，所以「今日心镜」的八维属灵概览、灵命图谱、回路检测**看不到**偶像监测/
等候之路的洞察。整个 HIDOS「五层塑造」承诺的反馈闭环在这两个新模块上是断的。

**其它闭环/数据问题**：
- ⚠️ 今日心镜常显示「⚡ 预览数据」(is_mock)，新用户看到的是 mock，削弱信任。应改为
  诚实的空状态 + 引导首登记。
- ⚠️ HabitsPage 有 streak 概念，但**没有提醒/推送**，习惯回路缺少外部推力。
- ⚠️ 镜鉴人物、讲道笔记、代祷都与「我当前的情绪/处境/决策」无智能关联，错失个性化进深。

---

## 三、UI / UX 评估

- ✅ 统一深色玻璃拟态、配色克制、文案温柔（尤其两新模块「不定罪」基调做得好）。
- ❌ **导航模型碎片化**（最大 UX 问题）：9 个底部 Tab + 8 个仪表盘快捷入口 + 子 Tab +
  卡片入口 + overlay，五套并存。功能很多但**发现性差**、心智负担重。建议引入「今日」聚合
  首页 + 清晰的「进深路径」。
- ⚠️ **可访问性**：大量 10–11px、opacity 0.3–0.45 的灰字在纯黑底上，对比度低于 WCAG AA；
  老年/弱视用户（属灵陪伴的重要人群）阅读吃力。
- ⚠️ **设计无 token**：颜色/间距/圆角全是 inline 魔法值，难以统一与维护。
- ⚠️ 入口不一致：同在「心迹」，决策/人格是子 Tab，偶像监测/等候之路是仪表盘卡片。

---

## 四、工程质量

- ⚠️ **God-component**：App.jsx 2995 行、DecisionSupportPage 1841、PersonalityPage 1478。
  panel 路由、登录态、弹窗全堆在 App.jsx，维护/协作风险高。建议抽 `PanelRouter` + hooks。
- ❌ **测试覆盖缺口**：`tests/test_routers_compile.py` 覆盖 stats/verse/journal/prayer，
  但**未覆盖 idolatry/waiting**（今天新增）。引擎也无单测。
- ⚠️ **PWA 不完整**：有 sw.js（资产 cache-first），但无离线数据、无 Web Push。对「每日
  灵修陪伴」类应用，推送/提醒是留存核心。
- ⚠️ **数据导出/隐私**：用户的日记/祷告/省察是高度私人的属灵数据，目前无「导出我的数据」
  与隐私说明；信任与合规上建议补齐。
- ✅ 迁移机制规范（编号 SQL、Neon 生效）、安全头/CORS/限流齐全。

---

## 五、灵修进深 — 新功能路线图（按 影响 × 成本 排序）

### P0（高影响 / 成本中，建议优先）
1. **统一「属灵成长档案」闭环** ❌闭环修复：让 checkin 情绪、偶像监测、等候之路、操练、
   省察都写 formation 事件 → 八维/图谱/回路真正反映全部洞察 + **每周「牧养小结」**
   （AI 综合一周数据，温柔生成「神这周在你身上做的工 / 一个邀请」）。这是把孤岛连成
   系统的关键，也最「进深」。
2. **每日节奏引擎 + 提醒（Web Push）** ❌缺口：晨更/晚祷/操练打卡的定时提醒 + 连续天数 +
   断签温柔挽回。习惯回路真正闭合，留存与进深的第一推力。

### P1（高影响 / 成本中）
3. **每日省察 Examen（依纳爵式）**：回顾今天的「安慰/枯涩」(consolation/desolation)，
   感恩一件、求恕一件、明日一个微顺服。直接喂入成长档案，是公认最有效的进深操练。
4. **读经计划**：结构化计划（麦琴 / 福音书 90 天 / 恩典之路）+ 进度 + 与「通读」区分。
5. **背经 / 经文记忆（间隔重复 SM-2）**：把经文长入心里，formation 价值极高，技术轻。

### P2（锦上添花 / 成本低-中）
6. **教会历 / 属灵节期**：将临期、大斋期、复活期主题灵修，给一年节奏。
7. **认罪与赦免**：引导式认罪 + 赦免的确据，与偶像监测天然成对。
8. **灵修问责同伴**：复用「相通」好友，设共同目标 + 互相看见进度（非监视、是同行）。
9. **感恩 / 数算恩典日记**：极简、高留存、正向。
10. **离线灵修 + 我的数据导出**：弱网可读、私人数据可带走。

---

## 六、建议的执行顺序

1. **先补质量地基**（半天级）：给 idolatry/waiting 加路由 smoke 测试 + 引擎单测；
   今日心镜 mock → 诚实空状态。
2. **P0-①闭环**：两新模块 + checkin 回流 formation；周度牧养小结。（系统价值最大）
3. **P0-②节奏引擎 + Web Push 提醒**。（留存价值最大）
4. 之后按 P1 → P2 迭代。

> 说明：本路线图不动现有数据结构，新增均走 `migrations/00NN_*.sql`；前端沿用现有
> React + 深色玻璃风，逐步引入设计 token 与「今日」聚合首页以缓解导航碎片化。

---

## 七、本轮已实施（2026-06-01）

- ✅ **质量地基**：`tests/test_routers_compile.py` 增 idolatry/waiting/pastoral/examen/push 路由
  smoke 测试；新增 `test_idolatry_engine.py` / `test_waiting_engine.py`（12 例全过）；
  今日心镜 `is_mock` → 诚实空状态。
- ✅ **闭环整合**：`formation_bridge.py` + 两引擎 `formation_signal`，偶像监测/等候之路/
  每日省察的洞察均回流 formation 八维；`pastoral_engine.py` + `/api/pastoral/weekly`
  「本周牧养小结」，今日心镜展示。
- ✅ **每日省察 Examen**：迁移 0024 + `routers/examen.py` + `ExamenPage.jsx`，依纳爵式
  安慰/枯涩→感恩→求恕→明日微顺服，回流 formation，今日心镜入口。
- ✅ **节奏引擎 + Web Push**：迁移 0025 + `routers/push.py` + `ReminderSettings.jsx` +
  `sw.js` push/notificationclick 处理；晨更/晚祷定时提醒。
- ✅ **麦琴每日推送**：迁移 0222 + `mccheyne_push.py`；按上海时间每日 08:00
  向已授权的 Web Push / FCM 设备发送当天四处经文、简短查经指引和逐章查经深链，
  并按设备/日期幂等记录，失败由下一轮调度重试。

### Web Push 部署须知（上线提醒功能需配置）
1. 生成 VAPID 密钥：`npx web-push generate-vapid-keys`
2. 后端环境变量：`VAPID_PUBLIC_KEY`、`VAPID_PRIVATE_KEY`、
   `VAPID_SUBJECT=mailto:you@example.com`、`PUSH_CRON_SECRET=<随机串>`
3. 依赖：`pywebpush`（已加入 requirements.txt）
4. 定时触发：`.github/workflows/keepalive.yml` 每 10 分钟调用
   `POST /api/push/run-due`，请求头 `X-Cron-Secret: <PUSH_CRON_SECRET>`；GitHub
   仓库 Secret `PUSH_CRON_SECRET` 必须与后端环境变量同值。麦琴推送在 08:00 后
   的首次成功调用发送，GitHub 调度延迟时会顺延，但不会重复发送。
5. 未配置 VAPID 时，提醒相关接口返回 `configured:false`，前端给出说明，**应用其余部分不受影响**。

> 迁移 0021–0025 会在 push 到 main 后于 Neon 生效。

---

## 八、P1 已实施（读经计划 + 背经）

- ✅ **读经计划**：迁移 0026（reading_plan_enrollment / reading_plan_progress）+
  `routers/reading.py`（报名 / 进度 / 连续天数）+ `readingPlans.js`（麦琴365·复用
  public/mccheyne.json，约翰福音21天，诗篇30天）+ `ReadingPlanPage.jsx`（计划切换 +
  今日经文 + 进度环 + streak）。入口：**灵修 tab 新子 tab「📅 读经计划」**。
- ✅ **背经 SM-2**：迁移 0026（memory_verses）+ `sm2_engine.py`（纯函数，1→6→15 天推进、
  忘了归零、ease 下限 1.3）+ `routers/memory.py`（add/due/list/review/delete）+
  `MemoryVersePage.jsx`（复习「先回想再翻看」+ 四档评分 / 我的 / 添加）。入口：
  **灵修 tab 新子 tab「🧠 背经」**。
- 测试：sm2 单测 3 例 + reading/memory 路由 smoke；引擎单测累计 15 例全过。
- 迁移 0026 push 到 main 后于 Neon 生效。

---

## 九、P2 已实施（路线图收官）

统一入口：今日心镜「✦ 灵修操练」一张卡 → `PracticeHubPage`（五合一），缓解导航碎片化。

- ✅ **感恩日记**：迁移 0027 + `routers/gratitude.py`（add/list/delete，回流 formation）。
- ✅ **认罪与赦免**：`routers/confession.py` —— **不存储正文（隐私）**，仅回流 formation +
  返回随机「赦免确据」经文；前端 4 步引导（安静→省察→认罪→舍弃）→ 领受赦免。
- ✅ **教会历**：`churchCalendar.js` 纯计算（复活节 Meeus 算法 + 将临/圣诞/大斋/受难周/
  复活/五旬节/常年期），展示当前节期主题 + 经文。
- ✅ **灵修问责**：迁移 0027（accountability_goals + checkins）+ `routers/accountability.py`
  （目标 / 打卡 / 连续天数，回流 formation）。
- ✅ **我的数据导出**：`routers/export.py` `/api/export/me` 聚合 checkin/日记/省察/感恩/
  偶像/等候/背经/读经/问责 → 前端一键下载 JSON。

测试：gratitude/accountability/confession/export 路由 smoke 已加。迁移 0027 push 后生效。

> 路线图 P0/P1/P2 至此全部落地。后续可考虑的「大」项：导航信息架构重构（把分散入口
> 收进统一「操练中心 / 今日」）、设计 token 化、离线数据缓存、可访问性对比度提升。
