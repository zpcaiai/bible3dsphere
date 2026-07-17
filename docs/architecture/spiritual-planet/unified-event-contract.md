# Unified event contract

Every platform event uses a versioned envelope:

```json
{
  "event_id": "uuid",
  "event_type": "spiritual_planet.command_created",
  "event_version": "1.0",
  "tenant_id": "personal:user@example.com",
  "subject_user_id": "user@example.com",
  "actor": {"actor_type": "USER", "actor_id": "user@example.com"},
  "producer": "platform_orchestrator",
  "occurred_at": "ISO-8601",
  "published_at": "ISO-8601",
  "correlation_id": "uuid",
  "causation_id": null,
  "trace_id": "redacted technical trace",
  "data_classification": "HIGHLY_SENSITIVE",
  "purpose_tags": ["PLATFORM_COORDINATION"],
  "consent_reference_ids": [],
  "schema_uri": "spiritual-planet://events/spiritual_planet.command_created/1.0",
  "payload": {"command_id": "uuid", "target_module": "holy_habit"}
}
```

Payloads use registered fields only. The recursive scanner rejects complete
journal/prayer/transcript/confession/temptation/crisis content, third-party
details, prompts, internal risk scores and all prohibited platform spiritual
scores. The existing `domain_events` table transports this metadata envelope;
source bodies never enter it.

Breaking changes require a new major version, parallel support, a migration
guide and recorded consumer readiness. Minor additive changes must remain
backward compatible.
