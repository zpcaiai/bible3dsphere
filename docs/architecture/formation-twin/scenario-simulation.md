# Formation Scenario Simulation

Batch 10 adds a finite, deterministic scenario tool. It is a reflection aid, not a forecasting engine. The implementation lives in `backend/production_governance/scenarios.py`; the authenticated API is under `/api/v1/formation-twin/scenarios`.

## Contract

- The baseline snapshot, every assumption, and supporting evidence must be user-confirmed.
- A simulation has one explicit horizon: 24 hours, 7 days, 30 days, or a user-defined bounded date.
- Generation returns at most three branches: continue, protective adjustment, and changed external condition.
- Every branch includes possible effects, trade-offs, evidence against it, missing information, and observable signals.
- The rule version is fixed as `formation-scenario-rules-1.0.0`; generation makes no model call and performs no user action.
- Crisis states and unconfirmed baselines are rejected before generation.

Converting a branch into an intervention creates a Batch 6 proposal only. The user must confirm again and the existing intervention safety gate must pass.

## Failure behavior

Missing or deleted source snapshots, hidden-intent language, numeric destiny/relapse/salvation probabilities, or raw sensitive fields fail closed. The UI keeps assumptions editable and exposes deletion and “不准确” controls.
