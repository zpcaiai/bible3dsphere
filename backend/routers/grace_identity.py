"""Grace Identity router — 与基督联合 / 恩典身份日志 (/api/grace-identity)."""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from routers.ordo_amoris import scan_crisis  # reuse authoritative safety scan

router = APIRouter(prefix="/api/grace-identity", tags=["grace-identity"])
_state: Dict[str, Any] = {}


def init_grace_identity_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
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


class GraceLogIn(BaseModel):
    input_text: str = Field(default="", max_length=4000)
    scenario: str = Field(default="", max_length=60)
    response: Dict[str, Any] = Field(default_factory=dict)
    route: str = Field(default="grace_identity", max_length=40)


@router.post("/log")
def create_log(request: Request, body: GraceLogIn) -> dict:
    user = _require_user(request)
    crisis = scan_crisis(body.input_text)
    route = "pastoral_or_crisis" if crisis else (body.route or "grace_identity")
    rid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO grace_identity_logs (id, email, input_text, scenario, response, route) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (rid, user["email"], body.input_text.strip(), body.scenario, _Json(body.response), route),
            )
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="save failed")
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
                "SELECT input_text, scenario, response, route, created_at "
                "FROM grace_identity_logs WHERE email=%s ORDER BY created_at DESC LIMIT %s",
                (user["email"], limit),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = [{
        "input_text": r[0], "scenario": r[1], "response": _load(r[2], {}),
        "route": r[3], "created_at": _iso(r[4]),
    } for r in rows]
    return {"ok": True, "items": items}
