# Advanced Batch · Phase 2

Continuation of the Spiritual Formation Loop Engine, implementing the four
**clean gaps** that were not yet present in the repo (Worldview OS, Gifts &
Calling, and the Crisis engine already existed under the repo's own conventions):

| # | Module | Status |
|---|--------|--------|
| 1 | Real LLM Provider Layer | **new** |
| 3 | Group Leader Care Dashboard | **new** |
| 6 | Suffering Theology & Crisis **linkage** (lament + care plans + care signals) | **new** (extends existing crisis engine) |
| 2 | Supabase RLS | **new** (forward-looking SQL) |

Everything follows the **actual** repo conventions, which differ from the
idealized spec:

| Spec assumed | This repo actually uses | Consequence |
|---|---|---|
| SQLAlchemy 2.0 + Alembic | raw `psycopg2` + numbered idempotent SQL in `migrations/` | new migrations are `00NN_*.sql`, `CREATE … IF NOT EXISTS` |
| Supabase Auth, `users.id = auth.uid()` (UUID) | custom session auth, **email** is the user key (`users.id` is SERIAL) | tables key on `email`; RLS bridges via the JWT `email` claim |
| `community_groups` | `churches` + `church_members(church_id, email, role)` | "group" = church; care roles read from `church_members.role` |
| `ai_agent_runs`, async agents | existing `agent_runs` (BIGSERIAL), **sync** httpx | provider layer is synchronous, logs to `agent_runs` |
| Next.js App Router | **Vite + React 18** | the dashboard page is a React component in `bible3dsphere-frontend/src` |

---

## ⚠️ Concurrency note (please read)

While this was being built, a **second session was editing the same repo**
(migration files `0074`/`0075` changed identity under us and `0076`/`0077`/`0078`
were taken by `agent_runs_observability`, `theological_review_logs`,
`weekly_reviews`, `semantic_index`, `diagnostic_unified`). To avoid clobbering
that work:

- All four of my migrations were **renumbered to a clean `0080–0083` block**.
- I **did not** redefine `theological_review_logs` — the concurrent
  `0075_theological_review_logs.sql` owns it. My safety logger writes into
  **their** schema (`content_type` / `content_excerpt` / `review_status` /
  `detected_issues` / `reviewer`).
- `llm_provider_events` was **dropped**; provider observability is recorded onto
  their per-run `agent_runs` columns (`model_name`/`latency_ms`/`token_usage`/
  `error_message`/`skill_name`/`prompt_version`) — fully reconciled onto their design.

Because the other session is still moving the migration frontier, **verify the
final numbering before deploy** (the runner keys on the leading number as a PK).

---

## Files added

**Backend (`bible3dsphere/backend/`)**
- `llm_provider.py` — `LLMProvider` ABC + `MockLLMProvider`, `OpenAICompatibleProvider`,
  `AnthropicCompatibleProvider`, `GeminiCompatibleProvider`, `LocalLLMProvider`;
  `get_provider()` factory; `generate_json()` / `generate_text()` / `embed_text()`
  with schema validation, one retry, redaction, and `llm_provider_events` logging.
- `llm_schemas.py` — strict Pydantic v2 outputs (`DiagnosisAgentOutput`,
  `WorldviewAgentOutput`, `GiftCallingAgentOutput`, `SufferingAgentOutput`).
- `theological_safety.py` — `detect_crisis()` + `TheologicalSafetyService`
  (blocks prosperity-gospel / shaming / "AI replaces pastor" / sin-reductionism /
  spiritual-score-as-worth red lines); logs to `theological_review_logs`.
- `diagnosis_agent.py` — reference agent wiring the full path
  (agent_run → generate_json → safety review → deterministic fallback).
- `care_engine.py` — `CareSignalService` (dashboard from authorised summaries
  only; role gating; audit) — **no private logs, scores, or rankings** by construction.
- `suffering_engine.py` — `SufferingTheologyAgent` + crisis linkage
  (low/med → case + lament + care plan; high/critical → also `crisis_event` +
  `care_signal` escalation, never scripture-only).
- `routers/care.py`, `routers/suffering.py`
- `migrations/0080_llm_provider_layer.sql` (`llm_prompt_templates`, `audit_logs`)
- `migrations/0081_care_dashboard.sql` (`care_signals`, `care_actions`)
- `migrations/0082_suffering_care.sql` (`lament_prayers`, `suffering_care_plans`, + `suffering_cases` columns)
- `migrations/0083_advanced_batch_phase2_seed.sql` (prompt templates)
- `supabase_rls.sql` — forward-looking RLS for all private tables
- `tests/test_advanced_batch_phase2.py` — 19 no-DB tests

**Frontend (`bible3dsphere-frontend/src/`)**
- `CareDashboardPage.jsx` — minimal leader dashboard (props `{ user, token, churchId, onBack }`).
  Mount it from your router/nav, e.g.:
  `{panel === 'care' && <CareDashboardPage user={user} token={token} onBack={() => setPanel(null)} />}`
  (left unwired in `App.jsx` to avoid conflicting with the concurrent session.)

## Config (`core/config.py` / env)

```
LLM_PROVIDER=openai|anthropic|gemini|local|mock
LLM_MODEL=         LLM_API_KEY=        LLM_BASE_URL=
LLM_TIMEOUT_SECONDS=60   LLM_MAX_RETRIES=2
EMBEDDING_PROVIDER=openai  EMBEDDING_MODEL=  EMBEDDING_API_KEY=  EMBEDDING_BASE_URL=
AGENT_MODE=mock|real      THEOLOGICAL_SAFETY_REQUIRED=true
```
With `AGENT_MODE=mock` (or no key) the agents stay fully offline and deterministic.

## API

```
# Care (group_leader / pastor / owner / admin only; audited)
GET  /api/care/meta
GET  /api/care/groups/{church_id}/care-dashboard
POST /api/care/groups/{church_id}/signals
POST /api/care/signals/{signal_id}/actions      # pray|message|meet_1on1|refer_to_pastor|follow_up
POST /api/care/signals/{signal_id}/resolve

# Suffering (own data only)
POST  /api/suffering/cases/analyze
GET   /api/suffering/cases
GET   /api/suffering/cases/{id}
POST  /api/suffering/cases/{id}/lament-prayer
GET   /api/suffering/care-plans/active
PATCH /api/suffering/care-plans/{id}/status
```

## Run

```bash
# migrations apply automatically at app startup; or run the runner directly.
python -m pytest tests/test_advanced_batch_phase2.py -m no_db     # 19 pass, no DB needed
# (SQL validated against the real PostgreSQL grammar via pglast.)
```

## Acceptance (spec §八) — status

1. **LLM Provider** — mock/real switch ✓ · Pydantic-validated output ✓ · logs to
   `agent_runs` (model/latency/tokens/error) ✓ · user-visible content passes
   `theological_review_logs` ✓ · secret/PII redaction ✓
2. **Supabase RLS** — `supabase_rls.sql` provided ✓ · own-data-only ✓ ·
   `shared_reports` owner+recipient ✓ · `care_signals` leader-scoped ✓ ·
   `audit_logs` self-only + service_role notes ✓ (forward-looking — app not yet on Supabase Auth)
3. **Care Dashboard** — leader/pastor gating ✓ · no private logs / scores / rankings ✓ ·
   `care_actions` ✓ · every view audited ✓ · high/critical shows the real-care notice ✓
4. **Worldview OS** — already present (`0070–0074` pre-existing); provider/schema/safety now available to it.
5. **Gifts & Calling** — already present (`0069`); `GiftCallingAgentOutput` schema + no-absolute-prophecy guard added.
6. **Suffering & Crisis** — normal → `suffering_case` + `lament_prayer` + `care_plan` ✓ ·
   high-risk language → `crisis_event` ✓ · critical never scripture-only (real-person actions enforced) ✓ ·
   `care_signal` escalation to authorised leaders/pastors ✓

## Product line (enforced, not just hoped)
AI is not a shepherd; it never claims to replace church/pastor/companions.
Crisis always connects to a real human and is never answered with scripture alone.
No legalism, shame, prosperity gospel, mystical manipulation, or "spiritual score = worth".
Group oversight is consent-based, least-visible, revocable, and audited.
