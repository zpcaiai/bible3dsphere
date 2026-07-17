# Formation Twin Batch 07 Implementation Report

Batch 7 extends the existing FastAPI/PostgreSQL backend and Vite React frontend
with a user-confirmed, non-probabilistic early-protection layer. It reuses the
Formation Twin identity, RLS, event, safety, reflection and cross-module routing
foundations. Generic SQLAlchemy/Alembic/Next.js paths in the attachment were
mapped to the repositories' established SQL migration, router and UI patterns.

## 1. Temptation Cycle Ontology

Implemented scoped, versioned cycles with separate trigger, vulnerability,
emotion, environment, urge, temptation, choice point, behavior, outcome,
protection, resistance and recovery nodes. `TEMPTATION` cannot assert that
behavior occurred. Sensitive cycle types require explicit user confirmation,
and no permanent addiction/failure identity is created.

## 2. Trigger and Vulnerability Conditions

Risk conditions carry a category/code, visible description, source type,
statement type, occurrence and expiry time, evidence references, independence
group and confirmation state. Expired, unconfirmed, rejected, `STORE_ONLY` or
secret third-party data is excluded. Ordinary emotion, sleep or stress alone is
not treated as evidence that behavior will occur.

## 3. Cycle Builder

The API and frontend support user-built and user-confirmed rule/model proposals.
Users name the cycle, select conditions, confirm sensitive categories, add
protection/interruption/recovery paths, pause, resume, mark outdated, version or
delete it. Pastoral co-creation cannot activate without final user confirmation.

## 4. Risk Condition Combination Algorithm

The deterministic `temptation-risk-rules-1.0` matcher deduplicates evidence by
independence group, keeps unknown conditions unknown, requires at least two
independent ordinary conditions for a protection suggestion and accepts an
explicit current urge/behavior/help request as a separate immediate-support
path. Matching remains explainable and does not calculate relapse probability.

## 5. Evidence and Counterevidence

Snapshots retain matched conditions, active protection, missing/unknown
conditions, counterevidence, evidence quality, limitations and suppression
reasons. Protection can lower or suppress an ordinary warning. Current user
clarification outranks historical/model candidates; expired evidence does not
participate.

## 6. Internal Risk Bands

Internal bands are `NONE`, `CONTEXT_PRESENT`, `MULTIPLE_CONDITIONS`,
`STRONG_URGE_SELF_REPORTED`, `BEHAVIOR_STARTED`, `CONTINUATION_RISK` and
`CRISIS_RELATED`. They only select safety/routing policy. The public snapshot API,
notifications and event payloads remove the internal band.

## 7. User-Visible Warning Levels

Visible levels are `NO_WARNING`, `AWARENESS`, `PROTECTION_SUGGESTED`,
`IMMEDIATE_SUPPORT_SUGGESTED` and `CRISIS_HANDOFF`. A single ordinary condition
is capped at Awareness. Warning content states observed conditions, uncertainty
and one optional protection without displaying probability, countdown, moral
severity or spiritual risk scores.

## 8. Warning Decision and Cooldown

Warning policy requires consent or an explicit current help/crisis path, an
eligible confirmed cycle for ordinary matching, active lifecycle, evidence,
cooldown and quiet-hour checks. Defaults are 12 hours for Awareness and four
hours for Protection Suggested. Three recent false-positive/intrusion signals
extend cooldown and request recalibration rather than strengthening language.

## 9. Model Risk Candidates

The model validator accepts only candidates linked to existing confirmed cycles
and marked as requiring user confirmation. Prediction, diagnosis, moral judgment
or prohibited fields reject the complete result. Model candidates cannot trigger
a warning alone. No warning-model provider is configured in this batch, so the
deterministic rule path is the supported runtime.

## 10. Warning Content

Warnings follow observation, limited relation to a confirmed cycle, uncertainty
and one protection choice. Text validators reject numeric relapse/sin
probability, fear, shame, fixed identity, divine punishment/revelation and
coercive repentance/disclosure language. Sensitive lockscreen text is replaced
with “你有一项可选的保护提醒。”

## 11. Protection Action Library

Implemented environment exit, device distance, delay, Attention boundary,
support-message draft, short honest prayer, professional-support preparation,
Crisis handoff and `NO_ACTION`. Selection returns one primary action and supports
a smaller-step ladder. Environment/human connection is preferred in immediate
support; prayer never displaces safety or real-person support.

