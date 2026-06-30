"""
Fruit of the Spirit Tracker router — 圣灵果子追踪 (/api/fruit)

  GET  /api/fruit/dimensions        九样果子定义
  POST /api/fruit/assessments       提交一次自评（含各维度分数与证据）
  GET  /api/fruit/assessments       历史评估
  GET  /api/fruit/latest            最近一次评估
  GET  /api/fruit/trends            各维度趋势（最近/上次/变化/均值）
  POST /api/fruit/insights          生成谦卑、非比较的洞见

分数是反思指示，不是属灵排名；鼓励证据式反思，不与他人比较，不追求完美。email 标识用户。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/fruit", tags=["fruit"])

_state: Dict[str, Any] = {}


def init_fruit_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _jl(v):
    if v is None: return []
    if isinstance(v, (list, dict)): return v
    try: return json.loads(v)
    except Exception: return []


@router.get("/dimensions")
def dimensions(request: Request) -> dict:
    _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT dimension_key, display_name, description, scripture_reference, "
                        "related_virtues, opposing_vices, example_evidences, caution_notes "
                        "FROM fruit_dimensions ORDER BY sort_order")
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "dimensions": [
        {"dimension_key": r[0], "display_name": r[1], "description": r[2] or "",
         "scripture_reference": r[3], "related_virtues": _jl(r[4]), "opposing_vices": _jl(r[5]),
         "example_evidences": _jl(r[6]), "caution_notes": r[7] or ""} for r in rows
    ]}


class ScoreIn(BaseModel):
    dimension_key: str = Field(..., max_length=24)
    score: int = Field(..., ge=1, le=10)
    evidence_text: str = Field(default="", max_length=2000)
    growth_example: str = Field(default="", max_length=2000)
    struggle_example: str = Field(default="", max_length=2000)


class AssessmentCreate(BaseModel):
    assessment_type: str = Field(default="self", max_length=16)
    context_label: str = Field(default="overall", max_length=24)
    notes: str = Field(default="", max_length=2000)
    scores: List[ScoreIn] = Field(default_factory=list)


@router.post("/assessments")
def create_assessment(request: Request, body: AssessmentCreate) -> dict:
    user = _require_user(request)
    email = user["email"]
    aid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO fruit_assessments (id, email, assessment_date, assessment_type, context_label, notes) "
                "VALUES (%s,%s,(NOW() AT TIME ZONE 'Asia/Shanghai')::date,%s,%s,%s)",
                (aid, email, body.assessment_type, body.context_label, body.notes),
            )
            for sc in body.scores:
                cur.execute(
                    "INSERT INTO fruit_assessment_scores (id, assessment_id, email, dimension_key, score, evidence_text, growth_example, struggle_example) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (uuid.uuid4().hex, aid, email, sc.dimension_key, sc.score, sc.evidence_text, sc.growth_example, sc.struggle_example),
                )
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    try:
        from formation_bridge import record_formation
        record_formation(user.get("id"), ["growth"], reflection_active=True, decision_category="fruit_assessment")
    except Exception:
        pass
    return {"ok": True, "assessment_id": aid,
            "note": "这些分数只是你与神同行的反思镜子，不是属灵成绩，也不与任何人比较。"}


def _assessment_with_scores(cur, aid, to_iso):
    cur.execute("SELECT id, assessment_date, assessment_type, context_label, notes FROM fruit_assessments WHERE id=%s", (aid,))
    a = cur.fetchone()
    if not a:
        return None
    cur.execute("SELECT dimension_key, score, evidence_text, growth_example, struggle_example FROM fruit_assessment_scores WHERE assessment_id=%s", (aid,))
    scores = [{"dimension_key": s[0], "score": s[1], "evidence_text": s[2] or "",
               "growth_example": s[3] or "", "struggle_example": s[4] or ""} for s in cur.fetchall()]
    return {"id": a[0], "assessment_date": str(a[1]), "assessment_type": a[2],
            "context_label": a[3], "notes": a[4] or "", "scores": scores}


@router.get("/assessments")
def list_assessments(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, assessment_date, assessment_type, context_label FROM fruit_assessments "
                        "WHERE email=%s ORDER BY assessment_date DESC LIMIT 60", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "assessments": [
        {"id": r[0], "assessment_date": str(r[1]), "assessment_type": r[2], "context_label": r[3]} for r in rows
    ]}


@router.get("/latest")
def latest(request: Request) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM fruit_assessments WHERE email=%s ORDER BY assessment_date DESC, created_at DESC LIMIT 1", (user["email"],))
            row = cur.fetchone()
            data = _assessment_with_scores(cur, row[0], to_iso) if row else None
    finally:
        _state["release_db"](conn)
    return {"ok": True, "assessment": data}


@router.get("/trends")
def trends(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT fs.dimension_key, fs.score, fa.assessment_date "
                "FROM fruit_assessment_scores fs JOIN fruit_assessments fa ON fs.assessment_id=fa.id "
                "WHERE fa.email=%s AND fs.score IS NOT NULL ORDER BY fa.assessment_date ASC", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    by: Dict[str, List[int]] = {}
    for dim, score, _ in rows:
        by.setdefault(dim, []).append(score)
    out = {}
    for dim, scores in by.items():
        latest_v = scores[-1]
        prev_v = scores[-2] if len(scores) > 1 else None
        out[dim] = {"latest": latest_v, "previous": prev_v,
                    "delta": (latest_v - prev_v) if prev_v is not None else None,
                    "average": round(sum(scores) / len(scores), 1), "count": len(scores)}
    return {"ok": True, "trends": out,
            "note": "趋势是为了察觉神在你生命中的工作，不是为了评判自己。低分往往是邀请，不是定罪。"}


@router.post("/insights")
def insights(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM fruit_assessments WHERE email=%s ORDER BY assessment_date DESC, created_at DESC LIMIT 1", (user["email"],))
            row = cur.fetchone()
            scores = []
            if row:
                cur.execute("SELECT dimension_key, score FROM fruit_assessment_scores WHERE assessment_id=%s AND score IS NOT NULL", (row[0],))
                scores = cur.fetchall()
    finally:
        _state["release_db"](conn)
    if not scores:
        return {"ok": True, "insights": ["先完成一次果子自评，我再给你一些温柔的观察。"]}
    scores_sorted = sorted(scores, key=lambda x: x[1])
    weakest = scores_sorted[0]
    strongest = scores_sorted[-1]
    name = {"love": "仁爱", "joy": "喜乐", "peace": "和平", "patience": "忍耐", "kindness": "恩慈",
            "goodness": "良善", "faithfulness": "信实", "gentleness": "温柔", "self_control": "节制"}
    ins = [
        f"神似乎正在「{name.get(strongest[0], strongest[0])}」上结果子——为此感恩，这是圣灵的工作，不是你的成就。",
        f"「{name.get(weakest[0], weakest[0])}」此刻较难，这不是你的失败，而是一个邀请：把它带到祷告里，与一两个相关操练同行。",
        "记得：果子是圣灵结的，不是靠你拼出来的。你的角色是常在主里面（约 15:5）。",
    ]
    return {"ok": True, "insights": ins, "cultivate": weakest[0], "thank_god_for": strongest[0]}
