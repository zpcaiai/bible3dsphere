# Formation Twin Batch 03 Report

日期：2026-07-17
范围：情感状态孪生引擎（整合 Batch 1/2 的身份、生命事件、授权、加密内容、Crisis Gateway、事件总线、导出与删除能力）

## 1. 已实现的情绪本体

- 开放、非互斥、非诊断的 `EmotionLabel` 本体，包含 34 个标准/治理标签。
- 支持中英文资源、中文别名、多情绪、`MIXED`、`UNKNOWN` 与 `OTHER.custom_label`。
- 未识别的用户原词会保留，不强行一对一映射；本体不包含疾病、人格或属灵状态标签。

## 2. 用户自述处理方式

- 从用户主动签到与生命事件 metadata 提取明确填写的情绪、身体感受、精力、压力和睡眠。
- 固定写为 `USER_REPORT / USER_REPORTED_FACT`，`confidence=null`，保留 source event。
- 同一事件同一情绪只保留用户明确填写的最高强度；不补全缺失强度，不把未填写解释为没有情绪。
- `STORE_ONLY`、删除、排除、supersede、非 `ACCEPTED` 事件不会进入重建；相关既有观察会失效。

## 3. 规则型指标和版本

- `emotional-rules-1.0` 计算精力、压力、睡眠的 `INCREASING / DECREASING / STABLE / VOLATILE / INSUFFICIENT_DATA`。
- 至少需要三个不同日期；输出数据点数、中位数和范围，不生成综合情感健康分。
- 规则结果以 `RULE / RULE_DERIVED_METRIC` 写入独立审计表，并携带规则版本、窗口、覆盖率和证据事件 ID。

## 4. 启用的模型推断能力

- 实现了可选的文本情绪候选提取；默认关闭。
- 需要全局开关、真实配置的既有 LLM provider、用户级同意及 provider policy 同时满足。
- 模型只产生 `MODEL / MODEL_INFERENCE / PENDING` 候选；无证据、越界、低于 0.45、诊断或属灵评判尝试会 fail closed。
- 本地验证未启用真实 provider，因此没有向外部模型发送用户内容。

## 5. 模型、提示词和 Schema 版本

- 引擎：`emotional-state-engine-1.0`
- 提示词：`emotion-extraction-1.0`
- 候选 Schema：`emotion-candidates-1.0`
- 快照 JSON Schema：`backend/formation_twin/emotional-state.schema.json`
- 模型运行表只保存 provider、模型/提示词/Schema 版本和结果状态，不保存日记或转写正文。

## 6. 情感快照结构

- `CURRENT_EMOTIONAL_STATE`、`DAILY_EMOTIONAL_SUMMARY`、`WEEKLY_EMOTIONAL_TREND`。
- 独立字段保存 `user_reported_state`、`rule_derived_state`、`current_candidates`、覆盖率、不确定性与限制。
- 输入哈希保证相同输入幂等；变化时新建版本并 supersede 旧快照。
- 数据不足时明确返回 `INSUFFICIENT_DATA`，不显示误导图表。

## 7. Episode 构建规则

- 支持用户创建、查看、修改、结束、合并、拆分、删除情感事件。
- Episode 只整理相关生命事件，不解释心理或属灵原因；自动聚类未启用。
- 关联使用 owner-scoped `episode_events`，合并保留关联并归档原 Episode。

## 8. 用户确认和否定机制

- 支持确认、部分确认、否定、重标注和不回答。
- 确认/重标注会新建 `USER_CONFIRMED / USER_CONFIRMED_INFERENCE`，不会篡改模型候选为用户事实。
- 已审候选不可重复审核；同一事件/标签/来源唯一约束阻止否定后重复生成。
- 用户修改、删除、排除或审核会使当前快照过期，随后按当前授权重建。

## 9. Crisis 联动结果

- 复用 Batch 2 的 Crisis-First Safety Gateway，不创建第二套危机分类器。
- 普通情感重建只读取 `ACCEPTED`；`ROUTED_TO_CRISIS` 不进入普通趋势或模型分析。
- 即使事件处于普通链，`ELEVATED/IMMINENT` 也会阻断模型候选调用。
- 事件总线只发布 ID、版本、来源和状态元数据，不发布危机或日记正文。

