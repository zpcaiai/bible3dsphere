# Event schema registry

`platform_orchestration.registry.EVENT_SCHEMAS` is the code-authoritative seed;
`spiritual_planet_event_schemas` is its auditable database representation.

The registry stores event type/version, producer, schema URI, compatibility,
allowed payload fields, deprecation state and migration guide. Publication is
rejected when the event or version is absent or the payload contains a field
outside its allowlist.

Registered domains cover context grant/deny, orchestration start/finish/fail,
recommendation creation/selection/suppression, command lifecycle, consent
propagation, deletion propagation, rebuild lifecycle, degraded/recovered
integration and contract violations.

Compatibility values are:

- `BACKWARD_COMPATIBLE`
- `FORWARD_COMPATIBLE`
- `FULL_COMPATIBLE`
- `BREAKING_CHANGE`

Contract tests verify registration completeness, versioned URIs, payload
allowlists and sensitive-field denial.
