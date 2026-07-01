"""loneliness router — 属灵星球扩充第四辑 (/api/loneliness)。引擎: loneliness_engine。"""
from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:
    from backend import loneliness_engine as engine
except Exception:  # pragma: no cover
    import loneliness_engine as engine  # type: ignore
try:
    from backend.core.config import settings as _settings
except Exception:  # pragma: no cover
    try:
        from core.config import settings as _settings
    except Exception:
        _settings = None

router = APIRouter(prefix="/api/loneliness", tags=["loneliness"])
_state: Dict[str, Any] = {}
_TABLE = "loneliness_entries"


def init_loneliness_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    getter = _state.get("get_session_user")
    user = getter(request) if getter else None
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _Json(obj):
    try:
        from psycopg2.extras import Json
        return Json(obj)
    except Exception:
        import json as _json
        return _json.dumps(obj)


class AnalyzeBody(BaseModel):
    text: str = Field(default="", max_length=4000)
    use_ai: bool = True


@router.get("/meta")
def get_meta() -> dict:
    return {"ok": True, **engine.meta()}


@router.post("/analyze")
def analyze(request: Request, body: AnalyzeBody) -> dict:
    user = _require_user(request)
    result = engine.analyze(body.text, settings=_settings, use_ai=body.use_ai)
    # best-effort 持久化：即使表尚未迁移，也不影响 analyze 正常返回
    if _state.get("get_db"):
        conn = _state["get_db"]()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO " + _TABLE + " (id, email, input_text, crisis, prayer, analysis_json) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (uuid.uuid4().hex, user["email"], body.text[:4000],
                     bool(result.get("crisis")), result.get("prayer", ""), _Json(result)),
                )
                conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            try:
                _state["release_db"](conn)
            except Exception:
                pass
    # 回流 formation（best-effort）
    try:
        from formation_bridge import record_formation
        pats, lb, refl, emo = engine.formation_signal(result)
        record_formation(user.get("id"), pats, loop_broken=lb, reflection_active=refl, emotional_intensity=emo)
    except Exception:
        pass
    return {"ok": True, **result}


@router.get("/history")
def history(request: Request, limit: int = Query(default=20, ge=1, le=100)) -> dict:
    user = _require_user(request)
    if not _state.get("get_db"):
        return {"ok": True, "items": []}
    conn = _state["get_db"]()
    rows = []
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, input_text, crisis, prayer, created_at FROM " + _TABLE + " "
                "WHERE email=%s ORDER BY created_at DESC LIMIT %s",
                (user["email"], limit),
            )
            rows = cur.fetchall()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        rows = []
    finally:
        try:
            _state["release_db"](conn)
        except Exception:
            pass
    iso = _state.get("to_shanghai_iso") or (lambda x: x)
    return {"ok": True, "items": [
        {"id": r[0], "text": r[1], "crisis": r[2], "prayer": r[3], "created_at": iso(r[4])}
        for r in rows]}


@router.get("/latest")
def latest(request: Request) -> dict:
    user = _require_user(request)
    if not _state.get("get_db"):
        return {"ok": True, "entry": None}
    conn = _state["get_db"]()
    row = None
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT analysis_json, created_at FROM " + _TABLE + " WHERE email=%s "
                "ORDER BY created_at DESC LIMIT 1", (user["email"],))
            row = cur.fetchone()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        row = None
    finally:
        try:
            _state["release_db"](conn)
        except Exception:
            pass
    if not row:
        return {"ok": True, "entry": None}
    iso = _state.get("to_shanghai_iso") or (lambda x: x)
    return {"ok": True, "entry": row[0], "created_at": iso(row[1])}