## 10. 数据库迁移

- 新增 `0213_formation_twin_emotional_state.sql`，包含 settings、emotion/body/energy observations、evidence、episodes、snapshots、reviews、rule results、model runs 共 11 张表。
- 所有表都有租户/owner 字段与 RLS；应用查询继续显式按 email 限定，并设置事务级 RLS owner context。
- 迁移为可重复升级 SQL，并按仓库惯例在文件尾记录 operator-controlled 逆序回滚命令。
- Batch 2 导出与彻底擦除已扩展到 Batch 3 数据。

## 11. API 清单

- 设置：`GET/PUT /emotion-settings`
- 状态：`GET /emotional-state/current|daily|weekly`、`POST /emotional-state/rebuild`、`GET /emotional-state/data-quality`
- 观察：`GET/POST /emotion-observations`、`GET/PATCH/DELETE /emotion-observations/{id}`
- 候选：`GET /emotion-candidates` 及 `confirm / partially-confirm / reject / relabel / dismiss`
- Episode：list/create/get/update/merge/split/resolve/delete
- OpenAPI 已验证挂载 21 条 emotion/emotional 路径，并描述四类来源契约。

## 12. 前端页面

- 在现有 Formation Twin workspace 内整合“情感状态”模块。
- 包含当前状态、情绪时间线、变化趋势、待确认、情感事件、处理授权六个视图。
- UI 分块展示用户自述、规则计算、待确认候选；显示身体、精力、压力和睡眠；模型默认关闭。
- 支持候选审核、观察删除、Episode 创建/结束/选择合并、授权切换，以及不足数据提示。
- 中文优先，并补齐英文自动翻译资源。

## 13. 测试和评估结果

- Batch 2/3 后端定向测试：27 passed（本体、提取、趋势、快照、模型 fail-closed、红队、迁移、RLS、数据质量）。
- OpenAPI 导入检查：通过；1243 个总路径，21 个情感相关路径。
- 前端 Formation Twin：7 files / 18 tests passed。
- 前端完整回归：97 files / 455 tests passed。
- 前端 ESLint：0 errors；仓库既有 451 warnings。
- Vite production build：通过，2327 modules transformed。
- 后端完整回归：949 passed，238 errors；全部错误由测试 PostgreSQL `localhost:5431` 未运行导致，不是断言失败。没有可用 `DATABASE_URL`，因此本次不能执行真实迁移/RLS/E2E 数据库验证。

## 14. 数据质量扫描结果

- 静态扫描通过：来源/statement type 必填、用户自述无 confidence、模型版本与 evidence 必需、置信度边界、事件级唯一约束、无普通明文字段、无不安全 `ANY(%s)` 参数模式。
- 本体中英文标签与 Python enum 完全一致；快照 Schema 包含三类来源区。
- 运行时 owner 数据质量 endpoint 已实现；因本地 PostgreSQL 不可用，本次未生成真实用户表扫描结果。

## 15. 已知风险

- 生产或测试数据库必须先应用 0212、0213，并在真实非 owner 角色下验证 RLS 与回滚演练。
- 真实 provider 的结构化输出、延迟/用量元数据和供应商数据保留政策仍需在启用前做集成验收。
- Episode UI 已支持对现有关联生命事件进行选择拆分；更友好的时间线拖放关联交互可继续增强。
- 日/周窗口当前按服务端 UTC 窗口生成；跨时区自然日的历史浏览可在后续版本细化。

## 16. Batch 4 接入点

- Batch 4 只能消费 source-separated、用户可见且可纠正的快照，不得直接消费原始敏感正文。
- 用户自述应继续高于规则和模型候选；未确认候选不得进入属灵形成结论。
- 可从版本化 snapshot、episode 与 rule result 读取上下文，并沿用 consent、RLS、Crisis、导出/删除及 metadata-only event bus。
- 在任何属灵形成关联进入产品前，仍需单独定义“相关不等于因果”的证据和用户确认界面。
