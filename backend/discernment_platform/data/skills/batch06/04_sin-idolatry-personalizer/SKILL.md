---
id: sin-idolatry-personalizer
name: 罪与偶像个性化解释
version: 0.6.0
batch: 6
type: gospel-path-runtime-skill
---

# Purpose

将功能性救主、自我称义和关系果子连接到罪与错误敬拜。

# Inputs

- GospelPathContext
- active doctrine packs
- dialogue consent state
- Batch 01–05 findings
- safety and church context

# Outputs

Structured output containing:
- selected doctrine segments
- personalized explanation
- misconception guards
- law/gospel balance
- denominational notes
- response or safety action
- trace metadata

# Processing Contract

1. Begin with created good where applicable.
2. Name sin without erasing suffering or structural factors.
3. Use law to reveal truth, not to offer self-salvation.
4. Present Christ's objective person and work.
5. Keep justification distinct from sanctification.
6. Connect all benefits to union with Christ.
7. Make sanctification Spirit-dependent and community-embedded.
8. End with resurrection and new-creation hope where relevant.
9. Respect consent, refusal and doctrinal depth.
10. Mark denomination-specific claims by tier.

# Prompt Contract

Use invitational, clear and Christ-centered language.
Do not reduce gospel to advice, therapy, politics or success.
Do not claim hidden revelation or final salvation status.

# Guardrails

- No coercive evangelism.
- No moralism.
- No cheap grace.
- No prosperity-gospel promises.
- No trauma invalidation.
- No forced reconciliation with abusers.
- No scrupulosity amplification.
- No denomination-specific overreach.

# Failure Handling

Return:
- CONSENT_REQUIRED
- SAFETY_HOLD
- DOCTRINAL_REVIEW_REQUIRED
- DENOMINATIONAL_SCOPE_REQUIRED
- INSUFFICIENT_CONTEXT
- HUMAN_REVIEW_REQUIRED

# Acceptance Tests

- Christ, cross and resurrection are present where full gospel is requested.
- Justification basis is Christ, not behavior.
- Sanctification is fruit, not merit.
- User refusal is respected.
- Tier 2/3 claims are labeled.
