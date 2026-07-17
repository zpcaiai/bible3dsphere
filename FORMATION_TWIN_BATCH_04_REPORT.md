# Formation Twin Batch 04 Report

Date: 2026-07-17
Status: implemented in the existing FastAPI/PostgreSQL backend and Vite/React web application; optional provider and Neo4j paths remain disabled by default.

## 1. Formation ontology

Added a closed 16-node ontology covering event, interpretation, identity, belief, desire, fear, emotion, temptation, choice, behavior, spiritual practice, outcome, grace evidence, protective factor, recovery response, and formation direction. Added closed scopes, source kinds, statement types, relations, Chinese labels, and JSON/TypeScript contracts. Salvation, repentance validity, divine satisfaction, personality, maturity, holiness, sin, idol, and spiritual ranking are intentionally absent.

## 2. Formation Chain data structure

Added source-separated nodes and edges, ordered chain-node/chain-edge join records, rule/user creation methods, review state, structural completeness, limitations, versioning, context exclusion, and `alternative_of_chain_id`. Rule assembly only links records in the same event; it does not fabricate missing nodes or assert causality. Users can create, reorder, add/remove, confirm, reject, exclude, delete, and duplicate a chain as another interpretation.

## 3. Identity and belief engine

Implemented explicit `IDENTITY_STATEMENT`, `INTERPRETATION`, and `BELIEF_STATEMENT` records with event scope and provenance. Manual entries are always `USER_REPORT / USER_REPORTED_FACT` and never receive a system confidence. Optional model expressions remain model records until a separate user-confirmed record is created.

## 4. Desire and fear engine

Implemented `DESIRE` and `FEAR` records as scoped observations rather than hidden-motive findings. Deep candidates require evidence, confidence, alternatives, expiration, and user review. The UI asks a user-facing reflective question and saves the user's own wording.

## 5. Temptation and choice point

Implemented `TEMPTATION` and `CHOICE` nodes without automatic sin/idol classification. The system can represent what a user reports or an authorized event observes, but it cannot declare the user's real temptation, moral state, or motive.

## 6. Behavior and outcome

Implemented `BEHAVIOR`, `SPIRITUAL_PRACTICE`, and `OUTCOME`. Canonical event behavioral/practice facts create neutral observed nodes. The engine records that an allowed fact was present and does not infer why it happened or whether it was spiritually successful.

## 7. Grace and protective factors

Implemented `GRACE_EVIDENCE`, `PROTECTIVE_FACTOR`, and `RECOVERY_RESPONSE`, displayed separately in snapshots and the UI. Grace/recovery is not inferred as a divine oracle; it is stored as user report or explicitly reviewed pattern.

## 8. Model formation hypotheses

Added provider-agnostic structured inference with strict Pydantic output. It is off by default and double-gated by profile setting and environment flag. It runs only on authorized text after a second crisis screen. Deep candidates require evidence spans, confidence, alternative explanations, `THIS_EVENT_ONLY` default scope, `PENDING` review, and 30-day expiration. Provider runs store metadata only.

## 9. Theological safety validation

Added formation-specific blocking for salvation/repentance verdicts, divine oracles, hidden motives, automatic idol/sin claims, diagnosis, personality verdicts, spiritual scores/ranks, and absolute causality. It composes with the existing theological safety service without logging candidate text. Crisis concern/elevated/imminent and routed-to-crisis events are excluded before formation processing.

## 10. User confirmation and scope mechanism

Added confirm, partial confirm, reject, relabel, change-scope, dismiss, bulk dismiss, delete, and revoke paths. Confirmation creates a separate `USER_CONFIRMED / USER_CONFIRMED_FORMATION_PATTERN` node; it never mutates a model record into a fact. Scopes are event, season, recurring context, or user-defined. Revocation deletes the derived confirmation and reopens the candidate.

## 11. Formation Graph

Added an optional Neo4j projection using the existing driver. PostgreSQL remains authoritative. Projection is profile/tenant isolated and contains only IDs, types, source/statement/review state, relation type, and SHA-256 content hashes. Full journal, prayer, confession, temptation, transcript, evidence text, and crisis text are excluded. Only confirmed chains can be synchronized; missing Neo4j is a normal `DISABLED` or `UNAVAILABLE` state.

## 12. Formation Engine integration

