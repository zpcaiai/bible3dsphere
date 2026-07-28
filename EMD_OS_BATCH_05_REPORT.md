# EMD-OS Batch 5 Report — 依恋、家庭脚本与真我整合（EM-36 ~ EM-43）

Date: 2026-07-28
Scope: 三代家庭图、家庭脚本／角色／三角关系、依恋激活循环、自我分化训练、早年生存誓言重构、
虚假自我面具、真我罗盘、安全脆弱表达实验。

## 1. 交付物

```text
backend/formation_twin/emotional_maturity_family.py                   引擎（EM-36 ~ EM-43）
backend/migrations/0227_formation_twin_emd_family_self.sql            8 张表 + 索引 + Owner RLS
backend/migrations/rollback/0227_..._down.sql                         手动回滚
backend/routers/formation_twin_emotional_maturity.py                  新增 9 个端点
backend/tests/test_formation_twin_emotional_maturity_family.py        45 个测试
```

## 2. 模式证据等级 FP0–FP5

抽象评价永远停在 FP0；重复事件 FP2；多关系重复 FP3；与现实行为形成连接 FP4；
30/90 天纵向验证并经用户确认 FP5。**只有 FP4 以上才允许写入长期 Formation Twin**，
数据库层用 `CHECK(may_write_to_twin = FALSE OR evidence_level IN ('FP4','FP5'))` 兜底。

## 3. 八个 Skill 与其硬边界

- **EM-36 三代家庭图**：只记录用户报告的可观察行为；`自恋型人格 / 边缘型 / 人格障碍 / 焦虑型依恋者`
  等第三方诊断词直接拦截；记忆材料必须标来源，`system_hypothesis` 与「模糊印象」不进入家庭历史。
- **EM-37 家庭脚本／角色／三角关系**：8 条常见脚本、8 种角色、三角关系记录为可观察模式，
  每条各自携带 FP 等级与 `may_write_to_twin`。
- **EM-38 依恋激活循环**：七步循环 + 追逐／退缩／控制／混合四类保护动作；
  `attachment_type_assigned` 恒为 `None`（数据库层 `CHECK(attachment_type_assigned IS NULL)`），
  输出必须绑定关系对象、触发条件、压力水平、时间范围与证据等级，并主动指出「在其他情境中没有观察到」。
- **EM-39 自我分化**：SD0–SD5 + 五步协议（稳定自己／说出我的位置／承认关系／归还责任／保持连接或安全距离）；
  激活 ≥7 时先回到 Batch 4 的暂停协议，不在高激活时练习。
- **EM-40 早年生存誓言重构**：四道前置条件（用户同意、激活 ≤5、无危机、材料属事实性来源）；
  诱导式话术（「你小时候一定……」）直接拦截；输出保留「过去解释来源，成年后行为仍由自己负责」；
  「内在孩童」可替换为「过去的自己／早年生存反应／旧的核心信念」，拒绝不算抗拒成长。
- **EM-41 虚假自我面具**：8 种面具，每种都写明「当年保护了什么」与「现在的代价」，并强调面具不是虚伪、
  不是人格定义。
- **EM-42 真我罗盘**：身份／价值／限度／恩赐／责任／关系承诺六部分，显式列出「真我不是想做什么就做什么」，
  并要求限度与责任同时存在。
- **EM-43 脆弱表达实验**：V1–V5 深度；`UNSAFE` 关系完全不生成实验；`CAUTION/UNKNOWN` 封顶 V2 且只保留
  事实／请求／边界三段；高权力差封顶 V2；首次实验从 V1–V2 起步；激活 ≥7 延后。
  成功标准只由用户自己的行为定义（对方是否同意、是否道歉不算成功标准）。

数据库层另有两条约束：不安全关系的 `depth` 必须为 NULL；`CAUTION/UNKNOWN` 的 `depth` 只能是 V1/V2。

## 4. 饶恕四分法

`FORGIVENESS_DISTINCTIONS` 明确区分：停止报复 / 释放对结果的执着 / 饶恕 / 重新信任 / 恢复接触 / 关系和好。
它们不是同一件事；持续伤害中保持距离可能正是成熟边界。Batch 6 会继续使用这套区分。

## 5. 新增 API

```http
GET  /api/v1/formation-twin/emotional-maturity/family/overview
POST /api/v1/formation-twin/emotional-maturity/family/genogram
POST /api/v1/formation-twin/emotional-maturity/family/scripts
POST /api/v1/formation-twin/emotional-maturity/family/attachment-cycle
POST /api/v1/formation-twin/emotional-maturity/family/differentiation
POST /api/v1/formation-twin/emotional-maturity/family/oath-reframe
POST /api/v1/formation-twin/emotional-maturity/family/masks
POST /api/v1/formation-twin/emotional-maturity/family/true-self
POST /api/v1/formation-twin/emotional-maturity/family/vulnerability-experiment
```

## 6. 测试结果

```text
tests/test_formation_twin_emotional_maturity_family.py    45 passed
```
