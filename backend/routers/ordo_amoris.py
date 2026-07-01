"""Ordo Amoris router — 爱之秩序星图 (/api/ordo-amoris).

Persists福音重排记录 per-email. Analysis is computed client-side (JS engine);
this layer stores structured records and runs an authoritative server-side
crisis scan so safety routing does not depend on the client.
"""
from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/ordo-amoris", tags=["ordo-amoris"])
_state: Dict[str, Any] = {}


def init_ordo_amoris_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    fn = _state.get("get_session_user")
    user = fn(request) if fn else None
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _Json(obj):
    try:
        from psycopg2.extras import Json
        return Json(obj)
    except Exception:
        return json.dumps(obj, ensure_ascii=False)


def _load(v, default):
    if v is None:
        return default
    if isinstance(v, (dict, list)):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return default
    return v


def _iso(dt):
    fn = _state.get("to_shanghai_iso")
    try:
        return fn(dt) if fn else (dt.isoformat() if hasattr(dt, "isoformat") else dt)
    except Exception:
        return str(dt)


_CRISIS_RE = re.compile(r"自杀|自残|想死|不想活|结束生命|活不下去|suicide|kill myself|end my life|self[- ]?harm", re.I)


def scan_crisis(text: str):
    """Authoritative safety scan. Prefers shared safety_scan, falls back to regex."""
    try:
        from safety_scan import scan_crisis as _sc  # type: ignore
        r = _sc(text or "")
        if r:
            return r
    except Exception:
        pass
    if _CRISIS_RE.search(text or ""):
        return {"level": "crisis",
                "message": "这可能涉及自我安全风险。你并不孤单，请优先联系可信的人或当地紧急/危机支持资源。"}
    return None


class OrdoRecordIn(BaseModel):
    input_text: str = Field(default="", max_length=4000)
    selected_keys: List[str] = Field(default_factory=list, max_length=32)
    matches: List[str] = Field(default_factory=list, max_length=16)
    response: Dict[str, Any] = Field(default_factory=dict)
    love_order_map: List[Any] = Field(default_factory=list)
    route: str = Field(default="ordo_amoris", max_length=40)


@router.post("/record")
def create_record(request: Request, body: OrdoRecordIn) -> dict:
    user = _require_user(request)
    crisis = scan_crisis(body.input_text)
    route = "crisis" if crisis else (body.route or "ordo_amoris")
    rid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ordo_amoris_records "
                "(id, email, input_text, selected_keys, matches, response, love_order_map, route) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (rid, user["email"], body.input_text.strip(), _Json(body.selected_keys),
                 _Json(body.matches), _Json(body.response), _Json(body.love_order_map), route),
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
    out = {"ok": True, "id": rid, "route": route}
    if crisis:
        out["crisis"] = crisis
    return out


@router.get("/history")
def history(request: Request, limit: int = Query(default=20, ge=1, le=100)) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT input_text, selected_keys, matches, response, love_order_map, route, created_at "
                "FROM ordo_amoris_records WHERE email=%s ORDER BY created_at DESC LIMIT %s",
                (user["email"], limit),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = [{
        "input_text": r[0],
        "selected_keys": _load(r[1], []),
        "matches": _load(r[2], []),
        "response": _load(r[3], {}),
        "love_order_map": _load(r[4], []),
        "route": r[5],
        "created_at": _iso(r[6]),
    } for r in rows]
    return {"ok": True, "items": items}
