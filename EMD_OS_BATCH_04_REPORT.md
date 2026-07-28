# EMD-OS Batch 4 Report — 情绪觉察与调节训练系统（EM-28 ~ EM-35）

Date: 2026-07-28
Scope: 干预层。目标不是让用户「没有情绪」，而是在「触发 → 身体激活 → 情绪与意义 → 行动冲动 →
实际行为 → 后果 → 恢复」这条链路上尽早恢复选择能力。

## 1. 交付物

```text
backend/formation_twin/emotional_maturity_regulation.py                    引擎（EM-28 ~ EM-35）
backend/migrations/0226_formation_twin_emd_regulation.sql                  8 张表 + 索引 + Owner RLS
backend/migrations/rollback/0226_..._down.sql                              手动回滚
backend/routers/formation_twin_emotional_maturity.py                       新增 9 个端点
backend/tests/test_formation_twin_emotional_maturity_regulation.py         48 个测试
```

## 2. 激活分区与路由

| 分区 | 默认区间 | 路由 |
| --- | --- | --- |
| GREEN | 0–3 | 觉察与反思 |
| AMBER | 4–6 | EM-31 暂停协议 |
| RED | 7–8 或存在高冲动 | EM-32 冲动阻断 → EM-33 共同调节 |
| CRISIS | 9–10 且无法保证安全，或自伤/伤人/暴力/危险驾驶 | 现有 Crisis & Safety System |

路由从不只由一个数字决定：环境不安全、无法停止行动、存在待执行的不可逆行动，都会把分区抬到 RED；
危机信号直接抬到 CRISIS。数据库层用 `CHECK(deep_dive_allowed = FALSE OR activation_band IN ('GREEN','AMBER'))`
保证高激活时不做深度下潜。

## 3. 八个 Skill

- **EM-28 情绪精确命名**：分离事实／解释／情绪候选／行动冲动；候选最多 3 个且永远是
  `CANDIDATE_AWAITING_USER_CONFIRMATION`；愤怒不被自动解释为「次级情绪」；用户可以给出系统没列出的词。
  实时模式走短路径，训练模式提供易混淆对（内疚 vs 羞耻、失望 vs 羞耻、孤单 vs 被拒绝……）。
- **EM-29 身体信号扫描**：记录最早出现的身体信号；胸痛、呼吸困难、眩晕、心悸、麻木、昏倒
  一律退出情绪训练，只记录「用户报告了身体不适；原因未知」，并显式禁止解释为焦虑。
- **EM-30 触发预警建模**：至少 2 个真实事件才建模，输出 `DRAFT_AWAITING_USER_CONFIRMATION`，
  给出触发签名、最早身体信号、典型冲动与升级时间中位数。
- **EM-31 神圣暂停**：六步「停稳辨选告复」，P1 30–90 秒 / P2 10–20 分钟 / P3 2–24 小时；
  「告」与「复」防止暂停退化为冷暴力；关系安全存疑时不要求通知对方；双方都高激活强制 P3。
- **EM-32 冲动阻断**：四类可逆性；草稿保存但禁止发送、延迟窗口、摩擦层、替代行动、可选问责陪伴；
  `SAFETY_CRITICAL` 不进入普通阻断而走危机流程；用户始终可以覆盖（系统只加一步，不替用户决定）。
- **EM-33 共同调节路由**：七种支持类型；只路由双向同意、且本人同意过该支持类型的联系人；
  冲突对象永不作为支持者；只共享激活等级与求助类型，不共享事件细节，系统不代发消息。
- **EM-34 恢复计划**：三个时间层（10 分钟 / 2 小时 / 24–72 小时）× 四类恢复（行为、功能、情绪、关系），
  与 Batch 3 的恢复指标一一对应；明确「不要求你立刻不难过、不要求你立刻原谅」。
- **EM-35 旧模式复现演练**：三级梯度（Level 2 只改一个变量），If-Then 卡必含「暂停失败怎么办」
  与「如果我已经发出去了怎么办」；暴力情境不进入演练；用词是「旧模式复现」而非「复发者」。

## 4. 属灵语言的边界

祷告、诗篇默想、与肢体一起祷告可以作为**可选**支持出现，并且始终附带
「不用来替代安全、医疗或专业帮助，也不要求你立刻停止难过」。
`spiritual_framework = neutral` 时，祷告类支持与属灵建议整体不出现。

## 5. 新增 API

```http
GET  /api/v1/formation-twin/emotional-maturity/regulation/overview
POST /api/v1/formation-twin/emotional-maturity/regulation/label
POST /api/v1/formation-twin/emotional-maturity/regulation/body-scan
POST /api/v1/formation-twin/emotional-maturity/regulation/trigger-profile
POST /api/v1/formation-twin/emotional-maturity/regulation/pause
POST /api/v1/formation-twin/emotional-maturity/regulation/impulse-guard
POST /api/v1/formation-twin/emotional-maturity/regulation/coregulation
POST /api/v1/formation-twin/emotional-maturity/regulation/recovery-plan
POST /api/v1/formation-twin/emotional-maturity/regulation/rehearsal
```

数据库层另有两条硬约束：共同调节请求的 `message_auto_sent` 与 `event_details_shared` 恒为 FALSE。

## 6. 测试结果

```text
tests/test_formation_twin_emotional_maturity_regulation.py    48 passed
```
