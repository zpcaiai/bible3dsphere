---
id: integrated-virality-report-composer
name: 爆火洞鉴别综合报告
version: 0.3.0
batch: 3
type: composer
requires: all upstream skills
---

# Purpose

合成一份证据化、非诽谤、具有属灵深度和行动建议的综合报告。

# Trigger

核心分析链完成后。

# Inputs

全部中间状态、证据、Domain Pack 版本和安全结果。

# Outputs

ViralityDiscernmentReport、用户版、牧者复核版和技术审计版。

# Processing Contract


报告顺序：
1. 一页结论；
2. 证据覆盖与限制；
3. 人物与人设；
4. 内容叙事；
5. 商业模式；
6. 平台可供性；
7. 受众需要；
8. 爆火因素分解；
9. 传播网络；
10. 争议循环；
11. 操纵与信任风险；
12. 拟社会共同体；
13. 替代解释；
14. 长期塑造果子；
15. 苏格拉底首问；
16. 福音桥接；
17. 关注/节制/抵抗/创造建议。


# Prompt Contract

结论确定度不得超过证据。必须同时呈现真实贡献、风险、替代解释和未知项。

# Evidence and Uncertainty

所有 load-bearing claim 可追踪到 EvidenceRef 和 Skill 版本。

# Guardrails

声誉敏感报告必须人工复核；用户版隐藏不必要的内部推断。

# Failure Handling

任一质量门失败则 review_status 不得为 ready。

# Acceptance Tests

报告 Schema 通过；包含 limitations；算法因果有资格限定；公众人物高风险内容进入复核。