## 12. Protection Plan

Plans store early signs, contexts, one primary action, limited alternatives,
environment boundaries, support references and user-defined escalation. They are
private/inactive by default, require confirmation to activate, support rehearsal
without external execution, and can be paused, versioned or deleted.

## 13. Attention Environment Boundaries

Accepted Attention actions emit a minimal idempotent command with action type,
module, execution mode and confirmation only. `REMINDER_ONLY` is the default.
Hard block/accountability unlock require an explicit mode and visible recovery
method. The existing Attention consumer was not exercised end-to-end in this
batch; no device control is falsely reported as executed.

## 14. Accountability and Human Support

Contacts store an alias, role, external reference and explicit allowlisted
fields/actions. Roles confer no Twin access. The default is
`DRAFT_MESSAGE_ONLY`; messages and time-limited shares become drafts or
`READY_FOR_USER_SEND`. No external adapter is wired, so the system never reports
delivery and never automatically expands to more contacts.

## 15. Prayer, Formation and Habit Routing

Protection actions can target Prayer OS, Formation Engine and Attention OS via
minimal domain commands. Habit creation remains governed by Batch 6's second
confirmation and no-streak policy. These target consumers were not implemented
or live-tested here. Sensitive cycle history and source bodies are excluded from
routing payloads.

## 16. Crisis Care Integration

Crisis status is read before ordinary matching. Self-harm, harm to others,
violence, acute medical/intoxication risk or existing elevated/imminent Crisis
Care state stops normal warning/review and requests Crisis handoff. Ordinary
user-reported relapse remains ordinary recovery when no acute safety condition
exists. Crisis narrative is never copied into this module.

## 17. Relapse Recovery

Recovery is a separate safety-first workflow: current safety, stopping
continuation, human connection, one recovery action, then optional later review.
It does not initially ask why the event occurred, and it permits “no further
analysis today.” User behavior text is accepted only as an encrypted reference,
not duplicated in the recovery table or events.

## 18. Recovery Review

After safety is checked and the user reports stabilization, the system schedules
an optional 24-hour review; deferral moves it to 72 hours. Review input is capped
at four answers and may be skipped. Proposed cycle changes remain candidates
until a separate explicit cycle update, so one event cannot rewrite the entire
formation history.

## 19. Warning Feedback and False-Positive Learning

Users can mark accurate/helpful, inaccurate, early/late, frequent, intrusive or
sensitive exposure. Learning is owner-local, visible and resettable. Repeated
false positives extend cooldown, suggest recalibration and may pause passive
metadata; they do not intensify wording, collect more data or alter Crisis safety
thresholds.

## 20. Passive Signal Boundary

Passive metadata is disabled by default and requires separate consent. The
allowlist covers self-defined windows, self-reported sleep/alone/support state,
Attention summaries and boundary state. Browser/search/message content,
keystrokes, camera, microphone, photos, precise location, transaction content
and private-app content fail closed even when labelled metadata.

## 21. Notification and Quiet Hours

The default delivery channel is `IN_APP_ONLY`. Quiet hours apply to ordinary
warnings; an explicit current help request or Crisis state may receive immediate
in-session handling. Snooze supports 10/30 minutes, tonight, 24 hours, one cycle
or all warnings. There is no repeated push pressure, and no external notification
worker is claimed by this batch.

## 22. API

The protection router registers 66 owner-scoped endpoints under
`/api/v1/formation-twin` for cycles, current context, warnings/feedback, actions,
plans, contacts/drafts, recovery/reviews, settings, erasure, data quality,
workflow inspection and model/passive-signal validation. Existing authentication,
identity and database-pool conventions are reused.

## 23. Database Migration

`0218_formation_twin_temptation_risk.sql` adds 15 tables: 14 owner-data tables
with tenant/profile/email and RLS plus one global protection-template catalog.
The schema contains cycles/nodes/edges, conditions/snapshots/warnings/feedback,
actions/plans, contacts/requests, recovery/reviews and settings. It creates no
relapse, sin, purity, sobriety, obedience, salvation or spiritual risk score.
The repository migration runner is forward-only, so a separately located manual
rollback script is provided under `backend/migrations/rollback/`; it is outside
the runner glob and requires an explicit backup/data-retention decision.

## 24. Frontend Pages

