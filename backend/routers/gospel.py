"""
Gospel router — 福音诊断室 (/api/gospel)

  GET  /api/gospel/meta        五个核心问题 + 偶像表
  POST /api/gospel/diagnose    双引擎诊断 → 属灵病历（落库 + 回流 formation）
  GET  /api/gospel/history     历史病历
钟马田诊断 + 司布真牧养。用户以 email 标识。
"""
from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:
    from backend import gospel_engine as engine
except Exception:  # pragma: no cover
    import gospel_engine as engine  # type: ignore

try:
    from backend.core.config import settings as _settings
except Exception:  # pragma: no cover
    try:
        from core.config import settings as _settings
    except Exception:
        _settings = None

router = APIRouter(prefix="/api/gospel", tags=["gospel"])
_state: Dict[str, Any] = {}


def init_gospel_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
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


class DiagnoseBody(BaseModel):
    event: str = Field(default="", max_length=3000)
    feeling: str = Field(default="", max_length=2000)
    want: str = Field(default="", max_length=2000)
    fear: str = Field(default="", max_length=2000)
    belief: str = Field(default="", max_length=2000)
    use_ai: bool = True


@router.get("/meta")
def get_meta() -> dict:
    return {"ok": True, **engine.meta()}


@router.post("/diagnose")
def diagnose(request: Request, body: DiagnoseBody) -> dict:
    user = _require_user(request)
    email = user["email"]
    inputs = body.model_dump()
    result = engine.analyze(inputs, settings=_settings, use_ai=body.use_ai)

    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO gospel_diagnoses "
                "(id, email, event, feeling, want, fear, belief, emotion, idol_type, "
                " unbelief, gospel_truth, scripture_ref, scripture_text, meditation, "
                " prayer, action, analysis_json) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (uuid.uuid4().hex, email, body.event.strip(), body.feeling.strip(),
                 body.want.strip(), body.fear.strip(), body.belief.strip(),
                 result["emotion"], result["idol_type"], result["unbelief"],
                 result["gospel_truth"], result["scripture"].get("ref", ""),
                 result["scripture"].get("text", ""), result["meditation"],
                 result["prayer"], result["action"], _Json(result)),
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

    # 回流 formation（看见偶像 + 应用福音）
    try:
        from formation_bridge import record_formation
        pats, lb, refl, emo = engine.formation_signal(result)
        record_formation(user.get("id"), pats, loop_broken=lb,
                         reflection_active=refl, emotional_intensity=emo,
                         decision_category="gospel")
    except Exception:
        pass
    try:
        from routers.theological_safety import safety_review_and_log
        _txt = chr(10).join(str(v) for v in result.values() if isinstance(v, str))
        _saf = safety_review_and_log(email=user["email"], content=_txt, content_type="gospel_diagnosis")
        result["safety_status"] = _saf.get("review_status")
        if _saf.get("review_status") == "blocked":
            result["safety_notice"] = "此内容可能涉及危机安全，请尽快联系可信的属灵同伴、牧者、家人或当地紧急服务；不要仅依赖属灵操练。"
    except Exception:
        result.setdefault("safety_status", "skipped")
    try:
        import diagnosis_hub
        diagnosis_hub.record_from_gospel(user["email"], None, result)
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
            cur.execute(
                "SELECT event, emotion, idol_type, gospel_truth, scripture_ref, "
                "scripture_text, action, created_at FROM gospel_diagnoses "
                "WHERE email=%s ORDER BY created_at DESC LIMIT %s",
                (user["email"], limit),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = [{
        "event": r[0], "emotion": r[1], "idol_type": r[2],
        "idol_name": engine.IDOLS.get(r[2], {}).get("name", r[2]),
        "gospel_truth": r[3], "scripture": {"ref": r[4], "text": r[5]},
        "action": r[6], "created_at": to_iso(r[7]),
    } for r in rows]
    return {"ok": True, "count": len(items), "items": items}
