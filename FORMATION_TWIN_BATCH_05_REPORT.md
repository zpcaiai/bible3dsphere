# Formation Twin Batch 05 Implementation Report

Batch 5 is implemented as an incremental extension of the existing split
architecture: FastAPI + psycopg2/PostgreSQL in `bible3dsphere`, and Vite React in
`bible3dsphereWeb`. The attachment's SQLAlchemy/Alembic/Next.js paths were mapped
to the repository's established router, SQL migration, API client, overlay, and
Vitest conventions.

## 1. Temporal Model

Added timezone-aware DAY, WEEK, MONTH, QUARTER, YEAR and user-defined windows.
Boundaries use the user's IANA timezone and persist UTC instants. Exact,
approximate and unknown time precision remain distinct; occurrence, recording
and processing time are not collapsed.

## 2. Multi-Event Clustering Rules

Owner APIs support user-created clusters, member add/remove, rename, rejection,
and a 90-day regrouping cooldown. Original events and chains remain unchanged.
The rule engine groups only structured chain signatures with explicit reasons;
similar emotion words alone are insufficient.

## 3. Pattern Ontology

Patterns are versioned, scoped hypotheses with explicit source kind, statement
type, lifecycle, review status and due date. Grace, protection, recovery and
alternative responses are first-class. Fixed personality and hidden-motive
claims are rejected.

## 4. Evidence and Counterevidence Model

Supporting, counterevidence, context-limit, unresolved, superseded and invalid
roles are stored independently. Evidence references the source record but does
not copy sensitive bodies. `independence_group` prevents one journal's derived
nodes from being counted repeatedly.

## 5. Time Decay Algorithm

Configurable exponential half-lives reduce current relevance while retaining
history. User “still relevant” feedback and non-standard major events bypass
ordinary decay. Old evidence remains distinguishable from invalidated evidence.

## 6. Confidence Update Algorithm

Algorithm `pattern-confidence-1.0` combines deduplicated support, counterevidence,
source quality, temporal relevance, diversity, scope consistency and explicit
user feedback. It is replayable and append-only. User rejection has hard
priority and returns zero current support.

## 7. User Confirmation Learning

Confirmation, partial confirmation, rejection, relabelling and scope changes
create user-owned interpretation preferences. Preferences are visible and
revocable. Rejection is retained across rebuild and is never interpreted as
resistance or used for shared-model training.

## 8. Pattern Lifecycle

Implemented candidate, pending review, confirmed active/contextual, weakening,
dormant, resolved, outdated, rejected, invalidated and archived states. Only the
user may confirm or resolve. Every transition writes an append-only lifecycle
event.

## 9. Life Season

Users can create, edit, close, reopen, review and delete life seasons. A pattern
observed in one season remains season-specific. Closing a season makes related
active patterns contextual and due for review instead of extending them into the
next stage.

## 10. Formation Trajectory

Trajectories describe emerging, stable, weakening, replacing, dormant, resolved,
mixed or insufficient-data directions. User pattern actions and counterevidence
refresh metadata-only trajectory points; no growth percentage is produced.

## 11. Grace, Protection and Recovery Trajectories

Formation chains containing grace evidence, protective factors or recovery
responses produce dedicated positive pattern types. Counterexamples and
alternative responses remain visible so negative history cannot dominate the
current model.

## 12. Neo4j Temporal Evidence Graph

Added an optional metadata-only projection for patterns, evidence and life
seasons. Every query includes tenant and profile. Full sensitive text is never
projected. Disabled and unavailable graph infrastructure report honest degraded
status. PostgreSQL remains Source of Truth.

## 13. Restricted pgvector Use

Semantic retrieval is represented by a separate, default-off consent setting.
The implemented rule path does not require embeddings. No cross-user retrieval,
confirmed-pattern creation from similarity alone, or embedding of `STORE_ONLY`
records exists in this batch.

## 14. Formation Engine Integration

The long-term context endpoint emits only current, user-confirmed active,
contextual or weakening patterns plus confirmed seasons, alternatives, grace and
recovery. Pending, rejected, outdated, invalidated and resolved patterns are
excluded. Consent and crisis gates run before output.

