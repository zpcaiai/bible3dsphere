"""
Worldview lenses router — 护教学 / 文化分辨 / 职业使命

Endpoints (prefix /api/worldview):
  GET  /lenses/meta            三个引擎的静态配置
  POST /apologetics/ask        护教学视角分析（可匿名）
  POST /culture/discern        文化时代精神分辨
  POST /vocation/analyze       职业使命世界观诊断

与 worldview.py 共享 /api/worldview 前缀；各路径不冲突。键以 email 为准。
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

try:
    from backend import apologetics_engine as apol
except Exception:  # pragma: no cover
    import apologetics_engine as apol  # type: ignore
try:
    from backend import cultural_engine as culture
except Exception:  # pragma: no cover
    import cultural_engine as culture  # type: ignore
try:
    from backend import vocation_worldview_engine as vocation
except Exception:  # pragma: no cover
    import vocation_worldview_engine as vocation  # type: ignore
try:
    from backend import suffering_engine as suffering
except Exception:  # pragma: no cover
    import suffering_engine as suffering  # type: ignore
try:
    from backend import worldview_llm as _llm
except Exception:  # pragma: no cover
    try:
        import worldview_llm as _llm  # type: ignore
    except Exception:
        _llm = None  # type: ignore


def _ai_default(v):
    if v is not None:
        return bool(v)
    try:
        return bool(_llm and _llm.available())
    except Exception:
        return False

router = APIRouter(prefix="/api/worldview", tags=["worldview"])

_state: Dict[str, Any] = {}


def init_worldview_lenses_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _user_email(request: Request, required: bool = True) -> Optional[str]:
    user = _state["get_session_user"](request)
    if (not user or not user.get("email")):
        if required:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return None
    return user["email"]


def _Json(obj):
    try:
        from psycopg2.extras import Json
        return Json(obj)
    except Exception:
        import json as _json
        return _json.dumps(obj)


def _save(sql: str, params: tuple) -> None:
    try:
        conn = _state["get_db"]()
    except Exception:
        return
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        try:
            _state["release_db"](conn)
        except Exception:
            pass


# 说明：危机升级现统一走 suffering_engine.run_and_persist → crisis_events + care_signals（团队 0077/0078）。
# 原 _draft_guardian_alert（写 guardian_alerts）已移除，避免与 care_signals 重复记录两套告警。


# ── Models ──────────────────────────────────────────────────────────────────
class ApologeticsRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    topic: str = Field(default="", max_length=80)
    locale: str = Field(default="zh-CN", max_length=16)
    use_ai: Optional[bool] = None


class CultureRequest(BaseModel):
    user_input: str = Field(min_length=1, max_length=4000)
    cultural_topic: str = Field(default="", max_length=120)
    use_ai: Optional[bool] = None


class VocationRequest(BaseModel):
    vocation_context: str = Field(min_length=1, max_length=4000)
    current_question: str = Field(default="", max_length=1000)
    use_ai: Optional[bool] = None


class SufferingRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    source_type: str = Field(default="journal", max_length=40)
    locale: str = Field(default="zh-CN", max_length=16)
    intensity: Optional[int] = Field(default=None, ge=1, le=10)
    use_ai: Optional[bool] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("/lenses/meta")
def lenses_meta() -> dict:
    ai = {"available": False}
    try:
        ai = _llm.meta() if _llm else {"available": False}
    except Exception:
        pass
    suffering_meta = {}
    try:
        suffering_meta = suffering.meta() if hasattr(suffering, "meta") else \
            {"engine": "suffering_engine", "via": "llm_provider+theological_safety"}
    except Exception:
        suffering_meta = {}
    return {"ok": True, "apologetics": apol.meta(), "culture": culture.meta(),
            "vocation": vocation.meta(), "suffering": suffering_meta, "ai": ai}


@router.post("/apologetics/ask")
def apologetics_ask(request: Request, body: ApologeticsRequest) -> dict:
    email = _user_email(request, required=False)  # 护教问题允许匿名
    result = apol.analyze(body.question, locale=body.locale, use_ai=_ai_default(body.use_ai))
    _save(
        "INSERT INTO apologetics_cases (id, email, topic, question, "
        " detected_presuppositions, secular_framings, biblical_framing, "
        " apologetics_response, scripture_refs, doctrine_tags, recommended_resources, "
        " confidence, pastoral_caution) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (uuid.uuid4().hex, email or "", result["topic"], body.question[:4000],
         _Json(result["detectedPresuppositions"]), _Json(result["secularFramings"]),
         result["biblicalFraming"], result["apologeticsResponse"],
         _Json(result["scriptureRefs"]), _Json(result["doctrineTags"]),
         _Json(result["recommendedResources"]), result["confidence"],
         (result["pastoralCautions"] or [""])[0]),
    )
    if email:
        try:
            import formation_events as _fe
            _fe.record_event(email, "apologetics", "diagnosis", domain="apologetics",
                             title="护教辨析", summary=(result.get("topic") or "")[:120] or None,
                             severity="green")
        except Exception:
            pass
    return {"ok": True, **result}


@router.post("/culture/discern")
def culture_discern(request: Request, body: CultureRequest) -> dict:
    email = _user_email(request, required=False)
    result = culture.discern(body.user_input, cultural_topic=body.cultural_topic,
                             use_ai=_ai_default(body.use_ai))
    _save(
        "INSERT INTO cultural_discernment_cases (id, email, cultural_topic, user_input, "
        " detected_spirits, cultural_liturgies, hidden_promises, hidden_demands, "
        " biblical_discernment, risks_for_user, counter_practices) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (uuid.uuid4().hex, email or "", result["culturalTopic"], body.user_input[:4000],
         _Json(result["detectedSpirits"]), _Json(result["culturalLiturgies"]),
         _Json(result["hiddenPromises"]), _Json(result["hiddenDemands"]),
         result["biblicalDiscernment"], _Json(result["risksForUser"]),
         _Json(result["counterPractices"])),
    )
    if email:
        try:
            import formation_events as _fe
            _fe.record_event(email, "culture", "diagnosis", domain="culture",
                             title="文化辨识", summary=(result.get("culturalTopic") or "")[:120] or None,
                             severity="amber")
        except Exception:
            pass
    return {"ok": True, **result}


@router.post("/suffering/analyze")
def suffering_analyze(request: Request, body: SufferingRequest) -> dict:
    """苦难神学分析。委托既有 suffering_engine（llm_provider + theological_safety，
    离线走 Mock 兜底）。安全优先：危机风险由 detect_crisis 兜底抬高，高危必含真实求助步骤，
    并落 crisis_event / care_signal。本端点不再自行做神学分类或持久化。"""
    email = _user_email(request, required=True)
    try:
        result = suffering.run_and_persist(
            email, body.text, source_type=body.source_type,
            get_db=_state["get_db"], release_db=_state["release_db"],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"suffering analysis failed: {exc}")
    return {"ok": True, **result}


@router.post("/vocation/analyze")
def vocation_analyze(request: Request, body: VocationRequest) -> dict:
    email = _user_email(request, required=True)
    result = vocation.analyze(body.vocation_context, current_question=body.current_question,
                              use_ai=_ai_default(body.use_ai))
    _save(
        "INSERT INTO vocation_worldview_cases (id, email, vocation_context, current_question, "
        " work_view_detected, calling_view_detected, money_view_detected, success_view_detected, "
        " possible_idols, kingdom_opportunities, ethical_risks, biblical_vocation_frame, "
        " suggested_next_steps) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (uuid.uuid4().hex, email, body.vocation_context[:4000], body.current_question[:1000],
         result["workViewDetected"], result["callingViewDetected"],
         result["moneyViewDetected"], result["successViewDetected"],
         _Json(result["possibleIdols"]), _Json(result["kingdomOpportunities"]),
         _Json(result["ethicalRisks"]), result["biblicalVocationFrame"],
         _Json(result["suggestedNextSteps"])),
    )
    return {"ok": True, **result}
