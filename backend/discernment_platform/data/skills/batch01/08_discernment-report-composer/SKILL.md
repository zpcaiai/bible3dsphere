---
id: discernment-report-composer
name: 洞鉴别报告合成
version: 0.1.0
batch: 1
type: composer
---

# Purpose

把前序结果组合成清晰、温柔、可审计的用户报告。

# Trigger

所有分析节点完成后调用。

# Inputs

全部中间状态。

# Outputs

摘要、观察、世界观、可能自高、欲望链、苏格拉底首问、福音桥接、行动建议、局限性。

# Processing Contract


报告顺序：
1. 公平摘要；
2. 真实与可取之处；
3. 需要辨识的扭曲；
4. 证据支持的自高假设；
5. 对用户自身的镜照；
6. 一次只给一个首要追问；
7. 福音视角；
8. 一个可执行回应；
9. 局限性与证据等级。


# Prompt Contract

语气应有真理与恩典，避免控告式语言。不得输出比证据更确定的结论。

# Guardrails

高风险案例不直接生成深度报告，改为安全支持和人工复核。

# Failure Handling

任一关键中间结果 Schema 不合法则不合成，进入重试或人工复核。

# Acceptance Tests

报告必须包含 limitation；必须至少承认一个正面价值；必须清楚区分观察与解释。
