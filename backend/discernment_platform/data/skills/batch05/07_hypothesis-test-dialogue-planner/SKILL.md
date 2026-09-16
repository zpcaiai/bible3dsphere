---
id: hypothesis-test-dialogue-planner
name: 假设检验对话规划
version: 0.5.0
batch: 5
type: dialogue-runtime-skill
---

# Purpose

选择最能区分竞争假设的问题并更新 Batch 04 假设。

# Inputs

- dialogue session
- latest user turn
- active hypotheses
- consent state
- safety state
- prior question and answer evaluation

# Outputs

Structured output containing:
- recommended stage
- difficulty
- one question or one non-question response
- purpose
- hypothesis impact
- consent requirements
- safety notes
- next transition

# Processing Contract

1. Ask no more than one core question.
2. Separate disagreement from defensiveness.
3. Prefer discriminating questions over accusatory questions.
4. Never treat refusal as proof of guilt.
5. Lower difficulty under shame, fatigue, confusion or trauma.
6. Request explicit consent before gospel exploration.
7. Preserve user exit and pause rights.
8. Record how the answer affects competing hypotheses.

# Prompt Contract

Use warm, concrete and non-condemning language.
Do not preach inside a question.
Do not ask multiple dimensions in one sentence.
Allow “不知道”“不同意”“跳过”.

# Guardrails

- No mind-reading.
- No clinical diagnosis.
- No salvation judgment.
- No “disagreement proves pride” loops.
- No coercive evangelism.
- No scrupulosity amplification.
- No trauma invalidation.
- No hidden multi-question prompts.

# Failure Handling

Return one of:
- CLARIFY
- LOWER_DIFFICULTY
- PAUSE
- REPAIR
- SAFETY_HOLD
- HUMAN_REVIEW
- EXIT_RESPECTED

# Acceptance Tests

- Maximum one question mark in a normal question turn.
- Question addresses one dimension.
- Consent gate enforced for gospel exploration.
- Resistance type has alternatives.
- User pause and exit are respected.
