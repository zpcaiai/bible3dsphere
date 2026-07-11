"""Rule of Life + Discernment router — 生命规则 + 依纳爵辨识 (/api/rule-discernment)."""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/rule-discernment", tags=["rule-discernment"])
_state: Dict[str, Any] = {}


def init_rule_discernment_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
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


class RuleIn(BaseModel):
    profile: Dict[str, Any] = Field(default_factory=dict)
    rule: Dict[str, Any] = Field(default_factory=dict)


class DiscernmentIn(BaseModel):
    decision_title: str = Field(default="", max_length=200)
    input: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)


@router.post("/rule")
def save_rule(request: Request, body: RuleIn) -> dict:
    user = _require_user(request)
    rid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO rule_of_life_rules (id, email, profile, rule) VALUES (%s,%s,%s,%s)",
                (rid, user["email"], _Json(body.profile), _Json(body.rule)),
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
    return {"ok": True, "id": rid}


@router.get("/rule/latest")
def latest_rule(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT profile, rule, created_at FROM rule_of_life_rules "
                "WHERE email=%s ORDER BY created_at DESC LIMIT 1",
                (user["email"],),
            )
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not row:
        return {"ok": True, "rule": None}
    return {"ok": True, "rule": {"profile": _load(row[0], {}), "rule": _load(row[1], {}),
                                 "created_at": _iso(row[2])}}


@router.post("/discernment")
def save_discernment(request: Request, body: DiscernmentIn) -> dict:
    user = _require_user(request)
    rid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO rule_discernment_cases (id, email, decision_title, input_payload, result) "
                "VALUES (%s,%s,%s,%s,%s)",
                (rid, user["email"], body.decision_title.strip(), _Json(body.input), _Json(body.result)),
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
    return {"ok": True, "id": rid}


@router.get("/discernment/history")
def discernment_history(request: Request, limit: int = Query(default=20, ge=1, le=100)) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT decision_title, input_payload, result, created_at FROM rule_discernment_cases "
                "WHERE email=%s ORDER BY created_at DESC LIMIT %s",
                (user["email"], limit),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = [{"decision_title": r[0], "input": _load(r[1], {}), "result": _load(r[2], {}),
              "created_at": _iso(r[3])} for r in rows]
    return {"ok": True, "items": items}
