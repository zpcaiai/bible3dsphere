"""Attention Stewardship / 守心 API."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import os
import uuid
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

try:
    from backend.attention_suggest import ATTENTION_PULLS, build_attention_suggestion
    from backend.attention_domain import (
        ATTENTION_CATEGORIES, ATTENTION_STATES, PULL_LABELS, SCRIPTURE_LIBRARY,
        clean_pulls, calculate_daily_summary, compact_context_summary,
        generate_fallback_diagnosis, safety_check, build_warfare_map,
        pattern_definitions,
    )
    from backend.attention_reports import (
        build_daily_score_input, build_weekly_report, compute_daily_score,
        category_totals, growth_summary, list_dates,
        previous_week_range, week_range_from_start,
    )
    from backend.attention_accountability import (
        CHALLENGE_PRIVACY_MODES, CHALLENGE_STATUSES, CHALLENGE_TEMPLATES,
        CHALLENGE_TYPES, DEFAULT_PRIVACY, GROUP_ROLES, GROUP_STATUSES,
        GROUP_TYPES, MEMBER_STATUSES, PARTNER_STATUSES, PRAYER_CATEGORIES,
        PRAYER_STATUSES, SHARE_SCOPES, SHARE_SOURCE_TYPES, VISIBILITY_LEVELS,
        build_share_payload, challenge_progress, challenge_templates_for_lang,
        default_partner_permissions,
        sanitize_privacy_update, sanitize_sensitive_categories, sanitize_visibility,
    )
    from backend.attention_integration import (
        ATTENTION_ROUTES, ATTENTION_TABLES, ATTENTION_VERSION,
        attention_audit_checks, attention_environment_check,
        attention_feature_flags, content_library_summary, release_checklist,
    )
except Exception:  # pragma: no cover
    from attention_suggest import ATTENTION_PULLS, build_attention_suggestion  # type: ignore
    from attention_domain import (  # type: ignore
        ATTENTION_CATEGORIES, ATTENTION_STATES, PULL_LABELS, SCRIPTURE_LIBRARY,
        clean_pulls, calculate_daily_summary, compact_context_summary,
        generate_fallback_diagnosis, safety_check, build_warfare_map,
        pattern_definitions,
    )
    from attention_reports import (  # type: ignore
        build_daily_score_input, build_weekly_report, compute_daily_score,
        category_totals, growth_summary, list_dates,
        previous_week_range, week_range_from_start,
    )
    from attention_accountability import (  # type: ignore
        CHALLENGE_PRIVACY_MODES, CHALLENGE_STATUSES, CHALLENGE_TEMPLATES,
        CHALLENGE_TYPES, DEFAULT_PRIVACY, GROUP_ROLES, GROUP_STATUSES,
        GROUP_TYPES, MEMBER_STATUSES, PARTNER_STATUSES, PRAYER_CATEGORIES,
        PRAYER_STATUSES, SHARE_SCOPES, SHARE_SOURCE_TYPES, VISIBILITY_LEVELS,
        build_share_payload, challenge_progress, challenge_templates_for_lang,
        default_partner_permissions,
        sanitize_privacy_update, sanitize_sensitive_categories, sanitize_visibility,
    )
    from attention_integration import (  # type: ignore
        ATTENTION_ROUTES, ATTENTION_TABLES, ATTENTION_VERSION,
        attention_audit_checks, attention_environment_check,
        attention_feature_flags, content_library_summary, release_checklist,
    )

router = APIRouter(prefix="/api/attention", tags=["attention"])
_state: Dict[str, Any] = {}
DEFAULT_TIMEZONE = "Asia/Taipei"


def init_attention_router(*, get_db, release_db, get_session_user, to_shanghai_iso, is_admin=None) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail={"error": "UNAUTHORIZED", "message": "请先登录。"})
    return user


def _require_attention_admin(request: Request) -> dict:
    user = _require_user(request)
    checker = _state.get("is_admin")
    if not checker or not checker(user.get("email")):
        raise _json_error("FORBIDDEN", "仅管理员可访问守心运营后台。", 403)
    return user


def _db_user_id(user: dict) -> str:
    return str(user.get("email") or user.get("id") or "")


def _local_timezone(request: Request, user: dict) -> ZoneInfo:
    tz_name = (
        user.get("timezone")
        or request.headers.get("X-Timezone")
        or request.cookies.get("timezone")
        or DEFAULT_TIMEZONE
    )
    try:
        return ZoneInfo(str(tz_name))
    except Exception:
        return ZoneInfo(DEFAULT_TIMEZONE)


def _local_date(request: Request, user: dict) -> date:
    return datetime.now(_local_timezone(request, user)).date()


def _local_day_bounds(request: Request, user: dict, target: date) -> tuple[datetime, datetime]:
    tz = _local_timezone(request, user)
    start = datetime.combine(target, datetime.min.time(), tzinfo=tz)
    return start.astimezone(timezone.utc), (start + timedelta(days=1)).astimezone(timezone.utc)


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _json_error(error: str, message: str, status: int) -> HTTPException:
    return HTTPException(status_code=status, detail={"error": error, "message": message})


def _safe_scalar(cur, sql: str, params: tuple = ()) -> int:
    try:
        cur.execute(sql, params)
        row = cur.fetchone()
        return int(row[0] or 0) if row else 0
    except Exception:
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return 0


def _safe_rows(cur, sql: str, params: tuple = ()) -> list:
    try:
        cur.execute(sql, params)
        return list(cur.fetchall())
    except Exception:
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return []

def _parse_date(value: str, field_name: str) -> date:
    try:
        if not value:
            raise ValueError
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        raise _json_error("VALIDATION_ERROR", f"{field_name} 必须是 YYYY-MM-DD。", 400)
# ---------------------------------------------------------------------------
# Batch 2: Focus Mode / Ledger / Evening Review / Today Summary
# ---------------------------------------------------------------------------

FOCUS_TYPES = {"mission", "worship", "relationship", "restoration"}
DIAGNOSIS_TYPES = {"daily", "weekly_pattern", "quick_reset", "review_support", "user_question"}
WARFARE_PATTERN_KEYS = {p["key"] for p in pattern_definitions()} | {"custom"}
CHECKIN_STATUSES = {"not_seen", "noticed", "resisted", "escaped", "captured", "returned"}
PLAN_STATUSES = {"active", "paused", "archived"}


def _Json(obj):
    try:
        from psycopg2.extras import Json
        return Json(obj)
    except Exception:  # pragma: no cover
        return json.dumps(obj, ensure_ascii=False)


def _json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return value


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _minutes_between(started_at: datetime, ended_at: Optional[datetime] = None) -> int:
    end = ended_at or _utc_now()
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return max(1, int((end - started_at).total_seconds() // 60))


def _clip_text(value: Optional[str], max_len: int = 2000) -> Optional[str]:
    if value is None:
        return None
    text = value.strip()
    return text[:max_len] or None


def _clean_text_list(values: Optional[List[str]], *, max_items: int = 20, max_len: int = 200) -> List[str]:
    cleaned = []
    for value in values or []:
        text = str(value).strip()[:max_len]
        if text and text not in cleaned:
            cleaned.append(text)
        if len(cleaned) >= max_items:
            break
    return cleaned

def _focus_row_to_dto(row) -> dict:
    actual = row[5]
    if actual is None:
        actual = _minutes_between(row[1])
    return {
        "id": str(row[0]),
        "startedAt": _iso(row[1]),
        "endedAt": _iso(row[2]),
        "plannedMinutes": row[3],
        "actualMinutes": actual,
        "focusType": row[4],
        "intention": row[6],
        "openingPrayer": row[7],
        "closingReflection": row[8],
        "interrupted": bool(row[9]),
        "interruptionReason": row[10],
        "createdAt": _iso(row[11]),
    }


_FOCUS_COLUMNS = """
    id, started_at, ended_at, planned_minutes, focus_type, actual_minutes,
    intention, opening_prayer, closing_reflection, interrupted,
    interruption_reason, created_at
