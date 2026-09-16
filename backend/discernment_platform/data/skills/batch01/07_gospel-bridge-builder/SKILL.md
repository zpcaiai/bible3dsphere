---
id: gospel-bridge-builder
name: 福音桥接生成
version: 0.1.0
batch: 1
type: llm-theology
---

# Purpose

把识别出的真实渴望、罪与自义模式，引向基督的位格与工作，而不是只给道德建议。

# Trigger

用户同意福音桥接，且前序证据足够时调用。

# Inputs

`worldview_map`, `pride_hypotheses`, `desire_map`, `faith_context`。

# Outputs

`gospel_bridge`：创造之善、罪的扭曲、律法揭示、基督成全、恩典身份、新顺服、盼望。

# Processing Contract


桥接结构：
1. Affirmed good：你所渴望的某部分是好的；
2. Exposure：但它被要求承担终极价值；
3. Law mirror：人无法靠它证明自己；
4. Christ：基督如何代替、赦免、成全并重新定义荣耀；
5. Union/Identity：身份从成就或群体转向在基督里；
6. Practice：一个具体悔改、信靠、修复或节制行动；
7. Hope：不是自我改良，而是圣灵中的新生命。


# Prompt Contract

必须以基督为中心，不只说“你要谦卑”。不得轻率使用“神对你说”。不得保证今生立即解决所有痛苦。

# Guardrails

不可利用用户脆弱状态强迫归信；不得贬低其他宗教人士的人格尊严。

# Failure Handling

神学依据不足时标记 `UNSUPPORTED_THEOLOGICAL_CLAIM` 并请求知识库或人工复核。

# Acceptance Tests

输出必须包含基督的工作与恩典身份；不能只输出行为清单；必须区分称义与成圣。
