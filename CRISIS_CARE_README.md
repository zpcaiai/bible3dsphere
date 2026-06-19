# 危机守护子系统（Crisis Care Subsystem）

属灵星球的危机状态识别 + 心理急救 + 属灵陪伴 + 人工/专业资源转介子系统，与「模式库」并列，
作为「心迹」导航里的一个一级 Tab（`危机守护` 🆘），并提供常驻的「我现在撑不住了」醒目入口。

定位：**不是 AI 心理治疗师**。核心顺序贯穿全系统：

> **Safety 安全 > Stabilization 稳定 > Connection 连接 > Meaning 意义 > Formation 成长**
> 先保命 → 再稳定 → 再陪伴 → 再属灵重建。

---

## 1. 安全红线（贯穿前后端）

- **不诊断、不预测、不保证、不替代** 咨询师 / 急救 / 教会 / 牧者。
- **Red 规则优先于任何 LLM 判断**；红色绝不进入普通灵修建议、反思题或长日志。
- **任何模糊的自伤/自杀表达 ≥ orange**；系统绝不输出「你没有风险 / 你没事」。
- LLM 与历史趋势 **只能抬高** 风险等级，永不降低。
- 守护人通知必须 **预授权（consent）**，可随时撤销，且记录审计。
- 危机话术 **禁语表**（`FORBIDDEN_PHRASES`）：如「你就是信心不够」「自杀是罪」「你不够属灵」等，
  已用单元测试保证属灵安慰文案不含这些话。

---

## 2. 架构总览

```
User Input
  → TriageAgent（分级 green/yellow/orange/red + 风险类型）
     ├─ green  → 普通陪伴（回到 Guardian / 灵修）
     ├─ yellow → 关怀 + 稳定 + 属灵安慰
     ├─ orange → SafetyCheck 安全确认 → 安全计划 + PFA + 守护人 + 热线
     └─ red    → 紧急升级：停止普通对话 → 三步行动 + 复制求助文本 + 当地热线 + 守护人提醒
  → PostCrisisAgent（24h/72h/7d/30d 恢复跟进）
```

后端沿用本仓库既有的「engine（纯逻辑）+ router（FastAPI）+ schema.sql」三段式约定，
并 **复用** `guardian_engine.SafetyGuard` 作为底层兜底（只抬高、不降级）。

---

## 3. 后端文件（仓库 `bible3dsphere`）

| 文件 | 作用 |
| --- | --- |
| `backend/crisis_engine.py` | 纯逻辑层。9 个 Agent + 多地区资源 + 触发分级。无 IO。 |
| `backend/crisis_schema.sql` | 4 张表：`crisis_events` / `crisis_safety_plans` / `crisis_guardian_contacts` / `crisis_followups`。 |
| `backend/routers/crisis.py` | FastAPI 路由 `/api/crisis`（23 个端点），含 `init_crisis_router` 注入 + 启动建表。 |
| `backend/tests/test_crisis_engine.py` | 危机模拟测试集（36 用例，含规格书 6 个 Case + 红标记/降级保护/多地区/禁语）。 |
| `backend/main.py` | 已注册：import + `init_crisis_router(...)` + `app.include_router(crisis_router)`。 |

### 9 个 Agent（`crisis_engine.py`）

1. **TriageAgent** `triage()` — 规则 guard + 可选 LLM（只抬高）。强标记（已获取工具/正在行动）无条件 Red；
   情境标记（如「准备好了」歧义）需与自伤/医疗急症并存才 Red。
