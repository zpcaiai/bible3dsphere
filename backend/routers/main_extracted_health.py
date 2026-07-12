"""Health / liveness / AI-status 端点 — 从 main.py 逐字搬移（路径不变，无 prefix）。

main._db_pool 是运行期可变全局，因此以 getter（get_db_pool）注入；
_ai_status_payload 仍定义在 main.py（/api/home-bootstrap 也用它），此处注入引用。
"""
from __future__ import annotations

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

router = APIRouter()

# ── main.py 注入的依赖（导入期为 None，仅在请求期被调用）──
_get_db = None
_release_db = None
_get_db_pool = None
_ai_status_payload = None
_DATABASE_URL = None


def init_main_extracted_health(*, get_db, release_db, get_db_pool, ai_status_payload, database_url) -> None:
    global _get_db, _release_db, _get_db_pool, _ai_status_payload, _DATABASE_URL
    _get_db = get_db
    _release_db = release_db
    _get_db_pool = get_db_pool
    _ai_status_payload = ai_status_payload
    _DATABASE_URL = database_url


@router.get('/health')
def health_check() -> dict:
    return {
        'status': 'ok',
        'db': 'connected' if _get_db_pool() else 'no_database_url',
        'database_url_set': bool(_DATABASE_URL),
    }


@router.get('/health/live')
def health_live() -> dict:
    """Process liveness only; never depends on external services."""
    return {'status': 'live', 'service': 'bible3dsphere-api'}


@router.get('/health/ready')
def health_ready(response: Response) -> dict:
    """Deployment readiness includes a real database round trip."""
    if not _get_db_pool():
        response.status_code = 503
        return {'status': 'not_ready', 'database': 'not_configured'}
    conn = None
    try:
        conn = _get_db()
        with conn.cursor() as cur:
            cur.execute('SELECT 1')
            cur.fetchone()
        return {'status': 'ready', 'database': 'connected'}
    except Exception:
        response.status_code = 503
        return {'status': 'not_ready', 'database': 'unavailable'}
    finally:
        if conn is not None:
            _release_db(conn)

@router.get('/api/ai-status')
def get_ai_status_endpoint(response: Response) -> dict:
    response.headers['Cache-Control'] = 'public, max-age=60, stale-while-revalidate=300'
    return _ai_status_payload()


@router.get('/api/health/db')
def get_db_health(response: Response) -> dict:
    """数据库连接池健康自检（只读，无敏感信息）。

    返回 pre-ping 后取到活连接的耗时与连接池占用，便于部署后一眼确认
    pre-ping 生效、池未耗尽。DB 不可达时返回 503，方便探活/监控。"""
    response.headers['Cache-Control'] = 'no-store'
    import time as _t
    out = {'ok': False, 'db_configured': bool(_DATABASE_URL)}
    if not _DATABASE_URL:
        out['detail'] = '_DATABASE_URL not configured'
        return out
    # 连接池占用快照（ThreadedConnectionPool 私有计数，只读）
    try:
        _p = _get_db_pool()
        out['pool'] = {
            'min': getattr(_p, 'minconn', None),
            'max': getattr(_p, 'maxconn', None),
            'idle': len(getattr(_p, '_pool', []) or []),
            'in_use': len(getattr(_p, '_used', {}) or {}),
            'closed': bool(getattr(_p, 'closed', False)),
        }
    except Exception as exc:
        out['pool_error'] = str(exc)[:120]
    # 取活连接并计时（_get_db 内含 pre-ping / 陈旧连接回收）
    conn = None
    try:
        _t0 = _t.perf_counter()
        conn = _get_db()
        out['acquire_ms'] = round((_t.perf_counter() - _t0) * 1000, 2)  # 含 pre-ping/回收
        _t1 = _t.perf_counter()
        with conn.cursor() as cur:
            cur.execute('SELECT 1')
            cur.fetchone()
        out['ping_ms'] = round((_t.perf_counter() - _t1) * 1000, 2)     # 纯 SELECT 1 往返
        out['ok'] = True
    except Exception as exc:
        out['ok'] = False
        out['error'] = f'{type(exc).__name__}: {str(exc)[:160]}'
        response.status_code = 503
    finally:
        if conn is not None:
            try:
                _release_db(conn)
            except Exception:
                pass
    return out


@router.get('/api/health')
def health() -> dict:
    """Comprehensive health check — reports status of all critical subsystems.

    Response shape::

        {
          "ok": true,
          "status": "healthy",        // "healthy" | "degraded" | "unhealthy"
          "components": {
            "database": {"status": "ok",      "latency_ms": 2.1},
            "vector_index": {"status": "ok",   "feature_count": 1024},
            "embedding_service": {"status": "ok"},
            "mvfe_orchestrator": {"status": "ok"}
          },
          "version": "bible3dsphere/1.0"
        }
    """
    import time as _time
    components: dict = {}
    overall_ok = True

    # 1. Database connectivity
    conn = None
    try:
        _t0 = _time.perf_counter()
        conn = _get_db()
        with conn.cursor() as _cur:
            _cur.execute("SELECT 1")
        _lat = round((_time.perf_counter() - _t0) * 1000, 1)
        components["database"] = {"status": "ok", "latency_ms": _lat}
    except Exception as _e:
        components["database"] = {"status": "error", "detail": str(_e)[:120]}
        overall_ok = False
    finally:
        if conn is not None:
            _release_db(conn)

    # 2. Vector index (in-memory cache)
    try:
        from query_emotion_verses import _CACHE_FEATURES, _CACHE_FEATURE_EMBEDDINGS
        if _CACHE_FEATURES and _CACHE_FEATURE_EMBEDDINGS is not None:
            components["vector_index"] = {
                "status": "ok",
                "feature_count": len(_CACHE_FEATURES),
                "embedding_shape": list(_CACHE_FEATURE_EMBEDDINGS.shape),
            }
        else:
            components["vector_index"] = {"status": "cold", "detail": "cache not loaded yet"}
    except Exception as _e:
        components["vector_index"] = {"status": "error", "detail": str(_e)[:80]}

    # 3. Embedding service reachability (non-blocking check via cached state)
    try:
        import os as _os
        has_key = bool(_os.getenv("SILICONFLOW_API_KEY", ""))
        components["embedding_service"] = {
            "status": "ok" if has_key else "degraded",
            "provider": "SiliconFlow/BGE-M3",
            "key_configured": has_key,
        }
        if not has_key:
            overall_ok = False
    except Exception as _e:
        components["embedding_service"] = {"status": "error", "detail": str(_e)[:80]}

    # 4. MVFE orchestrator
    try:
        from mvfe.core.orchestrator import Orchestrator
        components["mvfe_orchestrator"] = {"status": "ok", "class": "Orchestrator"}
    except Exception as _e:
        components["mvfe_orchestrator"] = {"status": "error", "detail": str(_e)[:80]}
        overall_ok = False

    status = "healthy" if overall_ok else "degraded"
    degraded = [k for k, v in components.items() if v.get("status") not in ("ok", "cold")]
    if len(degraded) >= 2:
        status = "unhealthy"

    return {
        "ok": overall_ok,
        "status": status,
        "components": components,
        "version": "bible3dsphere/1.0",
    }


@router.get('/')
def serve_root():
    """API root — frontend is hosted independently at holiness.uk."""
    return JSONResponse({'service': 'biblesphere-api', 'status': 'ok', 'frontend': 'https://holiness.uk', 'docs': '/docs'})
