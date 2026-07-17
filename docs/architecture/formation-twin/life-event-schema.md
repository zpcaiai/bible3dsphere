# Formation Twin life-event schema

`CanonicalLifeEvent` is the only normalized event contract. It records who, what, when, source, explicit self-report or observable fact, consent, safety status, provenance, and lifecycle status.

Hard boundaries:

- `occurred_at`, `recorded_at`, and `created_at` are timezone-aware; `timezone` is an IANA identifier.
- Statement types are limited to `USER_REPORTED_FACT`, `OBSERVED_EVENT`, and `USER_CONFIRMED_PATTERN`.
- System inference is not part of Batch 02.
- Full journal, prayer, transcript, confession, crisis, medical, and legal text is rejected recursively by the contract.
- Sensitive body is represented only by an opaque encrypted-content reference.
- Events carry a stable idempotency key, version, normalization version, status, consent, and provenance.

The executable contract lives in `backend/formation_twin/contracts.py` and normalization in `backend/formation_twin/normalizer.py`.