2. **SafetyCheckAgent** `safety_check_step()` — 直接、温柔、每次只问一个问题的状态机。
3. **PFAAgent** `grounding_54321()` / `breathing_guide()` / `pfa_stabilize()` — 心理急救（Look/Listen/Link）。
4. **SafetyPlanAgent** `build_safety_plan()` — Stanley-Brown 结构 + 属灵锚点 + 当地资源 + 复制文本。
5. **EscalationAgent** `red_emergency_message()` / `guardian_alert_text()` — 红色升级 + 守护人提醒文本。
6. **SpiritualCareAgent** `spiritual_comfort()` / `detect_spiritual_crisis()` — 低压安慰 + 责备/控告分辨表。
7. **AddictionAgent** `ten_minute_delay()` + `HALT_PROMPT` — 成瘾复发 10 分钟延迟。
8. **TraumaAgent** `trauma_grounding()` — flashback/解离的 grounding，不逼回忆、不做暴露。
9. **PostCrisisAgent** `post_crisis_tasks()` — 24h/72h/7d/30d 恢复路径。

### API 端点（`/api/crisis`）

```
POST /triage                 分级（记录 crisis_events，orange/red 附资源、red 附紧急文案）
POST /safety-check           安全确认状态机推进
GET  /resources?locale=      按 locale 返回当地热线
GET  /safety-plan/template   安全计划模板
GET/POST /safety-plan        读取/保存安全计划（单一 active，历史归档）
GET/POST/PUT/DELETE /guardians[/{id}]   守护人 CRUD
POST /escalate               红色升级文本 + 守护人提醒（需 consent 才生成通知）
GET  /comfort?type=&message= 属灵安慰
GET  /pfa  /trauma  /addiction  /post-crisis     稳定/创伤/成瘾/恢复脚本
GET/POST/PUT /followups[/{id}]   危机后跟进
GET  /events   POST /events/{id}/ack   DELETE /events/{id}   个人审计（可删除）
GET  /meta                   元数据（风险类型/分辨表/禁语/免责声明）
```

---

## 4. 前端文件（仓库 `bible3dsphere-frontend`）

特性目录 `src/features/crisis-care/`，镜像 `spiritual-formation` 的结构（本地优先 + 后端同步）：

```
types/crisis.ts                 共享类型
data/crisisResources.ts         多地区资源（离线兜底，含 resolveRegion）
data/crisisContent.ts           安慰经文 / 分辨表 / 安全计划模板 / 恢复任务 / 禁语
lib/api.ts                      /api/crisis 客户端（全部可优雅降级）
lib/triage.ts                   客户端分级兜底（后端不可用时仍能分流，保守往高判）
lib/storage.ts                  本地优先存储（安全计划 + 守护人）
components/                     12 个组件（见下）
app/CrisisCarePage.jsx          编排页（9 个内部 Tab）
app/crisis-care.css            低刺激、慢节奏的视觉
__tests__/                      triage / SoulTabs / 整页 smoke（16 用例）
```

组件：`CrisisHelpButton`（常驻入口）、`CrisisIntakeFlow`（撑不住了入口+分流）、
`SafetyCheckFlow`、`BreathingGuide`（4-1-6）、`GroundingExercise`（5-4-3-2-1）、
`CrisisResourcePanel`（tel: 一键拨打）、`SafetyPlanEditor`、`GuardianNetworkManager`（含 consent）、
`SpiritualComfortCard`、`AddictionDelayFlow`（HALT + 10 分钟倒计时）、`TraumaGroundingFlow`、
`PostCrisisTimeline`、`EmergencyEscalationPanel`（红色三步 + 复制求助文本）。

### 接线点

- `src/components/SoulTabs.jsx` — 新增 `{ key: 'crisis', label: '危机守护', emoji: '🆘' }`（紧跟「模式库」）。
- `src/DecisionSupportPage.jsx` — `activeTab === 'crisis'` 渲染 `<CrisisCarePage>`；
  并常驻 `<CrisisHelpButton>`（除危机页本身外，任一 Tab 都可一键进入）。

---

## 5. 多地区危机资源（已核验，2025/2026 现行）

`locale → region` 自动解析（`resolveRegion`），未知回退台湾，并可在面板里手动切换地区。

