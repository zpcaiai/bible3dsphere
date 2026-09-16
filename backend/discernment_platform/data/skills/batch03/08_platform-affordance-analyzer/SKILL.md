---
id: platform-affordance-analyzer
name: 平台机制与算法可供性分析
version: 0.3.0
batch: 3
type: platform-observation
requires: content metrics
---

# Purpose

分析平台公开功能、互动结构和可观察分发迹象如何放大内容。

# Trigger

案例涉及一个或多个平台。

# Inputs

平台、内容格式、指标快照、推荐来源、互动模式。

# Outputs

可供性清单、可能放大机制、可观察指标、不可见机制限制。

# Processing Contract


分析：
- short-form completion pressure
- live interaction
- recommendation feed
- trending list
- repost/duet/remix
- hashtag clustering
- comment ranking
- notification cadence
- creator monetization tools
- moderation and friction

不得声称掌握平台内部模型权重。


# Prompt Contract

使用“平台功能可能奖励”“观察到分发与某特征共变”，禁止写成内部算法已证实因果。

# Evidence and Uncertainty

内部算法因果默认上限 P1；平台官方文档可支持功能存在但不自动支持个案因果。

# Guardrails

不提供规避平台安全、刷量或操纵推荐的方案。

# Failure Handling

指标不可比时标记 PLATFORM_METRIC_INCOMPARABLE。

# Acceptance Tests

区分功能存在与个案因果；不同平台指标不直接相加。
