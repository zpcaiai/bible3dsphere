# Incident Response

## Severity Levels

- P0: safety harm, privacy breach, unauthorized disclosure, or crisis-routing failure.
- P1: degraded safety evaluation, release gate bypass attempt, or user-rights failure.
- P2: partial governance telemetry loss, non-critical SLO breach, or canary anomaly.
- P3: documentation drift or non-user-impacting governance inconsistency.

## Required Actions

- Open an incident record with owner, severity, scope, and mitigation.
- Activate relevant kill switches when user harm or privacy exposure is plausible.
- Preserve audit logs without storing unnecessary sensitive payloads.
- Run post-incident review before resuming canary expansion.

## User Communication

Safety and privacy incidents require plain-language communication aligned with legal and compliance review.
