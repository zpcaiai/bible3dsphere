# Canary Release Policy

## Scope

This policy governs Spiritual Planet and Formation Twin canary exposure after a release candidate has passed static, safety, privacy, data quality, and rollback gates.

## Rules

- Canary cohorts must be non-sensitive, explicitly enrolled, and reversible.
- Relational collaboration features remain unavailable until Batch 08 is implemented and approved.
- Shadow results may inform canary readiness, but shadow traffic must have zero side effects.
- Canary expansion is blocked by open P0/P1 incidents, disabled kill switches, failed evaluation suites, missing rollback instructions, or missing data protection review.
- A canary must be paused before rollback when user-facing output quality degrades beyond the documented SLO.

## Required Evidence

- Release candidate id and immutable component versions.
- Evaluation run ids for theological safety, crisis safety, privacy, and deterministic replay.
- Synthetic load evidence marked as non-production unless collected against the production-like stack.
- Rollback owner, rollback command, expected recovery time, and post-rollback verification.
