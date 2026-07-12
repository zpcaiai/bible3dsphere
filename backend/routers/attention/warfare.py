"""Attention Stewardship / 守心 API — warfare map / plans / check-ins routes.

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
# Batch 4: Attention Warfare Map / Plans / Check-ins
# ---------------------------------------------------------------------------


@router.get("/warfare/pattern-library")
def get_warfare_pattern_library(request: Request) -> dict:
    _require_user(request)
    return {"patterns": pattern_definitions()}


@router.get("/warfare/map")
def get_warfare_map(
    request: Request,
    days: int = Query(default=7),
    from_date: Optional[str] = Query(default=None, alias="from"),
    to_date: Optional[str] = Query(default=None, alias="to"),
) -> dict:
    user = _require_user(request)
    today = _local_date(request, user)
    if from_date or to_date:
        end = _parse_optional_date(to_date, "to", today)
        start = _parse_optional_date(from_date, "from", end - timedelta(days=6))
    else:
        if days not in {7, 14, 30}:
            raise _json_error("VALIDATION_ERROR", "days 只能是 7、14 或 30。", 400)
        end = today
        start = end - timedelta(days=days - 1)
    if start > end or (end - start).days > 30:
        raise _json_error("VALIDATION_ERROR", "争战地图范围最多 30 天。", 400)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            data = _load_warfare_data(cur, _db_user_id(user), start, end)
        return {"map": build_warfare_map(data, start, end)}
    finally:
        _state["release_db"](conn)


@router.get("/warfare/plans")
def list_warfare_plans(request: Request, status: str = Query(default="active")) -> dict:
    user_id = _db_user_id(_require_user(request))
    if status not in {"active", "paused", "archived", "all"}:
        raise _json_error("VALIDATION_ERROR", "status 不合法。", 400)
    clause = "user_id=%s" if status == "all" else "user_id=%s AND status=%s"
    params = (user_id,) if status == "all" else (user_id, status)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_PLAN_COLUMNS} FROM attention_warfare_plans WHERE {clause} ORDER BY created_at DESC", params)
            rows = cur.fetchall()
        return {"plans": [_plan_row_to_dto(r) for r in rows]}
    finally:
        _state["release_db"](conn)


@router.post("/warfare/plans")
def create_warfare_plan(request: Request, body: WarfarePlanIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""INSERT INTO attention_warfare_plans
                (user_id, pattern_key, title, description, primary_pulls, trigger_situations,
                 vulnerable_times, common_behaviors, possible_root, gospel_truth,
                 scripture_reference, scripture_text, digital_boundary, time_boundary,
                 spiritual_boundary, replacement_practice, escape_plan, accountability_prompt,
                 status, source_type)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING {_PLAN_COLUMNS}""",
                (
                    user_id, body.pattern_key, body.title, body.description, body.primary_pulls,
                    body.trigger_situations, body.vulnerable_times, body.common_behaviors,
                    body.possible_root, body.gospel_truth, body.scripture_reference,
                    body.scripture_text, body.digital_boundary, body.time_boundary,
                    body.spiritual_boundary, body.replacement_practice, body.escape_plan,
                    body.accountability_prompt, body.status, body.source_type,
                ),
            )
            row = cur.fetchone()
        conn.commit()
        return {"plan": _plan_row_to_dto(row)}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/warfare/plans/{plan_id}")
