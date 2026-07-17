# Event versioning

Canonical event schema and source schema versions are `1.0`; the deterministic normalizer has an independent version. Idempotency is scoped by tenant, user, source type, and client/source event ID.

Editing a check-in or journal creates a new record and canonical event, increments revision, records the superseded relationship, and marks the old event `SUPERSEDED`. Exclusion and deletion are explicit lifecycle states. Downstream readers must filter deleted, superseded, excluded, and `STORE_ONLY` events before any future analysis.