"""


def _entry_row_to_dto(row) -> dict:
    return {
        "id": str(row[0]),
        "entryDate": _iso(row[1]),
        "category": row[2],
        "activityName": row[3],
        "durationMinutes": row[4],
        "attentionState": row[5],
        "pulls": list(row[6] or []),
        "note": row[7],
        "createdAt": _iso(row[8]),
        "updatedAt": _iso(row[9]),
    }


_ENTRY_COLUMNS = """
    id, entry_date, category, activity_name, duration_minutes,
    attention_state, pulls, note, created_at, updated_at
"""


def _review_row_to_dto(row) -> dict:
    return {
        "id": str(row[0]),
        "reviewDate": _iso(row[1]),
        "biggestCapture": row[2],
        "biggestGrace": row[3],
        "repentancePoint": row[4],
        "tomorrowBoundary": row[5],
        "prayer": row[6],
        "createdAt": _iso(row[7]),
        "updatedAt": _iso(row[8]),
    }


_REVIEW_COLUMNS = """
    id, review_date, biggest_capture, biggest_grace, repentance_point,
    tomorrow_boundary, prayer, created_at, updated_at
"""


def _diagnosis_row_to_dto(row) -> dict:
    return {
        "id": str(row[0]),
        "diagnosisDate": _iso(row[1]),
        "diagnosisType": row[2],
        "sourceRangeStart": _iso(row[3]),
        "sourceRangeEnd": _iso(row[4]),
        "result": _json_value(row[5]) or {},
        "provider": row[6],
        "modelName": row[7],
        "generatedBy": row[8],
        "safetyLevel": row[9],
        "savedByUser": bool(row[10]),
        "userFeedback": row[11],
        "userRating": row[12],
        "createdAt": _iso(row[13]),
        "updatedAt": _iso(row[14]),
    }


_DIAGNOSIS_COLUMNS = """
    id, diagnosis_date, diagnosis_type, source_range_start, source_range_end,
    result, provider, model_name, generated_by, safety_level, saved_by_user,
    user_feedback, user_rating, created_at, updated_at
