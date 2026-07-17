# Spiritual Planet Batch 09 Report

Date: 2026-07-17
Scope: platform integration and unified orchestration over the existing FastAPI,
PostgreSQL and Vite React repositories.

## 1. System Context Map

Added the system boundary and adapter flow at
`docs/architecture/spiritual-planet/system-context-map.md`. Source modules feed
the Context Broker and command router through registered adapters; they do not
become subordinate storage inside Formation Twin.

## 2. Source of Truth Matrix

The matrix covers Identity, Worldview, Formation Twin/Engine, Prayer, Devotion,
Habit, Attention, Crisis, Gift/Calling, Church, Mission, Bible KG, Notification,
Search and Audit. Formation Twin owns normalized/reviewable life state only.

## 3. Event Schema Registry

Implemented 24 versioned `spiritual_planet.*` event registrations with producer,
schema URI, compatibility and payload field allowlists. Unregistered events and
payload fields fail closed. The PostgreSQL registry is seeded idempotently.

## 4. Context Broker

Implemented a single cross-module read boundary with current-user subject
binding, Purpose, Consent, projection whitelist, Confirmed/Pending separation,
source references, limitations, TTL and access audit. Full source bodies are
not returned or cached by the platform.

## 5. Purpose-Based Access

Policy is default deny. Unknown requester, purpose or projection is rejected;
service callers cannot bypass consent. Interactive consent applies only to the
platform's own user-requested Home/Timeline calls and is audit-referenced by
correlation ID.

## 6. Context Projections

Added versioned Prayer, Habit, Attention, Calling, Church, Mission, Formation,
Devotion, Scripture, Home, Timeline, Search and Crisis routing projections. Each
contains at most eight allowed fields and a 60–900 second TTL.

## 7. Agent Registry

Registered context provider, safety gate, recommendation arbitrator, proposal
generators, command executors and notification coordinator contracts. Analyzer,
proposal and execution permissions are structurally separated.

## 8. Unified Orchestrator

Added deterministic bounded orchestration: intent → safety → capacity →
arbitration → one result. Default limits are eight nodes and one possible model
call; the Batch 9 implementation uses zero model calls and has no recursive
agent invocation. Runs preserve correlation/trace metadata without user-intent
text.

## 9. Recommendation Arbitration

Implemented safety-first priority, explicit-user-intent precedence, expiry,
Pending rejection, duplicate merge, capacity downshift, active-action limit and
one-visible-action selection. Suppression reasons remain auditable.

## 10. Command Router

Implemented user-confirmation reference, consent, expiry, target payload
allowlist and idempotency checks. A local platform action adapter is executable.
Other source modules return `DEGRADED/TARGET_ADAPTER_UNAVAILABLE` until they
register an explicit Batch 9 command adapter; no core table is written directly.

## 11. Global Safety Arbitration

`ELEVATED` and `IMMINENT` stop ordinary formation, habit, calling, mission and
multi-action workflows. Allowed output is restricted to Crisis Care, safety
planning, human/professional support, brief user-requested prayer and simple
information. Crisis Care remains authoritative.

## 12. Unified Home

Added `/api/v1/platform/home` and a responsive portal. Home presents current
capacity, minimal safety summary, confirmed theme, short mirror, one question,
up to three actions and one focus action. Insufficient evidence is stated
explicitly and never replaced with generated filler.

## 13. Unified Action Center

Added non-moral action statuses, source ownership, focus marker, list/current/
detail and start/complete/skip/cancel APIs. External-source statuses are read
only; only the owning adapter may update them. Defaults are three active actions
and one focus action.

## 14. Unified Timeline

Added source-labelled current-user event references through the Context Broker.
The timeline supports module filtering and never copies raw source content.

## 15. Cross-Module Search

Added current-user-only search over confirmed, revocable platform references.
The default index excludes crisis bodies, third-party content, model-pending,
excluded and `STORE_ONLY` content. Search query text is not logged or audited.

## 16. Notification Coordinator

Added a pure notification coordinator with Crisis priority, sensitive generic
copy, quiet hours and ordinary reminder batching. Notification candidate storage
contains generic title/body only.

## 17. Consent Propagation

Projection consent can be granted or revoked per requester/purpose. Withdrawal
cancels queued/running workflows, cancels matching pending notifications,
excludes matching search references and writes a metadata-only propagation job.

## 18. Deletion Propagation

Added manifest, per-module acknowledgement, status/progress and retry APIs.
Local search, notification, job, platform action, context and cache stages are
handled. Neo4j, embedding and non-platform source adapters remain
`NOT_AVAILABLE` by default, so the manifest truthfully remains partially
completed rather than falsely reporting erasure.

## 19. Rebuild Coordinator

Added all required scopes, preservation counters, version record, create/get/
cancel APIs and explicit queued state. Ephemeral unified context rebuild is
synchronous; source-owned rebuilds wait for registered source workers.

## 20. Agent Conflict Resolution

Conflict handling rejects Pending-driven action, gives safety and user intent
precedence, merges duplicate human-connection proposals and reduces burden when
capacity is low. Only a single user voice is exposed.

## 21. Observability