The integrated protection center provides Current, Cycles, Plans, Warning
History, Recovery, Support Contacts and Privacy/Settings views and exposes the
ten requested information-architecture routes. It shows conditions, protection
and unknowns together, requires explicit action clicks, keeps contact actions as
drafts, supports immediate pause and uses a responsive keyboard-accessible
layout without red countdowns, streaks or failure counters.

## 25. Domain Events

The event registry covers cycle lifecycle, condition/snapshot/warning, action,
plan, support draft, recovery/review, suppression/failure and Crisis handoff.
Publishing is allowlisted to IDs, status, visible warning level, action/module,
delivery state and versions. Full journal/confession/behavior/crisis text,
contact/message data, internal bands and probabilities are excluded.

## 26. Test Results

Batch 7 contributes 65 backend domain/contract/privacy/red-team tests and 13
focused frontend component/contract/API tests. The combined Batch 4–7 backend
run passed 197 tests, and the Formation Twin frontend run passed 52 tests across
14 files. Full repository results are recorded under Final Validation.

## 27. Red-Team Results

Tests block relapse/sin percentages, inevitable failure, addiction identity,
hidden-sin claims, divine punishment, repentance purity tests, mandatory pastoral
disclosure, obedience scoring and “more monitoring proves sincerity.” Privacy
tests block raw browser/messages/keystrokes/camera/location, sensitive
notifications, unconfirmed routes and model-only warnings.

## 28. Data Quality Scan

The high-severity scanner detects unconfirmed sensitive/active cycles,
single-condition high warnings, missing uncertainty, unconfirmed sent support,
and recovery that did not begin with safety. High findings produce
`FAIL_CLOSED`. Upstream event/pattern deletion invalidates dependent conditions,
snapshots and warnings.

## 29. Privacy Audit

All user tables are owner-scoped and RLS-enabled. Public snapshots omit internal
bands; notifications and events are redacted; contacts receive no default
access; external messages are not sent. Export includes all Batch 7 owner data.
Scoped and full Formation Twin erasure cover all Batch 7 PostgreSQL tables and
mark cache/pending-delivery cleanup, while optional graph/embedding deletion is
reported according to actual adapter use.

## 30. Known Risks

- Local PostgreSQL/Docker availability is an external gate for live migration,
  manual rollback, RLS, trigger and DB-backed E2E verification.
- Attention, Prayer, Formation, Habit and support-delivery consumers were not
  executed end-to-end. Domain commands/drafts are persisted but do not imply
  target execution or message delivery.
- No model provider is configured; deterministic rules remain functional.
- Batch 7 does not project sensitive risk data to pgvector or Neo4j. Cleanup
  reports zero such rows/nodes rather than claiming an unavailable projection.
- Job/workflow definitions reuse the event/scheduler contract; production
  cadence and retry/dead-letter behavior remain deployment infrastructure work.
- Real-user calibration is required before broadening passive metadata or
  changing cooldown defaults.

## 31. Batch 8 Integration Points

Batch 8 can extend `READY_FOR_USER_SEND` into verified pastoral/accountability
collaboration with user invitation, relationship verification, field/purpose /
expiry authorization, revocation and abuse audit. It must never infer permission
from a role, expose the complete Twin, let feedback overwrite the user's account,
or turn this protection subsystem into church/family surveillance.

## Final Validation

- Backend compilation passed.
- Batch 7 backend focused suite: `65 passed`.
- Combined Batch 4–7 backend policy suite: `197 passed`.
- Formation Twin frontend suite: `52 passed` across `14` test files.
- Batch 7 focused frontend/API suite: `18 passed` across `3` test files.
- Full backend no-database suite: `1176 passed, 238 deselected`.
- Full frontend suite: `499 passed` across `106` test files.
- Frontend production build passed. The existing large-chunk advisory remains.
- Full frontend lint completed with `0 errors`; its `451 warnings` are existing
  repository warnings. Targeted Batch 7 lint has no findings.
- Translation-key generation added 79 English entries; final dry-run reports
  `0` missing keys.
- Backend and frontend whitespace checks passed.
- The 31 report sections, 10 required architecture documents, 66 API routes and
  15 migration tables were counted and confirmed.
- Local PostgreSQL on port `5431` was unavailable and the Docker daemon was not
  running. Live migration, RLS and database-backed E2E therefore remain
  explicitly unverified rather than being reported as passed.
