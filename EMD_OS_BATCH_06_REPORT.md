# EMD-OS Batch 6 Report — 同理心、边界、清洁冲突、道歉、宽恕与修复（EM-44 ~ EM-53）

Date: 2026-07-28
Scope: 关系层。十个 Skill 覆盖同理心、心智化、边界权责、边界执行阶梯、清洁冲突议题、冲突对话、
负责任的道歉、宽恕辨析、修复补偿计划、修复成效与信任决策路由。

## 1. 交付物

```text
backend/formation_twin/emotional_maturity_conflict.py                   引擎（EM-44 ~ EM-53）
backend/migrations/0228_formation_twin_emd_conflict_repair.sql          8 张表 + 索引 + Owner RLS
backend/migrations/rollback/0228_..._down.sql                           手动回滚
backend/routers/formation_twin_emotional_maturity.py                    新增 11 个端点
backend/tests/test_formation_twin_emotional_maturity_conflict.py        48 个测试
```

## 2. 七个必须严格区分的概念（全部有测试）

| # | 区分 | 代码强制方式 |
| --- | --- | --- |
| 1 | 同理心 ≠ 同意 | 输出中出现「所以他这样做是合理的」直接 `UnsafeContentError`；伤害行为始终列在 `still_true_regardless` |
| 2 | 心智化 ≠ 读心 | 「他就是故意…」被改写为假设 + 三个澄清问题，状态恒为 `UNVERIFIED_HYPOTHESIS` |
| 3 | 边界 ≠ 控制 | 「你必须承认…否则我就…」被拦截；边界只描述「我会怎么做」 |
| 4 | 清洁冲突 ≠ 无情绪 | 允许愤怒、失望、哭泣、明确说不；八类脏冲突成分逐条检测 |
| 5 | 道歉 ≠ 自我羞辱 | 六种无效道歉模式检测（如果式／但是式／自我贬低／催促原谅／抽象式／只修形象） |
| 6 | 宽恕 ≠ 信任 ≠ 和好 ≠ 恢复角色 | 八项分离模型，每项标注是否依赖对方；`system_conclusion` 恒为 None |
| 7 | 修复行为 ≠ 关系必然恢复 | 修复计划显式声明「不保证关系恢复」；对方反应不改变阶段 |

## 3. 关键阶梯

- **关系证据等级 RE0–RE6**：抽象原则 → 模拟表达 → 现实尝试 → 48–72 小时验证 → 数周持续 →
  双方秩序改善 → 跨场景整合。重新见面本身不等于 RE5。
- **边界执行阶梯 L0–L5**：明确一次 → 简短重复 → 减少暴露 → 结构性保护 → 第三方支持 → 安全退出。
  出现安全风险可直接跳到 L5；执行目的是保护自己，不是让对方难堪。
- **信任重建阶梯 TR0–TR5**：按领域分别评估（情绪保密、时间可靠性、财务、照顾孩子、工作权限、
  属灵带领权、身体安全）。信任不是 0/100，也不是原谅与否。

## 4. 数据库层的硬约束

- `formation_twin_emd_apologies.auto_sent` 恒为 FALSE —— 系统从不代发道歉。
- `formation_twin_emd_forgiveness_maps.system_conclusion` 恒为 NULL —— 系统不判定用户是否已宽恕。
- `formation_twin_emd_trust_assessments.system_decides` 恒为 FALSE —— 只给选项，不做决定。
- 共享修复工作区（`MUTUAL_WORKSPACE`）为 READY 时必须 `both_parties_consented = TRUE`。
- 状态为 READY 的冲突议题必须写明单一议题。

## 5. 新增 API

```http
GET  /api/v1/formation-twin/emotional-maturity/conflict/overview
POST /api/v1/formation-twin/emotional-maturity/conflict/perspective
POST /api/v1/formation-twin/emotional-maturity/conflict/motive-calibration
POST /api/v1/formation-twin/emotional-maturity/conflict/boundary
POST /api/v1/formation-twin/emotional-maturity/conflict/enforcement
POST /api/v1/formation-twin/emotional-maturity/conflict/issue
POST /api/v1/formation-twin/emotional-maturity/conflict/dialogue
POST /api/v1/formation-twin/emotional-maturity/conflict/apology
POST /api/v1/formation-twin/emotional-maturity/conflict/forgiveness
POST /api/v1/formation-twin/emotional-maturity/conflict/restitution
POST /api/v1/formation-twin/emotional-maturity/conflict/outcome
```

## 6. 测试结果

```text
tests/test_formation_twin_emotional_maturity_conflict.py    48 passed
```
