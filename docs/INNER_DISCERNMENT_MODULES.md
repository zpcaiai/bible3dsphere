# 心迹 · 内在辨识两模块

为「心迹 / 今日心镜」新增的两个独立、低耦合子系统。两者都遵循同一铁律：
**不定罪、不贴标签、不审判**，只温柔地帮助人看见内心，并导向信靠与自由。

入口：今日心镜 (`SoulDashboard`) 顶部的两张卡片 → 全屏 overlay 打开。

---

## 1. 偶像监测 · 依附强度指数 (Attachment Intensity Index)

监测什么正在取代神，成为安全感、价值感、盼望、身份与顺服的中心。
评分刻意不叫「偶像分」，而叫**依附强度指数**，以避免羞耻。

监测 7 类功能性偶像：成就/表现、金钱/保障、认可/被看见、掌控/确定性、
关系/某个人、舒适/安逸、属灵形象。

每类按 5 个子维度自评 (0–1)：身份依赖、平安扰动、害怕失去、顺服冲突、注意捕获。
加权得到 0–1 的依附强度指数 → 风险等级 low/moderate/elevated/high。
另叠加 Graph 依附回路 + 福音「破除节点」(信靠/安息/谦卑/在基督里的身份…)，
并给非定罪式说明 + 3 条建议 + 经文。

可选信号增益：从近期 checkin 的情绪 (焦虑/恐惧/嫉妒) 与注意力焦点，
温和地为子维度加权，并提示「值得先省察」的偶像类型。

**文件**
- DB：`backend/migrations/0021_attachment_patterns.sql`
  （`attachment_patterns` + `attachment_sessions`，email 主键）
- 引擎：`backend/idolatry_engine.py`（纯函数，无 DB / 无外部依赖）
- 路由：`backend/routers/idolatry.py`
- 前端：`emotion-sphere-ui/src/IdolatryMonitorPage.jsx`

**API**（`/api/idolatry`，需登录）
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/meta` | 7 类偶像 / 6 问题 / 5 维度 / 风险标签 |
| GET | `/signals` | 客观信号 + 建议省察的偶像类型 |
| POST | `/assess` | 提交省察，落库并返回完整分析 |
| GET | `/patterns?limit=` | 历史（按会话聚合） |
| GET | `/latest` | 最近一次摘要（供卡片） |

---

## 2. 等候之路 · Waiting Transformation Module

把「等待戈多」(被动、虚无、焦虑、幻想式) 温柔地分辨与转化为
「等候上帝」(在不确定中仍信靠、忠心行动、不把结果当偶像)。

流程：命名等待 → 7 维自评 (0–10) → 分辨 → 7 天操练 → 复盘。

**分辨指标**（0–1）：等待戈多倾向、等候上帝倾向、偶像化风险、被动风险、
盼望稳定度，并给出温柔的五段分析（等待对象 / 情绪模式 / 偶像风险 /
被动风险 / 信望爱方向）+ 3 条可执行建议 + 反思问题。

**AI 可替换**：默认走确定性引擎（无需任何 API key 即可运行）；若配置了
`GEMINI_API_KEY` / `SILICONFLOW_API_KEY`，`analyze` 会尝试用 OpenAI 兼容
接口增强分析，任何失败都自动回退确定性结果。

**安全**：内置危机词检测；若用户文字流露自伤 / 极端绝望，输出开头会温柔地
建议寻求现实中的专业帮助与可信赖的人——不替代专业判断。

**7 天操练**为固定模板：命名等待 → 识别依附 → 从幻想回到现实 → 交托结果
→ 等候中的行动 → 等候中的爱 → 复盘转化。

**文件**
- DB：`backend/migrations/0022_waiting_transformation.sql`
  （`waiting_cases` / `waiting_practices` / `waiting_reflections`，email 主键）
- 引擎：`backend/waiting_engine.py`（确定性评分 + Prompt 构建 + 可替换 Provider）
- 路由：`backend/routers/waiting.py`
- 前端：`emotion-sphere-ui/src/WaitingPathPage.jsx`

**API**（`/api/waiting`，需登录）
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/meta` | 维度 / 类型标签 / 7 天模板 |
| GET | `/cases` | 我的等待案例列表 |
| POST | `/cases` | 新建案例 |
| GET | `/cases/{id}` | 详情（分析 + 操练 + 复盘） |
| POST | `/cases/{id}/analyze` | 运行分析（确定性 + 可选 AI） |
| POST | `/cases/{id}/practices/generate` | 生成 7 天操练 |
| POST | `/cases/{id}/reflect` | 提交复盘 |
| POST | `/practices/{id}/complete` | 完成某天操练 + 反思 |

---

## 设计取舍（与原始规格的差异）

- **技术栈**：原始规格假设 Vue3+TS；本项目前端是 **React (JSX)**，故按既有
  栈以最小侵入实现（单文件页面 + overlay，不引入 Vue/TS）。
- **用户标识**：规格用 `user_id UUID`；本项目统一以 `email` 鉴权，故表以
  `email` 为属主列，与既有所有表一致。
- **迁移**：新增表只走 `backend/migrations/00NN_*.sql`，在 commit 到 GitHub
  main 时由 CI 在 Neon 生效（遵循项目既定策略）。
- **AI**：封装为可替换 provider，**默认确定性、零外部依赖即可跑通**。

两个引擎都是纯函数，已用样例数据自测（评分 / 风险分级 / 危机检测 / 7 天计划）。
路由已在 `backend/main.py` 注册（import + `include_router` + lifespan init）。
