# Release Gates

## Required Gates

- Component versions are immutable and approved.
- Prompt/rule changes have owner review.
- Theological safety suite passes.
- Crisis and psychological safety suite passes.
- Privacy and consent suite passes.
- Data quality scan passes.
- Deterministic replay passes.
- Shadow mode has zero side effects.
- Canary cohort is valid and non-sensitive.
- Rollback plan is documented and tested.
- Kill switches are configured.
- SLO and error budget are defined.
- Incident owner is assigned.
- DR evidence exists.
- Batch 08 relational collaboration is implemented or explicitly disabled.

## Decision Model

Any missing required gate blocks production release. Exceptions require documented risk acceptance and must not bypass safety, privacy, deletion, or crisis controls.
