# EMD-OS Batch 7 Report — 哀伤、有限、安息与属灵逃避治理（EM-54 ~ EM-61）

Date: 2026-07-28
Scope: 丧失与影响地图、哀伤与哀歌陪伴、控制／影响／责任校准、模糊丧失与未完成告别、
属灵逃避检测、交托与纪念仪式、每日暂停与安息节奏、14/30/90 整合评估。

## 1. 交付物

```text
backend/formation_twin/emotional_maturity_grief.py                   引擎（EM-54 ~ EM-61）
backend/migrations/0229_formation_twin_emd_grief_rest.sql            8 张表 + 索引 + Owner RLS
backend/migrations/rollback/0229_..._down.sql                        手动回滚
backend/routers/formation_twin_emotional_maturity.py                 新增 9 个端点
backend/tests/test_formation_twin_emotional_maturity_grief.py        43 个测试
```

## 2. 八个必须严格区分的概念

1. 接纳 ≠ 认同：可以承认关系已经结束，同时仍认为对方的欺骗是错的并保留追责。
2. 交托 ≠ 消极放弃：「一切交给神就不用去治疗了」被 `UnsafeContentError` 直接拦截。
3. 哀伤 ≠ 属灵失败：仍在流泪或困惑不会被判定为缺乏信心、没有宽恕或不成熟。
4. 安息 ≠ 逃避责任：安息的目的是之后能更自由地承担该承担的。
5. 停止工作 ≠ 恢复：行为停止、身体恢复、注意力脱离、情绪恢复、休息负罪感、重新承担能力**六轴分别测量**。
6. 宽恕 ≠ 结束哀伤。
7. 意义 ≠ 过早意义化：系统不代神宣告这件事的理由。
8. 纪念 ≠ 迷信：仪式不产生超自然效力，也不是与神交换条件。

## 3. 丧失与整合等级 GI0–GI6

命名丧失 → 识别次生影响 → 责任与有限分离 → 容纳哀伤并采取现实行动 → 建立恢复与安息节奏 →
纵向整合。这不是「哀伤完成度」，而是与丧失、有限和现实生活相处的整合能力；
数据库层 `CHECK(grief_completed = FALSE)` 保证系统永远不声称哀伤已完成。

## 4. 属灵逃避检测（EM-58）

七类：过早意义化、情绪压抑、责任回避、强迫宽恕、宣称神意、以受苦为荣、以祷告替代帮助。
每一类都配一条诚实的重构说明，并明确「本检查不是禁止属灵操练，而是防止属灵语言被用来压抑现实」。
`spiritual_framework = neutral` 时不提供任何属灵选项。

## 5. 其他硬约束

- 模糊丧失表 `closure_claimed` 恒为 FALSE —— 系统不制造「结案」。
- 仪式表 `claims_efficacy` 恒为 FALSE。
- 哀伤陪伴永不设定时间表；纪念日反弹显式标注为「不计为退步」。
- 整合评估必须附带归因限制（环境、支持系统、身体状况同样会影响结果）。

## 6. 新增 API

```http
GET  /api/v1/formation-twin/emotional-maturity/grief/overview
POST /api/v1/formation-twin/emotional-maturity/grief/loss-map
POST /api/v1/formation-twin/emotional-maturity/grief/companion
POST /api/v1/formation-twin/emotional-maturity/grief/control-calibration
POST /api/v1/formation-twin/emotional-maturity/grief/ambiguous-loss
POST /api/v1/formation-twin/emotional-maturity/grief/bypassing-check
POST /api/v1/formation-twin/emotional-maturity/grief/ritual
POST /api/v1/formation-twin/emotional-maturity/grief/rest-rhythm
POST /api/v1/formation-twin/emotional-maturity/grief/integration
```

## 7. 测试结果

```text
tests/test_formation_twin_emotional_maturity_grief.py    43 passed
```
