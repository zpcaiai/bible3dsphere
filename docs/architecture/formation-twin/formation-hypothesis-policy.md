# Formation Hypothesis Policy

## Default state

Model formation inference is disabled by default. It requires all of:

1. `belief_hypothesis_enabled = true`;
2. `provider_policy = CONFIGURED_PROVIDER`;
3. `FORMATION_TWIN_BELIEF_HYPOTHESIS_ENABLED=true`;
4. an actually configured provider;
5. an event authorized for future analysis;
6. a second crisis screen returning low risk.

## Candidate requirements

Every model candidate must have a concrete node type, evidence span, confidence, scope, pending review state, and expiration. A deep hypothesis must additionally include at least one alternative explanation. Insufficient evidence yields no candidate.

Candidate content must pass the formation-specific and shared theological validator. A high confidence does not reduce any requirement and never permits automatic confirmation.

## Review

The user can confirm, partially confirm after editing, relabel, change scope, reject, dismiss, delete, or later revoke. Confirming creates a separate `USER_CONFIRMED` node. Original provenance is immutable and auditable without placing sensitive full text in the audit event.

Pending candidates are excluded from Prayer, Habit, and Attention context envelopes. Formation UI may display them only in a clearly marked candidate/review area.

## Retention

Deep hypotheses expire after 30 days unless reviewed. Rebuild can supersede unreviewed candidates. Export includes candidate provenance and evidence offsets; erase deletes model runs, evidence, reviews, nodes, snapshots, and graph projection receipts.

## Provider data boundary

Only the selected authorized record is sent to the configured provider. Provider metadata is retained, but the input text, prompt body, response body, confession, temptation detail, prayer text, transcript, and crisis text are not written to logs, domain events, model-run records, monitoring tags, or Neo4j.
