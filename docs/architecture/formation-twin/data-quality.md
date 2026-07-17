# Data quality and governance checks

`GET /api/v1/formation-twin/data-quality` provides an owner-scoped report with:

- total canonical events;
- invalid or missing time fields;
- missing consent/provenance metadata;
- sensitive-key leak candidates in canonical JSON;
- rejected/quarantined and excluded counts;
- orphaned encrypted-content records;
- fail-closed `quality_passed` and `valid_event_ratio`.

Contract tests additionally cover timezone validation, recursive sensitive-body rejection, deterministic idempotency, authenticated encryption, inference-free provenance, and source field minimization. Operational monitoring must alert on any sensitive leak candidate, missing governance metadata, or sustained ingestion failures.
