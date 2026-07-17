# Formation Twin Batch 02 implementation report

## 1. Implemented life-event types

Version `1.0` supports daily check-in, journal, voice journal, prayer, devotion, habit, attention, church, relationship, calling, formation, crisis status, user correction, external module event, and the `OTHER` compatibility fallback. Provenance permits only `USER_REPORTED_FACT`, `OBSERVED_EVENT`, and `USER_CONFIRMED_PATTERN`; `SYSTEM_INFERENCE` is deliberately absent.

Python, TypeScript, and JSON Schema contracts are checked in and tested for enum parity, aware timestamps, statement types, version markers, and sensitive-body rejection.

## 2. Database tables

Migration `0212_formation_twin_life_events.sql` adds:

- `formation_twin_life_events`
- `formation_twin_sensitive_contents`
- `formation_twin_event_revisions`
- `formation_twin_ingestion_receipts`
- `formation_twin_ingestion_failures`
- `formation_twin_daily_checkins`
- `formation_twin_journals`
- `formation_twin_voice_journals`
- `formation_twin_source_connections`

The repository uses forward-only numbered SQL migrations, not Alembic. Therefore Batch 02 follows the existing migration runner rather than introducing a second migration framework.

## 3. API inventory

- Check-ins: create, list, get, revise, delete.
- Journals: create, list, get/decrypt, revise, delete; restore explicitly rejects permanently purged content.
- Voice journals: upload/transcribe, get, edit transcript, confirm, delete.
- Life events: controlled manual create, list/timeline, get, exclude, include, delete.
- Sources: list boundaries, pause, resume, authenticated internal module-event ingestion.
- Governance: owner data-quality report, complete owner export, confirmed full Formation Twin erasure.

OpenAPI generation confirms 21 versioned Formation Twin paths are registered in the real FastAPI app.

## 4. Source adapters completed

The minimum five adapters are implemented: Prayer, Holy Habit, Devotion, Attention, and Crisis. Formation, Worldview, Gift/Calling, and Church are also registered. The originating module remains source of truth; every source is paused by default and internal delivery requires `FORMATION_TWIN_SERVICE_KEY` plus an active owner authorization.

## 5. Adapter field boundaries

- Prayer allows session/time/duration/category/user tags/existence; blocks prayer body, person identity, medical and legal detail.
- Holy Habit allows habit/time/status/category; blocks private notes, partner messages, and notification body.
- Devotion allows session/time/completion/duration/scripture/user tags; blocks reflection and prayer body.
- Attention allows session/time/duration/user-reported distraction/summary metric; blocks browsing, chat/app body, contacts, and location.
- Crisis allows case reference/time/risk/resumable/status; blocks crisis body, safety plan, contact, medical, and method detail.
- Formation blocks effectiveness judgments and spiritual scores.
- Worldview blocks unconfirmed inference and hidden motive.
- Gift/Calling blocks divine determination and absolute-calling claims.
- Church blocks pastoral/discipline records, administrator spiritual ratings, and member identity.

Provenance retains accepted and discarded field names only; discarded values are not stored.

## 6. Encryption and retention

Sensitive body uses AES-256-GCM, a per-record random nonce, owner/content associated data, SHA-256 reference, and key version. Production must set a rotated 64-hex-character `FORMATION_TWIN_ENCRYPTION_KEY`; purpose-separated JWT-key derivation is only a local/test compatibility path.

Manual input defaults to `STORE_ONLY`. Voice audio is transient and records deletion immediately after transcription. The user can exclude or delete an event, pause a source, export all data, or permanently erase the subsystem. Purged ciphertext is intentionally not restorable.

## 7. Crisis-first verification

Check-in notes, journal body, manual summaries, and confirmed transcripts pass through the existing bilingual crisis scanner before canonical acceptance. Positive results return `ROUTED_TO_CRISIS`, surface the existing safety entry in the UI, and never copy crisis text into canonical or domain-event payloads. Crisis adapter ingestion accepts only minimal status metadata.

The safety path is contract-covered, but a live production crisis smoke test was not performed in this local run.

## 8. Test results

- Backend targeted suite: 20 passed, covering contracts, encryption, JSON Schema parity, migration inventory, data quality, and existing speech behavior.
- Frontend full suite: 94 files / 448 tests passed before the final contract-only additions.
- Frontend final Formation Twin suite: 5 files / 13 tests passed after all additions.
- Targeted frontend ESLint passed.
- Vite production build passed (existing large-chunk warnings remain).
- Python compilation, FastAPI OpenAPI generation, and `git diff --check` passed.

The local PostgreSQL test port was unavailable, so migration execution and database-backed E2E were not run in this environment.

## 9. Data-quality result

The owner-scoped scanner checks missing/invalid time, missing consent/provenance, canonical sensitive-key leak candidates, rejected/quarantined and excluded totals, and orphaned encrypted records. It fails closed with `quality_passed=false` when a high-severity issue exists. Unit fixtures passed; no production rows were scanned because no local database was available.

## 10. Incomplete items

- Deploy and execute migration `0212` against a staging PostgreSQL database, then run authenticated API E2E.
- Configure production encryption, service identity, and Deepgram secrets.
- Add calls from each existing module publisher to the internal adapter endpoint. The receiving adapters are complete, but source modules are not silently modified or auto-enabled.
- Add CI jobs for live PostgreSQL migration upgrade checks, cross-user isolation, full adapter matrices, and sensitive-leak scanning.
- The existing migration system is forward-only; a downgrade artifact is not provided.

These items are stated explicitly rather than treating unexecuted infrastructure checks as complete.

## 11. Batch 3 insertion points

Future processing can consume only events whose status is accepted, processing preference permits analysis, and exclusion is false. New nodes belong after safety/consent/minimization and before downstream state derivation. Any inferred state must use a new, separately governed statement type and must never mutate the Batch 02 source facts.

## 12. Known risks and technical debt

- Derived-key fallback couples decryptability to JWT-secret stability; production must use the dedicated key and a rotation plan.
- Internal adapters currently use synchronous database transactions rather than a durable workflow engine and retry worker.
- Source authorization is application-enforced and owner-scoped; database RLS is not enabled in the existing schema.
- Event lifecycle state is updated in place while revision provenance is appended; a future immutable ledger may separate lifecycle projections from event rows.
- Export includes decrypted owner body by design and therefore requires HTTPS, no intermediary logging, and careful client handling.
- Formation Twin does not calculate spiritual scores, infer motives, declare divine guidance, diagnose health conditions, or create an autonomous personality agent.
