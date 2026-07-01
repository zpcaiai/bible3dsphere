# 🔒 EXPANSION CLAIM — 内容与神学扩充批次（协调用，勿删）

> 给并行进程的协调说明。本批次（content-theology-expansion）**只新增文件**，
> 与并行进程（church_health 后端 + features/spiritual-formation 前端）尽量零重叠。
> 状态：**后端已完成并通过引擎级测试**；前端待定（见文末重叠说明）。日期：2026-07-01

## ✅ 后端已交付（全部 py_compile + 引擎测试通过）
迁移号 **0130–0141**（已让开并行进程的下一号）。均 email-keyed、幂等、确定性优先 + AI 可选回退。

| 迁移 | 引擎 | 路由(文件 / 前缀 / 主POST) | 表 |
|---|---|---|---|
| 0130 | lament_engine | routers/lament.py · /api/lament · /compose | lament_entries |
| 0131 | affections_engine | routers/affections.py · /api/affections · /assess | affections_entries |
| 0132 | ordo_amoris_engine | routers/**ordo_amoris_augustine**.py · /api/ordo · /analyze | ordo_amoris_entries |
| 0133 | tender_heart_engine | routers/tender_heart.py · /api/tender · /comfort | tender_heart_entries |
| 0134 | formation_liturgy_engine | routers/formation_liturgy.py · /api/liturgy · /analyze | formation_liturgy_entries |
| 0135 | spirits_engine | routers/spirits.py · /api/spirits · /discern | spirits_entries |
| 0136 | union_engine | routers/union.py · /api/union · /assess | union_entries |
| 0137 | delight_engine | routers/delight.py · /api/delight · /reframe | delight_entries |
| 0138 | emotionally_healthy_engine | routers/emotionally_healthy.py · /api/eh · /assess | eh_entries |
| 0139 | contentment_engine | routers/contentment.py · /api/contentment · /analyze | contentment_entries |
| 0140 | know_god_engine | routers/**knowgod**.py · /api/knowgod · /meditate | know_god_entries |
| 0141 | (expansion_content.py) | routers/expansion_resources.py · /api/resources | resource_bookmarks |
| 0142 | renovation_engine | routers/renovation.py · /api/renovation · /assess | renovation_entries |
| 0143 | chinese_devotion_engine | routers/chinese.py · /api/chinese · /meditate,/search | chinese_devotion_entries |

聚合器：`routers/expansion_pack.py`（动态导入 12 子路由 + `init_expansion_pack`，单个失败不影响其余）。
测试：`backend/tests/test_expansion_pack.py`（7 项，stdlib 可跑；CI/.venv 走 pytest）。

## ⚠️ 我对既有热点文件的唯一改动
`backend/main.py`：**仅文件末尾一处**带标记 `# === EXPANSION PACK (content-theology-expansion) ===`
的幂等 try 块（import + init + include_router）。未改中段、未碰 church_health。

## 已知命名避让（重要）
- `routers/ordo_amoris.py` **已被既有功能占用**（爱之秩序星图，/api/ordo-amoris，表 ordo_amoris_records，
  已在 main.py 注册）。本批次的奥古斯丁版改名 **`ordo_amoris_augustine.py`**（/api/ordo，表 ordo_amoris_entries），
  未触碰既有文件。
- know_god 路由文件名为 **`knowgod.py`**（匹配 /api/knowgod）。

## 请并行进程避免
- 勿占用迁移 0130–0143；勿新建上表同名 `*_engine.py`；保留 main.py 末尾我的标记块。

## ✅ 前端已交付（自包含，只覆盖不重叠模块）
用户定案「只做不重叠的、自包含」。**未触碰** `PlanetHome.jsx` / `SoulDashboard.jsx` / `src/api.js` /
`features/spiritual-formation/*`（这些是并行进程的客户端灵修引擎：crossLamentHope/ordoAmoris/ruleDiscernment）。

新增（全在自有命名空间 `src/expansion/`）：
- `src/expansion/expansionApi.js`（自包含 API 助手，只读引用 `../auth` 的 getToken，不改 api.js）
- `src/expansion/ExpansionHub.jsx`（聚合面板：8 个不重叠模块 + 推荐书目/圣诗，通用结果渲染器）
- `src/expansion/ExpansionLauncher.jsx`（自挂载悬浮入口 📖，幂等）

覆盖的 8 模块（跳过 lament/ordo/spirits——前端归并行进程）：认识神(knowgod) · 与基督联合(union) ·
以神为乐(delight) · 基督徒知足(contentment) · 温柔谦卑(tender) · 文化礼仪(liturgy) ·
情感真伪辨(affections) · 情感健康属灵(eh) · 推荐书目/圣诗(resources)。

对既有文件的唯一改动：`src/main.jsx` 末尾**一行**幂等动态 import（改前该文件是干净的）。
全部 4 文件经 @babel/parser 校验 JSX 语法有效。

## 合并须知
- 后端 `main.py`、前端 `main.jsx` 是我与你的**唯一共享改动点**（均为末尾追加/一行，带标记，可安全合并或摘出）。
- 若并行进程的客户端 lament/ordo/discernment 要改用服务端，可直接调我的 `/api/lament`、`/api/ordo`、`/api/spirits`。

## ➕ 追加交付（本轮）
- **深链开启**：`ExpansionLauncher` 暴露 `window.__expansionOpen(featureKey)`；`ExpansionHub` 支持 `initialFeatureKey`；哀歌已加回 hub。
- **PlanetHome 大陆入口（延迟接线，不碰他们在改的 PlanetHome.jsx）**：`src/expansion/planetEntries.js` + `docs/EXPANSION_PLANETHOME_WIRING.md`。默认挂 与基督联合/基督徒知足/哀歌 三入口，用 `exp:` 前缀经 `window.__expansionOpen` 绕过既有 `go()`。合并后照贴 3 行即生效。
- **12 端点对接**：`src/expansion/expansionEndpoints.js`（50 导出，api.js 风格）+ `docs/EXPANSION_API.md`。他们前端可直接 import 调用我的服务端引擎。

## 🌐 中文|EN 双语（本轮）
- 新增 `src/expansion/expansionI18n.js`：约 60 条 UI 文案的中英词典，用 runtime 导出的 `setEnEntry` 在加载时**预置英文**（**不触碰他们在改的 `i18n/auto-en.js`**）。
- `ExpansionHub.jsx` / `ExpansionLauncher.jsx`：静态文案包 `i18nT('中文')`（EN 模式命中预置英文，漏词由全站 auto-translate 兜底）；动态后端内容（经文/祷文/框架/危机提示/书目简介/结果值）包 `<Translatable>`（EN 模式出现「翻译」按钮，与 App.jsx 处理 guidance 一致）。
- PlanetHome chip 标签经其既有 `i18nT(label)` + 我的预置词典自动双语，无需额外改动。
- 全站语言切换整页刷新即生效；6 个前端文件均通过 `@babel/parser` 校验。

## ➕ 补齐（本轮：#3/#6/#7/#8 全部落地）
- **魏乐德「心意更新」** `renovation_engine`（VIM × 心思/意志/身体/社会/灵魂 五维自评）— 迁移 0142，/api/renovation。
- **华人本土灵修** `chinese_devotion_engine`（倪柝声/王明道/唐崇荣/宋尚节 思想**中文摘述**+教义分辨+可检索/默想）— 迁移 0143，/api/chinese。均已加入聚合器与测试（8/8 通过）。
- **前端 hub 现覆盖 14 个模块**：新增 失序之爱(ordo)、诸灵分辨(spirits)、心意更新(renovation)、华人本土灵修(chinese)。
  - ⚠️ 应用户要求，ordo/spirits 现已进 hub —— 与并行进程客户端 `ordoAmoris`/`ruleDiscernment` 主题重叠，合并时如需去重由你/他们定夺（删 hub 里这两个 FEATURES 项即可）。
