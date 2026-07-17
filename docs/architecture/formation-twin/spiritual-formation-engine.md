# Spiritual Formation Engine

## Purpose

The Batch 4 engine organizes already-authorized Formation Twin records into a reviewable description of a concrete situation. It is a reflective record system, not a spiritual authority, diagnosis service, moral judge, prophecy mechanism, or maturity measurement.

The implemented processing order is:

```text
consent and event eligibility
→ crisis-first exclusion
→ explicit/observed node materialization
→ optional model candidates
→ theological and evidence validation
→ minimal event-scoped chain assembly
→ source-separated snapshots
→ optional, consented context envelopes
```

## Inputs

Only canonical life events with all of the following are eligible:

- `status = ACCEPTED`;
- `processing_preference = ALLOW_FUTURE_ANALYSIS`;
- not deleted, superseded, or excluded;
- no concern, elevated, imminent, or routed-to-crisis safety state.

The deterministic engine reads canonical metadata, explicit emotion observations, allow-listed behavioral facts, and spiritual-practice facts. It does not decrypt a journal merely to build a deterministic chain. Sensitive text is decrypted only when the user has enabled the optional provider and the event explicitly permits future analysis; crisis screening runs again before a provider call.

## Outputs

The engine creates immutable formation nodes, evidence records, neutral edges, chains, and current/daily/weekly snapshots. A snapshot separates:

- user-reported items;
- observed or rule-derived relations;
- model hypotheses awaiting review;
- user-confirmed patterns;
- grace, protection, and recovery records;
- limitations and reflective questions.

No score or rank is computed. Existing legacy Formation Engine dimension scores are not imported into this subsystem.

## Feature flags

- Spiritual engine: on by default.
- Formation chain assembly: on by default.
- Belief/deep-formation hypotheses: off by default and double-gated by database setting plus environment flag.
- Neo4j projection: off by default and optional.
- Prayer, habit, attention, and Formation Engine context exports: separately consented and off by default.

## Failure behavior

PostgreSQL is the source of record. Model or Neo4j unavailability does not stop manual records, deterministic chains, review, or snapshots. Unsafe candidates are rejected before persistence. Context exports fail closed when consent or a current snapshot is absent.
