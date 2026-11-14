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
    _state.update(get_db=get_db, release_db=release_db, to_shanghai_iso=to_shanghai_iso)


def _require_live_account(cur, request: Request) -> str:
    # Match the application's cookie-first session precedence. Rechecking the
    # token in PostgreSQL prevents a cached session from surviving revocation.
    token = request.cookies.get("biblesphere_session", "")
    auth = request.headers.get("Authorization", "")
    if not token and auth.startswith("Bearer "):
        token = auth[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # The migration runner can continue after a failed migration. Ordo must
    # remain unavailable until the database can enforce account ownership.
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM pg_constraint AS c
            JOIN pg_attribute AS source_key
              ON source_key.attrelid = c.conrelid AND source_key.attname = 'email'
            JOIN pg_attribute AS target_key
              ON target_key.attrelid = c.confrelid AND target_key.attname = 'email'
            WHERE c.conrelid = 'public.ordo_amoris_records'::regclass
              AND c.conname = 'ordo_amoris_records_account_fk'
              AND c.contype = 'f' AND c.confrelid = 'public.users'::regclass
              AND c.conkey = ARRAY[source_key.attnum]
              AND c.confkey = ARRAY[target_key.attnum]
              AND c.confupdtype = 'c' AND c.confdeltype = 'c' AND c.convalidated
        )
        """
    )
    if not cur.fetchone()[0]:
        raise HTTPException(status_code=503, detail="Ordo account storage is unavailable")
    cur.execute(
        "SELECT u.email FROM user_tokens AS t JOIN users AS u ON u.email = t.email "
        "WHERE t.token = %s AND (t.expires_at IS NULL OR t.expires_at > NOW()) "
        "AND NOT COALESCE(u.is_banned, FALSE) AND t.data->>'id' = u.id::text "
        "AND LOWER(t.data->>'email') = LOWER(u.email) FOR SHARE OF u",
        (token,),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return row[0]


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
    rid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            email = _require_live_account(cur, request)
            crisis = scan_crisis(body.input_text)
            route = "crisis" if crisis else (body.route or "ordo_amoris")
            cur.execute(
                "INSERT INTO ordo_amoris_records "
                "(id, email, input_text, selected_keys, matches, response, love_order_map, route) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (rid, email, body.input_text.strip(), _Json(body.selected_keys),
                 _Json(body.matches), _Json(body.response), _Json(body.love_order_map), route),
            )
            conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail="save failed") from exc
    finally:
        _state["release_db"](conn)
    out = {"ok": True, "id": rid, "route": route}
    if crisis:
        out["crisis"] = crisis
    return out


@router.get("/history")
def history(request: Request, limit: int = Query(default=20, ge=1, le=100)) -> dict:
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            email = _require_live_account(cur, request)
            cur.execute(
                "SELECT input_text, selected_keys, matches, response, love_order_map, route, created_at "
                "FROM ordo_amoris_records WHERE email=%s ORDER BY created_at DESC LIMIT %s",
                (email, limit),
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
