# 属灵技能登记（司布真 × 钟马田 7 大 Skill → 落地映射）

> PDF 愿景把司布真/钟马田沉淀为可被任何 Agent 调用的「技能」。下表把 7 个 Skill 对应到
> 已实现的引擎与系统提示词位置，作为「20 Agent / 50 Tool Prompt」体系的可演进基础。

| Skill | 角色 | 落地引擎 / 路由 | 提示词位置 |
|---|---|---|---|
| 1 司布真 Heart Formation | 属灵牧者，引向基督 | `routers/agent.py` (spurgeon) | AGENTS['spurgeon'].system |
| 2 钟马田 Gospel Diagnosis | 挖到偶像与不信 | `gospel_engine.py` + `routers/agent.py`(lloydjones) | SYSTEM_PROMPT / AGENTS |
| 3 Idol Detection | 偶像识别引擎 | `idolatry_engine.py` | 7 类功能性偶像 + 依附强度 |
| 4 Spurgeon Meditation | 清晨甘露生成 | `dew_engine.py` | build_prompt (司布真默想) |
| 5 Lloyd-Jones Checkup | 属灵低潮医生 | `checkup_engine.py` | build_prompt (《属灵低潮》) |
| 6 Spurgeon Decision Discernment | 信心辨识向导 | `decision_engine.py` | build_prompt (Skill 6) |
| 7 Faith-Hope-Love Engine | 品格评估 | `virtues_engine.py` | build_prompt (Skill 7) |
| ＋ 福音诊断室 | 双引擎合一闭环 | `gospel_engine.py` | 司布真+钟马田合一 |
| ＋ 天路客 | 状态→历程定位 | `pilgrim_engine.py` | 11 地点规则 |
| ＋ 养料库 | 按困扰组装 | `fuel_engine.py` | 8 困扰 × 多传统 |

所有 AI 技能都「确定性优先 + AI 增强」：未配置 LLM 时用确定性逻辑/内容兜底，配置后用上述
提示词增强，失败回退。统一走 `waiting_engine.call_ai_provider`（Gemini / SiliconFlow）。

## 关于 PDF「未来基建」的诚实说明
- **Neo4j 属灵知识图谱 / 用户成长状态机**：当前栈是 PostgreSQL(Neon)，未运行 Neo4j；项目
  已有 `graph_layer.py` 提供轻量图/回路推理。引入独立 Neo4j 与正式状态机属于**平台级决策**，
  建议作为单独立项，而非在现栈里勉强落地。本轮未实现（避免造一个不可运行的空壳）。
- **20 Agent / 50 Tool Prompt 拆分**：本表是其可演进基础；可在此之上逐步细化，无需推倒。

## IA 完整迁移（第六大陆收编）的现状与建议
- 已交付 **IA v1**：`PlanetHome` 五/六大陆「成长地图」作为今日心镜入口，深度路由到全部新功能。
- **完整迁移**（改默认落地页、把 9 个底部 Tab 收编进五大陆）会改变 app 的招牌体验(3D 情绪球落地)
  且需重构 2995 行的 App.jsx，**有破坏在跑体验的风险**。建议作为独立 UX 立项、分步可回退地做，
  而非一次性替换。本轮保持现有导航稳定，只做了「地图聚合入口」这一安全增量。
