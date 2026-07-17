# Formation Twin Batch 06 Implementation Report

Batch 6 extends the existing split architecture: FastAPI + psycopg2/PostgreSQL
in `bible3dsphere`, and Vite React in `bible3dsphereWeb`. It integrates the
structured outputs of Batches 2–5 into a capacity-aware reflection and voluntary
micro-intervention layer. Deterministic policy remains the authoritative path;
no new model provider is required.

## 1. Reflection Context

The context builder reads eligible life events, emotional state, confirmed
formation context, current temporal patterns and user preferences. It preserves
source references and limitations, excludes rejected/outdated/invalidated
hypotheses, and keeps pending clarification separate from confirmed context.
Sensitive source bodies are not copied into cross-module routing commands.

## 2. Capacity Model

Implemented low, normal and high capacity modes using explicit current signals
rather than a permanent user label. Capacity changes the amount of reflection,
the question burden and the intervention size. Low capacity reduces the system
to one gentle observation and an optional minimum action; crisis state bypasses
ordinary reflection entirely.

## 3. Daily Mirror

The daily mirror produces at most one bounded observation, one optional
high-value question and one optional action proposal. It shows evidence sources,
uncertainty and limitations, supports correction/versioning, and never renders
spiritual scores, streaks or completion pressure.

## 4. Weekly Review

The weekly review summarizes recurring context, counterexamples, recovery,
grace/protection and unfinished questions without converting frequency into a
growth grade. Users may review, correct, defer or skip it. The review continues
to work when model assistance is unavailable.

## 5. Question Selection

Question selection is deterministic and capacity-aware. It allows one question
only when the answer can materially improve understanding or action choice,
enforces a seven-day repetition guard, and supports answer, skip and “do not ask
again.” Questions that imply hidden motives, divine verdicts or diagnoses are
blocked.

## 6. Micro-Intervention Library

The intervention library contains small, domain-labelled options for Formation,
Prayer, Habit, Attention, rest, relationship and professional contexts. A
proposal returns no more than three candidates, explains why each may fit, and
allows a genuine `NO_ACTION` result. Crisis support is not represented as a
normal intervention.

## 7. Minimum Action Policy

Every proposed action has a smaller-step ladder and an explicit minimum action.
Selection prefers the least burdensome useful step compatible with current
capacity, consent and safety. It does not optimize engagement, streaks,
frequency, completion rate or a hidden spiritual-progress score.

## 8. User Decision Workflow

The workflow supports accept, modify, make smaller, request an alternative,
defer, skip, reject and choose no action. No downstream execution occurs before
an explicit decision. Habit creation/configuration requires a second explicit
confirmation. Decisions and corrections are append-only/versioned where
appropriate.

## 9. Formation Engine Routing

Accepted Formation actions emit an idempotent, minimal domain command using the
existing event transport. The command contains ownership, proposal/decision
references and the agreed action, not the source narrative. The target module's
consumer is outside this batch and was not exercised end-to-end.

## 10. Prayer OS

Prayer proposals route only after explicit acceptance and carry the smallest
agreed prayer practice. The policy blocks claims that God has revealed a hidden
cause, is punishing the user, or guarantees an outcome. Declining a prayer
proposal has no negative interpretation.

## 11. Holy Habit

Habit proposals remain suggestions until accepted, and configuration remains
pending until the second confirmation. This prevents a single click from
creating an ongoing obligation. The routing record is idempotent and carries no
formation score or coercive compliance metadata.

## 12. Attention OS

Attention actions use bounded practices such as a short pause, single-focus
window or notification reduction. They are capacity-aware and reversible.
Acceptance routes a minimal command; rejection or deferral does not trigger an
alternative automatically.

## 13. Rest, Relationship and Professional Routing

Rest, relationship and professional proposals are separated by domain and use
neutral, non-clinical language. Relationship actions avoid diagnosing another
person; professional actions avoid employment, legal or financial guarantees.
All three preserve the same explicit-decision and minimum-action gates.

## 14. Effect Review

Effect review records whether an action helped, felt neutral, felt burdensome,
was not attempted or should not be suggested again, with optional user notes.
It evaluates the proposal rather than the user's worth or faith. Reviews can be
recorded without manufacturing a success percentage.

## 15. Preference Learning

User-owned preferences learn from explicit decisions and effect reviews: desired
domains, burden tolerance, reminder choices and blocked suggestions. Preferences
remain visible, editable and revocable. Rejection is not interpreted as
resistance and is not converted into shared-model training data.

## 16. Anti-Gamification

The schema, API and UI omit points, levels, badges, streaks, leaderboards,
spiritual grades and competitive comparisons. History is chronological and
neutral. Practice frequency and review completion do not raise intervention
priority or produce a spiritual formation score.

