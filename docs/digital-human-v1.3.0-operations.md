# Digital Human v1.3.0 Operations

This module implements the fail-closed application boundary for the Spiritual
Planet Digital Human skills package v1.3.0. It is integrated into the existing
FastAPI identity, database and rate-limit stack; it is not a separate service.

## Release boundary

- `catalog.v1.3.0.json` is a deterministic build artifact compiled from the
  validated skills package. Production never reads the sibling frontend
  checkout.
- The catalog exposes 100 stable character IDs and 532 truth-case IDs. It does
  not make every truth case speakable.
- Prepared answers can pass the speech gate after release approval. Hybrid
  lexical/dense/graph retrieval is auditable, but non-prepared retrieval output
  remains evidence-only and text-only until a human-reviewed answer is added.
- Dense retrieval is enabled only by an operator-provided local model at
  `DIGITAL_HUMAN_EMBEDDING_MODEL_PATH`; absence degrades visibly to lexical +
  graph retrieval and never triggers an implicit model download.
- Speech remains disabled until five distinct independent human roles approve
  the exact content/catalog/asset subject and a trusted Ed25519 release key
  signs the release certificate. Configure only the certificate and public-key
  paths; there is no boolean or version/hash approval bypass.
- Asset manifest entries require HTTPS model/portrait URLs, SHA-256 digests,
  voice identity/version, and theology/rights/accessibility review references.
  Placeholder or partial entries fail closed.
- Jesus, God and the Holy Spirit are not normal selectable chat characters.

## Deployment order

1. Validate the source package and compile the catalog.
2. Apply migrations `0242_digital_human_foundation.sql` and
   `0243_digital_human_assurance.sql`.
3. Deploy the backend with no approval variables and confirm text-only
   fallbacks, authentication, rate limits and metadata-only audit writes.
4. Complete theology, pastoral, rights, accessibility and release review.
5. Publish versioned GLB/portrait assets and approved voice identifiers to the
   asset manifest; never place vendor secrets in browser variables.
6. Run `prepare_digital_human_review_packet.py`; collect detached human
   attestations from five distinct trusted keys; then run
   `build_digital_human_release_evidence.py` using an offline release key.
7. Install `DIGITAL_HUMAN_RELEASE_CERTIFICATE_PATH` and
   `DIGITAL_HUMAN_TRUSTED_RELEASE_KEYS_PATH` and verify the exact asset manifest
   with `validate_digital_human_assets.py --verify-bytes --require-core-100`.
8. Enable LiveSpeak only with an allowlisted HTTPS embed URL.
9. Build the isolated worker image from the repository root:
   `docker build -f Dockerfile.livekit-agent -t bible3dsphere-livekit-agent:<revision> .`.
   Authenticate the official CLI with `lk cloud auth`, then deploy that exact
   image with `lk agent create --image bible3dsphere-livekit-agent:<revision>`.
   LiveKit Cloud injects the project URL/key/secret into the worker; do not bake
   them into the image. Keep the default LiveKit Inference model
   `deepgram/nova-3:multi`, or explicitly set `DIGITAL_HUMAN_STT_MODEL` in the
   worker environment.
10. Confirm the named agent `spiritual-planet-digital-human` is healthy with
    `lk agent status` and inspect `lk agent logs` for registration or STT
    failures. Only then configure the application backend with the same
    project `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` and set
    `DIGITAL_HUMAN_LIVEKIT_AGENT_READY=true`. The readiness flag is an operator
    gate, not a synthetic health check.
11. Run the real browser journey below before production promotion. A token
    contract test or a successful image build does not prove microphone,
    network, STT, reviewed response and avatar playback end to end.

## Data handling

`digital_human_turn_audit` intentionally has no columns for raw questions,
transcripts, microphone audio, answer text, confessions or health details. It
stores only owner, character, state, grounding, reason codes, references,
latency and trace metadata. Row-level security binds writes and reads to
`app.user_email`.

The browser adapter does not persist audio or transcripts. LiveKit tokens are
short lived, room scoped and minted only after existing session authentication.
The browser grant may publish microphone media but may not publish arbitrary
data. The client accepts only final `lk.transcription` streams that name the
currently published local microphone track. The interaction is half duplex:
microphone publishing stops before the reviewed turn request begins and remains
blocked while that turn or avatar speech is active.

