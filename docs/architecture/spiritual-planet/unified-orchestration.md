# Unified orchestration

The bounded workflow is:

```text
trigger -> resolve explicit intent -> global safety gate -> capacity
-> minimum Context Broker request -> registered candidate producers
-> deterministic arbitration -> one unified result -> wait for user decision
-> confirmed command -> source-module result reference
```

Triggers include user request, state/pattern/warning/life-season/crisis changes,
weekly review, confirmed collaborator feedback, deletion and consent changes.

The request carries a correlation ID and configurable maximum nodes/model calls.
Defaults are eight nodes and one model call. Current Batch 9 orchestration is
deterministic and uses zero model calls. It has no recursive agent invocation.
Replay uses the stored trigger reference, contract version, candidate records
and arbitration result—not stored user intent text.

When safety is `ELEVATED` or `IMMINENT`, ordinary work stops and the result is
`STOPPED_FOR_SAFETY`. Limit exhaustion yields an explicit degraded state.
