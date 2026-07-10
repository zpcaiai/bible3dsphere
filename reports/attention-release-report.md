# Attention Stewardship Release Report

- Base Git commit: `d7e1411`
- Routes: 12
- Scripture library items: 10
- Warfare patterns: 9
- Challenge templates: 9
- Environment check: PASS

## Feature Flags

- `ATTENTION_MODULE_ENABLED`: `True`
- `ATTENTION_AI_ENABLED`: `True`
- `ATTENTION_COMMUNITY_ENABLED`: `True`
- `ATTENTION_GROUPS_ENABLED`: `True`
- `ATTENTION_ADMIN_ENABLED`: `True`
- `ATTENTION_E2E_MODE`: `False`
- `ATTENTION_DEMO_SEED_ENABLED`: `False`

## Warnings

- DATABASE_URL is not set in this process.
- APP_BASE_URL/VITE_API_BASE is not set; relative API base will be used.

## Latest Verification (2026-07-10)

- [x] Full backend suite: 843 tests.
- [x] Python compile plus attention security and permission audits.
- [x] Fresh UTF-8 PostgreSQL schema applied attention migrations 0146-0150 in one startup.
- [x] Demo seed executed twice idempotently; reset removed all reserved demo users.
- [x] Attention schema smoke check.

## Manual QA Checklist

- [ ] All /attention routes open and highlight correctly.
- [ ] All personal /api/attention routes require authenticated user.
- [ ] Attention admin APIs and UI are admin-only.
- [ ] Default visibility is status_only/private-first and sensitive categories hidden.
- [ ] Revoked shares are hidden and score sharing is opt-in.
- [ ] Group resources require active membership; no leaderboard is exposed.
- [ ] AI fallback works without provider key and does not expose raw prompt.
- [ ] No raw prayer/note/review/prompt/reflection logging.
- [ ] Dashboard, privacy, accountability, and groups work on mobile viewport.
- [ ] Smoke, build, and attention audit scripts have been run.

## Go/No-Go

Recommendation: GO only after frontend build, backend tests, py_compile, smoke check, permission/security audits, and manual privacy verification pass.
