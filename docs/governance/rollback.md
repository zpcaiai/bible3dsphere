# Rollback Policy

## Rollback Triggers

- P0/P1 incident.
- Failed safety or privacy evaluation.
- Unexpected model behavior in shadow/canary.
- SLO breach with user-facing degradation.
- Evidence of consent, deletion, or data lineage failure.

## Rollback Requirements

- Restore previous immutable component versions.
- Pause canary and shadow experiments before user-visible rollback.
- Verify kill switches and degraded responses.
- Confirm no deleted data is restored.
- Record post-rollback evaluation and owner sign-off.

## Current Boundary

The repository includes rollback records and migration rollback SQL for Batch 10. A production rollback remains unproven until exercised against a real environment.
