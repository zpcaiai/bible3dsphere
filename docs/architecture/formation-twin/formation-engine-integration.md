# Formation Engine Integration

## Integration principle

Batch 4 does not replace the existing Formation Engine, Prayer OS, Holy Habit Engine, or Attention OS. It produces a narrow context envelope that those modules may request after the user grants consent for that specific destination.

## Destination allowlists

`formation` may receive user-reported items, observed relations, confirmed patterns, grace/recovery, reflective questions, and limitations.

`prayer` may receive only user-confirmed prayer/practice/grace context, grace/recovery, reflective questions, and limitations.

`habit` may receive only user-confirmed behavior/practice/recovery context, protective factors, questions, and limitations.

`attention` may receive only user-confirmed event/season-scoped context, protective factors, questions, and limitations.

All receive snapshot/window identifiers. None receive full text, crisis records, model prompts, provider responses, diagnosis, scores, or unconfirmed deep hypotheses.

## Consent and behavior

Each destination has an independent setting, default false. A request without consent returns `CONSENT_REQUIRED`. An absent current snapshot returns `INSUFFICIENT_DATA`. Exporting context does not automatically create a prayer, prescribe a habit, block attention, notify a pastor, or trigger another intervention.

## Legacy Formation Engine

The legacy engine's dimension scores and inferred tendency profile are deliberately not imported into the Formation Twin snapshot. The integration surface is the source-separated envelope, so downstream code can distinguish a user report from a confirmed pattern and show limitations.

## Invalidation

Deleting or excluding a canonical life event supersedes formation snapshots and excludes or deletes linked nodes/chains. Revoking a confirmation also invalidates snapshots. Consumers therefore request the current envelope rather than caching an older interpretation indefinitely.
