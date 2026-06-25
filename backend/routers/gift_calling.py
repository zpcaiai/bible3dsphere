"""
Gift & Calling router — 恩赐与呼召识别系统 (/api/gift)

  GET  /api/gift/meta                 维度/恩赐/果子/使命/风险/服事清单 + 神学边界
  GET  /api/gift/profile              当前用户最近一次完整测评（聚合报告）
  POST /api/gift/assess               提交问卷 → 跑 8 Agent → 落库 → 返回完整报告
  GET  /api/gift/history              历次测评列表
  GET  /api/gift/assessment/{id}      指定测评的完整报告
  POST /api/gift/feedback            提交共同体反馈（牧者/同工/被服事者…）
  GET  /api/gift/feedback            当前用户收到的共同体反馈
  POST /api/gift/review              新增一条长期复盘
  GET  /api/gift/review             复盘记录列表

闭环：问卷 → 优势/恩赐/果子/使命 → 风险 → 服事匹配 → 30/90/180 计划 → 共同体反馈 → 复盘。
用户以 email 标识；AI 失败时全程有确定性兜底。
神学边界：本系统只做辅助辨识，不宣告最终呼召（theological_boundary_ack 记录确认）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:
    from backend import gift_calling_engine as engine
except Exception:  # pragma: no cover
    import gift_calling_engine as engine  # type: ignore

try:
    from backend.core.config import settings as _settings
except Exception:  # pragma: no cover
    try:
        from core.config import settings as _settings
    except Exception:
        _settings = None

router = APIRouter(prefix="/api/gift", tags=["gift"])
_state: Dict[str, Any] = {}


def init_gift_calling_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    """由 main.py 注入依赖（与 disciple 路由一致）。"""
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


def _norm_conf(c: Any) -> str:
    return c if c in engine.CONFIDENCE_LEVELS else "medium"


# ─────────────────────────────────────────────────────────────────────────────
# 请求体
# ─────────────────────────────────────────────────────────────────────────────

class AssessBody(BaseModel):
    experiences: str = Field(default="", max_length=6000)
    interests: str = Field(default="", max_length=6000)
    service: str = Field(default="", max_length=4000)
    others_say: str = Field(default="", max_length=4000)
    burdens: str = Field(default="", max_length=4000)
    skills: str = Field(default="", max_length=2000)
    struggles: str = Field(default="", max_length=4000)
    faith_journey: str = Field(default="", max_length=4000)
    use_ai: bool = True
    theological_boundary_ack: bool = False
    title: str = Field(default="", max_length=200)

    def inputs(self) -> Dict[str, str]:
        return {k: getattr(self, k) for k in engine.INPUT_KEYS}


class FeedbackBody(BaseModel):
    assessment_id: Optional[int] = None
    source_type: str = Field(default="other", max_length=30)
    source_alias: str = Field(default="", max_length=120)
    is_anonymous: bool = True
    relationship_description: str = Field(default="", max_length=1000)
    scores: Dict[str, int] = Field(default_factory=dict)          # {clarity,edification,...} 1~5
    confirmed_strengths: List[str] = Field(default_factory=list)
    confirmed_gifts: List[str] = Field(default_factory=list)
    concern_areas: List[str] = Field(default_factory=list)
    free_text_feedback: str = Field(default="", max_length=4000)
    suggested_ministry_roles: List[str] = Field(default_factory=list)
    maturity_observations: str = Field(default="", max_length=2000)
    risk_observations: str = Field(default="", max_length=2000)
    consent_given: bool = False


class ReviewBody(BaseModel):
    assessment_id: Optional[int] = None
    growth_plan_id: Optional[int] = None
    review_type: str = Field(default="self_review", max_length=30)
    reviewer_role: str = Field(default="self", max_length=30)
    reviewer_alias: str = Field(default="", max_length=120)
    scores: Dict[str, int] = Field(default_factory=dict)
    completed_actions: List[Any] = Field(default_factory=list)
    unfinished_actions: List[Any] = Field(default_factory=list)
    observations: str = Field(default="", max_length=6000)
    gratitude_notes: str = Field(default="", max_length=3000)
    repentance_notes: str = Field(default="", max_length=3000)
    prayer_notes: str = Field(default="", max_length=3000)
    action_items: List[Any] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 落库辅助：把引擎报告写入 8 张子表
# ─────────────────────────────────────────────────────────────────────────────

def _persist_report(cur, email: str, body: AssessBody, report: Dict[str, Any]) -> int:
    conf = _norm_conf(report.get("confidence"))
    sp = report["strength_profile"]
    sg = report["spiritual_gifts"]
    fr = report["fruit_scores"]
    cp = report["calling_patterns"]
    mr = report["misuse_risks"]
    mm = report["ministry_matches"]
    gp = report["growth_plan"]

    # 1) 主记录。spiritual_gifts 与 community_confirmation 入 agent_outputs（沿用设计）。
    agent_outputs = {
        "spiritual_gifts": sg,
        "community_confirmation": report.get("community_confirmation", {}),
        "source": report.get("source", "heuristic"),
        "identity_reminder": report.get("identity_reminder", ""),
    }
    input_sources = [{"type": "self_questionnaire"}]
    if report.get("source") == "ai":
        input_sources.append({"type": "ai_analysis"})
    cur.execute(
        """
        INSERT INTO gift_assessments
            (email, assessment_type, status, version, title, summary,
             questionnaire_responses, input_sources, agent_outputs, confidence,
             theological_boundary_ack, completed_at)
        VALUES (%s,%s,'completed',%s,%s,%s,%s,%s,%s,%s,%s, NOW())
        RETURNING id
        """,
        (email, "ai_generated" if report.get("source") == "ai" else "initial",
         "gcos1.0", (body.title or "恩赐与呼召分析"), report.get("summary", ""),
         _Json(body.inputs()), _Json(input_sources), _Json(agent_outputs), conf,
         bool(body.theological_boundary_ack)),
    )
    aid = cur.fetchone()[0]

    # 2) 天然优势
    ss = sp["scores"]
    cur.execute(
        """
        INSERT INTO strength_profiles
            (assessment_id, email, cognitive_score, expression_score, relational_score,
             execution_score, creativity_score, leadership_score, discernment_score,
             learning_score, technical_score, resilience_score,
             core_strengths, secondary_strengths, underdeveloped_areas, skill_assets,
             personality_tendencies, summary, confidence)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (aid, email, ss.get("cognitive"), ss.get("expression"), ss.get("relational"),
         ss.get("execution"), ss.get("creativity"), ss.get("leadership"),
         ss.get("discernment"), ss.get("learning"), ss.get("technical"), ss.get("resilience"),
         _Json(sp.get("core_strengths", [])), _Json(sp.get("secondary_strengths", [])),
         _Json(sp.get("underdeveloped_areas", [])), _Json(sp.get("skill_assets", [])),
         _Json(sp.get("personality_tendencies", [])), sp.get("summary", ""), conf),
    )

    # 3) 圣灵果子
    fs = fr["scores"]
    cur.execute(
        """
        INSERT INTO fruit_scores
            (assessment_id, email, love_score, joy_score, peace_score, patience_score,
             kindness_score, goodness_score, faithfulness_score, gentleness_score,
             self_control_score, average_score, supporting_fruits, growth_fruits,
             gift_fruit_alignment, red_flags, summary, confidence)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (aid, email, fs.get("love"), fs.get("joy"), fs.get("peace"), fs.get("patience"),
         fs.get("kindness"), fs.get("goodness"), fs.get("faithfulness"), fs.get("gentleness"),
         fs.get("self_control"), fr.get("average_score", 0),
         _Json(fr.get("supporting_fruits", [])), _Json(fr.get("growth_fruits", [])),
         _Json(fr.get("gift_fruit_alignment", [])), _Json(fr.get("red_flags", [])),
         fr.get("summary", ""), conf),
    )

    # 4) 使命负担
    cur.execute(
        """
        INSERT INTO calling_patterns
            (assessment_id, email, primary_pattern, secondary_patterns, pattern_scores,
             evidence, burden_groups, burden_topics, crossroads, possible_mission_sentence,
             validation_path, warnings, summary, confidence)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (aid, email, cp.get("primary_pattern", ""), _Json(cp.get("secondary_patterns", [])),
         _Json(cp.get("scores", {})), _Json(cp.get("evidence", [])),
         _Json(cp.get("burden_groups", [])), _Json(cp.get("burden_topics", [])),
         _Json(cp.get("crossroads", {})), cp.get("possible_mission_sentence", ""),
         _Json(cp.get("validation_path", [])), _Json(cp.get("warnings", [])),
         cp.get("summary", ""), conf),
    )

    # 5) 误用风险
    cur.execute(
        """
        INSERT INTO misuse_risks
            (assessment_id, email, overall_risk_score, top_risks, risk_profile,
             protective_disciplines, community_safeguards, gospel_reframes,
             warning_signs, summary, confidence)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (aid, email, mr.get("overall_risk_score"), _Json(mr.get("top_risks", [])),
         _Json(mr.get("risk_profile", {})), _Json(mr.get("protective_disciplines", [])),
         _Json(mr.get("community_safeguards", [])), _Json(mr.get("gospel_reframes", [])),
         _Json(mr.get("warning_signs", [])), mr.get("summary", ""), conf),
    )

    # 6) 服事匹配
    cur.execute(
        """
        INSERT INTO ministry_matches
            (assessment_id, email, top_ministry, top_match_score, recommended_ministries,
             experimental_ministries, not_recommended_now, safeguards, summary, confidence)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (aid, email, mm.get("top_ministry", ""), mm.get("top_match_score"),
         _Json(mm.get("recommended_ministries", [])), _Json(mm.get("experimental_ministries", [])),
         _Json(mm.get("not_recommended_now", [])), _Json(mm.get("safeguards", [])),
         mm.get("summary", ""), conf),
    )

    # 7) 成长计划
    cur.execute(
        """
        INSERT INTO growth_plans
            (assessment_id, email, status, plan_json, weekly_rhythm, success_indicators,
             warning_signs, current_phase, summary)
        VALUES (%s,%s,'not_started',%s,%s,%s,%s,%s,%s)
        """,
        (aid, email, _Json(gp.get("plan_json", {})), _Json(gp.get("weekly_rhythm", [])),
         _Json(gp.get("success_indicators", [])), _Json(gp.get("warning_signs", [])),
         gp.get("current_phase", "30_days"), gp.get("summary", "")),
    )
    return aid


