# EMD-OS Batch 1 Report — 情感成熟度诊断域（EM-01 ~ EM-10）

Date: 2026-07-28
Scope: 在 Formation Twin 内新增「情感成熟度诊断域」（Emotional Maturity Diagnostic OS, EMD-OS）的
Batch 1 底座：知情授权、安全分流、评估建档、证据规范化、自适应选题、维度评分、作答有效性校准、
画像合成、成长路由与用户修正／复测。

设计定位：EMD-OS **不是**独立于属灵星球的「情感星球」，而是 `formation_twin` 的一个诊断域，位于
仓库既有十余个训练干预引擎的**上游**。

---

## 1. 新增 vs 融入现有模块

按「功能已有就融入、缺的才新增」的原则处理：

| 设计文档中的能力 | 处理方式 | 落点 |
| --- | --- | --- |
| 危机识别与分级 | **复用**，不重造 | `crisis_engine.triage`（EM-02 只在其结果上叠加关系安全与医疗红旗规则，且只能升级、不能降级风险） |
| 属灵／人格／诊断类输出拦截 | **复用** | `formation_twin.formation_safety.review_generated_text` + `theological_safety` |
| 情绪命名与情绪状态快照 | **复用**，作为 D1 的训练路由 | `emotionally_healthy_engine`（六维自评）、`formation_twin/emotional_engine.py`、`routers/formation_twin_emotions.py` |
| 十维训练干预 | **复用**，全部指向现有引擎 | anger / comfort / burnout / suffering / repentance / conscience / grace_identity / narrative / adoption / loneliness / fear_of_man / rule_of_life / neighbor_love / ordo_amoris / forgiveness / tender_heart / lament / waiting / contentment / sabbath |
| 发布治理、评测注册、红队 | **已存在**，Batch 10 时再对接 | `backend/production_governance/`、`platform_orchestration/data_quality.py` |
| 同意闸门（分项、可独立撤回） | **新增** | EM-01 |
| 十维模型 EMDM v0.1 与阶段 E0–E5 | **新增** | `formation_twin/emotional_maturity.py` |
| 证据规范化、去重、时效 | **新增** | EM-04 |
| 自适应选题与停止条件 | **新增** | EM-05 |
| 阶段评分与置信度、封顶规则 | **新增** | EM-06 |
| 社会赞许性／自述—行为差距校准 | **新增** | EM-07 |
| 无总分画像 | **新增** | EM-08 |
| 成长路由（只路由到已有模块） | **新增** | EM-09 |
| 用户修正与 14/30/90 复测排程 | **新增** | EM-10 |

---

## 2. 交付物

```text
backend/formation_twin/emotional_maturity.py                     引擎（EM-01 ~ EM-10，纯确定性）
backend/routers/formation_twin_emotional_maturity.py             API（/api/v1/formation-twin/emotional-maturity/*）
backend/migrations/0223_formation_twin_emotional_maturity.sql    8 张表 + 索引 + Owner RLS
backend/migrations/rollback/0223_..._down.sql                    手动回滚
backend/tests/test_formation_twin_emotional_maturity.py          53 个测试
backend/main.py                                                  导入 / 初始化 / include_router
```

## 3. 十维模型 EMDM v0.1

D1 情绪觉察与颗粒度、D2 情绪调节与恢复、D3 压力退化与挫折承受、D4 责任承担与现实感、
D5 人格整合与真我一致性、D6 依恋安全与自我分化、D7 边界与课题分离、D8 同理心与心智化、
D9 冲突／脆弱表达与关系修复、D10 有限性、哀伤与安息。

每个维度独立出阶段 E0–E5 与置信度，**不存在任何跨维度总分**。每个维度都携带其在现有仓库中的
训练模块与路由，EM-09 只能从这张表里选，不生成新的心理干预。

## 4. 关键工程约束（已由代码与测试强制）

- **不得出现总分或排名**：`total_score` 恒为 `None`；`PROHIBITED_KEYS` 在出站前被剥离；
  「情感成熟总分／成熟度百分比／比谁更属灵」等措辞在 `validate_safe_text` 中硬失败。
