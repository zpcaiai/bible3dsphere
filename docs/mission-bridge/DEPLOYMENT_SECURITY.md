# MissionBridge deployment security

## Topology

- Deploy web, API, worker, and PostgreSQL as separate services.
- PostgreSQL has no public port. API and worker reach it through a private network only.
- Terminate TLS at the managed load balancer. Redirect HTTP to HTTPS and enable HSTS.
- Store database, JWT, model, mail, storage, and observability credentials in the platform secret manager. Never bake secrets into images.
- Put API routes behind a managed WAF. Keep application rate limiting enabled as a second layer.

## Operations

- Take encrypted daily backups and keep at least one copy in a separate failure domain.
- Run `scripts/mission_bridge_backup.sh` and `scripts/mission_bridge_restore_drill.sh` on the release schedule; record restore integrity in `mission_bridge_backup_drills`.
- Require recent MFA for incidents, exports, break-glass and restricted records.
- Emit structured JSON logs with request/trace IDs. Never log raw prompts, medical details, child records, criminal records, tokens, cookies, or authorization headers.
- Export OpenTelemetry traces through `OTEL_EXPORTER_OTLP_ENDPOINT`; configure error tracking with PII scrubbing.
- Alert on readiness failures, queue lag, L2/L3 escalation delay, authorization failures, model cost spikes, backup failure, and sync conflicts.

## Release security tests

1. RLS bypass and cross-tenant access
2. IDOR on every resource identifier
3. Minor-record authorization
4. Prompt injection and tool boundary enforcement
5. RAG unpublished/cross-tenant leakage
6. Malicious uploads and content-type validation
7. Export permission and MFA
8. Sensitive-data log scanning
9. Session fixation and token rotation
10. CSRF and XSS
