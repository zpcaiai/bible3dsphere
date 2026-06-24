"""
Worldview router — Worldview Formation OS / 世界观塑造系统 (Kingdom Lens OS)

Endpoints (prefix /api/worldview):
  GET  /meta                 静态配置：12 领域 + agent 序列 + 危机等级映射
  POST /diagnose             危机优先守卫 → 世界观诊断闭环；落库并返回分析
  GET  /profile              当前世界观画像 (worldview_profiles)
  GET  /assessments          历史诊断记录
  GET  /metrics              长期雷达图快照 (worldview_metric_snapshots)

安全第一：/diagnose 永远先过 crisis_guard()，高危直接转向危机/苦难安全路由，
不输出复杂世界观分析。键以 email 为准，与本仓库其余表 (attachment_*, gift_*, agent_runs) 一致。
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:  # 兼容 backend.* 与顶层两种导入路径
    from backend import worldview_orchestrator as orch
except Exception:  # pragma: no cover
    import worldview_orchestrator as orch  # type: ignore

try:
    from backend import worldview_diagnoser_engine as diagnoser
except Exception:  # pragma: no cover
    try:
        import worldview_diagnoser_engine as diagnoser  # type: ignore
    except Exception:  # 引擎尚未就绪时优雅降级
        diagnoser = None  # type: ignore

try:
    from backend import truth_mapper_engine as truth_mapper
except Exception:  # pragma: no cover
    try:
        import truth_mapper_engine as truth_mapper  # type: ignore
    except Exception:
        truth_mapper = None  # type: ignore

try:
    from backend import narrative_engine as narrative
except Exception:  # pragma: no cover
    try:
        import narrative_engine as narrative  # type: ignore
    except Exception:
        narrative = None  # type: ignore

try:
    from backend import decision_formation_engine as decision
except Exception:  # pragma: no cover
    try:
        import decision_formation_engine as decision  # type: ignore
    except Exception:
        decision = None  # type: ignore

try:
    from backend import formation_practice_engine as practice
except Exception:  # pragma: no cover
    try:
        import formation_practice_engine as practice  # type: ignore
    except Exception:
        practice = None  # type: ignore

try:
    from backend import worldview_llm as _llm
except Exception:  # pragma: no cover
    try:
        import worldview_llm as _llm  # type: ignore
    except Exception:
        _llm = None  # type: ignore


def _ai_default(v):
    """use_ai 未显式指定时，按 LLM 是否可用决定（有 key 则默认开启增强）。"""
    if v is not None:
        return bool(v)
    try:
        return bool(_llm and _llm.available())
    except Exception:
        return False

router = APIRouter(prefix="/api/worldview", tags=["worldview"])

_state: Dict[str, Any] = {}


def init_worldview_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
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


# ── Request models ──────────────────────────────────────────────────────────
class DiagnoseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    source_type: str = Field(default="journal", max_length=40)
    locale: str = Field(default="zh-CN", max_length=16)
    persist: bool = True
    use_ai: Optional[bool] = None  # None=按 LLM 可用性自动决定


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("/meta")
def get_meta() -> dict:
    out = {"ok": True, **orch.meta()}
    if diagnoser is not None and hasattr(diagnoser, "meta"):
        try:
            out["diagnoser"] = diagnoser.meta()
        except Exception:
            pass
    try:
        out["ai"] = _llm.meta() if _llm else {"available": False}
    except Exception:
        out["ai"] = {"available": False}
    return out


@router.post("/diagnose")
def post_diagnose(request: Request, body: DiagnoseRequest) -> dict:
    user = _require_user(request)
    email = user["email"]

    result = orch.run_pipeline(
        user_id=email,
        text=body.text,
        source_type=body.source_type,
        locale=body.locale,
        use_ai=_ai_default(body.use_ai),
    )

    # 高危：不落世界观分析，仅返回危机路由建议（安全优先）
    if result.get("blocked"):
        _audit(email, "worldview_diagnoser", {"source_type": body.source_type},
               {"blocked": True, "crisis": result.get("crisis")}, risk="red")
        return {"ok": True, "blocked": True, **result}

    if body.persist:
        try:
            _persist_diagnosis(email, body, result)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"save failed: {exc}")

    _audit(email, "worldview_diagnoser", {"source_type": body.source_type},
           {"blocked": False, "domains": (result.get("diagnosis") or {}).get("detectedDomains", [])})
    _emit_events(email, "worldview_diagnoser", result.get("recommendedNextAgents", []),
                 {"source_type": body.source_type})
    try:
        import diagnosis_hub
        diagnosis_hub.record_from_worldview(email, None, result)
    except Exception:
        pass
    return {"ok": True, "blocked": False, **result}


def _persist_diagnosis(email: str, body: DiagnoseRequest, result: Dict[str, Any]) -> None:
    diag = result.get("diagnosis") or {}
    assessment_id = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            # 原始回应留底
            cur.execute(
                "INSERT INTO worldview_responses "
                "(id, email, source_type, raw_response, detected_idols) "
                "VALUES (%s,%s,%s,%s,%s)",
                (uuid.uuid4().hex, email, body.source_type, body.text[:8000],
                 _Json((result.get("idols") or {}).get("suggestedTargets", []))),
            )
            # 诊断记录
            cur.execute(
                "INSERT INTO worldview_assessments "
                "(id, email, assessment_type, source_type, raw_input_summary, "
                " detected_domains, detected_idols, agent_outputs, overall_score, "
                " confidence, risk_level) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (assessment_id, email, "auto", body.source_type, body.text[:500],
                 _Json(diag.get("detectedDomains", [])),
                 _Json((result.get("idols") or {}).get("suggestedTargets", [])),
                 _Json(result), diag.get("overallScore"),
                 diag.get("confidence"),
                 (result.get("crisis") or {}).get("riskLevelRaw", "green")),
            )
            # 维度分数
            for ds in diag.get("dimensionScores", []):
                cur.execute(
                    "INSERT INTO worldview_dimension_scores "
                    "(id, email, assessment_id, domain, score, confidence, "
                    " evidence, growth_recommendation) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (uuid.uuid4().hex, email, assessment_id, ds.get("domain"),
                     ds.get("score"), ds.get("confidence"),
                     _Json(ds.get("evidence", [])), ds.get("explanation", "")),
                )
            # 底层信念
            for b in diag.get("extractedBeliefs", []):
                cur.execute(
                    "INSERT INTO worldview_beliefs "
                    "(id, email, assessment_id, domain, belief_statement, belief_status, "
                    " confidence, source_text_excerpt, emotional_fruit, behavioral_fruit, "
                    " biblical_evaluation, related_scripture_refs) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (uuid.uuid4().hex, email, assessment_id, b.get("domain"),
                     b.get("beliefStatement", "")[:1000], b.get("status", "detected"),
                     b.get("confidence"), b.get("evidence", "")[:1000],
                     _Json(b.get("emotionalFruit", [])), _Json(b.get("behavioralFruit", [])),
                     b.get("biblicalCounterTruth"), _Json(b.get("scriptureAnchors", []))),
                )
            # 画像 upsert
            cur.execute(
                "INSERT INTO worldview_profiles "
                "(email, summary, dominant_idols, biblical_alignment_score, "
                " strongest_domains, weakest_domains, current_growth_focus, "
                " risk_level, last_assessed_at, updated_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s, now(), now()) "
                "ON CONFLICT (email) DO UPDATE SET "
                "  summary=EXCLUDED.summary, dominant_idols=EXCLUDED.dominant_idols, "
                "  biblical_alignment_score=EXCLUDED.biblical_alignment_score, "
                "  strongest_domains=EXCLUDED.strongest_domains, "
                "  weakest_domains=EXCLUDED.weakest_domains, "
                "  current_growth_focus=EXCLUDED.current_growth_focus, "
                "  risk_level=EXCLUDED.risk_level, last_assessed_at=now(), updated_at=now()",
                (email, diag.get("profileSummary", ""),
                 _Json((result.get("idols") or {}).get("suggestedTargets", [])),
                 diag.get("overallScore"),
                 _Json(diag.get("strongestDomains", [])),
                 _Json(diag.get("weakestDomains", [])),
                 diag.get("currentGrowthFocus"),
                 (result.get("crisis") or {}).get("riskLevelRaw", "green")),
            )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        _state["release_db"](conn)


@router.get("/profile")
def get_profile(request: Request) -> dict:
    user = _require_user(request)
    email = user["email"]
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT summary, dominant_idols, biblical_alignment_score, maturity_level, "
                " strongest_domains, weakest_domains, current_growth_focus, risk_level, "
                " last_assessed_at FROM worldview_profiles WHERE email=%s",
                (email,),
            )
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not row:
        return {"ok": True, "has_data": False}
    return {
        "ok": True, "has_data": True,
        "summary": row[0], "dominant_idols": row[1],
        "biblical_alignment_score": float(row[2]) if row[2] is not None else None,
        "maturity_level": row[3],
        "strongest_domains": row[4], "weakest_domains": row[5],
        "current_growth_focus": row[6], "risk_level": row[7],
        "last_assessed_at": to_iso(row[8]) if row[8] else None,
    }


@router.get("/assessments")
def get_assessments(request: Request, limit: int = Query(default=20, ge=1, le=100)) -> dict:
    user = _require_user(request)
    email = user["email"]
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, source_type, raw_input_summary, detected_domains, "
                " overall_score, risk_level, created_at FROM worldview_assessments "
                "WHERE email=%s ORDER BY created_at DESC LIMIT %s",
                (email, limit),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "count": len(rows), "assessments": [
        {"id": r[0], "source_type": r[1], "summary": r[2], "domains": r[3],
         "overall_score": float(r[4]) if r[4] is not None else None,
         "risk_level": r[5], "created_at": to_iso(r[6])}
        for r in rows
    ]}


@router.get("/metrics")
def get_metrics(request: Request, limit: int = Query(default=30, ge=1, le=180)) -> dict:
    user = _require_user(request)
    email = user["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT snapshot_date, scores, dominant_idols, active_growth_focus "
                "FROM worldview_metric_snapshots WHERE email=%s "
                "ORDER BY snapshot_date DESC LIMIT %s",
                (email, limit),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "count": len(rows), "snapshots": [
        {"date": str(r[0]), "scores": r[1], "dominant_idols": r[2], "growth_focus": r[3]}
        for r in rows
    ]}


# ── Truth Mapper / Narrative Rewriter ────────────────────────────────────────
class TruthMapRequest(BaseModel):
    beliefs: List[Dict[str, Any]] = Field(default_factory=list)
    domain: Optional[str] = None
    idol_category: Optional[str] = None
    lie: Optional[str] = None
    persist: bool = True
    use_ai: Optional[bool] = None


class NarrativeRequest(BaseModel):
    text: str = Field(default="", max_length=4000)
    idol_category: Optional[str] = None
    domain: Optional[str] = None
    persist: bool = True
    use_ai: Optional[bool] = None


@router.post("/truth/map")
def post_truth_map(request: Request, body: TruthMapRequest) -> dict:
    if truth_mapper is None:
        raise HTTPException(status_code=503, detail="truth_mapper_engine unavailable")
    user = _require_user(request)
    email = user["email"]

    ai = _ai_default(body.use_ai)
    if body.beliefs:
        result = truth_mapper.map_beliefs(body.beliefs, use_ai=ai)
    else:
        result = {
            "mappings": [truth_mapper.map_one(domain=body.domain,
                                              idol_category=body.idol_category,
                                              lie=body.lie or "", use_ai=ai)],
            "summary": "", "recommendedNextAgents": ["narrative_rewriter", "formation_practice"],
        }
    _enrich_bible_persons(result)

    if body.persist and body.beliefs:
        try:
            _persist_distortions(email, body.beliefs, result["mappings"])
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"save failed: {exc}")

    _audit(email, "biblical_truth_mapper", {"count": len(result["mappings"])},
           {"refs": [m.get("scriptureRefs") for m in result["mappings"]]})
    return {"ok": True, **result}


@router.post("/narrative/rewrite")
def post_narrative_rewrite(request: Request, body: NarrativeRequest) -> dict:
    if narrative is None:
        raise HTTPException(status_code=503, detail="narrative_engine unavailable")
    user = _require_user(request)
    email = user["email"]

    result = narrative.rewrite(raw_text=body.text, idol_category=body.idol_category,
                               domain=body.domain, use_ai=_ai_default(body.use_ai))
    if body.persist:
        try:
            _persist_narrative(email, result)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"save failed: {exc}")

    _audit(email, "narrative_rewriter", {"idol": body.idol_category},
           {"hiddenIdol": result.get("hiddenIdol")})
    return {"ok": True, **result}


def _enrich_bible_persons(result: Dict[str, Any]) -> None:
    """按人物中文名查询 biblical_characters，附上 lesson / scripture_ref / summary。"""
    names: List[str] = []
    for m in result.get("mappings", []):
        for n in m.get("recommendedBiblePersons", []):
            if n not in names:
                names.append(n)
    if not names:
        return
    details: Dict[str, Any] = {}
    try:
        conn = _state["get_db"]()
    except Exception:
        return
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name, lesson, scripture_ref, summary FROM biblical_characters "
                "WHERE name = ANY(%s) AND is_active = TRUE",
                (names,),
            )
            for row in cur.fetchall():
                details[row[0]] = {"lesson": row[1], "scripture_ref": row[2], "summary": row[3]}
    except Exception:
        details = {}
    finally:
        try:
            _state["release_db"](conn)
        except Exception:
            pass
    if details:
        result["biblePersonDetails"] = details


def _persist_distortions(email: str, beliefs: List[Dict[str, Any]],
                         mappings: List[Dict[str, Any]]) -> None:
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            for b, m in zip(beliefs, mappings):
                cur.execute(
                    "INSERT INTO distorted_beliefs "
                    "(id, email, domain, distortion_type, lie_statement, idol_category, "
                    " severity, emotional_fruit, behavioral_fruit, biblical_truth_summary, "
                    " repentance_direction, status, gospel_reframe, scripture_refs, "
                    " requires_pastor_attention, possible_root) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (uuid.uuid4().hex, email, b.get("domain", "unknown"),
                     b.get("status", "distorted"),
                     (b.get("beliefStatement") or m.get("lieStatement", ""))[:1000],
                     b.get("idolHint") or b.get("idol_category"),
                     (b.get("severity") or m.get("severity")),
                     _Json(b.get("emotionalFruit", [])),
                     _Json(b.get("behavioralFruit", [])),
                     m.get("biblicalTruth", "")[:2000],
                     (m.get("practiceSuggestions") or [""])[0][:1000],
                     "in_growth",
                     m.get("gospelReframe", "")[:2000],
                     _Json(m.get("scriptureRefs", [])),
                     bool(m.get("requiresPastorAttention")),
                     m.get("possibleRoot")),
                )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        _state["release_db"](conn)


def _persist_narrative(email: str, r: Dict[str, Any]) -> None:
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO narrative_rewrites "
                "(id, email, old_narrative, old_narrative_template, core_fear, hidden_idol, "
                " core_lie, gospel_truth, new_narrative, scripture_refs, "
                " recommended_bible_persons, practice_plan, reflection_questions) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (uuid.uuid4().hex, email, r.get("oldNarrative", "")[:2000],
                 r.get("oldNarrativeTemplate", ""), r.get("coreFear", ""),
                 r.get("hiddenIdol", ""), r.get("coreLie", ""),
                 r.get("gospelTruth", ""), r.get("newNarrative", ""),
                 _Json(r.get("scriptureRefs", [])),
                 _Json(r.get("recommendedBiblePersons", [])),
                 _Json(r.get("practicePlan", [])),
                 _Json(r.get("reflectionQuestions", []))),
            )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        _state["release_db"](conn)


# ── Decision Formation / Formation Practice / Metric Snapshot ────────────────
class DecisionRequest(BaseModel):
    decision_title: str = Field(min_length=1, max_length=300)
    decision_context: str = Field(min_length=1, max_length=4000)
    options: List[Dict[str, str]] = Field(default_factory=list)
    urgency: str = Field(default="medium", max_length=10)
    use_ai: Optional[bool] = None


class PracticePlanRequest(BaseModel):
    focus_idols: List[str] = Field(default_factory=list)
    focus_domains: List[str] = Field(default_factory=list)
    duration_days: int = Field(default=7, ge=1, le=90)
    intensity: str = Field(default="normal", max_length=10)
    safety: Dict[str, bool] = Field(default_factory=dict)


class TaskCompleteRequest(BaseModel):
    user_reflection: str = Field(default="", max_length=4000)
    perceived_helpfulness: Optional[int] = Field(default=None, ge=1, le=10)


@router.post("/decision/discern")
def post_decision(request: Request, body: DecisionRequest) -> dict:
    if decision is None:
        raise HTTPException(status_code=503, detail="decision_formation_engine unavailable")
    user = _require_user(request)
    email = user["email"]
    result = decision.analyze(body.decision_title, body.decision_context,
                              options=body.options, urgency=body.urgency,
                              use_ai=_ai_default(body.use_ai))
    _save_one(
        "INSERT INTO decision_cases (id, email, decision_title, decision_context, options, "
        " detected_motives, detected_fears, detected_idols, biblical_values, wisdom_questions, "
        " red_flags, counsel_needed, recommended_people_to_consult, discernment_summary, "
        " next_faithful_step) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (uuid.uuid4().hex, email, body.decision_title[:300], body.decision_context[:4000],
         _Json(body.options), _Json(result["detectedMotives"]), _Json(result["detectedFears"]),
         _Json(result["detectedIdols"]), _Json(result["biblicalValues"]),
         _Json(result["wisdomQuestions"]), _Json(result["redFlags"]),
         bool(result["counselNeeded"]), _Json(result["recommendedPeopleToConsult"]),
         result["discernmentSummary"], result["nextFaithfulStep"]),
    )
    _audit(email, "decision_formation", {"title": body.decision_title},
           {"counselNeeded": result["counselNeeded"]})
    return {"ok": True, **result}


@router.post("/practice/plan")
def post_practice_plan(request: Request, body: PracticePlanRequest) -> dict:
    if practice is None:
        raise HTTPException(status_code=503, detail="formation_practice_engine unavailable")
    user = _require_user(request)
    email = user["email"]
    plan = practice.generate_plan(focus_idols=body.focus_idols, focus_domains=body.focus_domains,
                                  duration_days=body.duration_days, intensity=body.intensity,
                                  safety=body.safety)
    plan_id = uuid.uuid4().hex
    try:
        _persist_plan(email, plan_id, body, plan)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"save failed: {exc}")
    _audit(email, "formation_practice", {"idols": body.focus_idols, "days": body.duration_days},
           {"taskCount": len(plan.get("tasks", []))})
    return {"ok": True, "plan_id": plan_id, **plan}


@router.post("/practice/tasks/{task_id}/complete")
def post_task_complete(request: Request, task_id: str, body: TaskCompleteRequest) -> dict:
    user = _require_user(request)
    email = user["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO formation_task_logs (id, email, task_id, completed, "
                " user_reflection, perceived_helpfulness) VALUES (%s,%s,%s,%s,%s,%s)",
                (uuid.uuid4().hex, email, task_id, True,
                 body.user_reflection[:4000], body.perceived_helpfulness),
            )
            cur.execute(
                "UPDATE formation_tasks SET status='completed', updated_at=now() "
                "WHERE id=%s AND email=%s",
                (task_id, email),
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
    return {"ok": True, "task_id": task_id, "completed": True}


@router.post("/metrics/snapshot")
def post_metric_snapshot(request: Request) -> dict:
    """从最近的维度分数生成一张雷达图快照（每日唯一）。"""
    user = _require_user(request)
    email = user["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT ON (domain) domain, score FROM worldview_dimension_scores "
                "WHERE email=%s ORDER BY domain, created_at DESC",
                (email,),
            )
            scores = {row[0]: float(row[1]) if row[1] is not None else None
                      for row in cur.fetchall()}
            cur.execute("SELECT dominant_idols, current_growth_focus FROM worldview_profiles "
                        "WHERE email=%s", (email,))
            prow = cur.fetchone()
            idols = prow[0] if prow else []
            focus = [prow[1]] if prow and prow[1] else []
            cur.execute(
                "INSERT INTO worldview_metric_snapshots (id, email, snapshot_date, scores, "
                " dominant_idols, active_growth_focus) VALUES (%s,%s,CURRENT_DATE,%s,%s,%s) "
                "ON CONFLICT (email, snapshot_date) DO UPDATE SET "
                "  scores=EXCLUDED.scores, dominant_idols=EXCLUDED.dominant_idols, "
                "  active_growth_focus=EXCLUDED.active_growth_focus",
                (uuid.uuid4().hex, email, _Json(scores), _Json(idols), _Json(focus)),
            )
        conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"snapshot failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "scores": scores}


def _persist_plan(email: str, plan_id: str, body: "PracticePlanRequest", plan: Dict[str, Any]) -> None:
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO formation_plans (id, email, title, description, duration_days, "
                " intensity, focus_domains, focus_idols, review_questions, success_markers, "
                " warning_signs, status) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (plan_id, email, plan.get("planTitle", "")[:300], plan.get("focusSummary", ""),
                 plan.get("durationDays", body.duration_days), plan.get("intensity", body.intensity),
                 _Json(body.focus_domains), _Json(body.focus_idols),
                 _Json(plan.get("reviewQuestions", [])), _Json(plan.get("successMarkers", [])),
                 _Json(plan.get("warningSigns", [])), "active"),
            )
            for t in plan.get("tasks", []):
                cur.execute(
                    "INSERT INTO formation_tasks (id, email, plan_id, practice_key, day_index, "
                    " title, instructions, expected_minutes, scripture_refs, reflection_prompt, status) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (uuid.uuid4().hex, email, plan_id, t.get("practiceKey"), t.get("day"),
                     t.get("title", "")[:200], t.get("instructions", ""),
                     t.get("expectedMinutes"), _Json(t.get("scriptureRefs", [])),
                     t.get("reflectionPrompt", ""), "pending"),
                )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        _state["release_db"](conn)


def _save_one(sql: str, params: tuple) -> None:
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        _state["release_db"](conn)


# ── 群体协作：守护人 + Agent 事件 ────────────────────────────────────────────
class GuardianRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    role: str = Field(default="friend", max_length=40)
    contact_email: str = Field(default="", max_length=200)
    contact_phone: str = Field(default="", max_length=40)
    can_receive_crisis_alert: bool = False
    can_receive_growth_summary: bool = False
    priority_order: int = Field(default=1, ge=1, le=20)


@router.post("/guardians")
def post_guardian(request: Request, body: GuardianRequest) -> dict:
    user = _require_user(request)
    email = user["email"]
    gid = uuid.uuid4().hex
    _save_one(
        "INSERT INTO community_guardians (id, email, display_name, role, contact_email, "
        " contact_phone, can_receive_crisis_alert, can_receive_growth_summary, priority_order) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (gid, email, body.display_name[:80], body.role, body.contact_email,
         body.contact_phone, body.can_receive_crisis_alert,
         body.can_receive_growth_summary, body.priority_order),
    )
    return {"ok": True, "guardian_id": gid}


@router.get("/guardians")
def get_guardians(request: Request) -> dict:
    user = _require_user(request)
    email = user["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, display_name, role, can_receive_crisis_alert, "
                " can_receive_growth_summary, consent_confirmed, priority_order "
                "FROM community_guardians WHERE email=%s ORDER BY priority_order",
                (email,),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "guardians": [
        {"id": r[0], "display_name": r[1], "role": r[2], "can_receive_crisis_alert": r[3],
         "can_receive_growth_summary": r[4], "consent_confirmed": r[5], "priority_order": r[6]}
        for r in rows
    ]}


def _emit_events(email: str, source_agent: str, target_agents: List[str], payload: dict) -> None:
    """把 recommendedNextAgents 记为 agent_events（best-effort，编排可异步消费）。"""
    if not target_agents:
        return
    try:
        conn = _state["get_db"]()
    except Exception:
        return
    try:
        with conn.cursor() as cur:
            for tgt in target_agents:
                cur.execute(
                    "INSERT INTO agent_events (id, email, event_type, source_agent, target_agent, "
                    " payload, status) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (uuid.uuid4().hex, email, "recommend_next", source_agent, tgt,
                     _Json(payload), "recorded"),
                )
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


# ── 审计：写入既有 agent_runs（best-effort） ──────────────────────────────────
def _audit(email: str, agent: str, inp: dict, outp: dict, risk: str = "green") -> None:
    try:
        conn = _state["get_db"]()
    except Exception:
        return
    try:
        with conn.cursor() as cur:
            # agent_runs.id 是 BIGSERIAL —— 不要显式传 id（让自增）。
            cur.execute(
                "INSERT INTO agent_runs (email, agent_name, event_type, "
                " input_payload, output_payload, status, notified) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (email, agent, "worldview_pipeline",
                 _Json(inp), _Json(outp), "DONE", False),
            )
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
