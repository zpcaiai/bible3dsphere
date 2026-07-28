# EMD-OS 试点清单（PILOT 配置档）

Date: 2026-07-28
适用：个人或少数试点用户。证书上限 `RESTRICTED_PILOT`，报告必须继续标注 `exploratory`，
试点期不开启牧养分享与小组功能。

```json
POST /api/v1/assurance/emd/checklist  {"profile": "PILOT"}
{
  "profile": "PILOT",
  "max_certifiable_level": "RESTRICTED_PILOT",
  "ready_for_pilot_use": true,
  "outstanding_blocking_items": [],
  "auto_verified_items": ["DELETION_PROPAGATION", "MODEL_TRAINING_OPTOUT",
                          "SAFETY_E2E", "SHARING_OFF", "UI_LABELS"]
}
```

自动核验只证明测试文件、实现模块与路由接线存在且可导入；「测试通过」由 CI 判定。
传 `auto_verify: false` 可以看到未接线时的原始状态（`ready_for_pilot_use: false`）。

---

## 0. PILOT 放宽了什么、没放宽什么

**放宽（只有 G1 心理测量与 G3 公平性）**

| 设置 | PILOT | PRODUCTION |
| --- | ---: | ---: |
| 每语言试点样本 | 20 | 300 |
| 每语言认知访谈 | 5 | 15 |
| 开放文本评分一致性 | 0.70 | 0.75 |
| 重测信度 | 0.60 | 0.70 |
| 个体趋势信度 | 0.70 | 0.80 |
| 公平性最小组样本 | 5 | 30 |
| 证据等级上限 | PM3 | PM5 |
| 必要签署 | 5 项 | 9 项 |

**永不放宽（四道闸门在两档配置中完全一致）**

- G0 用途与禁止用途：IU-X 永久禁止，未成年人独立认证
- G4 领域安全：15 类伤害必须覆盖，7 类零容忍
- G5 隐私与个人权利：删除传播、分项同意、默认关闭训练、牧者零默认权限
- G6 LLM / Agent 安全：六项零容忍红队结果

---

## 1. 五项 MUST_DO —— 全部完成

### ✅ SAFETY_E2E — 危机路由端到端验证

`tests/test_emd_safety_end_to_end.py`，33 个用例覆盖 16 个下游面，外加「普通痛苦不得被过度危机化」的反向用例。

发现并修复两个真实缺口：

1. 「我真的想伤害我自己」原先判为 NONE → 现由 EMD 侧兜底规则升到 IMMINENT
2. 「他威胁说如果我离开就杀了我」原先只到 CONCERN → 现升到 ELEVATED 且标记关系 CAUTION

兜底规则只能抬高风险、永不降低（`_LIFE_RISK_PATTERNS`）。

### ✅ DELETION_PROPAGATION — 删除传播

`tests/test_emd_deletion_propagation.py`（18 个结构用例 + 3 个集成用例）、迁移 `0233_emd_erasure_propagation.sql`。

发现并修复三个真实缺口：

1. **账户级删除漏掉整个 EMD 域**。`erase_user_data()`（0145）的表清单是快照，EMD 的 71 张表在 0223+ 才出现，从未被纳入。
2. **向量库从未被删除**。`mvfe_memories` 存放用户原文与向量，是 user_id 键表且建在 `migrations/` 之外，快照不可能列到它。
3. **22 张 user_id 个人表同样在覆盖之外**（attention_*、mission_bridge_*、safeguarding_*）。

修法不是再抄一份快照，而是改成从系统目录动态发现：

```sql
SELECT * FROM erasure_coverage_gaps();   -- 必须返回零行
SELECT * FROM emd_erasure_coverage();    -- uncovered 必须为空
```

结构测试从迁移文件重新推导个人表集合，并与删除清单比对——将来新增个人表却忘了接线，测试会失败，而不是数据静默残留。
11 个删除目标各自映射到具体机制（`emotional_maturity_erasure.DELETION_PLAN`），
其中只有 BACKUPS 无法即时清除，删除回执如实告诉用户「保留期内自然过期」。

### ✅ MODEL_TRAINING_OPTOUT — 训练退出

`formation_twin/emotional_maturity_training_optout.py`。四层保障：

- `classify_material()` — 字段名与正文双通道判级；「我昨天为父亲的病祷告」按 P3 处理，即使字段名无害
- `sanitize_provider_call()` — **抛异常而不是警告**；未登记的供应商不能用于 EMD 材料
- 调用方传入的 `store: True` 会被强制覆写为 `False`
- `POST /emotional-maturity/training-optout/audit` — 六问审计，任一未过即 `emd_material_allowed: false`

剩余人工动作：对着供应商控制台跑一次审计接口，把 PASS 结果贴进隐私评估。

### ✅ UI_LABELS — 展示契约

`formation_twin/emotional_maturity_presentation.py` + `GET /emotional-maturity/display-contract`。

- 阶段展示必须同时带情境、时间范围、置信度，缺一个直接抛异常
- `validate_ui_payload()` 拒绝分数、百分位、排名、诊断、永久化人格与属灵评判措辞
- 明确禁止进度条、仪表盘、雷达图、排行榜、百分位徽章
- PILOT 档标签：`exploratory` / `非临床` / `个人反思用途` / `试点版本`

契约由后端提供而非写在文档里，前端只要拉取即可，契约测试在后端侧失败。

### ✅ SHARING_OFF — 关闭分享与小组

`formation_twin/emotional_maturity_pilot_gate.py`。默认档为 PILOT（**默认最保守，需显式配置才能开放**）。

- 同意接口不提供 `EMD_PASTORAL_SHARE`；直接构造请求也会被 `enforce_scope_request` 剥掉
- 四个接口经 `guard_feature` 返回 403：牧养摘要、转介、小组操练、社群反馈
- `EMD_ASSURANCE_PROFILE=PRODUCTION` 才会开放

---

## 2. 用户变多或开启分享前（5 项，仍待人工）

| 项目 | 工作量 | 验收 |
| --- | --- | --- |
| 轻量红队（真实 RAG + 工具栈） | 1 天 | 14 个攻击面各 ≥1 条；六项零容忍全 PASS |
| 认知访谈 5–10 人 | 5–10 人 × 30 分钟 | 每维度至少一题被逐字复述并确认理解一致 |
| 开放文本评分一致性抽查 | 30 条回答 | 一致率 ≥ 0.70 |
| 隐私影响评估（PIPL / GDPR） | 需专业审查 | 数据清单、目的、依据、留存、跨境、个人权利映射 |
| 事故熔断与回滚演练 | 半天 | staging 触发一次 SEV1 并完成召回与重算 |

另需在真实数据库上跑一次集成用例（`pytest -m integration tests/test_emd_deletion_propagation.py`），
确认 `erasure_coverage_gaps()` 在你的实际 schema 上也返回零行。

---

## 3. 面向公众之前（3 项）

- 每主要语言 300 份试点样本（PM4+）
- 完整公平性审计：DIF、测量不变性、安全公平、无障碍
- 九项独立签署（含心理测量负责人、牧养神学审核者、独立复核人）