# ─────────────────────────────────────────────────────────────────────────────
# 读取辅助：从子表聚合回引擎报告形状（/profile 与 /assessment/{id} 共用）
# ─────────────────────────────────────────────────────────────────────────────

def _assemble(cur, aid: int, to_iso) -> Dict[str, Any]:
    cur.execute(
        "SELECT id, email, assessment_type, status, title, summary, agent_outputs, "
        "confidence, theological_boundary_ack, completed_at, created_at "
        "FROM gift_assessments WHERE id=%s", (aid,))
    a = cur.fetchone()
    if not a:
        return {}
    agent_outputs = a[6] if isinstance(a[6], dict) else {}
    report: Dict[str, Any] = {
        "assessment_id": a[0], "email": a[1], "assessment_type": a[2],
        "status": a[3], "title": a[4], "summary": a[5],
        "confidence": a[7], "theological_boundary_ack": a[8],
        "completed_at": to_iso(a[9]) if a[9] else None,
        "created_at": to_iso(a[10]) if a[10] else None,
        "source": agent_outputs.get("source", "heuristic"),
        "spiritual_gifts": agent_outputs.get("spiritual_gifts", {}),
        "community_confirmation": agent_outputs.get("community_confirmation", {}),
        "identity_reminder": agent_outputs.get("identity_reminder", engine.IDENTITY_REMINDER),
        "boundary_notice": engine.BOUNDARY_NOTICE,
    }

    cur.execute(
        "SELECT cognitive_score, expression_score, relational_score, execution_score, "
        "creativity_score, leadership_score, discernment_score, learning_score, "
        "technical_score, resilience_score, core_strengths, secondary_strengths, "
        "underdeveloped_areas, skill_assets, personality_tendencies, summary "
        "FROM strength_profiles WHERE assessment_id=%s", (aid,))
    r = cur.fetchone()
    if r:
        report["strength_profile"] = {
            "scores": dict(zip(engine.STRENGTH_KEYS, [x for x in r[:10]])),
            "core_strengths": r[10] or [], "secondary_strengths": r[11] or [],
            "underdeveloped_areas": r[12] or [], "skill_assets": r[13] or [],
            "personality_tendencies": r[14] or [], "summary": r[15] or "",
        }

    cur.execute(
        "SELECT love_score, joy_score, peace_score, patience_score, kindness_score, "
        "goodness_score, faithfulness_score, gentleness_score, self_control_score, "
        "average_score, supporting_fruits, growth_fruits, gift_fruit_alignment, "
        "red_flags, summary FROM fruit_scores WHERE assessment_id=%s", (aid,))
    r = cur.fetchone()
    if r:
        report["fruit_scores"] = {
            "scores": dict(zip(engine.FRUIT_KEYS, [x for x in r[:9]])),
            "average_score": float(r[9]) if r[9] is not None else 0.0,
            "supporting_fruits": r[10] or [], "growth_fruits": r[11] or [],
            "gift_fruit_alignment": r[12] or [], "red_flags": r[13] or [], "summary": r[14] or "",
        }

    cur.execute(
        "SELECT primary_pattern, secondary_patterns, pattern_scores, evidence, "
        "burden_groups, burden_topics, crossroads, possible_mission_sentence, "
        "validation_path, warnings, summary FROM calling_patterns WHERE assessment_id=%s", (aid,))
    r = cur.fetchone()
    if r:
        report["calling_patterns"] = {
            "primary_pattern": r[0] or "", "secondary_patterns": r[1] or [],
            "scores": r[2] or {}, "evidence": r[3] or [], "burden_groups": r[4] or [],
            "burden_topics": r[5] or [], "crossroads": r[6] or {},
            "possible_mission_sentence": r[7] or "", "validation_path": r[8] or [],
            "warnings": r[9] or [], "summary": r[10] or "",
        }

    cur.execute(
        "SELECT overall_risk_score, top_risks, risk_profile, protective_disciplines, "
        "community_safeguards, gospel_reframes, warning_signs, summary "
        "FROM misuse_risks WHERE assessment_id=%s", (aid,))
    r = cur.fetchone()
    if r:
        report["misuse_risks"] = {
            "overall_risk_score": r[0], "top_risks": r[1] or [], "risk_profile": r[2] or {},
            "protective_disciplines": r[3] or [], "community_safeguards": r[4] or [],
            "gospel_reframes": r[5] or [], "warning_signs": r[6] or [], "summary": r[7] or "",
        }

    cur.execute(
        "SELECT top_ministry, top_match_score, recommended_ministries, "
        "experimental_ministries, not_recommended_now, safeguards, summary "
        "FROM ministry_matches WHERE assessment_id=%s", (aid,))
    r = cur.fetchone()
    if r:
        report["ministry_matches"] = {
            "top_ministry": r[0] or "", "top_match_score": r[1],
            "recommended_ministries": r[2] or [], "experimental_ministries": r[3] or [],
            "not_recommended_now": r[4] or [], "safeguards": r[5] or [], "summary": r[6] or "",
        }

    cur.execute(
        "SELECT id, status, plan_json, weekly_rhythm, success_indicators, warning_signs, "
        "current_phase, summary FROM growth_plans WHERE assessment_id=%s", (aid,))
    r = cur.fetchone()
    if r:
        report["growth_plan"] = {
            "growth_plan_id": r[0], "status": r[1], "plan_json": r[2] or {},
            "weekly_rhythm": r[3] or [], "success_indicators": r[4] or [],
            "warning_signs": r[5] or [], "current_phase": r[6] or "30_days", "summary": r[7] or "",
        }
    return report


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/meta")
def get_meta() -> dict:
    return {"ok": True, **engine.meta()}


