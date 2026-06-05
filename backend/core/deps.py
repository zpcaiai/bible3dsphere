"""
Shared FastAPI dependency-injection helpers.

Every router imports from here rather than reaching into main.py globals.
The actual pools/caches are set once at app startup via init_deps().
"""
from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request

logger = logging.getLogger(__name__)

# ── Module-level singletons set by main.py at startup ────────────────────────
_db_pool = None        # psycopg2 ThreadedConnectionPool
_settings = None       # backend.core.config.Settings instance


def init_deps(db_pool, settings) -> None:
    """Called once during app lifespan startup."""
    global _db_pool, _settings
    _db_pool = db_pool
    _settings = settings


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_db_pool():
    if _db_pool is None:
        raise RuntimeError("DB pool not initialised — call init_deps() at startup")
    return _db_pool


def acquire_conn():
    """Acquire a connection from the pool (caller must release)."""
    return get_db_pool().getconn()


def release_conn(conn) -> None:
    if _db_pool is not None and conn is not None:
        try:
            _db_pool.putconn(conn)
        except Exception:
            pass


# ── Settings accessor ─────────────────────────────────────────────────────────

def get_settings():
    if _settings is None:
        raise RuntimeError("Settings not initialised — call init_deps() at startup")
    return _settings


# ── Session / auth helpers ────────────────────────────────────────────────────

def get_session_user(request: Request) -> Optional[dict]:
    """Return the authenticated user dict or None (does NOT raise)."""
    # Import lazily to avoid circular imports at module load time
    try:
        from main import _get_session_user  # type: ignore[import]
        return _get_session_user(request)
    except ImportError:
        pass
    try:
        from backend.main import _get_session_user  # type: ignore[import]
        return _get_session_user(request)
    except ImportError:
        return None


def require_user(request: Request) -> dict:
    """Dependency: raises 401 if not authenticated."""
    user = get_session_user(request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# Type aliases for use in route signatures
OptionalUser = Annotated[Optional[dict], Depends(get_session_user)]
AuthUser     = Annotated[dict,           Depends(require_user)]


# ── Church membership cache ───────────────────────────────────────────────────
import time as _time

_CHURCH_CACHE: dict = {}   # email -> (expires_ts, church_id | None)
_CHURCH_TTL = 60.0          # seconds


def get_user_church_id(cur, email: str, *, use_cache: bool = True):
    """Return the church_id (int) for *email*, or None if not a member.

    Accepts an already-open psycopg2 cursor so callers control the
    transaction/connection.  Results are cached for _CHURCH_TTL seconds.
    """
    if use_cache:
        entry = _CHURCH_CACHE.get(email)
        if entry and entry[0] > _time.monotonic():
            return entry[1]

    cur.execute(
        "SELECT church_id FROM church_members WHERE email=%s LIMIT 1",
        (email,),
    )
    row = cur.fetchone()
    cid = row[0] if row else None

    _CHURCH_CACHE[email] = (_time.monotonic() + _CHURCH_TTL, cid)
    return cid


def invalidate_church_cache(email: str) -> None:
    """Drop the cached church_id for *email* (call after join/leave/create)."""
    _CHURCH_CACHE.pop(email, None)
