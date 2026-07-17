# Data Retention

## Retention Classes

- Raw journals and voice-derived text: shortest configured retention and encrypted storage.
- Derived emotional and spiritual snapshots: retained only while user consent and product purpose remain valid.
- Governance logs: retained for audit periods with minimized payloads.
- Deleted-user tombstones: minimal identifiers only, used to prevent accidental rehydration.

## Deletion Rules

Deletion must cascade through raw artifacts, derived projections, scenario simulations, evaluation-linked user artifacts, and shareable relational artifacts once Batch 08 exists.

## Current Boundary

Batch 10 adds retention tables and policy documents. Production readiness still requires scheduled retention jobs, deletion workflow evidence, and restore tests proving deleted data is not resurrected.