## Qualification and operations

- Local concurrency: `python scripts/load_test_digital_human.py --mode in-process --requests 1000 --concurrency 32`.
- Target concurrency: rerun it with `--mode external --base-url ...`; auth is
  supplied only through `DIGITAL_HUMAN_LOAD_COOKIE` or
  `DIGITAL_HUMAN_LOAD_BEARER_TOKEN`.
- Vendor drill: `python scripts/run_digital_human_outage_drills.py`.
- Real browser voice journey: from the web repository run
  `npm run test:e2e:digital-human:live` with
  `DIGITAL_HUMAN_E2E_BASE_URL`, `DIGITAL_HUMAN_E2E_STORAGE_STATE` and
  `DIGITAL_HUMAN_E2E_AUDIO_FILE`. It requires a real deployment, authenticated
  Playwright storage state, real speech WAV, healthy LiveKit/STT Worker and
  reviewed LiveSpeak assets. Missing prerequisites fail preflight.
- The LiveKit Agent exposes Prometheus on
  `DIGITAL_HUMAN_AGENT_PROMETHEUS_PORT` (default 9091). The existing app exposes
  an admin-only, PII-free 15-minute dashboard backed by
  `/api/v1/digital-human/operations/metrics`.

## Rollback

1. Unset `DIGITAL_HUMAN_LIVEKIT_AGENT_READY`,
   `DIGITAL_HUMAN_LIVESPEAK_EMBED_URL`, release certificate/key paths and asset
   manifest variables.
   This immediately returns the feature to text-only, review-blocked behavior.
2. Remove the `characters` navigation entry in the web application if a full UI
   withdrawal is required.
3. After retention/export obligations have been checked, run the rollback for
   `0243` first, then
   `backend/migrations/rollback/0242_digital_human_foundation_down.sql` to drop
   the two module-owned tables.

## Evidence status

Package validation, local unit/API contract tests, frontend adapter tests,
local load/outage drills, database replay, linting and production frontend
compilation are local engineering evidence. They are not provider execution or
independent certification. Approved real media, provider credentials, a
deployed LiveKit agent, target-device voice journeys, target concurrency,
independent human review and production signatures remain external gates until
their revision-bound evidence is supplied.

## Local completion update — 2026-10-22

- `GET /api/v1/digital-human/characters/{id}/study` exposes the real 100-person,
  532-topic catalog with canonical citations and review-pending relationships.
  Study references are not complete answers. Prepared answer coverage remains
  five answers across four characters.
- Citation resolution supports compound, cross-chapter, single-chapter-book,
  whole-book and alias forms against the actual local canon. All 552 distinct
  catalog citations are checked by regression tests.
- Turn `context` accepts only `{characterId, topicIds}` (at most four). Topics
  are checked against the active character. Explicit followups reuse server-owned
  evidence; the backend does not store conversation text or trust browser-authored
  assistant claims.
- Unsupported intent takes precedence over prepared-topic anchors, including
  non-exact questions. Known scriptural historical questions are distinguished
  from a user's personal crisis without disabling the crisis boundary.
- Runtime diagnostics separate configuration presence, declared worker readiness,
  content approval and unverified real-provider execution. They do not certify
  media, inference, provider health or end-to-end voice.
- Admin-only `POST /draft-context` prepares source-bound draft context without
  calling a model. Admin-only `POST /drafts` requires explicit
  `DIGITAL_HUMAN_DRAFT_GENERATION_ENABLED=true` and the existing real provider
  configuration. It rejects Mock providers. Model results must pass structured
  identity/reference/claim-boundary validation and always remain
  `THEOLOGY_REVIEW`, non-speakable, and not automatically persisted or published.
  Citation membership is not semantic entailment; human review is mandatory.
- The public `/turns` route still never substitutes generated drafts for approved
  answers. Adding a reviewed draft to the versioned corpus requires the existing
  content change, independent review and signed release process.
- No database migration was added by this update. Production replay of 0242/0243,
  physical audit persistence, multi-instance metrics, real inference and provider
  voice remain separate acceptance gates.
