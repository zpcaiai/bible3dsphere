"""Morning-dew router — 清晨甘露 (/api/dew). 司布真式每日默想，按日全站缓存。"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Query, Request

try:
    from backend import dew_engine as engine
except Exception:  # pragma: no cover
    import dew_engine as engine  # type: ignore
try:
    from backend.core.config import settings as _settings
except Exception:  # pragma: no cover
    try:
        from core.config import settings as _settings
    except Exception:
        _settings = None

router = APIRouter(prefix="/api/dew", tags=["dew"])
_state: Dict[str, Any] = {}
_SH = timezone(timedelta(hours=8))


def init_dew_router(*, get_db, release_db) -> None:
    _state.update(locals())


def _Json(obj):
    try:
        from psycopg2.extras import Json
        return Json(obj)
    except Exception:
        import json as _json
        return _json.dumps(obj)


@router.get("/today")
def today(request: Request, tier: int = Query(default=10)) -> dict:
    if tier not in (5, 10, 15):
        tier = 10
    d = datetime.now(_SH).date()

    # 1) 命中缓存？
    conn = _state["get_db"]() if _state.get("get_db") else None
    if conn is not None:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT content_json FROM daily_dew WHERE dew_date=%s AND tier=%s", (d, tier))
                row = cur.fetchone()
                if row and row[0]:
                    return {"ok": True, "cached": True, **(row[0] if isinstance(row[0], dict) else {})}
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            _state["release_db"](conn)

    # 2) 生成（AI，失败回退确定性）
    result = engine.generate(d, tier, settings=_settings, use_ai=True)

    # 3) 写缓存
    conn = _state["get_db"]() if _state.get("get_db") else None
    if conn is not None:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO daily_dew (dew_date, tier, content_json) VALUES (%s,%s,%s) "
                    "ON CONFLICT (dew_date, tier) DO NOTHING",
                    (d, tier, _Json(result)),
                )
                conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            _state["release_db"](conn)

    return {"ok": True, "cached": False, **result}
