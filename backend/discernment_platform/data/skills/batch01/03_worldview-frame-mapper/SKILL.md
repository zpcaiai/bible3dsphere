---
id: worldview-frame-mapper
name: 世界观框架映射
version: 0.1.0
batch: 1
type: llm+rules
---

# Purpose

把主张映射到创造—堕落—替代救赎—终局四层，并分析真理观、人论、善恶观、自由观、权力观和目的论。

# Trigger

主张抽取完成后调用。

# Inputs

`claims[]`, `normalized_case`。

# Outputs

`worldview_map`、支持证据、冲突点、未决问题。

# Processing Contract


回答：
1. 什么被视为终极真实？
2. 人是什么？
3. 人的根本问题是什么？
4. 谁或什么能拯救？
5. 什么算好人生？
6. 谁拥有最高权威？
7. 该叙事导向何种人和共同体？

同时标记其中的普遍恩典与真实洞见。


# Prompt Contract

必须先公平复述其最强版本，再进行基督教评估。禁止稻草人化。输出至少一个可能正确之处和一个潜在扭曲。

# Guardrails

不得把所有非基督教观点简单标记为“魔鬼”；应区分真理碎片、共同恩典、偶像化和明确恶行。

# Failure Handling

材料不足时返回问题而非完整定性。

# Acceptance Tests

同一现象必须同时能输出 creation_good 与 fall_distortion；不得只有负面标签。
