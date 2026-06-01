"""Discernment router — 决策辨识（司布真版） (/api/discern)."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:
    from backend import decision_engine as engine
except Exception:  # pragma: no cover
    import decision_engine as engine  # type: ignore
try:
    from backend.core.config import settings as _settings
except Exception:  # pragma: no cover
    try:
        from core.config import settings as _settings
    except Exception:
        _settings = None

router = APIRouter(prefix="/api/discern", tags=["discern"])
_state: Dict[str, Any] = {}


def init_discern_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
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


class OptionIn(BaseModel):
    label: str = Field(default="", max_length=120)
    faith: float = Field(default=0, ge=0, le=10)
    obedience: float = Field(default=0, ge=0, le=10)
    love: float = Field(default=0, ge=0, le=10)
    fear: float = Field(default=0, ge=0, le=10)


class DiscernBody(BaseModel):
    situation: str = Field(default="", max_length=2000)
    options: List[OptionIn] = Field(default_factory=list, max_length=2)
    use_ai: bool = True


@router.get("/meta")
def get_meta() -> dict:
    return {"ok": True, **engine.meta()}


@router.post("/run")
def run(request: Request, body: DiscernBody) -> dict:
    user = _require_user(request)
    payload = {"situation": body.situation, "options": [o.model_dump() for o in body.options]}
    result = engine.analyze(payload, settings=_settings, use_ai=body.use_ai)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO decision_discernments (id, email, situation, options_json, recommended, analysis_json) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (uuid.uuid4().hex, user["email"], body.situation.strip(),
                 _Json(result.get("options", [])), result.get("recommended", 0), _Json(result)),
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
        record_formation(user.get("id"), pats, loop_broken=lb, reflection_active=refl,
                         emotional_intensity=emo, decision_category="discern")
    except Exception:
        pass
    return {"ok": True, **result}


@router.get("/history")
def history(request: Request, limit: int = Query(default=20, ge=1, le=100)) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT situation, options_json, recommended, created_at FROM decision_discernments "
                        "WHERE email=%s ORDER BY created_at DESC LIMIT %s", (user["email"], limit))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    out = []
    for r in rows:
        opts = r[1] if isinstance(r[1], list) else []
        rec = r[2] or 0
        out.append({"situation": r[0], "recommended_label": (opts[rec]["label"] if rec < len(opts) else ""),
                    "created_at": to_iso(r[3])})
    return {"ok": True, "items": out}