"""


def _plan_row_to_dto(row) -> dict:
    return {
        "id": str(row[0]),
        "patternKey": row[1],
        "title": row[2],
        "description": row[3],
        "primaryPulls": list(row[4] or []),
        "triggerSituations": list(row[5] or []),
        "vulnerableTimes": list(row[6] or []),
        "commonBehaviors": list(row[7] or []),
        "possibleRoot": row[8],
        "gospelTruth": row[9],
        "scriptureReference": row[10],
        "scriptureText": row[11],
        "digitalBoundary": row[12],
        "timeBoundary": row[13],
        "spiritualBoundary": row[14],
        "replacementPractice": row[15],
        "escapePlan": row[16],
        "accountabilityPrompt": row[17],
        "status": row[18],
        "sourceType": row[19],
        "sourceDiagnosisId": str(row[20]) if row[20] else None,
        "createdAt": _iso(row[21]),
        "updatedAt": _iso(row[22]),
    }


_PLAN_COLUMNS = """
    id, pattern_key, title, description, primary_pulls, trigger_situations,
    vulnerable_times, common_behaviors, possible_root, gospel_truth,
    scripture_reference, scripture_text, digital_boundary, time_boundary,
    spiritual_boundary, replacement_practice, escape_plan, accountability_prompt,
    status, source_type, source_diagnosis_id, created_at, updated_at
"""


def _checkin_row_to_dto(row) -> dict:
    return {
        "id": str(row[0]),
        "planId": str(row[1]),
        "checkinDate": _iso(row[2]),
        "status": row[3],
        "noticed": bool(row[4]),
        "resisted": bool(row[5]),
        "escaped": bool(row[6]),
        "returnedToGod": bool(row[7]),
        "triggerObserved": row[8],
        "boundaryUsed": row[9],
        "replacementUsed": row[10],
        "graceNoticed": row[11],
        "tomorrowAdjustment": row[12],
        "prayer": row[13],
        "createdAt": _iso(row[14]),
        "updatedAt": _iso(row[15]),
    }


_CHECKIN_COLUMNS = """
    id, plan_id, checkin_date, status, noticed, resisted, escaped,
    returned_to_god, trigger_observed, boundary_used, replacement_used,
    grace_noticed, tomorrow_adjustment, prayer, created_at, updated_at
"""


def _parse_optional_date(value: Optional[str], field_name: str, fallback: date) -> date:
    return _parse_date(value, field_name) if value else fallback


def _require_plan(cur, user_id: str, plan_id: str) -> dict:
    cur.execute(f"SELECT {_PLAN_COLUMNS} FROM attention_warfare_plans WHERE id=%s AND user_id=%s", (plan_id, user_id))
    row = cur.fetchone()
    if not row:
        raise _json_error("NOT_FOUND", "没有找到这条守心计划。", 404)
    return _plan_row_to_dto(row)


_SELECT_COLUMNS = """
    id, covenant_date, primary_offering, mission_focus, worship_focus,
    relationship_focus, restoration_focus, main_risk, risk_pulls,
    digital_boundary, time_boundary, spiritual_boundary, scripture_reference,
    scripture_text, prayer, status, created_at, updated_at
