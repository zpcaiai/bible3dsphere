"""Morning-dew router — 清晨甘露 (/api/dew). 司布真式每日默想，按日全站缓存。"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

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
_EN_CACHE: Dict[Any, Any] = {}  # per-process English cache (date,tier)->result
_SH = timezone(timedelta(hours=8))


def init_dew_router(*, get_db, release_db, get_session_user=None, award_milestone_if_due=None, **kwargs) -> None:
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

    # English requests use a per-process cache so the shared (date,tier) DB
    # cache — which stores the Chinese variant — is never served to EN users
    # or vice versa.
    _en = False
    try:
        from lang_context import is_english as _is_en
        _en = _is_en()
    except Exception:
        _en = False
    if _en:
        _k = (d, tier)
        _hit = _EN_CACHE.get(_k)
        if _hit is not None:
            return {"ok": True, "cached": True, **_hit}
        _res = engine.generate(d, tier, settings=_settings, use_ai=True)
        _EN_CACHE[_k] = _res
        return {"ok": True, "cached": False, **_res}

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
 
 
class DewCheckinRequest(BaseModel):
    tier: int = Field(default=10, description="默想时长档位 (5, 10, 15)")
    reflection: str = Field(default="", max_length=2000, description="个人默想心得")
    prayer: str = Field(default="", max_length=2000, description="回应祷告")


@router.post("/checkin")
def checkin(payload: DewCheckinRequest, request: Request) -> dict:
    get_user = _state.get("get_session_user")
    user = get_user(request) if get_user else None
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="请先登录")
    email = user["email"]
    d = datetime.now(_SH).date()

    conn = _state["get_db"]() if _state.get("get_db") else None
    new_badges = []
    if conn is not None:
        try:
            with conn.cursor() as cur:
                if payload.reflection.strip() or payload.prayer.strip():
                    cur.execute(
                        "INSERT INTO devotion_journals (email, journal_date, title, reflection, prayer, mood) "
                        "VALUES (%s,%s,%s,%s,%s,%s) "
                        "ON CONFLICT (email, journal_date) DO UPDATE SET "
                        "reflection = EXCLUDED.reflection, prayer = EXCLUDED.prayer, updated_at = NOW()",
                        (email, d, f"清晨甘露默想 ({d})", payload.reflection.strip(), payload.prayer.strip(), "peace"),
                    )
                    conn.commit()
            if _state.get("award_milestone_if_due"):
                try:
                    new_badges = _state["award_milestone_if_due"](email, conn)
                except Exception:
                    pass
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            _state["release_db"](conn)

    try:
        import formation_events as _fe
        _fe.record_event(
            email, "dew", "checkin",
            title="完成清晨甘露默想",
            summary=(payload.reflection or f"完成了 {payload.tier} 分钟清晨甘露默想")[:120],
            severity="green",
            ref_id=f"dew:{d}:{payload.tier}"
        )
    except Exception:
        pass

    resp = {"ok": True, "date": str(d), "tier": payload.tier}
    if new_badges:
        resp["new_milestones"] = new_badges
    return resp

