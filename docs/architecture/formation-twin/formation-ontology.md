# Formation Ontology

The closed ontology is implemented in `backend/formation_twin/formation_ontology.py` with Chinese labels in `formation_ontology.zh-CN.json`.

## Node types

- Event and meaning: `LIFE_EVENT`, `INTERPRETATION`.
- Identity and belief: `IDENTITY_STATEMENT`, `BELIEF_STATEMENT`.
- Desire and fear: `DESIRE`, `FEAR`.
- Felt and decision context: `EMOTION`, `TEMPTATION`, `CHOICE`.
- Action and result: `BEHAVIOR`, `SPIRITUAL_PRACTICE`, `OUTCOME`.
- Grace and resilience: `GRACE_EVIDENCE`, `PROTECTIVE_FACTOR`, `RECOVERY_RESPONSE`.
- User-reviewable direction: `FORMATION_DIRECTION`.

`FORMATION_DIRECTION` is a scoped description, not a verdict about sanctification, salvation, repentance, holiness, or God's hidden purpose.

## Evidence kinds

The system distinguishes:

- `USER_REPORTED_FACT`;
- `OBSERVED_EVENT`;
- `RULE_DERIVED_RELATION`;
- `MODEL_EXTRACTED_EXPLICIT_EXPRESSION`;
- `MODEL_FORMATION_HYPOTHESIS`;
- `USER_CONFIRMED_FORMATION_PATTERN`.

The principal five user-facing evidence classes from the product contract remain distinct; explicit model extraction is an additional, still-model-sourced class and never becomes a user fact automatically.

## Scopes

- `THIS_EVENT_ONLY` is the safe default.
- `THIS_SEASON` is time-bounded by user meaning.
- `RECURRING_CONTEXT` is used only after user review.
- `USER_DEFINED` preserves a user-stated boundary.

## Explicit exclusions

There are no node types or fields for salvation state, repentance validity, divine satisfaction, personality diagnosis, maturity, holiness, sin, idol, or spiritual rank. These concepts are not inferred indirectly through a numeric field either.