| 地区 | 关键资源（部分） |
| --- | --- |
| 台湾 TW | **1925** 安心專線（24h，卫福部）· **1995** 生命線 · 1980 張老師 · 119 |
| 中国大陆 CN | **12356** 全国统一心理援助热线 · 北京危机干预中心 **010-82951332** · 120 |
| 香港 HK | 撒瑪利亞防止自殺會 **2389 2222** · English 2389 2223 · 999 |
| 美国 US | **988** Suicide & Crisis Lifeline（call/text）· Crisis Text Line **741741** · 911 |
| 其他 INTL | 当地紧急电话 · findahelpline.com |

> 号码已通过官方/权威来源核验（见提交说明）。请在上线前按运营区域再次复核，并在后台开放配置。

---

## 6. 测试与验证

- 后端：`cd backend && pytest tests/test_crisis_engine.py`（36 用例通过）。涵盖规格书 6 个 Case、
  红标记优先、降级保护（LLM/历史只抬高）、多地区号码、禁语过滤、状态机、安全计划必备真人联系人。
- 前端：`npx vitest run src/features/crisis-care`（16 用例通过）+ 既有 SoulTabs 导航测试未回归。
- 生产构建：`vite build` 全量 2123 模块转译通过，危机守护代码已打入 `DecisionSupportPage` chunk。

---

## 7. MVP 优先级落地情况

- **P0（已实现）**：Triage / SafetyCheck / Red 紧急流 / 安全计划 / 多地区资源 / 守护人基础版 / 审计日志。
- **P1（已实现）**：PFA 稳定 / 属灵危机安慰 / 成瘾复发 / 创伤 grounding / 24h–30d 跟进 / 安慰经文库。
- **P2（预留接口，建议后续）**：
  - 与「模式库」(`spiritual-formation`) 联动：危机后 30 天导入罪模式/恩典恢复（已在恢复页文案中埋点）。
  - 与门训 / Healing Skills 联动。
  - 守护人 **真实通知通道**（SMS / push / 微信）：现已生成通知意图 + 文本并写审计，
    发送通道建议复用本仓库 `routers/push.py` 或外部短信服务，落地前务必再次校验 consent。
  - 牧者 / 小组长 / 咨询师协作后台视图。
  - 危机前兆预测：仅作提醒，绝不作为诊断或「低风险=没事」的依据。

---

## 8. 一句话架构

> TriageAgent 识别危险；SafetyCheck 负责保命；PFA 负责稳定；Guardian 连接真人；
> SpiritualCare 给不伤人的属灵安慰；PostCrisis 负责危机后的恢复与成圣成长。
> 在用户最危险、最羞耻、最绝望的时候，系统不讲大道理、不继续灵修任务，
> 而是快速把人带向 **安全、真人、专业资源和温柔的属灵盼望**。

---

## 9. 第二轮增量（守护人短信通道 / 模式库桥接 / 协作后台）

三项均已落地、跑通测试与构建，并遵循同样的安全红线（明确授权、可撤销、可审计、不带控告）。

### 9.1 守护人短信通道（Guardian SMS）
- `backend/notify.py` — 可插拔发送器：**Twilio SMS → 通用 webhook → 记录意图** 三级降级。
  没配凭据时返回 `not_configured`，只记录意图、绝不泄露，不影响功能。
- `/api/crisis/escalate` 现在对「已授权且权限覆盖该等级」的守护人**真实发送短信**，
  把每条投递状态写入 `crisis_events.escalation_actions`，并回传 `channelConfigured / anyDelivered`。
- 前端守护人页会显示「已通过短信提醒 N 位 / 通道未配置请直接拨打热线」等状态。
- 配置：`.env.example` 新增 `TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN/TWILIO_FROM_NUMBER`、`CRISIS_NOTIFY_WEBHOOK_URL`。

### 9.2 危机后 → 模式库桥接
- `crisis_engine.formation_seed(risk_types)` + `POST /api/crisis/bridge/formation-seed` —
  从近期危机风险**温柔地**建议一个转化计划「种子」（默认 `spiritual_numbness`、30 天、轻强度）。
  **红线**：绝不暗示「危机本身 = 罪」；种子可改、可不开始（文案与测试都守住这一点）。
