"""Cross / Lament / Hope router — 十架神学 · 哀歌 · 盼望 (/api/cross-lament-hope)."""
from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from routers.ordo_amoris import scan_crisis

router = APIRouter(prefix="/api/cross-lament-hope", tags=["cross-lament-hope"])
_state: Dict[str, Any] = {}

_UNSAFE_RE = re.compile(
    r"家暴|性侵|性虐|虐待|被打|被强迫|自杀|自残|想死|不想活|儿童安全|未成年|无法保证安全|"
    r"domestic violence|sexual assault|abuse|self[- ]?harm|suicide",
    re.I,
)


def init_cross_lament_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
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


def detect_unsafe(text: str):
    """Authoritative suffering-safety scan (crisis + abuse/violence)."""
    c = scan_crisis(text or "")
    if c:
        return {"route": "crisis_or_professional_support", "safety": c}
    if _UNSAFE_RE.search(text or ""):
        return {"route": "crisis_or_professional_support",
                "safety": {"level": "crisis",
                           "message": "这可能涉及安全风险。请优先联系当地紧急资源、可信的人和合格专业支持。"}}
    return None


class LamentIn(BaseModel):
    category_key: str = Field(default="", max_length=40)
    input_text: str = Field(default="", max_length=6000)
    frame: Dict[str, Any] = Field(default_factory=dict)
    route: str = Field(default="cross_lament_hope", max_length=40)


@router.post("/lament")
def save_lament(request: Request, body: LamentIn) -> dict:
    user = _require_user(request)
    unsafe = detect_unsafe(body.input_text)
    route = unsafe["route"] if unsafe else (body.route or "cross_lament_hope")
    rid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO cross_lament_records (id, email, category_key, input_text, frame, route) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (rid, user["email"], body.category_key, body.input_text.strip(), _Json(body.frame), route),
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
    if unsafe:
        out["safety"] = unsafe["safety"]
    return out


@router.get("/history")
def history(request: Request, limit: int = Query(default=20, ge=1, le=100)) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT category_key, input_text, frame, route, created_at FROM cross_lament_records "
                "WHERE email=%s ORDER BY created_at DESC LIMIT %s",
                (user["email"], limit),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = [{"category_key": r[0], "input_text": r[1], "frame": _load(r[2], {}),
              "route": r[3], "created_at": _iso(r[4])} for r in rows]
    return {"ok": True, "items": items}
