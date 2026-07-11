# 属灵星球 Mission OS 全功能版 — 开发路线图（Batch 0–6）

> 本文件是 Mission OS 规划的参考文档。应用内对应的可折叠路线图页面位于
> 「宣教」Tab → 「宣教」子标签 → 「🛰️ Mission OS 路线图」视图
> （前端：`bible3dsphereWeb/src/features/mission-os/roadmap/`）。

## 完整业务闭环

禾场情报 → 呼召辨识 → 工人装备 → 教会差派 → 团队建设 → 合法进入 → 在地服事
→ 工人关怀 → 本地领袖培养 → 权力移交 → 全球宣教基础设施。

## 每个 Skill 的统一完成定义（DoD）

领域模型 · 数据库迁移 · Repository/Service · API · 权限策略 · 前端页面/组件 ·
审计策略 · 单元测试 · 集成测试 · E2E 测试 · 文档 · 与现有属灵星球模块的集成。

## 技术假设（优先方向，不得强制覆盖已有架构）

- Frontend：Next.js / React / TypeScript / Tailwind / shadcn/ui / TanStack Query / RHF / Zod / next-intl / PWA
- Backend：FastAPI / Python / Pydantic v2 / SQLAlchemy 2 / Alembic
- Data：PostgreSQL / pgvector /（可选 Neo4j）/ RLS / Transactional Outbox
- AI：LangGraph / Provider Adapter / Structured Output / Prompt Registry / Model Run Audit / Human-in-the-loop
- Testing：pytest / Vitest / Playwright / axe-core / Schemathesis

---

## Batch 0：项目总控、架构与安全基线 — ✅ 已基本落地

目标：建立不会因后续扩展而推倒重来的工程和治理底座。

现状：仓库已实现 `backend/mission_os/`（feature_flags、outbox、audit、events、ports、
incidents、organizations、religious_freedom、errors、ids、pagination、subdomains）
及迁移 `0156_mission_os_feature_flags` / `0157_mission_os_outbox` /
`0160_mission_os_audit_lineage` / `0162_mission_os_incident_workflow` /
`0169_mission_os_organizations`。

- Skill 00 全项目总宪章与完成定义
- Skill 01 现有仓库审计与模块复用分析
- Skill 02 领域边界与上下文映射
- Skill 03 Monorepo 模块、依赖方向与代码规范
- Skill 04 Feature Flags、环境配置与版本治理
- Skill 05 Domain Event、Outbox 与跨模块集成
- Skill 06 审计日志、操作追踪与数据血缘
- Skill 07 宣教伦理、Safeguarding 与风险分级（L0–L3）

## Batch 1：身份、多租户、权限、隐私与同意 — ✅ 已达标

目标：建立个人、教会、差会、团队和合作机构之间的安全数据边界。

- Skill 08 多租户组织模型
- Skill 09 Mission OS 角色与权限矩阵（RBAC）
- Skill 10 PostgreSQL RLS 租户隔离
- Skill 11 敏感字段分级（P0–P4）与字段级授权
- Skill 12 知情同意与同意撤回系统
- Skill 13 数据保留、导出、删除与匿名化
- Skill 14 未成年人、监护人与高脆弱群体保护
- Skill 15 二次认证、敏感导出审批与安全会话

## Batch 2：全球宣教禾场情报系统 — 🟢 骨架已落地

目标：形成可追溯、可验证、可持续更新的国内及全球禾场知识系统。

- Skill 16 Mission Field 核心领域模型
- Skill 17 族群、语言、宗教与地区知识图谱
- Skill 18 侨民、留学生、移工与人口流动模型
- Skill 19 圣经、音频、手语与母语资源可及性
- Skill 20 当地教会成熟度与领袖缺口模型
- Skill 21 禾场需要、机会、进入条件与风险模型
- Skill 22 资料来源、快照与 Claim-Evidence 系统
- Skill 23 来源冲突、可信度、时效与数据质量管理
- Skill 24 禾场优先级评分与可解释推荐引擎（Need/Evidence/Readiness/Risk 分离）
- Skill 25 中国国内宣教禾场模板
- Skill 26 全球重点地区与侨民禾场模板
- Skill 27 禾场地图、比较、研究工作台与报告系统