"""


def _row_to_dto(row) -> dict:
    return {
        "id": str(row[0]),
        "covenantDate": _iso(row[1]),
        "primaryOffering": row[2],
        "missionFocus": row[3],
        "worshipFocus": row[4],
        "relationshipFocus": row[5],
        "restorationFocus": row[6],
        "mainRisk": row[7],
        "riskPulls": list(row[8] or []),
        "digitalBoundary": row[9],
        "timeBoundary": row[10],
        "spiritualBoundary": row[11],
        "scriptureReference": row[12],
        "scriptureText": row[13],
        "prayer": row[14],
        "status": row[15],
        "createdAt": _iso(row[16]),
        "updatedAt": _iso(row[17]),
    }

_SCORE_COLUMNS = """
    id, score_date, score, score_label, data_completeness, confidence,
    component_scores, input_summary, insights, generated_by, version,
    created_at, updated_at
"""

_REPORT_COLUMNS = """
    id, week_start, week_end, worship_minutes, mission_minutes,
    relationship_minutes, restoration_minutes, captured_minutes,
    score_average, score_label, score_trend, data_completeness,
    daily_scores, category_minutes, category_percentages, focus_summary,
    covenant_summary, review_summary, warfare_summary, top_pulls,
    growth_signals, report_sections, summary, main_pattern,
    recommended_practice, next_week_practice, prayer, status, version,
    created_at, updated_at
