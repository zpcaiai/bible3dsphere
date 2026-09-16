---
id: controversy-cycle-engine
name: 争议循环状态机
version: 0.3.0
batch: 3
type: state-machine
requires: timeline and content events
---

# Purpose

识别争议从潜伏、触发、放大、极化、商业化、疲劳、重构到再燃的阶段。

# Trigger

存在争议事件或明显正反阵营传播时。

# Inputs

事件时间线、内容、互动指标、商业动作、平台治理动作。

# Outputs

ControversyEpisode、当前状态、转移证据、受益者、伤害和下一状态假设。

# Processing Contract


合法状态：
LATENT -> TRIGGERED -> AMPLIFYING -> POLARIZED -> MONETIZED
-> FATIGUED -> REFRAMED/RESOLVED/REIGNITED

允许跳转，但必须说明事件证据。
检测：
- outrage bait
- apology cycle
- reaction economy
- pile-on
- counter-mobilization
- monetized response
- moderation shock


# Prompt Contract

不得把所有争议都视为策划炒作。区分真实问责和流量利用。

# Evidence and Uncertainty

“故意制造争议”的动机推断最高 P1，除非有公开承认或策划证据。

# Guardrails

不得鼓励网暴、举报轰炸或人肉搜索。

# Failure Handling

缺少时间线则只识别争议元素，不判断状态。

# Acceptance Tests

状态转移符合配置；真实纠错不自动标记炒作；重燃可被识别。
