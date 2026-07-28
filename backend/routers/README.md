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
| `film_studio.py` | Storyboard/PPT → video pipeline | `/api/film/start`, `/api/film/start-ppt`, `/api/film/status/{jid}`, `/api/film/sse/{jid}`, `/api/film/download/{fname}`, `/film-studio` |
| `media.py` | Multimodal outputs (guided narration, cards, clips, illustration) | `/api/tts/script`, `/api/media/card`, `/api/media/testimony-clip`, `/api/media/illustrate` |

## Multimodal media routes (`media.py`)

Backend half of `bible3dsphereWeb/docs/MULTIMODAL_OPPORTUNITY_AUDIT_2026-07.md` §6.
Nothing here is a new engine — every route wires up an existing base capability.

| Method | Path | Auth | Limit | Purpose |
|--------|------|------|-------|---------|
| `POST` | `/api/tts/script` | optional | 10/min | Guided narration. Body `{steps:[{text, pause_after_seconds, label}], voice_name, language_code, lead_in_seconds, inline_audio}`. Synthesizes each step, joins them with **real silence** of the requested length, returns one mp3 + cue points. Cached by content hash. |
| `GET` | `/api/tts/script/audio/{hash}.mp3` | none | — | Serves the cached script audio (immutable, content-hash filename). |
| `POST` | `/api/media/card` | optional | 30/min | Server-side card render, 1080×1350 (`aspect:"4:5"`) or 1080×1920 (`"9:16"`). Mirrors `src/lib/media/cardStudio.js` (5 gradient templates, badge/kicker/title/subtitle/sections/footer, CJK-per-char vs latin-per-word wrapping). Returns raw PNG. For push notifications / email where there is no canvas. |
| `POST` | `/api/media/testimony-clip` | required | 5/min | Multipart (`title`, `text`, `scripture`, `template`, `use_elevenlabs`, optional `audio`). Testimony → vertical 9:16 short video. Async: returns `{job_id, status_url, sse_url}`. |
| `GET` | `/api/media/testimony-clip/status/{job_id}` | required | — | Job polling. Same `JOBS` dict and ownership check as `/api/film/status`; `/api/film/sse/{job_id}` streams the same job, `/api/film/download/{file}` fetches the result. |
| `POST` | `/api/media/illustrate` | required | 6/min | Gemini image generation → R2. Content guardrail first: refuses depictions of Christ's face and any trauma / self-harm visualization with `{ok:false, refused:true, code, reason, guidance}` (HTTP 200, no model call, no spend). |
| `GET` | `/api/media/illustration/{hash}.png` | required | — | Local fallback when R2 env vars are absent. |

Reused, not reimplemented:

- `verse.py: synthesize_speech()` — the ElevenLabs → edge-tts → gTTS → Google Cloud fallback chain
  (extracted out of the `/api/tts` route body so both endpoints share one implementation).
- `film_studio.py` — `tts_to_file`, `kenburns_clip`, `concat_all`, `norm_vf`, `upload_r2`, `_ff`,
  `_audio_dur`, `_require_film_user`, `_is_spend_cap`, and the shared `JOBS` dict (so the testimony
  clip inherits the film jobs' concurrency guard, ownership checks, SSE and download routes).

`kenburns_clip(size=...)`, `concat_all(vf=...)`, `_normalize_clip(vf=...)` and `upload_r2(content_type=...)`
gained optional keyword arguments with the previous values as defaults — existing callers are unchanged.

Relevant env vars: `GEMINI_API_KEY` / `GOOGLE_API_KEY`, `GEMINI_IMAGE_MODEL` (default
`gemini-2.5-flash-image`), `IMAGEN_MODEL` (fallback), `R2_*`, `VIDEO_CDN_BASE`,
`R2_TESTIMONY_PREFIX`, `R2_ILLUSTRATION_PREFIX`, `TTS_SCRIPT_MAX_CHARS`,
`TESTIMONY_CLIP_MAX_CHARS` / `_MAX_AUDIO_BYTES` / `_MAX_SLIDES`.

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
