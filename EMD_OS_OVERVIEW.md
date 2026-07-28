# EMD-OS 总览 — 情感成熟度诊断系统（EM-01 ~ EM-87 全部实现）

Date: 2026-07-28
定位：EMD-OS 不是独立于属灵星球的「情感星球」，而是 `formation_twin` 的一个诊断域，
位于仓库既有十余个训练引擎的上游；生产认证层则并入既有 `production_governance` 包。

## 1. 十个批次一览

| Batch | Skills | 模块 | 迁移 | 测试 |
| --- | --- | --- | --- | --- |
| 1 诊断治理底座 | EM-01~10 | `formation_twin/emotional_maturity.py` | 0223 | 53 |
| 2 题库与行为证据 | EM-11~19 | `formation_twin/emotional_maturity_items.py` | 0224 | 54 |
| 3 现实事件与纵向验证 | EM-20~27 | `formation_twin/emotional_maturity_events.py` | 0225 | 42 |
| 4 情绪觉察与调节 | EM-28~35 | `formation_twin/emotional_maturity_regulation.py` | 0226 | 48 |
| 5 家庭脚本与真我整合 | EM-36~43 | `formation_twin/emotional_maturity_family.py` | 0227 | 45 |
| 6 边界、冲突与关系修复 | EM-44~53 | `formation_twin/emotional_maturity_conflict.py` | 0228 | 48 |
| 7 哀伤、有限与安息 | EM-54~61 | `formation_twin/emotional_maturity_grief.py` | 0229 | 43 |
| 8 Twin／身份／祷告／牧养整合 | EM-62~70 | `formation_twin/emotional_maturity_integration.py` | 0230 | 40 |
| 9 复测、趋势与报告 | EM-71~77 | `formation_twin/emotional_maturity_analytics.py` | 0231 | 39 |
| 10 生产认证与事故治理 | EM-78~87 | `production_governance/emd_certification.py` | 0232 | 48 |

合计：**87 个 Skill、10 个引擎模块、10 个迁移（共 78 张表）、约 90 个 API 端点、460 个新测试**。

## 2. 完整运行闭环

```text
用户授权（分项、可独立撤回）
→ 安全分流（复用 crisis_engine，风险只能升级）
→ 十维自适应评估（题库 + 压力情境 + 行为锚点）
→ 现实事件与四类恢复
→ 关系修复与信任重建
→ 情绪调节、家庭脚本、真我整合、哀伤与安息训练
→ Formation Twin / 身份 / 祷告 / 习惯 / 牧养 / 群体整合
→ 14/30/90 复测、趋势、泛化与归因
→ 用户批准的成长报告
→ 生产认证、上线监测、事故召回与重新认证
```

## 3. 融入既有模块（未重造）

| 能力 | 复用的既有模块 |
| --- | --- |
| 危机识别与分级 | `crisis_engine.triage` |
| 属灵／人格／诊断输出拦截 | `formation_twin/formation_safety.py` + `theological_safety.py` |
| 情绪状态与本体 | `formation_twin/emotional_engine.py`、`emotion_ontology` |
| 十维训练干预 | anger / comfort / burnout / suffering / repentance / conscience / grace_identity / narrative / adoption / loneliness / fear_of_man / rule_of_life / neighbor_love / ordo_amoris / forgiveness / tender_heart / lament / waiting / contentment / sabbath / emotionally_healthy |
| 发布治理、评测与场景 | `production_governance/{scenarios,evaluation,release}.py` |
| 多租户与 RLS 模式 | `core/tenancy.py` + 既有 `ft_owner_policy` 约定 |

## 4. 贯穿全系统的硬规则

1. 不存在任何总分、指数或用户间排名（代码 + 数据库双重拦截）。
2. 证据不足只能是 E0/GI0/G0，绝不推断阶段。
3. 自述封顶 E2、情境意向封顶 E3；只有跨场景真实行为才支持高置信度。
4. 安全永远优先：ELEVATED/IMMINENT 阻断评估与训练，直接转既有危机系统。
5. 不安全关系（家暴、性暴力、跟踪威胁、强制控制、宗教权威滥用）不进入修复、演练或脆弱表达流程。
6. 不诱导记忆、不远程诊断第三方、不指派永久依恋类型或人格标签。
7. 属灵语言不得用于压抑现实；系统从不代神说话（`神告诉你…` 一律拦截）。
8. 牧者／小组长默认零权限；一切分享字段级、可预览、可撤回、有期限、从不自动发送。
9. 群体反馈权重上限 0.3，且永不用于资格、按立或纪律。
10. 任何变化结论都必须附带替代解释，且从不作因果断言。

## 5. 当前状态

```json
{
  "architecture_status": "DESIGN_COMPLETE",
  "implementation_status": "EM-01 ~ EM-87 IMPLEMENTED",
  "verification_status": "NOT_VERIFIED_IN_PRODUCTION",
  "psychometric_status": "NOT_EVALUATED",
  "privacy_status": "NOT_ASSESSED",
  "security_status": "NOT_REDTEAMED",
  "production_certificate": "NOT_ISSUED"
}
```

代码层面的闸门、契约与拒绝规则已经全部就位；真实的心理测量研究、认知访谈、隐私影响评估、
红队执行与九项人类签署尚未发生。在这些证据真实存在之前，本域只能按
`IU-1 私人自我反思 / exploratory` 呈现，不得声称任何外部认证或临床能力。

## 6. 验收

```text
EMD-OS 全部批次（含 Batch 10 生产认证）        460 passed
formation_twin 全量回归（含既有批次）           658 passed
迁移文件总数                                    221（最新 0232）
```

Python 3.10 沙箱下 `test_formation_twin_contracts.py` 有一处既有失败
（`datetime.fromisoformat` 在 3.11 之前不接受 `Z` 后缀），与本次改动无关。
