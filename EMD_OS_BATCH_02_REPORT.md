# EMD-OS Batch 2 Report — 十维自适应测评与行为证据引擎（EM-11 ~ EM-19）

Date: 2026-07-28
Scope: 把 Batch 1 中抽象的 `adaptive_dimension_assessor` 拆成九个可独立测试的 Skill：题库注册、
自适应选题、情境化呈现、压力情境模拟、行为证据提取、行为锚点评分、反事实追问、跨题一致性校准、
证据充分性判断。

## 1. 交付物

```text
backend/formation_twin/emotional_maturity_items.py                 引擎（EM-11 ~ EM-19，纯确定性）
backend/migrations/0224_formation_twin_emd_item_bank.sql           9 张表 + 索引 + Owner RLS
backend/migrations/rollback/0224_..._down.sql                      手动回滚
backend/routers/formation_twin_emotional_maturity.py               新增 7 个端点（沿用 Batch 1 路由）
backend/tests/test_formation_twin_emotional_maturity_items.py      54 个测试
```

## 2. 题库

十维 × 五种题型（SR 自述 / BE 最近行为 / SF 压力情境 / CF 反事实 / RV 反向效度）。
种子题库落地了设计文档中的 40 道规范题（每维 SR+BE+SF+RV），CF 题由 EM-17 在运行时按需生成。

注册器强制：

- 每个维度必须同时具备 SR / BE / SF / RV，缺一即 `REJECTED`；
- 纯 Likert 题库被拒绝（`LIKERT_ONLY_BANK_NOT_ALLOWED`）；
- 题目文本不可变：改文案必须发新 `item_id` 或新 `bank_version`（数据库层用 `UNIQUE(item_id, bank_version, locale)` 兜底）；
- 难度与区分度在获得校准样本前只能是 `estimated`，不得声称心理测量学参数。

## 3. 关键约束（由代码与测试强制）

- **证据等级 L1–L5**：自述 L1、情境意向 L2、近期真实行为 L3、压力升级后 L4、事后修复 L5。
  情境题回答再好也不会自动升级为 L4/L5。
- **语言能力不参与评分**：回答长、术语多、引用经文、认同系统价值观都不加分；
  「昨天我先走开，等冷静再说」这类简短但行为明确的回答能拿到完整证据。
- **每条推断必须有原文片段**；没有出现的特征返回 `unknown`，「我不知道」记为证据不足而非低成熟。
- **伤害性标记封顶阶段**：攻击 → E1，冷处理/读心/属灵逃避/历史泛化 → E2，绝对化语言 → E3。
  情绪词丰富不能把「冲突中立即攻击且拒绝修复」抬到 E4。
- **意向不等于稳定**：`self_report` 封顶 E2，情境/反事实封顶 E3，`is_stable_capacity` 只对
  压力升级或事后修复证据成立（数据库层 CHECK 兜底）。
- **反事实每次只改一个变量**，每个原题最多两个追问，回答变化解释为情境敏感而非不诚实。
- **一致性校准只降置信度，不降阶段**，且禁止「撒谎 / 虚伪 / 诚实度」类措辞（`UnsafeContentError`）。
- **充分性四级**：insufficient / provisional / moderate_confidence / higher_confidence；
  疲劳高且已有最低证据 → 暂停保存；疲劳高且证据不足 → 停止并标记证据不足；
  安全状态变化 → 立即停止转安全系统；跳过敏感题不被惩罚。

## 4. 与 Batch 1 的桥接

`to_batch1_evidence()` 把 EM-16 的评分结果转成 Batch 1 的 `EvidenceItem`：

```text
self_report        → SELF_DESCRIPTION
scenario/CF/澄清   → SCENARIO_RESPONSE
recent_behavior    → RECENT_BEHAVIOR
escalated/post_repair → REAL_LIFE_EVENT
```

Batch 1 的封顶与置信度规则继续生效：两条真实事件证据若缺少第二种证据来源，仍然停在 E0。

## 5. 新增 API

```http
GET  /api/v1/formation-twin/emotional-maturity/item-bank
POST /api/v1/formation-twin/emotional-maturity/items/next
POST /api/v1/formation-twin/emotional-maturity/scenarios
POST /api/v1/formation-twin/emotional-maturity/responses
POST /api/v1/formation-twin/emotional-maturity/probes
POST /api/v1/formation-twin/emotional-maturity/calibrate
POST /api/v1/formation-twin/emotional-maturity/sufficiency
```

`/responses` 只落库结构化元数据与带原文片段的特征，**不存储开放文本正文**（`raw_text_stored: false`），
并在评分后自动把证据桥接进 Batch 1 的证据表。

## 6. 测试结果

```text
tests/test_formation_twin_emotional_maturity_items.py    54 passed
```
