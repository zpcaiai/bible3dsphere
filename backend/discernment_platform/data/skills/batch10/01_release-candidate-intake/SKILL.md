---
id: release-candidate-intake
name: 发布候选接入
version: 1.0.0
batch: 10
type: production-gate-runtime-skill
---

# Purpose

收集构建Hash、Batch manifests、模型、Prompt、Policy、Pack、功能范围与法域。

# Inputs

- ReleaseCandidate
- Batch 01–09 manifests
- certification controls
- evidence items
- findings
- red-team results
- human reviews
- operational and privacy evidence

# Outputs

Structured output containing:
- control decisions
- critical blockers
- findings
- evidence references
- domain result
- release recommendation
- expiry and recertification triggers
- audit trace

# Processing Contract

1. Bind all evidence to the exact build and version set.
2. Refuse evaluation when evidence is missing or expired.
3. Treat C3/C4 as non-compensable blockers.
4. Preserve dissenting human reviews.
5. Require purpose-specific privacy and legal review.
6. Test rollback and kill switch before production approval.
7. Revoke or suspend when critical evidence becomes invalid.
8. Maintain immutable audit and evidence hashes.
9. Never let AI self-certify high-risk controls without human approval.
10. Separate Pilot, Conditional and Production scope.

# Guardrails

- No score-based override of critical failures.
- No fabricated evidence or signatures.
- No blanket privacy compliance claims.
- No AI-only theological certification.
- No deployment without rollback.
- No silent certificate expiry.
- No suppression of serious dissent or incidents.
- No disabling continuous recertification.

# Failure Handling

Return:
- EVIDENCE_MISSING
- EVIDENCE_EXPIRED
- CRITICAL_BLOCKER
- HUMAN_REVIEW_REQUIRED
- LEGAL_REVIEW_REQUIRED
- ROLLBACK_NOT_READY
- CERTIFICATE_SUSPENDED
- CERTIFICATE_REVOKED
- RELEASE_BLOCKED

# Acceptance Tests

- Exact build hash is checked.
- C4 failure blocks all release.
- C3 failure blocks pilot and production.
- Conditional approval contains scope and expiry.
- Certificate has signatories and recertification triggers.
