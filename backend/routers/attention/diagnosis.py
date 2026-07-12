"""Attention Stewardship / 守心 API — AI spiritual attention diagnosis agent routes.

Mechanically split from the original single-file routers/attention.py.
Do not change route paths/parameters/logic here without checking the whole package.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import os
import uuid
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ._common import *  # noqa: F401,F403
from ._common import (  # noqa: F401
    _CHECKIN_COLUMNS,
    _DIAGNOSIS_COLUMNS,
    _ENTRY_COLUMNS,
    _FOCUS_COLUMNS,
    _Json,
    _PLAN_COLUMNS,
    _REPORT_COLUMNS,
    _REVIEW_COLUMNS,
    _SCORE_COLUMNS,
    _SELECT_COLUMNS,
    _checkin_row_to_dto,
    _clean_text_list,
    _clip_text,
    _db_user_id,
    _diagnosis_row_to_dto,
    _entry_row_to_dto,
    _fetch_entries_between,
    _focus_row_to_dto,
    _iso,
    _json_error,
    _json_value,
    _load_daily_score_input,
    _load_warfare_data,
    _local_date,
    _local_day_bounds,
    _local_timezone,
    _minutes_between,
    _parse_date,
    _parse_optional_date,
    _plan_row_to_dto,
    _report_row_to_dto,
    _require_attention_admin,
    _require_plan,
    _require_user,
    _review_row_to_dto,
    _row_to_dto,
    _safe_rows,
    _safe_scalar,
    _state,
    _utc_now,
)
from ._models import *  # noqa: F401,F403


# ---------------------------------------------------------------------------
# Batch 3: AI Spiritual Attention Diagnosis Agent (fallback-first)
# ---------------------------------------------------------------------------



def _build_diagnosis_context(cur, user_id: str, request: Request, target: date, diagnosis_type: str = "daily", user_question: Optional[str] = None) -> dict:
    if diagnosis_type == "weekly_pattern":
        start = target - timedelta(days=6)
    else:
        start = target
    entries = _fetch_entries_between(cur, user_id, start, target)
    day_entries = [e for e in entries if e["entryDate"] == target.isoformat()] if diagnosis_type != "weekly_pattern" else entries
    cur.execute(f"SELECT {_SELECT_COLUMNS} FROM attention_daily_covenants WHERE user_id=%s AND covenant_date=%s LIMIT 1", (user_id, target))
    covenant_row = cur.fetchone()
    covenant = _row_to_dto(covenant_row) if covenant_row else None
    cur.execute(f"SELECT {_FOCUS_COLUMNS} FROM attention_focus_sessions WHERE user_id=%s AND started_at::date BETWEEN %s AND %s", (user_id, start, target))
    sessions = [_focus_row_to_dto(r) for r in cur.fetchall()]
    cur.execute(f"SELECT {_REVIEW_COLUMNS} FROM attention_reviews WHERE user_id=%s AND review_date=%s LIMIT 1", (user_id, target))
    review_row = cur.fetchone()
    review = _review_row_to_dto(review_row) if review_row else None
    completed = [s for s in sessions if s.get("endedAt")]
    ledger = calculate_daily_summary(day_entries)
    return {
        "userLocalDate": target.isoformat(),
        "diagnosisType": diagnosis_type,
        "covenant": {
            "exists": bool(covenant),
            "primaryOffering": covenant.get("primaryOffering") if covenant else None,
            "missionFocus": covenant.get("missionFocus") if covenant else None,
            "worshipFocus": covenant.get("worshipFocus") if covenant else None,
            "relationshipFocus": covenant.get("relationshipFocus") if covenant else None,
            "restorationFocus": covenant.get("restorationFocus") if covenant else None,
            "mainRisk": covenant.get("mainRisk") if covenant else None,
            "riskPulls": covenant.get("riskPulls") if covenant else [],
            "digitalBoundary": covenant.get("digitalBoundary") if covenant else None,
            "timeBoundary": covenant.get("timeBoundary") if covenant else None,
            "spiritualBoundary": covenant.get("spiritualBoundary") if covenant else None,
            "scriptureReference": covenant.get("scriptureReference") if covenant else None,
            "scriptureText": covenant.get("scriptureText") if covenant else None,
        },
        "ledger": ledger,
        "entries": [
            {
                "id": e["id"],
                "category": e["category"],
                "activityName": e["activityName"],
                "durationMinutes": e["durationMinutes"],
                "attentionState": e.get("attentionState"),
                "pulls": e.get("pulls") or [],
                "noteSummary": (e.get("note") or "")[:120] or None,
            }
            for e in day_entries[:50]
        ],
        "focus": {
            "completedSessions": len(completed),
            "totalActualMinutes": sum(int(s.get("actualMinutes") or 0) for s in completed),
            "interruptedSessions": len([s for s in sessions if s.get("interrupted")]),
            "activeSessionExists": any(not s.get("endedAt") for s in sessions),
        },
        "review": {
            "exists": bool(review),
            "hasBiggestCapture": bool(review and review.get("biggestCapture")),
            "hasBiggestGrace": bool(review and review.get("biggestGrace")),
            "hasRepentancePoint": bool(review and review.get("repentancePoint")),
            "hasTomorrowBoundary": bool(review and review.get("tomorrowBoundary")),
        },
        "recentPatterns": {
            "daysIncluded": (target - start).days + 1,
            "averageCapturedMinutes": round(calculate_daily_summary(entries)["capturedMinutes"] / max(1, (target - start).days + 1), 1),
            "averageInvestedMinutes": round(calculate_daily_summary(entries)["investedMinutes"] / max(1, (target - start).days + 1), 1),
            "frequentPulls": calculate_daily_summary(entries)["topPulls"],
        },
        "userQuestion": user_question,
    }


def _generate_diagnosis_output(ctx: dict, extra_text: Optional[str] = None, quick: bool = False) -> dict:
    texts = [extra_text, ctx.get("userQuestion"), (ctx.get("covenant") or {}).get("mainRisk")]
    for e in ctx.get("entries") or []:
        texts.extend([e.get("activityName"), e.get("noteSummary")])
    safety = safety_check(*texts)
    result = generate_fallback_diagnosis(ctx, safety["level"], quick=quick)
    return {"diagnosis": result, "provider": "fallback_rules", "modelName": "rule_based_v1", "generatedBy": "fallback"}


def _save_diagnosis_record(cur, user_id: str, target: date, diagnosis_type: str, ctx: dict, output: dict, saved: bool) -> dict:
    cur.execute(
        f"""INSERT INTO attention_ai_diagnoses
        (user_id, diagnosis_date, diagnosis_type, source_range_start, source_range_end,
         input_summary, result, provider, model_name, generated_by, safety_level, saved_by_user)
        VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s)
        RETURNING {_DIAGNOSIS_COLUMNS}""",
        (
            user_id,
            target,
            diagnosis_type,
            target - timedelta(days=6) if diagnosis_type == "weekly_pattern" else target,
            target,
            _Json(compact_context_summary(ctx)),
            _Json(output["diagnosis"]),
            output["provider"],
            output["modelName"],
            output["generatedBy"],
            output["diagnosis"].get("safetyLevel", "normal"),
            saved,
        ),
    )
    return _diagnosis_row_to_dto(cur.fetchone())


@router.post("/diagnosis/generate")
def generate_diagnosis(request: Request, body: DiagnosisGenerateIn) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    target = _parse_optional_date(body.date, "date", _local_date(request, user))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            ctx = _build_diagnosis_context(cur, user_id, request, target, body.diagnosis_type)
            output = _generate_diagnosis_output(ctx)
            record = _save_diagnosis_record(cur, user_id, target, body.diagnosis_type, ctx, output, True) if body.save else None
        conn.commit()
        return {**output, "record": record}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise _json_error("DIAGNOSIS_GENERATION_FAILED", "暂时无法生成守心洞察，请稍后再试。", 500)
    finally:
        _state["release_db"](conn)


@router.post("/diagnosis/quick-reset")
def quick_reset(request: Request, body: QuickResetIn) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    target = _local_date(request, user)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            ctx = _build_diagnosis_context(cur, user_id, request, target, "quick_reset", body.current_struggle)
            if body.pulls:
                ctx["ledger"]["topPulls"] = [{"pull": p, "label": PULL_LABELS.get(p, p), "count": 1, "minutes": 0} for p in body.pulls]
            output = _generate_diagnosis_output(ctx, extra_text=body.current_struggle, quick=True)
            record = _save_diagnosis_record(cur, user_id, target, "quick_reset", ctx, output, True) if body.save else None
        conn.commit()
        return {**output, "record": record}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/diagnosis/ask")
def ask_diagnosis_agent(request: Request, body: AskDiagnosisIn) -> dict:
    user = _require_user(request)
    question_lower = body.question.lower()
    if any(k in question_lower for k in ["买什么", "卖什么", "投资建议", "诊断疾病", "法律意见"]):
        ctx = {
            "userLocalDate": _local_date(request, user).isoformat(),
            "diagnosisType": "user_question",
            "ledger": {"entriesCount": 0, "topPulls": [], "capturedMinutes": 0},
            "focus": {},
            "covenant": {"exists": False},
            "review": {"exists": False},
            "entries": [],
            "userQuestion": body.question,
        }
        output = _generate_diagnosis_output(ctx)
        output["diagnosis"]["shortSummary"] = "这个问题超出了守心 Agent 的范围。我不能提供投资、医疗或法律判断，但可以帮助你看见这个问题背后的注意力牵引，并设立边界。"
        return {**output, "record": None}
    user_id = _db_user_id(user)
    target = _parse_optional_date(body.date, "date", _local_date(request, user))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            ctx = _build_diagnosis_context(cur, user_id, request, target, "user_question", body.question)
            output = _generate_diagnosis_output(ctx, extra_text=body.question)
            record = _save_diagnosis_record(cur, user_id, target, "user_question", ctx, output, True) if body.save else None
        conn.commit()
        return {**output, "record": record}
    finally:
        _state["release_db"](conn)


@router.get("/diagnoses")
def list_diagnoses(
    request: Request,
    from_date: Optional[str] = Query(default=None, alias="from"),
    to_date: Optional[str] = Query(default=None, alias="to"),
    type: Optional[str] = Query(default=None),
    saved_only: bool = Query(default=False, alias="savedOnly"),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    user = _require_user(request)
    today = _local_date(request, user)
    end = _parse_optional_date(to_date, "to", today)
    start = _parse_optional_date(from_date, "from", end - timedelta(days=30))
    if type and type not in DIAGNOSIS_TYPES:
        raise _json_error("VALIDATION_ERROR", "type 不合法。", 400)
    clauses = ["user_id=%s", "diagnosis_date BETWEEN %s AND %s"]
    params: list[Any] = [_db_user_id(user), start, end]
    if type:
        clauses.append("diagnosis_type=%s")
        params.append(type)
    if saved_only:
        clauses.append("saved_by_user=true")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_DIAGNOSIS_COLUMNS} FROM attention_ai_diagnoses WHERE {' AND '.join(clauses)} ORDER BY created_at DESC LIMIT %s",
                params + [limit],
            )
            rows = cur.fetchall()
        return {"diagnoses": [_diagnosis_row_to_dto(r) for r in rows]}
    finally:
        _state["release_db"](conn)


@router.get("/diagnoses/{diagnosis_id}")
def get_diagnosis(diagnosis_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_DIAGNOSIS_COLUMNS} FROM attention_ai_diagnoses WHERE id=%s AND user_id=%s", (diagnosis_id, user_id))
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这份守心洞察。", 404)
        return {"diagnosis": _diagnosis_row_to_dto(row)}
    finally:
        _state["release_db"](conn)


@router.delete("/diagnoses/{diagnosis_id}")
def delete_diagnosis(diagnosis_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM attention_ai_diagnoses WHERE id=%s AND user_id=%s", (diagnosis_id, user_id))
            if cur.rowcount == 0:
                raise _json_error("NOT_FOUND", "没有找到这份守心洞察。", 404)
        conn.commit()
        return {"ok": True}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.patch("/diagnoses/{diagnosis_id}/feedback")
def update_diagnosis_feedback(diagnosis_id: str, request: Request, body: FeedbackIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE attention_ai_diagnoses SET user_rating=%s, user_feedback=%s WHERE id=%s AND user_id=%s RETURNING {_DIAGNOSIS_COLUMNS}",
                (body.rating, body.feedback, diagnosis_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这份守心洞察。", 404)
        conn.commit()
        return {"diagnosis": _diagnosis_row_to_dto(row)}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)