- **证据不足即 E0**：置信度 `INSUFFICIENT` 时阶段只能是 `E0`，并在数据库层用
  `CHECK(confidence <> 'INSUFFICIENT' OR stage = 'E0')` 二次兜底。
- **自述不能证明能力**：只有自评证据时阶段封顶 E2；没有真实事件时封顶 E3；
  `HIGHER` 置信度要求 ≥2 条真实事件且跨 ≥2 个情境。
- **单次成功不算稳定**：阶段取「被至少两条独立证据支持的最高阶段」，单条高阶证据自动降级。
- **安全优先于训练**：`ELEVATED/IMMINENT` 直接阻断评估并路由到 Crisis Care；
  关系安全为 CAUTION 时，D6/D9 禁止对质、深度披露与恢复联系类建议。
- **身体症状不做情绪归因**：胸痛／呼吸困难触发身体安全提示而非情绪解释。
- **同意分项且可独立撤回**：撤回行为证据授权会把相关证据置为 excluded 并要求重算；
  撤回长期授权会取消复测排程；撤回分享不影响私人核心功能。
- **用户修正优先**：有异议的结论 `twin_update_allowed=False`，旧快照被 supersede 而非删除。
- **事件不带正文**：`sanitize_event` 白名单只允许 ID、阶段、置信度、状态等字段。

## 5. API

```http
GET    /api/v1/formation-twin/emotional-maturity/overview
GET    /api/v1/formation-twin/emotional-maturity/consent-scopes
POST   /api/v1/formation-twin/emotional-maturity/consent
POST   /api/v1/formation-twin/emotional-maturity/consent/withdraw
POST   /api/v1/formation-twin/emotional-maturity/triage
POST   /api/v1/formation-twin/emotional-maturity/intake
POST   /api/v1/formation-twin/emotional-maturity/evidence
POST   /api/v1/formation-twin/emotional-maturity/next-items
POST   /api/v1/formation-twin/emotional-maturity/score
POST   /api/v1/formation-twin/emotional-maturity/route
POST   /api/v1/formation-twin/emotional-maturity/corrections
POST   /api/v1/formation-twin/emotional-maturity/reassessment
GET    /api/v1/formation-twin/emotional-maturity/profile
GET    /api/v1/formation-twin/emotional-maturity/data-quality
DELETE /api/v1/formation-twin/emotional-maturity/data
```

## 6. 测试结果

```text
tests/test_formation_twin_emotional_maturity.py    53 passed
formation_twin 全量（10 个文件）                    262 passed, 1 failed
```

唯一失败项 `test_formation_twin_contracts.py::test_checked_in_json_schema_validates_the_python_contract_sample`
是**既有测试在 Python 3.10 沙箱下的环境问题**（`datetime.fromisoformat` 在 3.11 之前不接受 `Z` 后缀），
与本批次改动无关；仓库目标运行时为 Python 3.11。

## 7. 明确不提供的能力

得救／重生／圣灵同在判断、属灵成熟总分与排名、精神疾病临床诊断、替代牧者或危机服务、
把一次评估写成永久人格、未成年人流程（需独立儿童安全认证，EM-01 直接阻断）。

## 8. 当前状态与后续批次

```json
{
  "architecture_status": "BATCH_1_IMPLEMENTED",
  "psychometric_status": "NOT_EVALUATED",
  "privacy_status": "NOT_ASSESSED",
  "security_status": "NOT_REDTEAMED",
  "production_certificate": "NOT_ISSUED"
}
```

Batch 1 只完成底座。题库与压力情境模拟（Batch 2）、真实事件与纵向验证（Batch 3）、
Batch 4–9 的训练与分析层、以及 Batch 10 的生产认证（应并入既有
`backend/production_governance/`，而非另起模块）尚未实现。在心理测量证据、隐私评估与红队结果
真实存在之前，本域只能按 `IU-1 私人自我反思 / exploratory` 对外呈现。