@router.get("/profile")
def get_profile(request: Request) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM gift_assessments WHERE email=%s AND status='completed' "
                "ORDER BY completed_at DESC NULLS LAST, id DESC LIMIT 1", (user["email"],))
            row = cur.fetchone()
            if not row:
                return {"ok": True, "profile": {**engine.empty_profile(), "has_assessment": False}}
            report = _assemble(cur, row[0], to_iso)
    finally:
        _state["release_db"](conn)
    report["has_assessment"] = True
    return {"ok": True, "profile": report}


@router.post("/assess")
def post_assess(request: Request, body: AssessBody) -> dict:
    user = _require_user(request)
    email = user["email"]
    report = engine.assess(body.inputs(), settings=_settings, use_ai=body.use_ai)

    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            aid = _persist_report(cur, email, body, report)
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"assess failed: {exc}")
    finally:
        _state["release_db"](conn)

    report["assessment_id"] = aid
    try:
        import formation_events as _fe
        _fe.record_event(email, "gift", "gift", domain=(report.get("primary_gift") or None),
                         title=(report.get("title") or "恩赐测评"), summary=(report.get("summary") or ""),
                         severity="green", ref_id=str(aid))
    except Exception:
        pass
    return {"ok": True, **report}


@router.get("/history")
def get_history(request: Request, limit: int = Query(20, ge=1, le=100)) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, assessment_type, status, title, summary, confidence, "
                "completed_at, created_at FROM gift_assessments "
                "WHERE email=%s ORDER BY created_at DESC LIMIT %s", (user["email"], limit))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = [{
        "id": r[0], "assessment_type": r[1], "status": r[2], "title": r[3],
        "summary": r[4], "confidence": r[5],
        "completed_at": to_iso(r[6]) if r[6] else None,
        "created_at": to_iso(r[7]) if r[7] else None,
    } for r in rows]
    return {"ok": True, "count": len(items), "items": items}


