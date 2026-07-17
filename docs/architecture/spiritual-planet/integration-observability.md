# Integration observability

Traces use correlation ID, causation ID, trace ID, module, workflow, result and
redacted reason code. Platform persistence contains no user intent text.

Recommended metrics:

- event publish/consume and schema-validation failures;
- context request/deny/staleness totals;
- orchestration and suppression totals;
- command execution/failure totals;
- deletion and consent-revocation latency;
- cross-module conflict and crisis override totals.

Forbidden metric/log labels include user ID, emotion, temptation/crisis type,
journal title, church name, sensitive pattern and search query. Health is
technical-only and admin-gated; it reports registered/disabled/degraded/healthy,
contract version, reason codes and circuit state, never user content.

Circuit breakers open after repeated technical failure, then become half-open
after a recovery window. One degraded module must not prevent safety routing,
privacy controls or unrelated module navigation.