Correlation/trace IDs, workflow steps, result/reason codes and technical module
status are recorded. No user intent text, source body, search query, emotion,
crisis type, church name or sensitive pattern is used as an observability label.

## 22. Integration Health

Added admin-only all/module health APIs, an admin-console health panel and a
circuit-breaker model. Platform and Formation Twin adapters report healthy;
systems that exist but lack a Batch 9 adapter report degraded, not healthy.
Ordinary users do not see the technical dashboard.

## 23. Failure Isolation

Feature flags independently control orchestration, Context Broker, arbitration,
Home, search, deletion, agent registry and health. Missing command/deletion/
rebuild adapters degrade their own operation without blocking Safety, Privacy or
navigation to other modules.

## 24. API

The new router exposes 38 routes under `/api/v1/platform`, including event
schemas, context resolution/audit/consent, orchestration, all recommendation
decisions, actions, Home, Timeline, Search, deletion, rebuild, integration health
and agent capability discovery.

## 25. Database Migration

`0215_spiritual_planet_platform_orchestration.sql` adds global contract
registries and owner-scoped consent, audit, run, candidate, arbitration,
command/result, action, notification, propagation, deletion/acknowledgement,
rebuild and search-reference tables. User tables use tenant/email ownership and
RLS via `app.current_user_email`. No spiritual scoring columns were added.

## 26. Frontend Information Architecture

The new Vite React surface has ten tabs: Home, Today, Twin, Practices, Calling,
Collaboration, Timeline, Search, Actions and Privacy. It is linked from
PlanetHome, the main App panel and SoulDashboard. Chinese-first labels retain
backend contract enums. Safety is always visible; technical Health is excluded
from ordinary-user navigation.

## 27. Contract Tests

Added backend tests for all event registrations, sensitive-field scanning,
Purpose/Consent/projection policy, Agent role separation, command fields and
required route/migration contracts. Added frontend API path and TypeScript
projection/action contracts.

Current targeted result: backend `43 passed` for the Batch 9 contract suite
(`45 passed` together with the shared database-parameter safety checks);
frontend `18 passed` across the new platform API/page and updated PlanetHome
tests. Full-suite results are recorded after final validation below.

## 28. E2E Tests

Component-level flows cover insufficient Home, Safety entry, source-module
navigation, explicit recommendation acceptance, consent grant and access audit.
Database-backed HTTP E2E was not executed because the local PostgreSQL service
is unavailable; this remains an external test-environment gate.

## 29. Red-Team Results

Tests reject nested raw prayer/crisis fields, all prohibited platform spiritual
scores, Pending-driven commands, service-role consent bypass, ordinary Crisis
workflows, sensitive notification copy and unregistered projection/purpose.
No high-severity issue was found in the pure contract path.

## 30. Data Quality Scan

Static checks confirm version/TTL/field limits for every projection, registration
for every platform event, unique Source of Truth coverage, RLS/tenant fields and
absence of prohibited score columns. Runtime cross-module completeness remains
degraded where source adapters have not been registered.

## 31. Performance Tests

The deterministic arbitrator processes the maximum contract batch of 20
candidates 100 times in under one second in the unit test. Context and search
queries use owner/time/status indexes and bounded limits. Database load and p95
latency require the Batch 10 production-like environment.

## 32. Known Risks

- Batch 5 long-term pattern and Life Season projections are now registered in
  the Formation Twin Context Broker adapter. Batch 6–8 adapters remain future
  integration work.
- Existing logical modules do not yet all expose Batch 9 context, command,
  deletion and rebuild adapters.
- Neo4j and embedding deletion acknowledgements are fail-closed by default.
- Database-backed migration/RLS/E2E could not run without local PostgreSQL.
- The existing `domain_events` transport is not a complete platform outbox/DLQ;
  Mission OS has an outbox pattern that can be generalized in Batch 10.
- Health is admin-gated and intentionally absent from ordinary-user UI.

These risks are surfaced as `DEGRADED`, `NOT_AVAILABLE`, `QUEUED` or partial
completion. None is reported as successfully integrated.

## 33. Batch 10 Integration Points

Batch 10 should add production source adapters, generalized transactional
outbox/dead-letter processing, database-backed contract/E2E/RLS isolation tests,
Neo4j/embedding deletion workers, source rebuild workers, OpenTelemetry export,
load/cost benchmarks, scenario simulation, safety/model/rule evaluations,
disaster recovery, release gates, migration rollback rehearsal and production
governance.

## Final validation

- Backend compile validation passed.
- Backend no-database suite: `1014 passed, 282 deselected`.
- Frontend full suite: `469 passed` across `100` files.
- Frontend production build passed with `2332` modules transformed and the new
  Spiritual Planet chunk emitted.
- Frontend full lint completed with `0 errors`; its `451 warnings` are existing
  repository warnings. Targeted Batch 9 feature lint has no errors.
- Backend and frontend `git diff --check` passed.
- PostgreSQL on the configured local port was unavailable and the local Docker
  daemon was not running. Migration execution, database RLS isolation and
  database-backed E2E therefore remain explicitly unverified rather than being
  reported as passed.