@router.get("/assessment/{aid}")
def get_assessment(request: Request, aid: int) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT email FROM gift_assessments WHERE id=%s", (aid,))
            owner = cur.fetchone()
            if not owner:
                raise HTTPException(status_code=404, detail="assessment not found")
            if owner[0] != user["email"]:
                raise HTTPException(status_code=403, detail="forbidden")
            report = _assemble(cur, aid, to_iso)
    finally:
        _state["release_db"](conn)
    return {"ok": True, "report": report}


@router.post("/feedback")
def post_feedback(request: Request, body: FeedbackBody) -> dict:
    """提交共同体反馈。被反馈者 = 当前登录用户（MVP：自邀请收集）。"""
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO community_feedback
                    (email, assessment_id, source_type, source_alias, is_anonymous,
                     relationship_description, scores, confirmed_strengths, confirmed_gifts,
                     concern_areas, free_text_feedback, suggested_ministry_roles,
                     maturity_observations, risk_observations, consent_given)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (user["email"], body.assessment_id, body.source_type, body.source_alias,
                 body.is_anonymous, body.relationship_description, _Json(body.scores),
                 _Json(body.confirmed_strengths), _Json(body.confirmed_gifts),
                 _Json(body.concern_areas), body.free_text_feedback,
                 _Json(body.suggested_ministry_roles), body.maturity_observations,
                 body.risk_observations, body.consent_given),
            )
            fid = cur.fetchone()[0]
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"feedback failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": fid}


