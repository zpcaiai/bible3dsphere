# EMD-OS Batch 1–10 审计：完整性、闭环、与既有系统的融合

Date: 2026-07-28
审计方式：`backend/tests/test_emd_batches_closure.py`（39 个用例），每次运行都从代码树重新推导事实。
一次性人工审阅会立刻过时，因此所有结论都写成可重跑的断言。

---

## 结论

**完整**：EM-01 ~ EM-87 全部实现，十个批次严格分区、无缺口无重叠。
**闭环**：审计发现三条断裂的回路，已全部接上。
**融洽**：复用既有危机系统、文本安全与十个训练引擎，未另起平行系统；未引入任何总分。

---

## 1. 完整性

| 项目 | 数量 |
| --- | ---: |
| 能力条目 EM-01 ~ EM-87 | 87 / 87 |
| 引擎模块 | 15 |
| 引擎代码行数 | 10,288 |
| 公开函数 | 144（其中 ≥75% 可从 API 到达） |
| 迁移文件 | 11（各自带 rollback） |
| 数据表 | 79 |
| API 路由 | 93（Formation Twin）+ 13（治理） |
| 测试文件 | 15 |
| 测试用例 | 645 通过 |

批次分区：

| 批次 | 能力 | 主题 |
| ---: | --- | --- |
| 1 | EM-01 ~ EM-10 | 同意、安全分流、十维模型、证据与画像 |
| 2 | EM-11 ~ EM-19 | 题库、自适应选题、压力情境、行为证据 |
| 3 | EM-20 ~ EM-27 | 真实事件、时间线、恢复指标、修复验证 |
| 4 | EM-28 ~ EM-37 | 情绪调节、暂停协议、冲动阻断、共调节 |
| 5 | EM-38 ~ EM-46 | 家谱、依恋循环、分化、面具与真我 |
| 6 | EM-47 ~ EM-55 | 边界、冲突对话、道歉、宽恕、信任重建 |
| 7 | EM-56 ~ EM-64 | 哀伤、有限性、安息、属灵逃避辨识 |
| 8 | EM-65 ~ EM-70 | 跨系统编排、祷告路由、Twin 桥接、牧养转介 |
| 9 | EM-71 ~ EM-77 | 指标目录、轨迹、归因、泛化、可比性 |
| 10 | EM-78 ~ EM-87 | 用途分级、心理测量治理、公平性、认证与事故 |

每个批次都有报告（`EMD_OS_BATCH_01..10_REPORT.md`）、迁移、路由与测试。

---

## 2. 闭环：审计发现的三条断裂回路

审计对每个公开函数统计生产调用点，剔除模块限定调用的误报后，发现三个函数**有实现、有测试，但没有任何生产调用方**——也就是说，这三条设计好的回路从未真正接通。

### 2.1 真实事件回不到阶段判定（Batch 3 → Batch 1）

`event_to_batch1_evidence()` 无人调用。后果不是报错，而是更隐蔽的东西：用户认真记录的真实冲突事件，
永远不会成为 `REAL_LIFE_EVENT` 证据，而 Batch 1 的规则规定「没有真实事件证据，阶段上限为 E3」。
换句话说，**再努力也升不上去，而且看不出为什么**。

已接通：`POST /emotional-maturity/events` 在事件核实后，为每个相关维度写入 Batch 1 证据，
返回 `bridged_to_batch1_dimensions`。

### 2.2 撤回 Twin 同意没有真的撤回（Batch 8 → Batch 1）

`withdraw_twin_evidence()` 无人调用。撤回 `EMD_LONGITUDINAL_TWIN` 时只取消了复测计划，
**已经写进 Formation Twin 的 EMD 证据仍在原处继续生效**。用户以为撤回了，实际只是不再更新。

已接通：撤回时遍历该用户所有未撤回的 twin bridge，逐条撤回并触发重算，
返回 `twin_evidence_withdrawn` 计数。

### 2.3 训练候选守卫没有入口

`assert_no_training_material()` 是本轮新增的守卫，但没有调用点。
已接通为 `POST /emotional-maturity/training-optout/check-corpus`，
命中 P2 及以上材料返回 **422 而不是警告**——语料里混入敏感材料不是「稍后处理的发现」，是必须当场终止的请求。

三条回路各自有测试锁死，不会再悄悄断开。

---

## 3. 融洽：复用而非另起

| 既有能力 | EMD 的用法 | 断言 |
| --- | --- | --- |
| `crisis_engine.triage` | 危机分流的第一判断；EMD 只做「只能抬高不能降低」的兜底 | `test_safety_reuses_the_existing_crisis_system` |
| `formation_safety.review_generated_text` | 所有开放文本的安全校验 | `test_text_safety_reuses_formation_safety` |
| 十个训练引擎 | 成长路由指向 `/api/anger`、`/api/lament`、`/api/forgiveness` 等既有接口，EMD 不自己实现训练 | `test_growth_routing_points_at_the_existing_training_engines` |
| `production_governance` 包 | Batch 10 长在既有治理包内，与 `scenarios/evaluation/release` 并列 | `test_certification_extends_the_existing_governance_package` |
| Formation Twin 前缀 | 93 条路由全部挂在 `/api/v1/formation-twin/` 下 | `test_emd_routes_live_under_the_existing_formation_twin_prefix` |
| 迁移体系 | 所有表由迁移创建，路由层零 `CREATE TABLE` | `test_every_emd_table_is_created_by_a_migration_not_at_runtime` |

**没有引入平行计分体系**：`emotional_maturity_total_score`、`maturity_percentile`、`spiritual_rank`
只出现在禁用清单里，从未被真实赋值——测试用正则确认没有任何一处给它们赋非 None 的值。

**没有孤岛模块**：每个引擎模块要么被路由引用，要么被其他引擎模块引用。

---

## 4. 仍然是人工判断的部分

审计能证明结构、接线与不变量，不能替代下列判断：

- 题目措辞是否被目标用户正确理解（认知访谈）
- 阶段判定是否与真实生活表现对应（试点样本）
- 真实 RAG + 工具栈上的间接注入是否被挡住（红队）
- 跨语言、跨传统的误判率是否可接受（公平性审计）

这四项都在 `BEFORE_MORE_USERS` / `BEFORE_PUBLIC_LAUNCH` 清单里，且都需要人。