## 17. AI Dependency

All required flows have deterministic policy implementations. Model-generated
text is optional, bounded by prohibited-field/phrase validation and cannot
override consent, crisis routing, data eligibility or execution rules. No model
provider adapter is configured in this batch, so model-assisted enrichment is
honestly unavailable while the core workflow remains functional.

## 18. API

The Batch 6 router adds 42 owner-scoped endpoints under
`/api/v1/formation-twin` for daily/weekly mirrors, context, questions, proposals,
decisions, executions, effect review, preferences, settings, data quality, job
registry and engagement-policy validation. Existing authentication and tenant /
profile ownership conventions are retained.

## 19. Database Migration

`0217_formation_twin_reflection_interventions.sql` adds 12 tables for contexts,
mirrors, questions/answers, intervention templates/proposals, decisions,
executions, effect reviews, preferences, weekly reviews and settings. User data
tables contain tenant/profile/email ownership and RLS; the template catalog is
global. No score, streak, rank or hidden-compliance column was introduced.

## 20. Frontend

The Formation Twin surface now includes Today, Weekly Review, Current Action,
History, Effect Review and Preferences/Settings views. It shows source and
limitation context, exposes every user decision, includes the habit second
confirmation, supports quiet hours and pause, and uses responsive, keyboard-
accessible controls. Crisis handoff replaces the ordinary proposal surface when
applicable.

## 21. Scheduling and Reminders

The job registry covers daily mirror preparation, weekly review, effect-review
follow-up and maintenance tasks. Reminder policy respects enablement, pause,
quiet hours, timezone and generic notification copy. Production cadence still
depends on the deployment scheduler; the batch does not claim that a local
registry is an active production worker.

## 22. Test Results

Batch 6 adds 57 backend policy/integration tests and 10 focused frontend tests.
They cover capacity, context eligibility, mirror limits, question repetition,
minimum actions, routing, effect learning, reminders, red-team constraints,
static migration/API wiring and performance bounds. Full-suite results are
recorded in Final Validation below.

## 23. Red-Team Results

Tests reject diagnosis, fixed personality, salvation state, divine punishment,
hidden motives, guaranteed outcomes, coercive language and spiritual scoring.
They verify crisis-first routing, no silent execution, habit double confirmation,
rejected-source exclusion, at-most-one reflection/question/action, `NO_ACTION`,
source minimization and anti-gamification policy.

## 24. Data Quality

High-severity checks cover missing ownership, source references, limitations,
capacity, question rationale, proposal rationale/minimum action, explicit
decision, idempotency key, effect semantics and prohibited fields. Invalid
records fail closed for reflection publication or downstream routing. Source
deletion/rejection/outdated transitions invalidate dependent Batch 6 artifacts.

## 25. Known Risks

- Local PostgreSQL and Docker availability are checked separately. If they are
  unavailable, live migration, RLS isolation, trigger behavior and database-
  backed E2E remain an explicit external environment gate.
- The existing `domain_events` transport is reused, but target Formation,
  Prayer, Habit and Attention consumers were not implemented or live-tested in
  this batch.
- Scheduled job definitions are present; production cadence, delivery and retry
  behavior depend on the deployment scheduler and worker infrastructure.
- Model-assisted rewriting is not connected to a provider. Deterministic
  reflection and intervention policies are the supported path.
- Rule-based capacity is deliberately conservative and should be reviewed with
  real user feedback before expanding automation.

## 26. Batch 7 Integration

Batch 7 can consume accepted action/execution references and effect reviews to
support longitudinal outcome evaluation. It must preserve explicit consent,
capacity snapshots, source eligibility, correction versions and `NO_ACTION`.
It must not reinterpret non-completion as failure, convert effect reviews into
a person-level score, or infer spiritual maturity from intervention frequency.

## Final Validation

- Backend compilation and focused Batch 4–6 policy tests passed.
- Full backend no-database suite: `1111 passed, 238 deselected`.
- Full Formation Twin frontend suite and focused Batch 6 tests passed.
- Full frontend suite: `486 passed` across `104` test files.
- Frontend production build passed with `2334` modules transformed.
- Full frontend lint completed with `0 errors`; its `451 warnings` are existing
  repository warnings. Targeted Batch 6 lint has no errors.
- Translation-key generation dry-run reports `0` missing keys.
- Backend and frontend whitespace checks passed.
- Local PostgreSQL on port `5431` was unavailable and the Docker daemon was not
  running. Live migration, RLS and database-backed E2E therefore remain
  explicitly unverified rather than being reported as passed.