@router.get("/feedback")
def get_feedback(request: Request) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT source_type, source_alias, is_anonymous, scores, confirmed_strengths, "
                "confirmed_gifts, concern_areas, free_text_feedback, suggested_ministry_roles, "
                "submitted_at FROM community_feedback WHERE email=%s "
                "ORDER BY submitted_at DESC", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = [{
        "source_type": r[0], "source_alias": (r[1] if not r[2] else "匿名"),
        "scores": r[3] or {}, "confirmed_strengths": r[4] or [], "confirmed_gifts": r[5] or [],
        "concern_areas": r[6] or [], "free_text_feedback": r[7] or "",
        "suggested_ministry_roles": r[8] or [],
        "submitted_at": to_iso(r[9]) if r[9] else None,
    } for r in rows]
    # 加权聚合（复用引擎）
    agg = engine.summarize_community_feedback([
        {"source_type": it["source_type"], "scores": it["scores"],
         "confirmed_gifts": it["confirmed_gifts"], "confirmed_strengths": it["confirmed_strengths"],
         "concern_areas": it["concern_areas"]} for it in items])
    return {"ok": True, "count": len(items), "items": items, "aggregate": agg}


@router.post("/review")
def post_review(request: Request, body: ReviewBody) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO review_logs
                    (email, assessment_id, growth_plan_id, review_type, reviewer_role,
                     reviewer_alias, scores, completed_actions, unfinished_actions,
                     observations, gratitude_notes, repentance_notes, prayer_notes, action_items)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (user["email"], body.assessment_id, body.growth_plan_id, body.review_type,
                 body.reviewer_role, body.reviewer_alias, _Json(body.scores),
                 _Json(body.completed_actions), _Json(body.unfinished_actions),
                 body.observations, body.gratitude_notes, body.repentance_notes,
                 body.prayer_notes, _Json(body.action_items)),
            )
            rid = cur.fetchone()[0]
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"review failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": rid}


@router.get("/review")
def get_reviews(request: Request, limit: int = Query(20, ge=1, le=100)) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, assessment_id, review_type, reviewer_role, scores, observations, "
                "gratitude_notes, action_items, created_at FROM review_logs "
                "WHERE email=%s ORDER BY created_at DESC LIMIT %s", (user["email"], limit))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = [{
        "id": r[0], "assessment_id": r[1], "review_type": r[2], "reviewer_role": r[3],
        "scores": r[4] or {}, "observations": r[5] or "", "gratitude_notes": r[6] or "",
        "action_items": r[7] or [], "created_at": to_iso(r[8]) if r[8] else None,
    } for r in rows]
    return {"ok": True, "count": len(items), "items": items}
