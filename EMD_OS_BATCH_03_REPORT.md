# EMD-OS Batch 3 Report — 真实行为与纵向成长验证（EM-20 ~ EM-27）

Date: 2026-07-28
Scope: 真实事件采集、触发—反应—恢复时间线、四种恢复指标、关系修复验证、训练迁移与提示依赖、
复发与情境泛化、14/30/90 检查点调度、纵向成长评估。

## 1. 交付物

```text
backend/formation_twin/emotional_maturity_events.py                    引擎（EM-20 ~ EM-27，纯确定性）
backend/migrations/0225_formation_twin_emd_real_life_events.sql        8 张表 + 索引 + Owner RLS
backend/migrations/rollback/0225_..._down.sql                          手动回滚
backend/routers/formation_twin_emotional_maturity.py                   新增 8 个端点
backend/tests/test_formation_twin_emotional_maturity_events.py         42 个测试
```

## 2. 事件模型

统一时间轴 T-1 → T8（事件前状态、触发、即时解释、情绪与身体、第一反应、调节尝试、第二选择、
关系处理、恢复、学习）。空白节点保持 `UNKNOWN`，引擎不替用户补全记忆；转折点只是观察，
显式标记 `causal_claim: false`。

真实行为证据等级 RL0–RL5：抽象表达 RL0、回顾事件 RL1、24 小时内记录 RL2、48–72 小时复核 RL3、
完成具体沟通/补偿/改变 RL4、多次多场景稳定 RL5。

## 3. 关键约束（由代码与测试强制）

- **四种恢复分开计算**：行为控制、功能、情绪、关系。情绪仍难过但已停止伤害行为 → 行为恢复良好；
  快速恢复工作不等于成熟，持续有情绪也不等于不成熟。
- **区分冲动与执行冲动**：`urge_without_action` 记为自我控制证据，不记为伤害行为。
- **只与用户自己的历史比较**：少于 2 条可比历史时输出 `INSUFFICIENT_HISTORY`，用中位数而非均值。
- **修复只评估用户可负责的部分**：R0–R5 阶段完全由用户行为与质量要素决定；
  对方拒绝原谅、拒绝回应或关系结束，都不改变阶段（`other_party_response_affects_stage: false`）。
  道歉中夹带反击或旧账，停在 R2。
- **不安全关系不进入普通修复流程**：家暴、性暴力、跟踪威胁、强制控制、宗教权威滥用、
  严重报复风险、儿童或弱势受害 → 直接 R0 + `SAFETY_FIRST`，并明说「安全退出就是成熟行为」。
- **迁移必须有事件证据**：T0–T6 与提示依赖 P4→P0 分开记录；使用系统完整脚本成功仍然算数，
  只是提示依赖等级更高，系统提示不会抹掉已观察到的进步。
- **模式不是人格**：循环名称（边界内疚循环、拒绝恐慌循环等）只是事件模式，不是医学诊断；
  少于 3 次事件时返回 `INSUFFICIENT_EVENTS` 并说明「这不代表用户有问题」。
- **不制造冲突**：14/30/90 检查点若没有可比事件，输出 `INSUFFICIENT_EVIDENCE_FOR_CHANGE`
  并提供回顾/延后/跳过选项，明确禁止要求或暗示用户制造一次冲突。
- **归因限制**：每一次成长评估都必须附上替代解释（触发机会变化、睡眠与工作强度、环境或对象变化、
  记录意愿变化、对方反应不同），并禁止把一次成功显示为稳定、把打卡当能力、因一次复发取消已观察到的改变。
  数据库层用 `CHECK(result = 'INSUFFICIENT_EVIDENCE' OR comparable_event_count >= 1)` 兜底。

## 4. 新增 API

```http
GET  /api/v1/formation-twin/emotional-maturity/events/overview
POST /api/v1/formation-twin/emotional-maturity/events
POST /api/v1/formation-twin/emotional-maturity/events/recovery
POST /api/v1/formation-twin/emotional-maturity/events/repair
POST /api/v1/formation-twin/emotional-maturity/transfer
POST /api/v1/formation-twin/emotional-maturity/patterns
POST /api/v1/formation-twin/emotional-maturity/checkpoints
POST /api/v1/formation-twin/emotional-maturity/checkpoints/evaluate
```

第三方姓名在入库前被统一替换为「对方」；事件正文只保留用户自己划分的客观事实与解释条目，
不保存日记式叙述。删除接口已覆盖 Batch 1–3 全部 23 张表。

## 5. 测试结果

```text
tests/test_formation_twin_emotional_maturity_events.py       42 passed
EMD-OS Batch 1 + 2 + 3 合计                                  151 passed
formation_twin 全量（12 个文件）                              358 passed, 1 failed
```

唯一失败项 `test_formation_twin_contracts.py::test_checked_in_json_schema_validates_the_python_contract_sample`
是既有测试在 Python 3.10 沙箱下的环境问题（`fromisoformat` 在 3.11 之前不接受 `Z` 后缀），与本批次无关。

## 6. 当前状态

```json
{
  "architecture_status": "BATCH_1_3_IMPLEMENTED",
  "implementation_status": "EM-01 ~ EM-27 done, EM-28 ~ EM-87 pending",
  "psychometric_status": "NOT_EVALUATED",
  "privacy_status": "NOT_ASSESSED",
  "security_status": "NOT_REDTEAMED",
  "production_certificate": "NOT_ISSUED"
}
```

Batch 1–3 已构成完整的「授权 → 安全 → 评估 → 证据 → 现实行为 → 纵向验证」闭环。
后续 Batch 4–7 是训练层（情绪命名与冲动阻断、家庭脚本与依恋、同理心与冲突修复、哀伤与安息），
Batch 8 是与身份／祷告／习惯／牧养的整合，Batch 9 是趋势与报告，
Batch 10 的生产认证应并入既有 `backend/production_governance/`，而不是另起模块。
在心理测量证据、隐私评估与红队结果真实存在之前，本域只能按 `IU-1 私人自我反思 / exploratory` 呈现。
