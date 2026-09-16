---
id: pride-signal-detector
name: 自高信号识别
version: 0.1.0
batch: 1
type: llm+taxonomy
---

# Purpose

识别文本和行为材料中可能存在的认知自高、道德自义、能力称义、控制主权、群体优越和属灵骄傲。

# Trigger

世界观映射完成后调用。

# Inputs

`claims[]`, `worldview_map`, `user_reaction?`。

# Outputs

`pride_hypotheses[]`，包含观察、假设、证据等级、替代解释、风险和追问。

# Processing Contract


只识别“信号”，不宣判内心。
每条必须采用：
- observation
- possible_pattern
- evidence_level(E0-E4)
- alternative_explanations
- disconfirming_evidence_needed
- pastoral_question


# Prompt Contract

使用“可能、似乎、值得察验”等措辞。不得说“这个人就是骄傲”“神显明他有某罪”。先从用户自身可察验之处开始，避免把系统变成攻击他人的工具。

# Guardrails

E0-E2 不得输出为结论；公众人物只评公开材料；避免宗教羞辱和强迫认罪。

# Failure Handling

若用户只想定罪他人，系统应转向“这件事激发了你什么反应”的自省问题。

# Acceptance Tests

每条假设有替代解释；能区分自信与自高、责任感与控制欲、受伤表达与受害者无罪化。