Batch 9's Context Broker source adapter now reads confirmed Batch 5 patterns and
life seasons as metadata references while preserving Pending/Confirmed
separation.

## 15. API

The Batch 5 router adds pattern settings, temporal windows, clusters, patterns,
all review actions, evidence and counterevidence, life seasons, trajectories,
periodic reviews, rebuild jobs, current long-term state, Formation Engine context,
data quality, interpretation preferences and scoped long-term erasure under
`/api/v1/formation-twin`.

## 16. Database Migration

`0216_formation_twin_temporal_patterns.sql` adds 18 owner-scoped tables for
settings, windows, clusters, patterns, evidence, confidence history, lifecycle,
life seasons, trajectories, reviews, preferences, snapshots, rebuild checkpoints
and graph receipts. All tables contain tenant/profile/email ownership and RLS.
No personality or spiritual-scoring columns were introduced.

## 17. Frontend Pages

The existing Formation Twin overlay now includes Current Patterns, Candidates,
Trajectories, Life Seasons, Reviews and Evidence. It exposes the required route
semantics through internal navigation, shows scope/support/counterevidence, and
provides explicit confirm, narrow, reject, weakening, outdated and resolved
actions. Mobile layout and keyboard focus reuse the existing responsive surface.

## 18. Scheduled Jobs

The router registers the eight required job names and provides a versioned,
idempotent manual rebuild entry compatible with the existing scheduler. Rebuild
preserves rejections, excludes ineligible source data, creates a report, rebuilds
the snapshot and degrades cleanly when the model or graph adapter is unavailable.

## 19. Test Results

Batch 5 contributes 40 backend temporal-pattern tests and seven focused frontend
tests. The combined Batch 4/5/backend-parameter targeted run passed 63 tests;
the combined Batch 5/current-Formation-Twin frontend run passed 13 tests.

## 20. Red-Team Results

Tests block fixed personality, permanent-life-story, automatic-idol,
divine-punishment, salvation and spiritual-progress verdicts. Crisis processing,
single-event patterns, same-source duplicate evidence, user rejection override,
globalizing a season and sensitive graph payloads are all explicitly tested.

## 21. Data Quality Scan

High-severity checks cover missing scope, evidence, counterevidence, review date,
review status, lifecycle, limitations, model alternatives, prohibited fields and
ineligible patterns in current snapshots. High-severity results fail closed for
snapshot and Formation Engine context publication.

## 22. Known Risks

- Local PostgreSQL and Docker were unavailable during this implementation, so
  live migration, RLS isolation, trigger behavior and DB-backed E2E remain an
  external environment gate.
- Neo4j and pgvector are optional and not available in this checkout's runtime;
  their adapters are disabled/degraded rather than reported healthy.
- The existing `domain_events` transport is reused, but a generalized
  transactional outbox/dead-letter worker remains Batch 10 platform work.
- Scheduled job names and checkpoints are implemented; production cadence still
  depends on the deployment scheduler.
- Model-assisted pattern inference remains off by default and has no configured
  provider adapter. Deterministic rules remain functional.

## 23. Batch 6 Integration Points

Batch 6 can consume the consent-gated long-term context envelope: confirmed
patterns, current life seasons, alternatives, grace/protection, recovery and
limitations. It must retain crisis-first routing, one high-value question, one
small voluntary action, Pending/Confirmed separation, and capacity-aware burden.
It must not turn confidence, practice frequency or review completion into an
intervention priority score.

## Final Validation

- Backend compilation passed.
- Backend no-database suite: `1054 passed, 282 deselected`.
- Frontend full suite after translation generation: `476 passed` across `102`
  test files.
- Frontend production build passed with `2333` modules transformed and an
  updated Formation Twin chunk emitted.
- Full frontend lint completed with `0 errors`; its `451 warnings` are existing
  repository warnings. Targeted Batch 5 lint has no findings.
- Backend and frontend whitespace checks passed.
- Local PostgreSQL on the configured port was unavailable and the local Docker
  daemon was not running. Live migration, RLS and database-backed E2E therefore
  remain explicitly unverified rather than being reported as passed.
