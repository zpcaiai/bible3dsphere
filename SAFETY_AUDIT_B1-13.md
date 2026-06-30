# 属灵星球 · 安全与完整性审计(B1–B13)

日期:2026-06-30 · 范围:13 个 batch 的后端 router、迁移、前端安全相关面

## 总评:**通过(已修一处真缺口)**

五个安全维度逐项核查,四项原本即合规,一项(危机扫描覆盖)发现并已修补。

---

## 1. 危机安全门覆盖 — ⚠️→✅(已补)

**原则**:任何摄入用户敏感倾诉的端点,命中危机信号时必须先路由到 `/api/crisis`,绝不进入反思/LLM 流程。

**已具备危机扫描的 router(20)**:
`crisis, suffering, care(目的地), examen, idolatry, discern, waiting, gratitude, lectio, psalm, intercession, prayer_rule, mission_life, temptation, accountability_group, church_integration, formation_agent, formation_advanced, ai_tutor, spiritual_memory`

**本次发现的缺口**:三个私密自由文本入口此前**未**做危机扫描:
- `journal.py` — 灵修日志 `reflection`
- `personal_notes.py` — 个人笔记 `reflection`
- `daily_soul_question.py` — 灵魂一问 `answer`

**处置**:已附加式加固(`_scan_crisis_safe()`,在响应中增加非破坏性 `crisis` 字段;命中即带 `route=/api/crisis`)。不改变既有字段与行为,前端可渐进消费。

**仍建议人工复核(本次未改,风险较低或语义不同)**:
`prayer.py(代祷请求)、community_feed.py(公开贴文)、disciple.py、evangelism.py、worldview.py、agent.py、spiritual_formation.py` — 若这些会承载个人危机倾诉,建议同样附加扫描。

---

## 2. 不冒充神 / 不宣称私人启示 — ✅

全仓库扫描「神告诉我 / 神对你说 / God told you / thus says the Lord」等,**仅 3 处命中,全部位于"禁止"条款**:
- `ai_tutor.py` 文档串 + SYSTEM_PROMPT(明确禁止)
- `stronghold_rag.py`(系统约束:"Do not say 'God told you'")

无任何模板/生成文案以神的口吻发话。AI 导师 system prompt 明确:工具非圣灵/牧者/辅导师,不宣称预言或私人启示。

---

## 3. 禁食健康安全门 — ✅

`fasting.py` 完整实现:
- `_UNSAFE` 关键词表覆盖进食障碍/厌食/暴食/催吐/孕期/糖尿病/胰岛素/随餐服药/晕厥/体重过轻/减重动机(中英双语)。
- `_validate_food_fast()` 命中即**拒绝食物禁食**并给非食物替代;食物禁食强制 `health_acknowledgement=true`。
- 文案为爱与自由,不夸耀、不极端。

---

## 4. 订阅不得拦截危机/安全 — ✅

`productization.py`:
- `entitlements/check`:`crisis_triage / safety_plan / crisis` 直接 `allowed=true, reason="safety_exception"`,**不受订阅状态影响**。
- 平台管理台 `/admin/overview` 经 `_is_platform_admin` 校验(403 拒绝越权)。

---

## 5. 记忆 / 隐私同意门 — ✅

`spiritual_memory.py` + `ai_tutor.py`:
- 同意规则 `memory_consent_rules`:`allow_ai_tutor / allow_mentor / allow_group / exclude_sensitive`(默认仅 AI 导师可读、默认排除敏感)。
- 危机内容入库自动升 `sensitivity='crisis'`,默认不进入 LLM 接地摘要。
- 接地查询在 `allow_ai_tutor=false` 时返回空;`exclude_sensitive=true` 时过滤敏感条目。

---

## 仍需你在本地验证的两点(沙箱跑不了)

1. `npm run build` — 沙箱无 Vite,无法做真实 JSX/打包校验(本会话仅做了括号/结构平衡检查)。
2. `python -m core.migrations` — 沙箱无 Postgres,迁移仅做结构检查(列数/括号/表名碰撞/版本号唯一)。

> 本次另修复:迁移版本号重复(0118/0119),已重排为唯一。仓库存在两套并行命名的迁移(`batchX_Y` vs 单技能),建议统一编号规则避免再撞。
