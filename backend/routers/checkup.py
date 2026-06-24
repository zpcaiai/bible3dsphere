"""Checkup router — 属灵低潮体检 (/api/checkup). 钟马田《属灵低潮》。"""
from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:
    from backend import checkup_engine as engine
except Exception:  # pragma: no cover
    import checkup_engine as engine  # type: ignore
try:
    from backend.core.config import settings as _settings
except Exception:  # pragma: no cover
    try:
        from core.config import settings as _settings
    except Exception:
        _settings = None

router = APIRouter(prefix="/api/checkup", tags=["checkup"])
_state: Dict[str, Any] = {}


def init_checkup_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
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


class SubmitBody(BaseModel):
    ratings: Dict[str, float] = Field(default_factory=dict)
    use_ai: bool = True


@router.get("/meta")
def get_meta() -> dict:
    return {"ok": True, **engine.meta()}


@router.post("/submit")
def submit(request: Request, body: SubmitBody) -> dict:
    user = _require_user(request)
    ratings = {k: float(v) for k, v in list(body.ratings.items())[:20]}
    result = engine.analyze(ratings, settings=_settings, use_ai=body.use_ai)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO spiritual_checkups (id, email, ratings, index_score, level, summary, analysis_json) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (uuid.uuid4().hex, user["email"], _Json(ratings), result.get("index", 0),
                 result.get("level", ""), result.get("summary", ""), _Json(result)),
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
                         emotional_intensity=emo, decision_category="checkup")
    except Exception:
        pass
    try:
        from routers.theological_safety import safety_review_and_log
        _txt = chr(10).join(str(v) for v in result.values() if isinstance(v, str))
        _saf = safety_review_and_log(email=user["email"], content=_txt, content_type="checkup")
        result["safety_status"] = _saf.get("review_status")
        if _saf.get("review_status") == "blocked":
            result["safety_notice"] = "此内容可能涉及危机安全，请尽快联系可信的属灵同伴、牧者、家人或当地紧急服务；不要仅依赖属灵操练。"
    except Exception:
        result.setdefault("safety_status", "skipped")
    try:
        import diagnosis_hub
        diagnosis_hub.record_from_checkup(user["email"], None, result)
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
            cur.execute("SELECT index_score, level, summary, created_at FROM spiritual_checkups "
                        "WHERE email=%s ORDER BY created_at DESC LIMIT %s", (user["email"], limit))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "items": [{"index": r[0], "level": r[1], "summary": r[2],
                                   "created_at": to_iso(r[3])} for r in rows]}