Added a source-separated context envelope instead of importing legacy Formation Engine scores. The `formation` target can receive a limited snapshot with reports, observed relations, confirmed patterns, grace/recovery, questions, and limitations only after its independent consent is enabled. No legacy maturity/tendency score is consumed or emitted.

## 13. Prayer, Habit, and Attention integration

Added independent, default-off consent flags and destination-specific field allowlists. Prayer receives only confirmed prayer/practice/grace context; Habit receives confirmed practice/recovery and protective factors; Attention receives confirmed, scoped context and protective factors. Pending hypotheses and full text are excluded. Reading context never auto-creates a prayer, habit, attention block, notification, or intervention.

## 14. API

Added 45 Batch 4 routes under `/api/v1/formation-twin`: settings, current/daily/weekly/rebuild state, node CRUD and review, review queue and bulk dismiss, chain CRUD/edit/alternative/status/graph sync, category lists, context envelopes, graph status, and data quality. The existing export and erase APIs now include and delete Batch 4 records.

## 15. Database migration

Added `0214_formation_twin_spiritual_formation.sql` with 19 tables: settings; eight category tables; nodes; evidence; edges; chains; ordered node/edge links; snapshots; reviews; model runs; and graph sync receipts. All tables have owner-scoped RLS. Constraints reject forbidden causal edge codes, invalid confidence ranges, model statement-type mismatch, self-links, and user reports with confidence.

## 16. Frontend page

Added the “属灵形成” Formation Twin workspace with nine transparent views: current state, chain builder, identity/belief, desire/fear, temptation/choice, behavior/outcome, grace/recovery, review queue, and boundaries/integrations. Source badges visibly distinguish user report, observation, rule, model candidate, and user confirmation. Chain cards support accessible drag reorder and alternative duplication. The settings view previews the exact downstream context envelope.

## 17. Test results

Targeted results at implementation time:

- Backend Batch 4 no-database tests: 21 passed; all Formation Twin Batch 2–4 tests: 48 passed.
- Repository-wide backend no-database suite: 971 passed, 238 live-database tests deselected.
- Frontend full suite: 459 passed across 98 test files; Formation Twin UI targeted tests: 9 passed across formation, emotions, and workspace, plus API contract coverage.
- Frontend production build: passed (Vite 5.4.11, 2328 modules transformed); pre-existing large-chunk warnings remain non-blocking.
- Python compilation for all new modules, router, and `main.py`: passed.

The repository-wide backend suite still requires the configured PostgreSQL test service on `localhost:5431`; when it is absent, database tests fail at fixture setup rather than in Batch 4 assertions. Live migration/API integration and Neo4j connectivity are therefore environment-gated, not claimed as executed here.

## 18. Red-team results

Automated red-team cases block salvation verdict, repentance verdict, God's-will oracle, hidden motive, automatic idol/sin, clinical diagnosis, personality verdict, spiritual score/rank, and absolute-cause language. Tests also verify that crisis records block processing, deep hypotheses without evidence/alternatives fail validation, rule chains do not fabricate missing states, and downstream contexts exclude pending hypotheses.

## 19. Data quality results

The data-quality endpoint checks model provenance, alternatives for deep hypotheses, confidence incorrectly attached to user reports, confirmed-source mismatch, and forbidden causal edges. The pure-engine test fixture passes all ontology and separation assertions. A live database quality scan is intentionally not reported without an applied migration and PostgreSQL test service.

## 20. Known risks

- Live PostgreSQL migration and HTTP integration tests require the external test database.
- Neo4j sync/erase requires configured credentials and was not exercised against a live graph.
- Optional model inference requires a configured provider and explicit user opt-in; it was contract/red-team tested but not called externally.
- The web build retains existing large bundle warnings unrelated to this module.
- Batch 4 describes event-scoped and short-window records; it does not establish long-term recurrence or causal truth.
- Specialized category tables and generic nodes intentionally duplicate a small reviewable statement for explicit queryability; erase covers both copies.

## 21. Batch 5 entry point

Batch 5 can build on immutable node/review provenance, event time, chain alternatives, snapshot versions, evidence hashes, and graph receipts to add multi-event grouping, time decay, user-confirmation learning, hypothesis expiration, life-stage context, and longitudinal trajectories. It must preserve the Batch 4 source boundaries and must not turn repeated observations into salvation, holiness, sin, idol, maturity, or divine-will scores.
