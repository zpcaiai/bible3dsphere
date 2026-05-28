# backend/routers — Domain Router Pattern

Each file owns one business domain. `main.py` only holds app init, lifespan,
middleware, and router registration.

## How to add a new router

1. Create `backend/routers/<domain>.py`
2. Define an `APIRouter` with `prefix="/api"` and a `tags` list.
3. Define an `init_<domain>_router(**kwargs)` that stores shared helpers in a
   module-level `_state` dict.
4. In `backend/main.py`:
   - Import: `from routers.<domain> import router as <domain>_router, init_<domain>_router`
   - Register: `app.include_router(<domain>_router)`
   - Init inside lifespan: `init_<domain>_router(get_db=_get_db, ...)`

## Current routers

| File | Domain | Endpoints |
|------|--------|-----------|
| `stats.py` | Observability & layout | `/api/stats`, `/api/layout`, `/api/history`, `/api/feature`, `/api/retrieval/evaluation` |
| `verse.py` | Verse retrieval & AI | `/api/query`, `/api/guidance`, `/api/biblical-example`, `/api/verse-prayer`, `/api/meditation-questions`, `/api/translate`, `/api/sermon`, `/api/faith-qa`, `/api/punctuation`, `/api/tts` |
| `journal.py` | Devotion & sermon journals | `/api/devotion/journals`, `/api/sermon/journals` |
| `prayer.py` | Prayer wall | `/api/prayers` |

## Shared dependency layer

`backend/core/deps.py` exposes:
- `init_deps(db_pool, settings)` — called once at startup
- `get_db_pool()` — access the pool
- `acquire_conn()` / `release_conn(conn)` — pool management
- `get_settings()` — settings singleton
- `get_session_user(request)` — optional auth
- `require_user(request)` — auth-required dependency (raises 401)
- `OptionalUser` / `AuthUser` — typed `Annotated` aliases for route signatures

## Domains still in main.py (next migration targets)

- `auth` — `/api/auth/*` (wechat, email, miniprogram)
- `user` — `/api/user/*`, `/api/daily-snapshot`, `/api/milestones`, `/api/spiritual-partner`
- `social` — `/api/personal/notes`, `/api/shared/notes`, share wall
- `behavior` — `/api/behavior/*`, `/api/habits/*`, `/api/reflection/*`
- `chat` — `/api/chat`
- `dating` — `/api/dating-priority/*`
