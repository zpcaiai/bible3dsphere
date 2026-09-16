---
id: gospel-identity-reanchoring
name: 福音身份重新安置
version: 0.4.0
batch: 4
type: runtime-skill
---

# Purpose

把称义、荣耀、能力、权柄、群体和救主位置重新安置于基督。

# Inputs

- case scope
- observations
- applicable hypothesis packs
- consent and safety state
- prior longitudinal evidence where available

# Outputs

Structured output with:
- observations or hypotheses
- evidence level
- alternative explanations
- counter-evidence
- limitations
- next action

# Processing Contract

1. Separate observation from interpretation.
2. Preserve created good before naming distortion.
3. Never exceed H-level evidence.
4. Generate at least two plausible alternatives for H0–H2.
5. State what would falsify the result.
6. Prefer self-examination over accusation.
7. Escalate scrupulosity, trauma, crisis and reputation risk.

# Prompt Contract

Use non-condemning language such as “可能”“值得察验”“当前材料呈现”.
Never say the system knows the heart or God's hidden verdict.

# Guardrails

- Not a clinical diagnosis.
- Not a salvation judgment.
- Not a spiritual abuse tool.
- Do not treat disagreement as evidence of pride.
- Do not erase structural injustice or real harm.
- Do not amplify compulsive confession.

# Failure Handling

Return `INSUFFICIENT_EVIDENCE`, `PASTORAL_SAFETY_HOLD`,
or `HUMAN_REVIEW_REQUIRED` instead of forcing a conclusion.

# Acceptance Tests

- Observation and interpretation are distinct.
- Alternative explanations are present.
- Counter-evidence is explicit.
- H0–H2 are not written as stable character conclusions.
- Gospel output is not mere behaviorism.
