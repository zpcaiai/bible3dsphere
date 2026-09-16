---
id: socratic-question-planner
name: 苏格拉底式属灵追问规划
version: 0.1.0
batch: 1
type: planner
---

# Purpose

生成不操纵、分阶段、可适应的追问，引导用户从观点澄清进入自我察验、律法镜照与福音盼望。

# Trigger

欲望与偶像映射完成后调用。

# Inputs

`claims`, `worldview_map`, `pride_hypotheses`, `desire_map`, `faith_context`。

# Outputs

按阶段排序的问题列表，每题含目的、难度、预计风险、分支条件。

# Processing Contract


问题阶段：
1. Clarify：你所说的具体含义是什么？
2. Assumption：这个判断依赖什么前提？
3. Evidence：什么证据会改变你的看法？
4. Counterexample：是否存在反例？
5. Consequence：长期相信它会结出什么果子？
6. Heart：你最想得到或最怕失去什么？
7. Worship：什么东西正在承担只有神能承担的重量？
8. Law：这个标准若同样用在你身上会怎样？
9. Gospel：若价值不是靠赢得，而是在基督里领受，会改变什么？
10. Response：今天可以采取什么真实而非表演性的回应？


# Prompt Contract

每轮最多提出一个核心问题。问题应开放、尊重、可回答，不以暗示性措辞强迫用户接受预设结论。

# Guardrails

对非基督徒先征得进入福音层的同意；对焦虑、强迫性认罪或宗教创伤用户降低律法压力并优先安全。

# Failure Handling

用户防御升高时回到澄清和共情，不继续层层逼问。

# Acceptance Tests

不得连续堆叠十个问题；每个问题有明确阶段和分支；问题不能预设对方有罪。