- 前端 `lib/formationBridge.ts` 复用 spiritual-formation 自己的 `generateTransformationPlan` +
  `createTransformationPlanRemote` 创建计划（确保 user_id 正确），危机后页一键「导入模式库」并跳转。

### 9.3 牧者/咨询师协作后台
- 新表 `crisis_care_shares`（明确授权、按 scope、可撤销、查看留痕）。
- 端点：`POST/GET/DELETE /api/crisis/shares`（当事人授权/撤销）、
  `GET /api/crisis/caregiver/shares`、`GET /api/crisis/caregiver/shares/{id}`（牧者/咨询师只读查看，按 email 匹配登录身份）。
- 前端「协作」Tab（`CollaborationConsole.jsx`）：当事人管理分享 + 牧者/咨询师查看只读摘要
  （当前状态 / 安全计划 / 近期事件，按对方勾选范围）。强调**陪伴而非审判**。

### 新增/改动文件
- 后端：`backend/notify.py`(新)、`backend/crisis_engine.py`、`backend/routers/crisis.py`、
  `backend/crisis_schema.sql`、`backend/tests/test_crisis_engine.py`、`.env.example`。
- 前端：`features/crisis-care/lib/formationBridge.ts`(新)、`components/CollaborationConsole.jsx`(新)、
  `lib/api.ts`、`components/PostCrisisTimeline.jsx`、`app/CrisisCarePage.jsx`、`DecisionSupportPage.jsx`。

### 验证
- 后端 `pytest tests/test_crisis_engine.py`：**39 passed**（含 formation_seed 非控告 + notify 降级）。
- 前端 `vitest src/features/crisis-care`：**18 passed**（含模式库导入入口 + 协作 Tab）。
- `vite build`：clean 构建通过，三项均已打入 bundle。

> 上线前务必：填入 Twilio/webhook 凭据并按地区复核热线；对 caregiver 协作做一次隐私/合规评审
> （建议加入查看审计的后台展示，以及对 `CRISIS_CAREGIVER_ROLES` 的收紧）。

---

## 10. 第三轮增量（微信模板消息 / 牧者独立入口 / 协作隐私加固）

### 10.1 微信模板消息通道（优先于短信）
- `backend/notify.py` 重构为统一分发 `send_notification(methods, phone, wechat_openid, body)`：
  **微信模板消息 → Twilio 短信 → 通用 webhook → not_configured**，按守护人 `notify_methods` 选通道。
- 微信走 `WX_APP_ID/WX_APP_SECRET`（已有）+ 新增 `WX_CRISIS_TEMPLATE_ID`，access_token 带内存缓存；
  守护人需有 `wechat_openid`（前端守护人表单已加「通知方式：微信/短信」+ openid 字段，schema 用
  `ALTER TABLE ... ADD COLUMN IF NOT EXISTS wechat_openid`）。
- 模板需在公众号后台预建，字段 `first/keyword1/keyword2/remark`。未配置时仍优雅降级、只记录意图。

### 10.2 牧者/咨询师独立登录入口
- 独立路由 **`/caregiver`**（`App.jsx` pathname 路由，仿 `/seekers`）→ `CaregiverConsolePage`。
- 未登录复用 `LoginScreen`；登录后只读查看「分享给你的人」（复用抽出的 `CaregiverInbox` 组件）。
- 身份按**登录邮箱**匹配（`users.email` 唯一、注册时邮箱验证码已验证），会话由服务端解析，防冒名。

### 10.3 协作隐私加固
- **查看审计**：新表 `crisis_share_views` 记录每次牧者查看（share/ sharer / caregiver / 时间）；
  当事人「我分享给谁」列表显示「已被查看 N 次（最近 …）」。
- **角色收紧**：`CRISIS_CAREGIVER_ROLES` 环境变量（默认 `pastor,counselor,small_group_leader`）约束可授权角色。
- **未注册提示**：授权时检测对方邮箱是否已注册 `users`，未注册则标「未注册」并提示对方需先用该邮箱注册登录。

