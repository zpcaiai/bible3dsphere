# Deletion and consent propagation

A deletion creates a manifest containing the current tenant/user, source
module/type/record references, scope and required acknowledgement modules.

```text
source deletion -> manifest -> invalidate platform references -> cancel
notifications/jobs -> delete search references -> invalidate ephemeral context
-> embedding/graph/cache/source acknowledgements -> derived-state rebuild
-> complete only when every required acknowledgement is complete
```

Statuses are requested, propagating, partially completed, completed,
failed-retryable and failed-manual-review. Retry re-runs only registered
adapters. The platform never reports completion while an acknowledgement is
`NOT_AVAILABLE` or failed.

Current local adapters invalidate unified search, notification candidates,
orchestration jobs, local actions and ephemeral contexts. Neo4j, embedding and
non-platform source deletion adapters are disabled by default and therefore
produce `NOT_AVAILABLE`; this yields honest partial completion until Batch 10
production adapters are connected.

Consent withdrawal is separate from deletion. It blocks new reads immediately,
cancels pending work and notifications, excludes related search references and
records a metadata-only propagation job.
