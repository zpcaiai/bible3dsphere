# Threat Model

## Assets

- Raw journals, voice-derived text, emotional snapshots, spiritual formation hypotheses, scenario simulations, safety decisions, and governance audit logs.

## Primary Threats

- Unauthorized access to sensitive inner-life data.
- Reuse of deleted data through backup restore or derived projections.
- Prompt or rule changes bypassing theological, crisis, or privacy review.
- Relational sharing before consent and Batch 08 controls exist.
- Model output framed as prophecy, diagnosis, coercion, or moral judgment.
- Supply chain compromise through unpinned dependencies or unreviewed CI actions.

## Mitigations

- RLS and ownership checks.
- Encrypted artifact storage.
- Purpose-bound event payloads.
- Immutable component registry.
- Release gates and kill switches.
- Fail-closed relational collaboration.
- Deletion tombstones and DR checks.

## Remaining Work

Production readiness requires penetration testing, dependency provenance review, secret scanning, CI hardening, and live incident exercises.
