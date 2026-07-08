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


def _is_stale_conn_error(exc) -> bool:
    """陈旧/被服务器掐断的连接错误 —— 回收换新即可。"""
    import psycopg2 as _pg
    if isinstance(exc, (_pg.OperationalError, _pg.InterfaceError)):
        return True
    m = str(exc).lower()
    return ('ssl connection has been closed' in m
            or 'server closed the connection' in m
            or 'connection already closed' in m
            or 'consuming input failed' in m
            or 'terminating connection' in m
            or 'bad connection' in m
            or 'connection not open' in m)


def acquire_conn():
    """Acquire a *live* connection from the pool (caller must release).

    Pre-pings with SELECT 1 and silently recycles stale/dead pooled
    connections (Neon/Render drop idle SSL conns) so callers never receive a
    connection the server has already closed. Genuine connectivity failures
    surface after a couple of quick retries."""
    import psycopg2 as _pg
    from psycopg2.pool import PoolError as _PoolError
    pool = get_db_pool()
    last_exc = None
    for _attempt in range(10):
        conn = None
        try:
            conn = pool.getconn()
            if getattr(conn, "closed", 0):
                pool.putconn(conn, close=True)
                conn = pool.getconn()
            with conn.cursor() as cur:          # pre-ping
                cur.execute('SELECT 1')
            try:
                conn.rollback()                 # 清掉探活事务，交出干净连接
            except Exception:
                pass
            return conn
        except Exception as exc:
            if conn is not None:
                try:
                    pool.putconn(conn, close=True)
                except Exception:
                    pass
            if not isinstance(exc, (_pg.Error, _PoolError)):
                raise
            last_exc = exc
            if _is_stale_conn_error(exc):
                continue                        # 静默换下一个
            if _attempt >= 2:                   # 真正故障：快速重试几次后上抛
                raise
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("acquire_conn: exhausted retries without a live connection")


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
import threading as _threading
import time as _time

_CHURCH_CACHE: dict = {}   # email -> (expires_ts, church_id | None)
_CHURCH_TTL = 60.0          # seconds
_CHURCH_CACHE_MAX = 5000    # hard size cap (bounded memory)
_CHURCH_CACHE_LOCK = _threading.Lock()  # writes can race across worker threads


def _church_cache_store(email: str, cid) -> None:
    """Insert/refresh an entry under lock, enforcing the size cap.

    Eviction: first purge expired entries; if still at the cap, drop the
    soonest-to-expire ~10% so the cache can never grow without bound.
    """
    now = _time.monotonic()
    with _CHURCH_CACHE_LOCK:
        if email not in _CHURCH_CACHE and len(_CHURCH_CACHE) >= _CHURCH_CACHE_MAX:
            for k in [k for k, v in _CHURCH_CACHE.items() if v[0] <= now]:
                _CHURCH_CACHE.pop(k, None)
            if len(_CHURCH_CACHE) >= _CHURCH_CACHE_MAX:
                for k in sorted(_CHURCH_CACHE, key=lambda k: _CHURCH_CACHE[k][0])[
                        :max(1, _CHURCH_CACHE_MAX // 10)]:
                    _CHURCH_CACHE.pop(k, None)
        _CHURCH_CACHE[email] = (now + _CHURCH_TTL, cid)


def get_user_church_id(cur, email: str, *, use_cache: bool = True):
    """Return the church_id (int) for *email*, or None if not a member.

    Accepts an already-open psycopg2 cursor so callers control the
    transaction/connection.  Results are cached for _CHURCH_TTL seconds
    (bounded to _CHURCH_CACHE_MAX entries, thread-safe).
    """
    if use_cache:
        with _CHURCH_CACHE_LOCK:
            entry = _CHURCH_CACHE.get(email)
        if entry and entry[0] > _time.monotonic():
            return entry[1]

    cur.execute(
        "SELECT church_id FROM church_members WHERE email=%s LIMIT 1",
        (email,),
    )
    row = cur.fetchone()
    cid = row[0] if row else None

    _church_cache_store(email, cid)
    return cid


def invalidate_church_cache(email: str) -> None:
    """Drop the cached church_id for *email* (call after join/leave/create)."""
    with _CHURCH_CACHE_LOCK:
        _CHURCH_CACHE.pop(email, None)
