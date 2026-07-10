# Attention Stewardship Release Report

- Git commit: `3ac3da1`
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
- No AI provider key detected; attention fallback must remain enabled.

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

Recommendation: GO only after frontend build, backend py_compile, smoke check, and manual privacy verification pass.