### 安全说明（务必人工完成的部分）
- **凭据需你来填**：`.env` 里的 Twilio / 微信 / webhook 是占位符，我不会、也不应代填真实密钥。
- 上线前建议：(1) 对 `/caregiver` 协作做一次隐私/合规评审；(2) 如需更强匿名化，可对 sharer 邮箱做脱敏展示；
  (3) 确认登录邮箱唯一且已验证（当前 `users.email UNIQUE` + 注册验证码已满足，但请按你们流程复核）。

### 第三轮验证
- 后端 `pytest`：**40 passed**（含 notify 通道降级）。
- 前端 `vitest src/features/crisis-care`：**17 passed**（含微信/短信通道 UI + 牧者收件箱）。
- `vite build`：clean 通过；`/caregiver` 独立 chunk 已生成，微信字段与协作台均已打包。

---

## 11. 第四轮调整（移除微信 + 牧者「一键回拨/发起关怀」）

### 11.1 移除微信（wx）
- `notify.py` 回退为 **Twilio SMS → 通用 webhook → not_configured** 两级通道（不再含微信模板消息）。
- 一并移除：`crisis_guardian_contacts.wechat_openid`（schema 不再 ALTER 该列）、`GuardianBody.wechatOpenid`、
  守护人表单的「通知方式/微信 openid」字段、`.env` 的 `WX_CRISIS_TEMPLATE_*`。
- 说明：应用既有的 `WX_APP_ID/WX_APP_SECRET`（微信**登录**用）未改动，只移除危机通知里的微信模板消息。

### 11.2 牧者协作台「一键回拨 / 发起关怀」
- 当事人授权分享时可选填**回拨电话** `contactPhone`（schema `ALTER ... ADD contact_phone`）。
- 牧者/咨询师在「分享给我的人」与只读摘要里看到：
  - **📞 一键回拨**：`tel:` 直接拨打当事人留的回拨电话（没留则提示可改用发起关怀）。
  - **🤝 我来关心 TA（发起关怀）**：`POST /api/crisis/caregiver/shares/{id}/care` 记录一次关怀（可附留言），
    写入新表 `crisis_care_actions`（闭环 + 审计）。
- 当事人在「我分享给谁」里看到 **「收到关怀 N 次」**，形成被陪伴的正反馈。

### 第四轮验证
- 后端 `pytest`：**41 passed**（含 notify 无微信断言）。
- 前端 `vitest src/features/crisis-care`：**18 passed**（含回拨链接）。
- `vite build`：clean 通过；`一键回拨/发起关怀` 已打包，bundle 内已无任何 wechat 残留。

### 11.3 关怀实时触达（Web Push 给当事人）
- 牧者点「发起关怀」时，后端复用 `routers/push.send_to_email()` 给**当事人**推一条 Web Push
  「🕊️ 有人在关心你」（可带留言），点击落到 `/?tab=crisis`。
- 复用既有 `push_subscriptions` + VAPID；未配置 VAPID / 当事人未订阅时优雅降级（只记录、不报错），
  前端提示「对方下次打开时会看到」；推送成功则提示「已即时通知对方」。
- 验证：后端 **42 passed**（含 `push.send_to_email` 降级）、前端 **18 passed**、`vite build` clean。

### 11.4 移除「发起关怀」（保留一键回拨）
- 应要求移除牧者「🤝 发起关怀」动作及其闭环：删除 `/api/crisis/caregiver/shares/{id}/care` 端点、
  `CareBody`、`crisis_care_actions` 表、`list_shares` 的「收到关怀」计数、前端 `发起关怀` 按钮与 `caregiverCare`，
  以及为其新增的 `push.send_to_email`（routers/push.py 回到原状）。
- **保留**「📞 一键回拨」：当事人可选填回拨电话，牧者在协作台一键 `tel:` 拨打。
- 验证：后端 **41 passed**、前端 **18 passed**、`vite build` clean；`/api/crisis` 回到 24 个端点，bundle 内已无关怀动作残留。
