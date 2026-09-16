---
id: viral-case-normalizer
name: 爆火案例规范化
version: 0.3.0
batch: 3
type: deterministic+llm
requires: Batch 01 case intake
---

# Purpose

把人物、热点、内容系列或营销事件整理为带时间窗口、平台范围、分析目标和授权边界的统一 ViralityCase。

# Trigger

任何新的网红、热点或平台爆火分析请求进入系统时。

# Inputs

原始描述、平台链接或材料、时间范围、分析目标、用户授权、已知人物标识。

# Outputs

规范化 case、主体消歧、平台清单、时间窗口、材料缺口、敏感等级。

# Processing Contract


1. 区分人物、事件、内容系列、产品和营销活动；
2. 解析同名人物和账号；
3. 明确“爆火前—爆火期—稳定期/衰退期”时间切片；
4. 区分用户提供事实、用户评价和待验证问题；
5. 检测未成年人、法律争议和声誉敏感内容；
6. 不自动扩展到私人生活。


# Prompt Contract

你是案例规范化器，不分析内心和属灵状态。使用中性措辞，所有身份消歧必须保留来源。

# Evidence and Uncertainty

主体身份不确定时不得合并账号；时间不明时输出未知项。

# Guardrails

不接受以骚扰、开盒或挖掘私人信息为目标的请求。

# Failure Handling

主体无法消歧则进入 USER_INPUT_REQUIRED 或 HUMAN_REVIEW。

# Acceptance Tests

正确区分人物与事件；保留时间窗口；不添加私人信息；输出通过 ViralityCase Schema。