def get_warfare_plan(plan_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            return {"plan": _require_plan(cur, user_id, plan_id)}
    finally:
        _state["release_db"](conn)


@router.put("/warfare/plans/{plan_id}")
def update_warfare_plan(plan_id: str, request: Request, body: WarfarePlanUpdate) -> dict:
    user_id = _db_user_id(_require_user(request))
    data = body.model_dump(by_alias=False, exclude_unset=True)
    fields = {
        "title": "title", "description": "description", "primary_pulls": "primary_pulls",
        "trigger_situations": "trigger_situations", "vulnerable_times": "vulnerable_times",
        "common_behaviors": "common_behaviors", "possible_root": "possible_root",
        "gospel_truth": "gospel_truth", "scripture_reference": "scripture_reference",
        "scripture_text": "scripture_text", "digital_boundary": "digital_boundary",
        "time_boundary": "time_boundary", "spiritual_boundary": "spiritual_boundary",
        "replacement_practice": "replacement_practice", "escape_plan": "escape_plan",
        "accountability_prompt": "accountability_prompt", "status": "status",
    }
    updates = [(fields[k], v) for k, v in data.items() if k in fields]
    if not updates:
        raise _json_error("VALIDATION_ERROR", "没有可更新的字段。", 400)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            assignments = ", ".join([f"{col}=%s" for col, _ in updates])
            cur.execute(
                f"UPDATE attention_warfare_plans SET {assignments} WHERE id=%s AND user_id=%s RETURNING {_PLAN_COLUMNS}",
                [v for _, v in updates] + [plan_id, user_id],
            )
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这条守心计划。", 404)
        conn.commit()
        return {"plan": _plan_row_to_dto(row)}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.delete("/warfare/plans/{plan_id}")
def delete_warfare_plan(plan_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM attention_warfare_plans WHERE id=%s AND user_id=%s", (plan_id, user_id))
            if cur.rowcount == 0:
                raise _json_error("NOT_FOUND", "没有找到这条守心计划。", 404)
        conn.commit()
        return {"ok": True}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/warfare/from-diagnosis")
def create_plan_from_diagnosis(request: Request, body: FromDiagnosisIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_DIAGNOSIS_COLUMNS} FROM attention_ai_diagnoses WHERE id=%s AND user_id=%s", (body.diagnosis_id, user_id))
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这份守心洞察。", 404)
            diagnosis = _diagnosis_row_to_dto(row)
            cur.execute("SELECT id FROM attention_warfare_plans WHERE user_id=%s AND source_diagnosis_id=%s LIMIT 1", (user_id, body.diagnosis_id))
            if cur.fetchone():
                raise _json_error("PLAN_ALREADY_EXISTS_FOR_DIAGNOSIS", "这份守心洞察已经创建过计划。", 409)
            result = diagnosis["result"] or {}
            primary = result.get("primaryPattern") or {}
            key = primary.get("key") if primary.get("key") in WARFARE_PATTERN_KEYS else "custom"
            scripture = (result.get("scriptureSuggestions") or [{}])[0]
            action = result.get("actionPlan") or {}
            pulls = [p.get("pull") for p in result.get("attentionPulls", []) if p.get("pull") in ATTENTION_PULLS]
            cur.execute(
                f"""INSERT INTO attention_warfare_plans
                (user_id, pattern_key, title, description, primary_pulls, possible_root,
                 gospel_truth, scripture_reference, scripture_text, digital_boundary,
                 spiritual_boundary, replacement_practice, escape_plan, accountability_prompt,
                 source_type, source_diagnosis_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'diagnosis',%s)
                RETURNING {_PLAN_COLUMNS}""",
                (
                    user_id, key, f"{primary.get('label') or '守心'}计划",
                    result.get("shortSummary"), clean_pulls(pulls),
                    primary.get("description"), (result.get("repentanceInvitation") or {}).get("content"),
                    scripture.get("reference"), scripture.get("text"),
                    action.get("tomorrowBoundary"), action.get("todayReset"),
                    action.get("replacementPractice"), action.get("concreteNextStep"),
                    action.get("accountabilityPrompt"), body.diagnosis_id,
                ),
            )
            plan = _plan_row_to_dto(cur.fetchone())
        conn.commit()
        return {"plan": plan}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/warfare/plans/{plan_id}/checkins")
def list_plan_checkins(
    plan_id: str,
    request: Request,
    from_date: Optional[str] = Query(default=None, alias="from"),
    to_date: Optional[str] = Query(default=None, alias="to"),
) -> dict:
    user = _require_user(request)
    today = _local_date(request, user)
    end = _parse_optional_date(to_date, "to", today)
    start = _parse_optional_date(from_date, "from", end - timedelta(days=13))
    user_id = _db_user_id(user)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_plan(cur, user_id, plan_id)
            cur.execute(
                f"SELECT {_CHECKIN_COLUMNS} FROM attention_warfare_checkins WHERE user_id=%s AND plan_id=%s AND checkin_date BETWEEN %s AND %s ORDER BY checkin_date DESC",
                (user_id, plan_id, start, end),
            )
            rows = cur.fetchall()
        return {"checkins": [_checkin_row_to_dto(r) for r in rows]}
    finally:
        _state["release_db"](conn)


@router.post("/warfare/plans/{plan_id}/checkins")
def upsert_plan_checkin(plan_id: str, request: Request, body: WarfareCheckinIn) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    target = _parse_optional_date(body.checkin_date, "checkinDate", _local_date(request, user))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_plan(cur, user_id, plan_id)
            cur.execute(
                f"""INSERT INTO attention_warfare_checkins
                (user_id, plan_id, checkin_date, status, noticed, resisted, escaped,
                 returned_to_god, trigger_observed, boundary_used, replacement_used,
                 grace_noticed, tomorrow_adjustment, prayer)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (user_id, plan_id, checkin_date) DO UPDATE SET
                status=EXCLUDED.status, noticed=EXCLUDED.noticed, resisted=EXCLUDED.resisted,
                escaped=EXCLUDED.escaped, returned_to_god=EXCLUDED.returned_to_god,
                trigger_observed=EXCLUDED.trigger_observed, boundary_used=EXCLUDED.boundary_used,
                replacement_used=EXCLUDED.replacement_used, grace_noticed=EXCLUDED.grace_noticed,
                tomorrow_adjustment=EXCLUDED.tomorrow_adjustment, prayer=EXCLUDED.prayer
                RETURNING {_CHECKIN_COLUMNS}""",
                (
                    user_id, plan_id, target, body.status, body.noticed, body.resisted,
                    body.escaped, body.returned_to_god, body.trigger_observed,
                    body.boundary_used, body.replacement_used, body.grace_noticed,
                    body.tomorrow_adjustment, body.prayer,
                ),
            )
            row = cur.fetchone()
        conn.commit()
        return {"checkin": _checkin_row_to_dto(row)}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/warfare/checkins/today")
def get_today_warfare_checkins(request: Request) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    today = _local_date(request, user)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_PLAN_COLUMNS} FROM attention_warfare_plans WHERE user_id=%s AND status='active' ORDER BY created_at DESC", (user_id,))
            plans = [_plan_row_to_dto(r) for r in cur.fetchall()]
            cur.execute(f"SELECT {_CHECKIN_COLUMNS} FROM attention_warfare_checkins WHERE user_id=%s AND checkin_date=%s", (user_id, today))
            by_plan = {_checkin_row_to_dto(r)["planId"]: _checkin_row_to_dto(r) for r in cur.fetchall()}
        return {"date": today.isoformat(), "items": [{"plan": p, "checkin": by_plan.get(p["id"])} for p in plans]}
    finally:
        _state["release_db"](conn)
