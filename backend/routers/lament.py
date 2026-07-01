"""Lament router — 哀歌 (/api/lament). Vroegop《Dark Clouds, Deep Mercy》四步哀歌。"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:
    from backend import lament_engine as engine
except Exception:  # pragma: no cover
    import lament_engine as engine  # type: ignore
try:
    from backend.core.config import settings as _settings
except Exception:  # pragma: no cover
    try:
        from core.config import settings as _settings
    except Exception:
        _settings = None

router = APIRouter(prefix="/api/lament", tags=["lament"])
_state: Dict[str, Any] = {}


def init_lament_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
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


class ComposeBody(BaseModel):
    text: str = Field(default="", max_length=4000)
    situation: Optional[str] = Field(default=None, max_length=400)
    use_ai: bool = True


@router.get("/meta")
def get_meta() -> dict:
    return {"ok": True, **engine.meta()}


@router.post("/compose")
def compose(request: Request, body: ComposeBody) -> dict:
    user = _require_user(request)
    result = engine.compose(body.text, body.situation, settings=_settings, use_ai=body.use_ai)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO lament_entries (id, email, input_text, situation, crisis, prayer, analysis_json) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (uuid.uuid4().hex, user["email"], body.text[:4000], (body.situation or "")[:400],
                 bool(result.get("crisis")), result.get("prayer", ""), _Json(result)),
            )
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"save failed: {exc}")
    finally:
        _state["release_db"](conn)
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
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, situation, crisis, prayer, created_at FROM lament_entries "
                "WHERE email=%s ORDER BY created_at DESC LIMIT %s",
                (user["email"], limit),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    iso = _state["to_shanghai_iso"]
    return {"ok": True, "items": [
        {"id": r[0], "situation": r[1], "crisis": r[2], "prayer": r[3], "created_at": iso(r[4])}
        for r in rows]}


@router.get("/latest")
def latest(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT analysis_json, created_at FROM lament_entries WHERE email=%s "
                "ORDER BY created_at DESC LIMIT 1", (user["email"],))
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not row:
        return {"ok": True, "entry": None}
    return {"ok": True, "entry": row[0], "created_at": _state["to_shanghai_iso"](row[1])}
