"""Ordo Amoris (Augustine) router — 失序之爱→重排 (/api/ordo). 奥古斯丁 ordo amoris。

注意：本文件是「奥古斯丁·爱的次序」服务端引擎版（prefix /api/ordo, 表 ordo_amoris_entries），
与既有的 routers/ordo_amoris.py（爱之秩序星图 /api/ordo-amoris, 表 ordo_amoris_records,
客户端 JS 引擎）是两个不同的功能；为避免符号冲突与覆盖既有已接线的路由，独立命名于此。
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:
    from backend import ordo_amoris_engine as engine
except Exception:  # pragma: no cover
    import ordo_amoris_engine as engine  # type: ignore
try:
    from backend.core.config import settings as _settings
except Exception:  # pragma: no cover
    try:
        from core.config import settings as _settings
    except Exception:
        _settings = None

router = APIRouter(prefix="/api/ordo", tags=["ordo"])
_state: Dict[str, Any] = {}


def init_ordo_amoris_augustine_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _extract_session_token(request: Request) -> str:
    token = request.cookies.get("biblesphere_session", "")
    auth = request.headers.get("Authorization", "")
    if not token and auth.startswith("Bearer "):
        token = auth[7:].strip()
    return token


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


class AnalyzeBody(BaseModel):
    loves: List[str] = Field(default_factory=list, max_length=32)
    text: Optional[str] = Field(default=None, max_length=4000)
    use_ai: bool = True


@router.get("/meta")
def get_meta() -> dict:
    return {"ok": True, **engine.meta()}


@router.post("/analyze")
def analyze(request: Request, body: AnalyzeBody) -> dict:
    user = _require_user(request)
    token = _extract_session_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Session expired or revoked")
    result = engine.analyze(body.loves, body.text, settings=_settings, use_ai=body.use_ai)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT u.id, u.email FROM user_tokens t "
                "JOIN users u ON lower(u.email) = lower(t.email) "
                "WHERE t.token = %s AND (t.expires_at IS NULL OR t.expires_at > NOW()) "
                "AND NOT COALESCE(u.is_banned, FALSE) "
                "FOR SHARE OF u",
                (token,),
            )
            live_account = cur.fetchone()
            if live_account is None:
                raise HTTPException(status_code=401, detail="Session expired or revoked")
            live_user_id, live_email = live_account[0], live_account[1]
            cur.execute(
                "INSERT INTO ordo_amoris_entries (id, email, input_text, crisis, analysis_json) "
                "VALUES (%s,%s,%s,%s,%s)",
                (uuid.uuid4().hex, live_email, (body.text or "")[:4000],
                 bool(result.get("crisis")), _Json(result)),
            )
            conn.commit()
    except HTTPException:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="save failed") from exc
    finally:
        _state["release_db"](conn)
    try:
        from formation_bridge import record_formation
        pats, lb, refl, emo = engine.formation_signal(result)
        record_formation(live_user_id or user.get("id"), pats, loop_broken=lb, reflection_active=refl, emotional_intensity=emo)
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
                "SELECT id, crisis, created_at FROM ordo_amoris_entries "
                "WHERE email=%s ORDER BY created_at DESC LIMIT %s",
                (user["email"], limit),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    iso = _state["to_shanghai_iso"]
    return {"ok": True, "items": [
        {"id": r[0], "crisis": r[1], "created_at": iso(r[2])}
        for r in rows]}


@router.get("/latest")
def latest(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT analysis_json, created_at FROM ordo_amoris_entries WHERE email=%s "
                "ORDER BY created_at DESC LIMIT 1", (user["email"],))
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not row:
        return {"ok": True, "entry": None}
    return {"ok": True, "entry": row[0], "created_at": _state["to_shanghai_iso"](row[1])}
