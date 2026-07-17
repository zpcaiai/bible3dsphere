# Context Broker

All cross-module reads use this sequence:

```text
authenticate subject -> match current user/tenant -> validate purpose
-> validate persisted or interactive user consent -> intersect projection and
consent field allowlists -> read through registered source adapter -> remove
deleted/excluded records -> separate Confirmed/Pending -> redact source body
-> attach references and limitations -> set TTL -> write metadata audit
```

Unknown purpose, requester, projection or field is denied. A service actor is
subject to the same consent decision as a user-facing request. Interactive
consent is accepted only for the platform's own user-requested home/timeline
view and is recorded with the correlation ID; it cannot impersonate another
module.

Responses contain `confirmed_context`, `pending_context`, limitations, consent
references, source references, generation time and expiry. Crisis projections
never contain pending context or narrative. Stale contexts are invalid and are
not persisted as a reusable user cache.
