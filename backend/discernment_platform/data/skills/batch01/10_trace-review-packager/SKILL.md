---
id: trace-review-packager
name: 追踪与人工复核打包
version: 0.1.0
batch: 1
type: deterministic
---

# Purpose

保存每一步输入、输出、模型版本、规则版本、证据片段、重试和安全决定，供审计与牧者复核。

# Trigger

每个 Skill 完成时记录，最终统一打包。

# Inputs

workflow state, model metadata, prompt version, policy version。

# Outputs

`trace_bundle`, `review_packet`, `redacted_user_view`。

# Processing Contract


记录：
- trace_id
- case_id
- skill_id/version
- model/provider
- prompt_hash
- input_hash
- structured_output
- evidence_links
- safety_decisions
- latency/token/cost
- human_overrides


# Prompt Contract

无。

# Guardrails

对用户界面隐藏内部敏感推断；支持删除、导出、最小保留和租户隔离。

# Failure Handling

缺失 trace 时报告不得标记为 production-ready。

# Acceptance Tests

每个输出可追溯到证据和 Skill 版本；人工修改必须保留原值与修改理由。