"""

def _load_daily_score_input(cur, user_id: str, target: date) -> dict:
    cur.execute(f"SELECT {_SELECT_COLUMNS} FROM attention_daily_covenants WHERE user_id=%s AND covenant_date=%s LIMIT 1", (user_id, target))
    covenant_row = cur.fetchone()
    covenant = _row_to_dto(covenant_row) if covenant_row else None
    cur.execute(f"SELECT {_ENTRY_COLUMNS} FROM attention_entries WHERE user_id=%s AND entry_date=%s ORDER BY created_at DESC", (user_id, target))
    entries = [_entry_row_to_dto(r) for r in cur.fetchall()]
    cur.execute(f"SELECT {_FOCUS_COLUMNS} FROM attention_focus_sessions WHERE user_id=%s AND started_at::date=%s", (user_id, target))
    sessions = [_focus_row_to_dto(r) for r in cur.fetchall()]
    cur.execute(f"SELECT {_REVIEW_COLUMNS} FROM attention_reviews WHERE user_id=%s AND review_date=%s LIMIT 1", (user_id, target))
    review_row = cur.fetchone()
    review = _review_row_to_dto(review_row) if review_row else None
    cur.execute(
        f"SELECT {_CHECKIN_COLUMNS} FROM attention_warfare_checkins WHERE user_id=%s AND checkin_date=%s",
        (user_id, target),
    )
    checkins = [_checkin_row_to_dto(r) for r in cur.fetchall()]
    return build_daily_score_input(
        target=target,
        covenant=covenant,
        entries=entries,
        focus_sessions=sessions,
        review=review,
        checkins=checkins,
    )

def _report_row_to_dto(row) -> dict:
    category_minutes = _json_value(row[13]) or {
        "worship": row[3] or 0,
        "mission": row[4] or 0,
        "relationship": row[5] or 0,
        "restoration": row[6] or 0,
        "captured": row[7] or 0,
    }
    report_sections = _json_value(row[21]) or {}
    return {
        "id": str(row[0]),
        "weekStart": _iso(row[1]),
        "weekEnd": _iso(row[2]),
        "scoreAverage": row[8],
        "scoreLabel": row[9] or "insufficient_data",
        "scoreTrend": row[10] or "insufficient",
        "dataCompleteness": int(row[11] or 0),
        "dailyScores": _json_value(row[12]) or [],
        "categoryMinutes": category_minutes,
        "categoryPercentages": _json_value(row[14]) or {},
        "focusSummary": _json_value(row[15]) or {},
        "covenantSummary": _json_value(row[16]) or {},
        "reviewSummary": _json_value(row[17]) or {},
        "warfareSummary": _json_value(row[18]) or {},
        "topPulls": _json_value(row[19]) or [],
        "growthSignals": _json_value(row[20]) or {},
        "reportSections": report_sections,
        "summary": row[22] or report_sections.get("weeklySummary"),
        "mainPattern": row[23] or report_sections.get("mainPattern"),
        "recommendedPractice": row[24],
        "nextWeekPractice": row[25] or report_sections.get("nextWeekPractice"),
        "prayer": row[26],
        "status": row[27] or "generated",
        "version": row[28] or "v1",
        "createdAt": _iso(row[29]),
        "updatedAt": _iso(row[30]),
    }

def _fetch_entries_between(cur, user_id: str, start: date, end: date) -> list[dict]:
    cur.execute(
        f"SELECT {_ENTRY_COLUMNS} FROM attention_entries WHERE user_id=%s AND entry_date BETWEEN %s AND %s ORDER BY entry_date DESC, created_at DESC LIMIT 200",
        (user_id, start, end),
    )
    return [_entry_row_to_dto(r) for r in cur.fetchall()]

def _load_warfare_data(cur, user_id: str, start: date, end: date) -> dict:
    entries = _fetch_entries_between(cur, user_id, start, end)
    cur.execute(f"SELECT {_SELECT_COLUMNS} FROM attention_daily_covenants WHERE user_id=%s AND covenant_date BETWEEN %s AND %s", (user_id, start, end))
    covenants = [_row_to_dto(r) for r in cur.fetchall()]
    cur.execute(f"SELECT {_FOCUS_COLUMNS} FROM attention_focus_sessions WHERE user_id=%s AND started_at::date BETWEEN %s AND %s", (user_id, start, end))
    sessions = [_focus_row_to_dto(r) for r in cur.fetchall()]
    cur.execute(f"SELECT {_REVIEW_COLUMNS} FROM attention_reviews WHERE user_id=%s AND review_date BETWEEN %s AND %s", (user_id, start, end))
    reviews = [_review_row_to_dto(r) for r in cur.fetchall()]
    cur.execute(f"SELECT {_DIAGNOSIS_COLUMNS} FROM attention_ai_diagnoses WHERE user_id=%s AND diagnosis_date BETWEEN %s AND %s ORDER BY created_at DESC LIMIT 20", (user_id, start, end))
    diagnoses = [_diagnosis_row_to_dto(r) for r in cur.fetchall()]
    cur.execute(f"SELECT {_PLAN_COLUMNS} FROM attention_warfare_plans WHERE user_id=%s AND status='active' ORDER BY created_at DESC", (user_id,))
    plans = [_plan_row_to_dto(r) for r in cur.fetchall()]
    cur.execute(
        """SELECT c.id, c.plan_id, c.checkin_date, c.status, c.noticed, c.resisted,
        c.escaped, c.returned_to_god, c.trigger_observed, c.boundary_used,
        c.replacement_used, c.grace_noticed, c.tomorrow_adjustment, c.prayer,
        c.created_at, c.updated_at, p.pattern_key
        FROM attention_warfare_checkins c JOIN attention_warfare_plans p ON p.id=c.plan_id
        WHERE c.user_id=%s AND c.checkin_date BETWEEN %s AND %s
        ORDER BY c.checkin_date DESC""",
        (user_id, start, end),
    )
    checkins = []
    for row in cur.fetchall():
        dto = _checkin_row_to_dto(row[:16])
        dto["patternKey"] = row[16]
        checkins.append(dto)
    recent_patterns = []
    for d in diagnoses[:3]:
        primary = ((d.get("result") or {}).get("primaryPattern") or {})
        if primary:
            recent_patterns.append({
                "diagnosisId": d["id"],
                "diagnosisDate": d["diagnosisDate"],
                "patternKey": primary.get("key"),
                "label": primary.get("label"),
                "shortSummary": (d.get("result") or {}).get("shortSummary", ""),
            })
    return {
        "entries": entries,
        "covenants": covenants,
        "focusSessions": sessions,
        "reviews": reviews,
        "diagnoses": diagnoses,
        "activePlans": plans,
        "checkins": checkins,
        "recentDiagnosisPatterns": recent_patterns,
    }


