---
id: worldview-salvation-linker
name: 思潮与替代救恩链接
version: 0.3.0
batch: 3
type: batch02-integration
requires: Batch 02 registry
---

# Purpose

将内容叙事匹配到一个或多个现代思潮 Domain Packs，并解释各自覆盖的主张。

# Trigger

叙事分析完成后。

# Inputs

叙事矩阵、主张、Batch 02 Registry。

# Outputs

Top-K Domain Pack 命中、版本、证据、排除规则、复合世界观。

# Processing Contract


1. 召回候选 Pack；
2. 检查 include/exclude/counter-evidence；
3. 每个 Pack 指明解释了哪一部分；
4. 合并共同的功能性救主、终局和自高假设；
5. 低置信度只生成澄清问题。


# Prompt Contract

不得用单一标签覆盖人物全部内容。必须承认可能存在的真实洞见。

# Evidence and Uncertainty

保留 Pack ID、版本、匹配分数和证据片段。

# Guardrails

思潮标签不是人格标签，也不是得救状态判断。

# Failure Handling

无 Pack 超过阈值时返回 unclassified，而非强制分类。

# Acceptance Tests

成功主义+消费主义可复合命中；反证规则可降低匹配；版本可追踪。
