# Mission OS 集成映射（端到端逻辑主线）

Mission OS 的六个批次不是孤立模块，而是一条从「感动」到「具备部署条件」的
生命周期主线，由 `backend/mission_os/pipeline.py` 显式编码并由
`tests/test_mission_integration.py` 守护。任何下游阶段都不能在上游阶段达到
所需状态之前进入；自动化流程的任何阶段都不会把工人标记为「已出发」。

## 端到端阶段（pipeline.STAGES）

```
Batch 3  calling_discernment        ── 呼召辨识旅程（Skill 28）
             │  ready_for_readiness_assessment
             ▼
Batch 3  readiness_assessment       ── 15 维准备度（Skill 34）
             │  deployment_candidate（需人工 Panel）
             ▼
Batch 4  training_and_practicum     ── 装备/语言/实习/阶段认证（Skill 37–49，不签发差派批准）
             │
             ▼
Batch 5  sending_application        ── 候选人申请（Skill 52，完整性检查）
             │  committee_ready
             ▼
Batch 5  sending_committee_decision ── 差派委员会（Skill 53，quorum+CoI）
             │  approved_for_next_stage（仅解锁 Batch 6）
             ▼
Batch 6  deployment_preparation     ── 财务/身份/证件/合规/医疗/家庭/安全（Skill 61–70）
             │  complete
             ▼
Batch 6  deployment_readiness_gate  ── Deployment Readiness Gate（Skill 71，聚合全部条件）
             │  ready_for_deployment_planning（终态，需人工 Panel）
             ▼
         deployment_planning        ── 运营侧部署规划（系统终态；无 Batch 7；不代表已出发）
```

## 关键跨批依赖与守护

| 上游产出 | 下游消费 | 守护 |
|---|---|---|
| Calling `ready_for_readiness_assessment`（B3） | Readiness Assessment（B3） | `pipeline.assert_can_enter` |
| Readiness `deployment_candidate`（B3，人工 Panel） | Sending Application（B5） | `pipeline` + `readiness.can_decide_deployment_candidate` |
| Application `committee_ready`（B5，完整性检查） | Committee Decision（B5） | `sending.assert_can_submit` |
| Sending Decision `approved_for_next_stage`（B5） | Deployment Preparation（B6） | `pipeline` + `sending.approval_unlocks_batch6_only` |
| Field Assessment 四信号（B2） | 呼召 Field Interest / 匹配（B3） | `field.assess_field`（Need/Evidence/Readiness/Risk 分离） |
| Batch 1 敏感字段分级 P0–P4 | 所有批次 DTO/AI 输入 | `classification` + `assert_dto_safe` / `ai_input_allowed` |
| Batch 0 Outbox / Audit / Feature Flags | 所有批次写操作 | `outbox.enqueue` / `audit` / `require_mission_os` |

## 复用（不重建）的既有模块

- 组织与关系：`mission_os/organizations.py` + `0169`（B5 复用）。
- 恩赐/呼召模式：`gift_calling_engine.py`（B3 Skill 31 通过 Adapter 复用）。
- 导师/Cohort/督导：`mission_bridge_training`（B4 Skill 48 复用）。
- 多租户/RBAC/同意/监护人：`mission_bridge_tenancy` / `consent_lifecycle`（B1 复用）。
- 会计系统：Mission OS 财务通过 Adapter 连接，不做影子会计（B6 原则）。

## 横切不变式（贯穿全部批次）

- 租户隔离：所有业务表 `tenant_id` + RLS（`app.tenant_id`）。
- AI 边界：AI 不宣告呼召、不批准准备度/差派/Gate、不作法律/医疗最终结论、不决定撤离、P4 不入模型（`ai_boundaries` / `identity` / `health_family` / `deployment`）。
- 人工治理：关键决定需人工 Panel、禁自审、利益冲突排除、原决定者不独审申诉。
- 硬阻塞不可被高 Need/高分/信心抵消（`field` / `readiness` / `deployment`）。
- 敏感数据最小化：医疗只存状态摘要、证件号掩码、代祷更新去 P3/P4、敏感导出 step-up。
