---
id: case-intake-normalizer
name: 案例输入规范化
version: 0.1.0
batch: 1
type: deterministic+llm
---

# Purpose

把用户输入、文章、视频转录、人物材料或自我反思整理为统一案例对象，不做深层属灵判断。

# Trigger

任何新的洞鉴别案例进入系统时调用。

# Inputs

`raw_input`, `subject_type?`, `source_metadata?`, `user_goal`, `faith_context?`, `consent_scope`。

# Outputs

规范化主题、时间范围、主体、来源、用户希望解决的问题、已知事实、未知项、敏感级别。

# Processing Contract


1. 清理格式与重复内容；
2. 区分“被分析对象”与“用户自身反应”；
3. 标记文本来源：原话、转述、评论、推断；
4. 检测是否缺少关键上下文；
5. 不补造人物动机；
6. 生成 `normalized_case`。


# Prompt Contract


系统角色：信息整理员，不是属灵裁判。
必须使用中性语言。
不得把情绪表达改写为事实。
不得声称知道当事人内心。
输出必须符合 `DiscernmentCaseNormalized` 结构。


# Guardrails

未获得属灵分析同意时，只能做内容与观点分析。涉及他人隐私时最小化保存。

# Failure Handling

输入过短则返回 `INSUFFICIENT_EVIDENCE`；输入冲突时保留冲突，不自行裁决。

# Acceptance Tests

能正确区分原文、用户评价和系统推断；不得生成新的事实；JSON 100% 通过 Schema。
