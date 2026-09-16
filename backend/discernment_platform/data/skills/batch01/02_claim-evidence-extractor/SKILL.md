---
id: claim-evidence-extractor
name: 主张与证据抽取
version: 0.1.0
batch: 1
type: llm-structured
---

# Purpose

从材料中抽取事实主张、价值判断、因果主张、身份主张、救恩承诺和行动号召。

# Trigger

输入规范化完成后调用。

# Inputs

`normalized_case.raw_input`, `source_metadata`。

# Outputs

`claims[]`，每项包含类型、原文证据、可核验性、置信度、反证需求。

# Processing Contract


将内容划分为：
- factual_claim
- causal_claim
- moral_claim
- identity_claim
- anthropological_claim
- salvation_claim
- enemy_claim
- action_call
- emotional_signal

每项必须绑定原文片段或明确标记“隐含主张”。


# Prompt Contract

只抽取文本能支持的主张。禁止把可能含义写成作者确定意图。对讽刺、夸张和修辞降低置信度。

# Guardrails

不联网时不得把外部事实标为已核实；人物争议内容必须避免诽谤式措辞。

# Failure Handling

无法定位证据片段时，相关 claim 不得进入高置信输出。

# Acceptance Tests

每个高置信 claim 有证据 span；区分事实与价值；能识别“只要有钱就自由”属于救恩承诺。
