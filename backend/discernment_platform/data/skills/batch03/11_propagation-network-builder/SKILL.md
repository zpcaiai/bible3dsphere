---
id: propagation-network-builder
name: 传播网络构建
version: 0.3.0
batch: 3
type: graph-builder
requires: content and interaction data
---

# Purpose

构建人物、内容、媒体、品牌、社群、反对者和搬运者之间的传播图。

# Trigger

有转发、引用、评论、合拍、媒体报道或跨平台搬运数据时。

# Inputs

节点、互动事件、时间戳、平台、内容关系。

# Outputs

PropagationGraph、社区、桥接节点、种子节点候选、批评传播占比和盲区。

# Processing Contract


边类型：
- authored
- reposted
- quoted
- criticized
- endorsed
- remixed
- covered_by_media
- sponsored
- linked_to_product
- migrated_cross_platform

反对者传播必须与支持传播分开。


# Prompt Contract

无。

# Evidence and Uncertainty

缺失 API 数据时明确图是部分图，不以采样图代表全网。

# Guardrails

不构建用于骚扰普通用户的个人画像；默认聚合化。

# Failure Handling

节点标识冲突时不合并。

# Acceptance Tests

支持跨平台边；批评转发不计为支持；图输出可通过 Schema。
