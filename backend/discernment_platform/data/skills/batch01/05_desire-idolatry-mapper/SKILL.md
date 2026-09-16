---
id: desire-idolatry-mapper
name: 欲望与偶像映射
version: 0.1.0
batch: 1
type: llm-structured
---

# Purpose

识别现象或用户反应背后的正当需要、过度欲望、恐惧、功能性救主和可能的偶像化。

# Trigger

自高假设生成后调用。

# Inputs

`worldview_map`, `pride_hypotheses`, `user_reaction?`。

# Outputs

`desire_map[]`：正当需要、扭曲形式、所许诺救恩、所要求牺牲、失去时的反应。

# Processing Contract


采用链条：
good_desire -> absolutized_desire -> functional_savior -> demanded_sacrifice -> enslaving_fruit

示例：
被认可 -> 必须人人肯定 -> 流量/地位作救主 -> 牺牲真实与安息 -> 焦虑和比较。


# Prompt Contract

偶像是“比喻性和牧养性假设”，不是对人灵魂状态的最终判决。必须指出正当需要如何在基督里被重新安置。

# Guardrails

不要把创伤、贫困或现实压迫仅归因于个人偶像；同时保留结构性因素。

# Failure Handling

无法确定时输出多个候选模型并请求更多自我报告。

# Acceptance Tests

能同时识别个人因素与结构因素；不得把所有愿望都污名化。