## Batch 3：呼召辨识、恩赐画像与工人准备度 — 🟢 骨架已落地

目标：避免把一次感动直接等同于长期差派呼召。

- Skill 28 宣教呼召辨识旅程
- Skill 29 呼召动机、属灵状态与反逃避检查
- Skill 30 教会、导师、家庭与群体多方确认
- Skill 31 工人恩赐、职业、经历与能力画像
- Skill 32 宣教工人角色分类与岗位能力模型
- Skill 33 工人、角色、团队与禾场匹配引擎
- Skill 34 工人准备度十五维评估系统
- Skill 35 暂停、恢复、申诉与重新评估流程
- Skill 36 AI 呼召辨识边界、人工复核与模型治理

## Batch 4：宣教装备、课程、语言文化与本地实习 — 🟢 骨架已落地

目标：把准备度差距转化为 6–24 个月的具体训练、实践、督导与人工认证路径。

- Skill 37 个性化宣教装备计划生成器
- Skill 38 圣经宣教神学课程系统
- Skill 39 教会论、门徒训练与植堂课程
- Skill 40 世界宗教与跨宗教沟通课程
- Skill 41 处境化、文化人类学与殖民反思课程
- Skill 42 团队生活、冲突处理与权力边界课程
- Skill 43 儿童保护、家暴、心理危机与专业转介课程
- Skill 44 语言学习与文化观察系统
- Skill 45 职业能力与真实职业身份预备系统
- Skill 46 本地跨文化实习管理系统
- Skill 47 短期观察、探索旅程与长期跨文化实习
- Skill 48 导师、督导、训练 Cohort 与同伴学习系统
- Skill 49 课程测验、实践观察与人工阶段认证

## Batch 5：差派教会、机构、团队、本地伙伴与正式差派 — 🟢 骨架已落地

目标：让工人由教会、机构与接收团队共同差派，而非个人独立行动。

- Skill 50 差派教会管理与教会确认
- Skill 51 宣教机构、接收机构与机构能力管理
- Skill 52 候选人差派申请与完整性审核
- Skill 53 多方审批、差派委员会与正式决定
- Skill 54 宣教团队组建与成员生命周期
- Skill 55 团队角色、能力、容量与缺口分析
- Skill 56 团队契约、神学共识与行为规范
- Skill 57 团队冲突模拟、健康评估与申诉机制
- Skill 58 本地伙伴发现、尽职调查与合作评估
- Skill 59 合作协议、决策权、资源权与退出安排
- Skill 60 代祷伙伴、支持教会与沟通网络


## Batch 6：财务、筹款、签证、合规、医疗保险、家庭、数字安全与撤离 — 🟢 骨架已落地

目标：从委员会批准进入部署预备，到具备真实、合法、财务可持续、安全可执行的部署条件。

- Skill 61 宣教全周期预算、现金流与储备模型
- Skill 62 个人支持筹集、支持承诺与筹款伦理
- Skill 63 教会、机构与项目资金治理
- Skill 64 财务透明、利益冲突、审计与反欺诈
- Skill 65 真实职业、学习、居留与身份路径管理
- Skill 66 签证、证件、许可与到期任务系统
- Skill 67 法律、税务、宗教活动与数据合规审查
- Skill 68 医疗评估、保险、用药与健康连续性
- Skill 69 配偶、子女、父母责任与家庭预备
- Skill 70 数字安全、设备、通信与敏感数据保护
- Skill 71 危机响应、撤离、事工连续性与 Deployment Readiness Gate

> 无 Batch 7：Deployment Readiness Gate 的 `ready_for_deployment_planning` 即系统自动化终态，
> 之后的实际出发/抵达/现场运营属运营侧、不由自动化 Gate 触发。
> 端到端主线见 [integration-map.md](./integration-map.md)。

---

## 逐批实现顺序与验收

按 `Batch 1 → 2 → 3 → 4 → 5`、每批内 `Skill by Skill` 实现后端 / 前端 / 迁移 /
权限 / 安全 / 测试 / 文档 / 集成；每批完成后生成 `batch-N-validation-report.md`
验收报告，任一 P0/P1 未解决则结论为 `NOT READY FOR BATCH N+1`。

> 不得通过删除测试、关闭 RLS、弱化权限、降低敏感级别或修改验收标准来获得通过。
