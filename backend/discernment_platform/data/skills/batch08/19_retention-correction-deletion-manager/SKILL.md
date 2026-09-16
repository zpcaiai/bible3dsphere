---
id: retention-correction-deletion-manager
name: 保留、纠正与删除管理
version: 0.8.0
batch: 8
type: pastoral-collaboration-runtime-skill
---

# Purpose

支持用户纠正、撤回、删除、保留例外和第三方信息隔离。

# Inputs

- pastoral case
- actors and role packs
- consent grants
- data classifications
- purpose and requested fields
- safety and conflict state
- prior audit events

# Outputs

Structured output containing:
- access or workflow decision
- selected and redacted fields
- user-visible rationale
- review level
- safety or referral action
- expiry and re-share policy
- audit event

# Processing Contract

1. Default deny.
2. Require a named purpose.
3. Apply role permission and attribute constraints.
4. Select minimum necessary fields.
5. Check user consent or documented safety/legal basis.
6. Detect conflicts of interest.
7. Preserve user correction and visibility rights.
8. Never turn AI hypotheses into governance facts.
9. Escalate L2/L3 to qualified human roles.
10. Record all sensitive access and overrides.

# Guardrails

- No unlimited pastoral access.
- No surveillance-style accountability.
- No hidden re-sharing.
- No AI-driven discipline verdict.
- No internal-only handling of reportable abuse.
- No forced reconciliation.
- No public-person private Formation Twin.
- No professional claims without qualified review.

# Failure Handling

Return:
- ACCESS_DENIED
- CONSENT_REQUIRED
- PURPOSE_TOO_BROAD
- MINIMIZATION_REQUIRED
- CONFLICT_OF_INTEREST_HOLD
- SAFEGUARDING_REVIEW
- PROFESSIONAL_REFERRAL
- LEGAL_DUTY_REVIEW
- HUMAN_REVIEW_REQUIRED

# Acceptance Tests

- Access requires role, purpose and consent/basis.
- L2/L3 never flows to ordinary group roles.
- Re-share rules are explicit.
- User corrections never overwrite audit history.
- AI outputs cannot directly decide discipline.
