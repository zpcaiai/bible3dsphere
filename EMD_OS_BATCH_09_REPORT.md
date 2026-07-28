# EMD-OS Batch 9 Report — 复测、趋势归因与成长报告（EM-71 ~ EM-77）

Date: 2026-07-28
Scope: 整个 EMD-OS 的测量平面、分析平面与报告平面。

## 1. 交付物

```text
backend/formation_twin/emotional_maturity_analytics.py                   引擎（EM-71 ~ EM-77）
backend/migrations/0231_formation_twin_emd_analytics.sql                 8 张表 + 索引 + Owner RLS
backend/migrations/rollback/0231_..._down.sql                            手动回滚
backend/routers/formation_twin_emotional_maturity.py                     新增 8 个端点
backend/tests/test_formation_twin_emotional_maturity_analytics.py        39 个测试
```

## 2. 三个平面

| 平面 | Skill | 职责 |
| --- | --- | --- |
| Measurement | EM-71 / EM-72 / EM-73 | 指标语义注册、自适应复测、基线可比性 |
| Analytics | EM-74 / EM-75 / EM-76 | 趋势与转折点、跨场景泛化、归因与恶化风险 |
| Reporting | EM-77 | 用户控制的成长报告 |

## 3. 关键约束

- **指标语义唯一**：`pause_success_rate` 只能有一个定义；比率型指标必须同时声明分子与分母，
  并声明可用证据类型。冻结版本被改写 → `FROZEN_METRIC_REDEFINED`；跨版本改单位 → `UNIT_CONFLICT`。
  数据库层 `UNIQUE(metric_code, version)` + `CHECK(unit <> 'RATE' OR 分子分母非空)`。
- **版本漂移即不可比**：Rubric、题库、模型、引擎、指标任一版本变化 → `NOT_COMPARABLE` 并要求重算，
  不做静默比较。
- **小于测量误差 = 无法确认变化**：`CHANGE_NOT_CONFIRMED`，而不是「略有改善」。
- **趋势不作因果断言**：转折点带 `causal_claim: false`；数据库层 `CHECK(causal_claim = FALSE)`。
- **归因永远是相关性**：`attribution_claim` 恒为 `CORRELATION_ONLY`，且必须至少带一条替代解释
  （数据库层 `CHECK(jsonb_array_length(alternative_explanations_json) > 0)`）。
  出现安全信号立即 `SAFETY_FIRST` 并转安全流程。
- **报告零分数**：`情感成熟度：/ 综合生命指数 / 排名前` 等措辞一律拦截；
  `total_score` 与 `ranking` 在数据库层被强制为 NULL；
  报告必须包含「没有变化」与「仍然未知」两节；图表默认用置信度带与时间分桶，不给假精度。
- **用户批准后才存在**：未批准只能是 `DRAFT_AWAITING_USER_APPROVAL`；牧养视图与小组视图需要分享同意、
  逐字段选择、到期与撤回（数据库层 `CHECK(status <> 'PUBLISHED' OR user_approved = TRUE)`）。

## 4. 新增 API

```http
GET  /api/v1/formation-twin/emotional-maturity/analytics/overview
POST /api/v1/formation-twin/emotional-maturity/analytics/metrics
POST /api/v1/formation-twin/emotional-maturity/analytics/reassessment
POST /api/v1/formation-twin/emotional-maturity/analytics/comparability
POST /api/v1/formation-twin/emotional-maturity/analytics/trajectory
POST /api/v1/formation-twin/emotional-maturity/analytics/generalization
POST /api/v1/formation-twin/emotional-maturity/analytics/attribution
POST /api/v1/formation-twin/emotional-maturity/analytics/report
```

## 5. 测试结果

```text
tests/test_formation_twin_emotional_maturity_analytics.py    39 passed
```
