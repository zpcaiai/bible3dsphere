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
        build_share_payload, challenge_progress, default_partner_permissions,
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
        build_share_payload, challenge_progress, default_partner_permissions,
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


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class CovenantIn(CamelModel):
    primary_offering: str = Field(alias="primaryOffering", min_length=1, max_length=500)
    mission_focus: Optional[str] = Field(default=None, alias="missionFocus", max_length=500)
    worship_focus: Optional[str] = Field(default=None, alias="worshipFocus", max_length=500)
    relationship_focus: Optional[str] = Field(default=None, alias="relationshipFocus", max_length=500)
    restoration_focus: Optional[str] = Field(default=None, alias="restorationFocus", max_length=500)
    main_risk: Optional[str] = Field(default=None, alias="mainRisk", max_length=500)
    risk_pulls: List[str] = Field(default_factory=list, alias="riskPulls", max_length=20)
    digital_boundary: Optional[str] = Field(default=None, alias="digitalBoundary", max_length=500)
    time_boundary: Optional[str] = Field(default=None, alias="timeBoundary", max_length=500)
    spiritual_boundary: Optional[str] = Field(default=None, alias="spiritualBoundary", max_length=500)
    scripture_reference: Optional[str] = Field(default=None, alias="scriptureReference", max_length=100)
    scripture_text: Optional[str] = Field(default=None, alias="scriptureText", max_length=1000)
    prayer: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("primary_offering")
    @classmethod
    def trim_primary(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("请写下今天最想把注意力献给什么。")
        return value

    @field_validator(
        "mission_focus", "worship_focus", "relationship_focus", "restoration_focus",
        "main_risk", "digital_boundary", "time_boundary", "spiritual_boundary",
        "scripture_reference", "scripture_text", "prayer",
    )
    @classmethod
    def trim_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("risk_pulls")
    @classmethod
    def validate_pulls(cls, values: List[str]) -> List[str]:
        cleaned = []
        for value in values or []:
            if value not in ATTENTION_PULLS:
                raise ValueError(f"invalid attention pull: {value}")
            if value not in cleaned:
                cleaned.append(value)
        return cleaned


class CovenantUpdate(CamelModel):
    id: Optional[str] = Field(default=None, max_length=80)
    primary_offering: Optional[str] = Field(default=None, alias="primaryOffering", max_length=500)
    mission_focus: Optional[str] = Field(default=None, alias="missionFocus", max_length=500)
    worship_focus: Optional[str] = Field(default=None, alias="worshipFocus", max_length=500)
    relationship_focus: Optional[str] = Field(default=None, alias="relationshipFocus", max_length=500)
    restoration_focus: Optional[str] = Field(default=None, alias="restorationFocus", max_length=500)
    main_risk: Optional[str] = Field(default=None, alias="mainRisk", max_length=500)
    risk_pulls: Optional[List[str]] = Field(default=None, alias="riskPulls", max_length=20)
    digital_boundary: Optional[str] = Field(default=None, alias="digitalBoundary", max_length=500)
    time_boundary: Optional[str] = Field(default=None, alias="timeBoundary", max_length=500)
    spiritual_boundary: Optional[str] = Field(default=None, alias="spiritualBoundary", max_length=500)
    scripture_reference: Optional[str] = Field(default=None, alias="scriptureReference", max_length=100)
    scripture_text: Optional[str] = Field(default=None, alias="scriptureText", max_length=1000)
    prayer: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[str] = Field(default=None, max_length=40)

    @field_validator("primary_offering")
    @classmethod
    def trim_primary(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("请写下今天最想把注意力献给什么。")
        return value

    @field_validator(
        "mission_focus", "worship_focus", "relationship_focus", "restoration_focus",
        "main_risk", "digital_boundary", "time_boundary", "spiritual_boundary",
        "scripture_reference", "scripture_text", "prayer", "status",
    )
    @classmethod
    def trim_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("risk_pulls")
    @classmethod
    def validate_pulls(cls, values: Optional[List[str]]) -> Optional[List[str]]:
        if values is None:
            return None
        cleaned = []
        for value in values:
            if value not in ATTENTION_PULLS:
                raise ValueError(f"invalid attention pull: {value}")
            if value not in cleaned:
                cleaned.append(value)
        return cleaned


class SuggestIn(CamelModel):
    primary_offering: str = Field(default="", alias="primaryOffering", max_length=500)
    main_risk: str = Field(default="", alias="mainRisk", max_length=500)
    risk_pulls: List[str] = Field(default_factory=list, alias="riskPulls", max_length=20)

    @field_validator("risk_pulls")
    @classmethod
    def validate_pulls(cls, values: List[str]) -> List[str]:
        for value in values or []:
            if value not in ATTENTION_PULLS:
                raise ValueError(f"invalid attention pull: {value}")
        return list(dict.fromkeys(values or []))


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


def _parse_date(value: str, field_name: str) -> date:
    try:
        if not value:
            raise ValueError
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        raise _json_error("VALIDATION_ERROR", f"{field_name} 必须是 YYYY-MM-DD。", 400)


@router.get("/covenant/today")
def get_today_covenant(request: Request) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    today = _local_date(request, user)
    day_start, day_end = _local_day_bounds(request, user, today)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_SELECT_COLUMNS} FROM attention_daily_covenants "
                "WHERE user_id=%s AND covenant_date=%s LIMIT 1",
                (user_id, today),
            )
            row = cur.fetchone()
        return {"exists": bool(row), "covenant": _row_to_dto(row) if row else None}
    except HTTPException:
        raise
    except Exception:
        raise _json_error("INTERNAL_SERVER_ERROR", "获取今日立约失败。", 500)
    finally:
        _state["release_db"](conn)


@router.post("/covenant")
def create_covenant(request: Request, body: CovenantIn) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    today = _local_date(request, user)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM attention_daily_covenants WHERE user_id=%s AND covenant_date=%s LIMIT 1",
                (user_id, today),
            )
            if cur.fetchone():
                raise _json_error("COVENANT_ALREADY_EXISTS", "今天已经完成注意力立约，可以编辑已有立约。", 409)
            cur.execute(
                f"""
                INSERT INTO attention_daily_covenants (
                    user_id, covenant_date, primary_offering, mission_focus,
                    worship_focus, relationship_focus, restoration_focus,
                    main_risk, risk_pulls, digital_boundary, time_boundary,
                    spiritual_boundary, scripture_reference, scripture_text, prayer
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING {_SELECT_COLUMNS}
                """,
                (
                    user_id, today, body.primary_offering, body.mission_focus,
                    body.worship_focus, body.relationship_focus, body.restoration_focus,
                    body.main_risk, body.risk_pulls, body.digital_boundary,
                    body.time_boundary, body.spiritual_boundary,
                    body.scripture_reference, body.scripture_text, body.prayer,
                ),
            )
            row = cur.fetchone()
        conn.commit()
        return {"covenant": _row_to_dto(row)}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise _json_error("INTERNAL_SERVER_ERROR", "保存今日立约时遇到问题，请稍后再试。", 500)
    finally:
        _state["release_db"](conn)


@router.put("/covenant/{covenant_id}")
def update_covenant_by_id(covenant_id: str, request: Request, body: CovenantUpdate) -> dict:
    return _update_covenant(request, covenant_id, body)


@router.put("/covenant")
def update_covenant(request: Request, body: CovenantUpdate) -> dict:
    if not body.id:
        raise _json_error("VALIDATION_ERROR", "缺少立约 ID。", 400)
    return _update_covenant(request, body.id, body)


def _update_covenant(request: Request, covenant_id: str, body: CovenantUpdate) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    data = body.model_dump(by_alias=False, exclude_unset=True)
    data.pop("id", None)
    fields = {
        "primary_offering": "primary_offering",
        "mission_focus": "mission_focus",
        "worship_focus": "worship_focus",
        "relationship_focus": "relationship_focus",
        "restoration_focus": "restoration_focus",
        "main_risk": "main_risk",
        "risk_pulls": "risk_pulls",
        "digital_boundary": "digital_boundary",
        "time_boundary": "time_boundary",
        "spiritual_boundary": "spiritual_boundary",
        "scripture_reference": "scripture_reference",
        "scripture_text": "scripture_text",
        "prayer": "prayer",
        "status": "status",
    }
    updates = [(column, data[key]) for key, column in fields.items() if key in data]
    if not updates:
        raise _json_error("VALIDATION_ERROR", "没有可更新的字段。", 400)
    assignments = ", ".join([f"{column}=%s" for column, _ in updates])
    params = [value for _, value in updates] + [covenant_id, user_id]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE attention_daily_covenants SET {assignments} "
                "WHERE id=%s AND user_id=%s RETURNING " + _SELECT_COLUMNS,
                params,
            )
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这条立约。", 404)
        conn.commit()
        return {"covenant": _row_to_dto(row)}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise _json_error("INTERNAL_SERVER_ERROR", "保存今日立约时遇到问题，请稍后再试。", 500)
    finally:
        _state["release_db"](conn)


@router.get("/covenants")
def list_covenants(
    request: Request,
    from_date: Optional[str] = Query(default=None, alias="from"),
    to_date: Optional[str] = Query(default=None, alias="to"),
) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    today = _local_date(request, user)
    end = _parse_date(to_date, "to") if to_date else today
    start = _parse_date(from_date, "from") if from_date else end - timedelta(days=13)
    if start > end:
        raise _json_error("VALIDATION_ERROR", "from 不能晚于 to。", 400)
    if (end - start).days > 90:
        raise _json_error("VALIDATION_ERROR", "日期范围最多 90 天。", 400)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_SELECT_COLUMNS} FROM attention_daily_covenants "
                "WHERE user_id=%s AND covenant_date BETWEEN %s AND %s "
                "ORDER BY covenant_date DESC",
                (user_id, start, end),
            )
            rows = cur.fetchall()
        return {"covenants": [_row_to_dto(row) for row in rows]}
    except HTTPException:
        raise
    except Exception:
        raise _json_error("INTERNAL_SERVER_ERROR", "获取历史立约失败。", 500)
    finally:
        _state["release_db"](conn)


@router.post("/covenant/suggest")
def suggest_covenant(body: SuggestIn) -> dict:
    return build_attention_suggestion(
        primary_offering=body.primary_offering,
        main_risk=body.main_risk,
        risk_pulls=body.risk_pulls,
    )


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


class FocusSessionIn(CamelModel):
    planned_minutes: int = Field(alias="plannedMinutes", ge=1, le=240)
    focus_type: str = Field(alias="focusType", min_length=1, max_length=40)
    intention: Optional[str] = Field(default=None, max_length=500)
    opening_prayer: Optional[str] = Field(default=None, alias="openingPrayer", max_length=2000)

    @field_validator("focus_type")
    @classmethod
    def validate_focus_type(cls, value: str) -> str:
        if value not in FOCUS_TYPES:
            raise ValueError("invalid focus type")
        return value

    @field_validator("intention", "opening_prayer")
    @classmethod
    def trim_optional(cls, value: Optional[str]) -> Optional[str]:
        return _clip_text(value)


class FocusEndIn(CamelModel):
    closing_reflection: Optional[str] = Field(default=None, alias="closingReflection", max_length=2000)
    actual_minutes: Optional[int] = Field(default=None, alias="actualMinutes", ge=1, le=1440)

    @field_validator("closing_reflection")
    @classmethod
    def trim_optional(cls, value: Optional[str]) -> Optional[str]:
        return _clip_text(value)


class FocusInterruptIn(CamelModel):
    interruption_reason: str = Field(alias="interruptionReason", min_length=1, max_length=2000)

    @field_validator("interruption_reason")
    @classmethod
    def trim_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("interruptionReason required")
        return value[:2000]


class EntryIn(CamelModel):
    entry_date: Optional[str] = Field(default=None, alias="entryDate")
    category: str = Field(min_length=1, max_length=40)
    activity_name: str = Field(alias="activityName", min_length=1, max_length=200)
    duration_minutes: int = Field(alias="durationMinutes", ge=1, le=1440)
    attention_state: Optional[str] = Field(default=None, alias="attentionState", max_length=40)
    pulls: List[str] = Field(default_factory=list, max_length=20)
    note: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        if value not in ATTENTION_CATEGORIES:
            raise ValueError("invalid category")
        return value

    @field_validator("attention_state")
    @classmethod
    def validate_state(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        if value not in ATTENTION_STATES:
            raise ValueError("invalid attention state")
        return value

    @field_validator("pulls")
    @classmethod
    def validate_pulls(cls, values: List[str]) -> List[str]:
        cleaned = clean_pulls(values)
        if len(cleaned) != len(list(dict.fromkeys(values or []))):
            raise ValueError("invalid attention pull")
        return cleaned

    @field_validator("activity_name", "note")
    @classmethod
    def trim_text(cls, value: Optional[str]) -> Optional[str]:
        return _clip_text(value)


class EntryUpdate(CamelModel):
    entry_date: Optional[str] = Field(default=None, alias="entryDate")
    category: Optional[str] = Field(default=None, max_length=40)
    activity_name: Optional[str] = Field(default=None, alias="activityName", max_length=200)
    duration_minutes: Optional[int] = Field(default=None, alias="durationMinutes", ge=1, le=1440)
    attention_state: Optional[str] = Field(default=None, alias="attentionState", max_length=40)
    pulls: Optional[List[str]] = Field(default=None, max_length=20)
    note: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if value not in ATTENTION_CATEGORIES:
            raise ValueError("invalid category")
        return value

    @field_validator("attention_state")
    @classmethod
    def validate_state(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        if value not in ATTENTION_STATES:
            raise ValueError("invalid attention state")
        return value

    @field_validator("pulls")
    @classmethod
    def validate_pulls(cls, values: Optional[List[str]]) -> Optional[List[str]]:
        if values is None:
            return None
        cleaned = clean_pulls(values)
        if len(cleaned) != len(list(dict.fromkeys(values or []))):
            raise ValueError("invalid attention pull")
        return cleaned

    @field_validator("activity_name", "note")
    @classmethod
    def trim_text(cls, value: Optional[str]) -> Optional[str]:
        return _clip_text(value)


class ReviewIn(CamelModel):
    review_date: Optional[str] = Field(default=None, alias="reviewDate")
    biggest_capture: Optional[str] = Field(default=None, alias="biggestCapture", max_length=2000)
    biggest_grace: Optional[str] = Field(default=None, alias="biggestGrace", max_length=2000)
    repentance_point: Optional[str] = Field(default=None, alias="repentancePoint", max_length=2000)
    tomorrow_boundary: Optional[str] = Field(default=None, alias="tomorrowBoundary", max_length=2000)
    prayer: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("biggest_capture", "biggest_grace", "repentance_point", "tomorrow_boundary", "prayer")
    @classmethod
    def trim_optional(cls, value: Optional[str]) -> Optional[str]:
        return _clip_text(value)


class DiagnosisGenerateIn(CamelModel):
    date: Optional[str] = None
    diagnosis_type: str = Field(default="daily", alias="diagnosisType")
    include_recent_patterns: bool = Field(default=True, alias="includeRecentPatterns")
    save: bool = False

    @field_validator("diagnosis_type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value not in DIAGNOSIS_TYPES:
            raise ValueError("invalid diagnosisType")
        return value


class QuickResetIn(CamelModel):
    current_struggle: str = Field(alias="currentStruggle", min_length=1, max_length=1000)
    pulls: List[str] = Field(default_factory=list, max_length=20)
    save: bool = False

    @field_validator("pulls")
    @classmethod
    def validate_pulls(cls, values: List[str]) -> List[str]:
        cleaned = clean_pulls(values)
        if len(cleaned) != len(list(dict.fromkeys(values or []))):
            raise ValueError("invalid attention pull")
        return cleaned

    @field_validator("current_struggle")
    @classmethod
    def trim_struggle(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("currentStruggle required")
        return value[:1000]


class AskDiagnosisIn(CamelModel):
    question: str = Field(min_length=1, max_length=2000)
    date: Optional[str] = None
    include_recent_patterns: bool = Field(default=True, alias="includeRecentPatterns")
    save: bool = False

    @field_validator("question")
    @classmethod
    def trim_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question required")
        return value[:2000]


class FeedbackIn(CamelModel):
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    feedback: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("feedback")
    @classmethod
    def trim_feedback(cls, value: Optional[str]) -> Optional[str]:
        return _clip_text(value, 1000)


class WarfarePlanIn(CamelModel):
    pattern_key: str = Field(alias="patternKey", min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    primary_pulls: List[str] = Field(default_factory=list, alias="primaryPulls", max_length=20)
    trigger_situations: List[str] = Field(default_factory=list, alias="triggerSituations", max_length=20)
    vulnerable_times: List[str] = Field(default_factory=list, alias="vulnerableTimes", max_length=20)
    common_behaviors: List[str] = Field(default_factory=list, alias="commonBehaviors", max_length=20)
    possible_root: Optional[str] = Field(default=None, alias="possibleRoot", max_length=2000)
    gospel_truth: Optional[str] = Field(default=None, alias="gospelTruth", max_length=2000)
    scripture_reference: Optional[str] = Field(default=None, alias="scriptureReference", max_length=100)
    scripture_text: Optional[str] = Field(default=None, alias="scriptureText", max_length=1000)
    digital_boundary: Optional[str] = Field(default=None, alias="digitalBoundary", max_length=1000)
    time_boundary: Optional[str] = Field(default=None, alias="timeBoundary", max_length=1000)
    spiritual_boundary: Optional[str] = Field(default=None, alias="spiritualBoundary", max_length=1000)
    replacement_practice: Optional[str] = Field(default=None, alias="replacementPractice", max_length=1000)
    escape_plan: Optional[str] = Field(default=None, alias="escapePlan", max_length=1000)
    accountability_prompt: Optional[str] = Field(default=None, alias="accountabilityPrompt", max_length=1000)
    source_type: Optional[str] = Field(default="manual", alias="sourceType", max_length=40)
    status: Optional[str] = Field(default="active", max_length=40)

    @field_validator("pattern_key")
    @classmethod
    def validate_pattern(cls, value: str) -> str:
        if value not in WARFARE_PATTERN_KEYS:
            raise ValueError("invalid patternKey")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> str:
        value = value or "active"
        if value not in PLAN_STATUSES:
            raise ValueError("invalid status")
        return value

    @field_validator("primary_pulls")
    @classmethod
    def validate_pulls(cls, values: List[str]) -> List[str]:
        cleaned = clean_pulls(values)
        if len(cleaned) != len(list(dict.fromkeys(values or []))):
            raise ValueError("invalid attention pull")
        return cleaned

    @field_validator("trigger_situations", "vulnerable_times", "common_behaviors")
    @classmethod
    def clean_lists(cls, values: List[str]) -> List[str]:
        return _clean_text_list(values)

    @field_validator(
        "title", "description", "possible_root", "gospel_truth", "scripture_reference",
        "scripture_text", "digital_boundary", "time_boundary", "spiritual_boundary",
        "replacement_practice", "escape_plan", "accountability_prompt", "source_type",
    )
    @classmethod
    def trim_text(cls, value: Optional[str]) -> Optional[str]:
        return _clip_text(value)


class WarfarePlanUpdate(CamelModel):
    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    primary_pulls: Optional[List[str]] = Field(default=None, alias="primaryPulls", max_length=20)
    trigger_situations: Optional[List[str]] = Field(default=None, alias="triggerSituations", max_length=20)
    vulnerable_times: Optional[List[str]] = Field(default=None, alias="vulnerableTimes", max_length=20)
    common_behaviors: Optional[List[str]] = Field(default=None, alias="commonBehaviors", max_length=20)
    possible_root: Optional[str] = Field(default=None, alias="possibleRoot", max_length=2000)
    gospel_truth: Optional[str] = Field(default=None, alias="gospelTruth", max_length=2000)
    scripture_reference: Optional[str] = Field(default=None, alias="scriptureReference", max_length=100)
    scripture_text: Optional[str] = Field(default=None, alias="scriptureText", max_length=1000)
    digital_boundary: Optional[str] = Field(default=None, alias="digitalBoundary", max_length=1000)
    time_boundary: Optional[str] = Field(default=None, alias="timeBoundary", max_length=1000)
    spiritual_boundary: Optional[str] = Field(default=None, alias="spiritualBoundary", max_length=1000)
    replacement_practice: Optional[str] = Field(default=None, alias="replacementPractice", max_length=1000)
    escape_plan: Optional[str] = Field(default=None, alias="escapePlan", max_length=1000)
    accountability_prompt: Optional[str] = Field(default=None, alias="accountabilityPrompt", max_length=1000)
    status: Optional[str] = Field(default=None, max_length=40)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in PLAN_STATUSES:
            raise ValueError("invalid status")
        return value

    @field_validator("primary_pulls")
    @classmethod
    def validate_pulls(cls, values: Optional[List[str]]) -> Optional[List[str]]:
        if values is None:
            return None
        cleaned = clean_pulls(values)
        if len(cleaned) != len(list(dict.fromkeys(values or []))):
            raise ValueError("invalid attention pull")
        return cleaned

    @field_validator("trigger_situations", "vulnerable_times", "common_behaviors")
    @classmethod
    def clean_lists(cls, values: Optional[List[str]]) -> Optional[List[str]]:
        if values is None:
            return None
        return _clean_text_list(values)

    @field_validator(
        "title", "description", "possible_root", "gospel_truth", "scripture_reference",
        "scripture_text", "digital_boundary", "time_boundary", "spiritual_boundary",
        "replacement_practice", "escape_plan", "accountability_prompt",
    )
    @classmethod
    def trim_text(cls, value: Optional[str]) -> Optional[str]:
        return _clip_text(value)


class WarfareCheckinIn(CamelModel):
    checkin_date: Optional[str] = Field(default=None, alias="checkinDate")
    status: str = Field(min_length=1, max_length=40)
    noticed: bool = False
    resisted: bool = False
    escaped: bool = False
    returned_to_god: bool = Field(default=False, alias="returnedToGod")
    trigger_observed: Optional[str] = Field(default=None, alias="triggerObserved", max_length=2000)
    boundary_used: Optional[str] = Field(default=None, alias="boundaryUsed", max_length=2000)
    replacement_used: Optional[str] = Field(default=None, alias="replacementUsed", max_length=2000)
    grace_noticed: Optional[str] = Field(default=None, alias="graceNoticed", max_length=2000)
    tomorrow_adjustment: Optional[str] = Field(default=None, alias="tomorrowAdjustment", max_length=2000)
    prayer: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in CHECKIN_STATUSES:
            raise ValueError("invalid status")
        return value

    @field_validator("trigger_observed", "boundary_used", "replacement_used", "grace_noticed", "tomorrow_adjustment", "prayer")
    @classmethod
    def trim_optional(cls, value: Optional[str]) -> Optional[str]:
        return _clip_text(value)


class FromDiagnosisIn(CamelModel):
    diagnosis_id: str = Field(alias="diagnosisId", min_length=1, max_length=80)


class DailyScoreIn(CamelModel):
    date: Optional[str] = Field(default=None, max_length=10)


class WeeklyReportGenerateIn(CamelModel):
    week_start: Optional[str] = Field(default=None, alias="weekStart", max_length=10)
    force_regenerate: bool = Field(default=False, alias="forceRegenerate")


class PrivacySettingsIn(CamelModel):
    default_partner_visibility: Optional[str] = Field(default=None, alias="defaultPartnerVisibility")
    default_group_visibility: Optional[str] = Field(default=None, alias="defaultGroupVisibility")
    default_challenge_visibility: Optional[str] = Field(default=None, alias="defaultChallengeVisibility")
    share_scores_with_partners: Optional[bool] = Field(default=None, alias="shareScoresWithPartners")
    share_scores_with_groups: Optional[bool] = Field(default=None, alias="shareScoresWithGroups")
    share_weekly_report_summary: Optional[bool] = Field(default=None, alias="shareWeeklyReportSummary")
    share_warfare_plan_progress: Optional[bool] = Field(default=None, alias="shareWarfarePlanProgress")
    share_prayer_requests: Optional[bool] = Field(default=None, alias="sharePrayerRequests")
    hide_sensitive_categories: Optional[List[str]] = Field(default=None, alias="hideSensitiveCategories")
    allow_partner_reminders: Optional[bool] = Field(default=None, alias="allowPartnerReminders")
    allow_group_challenge_reminders: Optional[bool] = Field(default=None, alias="allowGroupChallengeReminders")
    require_preview_before_sharing: Optional[bool] = Field(default=None, alias="requirePreviewBeforeSharing")


class PartnerInviteIn(CamelModel):
    partner_user_id: str = Field(alias="partnerUserId", min_length=1, max_length=255)
    message: Optional[str] = Field(default=None, max_length=1000)
    permissions: Optional[dict] = None

    @field_validator("message")
    @classmethod
    def trim_message(cls, value: Optional[str]) -> Optional[str]:
        return _clip_text(value, 1000)


class PartnerActionIn(CamelModel):
    action: str = Field(min_length=1, max_length=20)


class PartnerPermissionsIn(CamelModel):
    visibility_level: Optional[str] = Field(default=None, alias="visibilityLevel")
    can_see_daily_covenant_status: Optional[bool] = Field(default=None, alias="canSeeDailyCovenantStatus")
    can_see_focus_status: Optional[bool] = Field(default=None, alias="canSeeFocusStatus")
    can_see_review_status: Optional[bool] = Field(default=None, alias="canSeeReviewStatus")
    can_see_weekly_report_summary: Optional[bool] = Field(default=None, alias="canSeeWeeklyReportSummary")
    can_see_score_summary: Optional[bool] = Field(default=None, alias="canSeeScoreSummary")
    can_see_warfare_plan_progress: Optional[bool] = Field(default=None, alias="canSeeWarfarePlanProgress")
    can_see_prayer_requests: Optional[bool] = Field(default=None, alias="canSeePrayerRequests")
    can_send_reminders: Optional[bool] = Field(default=None, alias="canSendReminders")
    hidden_sensitive_categories: Optional[List[str]] = Field(default=None, alias="hiddenSensitiveCategories")


class ShareCreateIn(CamelModel):
    scope: str = Field(min_length=1, max_length=40)
    target_user_id: Optional[str] = Field(default=None, alias="targetUserId", max_length=255)
    target_group_id: Optional[str] = Field(default=None, alias="targetGroupId", max_length=80)
    source_type: str = Field(alias="sourceType", min_length=1, max_length=60)
    source_id: Optional[str] = Field(default=None, alias="sourceId", max_length=80)
    visibility_level: str = Field(default="summary", alias="visibilityLevel", max_length=40)
    include_score: bool = Field(default=False, alias="includeScore")
    include_top_pulls: bool = Field(default=False, alias="includeTopPulls")
    include_next_practice: bool = Field(default=True, alias="includeNextPractice")
    custom_message: Optional[str] = Field(default=None, alias="customMessage", max_length=1000)

    @field_validator("custom_message")
    @classmethod
    def trim_custom(cls, value: Optional[str]) -> Optional[str]:
        return _clip_text(value, 1000)


class PrayerRequestIn(CamelModel):
    target_user_id: Optional[str] = Field(default=None, alias="targetUserId", max_length=255)
    target_group_id: Optional[str] = Field(default=None, alias="targetGroupId", max_length=80)
    title: str = Field(min_length=1, max_length=200)
    body: Optional[str] = Field(default=None, max_length=2000)
    category: Optional[str] = Field(default="attention", max_length=40)
    visibility_level: str = Field(default="summary", alias="visibilityLevel", max_length=40)
    is_sensitive: bool = Field(default=False, alias="isSensitive")

    @field_validator("title", "body")
    @classmethod
    def trim_prayer_text(cls, value: Optional[str]) -> Optional[str]:
        return _clip_text(value, 2000)


class PrayerRequestUpdateIn(CamelModel):
    title: Optional[str] = Field(default=None, max_length=200)
    body: Optional[str] = Field(default=None, max_length=2000)
    category: Optional[str] = Field(default=None, max_length=40)
    visibility_level: Optional[str] = Field(default=None, alias="visibilityLevel", max_length=40)
    is_sensitive: Optional[bool] = Field(default=None, alias="isSensitive")
    status: Optional[str] = Field(default=None, max_length=40)
    answered_note: Optional[str] = Field(default=None, alias="answeredNote", max_length=2000)
    action: Optional[str] = Field(default=None, max_length=40)


class PrayerMarkIn(CamelModel):
    message: Optional[str] = Field(default=None, max_length=500)


class GroupCreateIn(CamelModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    group_type: str = Field(default="private", alias="groupType", max_length=40)
    default_member_visibility: str = Field(default="status_only", alias="defaultMemberVisibility", max_length=40)
    guidelines: Optional[str] = Field(default=None, max_length=2000)


class GroupUpdateIn(CamelModel):
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    group_type: Optional[str] = Field(default=None, alias="groupType", max_length=40)
    invite_enabled: Optional[bool] = Field(default=None, alias="inviteEnabled")
    default_member_visibility: Optional[str] = Field(default=None, alias="defaultMemberVisibility", max_length=40)
    guidelines: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[str] = Field(default=None, max_length=40)


class GroupInviteIn(CamelModel):
    invited_user_id: Optional[str] = Field(default=None, alias="invitedUserId", max_length=255)
    invited_email: Optional[str] = Field(default=None, alias="invitedEmail", max_length=255)
    create_invite_code: bool = Field(default=False, alias="createInviteCode")
    message: Optional[str] = Field(default=None, max_length=1000)


class GroupJoinIn(CamelModel):
    invite_code: str = Field(alias="inviteCode", min_length=1, max_length=80)


class MemberUpdateIn(CamelModel):
    role: Optional[str] = Field(default=None, max_length=40)
    status: Optional[str] = Field(default=None, max_length=40)


class ChallengeCreateIn(CamelModel):
    template_key: Optional[str] = Field(default=None, alias="templateKey", max_length=80)
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    challenge_type: str = Field(alias="challengeType", min_length=1, max_length=60)
    start_date: str = Field(alias="startDate", min_length=10, max_length=10)
    end_date: str = Field(alias="endDate", min_length=10, max_length=10)
    target_days: Optional[int] = Field(default=None, alias="targetDays", ge=1, le=90)
    target_minutes: Optional[int] = Field(default=None, alias="targetMinutes", ge=1, le=10000)
    checkin_prompt: Optional[str] = Field(default=None, alias="checkinPrompt", max_length=500)
    privacy_mode: str = Field(default="status_only", alias="privacyMode", max_length=40)
    allow_comments: bool = Field(default=False, alias="allowComments")
    allow_prayer_requests: bool = Field(default=True, alias="allowPrayerRequests")


class ChallengeUpdateIn(CamelModel):
    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    start_date: Optional[str] = Field(default=None, alias="startDate", max_length=10)
    end_date: Optional[str] = Field(default=None, alias="endDate", max_length=10)
    target_days: Optional[int] = Field(default=None, alias="targetDays", ge=1, le=90)
    target_minutes: Optional[int] = Field(default=None, alias="targetMinutes", ge=1, le=10000)
    checkin_prompt: Optional[str] = Field(default=None, alias="checkinPrompt", max_length=500)
    privacy_mode: Optional[str] = Field(default=None, alias="privacyMode", max_length=40)
    allow_comments: Optional[bool] = Field(default=None, alias="allowComments")
    allow_prayer_requests: Optional[bool] = Field(default=None, alias="allowPrayerRequests")
    status: Optional[str] = Field(default=None, max_length=40)


class ChallengeCheckinIn(CamelModel):
    checkin_date: Optional[str] = Field(default=None, alias="checkinDate", max_length=10)
    completed: bool = False
    value_minutes: Optional[int] = Field(default=None, alias="valueMinutes", ge=0, le=1440)
    value_count: Optional[int] = Field(default=None, alias="valueCount", ge=0, le=1000)
    reflection: Optional[str] = Field(default=None, max_length=1000)
    visibility_level: str = Field(default="status_only", alias="visibilityLevel", max_length=40)
    create_prayer_request: bool = Field(default=False, alias="createPrayerRequest")
    prayer_request_title: Optional[str] = Field(default=None, alias="prayerRequestTitle", max_length=200)
    prayer_request_body: Optional[str] = Field(default=None, alias="prayerRequestBody", max_length=2000)


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


@router.get("/focus-sessions/active")
def get_active_focus_session(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_FOCUS_COLUMNS} FROM attention_focus_sessions WHERE user_id=%s AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1", (_db_user_id(user),))
            row = cur.fetchone()
        return {"active": _focus_row_to_dto(row) if row else None}
    finally:
        _state["release_db"](conn)


@router.post("/focus-sessions")
def create_focus_session(request: Request, body: FocusSessionIn) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    now = _utc_now()
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM attention_focus_sessions WHERE user_id=%s AND ended_at IS NULL LIMIT 1", (user_id,))
            if cur.fetchone():
                raise _json_error("ACTIVE_FOCUS_SESSION_EXISTS", "当前已有进行中的专注。", 409)
            cur.execute(
                f"""INSERT INTO attention_focus_sessions
                (user_id, started_at, planned_minutes, focus_type, intention, opening_prayer)
                VALUES (%s,%s,%s,%s,%s,%s) RETURNING {_FOCUS_COLUMNS}""",
                (user_id, now, body.planned_minutes, body.focus_type, body.intention, body.opening_prayer),
            )
            row = cur.fetchone()
        conn.commit()
        return {"session": _focus_row_to_dto(row)}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise _json_error("INTERNAL_SERVER_ERROR", "开始专注时遇到问题。", 500)
    finally:
        _state["release_db"](conn)


@router.post("/focus-sessions/{session_id}/end")
@router.patch("/focus-sessions/{session_id}/end")
def end_focus_session(session_id: str, request: Request, body: FocusEndIn) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    ended_at = _utc_now()
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT started_at FROM attention_focus_sessions WHERE id=%s AND user_id=%s", (session_id, user_id))
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这段专注。", 404)
            actual = body.actual_minutes or _minutes_between(row[0], ended_at)
            cur.execute(
                f"""UPDATE attention_focus_sessions
                SET ended_at=%s, actual_minutes=%s, closing_reflection=COALESCE(%s, closing_reflection)
                WHERE id=%s AND user_id=%s RETURNING {_FOCUS_COLUMNS}""",
                (ended_at, actual, body.closing_reflection, session_id, user_id),
            )
            updated = cur.fetchone()
        conn.commit()
        return {"session": _focus_row_to_dto(updated)}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/focus-sessions/{session_id}/interrupt")
@router.patch("/focus-sessions/{session_id}/interrupt")
def interrupt_focus_session(session_id: str, request: Request, body: FocusInterruptIn) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""UPDATE attention_focus_sessions
                SET interrupted=true, interruption_reason=%s
                WHERE id=%s AND user_id=%s RETURNING {_FOCUS_COLUMNS}""",
                (body.interruption_reason, session_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这段专注。", 404)
        conn.commit()
        return {"session": _focus_row_to_dto(row)}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/focus-sessions")
def list_focus_sessions(
    request: Request,
    from_date: Optional[str] = Query(default=None, alias="from"),
    to_date: Optional[str] = Query(default=None, alias="to"),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    user = _require_user(request)
    today = _local_date(request, user)
    end = _parse_optional_date(to_date, "to", today + timedelta(days=1))
    start = _parse_optional_date(from_date, "from", end - timedelta(days=14))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT {_FOCUS_COLUMNS} FROM attention_focus_sessions
                WHERE user_id=%s AND started_at::date BETWEEN %s AND %s
                ORDER BY started_at DESC LIMIT %s""",
                (_db_user_id(user), start, end, limit),
            )
            rows = cur.fetchall()
        return {"sessions": [_focus_row_to_dto(row) for row in rows]}
    finally:
        _state["release_db"](conn)


@router.get("/entries/summary")
def get_entries_summary(request: Request, date_value: Optional[str] = Query(default=None, alias="date")) -> dict:
    user = _require_user(request)
    target = _parse_optional_date(date_value, "date", _local_date(request, user))
    entries = _load_entries_for_date(_db_user_id(user), target)
    return {"date": target.isoformat(), "summary": calculate_daily_summary(entries)}


@router.get("/entries")
def list_entries(request: Request, date_value: Optional[str] = Query(default=None, alias="date")) -> dict:
    user = _require_user(request)
    target = _parse_optional_date(date_value, "date", _local_date(request, user))
    entries = _load_entries_for_date(_db_user_id(user), target)
    return {"date": target.isoformat(), "entries": entries, "summary": calculate_daily_summary(entries)}


def _load_entries_for_date(user_id: str, target: date) -> list[dict]:
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_ENTRY_COLUMNS} FROM attention_entries WHERE user_id=%s AND entry_date=%s ORDER BY created_at DESC", (user_id, target))
            return [_entry_row_to_dto(row) for row in cur.fetchall()]
    finally:
        _state["release_db"](conn)


@router.post("/entries")
def create_entry(request: Request, body: EntryIn) -> dict:
    user = _require_user(request)
    target = _parse_optional_date(body.entry_date, "entryDate", _local_date(request, user))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""INSERT INTO attention_entries
                (user_id, entry_date, category, activity_name, duration_minutes, attention_state, pulls, note)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING {_ENTRY_COLUMNS}""",
                (_db_user_id(user), target, body.category, body.activity_name, body.duration_minutes, body.attention_state, body.pulls, body.note),
            )
            row = cur.fetchone()
        conn.commit()
        return {"entry": _entry_row_to_dto(row)}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.put("/entries/{entry_id}")
def update_entry(entry_id: str, request: Request, body: EntryUpdate) -> dict:
    user_id = _db_user_id(_require_user(request))
    data = body.model_dump(by_alias=False, exclude_unset=True)
    if "entry_date" in data and data["entry_date"]:
        data["entry_date"] = _parse_date(data["entry_date"], "entryDate")
    fields = {
        "entry_date": "entry_date", "category": "category", "activity_name": "activity_name",
        "duration_minutes": "duration_minutes", "attention_state": "attention_state",
        "pulls": "pulls", "note": "note",
    }
    updates = [(fields[k], v) for k, v in data.items() if k in fields]
    if not updates:
        raise _json_error("VALIDATION_ERROR", "没有可更新的字段。", 400)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            assignments = ", ".join([f"{col}=%s" for col, _ in updates])
            cur.execute(
                f"UPDATE attention_entries SET {assignments} WHERE id=%s AND user_id=%s RETURNING {_ENTRY_COLUMNS}",
                [v for _, v in updates] + [entry_id, user_id],
            )
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这条注意力记录。", 404)
        conn.commit()
        return {"entry": _entry_row_to_dto(row)}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.delete("/entries/{entry_id}")
def delete_entry(entry_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM attention_entries WHERE id=%s AND user_id=%s", (entry_id, user_id))
            if cur.rowcount == 0:
                raise _json_error("NOT_FOUND", "没有找到这条注意力记录。", 404)
        conn.commit()
        return {"ok": True}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/review/today")
def get_today_review(request: Request) -> dict:
    user = _require_user(request)
    target = _local_date(request, user)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_REVIEW_COLUMNS} FROM attention_reviews WHERE user_id=%s AND review_date=%s LIMIT 1", (_db_user_id(user), target))
            row = cur.fetchone()
        return {"exists": bool(row), "review": _review_row_to_dto(row) if row else None}
    finally:
        _state["release_db"](conn)


@router.post("/review")
def create_review(request: Request, body: ReviewIn) -> dict:
    user = _require_user(request)
    target = _parse_optional_date(body.review_date, "reviewDate", _local_date(request, user))
    if not any([body.biggest_capture, body.biggest_grace, body.repentance_point, body.tomorrow_boundary, body.prayer]):
        raise _json_error("VALIDATION_ERROR", "至少填写一项复盘内容。", 400)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""INSERT INTO attention_reviews
                (user_id, review_date, biggest_capture, biggest_grace, repentance_point, tomorrow_boundary, prayer)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (user_id, review_date) DO UPDATE SET
                biggest_capture=EXCLUDED.biggest_capture, biggest_grace=EXCLUDED.biggest_grace,
                repentance_point=EXCLUDED.repentance_point, tomorrow_boundary=EXCLUDED.tomorrow_boundary,
                prayer=EXCLUDED.prayer
                RETURNING {_REVIEW_COLUMNS}""",
                (_db_user_id(user), target, body.biggest_capture, body.biggest_grace, body.repentance_point, body.tomorrow_boundary, body.prayer),
            )
            row = cur.fetchone()
        conn.commit()
        return {"review": _review_row_to_dto(row)}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.put("/review/{review_id}")
def update_review(review_id: str, request: Request, body: ReviewIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""UPDATE attention_reviews SET
                biggest_capture=%s, biggest_grace=%s, repentance_point=%s,
                tomorrow_boundary=%s, prayer=%s
                WHERE id=%s AND user_id=%s RETURNING {_REVIEW_COLUMNS}""",
                (body.biggest_capture, body.biggest_grace, body.repentance_point, body.tomorrow_boundary, body.prayer, review_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这份复盘。", 404)
        conn.commit()
        return {"review": _review_row_to_dto(row)}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/review/suggest")
def suggest_review(request: Request) -> dict:
    user = _require_user(request)
    today = _local_date(request, user)
    entries = _load_entries_for_date(_db_user_id(user), today)
    summary = calculate_daily_summary(entries)
    top = summary["topPulls"][0]["label"] if summary["topPulls"] else "今天最明显的牵引"
    return {
        "suggestion": {
            "biggestGrace": "今天你愿意看见注意力的方向，这本身就是恩典。",
            "repentancePoint": f"可以把「{top}」带到神面前，不停在自责，而是选择归回。",
            "tomorrowBoundary": "明天先设一道小而具体的数字边界，并保留一段使命专注。",
            "prayer": "主啊，求你帮助我在诚实中看见，在恩典中归回。",
        }
    }


@router.get("/today/summary")
def get_today_summary(request: Request) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    today = _local_date(request, user)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_ENTRY_COLUMNS} FROM attention_entries WHERE user_id=%s AND entry_date=%s ORDER BY created_at DESC",
                (user_id, today),
            )
            entries = [_entry_row_to_dto(row) for row in cur.fetchall()]
            cur.execute(
                f"SELECT {_SELECT_COLUMNS} FROM attention_daily_covenants WHERE user_id=%s AND covenant_date=%s LIMIT 1",
                (user_id, today),
            )
            covenant_row = cur.fetchone()
            covenant = _row_to_dto(covenant_row) if covenant_row else None
            cur.execute(
                f"SELECT {_FOCUS_COLUMNS} FROM attention_focus_sessions WHERE user_id=%s AND started_at >= %s AND started_at < %s",
                (user_id, day_start, day_end),
            )
            sessions = [_focus_row_to_dto(r) for r in cur.fetchall()]
            cur.execute(f"SELECT {_REVIEW_COLUMNS} FROM attention_reviews WHERE user_id=%s AND review_date=%s LIMIT 1", (user_id, today))
            review = cur.fetchone()
            cur.execute(f"SELECT {_DIAGNOSIS_COLUMNS} FROM attention_ai_diagnoses WHERE user_id=%s AND diagnosis_date=%s ORDER BY created_at DESC LIMIT 1", (user_id, today))
            diagnosis = cur.fetchone()
            cur.execute(f"SELECT {_PLAN_COLUMNS} FROM attention_warfare_plans WHERE user_id=%s AND status='active' ORDER BY created_at DESC", (user_id,))
            plans = [_plan_row_to_dto(r) for r in cur.fetchall()]
            cur.execute(
                "SELECT COUNT(DISTINCT plan_id) FROM attention_warfare_checkins WHERE user_id=%s AND checkin_date=%s",
                (user_id, today),
            )
            today_warfare_checkins = int(cur.fetchone()[0] or 0)
            week_start, week_end = week_range_from_start(today)
            cur.execute(
                """SELECT score_average, score_label, data_completeness, top_pulls,
                next_week_practice FROM attention_weekly_reports
                WHERE user_id=%s AND week_start=%s AND week_end=%s AND status <> 'hidden'
                LIMIT 1""",
                (user_id, week_start, week_end),
            )
            weekly_row = cur.fetchone()
            cur.execute(
                """SELECT COUNT(*) FROM attention_accountability_relationships
                WHERE (requester_user_id=%s OR partner_user_id=%s) AND status='active'""",
                (user_id, user_id),
            )
            active_partners_count = int(cur.fetchone()[0] or 0)
            cur.execute(
                "SELECT COUNT(*) FROM attention_accountability_relationships WHERE partner_user_id=%s AND status='pending'",
                (user_id,),
            )
            pending_invitations_count = int(cur.fetchone()[0] or 0)
            cur.execute(
                """SELECT COUNT(*) FROM attention_prayer_requests
                WHERE status='open' AND (
                    owner_user_id=%s OR target_user_id=%s OR target_group_id IN (
                        SELECT group_id FROM attention_group_members WHERE user_id=%s AND status='active'
                    )
                )""",
                (user_id, user_id, user_id),
            )
            open_prayer_requests_count = int(cur.fetchone()[0] or 0)
            cur.execute("SELECT COUNT(*) FROM attention_group_members WHERE user_id=%s AND status='active'", (user_id,))
            active_groups_count = int(cur.fetchone()[0] or 0)
            cur.execute(
                """SELECT COUNT(*) FROM attention_challenge_participations p
                JOIN attention_group_challenges c ON c.id=p.challenge_id
                WHERE p.user_id=%s AND p.status='active' AND c.status='active'""",
                (user_id,),
            )
            active_challenges_count = int(cur.fetchone()[0] or 0)
            cur.execute(
                """SELECT COUNT(*) FROM attention_challenge_participations p
                JOIN attention_group_challenges c ON c.id=p.challenge_id
                WHERE p.user_id=%s AND p.status='active' AND c.status='active'
                  AND %s BETWEEN c.start_date AND c.end_date
                  AND NOT EXISTS (
                    SELECT 1 FROM attention_challenge_checkins cc
                    WHERE cc.challenge_id=c.id AND cc.user_id=%s AND cc.checkin_date=%s
                  )""",
                (user_id, today, user_id, today),
            )
            today_challenge_checkins_due = int(cur.fetchone()[0] or 0)
            privacy_settings = _get_or_create_privacy(cur, user_id)
        summary = calculate_daily_summary(entries)
        completed = [s for s in sessions if s.get("endedAt")]
        diagnosis_dto = _diagnosis_row_to_dto(diagnosis) if diagnosis else None
        diagnosis_result = (diagnosis_dto or {}).get("result") or {}
        primary_pattern = diagnosis_result.get("primaryPattern")
        if not primary_pattern and plans:
            pattern = next((item for item in pattern_definitions() if item.get("key") == plans[0].get("patternKey")), None)
            primary_pattern = {
                "patternKey": plans[0].get("patternKey"),
                "label": (pattern or {}).get("label") or plans[0].get("title"),
                "intensity": "active_plan",
            }
        return {
            "date": today.isoformat(),
            "covenant": covenant,
            "ledger": summary,
            "focus": {
                "completedSessions": len(completed),
                "totalActualMinutes": sum(int(s.get("actualMinutes") or 0) for s in completed),
                "interruptedSessions": len([s for s in sessions if s.get("interrupted")]),
                "activeSessionExists": any(not s.get("endedAt") for s in sessions),
            },
            "review": {"exists": bool(review), "review": _review_row_to_dto(review) if review else None},
            "diagnosis": ({
                **diagnosis_dto,
                "todayExists": True,
                "latestTitle": diagnosis_result.get("title"),
                "latestShortSummary": diagnosis_result.get("shortSummary"),
            } if diagnosis_dto else None),
            "warfare": {
                "activePlansCount": len(plans),
                "todayCheckinsCount": today_warfare_checkins,
                "todayCheckinsDue": max(0, len(plans) - today_warfare_checkins),
                "primaryPattern": primary_pattern,
            },
            "weekly": {
                "weekStart": week_start.isoformat(),
                "weekEnd": week_end.isoformat(),
                "reportExists": bool(weekly_row),
                "scoreAverage": weekly_row[0] if weekly_row else None,
                "scoreLabel": weekly_row[1] if weekly_row else "insufficient_data",
                "dataCompleteness": int(weekly_row[2] or 0) if weekly_row else 0,
                "topPulls": (_json_value(weekly_row[3]) or [])[:3] if weekly_row else [],
                "nextWeekPractice": weekly_row[4] if weekly_row else None,
            },
            "accountability": {
                "activePartnersCount": active_partners_count,
                "pendingInvitationsCount": pending_invitations_count,
                "openPrayerRequestsCount": open_prayer_requests_count,
            },
            "groups": {
                "activeGroupsCount": active_groups_count,
                "activeChallengesCount": active_challenges_count,
                "todayChallengeCheckinsDue": today_challenge_checkins_due,
            },
            "privacy": {
                "defaultPartnerVisibility": privacy_settings.get("defaultPartnerVisibility"),
                "defaultGroupVisibility": privacy_settings.get("defaultGroupVisibility"),
                "sensitiveProtectionEnabled": bool(privacy_settings.get("hideSensitiveCategories")),
            },
        }
    finally:
        _state["release_db"](conn)


def _attention_table_status(cur) -> dict[str, bool]:
    status = {}
    for table in ATTENTION_TABLES:
        rows = _safe_rows(cur, "SELECT to_regclass(%s)", (f"public.{table}",))
        status[table] = bool(rows and rows[0][0])
    return status


def _attention_health_payload(cur) -> dict:
    tables = _attention_table_status(cur)
    env = attention_environment_check(os.environ)
    content = content_library_summary(
        scripture_count=len(SCRIPTURE_LIBRARY),
        warfare_count=len(pattern_definitions()),
        challenge_count=len(CHALLENGE_TEMPLATES),
    )
    checks = {
        "database": "ok",
        "migrations": "ok" if all(tables.values()) else "missing_tables",
        "featureFlags": "ok" if env.get("ok") else "error",
        "scriptureLibrary": "ok" if content["scriptureCount"] > 0 else "missing",
        "warfarePatternLibrary": "ok" if content["warfarePatternCount"] >= 9 else "incomplete",
        "challengeTemplates": "ok" if content["challengeTemplateCount"] >= 9 else "incomplete",
        "aiFallback": "ok",
        "privacyDefaults": "ok" if DEFAULT_PRIVACY.get("defaultPartnerVisibility") == "status_only" else "warn",
    }
    return {
        "ok": all(value == "ok" for value in checks.values()),
        "version": ATTENTION_VERSION,
        "checks": checks,
        "featureFlags": env.get("featureFlags", {}),
        "environment": {"ok": env.get("ok"), "warnings": env.get("warnings", []), "errors": env.get("errors", [])},
        "tables": tables,
    }


@router.get("/health")
def get_attention_health() -> dict:
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            return _attention_health_payload(cur)
    finally:
        _state["release_db"](conn)


@router.get("/dashboard/summary")
def get_attention_dashboard_summary(request: Request) -> dict:
    return get_today_summary(request)


@router.get("/integration/routes")
def get_attention_route_registry(request: Request) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    routes = [
        route for route in ATTENTION_ROUTES
        if not route.get("requiresAdmin") or (_state.get("is_admin") and _state["is_admin"](user_id))
    ]
    return {"routes": routes}


def _aggregate_top_pulls(rows: list) -> list[dict]:
    counts: dict[str, int] = {}
    labels: dict[str, str] = {}
    for row in rows:
        items = _json_value(row[0]) or []
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            pull = str(item.get("pull") or "")
            if not pull:
                continue
            key = "sensitive" if pull in {"lust", "trauma", "addiction", "mental_health", "family_conflict"} else pull
            labels[key] = "敏感牵引" if key == "sensitive" else (item.get("label") or PULL_LABELS.get(key) or key)
            counts[key] = counts.get(key, 0) + int(item.get("count") or 1)
    return [
        {"pull": key, "label": labels.get(key, key), "count": count}
        for key, count in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:8]
    ]


def _attention_admin_overview(cur, start: date, end: date) -> dict:
    active_users = _safe_scalar(
        cur,
        """SELECT COUNT(DISTINCT user_id) FROM (
            SELECT user_id FROM attention_daily_covenants WHERE covenant_date BETWEEN %s AND %s
            UNION SELECT user_id FROM attention_entries WHERE entry_date BETWEEN %s AND %s
            UNION SELECT user_id FROM attention_focus_sessions WHERE started_at::date BETWEEN %s AND %s
            UNION SELECT user_id FROM attention_reviews WHERE review_date BETWEEN %s AND %s
        ) s""",
        (start, end, start, end, start, end, start, end),
    )
    category_rows = _safe_rows(
        cur,
        """SELECT category, COALESCE(SUM(duration_minutes),0)
        FROM attention_entries WHERE entry_date BETWEEN %s AND %s
        GROUP BY category""",
        (start, end),
    )
    top_pull_rows = _safe_rows(
        cur,
        "SELECT top_pulls FROM attention_weekly_reports WHERE week_start >= %s AND week_end <= %s AND status <> 'hidden'",
        (start, end),
    )
    metrics = {
        "activeAttentionUsers7d": active_users,
        "dailyCovenants7d": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_daily_covenants WHERE covenant_date BETWEEN %s AND %s", (start, end)),
        "focusSessions7d": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_focus_sessions WHERE started_at::date BETWEEN %s AND %s", (start, end)),
        "ledgerEntries7d": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_entries WHERE entry_date BETWEEN %s AND %s", (start, end)),
        "reviews7d": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_reviews WHERE review_date BETWEEN %s AND %s", (start, end)),
        "diagnoses7d": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_ai_diagnoses WHERE diagnosis_date BETWEEN %s AND %s", (start, end)),
        "warfarePlansActive": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_warfare_plans WHERE status='active'"),
        "weeklyReportsGenerated7d": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_weekly_reports WHERE week_start >= %s AND week_end <= %s AND status <> 'hidden'", (start, end)),
        "groupsActive": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_groups WHERE status='active'"),
        "challengesActive": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_group_challenges WHERE status='active'"),
        "prayerRequestsOpen": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_prayer_requests WHERE status='open'"),
        "crisisSafetyTriggers7d": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_ai_diagnoses WHERE safety_level='crisis' AND diagnosis_date BETWEEN %s AND %s", (start, end)),
    }
    category_distribution = {str(row[0]): int(row[1] or 0) for row in category_rows}
    return {
        "metrics": metrics,
        "categoryDistribution": category_distribution,
        "topPullsAggregate": _aggregate_top_pulls(top_pull_rows),
        "featureFlags": attention_feature_flags(os.environ),
    }


@router.get("/admin/overview")
def get_attention_admin_overview(request: Request) -> dict:
    _require_attention_admin(request)
    end = date.today()
    start = end - timedelta(days=6)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            overview = _attention_admin_overview(cur, start, end)
            overview["health"] = _attention_health_payload(cur)
        return overview
    finally:
        _state["release_db"](conn)


@router.get("/admin/audit")
def get_attention_admin_audit(request: Request) -> dict:
    _require_attention_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            tables = _attention_table_status(cur)
            return attention_audit_checks(
                route_count=len(router.routes),
                table_status=tables,
                admin_enabled=attention_feature_flags(os.environ).get("ATTENTION_ADMIN_ENABLED", True),
            )
    finally:
        _state["release_db"](conn)


@router.get("/admin/content-library")
def get_attention_admin_content_library(request: Request) -> dict:
    _require_attention_admin(request)
    return {
        "contentLibrary": content_library_summary(
            scripture_count=len(SCRIPTURE_LIBRARY),
            warfare_count=len(pattern_definitions()),
            challenge_count=len(CHALLENGE_TEMPLATES),
        ),
        "routeRegistry": ATTENTION_ROUTES,
        "releaseChecklist": release_checklist(),
    }


@router.get("/admin/reports")
def get_attention_admin_reports(
    request: Request,
    from_value: Optional[str] = Query(default=None, alias="from"),
    to_value: Optional[str] = Query(default=None, alias="to"),
) -> dict:
    _require_attention_admin(request)
    end = _parse_optional_date(to_value, "to", date.today())
    start = _parse_optional_date(from_value, "from", end - timedelta(days=29))
    if (end - start).days > 90:
        raise _json_error("VALIDATION_ERROR", "运营报表时间范围最多 90 天。", 400)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            overview = _attention_admin_overview(cur, start, end)
        return {"range": {"from": start.isoformat(), "to": end.isoformat()}, **overview}
    finally:
        _state["release_db"](conn)


# ---------------------------------------------------------------------------
# Batch 5: Weekly Reports / Stewardship Scores / Growth Curves
# ---------------------------------------------------------------------------

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


def _score_row_to_dto(row) -> dict:
    components = _json_value(row[6]) or []
    input_summary = _json_value(row[7]) or {}
    insights = _json_value(row[8]) or {}
    return {
        "id": str(row[0]),
        "date": _iso(row[1]),
        "score": row[2],
        "scoreLabel": row[3] or "insufficient_data",
        "dataCompleteness": int(row[4] or 0),
        "confidence": row[5] or "low",
        "components": components if isinstance(components, list) else [],
        "inputSummary": input_summary if isinstance(input_summary, dict) else {},
        "insights": insights if isinstance(insights, dict) else {},
        "generatedBy": row[9],
        "version": row[10],
        "createdAt": _iso(row[11]),
        "updatedAt": _iso(row[12]),
    }


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


def _upsert_daily_score(cur, user_id: str, dto: dict) -> dict:
    cur.execute(
        f"""INSERT INTO attention_daily_scores
        (user_id, score_date, score, score_label, data_completeness, confidence,
         component_scores, input_summary, insights, generated_by, version)
        VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,'rules','v1')
        ON CONFLICT (user_id, score_date) DO UPDATE SET
        score=EXCLUDED.score, score_label=EXCLUDED.score_label,
        data_completeness=EXCLUDED.data_completeness, confidence=EXCLUDED.confidence,
        component_scores=EXCLUDED.component_scores, input_summary=EXCLUDED.input_summary,
        insights=EXCLUDED.insights, generated_by='rules', version='v1'
        RETURNING {_SCORE_COLUMNS}""",
        (
            user_id,
            dto["date"],
            dto.get("score"),
            dto.get("scoreLabel"),
            dto.get("dataCompleteness"),
            dto.get("confidence"),
            _Json(dto.get("components") or []),
            _Json(dto.get("inputSummary") or {}),
            _Json(dto.get("insights") or {}),
        ),
    )
    return _score_row_to_dto(cur.fetchone())


def _compute_daily_score(cur, user_id: str, target: date) -> dict:
    dto = compute_daily_score(_load_daily_score_input(cur, user_id, target))
    return _upsert_daily_score(cur, user_id, dto)


def _get_or_compute_daily_score(cur, user_id: str, target: date, force: bool = False) -> dict:
    if not force:
        cur.execute(f"SELECT {_SCORE_COLUMNS} FROM attention_daily_scores WHERE user_id=%s AND score_date=%s LIMIT 1", (user_id, target))
        row = cur.fetchone()
        if row:
            return _score_row_to_dto(row)
    return _compute_daily_score(cur, user_id, target)


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


def _weekly_raw_summary(cur, user_id: str, start: date, end: date) -> dict:
    cur.execute(f"SELECT {_ENTRY_COLUMNS} FROM attention_entries WHERE user_id=%s AND entry_date BETWEEN %s AND %s", (user_id, start, end))
    entries = [_entry_row_to_dto(r) for r in cur.fetchall()]
    totals = category_totals(entries)
    cur.execute(f"SELECT {_FOCUS_COLUMNS} FROM attention_focus_sessions WHERE user_id=%s AND started_at::date BETWEEN %s AND %s", (user_id, start, end))
    sessions = [_focus_row_to_dto(r) for r in cur.fetchall()]
    cur.execute(f"SELECT {_REVIEW_COLUMNS} FROM attention_reviews WHERE user_id=%s AND review_date BETWEEN %s AND %s", (user_id, start, end))
    reviews = [_review_row_to_dto(r) for r in cur.fetchall()]
    cur.execute(f"SELECT {_SCORE_COLUMNS} FROM attention_daily_scores WHERE user_id=%s AND score_date BETWEEN %s AND %s", (user_id, start, end))
    stored_scores = [_score_row_to_dto(r) for r in cur.fetchall()]
    avg_values = [s["score"] for s in stored_scores if s.get("score") is not None]
    return {
        "scoreAverage": round(sum(avg_values) / len(avg_values)) if len(avg_values) >= 2 else None,
        "capturedMinutes": totals.get("captured", 0),
        "investedMinutes": totals.get("worship", 0) + totals.get("mission", 0) + totals.get("relationship", 0) + totals.get("restoration", 0),
        "focusMinutes": sum(int(s.get("actualMinutes") or 0) for s in sessions if s.get("endedAt")),
        "reviewDays": len({r.get("reviewDate") for r in reviews}),
    }


def _build_weekly_report_input(cur, user_id: str, start: date, end: date) -> dict:
    daily_scores = [_get_or_compute_daily_score(cur, user_id, day, force=True) for day in list_dates(start, end)]
    warfare_data = _load_warfare_data(cur, user_id, start, end)
    warfare_map = build_warfare_map(warfare_data, start, end)
    return {
        "dailyScores": daily_scores,
        "entries": warfare_data["entries"],
        "focusSessions": warfare_data["focusSessions"],
        "covenants": warfare_data["covenants"],
        "reviews": warfare_data["reviews"],
        "checkins": warfare_data["checkins"],
        "activePlans": warfare_data["activePlans"],
        "primaryPattern": warfare_map.get("primaryPattern"),
    }


def _upsert_weekly_report(cur, user_id: str, report: dict) -> dict:
    cm = report["categoryMinutes"]
    sections = report["reportSections"]
    cur.execute(
        f"""INSERT INTO attention_weekly_reports
        (user_id, week_start, week_end, worship_minutes, mission_minutes,
         relationship_minutes, restoration_minutes, captured_minutes,
         score_average, score_label, score_trend, data_completeness,
         daily_scores, category_minutes, category_percentages, focus_summary,
         covenant_summary, review_summary, warfare_summary, top_pulls,
         growth_signals, report_sections, summary, main_pattern,
         recommended_practice, next_week_practice, prayer, status, version)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s,'generated','v1')
        ON CONFLICT (user_id, week_start, week_end) DO UPDATE SET
        worship_minutes=EXCLUDED.worship_minutes, mission_minutes=EXCLUDED.mission_minutes,
        relationship_minutes=EXCLUDED.relationship_minutes, restoration_minutes=EXCLUDED.restoration_minutes,
        captured_minutes=EXCLUDED.captured_minutes, score_average=EXCLUDED.score_average,
        score_label=EXCLUDED.score_label, score_trend=EXCLUDED.score_trend,
        data_completeness=EXCLUDED.data_completeness, daily_scores=EXCLUDED.daily_scores,
        category_minutes=EXCLUDED.category_minutes, category_percentages=EXCLUDED.category_percentages,
        focus_summary=EXCLUDED.focus_summary, covenant_summary=EXCLUDED.covenant_summary,
        review_summary=EXCLUDED.review_summary, warfare_summary=EXCLUDED.warfare_summary,
        top_pulls=EXCLUDED.top_pulls, growth_signals=EXCLUDED.growth_signals,
        report_sections=EXCLUDED.report_sections, summary=EXCLUDED.summary,
        main_pattern=EXCLUDED.main_pattern, recommended_practice=EXCLUDED.recommended_practice,
        next_week_practice=EXCLUDED.next_week_practice, prayer=EXCLUDED.prayer,
        status='generated', version='v1'
        RETURNING {_REPORT_COLUMNS}""",
        (
            user_id,
            report["weekStart"],
            report["weekEnd"],
            cm.get("worship", 0),
            cm.get("mission", 0),
            cm.get("relationship", 0),
            cm.get("restoration", 0),
            cm.get("captured", 0),
            report.get("scoreAverage"),
            report.get("scoreLabel"),
            report.get("scoreTrend"),
            report.get("dataCompleteness"),
            _Json(report.get("dailyScores") or []),
            _Json(report.get("categoryMinutes") or {}),
            _Json(report.get("categoryPercentages") or {}),
            _Json(report.get("focusSummary") or {}),
            _Json(report.get("covenantSummary") or {}),
            _Json(report.get("reviewSummary") or {}),
            _Json(report.get("warfareSummary") or {}),
            _Json(report.get("topPulls") or []),
            _Json(report.get("growthSignals") or {}),
            _Json(sections),
            sections.get("weeklySummary"),
            sections.get("mainPattern"),
            report.get("nextWeekPractice"),
            report.get("nextWeekPractice"),
            report.get("prayer"),
        ),
    )
    return _report_row_to_dto(cur.fetchone())


def _week_range_for_request(request: Request, user: dict, week_start: Optional[str]) -> tuple[date, date]:
    target = _parse_optional_date(week_start, "weekStart", _local_date(request, user))
    return week_range_from_start(target)


@router.get("/scores/daily")
def get_daily_score(request: Request, date_value: Optional[str] = Query(default=None, alias="date"), force: bool = Query(default=False)) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    target = _parse_optional_date(date_value, "date", _local_date(request, user))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            score = _get_or_compute_daily_score(cur, user_id, target, force)
        conn.commit()
        return {"score": score}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise _json_error("INTERNAL_SERVER_ERROR", "暂时无法计算守心节奏指标，请稍后再试。", 500)
    finally:
        _state["release_db"](conn)


@router.post("/scores/daily")
def recompute_daily_score(request: Request, body: DailyScoreIn) -> dict:
    user = _require_user(request)
    target = _parse_optional_date(body.date, "date", _local_date(request, user))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            score = _compute_daily_score(cur, _db_user_id(user), target)
        conn.commit()
        return {"score": score}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise _json_error("INTERNAL_SERVER_ERROR", "暂时无法计算守心节奏指标，请稍后再试。", 500)
    finally:
        _state["release_db"](conn)


@router.get("/scores/range")
def get_daily_scores_range(
    request: Request,
    from_date: Optional[str] = Query(default=None, alias="from"),
    to_date: Optional[str] = Query(default=None, alias="to"),
) -> dict:
    user = _require_user(request)
    end = _parse_optional_date(to_date, "to", _local_date(request, user))
    start = _parse_optional_date(from_date, "from", end - timedelta(days=13))
    if start > end or (end - start).days > 89:
        raise _json_error("VALIDATION_ERROR", "分数范围最多 90 天。", 400)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            scores = [_get_or_compute_daily_score(cur, _db_user_id(user), day, False) for day in list_dates(start, end)]
        conn.commit()
        return {"scores": scores}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise _json_error("INTERNAL_SERVER_ERROR", "暂时无法计算守心节奏指标，请稍后再试。", 500)
    finally:
        _state["release_db"](conn)


@router.get("/reports/weekly")
def get_weekly_report(request: Request, week_start: Optional[str] = Query(default=None, alias="weekStart")) -> dict:
    user = _require_user(request)
    start, end = _week_range_for_request(request, user, week_start)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_REPORT_COLUMNS} FROM attention_weekly_reports WHERE user_id=%s AND week_start=%s AND week_end=%s AND status <> 'hidden' LIMIT 1",
                (_db_user_id(user), start, end),
            )
            row = cur.fetchone()
        return {"exists": bool(row), "report": _report_row_to_dto(row) if row else None, "weekStart": start.isoformat(), "weekEnd": end.isoformat()}
    finally:
        _state["release_db"](conn)


@router.post("/reports/weekly/generate")
def generate_weekly_report(request: Request, body: WeeklyReportGenerateIn) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    start, end = _week_range_for_request(request, user, body.week_start)
    prev_start, prev_end = previous_week_range(start)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if not body.force_regenerate:
                cur.execute(
                    f"SELECT {_REPORT_COLUMNS} FROM attention_weekly_reports WHERE user_id=%s AND week_start=%s AND week_end=%s AND status <> 'hidden' LIMIT 1",
                    (user_id, start, end),
                )
                row = cur.fetchone()
                if row:
                    return {"report": _report_row_to_dto(row)}
            previous = _weekly_raw_summary(cur, user_id, prev_start, prev_end)
            report_input = _build_weekly_report_input(cur, user_id, start, end)
            report = build_weekly_report(start, end, report_input, previous)
            saved = _upsert_weekly_report(cur, user_id, report)
        conn.commit()
        return {"report": saved}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise _json_error("INTERNAL_SERVER_ERROR", "生成守心周报时遇到问题，请稍后再试。", 500)
    finally:
        _state["release_db"](conn)


@router.get("/reports/weekly/history")
def list_weekly_reports(request: Request, limit: int = Query(default=12, ge=1, le=52)) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_REPORT_COLUMNS} FROM attention_weekly_reports WHERE user_id=%s AND status <> 'hidden' ORDER BY week_start DESC LIMIT %s",
                (user_id, limit),
            )
            rows = cur.fetchall()
        return {"reports": [_report_row_to_dto(r) for r in rows]}
    finally:
        _state["release_db"](conn)


@router.get("/reports/weekly/{report_id}")
def get_weekly_report_by_id(report_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_REPORT_COLUMNS} FROM attention_weekly_reports WHERE id=%s AND user_id=%s AND status <> 'hidden'", (report_id, user_id))
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这份周报。", 404)
        return {"report": _report_row_to_dto(row)}
    finally:
        _state["release_db"](conn)


@router.delete("/reports/weekly/{report_id}")
def hide_weekly_report(report_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE attention_weekly_reports SET status='hidden' WHERE id=%s AND user_id=%s", (report_id, user_id))
            if cur.rowcount == 0:
                raise _json_error("NOT_FOUND", "没有找到这份周报。", 404)
        conn.commit()
        return {"ok": True}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/growth")
def get_growth_trends(
    request: Request,
    days: int = Query(default=30),
    from_date: Optional[str] = Query(default=None, alias="from"),
    to_date: Optional[str] = Query(default=None, alias="to"),
) -> dict:
    user = _require_user(request)
    today = _local_date(request, user)
    if from_date or to_date:
        end = _parse_optional_date(to_date, "to", today)
        start = _parse_optional_date(from_date, "from", end - timedelta(days=29))
    else:
        if days not in {30, 60, 90}:
            raise _json_error("VALIDATION_ERROR", "days 只能是 30、60 或 90。", 400)
        end = today
        start = end - timedelta(days=days - 1)
    if start > end or (end - start).days > 89:
        raise _json_error("VALIDATION_ERROR", "成长曲线范围最多 90 天。", 400)
    user_id = _db_user_id(user)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            points = []
            for day in list_dates(start, end):
                score = _get_or_compute_daily_score(cur, user_id, day, False)
                input_summary = score.get("inputSummary") or {}
                cm = input_summary
                category_minutes = input_summary.get("categoryMinutes") or {}
                points.append({
                    "date": day.isoformat(),
                    "score": score.get("score"),
                    "dataCompleteness": score.get("dataCompleteness", 0),
                    "investedMinutes": cm.get("investedMinutes", 0),
                    "capturedMinutes": cm.get("capturedMinutes", 0),
                    "capturedRatio": cm.get("capturedRatio"),
                    "worshipMinutes": category_minutes.get("worship", 0),
                    "missionMinutes": category_minutes.get("mission", 0),
                    "relationshipMinutes": category_minutes.get("relationship", 0),
                    "restorationMinutes": category_minutes.get("restoration", 0),
                    "focusMinutes": cm.get("focusMinutes", 0),
                    "reviewCompleted": bool(cm.get("reviewExists")),
                    "planCheckins": cm.get("planCheckinsCount", 0),
                    "topPulls": cm.get("topPulls", []),
                })
        conn.commit()
        return {"trend": {"range": {"from": start.isoformat(), "to": end.isoformat(), "days": (end - start).days + 1}, "points": points, "summary": growth_summary(points)}}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise _json_error("INTERNAL_SERVER_ERROR", "暂时无法加载成长曲线，请稍后再试。", 500)
    finally:
        _state["release_db"](conn)


# ---------------------------------------------------------------------------
# Batch 6: Accountability Partners / Groups / Privacy
# ---------------------------------------------------------------------------

_PRIVACY_COLUMNS = """
    id, user_id, default_partner_visibility, default_group_visibility,
    default_challenge_visibility, share_scores_with_partners,
    share_scores_with_groups, share_weekly_report_summary,
    share_warfare_plan_progress, share_prayer_requests,
    hide_sensitive_categories, allow_partner_reminders,
    allow_group_challenge_reminders, require_preview_before_sharing,
    created_at, updated_at
"""

_REL_COLUMNS = """
    id, requester_user_id, partner_user_id, status, direction_label,
    requester_message, requester_permissions, partner_permissions,
    accepted_at, declined_at, paused_at, ended_at, created_at, updated_at
"""

_GROUP_COLUMNS = """
    id, owner_user_id, name, description, group_type, invite_code,
    invite_enabled, default_member_visibility, guidelines, status,
    created_at, updated_at
"""

_GROUP_COLUMNS_G = """
    g.id, g.owner_user_id, g.name, g.description, g.group_type, g.invite_code,
    g.invite_enabled, g.default_member_visibility, g.guidelines, g.status,
    g.created_at, g.updated_at
"""

_MEMBER_COLUMNS = """
    id, group_id, user_id, role, status, visibility_level, permissions,
    joined_at, left_at, removed_at, created_at, updated_at
"""

_CHALLENGE_COLUMNS = """
    id, group_id, created_by_user_id, template_key, title, description,
    challenge_type, start_date, end_date, target_days, target_minutes,
    checkin_prompt, privacy_mode, allow_comments, allow_prayer_requests,
    status, created_at, updated_at
"""

_CHALLENGE_COLUMNS_C = """
    c.id, c.group_id, c.created_by_user_id, c.template_key, c.title, c.description,
    c.challenge_type, c.start_date, c.end_date, c.target_days, c.target_minutes,
    c.checkin_prompt, c.privacy_mode, c.allow_comments, c.allow_prayer_requests,
    c.status, c.created_at, c.updated_at
"""

_CHALLENGE_CHECKIN_COLUMNS = """
    id, challenge_id, user_id, checkin_date, completed, value_minutes,
    value_count, reflection, prayer_request_id, visibility_level,
    created_at, updated_at
"""

_SHARE_COLUMNS = """
    id, owner_user_id, scope, target_user_id, target_group_id, source_type,
    source_id, title, summary, payload, visibility_level, sensitive_redactions,
    revoked_at, created_at, updated_at
"""

_PRAYER_COLUMNS = """
    id, owner_user_id, target_user_id, target_group_id, title, body, category,
    visibility_level, is_sensitive, status, answered_note, created_at,
    updated_at, closed_at
"""


def _pair_key(a: str, b: str) -> str:
    left, right = sorted([a.strip().lower(), b.strip().lower()])
    return f"{left}::{right}"


def _display_user(cur, user_id: Optional[str]) -> dict:
    if not user_id:
        return {"id": None, "displayName": None, "avatarUrl": None}
    cur.execute("SELECT email, nickname, avatar FROM users WHERE LOWER(email)=LOWER(%s) LIMIT 1", (user_id,))
    row = cur.fetchone()
    if not row:
        return {"id": user_id, "displayName": user_id.split("@")[0], "avatarUrl": None}
    return {"id": row[0], "displayName": row[1] or row[0].split("@")[0], "avatarUrl": row[2]}


def _resolve_user_id(cur, value: str) -> str:
    ident = (value or "").strip().lower()
    if not ident:
        raise _json_error("VALIDATION_ERROR", "请选择守望对象。", 400)
    cur.execute("SELECT email FROM users WHERE LOWER(email)=LOWER(%s) OR id::text=%s LIMIT 1", (ident, ident))
    row = cur.fetchone()
    if not row:
        raise _json_error("NOT_FOUND", "没有找到这位用户。", 404)
    return row[0]


def _privacy_row_to_dto(row) -> dict:
    return {
        "userId": row[1],
        "defaultPartnerVisibility": row[2],
        "defaultGroupVisibility": row[3],
        "defaultChallengeVisibility": row[4],
        "shareScoresWithPartners": bool(row[5]),
        "shareScoresWithGroups": bool(row[6]),
        "shareWeeklyReportSummary": bool(row[7]),
        "shareWarfarePlanProgress": bool(row[8]),
        "sharePrayerRequests": bool(row[9]),
        "hideSensitiveCategories": list(row[10] or []),
        "allowPartnerReminders": bool(row[11]),
        "allowGroupChallengeReminders": bool(row[12]),
        "requirePreviewBeforeSharing": bool(row[13]),
        "createdAt": _iso(row[14]),
        "updatedAt": _iso(row[15]),
    }


def _get_or_create_privacy(cur, user_id: str) -> dict:
    cur.execute(f"SELECT {_PRIVACY_COLUMNS} FROM attention_privacy_settings WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    if not row:
        cur.execute(
            f"""INSERT INTO attention_privacy_settings
            (user_id, default_partner_visibility, default_group_visibility,
             default_challenge_visibility, share_scores_with_partners,
             share_scores_with_groups, share_weekly_report_summary,
             share_warfare_plan_progress, share_prayer_requests,
             hide_sensitive_categories, allow_partner_reminders,
             allow_group_challenge_reminders, require_preview_before_sharing)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING {_PRIVACY_COLUMNS}""",
            (
                user_id,
                DEFAULT_PRIVACY["defaultPartnerVisibility"],
                DEFAULT_PRIVACY["defaultGroupVisibility"],
                DEFAULT_PRIVACY["defaultChallengeVisibility"],
                DEFAULT_PRIVACY["shareScoresWithPartners"],
                DEFAULT_PRIVACY["shareScoresWithGroups"],
                DEFAULT_PRIVACY["shareWeeklyReportSummary"],
                DEFAULT_PRIVACY["shareWarfarePlanProgress"],
                DEFAULT_PRIVACY["sharePrayerRequests"],
                DEFAULT_PRIVACY["hideSensitiveCategories"],
                DEFAULT_PRIVACY["allowPartnerReminders"],
                DEFAULT_PRIVACY["allowGroupChallengeReminders"],
                DEFAULT_PRIVACY["requirePreviewBeforeSharing"],
            ),
        )
        row = cur.fetchone()
    return _privacy_row_to_dto(row)


def _permission_dto(perms: dict, relationship_id: str) -> dict:
    merged = default_partner_permissions(perms or {})
    return {"relationshipId": relationship_id, **merged, "updatedAt": _iso(_utc_now())}


def _relationship_row_to_dto(cur, row, current_user_id: str) -> dict:
    rid = str(row[0])
    requester = row[1]
    partner = row[2]
    current_role = "requester" if requester == current_user_id else "partner"
    return {
        "id": rid,
        "requesterUser": _display_user(cur, requester),
        "partnerUser": _display_user(cur, partner),
        "status": row[3],
        "currentUserRole": current_role,
        "directionLabel": row[4],
        "requesterMessage": row[5],
        "permissionsForCurrentUserSharing": _permission_dto(_json_value(row[6] if current_role == "requester" else row[7]) or {}, rid),
        "permissionsForPartnerSharing": _permission_dto(_json_value(row[7] if current_role == "requester" else row[6]) or {}, rid),
        "acceptedAt": _iso(row[8]),
        "declinedAt": _iso(row[9]),
        "pausedAt": _iso(row[10]),
        "endedAt": _iso(row[11]),
        "createdAt": _iso(row[12]),
        "updatedAt": _iso(row[13]),
    }


def _require_relationship(cur, user_id: str, relationship_id: str):
    cur.execute(
        f"SELECT {_REL_COLUMNS} FROM attention_accountability_relationships WHERE id=%s AND (requester_user_id=%s OR partner_user_id=%s)",
        (relationship_id, user_id, user_id),
    )
    row = cur.fetchone()
    if not row:
        raise _json_error("NOT_FOUND", "没有找到这段守望关系。", 404)
    return row


def _has_active_relationship(cur, user_a: str, user_b: str) -> bool:
    cur.execute(
        """SELECT id FROM attention_accountability_relationships
        WHERE pair_key=%s AND status='active' LIMIT 1""",
        (_pair_key(user_a, user_b),),
    )
    return bool(cur.fetchone())


def _member_row(cur, group_id: str, user_id: str):
    cur.execute(f"SELECT {_MEMBER_COLUMNS} FROM attention_group_members WHERE group_id=%s AND user_id=%s AND status='active'", (group_id, user_id))
    return cur.fetchone()


def _require_group_member(cur, group_id: str, user_id: str):
    row = _member_row(cur, group_id, user_id)
    if not row:
        raise _json_error("NOT_FOUND", "没有找到这个守心小组，或你尚未加入。", 404)
    return row


def _require_group_manager(cur, group_id: str, user_id: str):
    member = _require_group_member(cur, group_id, user_id)
    if member[3] not in {"owner", "leader"}:
        raise _json_error("FORBIDDEN", "只有小组 owner/leader 可以操作。", 403)
    return member


def _require_group_owner(cur, group_id: str, user_id: str):
    member = _require_group_member(cur, group_id, user_id)
    if member[3] != "owner":
        raise _json_error("FORBIDDEN", "只有小组 owner 可以操作。", 403)
    return member


def _group_row_to_dto(cur, row, current_user_id: str) -> dict:
    gid = str(row[0])
    cur.execute("SELECT role, status FROM attention_group_members WHERE group_id=%s AND user_id=%s LIMIT 1", (gid, current_user_id))
    mine = cur.fetchone()
    cur.execute("SELECT COUNT(*) FROM attention_group_members WHERE group_id=%s AND status='active'", (gid,))
    members_count = int(cur.fetchone()[0] or 0)
    cur.execute("SELECT COUNT(*) FROM attention_group_challenges WHERE group_id=%s AND status='active'", (gid,))
    active_challenges = int(cur.fetchone()[0] or 0)
    return {
        "id": gid,
        "ownerUserId": row[1],
        "name": row[2],
        "description": row[3],
        "groupType": row[4],
        "inviteCode": row[5],
        "inviteEnabled": bool(row[6]),
        "defaultMemberVisibility": row[7],
        "guidelines": row[8],
        "status": row[9],
        "currentUserRole": mine[0] if mine else None,
        "currentUserMembershipStatus": mine[1] if mine else None,
        "membersCount": members_count,
        "activeChallengesCount": active_challenges,
        "createdAt": _iso(row[10]),
        "updatedAt": _iso(row[11]),
    }


def _member_row_to_dto(cur, row) -> dict:
    return {
        "id": str(row[0]),
        "groupId": str(row[1]),
        "user": _display_user(cur, row[2]),
        "role": row[3],
        "status": row[4],
        "visibilityLevel": row[5],
        "joinedAt": _iso(row[7]),
        "createdAt": _iso(row[10]),
        "updatedAt": _iso(row[11]),
    }


def _challenge_row_to_dict(row) -> dict:
    return {
        "id": str(row[0]),
        "groupId": str(row[1]),
        "createdByUserId": row[2],
        "templateKey": row[3],
        "title": row[4],
        "description": row[5],
        "challengeType": row[6],
        "startDate": _iso(row[7]),
        "endDate": _iso(row[8]),
        "targetDays": row[9],
        "targetMinutes": row[10],
        "checkinPrompt": row[11],
        "privacyMode": row[12],
        "allowComments": bool(row[13]),
        "allowPrayerRequests": bool(row[14]),
        "status": row[15],
        "createdAt": _iso(row[16]),
        "updatedAt": _iso(row[17]),
    }


def _challenge_participants(cur, challenge_id: str) -> list[dict]:
    cur.execute("SELECT user_id, status, joined_at FROM attention_challenge_participations WHERE challenge_id=%s ORDER BY joined_at ASC", (challenge_id,))
    return [{"userId": r[0], "status": r[1], "joinedAt": _iso(r[2])} for r in cur.fetchall()]


def _challenge_checkins(cur, challenge_id: str) -> list[dict]:
    cur.execute(f"SELECT {_CHALLENGE_CHECKIN_COLUMNS} FROM attention_challenge_checkins WHERE challenge_id=%s ORDER BY checkin_date DESC", (challenge_id,))
    return [_challenge_checkin_row_to_dto(r, include_reflection=True) for r in cur.fetchall()]


def _challenge_row_to_dto(cur, row, current_user_id: str) -> dict:
    data = _challenge_row_to_dict(row)
    participants = _challenge_participants(cur, data["id"])
    checkins = _challenge_checkins(cur, data["id"])
    cur.execute("SELECT status, joined_at FROM attention_challenge_participations WHERE challenge_id=%s AND user_id=%s", (data["id"], current_user_id))
    mine = cur.fetchone()
    data["currentUserParticipation"] = {"status": mine[0], "joinedAt": _iso(mine[1])} if mine else None
    data["progress"] = challenge_progress(challenge=data, participants=participants, checkins=checkins, current_user_id=current_user_id, today=date.today())
    return data


def _challenge_checkin_row_to_dto(row, include_reflection: bool = False) -> dict:
    return {
        "id": str(row[0]),
        "challengeId": str(row[1]),
        "userId": row[2],
        "checkinDate": _iso(row[3]),
        "completed": bool(row[4]),
        "valueMinutes": row[5],
        "valueCount": row[6],
        "reflection": row[7] if include_reflection else None,
        "prayerRequestId": str(row[8]) if row[8] else None,
        "visibilityLevel": row[9],
        "createdAt": _iso(row[10]),
        "updatedAt": _iso(row[11]),
    }


def _share_row_to_dto(cur, row) -> dict:
    return {
        "id": str(row[0]),
        "ownerUser": _display_user(cur, row[1]),
        "scope": row[2],
        "targetUserId": row[3],
        "targetGroupId": str(row[4]) if row[4] else None,
        "sourceType": row[5],
        "sourceId": row[6],
        "title": row[7],
        "summary": row[8],
        "payload": _json_value(row[9]) or {},
        "visibilityLevel": row[10],
        "sensitiveRedactions": list(row[11] or []),
        "revokedAt": _iso(row[12]),
        "createdAt": _iso(row[13]),
        "updatedAt": _iso(row[14]),
    }


def _prayer_row_to_dto(cur, row, current_user_id: str) -> dict:
    prayer_id = str(row[0])
    cur.execute("SELECT COUNT(*) FROM attention_prayer_marks WHERE prayer_request_id=%s", (prayer_id,))
    count = int(cur.fetchone()[0] or 0)
    cur.execute("SELECT id FROM attention_prayer_marks WHERE prayer_request_id=%s AND user_id=%s", (prayer_id, current_user_id))
    prayed = bool(cur.fetchone())
    is_owner = row[1] == current_user_id
    is_sensitive = bool(row[8])
    may_see_body = is_owner or (row[7] == "selected_details" and not is_sensitive)
    return {
        "id": prayer_id,
        "ownerUser": _display_user(cur, row[1]),
        "targetUserId": row[2],
        "targetGroupId": str(row[3]) if row[3] else None,
        "title": row[4] if is_owner or not is_sensitive else "一项敏感代祷需要",
        "body": row[5] if may_see_body else None,
        "category": row[6],
        "visibilityLevel": row[7],
        "isSensitive": bool(row[8]),
        "status": row[9],
        "answeredNote": row[10] if is_owner else None,
        "prayedCount": count,
        "hasCurrentUserPrayed": prayed,
        "createdAt": _iso(row[11]),
        "updatedAt": _iso(row[12]),
        "closedAt": _iso(row[13]),
    }


def _can_access_prayer(cur, user_id: str, row) -> bool:
    if row[1] == user_id or row[2] == user_id:
        return True
    if row[3]:
        return bool(_member_row(cur, str(row[3]), user_id))
    return False


def _load_share_source(cur, user_id: str, body: ShareCreateIn) -> dict:
    if body.source_type == "weekly_report" and body.source_id:
        cur.execute(f"SELECT {_REPORT_COLUMNS} FROM attention_weekly_reports WHERE id=%s AND user_id=%s AND status <> 'hidden'", (body.source_id, user_id))
        row = cur.fetchone()
        if not row:
            raise _json_error("NOT_FOUND", "没有找到这份周报。", 404)
        return _report_row_to_dto(row)
    if body.source_type == "warfare_plan" and body.source_id:
        cur.execute(f"SELECT {_PLAN_COLUMNS} FROM attention_warfare_plans WHERE id=%s AND user_id=%s", (body.source_id, user_id))
        row = cur.fetchone()
        if not row:
            raise _json_error("NOT_FOUND", "没有找到这条守心计划。", 404)
        return _plan_row_to_dto(row)
    if body.source_type == "daily_summary":
        target = _local_date_from_source(body.source_id)
        score_input = _load_daily_score_input(cur, user_id, target)
        return {
            "date": target.isoformat(),
            "covenant": score_input.get("covenant"),
            "focus": {"totalActualMinutes": score_input.get("focusMinutes", 0)},
            "review": {"exists": bool(score_input.get("review"))},
        }
    if body.source_type == "challenge_progress" and body.source_id:
        cur.execute(f"SELECT {_CHALLENGE_COLUMNS} FROM attention_group_challenges WHERE id=%s", (body.source_id,))
        row = cur.fetchone()
        if not row:
            raise _json_error("NOT_FOUND", "没有找到这个挑战。", 404)
        return _challenge_row_to_dto(cur, row, user_id)
    if body.source_type == "prayer_request" and body.source_id:
        cur.execute(f"SELECT {_PRAYER_COLUMNS} FROM attention_prayer_requests WHERE id=%s AND owner_user_id=%s", (body.source_id, user_id))
        row = cur.fetchone()
        if not row:
            raise _json_error("NOT_FOUND", "没有找到这个代祷请求。", 404)
        return _prayer_row_to_dto(cur, row, user_id)
    return {"customMessage": body.custom_message}


def _local_date_from_source(value: Optional[str]) -> date:
    if not value:
        return date.today()
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except Exception:
        return date.today()


@router.get("/privacy")
def get_attention_privacy(request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            settings = _get_or_create_privacy(cur, user_id)
        conn.commit()
        return {"settings": settings}
    finally:
        _state["release_db"](conn)


@router.put("/privacy")
def update_attention_privacy(request: Request, body: PrivacySettingsIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    data = sanitize_privacy_update(body.model_dump(by_alias=True, exclude_unset=True))
    if not data:
        raise _json_error("VALIDATION_ERROR", "没有可更新的隐私设置。", 400)
    field_map = {
        "defaultPartnerVisibility": "default_partner_visibility",
        "defaultGroupVisibility": "default_group_visibility",
        "defaultChallengeVisibility": "default_challenge_visibility",
        "shareScoresWithPartners": "share_scores_with_partners",
        "shareScoresWithGroups": "share_scores_with_groups",
        "shareWeeklyReportSummary": "share_weekly_report_summary",
        "shareWarfarePlanProgress": "share_warfare_plan_progress",
        "sharePrayerRequests": "share_prayer_requests",
        "hideSensitiveCategories": "hide_sensitive_categories",
        "allowPartnerReminders": "allow_partner_reminders",
        "allowGroupChallengeReminders": "allow_group_challenge_reminders",
        "requirePreviewBeforeSharing": "require_preview_before_sharing",
    }
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _get_or_create_privacy(cur, user_id)
            assignments = ", ".join([f"{field_map[k]}=%s" for k in data])
            cur.execute(
                f"UPDATE attention_privacy_settings SET {assignments} WHERE user_id=%s RETURNING {_PRIVACY_COLUMNS}",
                list(data.values()) + [user_id],
            )
            settings = _privacy_row_to_dto(cur.fetchone())
        conn.commit()
        return {"settings": settings}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/accountability/partners")
def list_attention_partners(request: Request, status: str = Query(default="active")) -> dict:
    user_id = _db_user_id(_require_user(request))
    if status not in PARTNER_STATUSES | {"all"}:
        raise _json_error("VALIDATION_ERROR", "status 不合法。", 400)
    clause = "(requester_user_id=%s OR partner_user_id=%s)" if status == "all" else "(requester_user_id=%s OR partner_user_id=%s) AND status=%s"
    params = (user_id, user_id) if status == "all" else (user_id, user_id, status)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_REL_COLUMNS} FROM attention_accountability_relationships WHERE {clause} ORDER BY created_at DESC", params)
            rows = cur.fetchall()
            return {"relationships": [_relationship_row_to_dto(cur, r, user_id) for r in rows]}
    finally:
        _state["release_db"](conn)


@router.post("/accountability/partners/invite")
def invite_attention_partner(request: Request, body: PartnerInviteIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            partner_id = _resolve_user_id(cur, body.partner_user_id)
            if partner_id == user_id:
                raise _json_error("VALIDATION_ERROR", "不能邀请自己成为守望伙伴。", 400)
            perms = default_partner_permissions(body.permissions)
            cur.execute(
                f"""INSERT INTO attention_accountability_relationships
                (requester_user_id, partner_user_id, pair_key, requester_message,
                 requester_permissions, partner_permissions)
                VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb)
                RETURNING {_REL_COLUMNS}""",
                (user_id, partner_id, _pair_key(user_id, partner_id), body.message, _Json(perms), _Json(default_partner_permissions())),
            )
            row = cur.fetchone()
            relationship = _relationship_row_to_dto(cur, row, user_id)
        conn.commit()
        return {"relationship": relationship}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        if "uniq_attention_accountability_pair_active" in str(exc):
            raise _json_error("RELATIONSHIP_EXISTS", "你们已经有进行中的守望关系或邀请。", 409)
        raise
    finally:
        _state["release_db"](conn)


@router.get("/accountability/partners/invitations")
def list_attention_partner_invitations(request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_REL_COLUMNS} FROM attention_accountability_relationships WHERE status='pending' AND partner_user_id=%s ORDER BY created_at DESC", (user_id,))
            received = [_relationship_row_to_dto(cur, r, user_id) for r in cur.fetchall()]
            cur.execute(f"SELECT {_REL_COLUMNS} FROM attention_accountability_relationships WHERE status='pending' AND requester_user_id=%s ORDER BY created_at DESC", (user_id,))
            sent = [_relationship_row_to_dto(cur, r, user_id) for r in cur.fetchall()]
        return {"received": received, "sent": sent}
    finally:
        _state["release_db"](conn)


@router.put("/accountability/partners/{relationship_id}")
def update_attention_partner_relationship(relationship_id: str, request: Request, body: PartnerActionIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    action = body.action
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _require_relationship(cur, user_id, relationship_id)
            requester, partner, status = row[1], row[2], row[3]
            if action in {"accept", "decline"} and user_id != partner:
                raise _json_error("FORBIDDEN", "只有被邀请方可以接受或拒绝。", 403)
            updates = {
                "accept": ("active", "accepted_at=now(), declined_at=NULL, paused_at=NULL, ended_at=NULL"),
                "decline": ("declined", "declined_at=now()"),
                "pause": ("paused", "paused_at=now()"),
                "resume": ("active", "paused_at=NULL"),
                "end": ("ended", "ended_at=now()"),
            }
            if action not in updates:
                raise _json_error("VALIDATION_ERROR", "action 不合法。", 400)
            if action == "accept" and status != "pending":
                raise _json_error("VALIDATION_ERROR", "只能接受待处理邀请。", 400)
            next_status, extra = updates[action]
            cur.execute(
                f"UPDATE attention_accountability_relationships SET status=%s, {extra} WHERE id=%s RETURNING {_REL_COLUMNS}",
                (next_status, relationship_id),
            )
            updated = cur.fetchone()
            relationship = _relationship_row_to_dto(cur, updated, user_id)
        conn.commit()
        return {"relationship": relationship}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/accountability/partners/{relationship_id}/permissions")
def get_attention_partner_permissions(relationship_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _require_relationship(cur, user_id, relationship_id)
            perms = _json_value(row[6] if row[1] == user_id else row[7]) or {}
        return {"permissions": _permission_dto(perms, relationship_id)}
    finally:
        _state["release_db"](conn)


@router.put("/accountability/partners/{relationship_id}/permissions")
def update_attention_partner_permissions(relationship_id: str, request: Request, body: PartnerPermissionsIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    data = body.model_dump(by_alias=True, exclude_unset=True)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _require_relationship(cur, user_id, relationship_id)
            column = "requester_permissions" if row[1] == user_id else "partner_permissions"
            current = _json_value(row[6] if row[1] == user_id else row[7]) or {}
            next_perms = default_partner_permissions({**current, **data})
            cur.execute(
                f"UPDATE attention_accountability_relationships SET {column}=%s::jsonb WHERE id=%s RETURNING {_REL_COLUMNS}",
                (_Json(next_perms), relationship_id),
            )
            updated = cur.fetchone()
            relationship = _relationship_row_to_dto(cur, updated, user_id)
        conn.commit()
        return {"permissions": _permission_dto(next_perms, relationship_id), "relationship": relationship}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


def _share_targets_for_user(cur, user_id: str) -> tuple[list[str], list[str]]:
    cur.execute(
        "SELECT group_id FROM attention_group_members WHERE user_id=%s AND status='active'",
        (user_id,),
    )
    groups = [str(r[0]) for r in cur.fetchall()]
    cur.execute(
        """SELECT requester_user_id, partner_user_id FROM attention_accountability_relationships
        WHERE (requester_user_id=%s OR partner_user_id=%s) AND status='active'""",
        (user_id, user_id),
    )
    partners = []
    for requester, partner in cur.fetchall():
        partners.append(partner if requester == user_id else requester)
    return partners, groups


def _require_share_access(cur, user_id: str, share_id: str):
    cur.execute(f"SELECT {_SHARE_COLUMNS} FROM attention_share_snapshots WHERE id=%s", (share_id,))
    row = cur.fetchone()
    if not row:
        raise _json_error("NOT_FOUND", "没有找到这份分享。", 404)
    if row[1] == user_id:
        return row
    if row[12]:
        raise _json_error("NOT_FOUND", "没有找到这份分享。", 404)
    if row[3] == user_id:
        if row[2] == "partner" and not _has_active_relationship(cur, row[1], user_id):
            raise _json_error("NOT_FOUND", "没有找到这份分享。", 404)
        return row
    if row[4] and _member_row(cur, str(row[4]), user_id):
        return row
    raise _json_error("FORBIDDEN", "你没有权限查看这份分享。", 403)


def _challenge_access_row(cur, challenge_id: str, group_id: Optional[str], user_id: str):
    if group_id:
        _require_group_member(cur, group_id, user_id)
        cur.execute(f"SELECT {_CHALLENGE_COLUMNS} FROM attention_group_challenges WHERE id=%s AND group_id=%s", (challenge_id, group_id))
    else:
        cur.execute(f"SELECT {_CHALLENGE_COLUMNS} FROM attention_group_challenges WHERE id=%s", (challenge_id,))
    row = cur.fetchone()
    if not row:
        raise _json_error("NOT_FOUND", "没有找到这个挑战。", 404)
    _require_group_member(cur, str(row[1]), user_id)
    return row


def _member_participant_summary(cur, challenge_id: str, user_id: str) -> dict:
    cur.execute(
        f"SELECT {_CHALLENGE_CHECKIN_COLUMNS} FROM attention_challenge_checkins WHERE challenge_id=%s AND user_id=%s ORDER BY checkin_date DESC",
        (challenge_id, user_id),
    )
    checkins = [_challenge_checkin_row_to_dto(r, include_reflection=False) for r in cur.fetchall()]
    completed = [c for c in checkins if c.get("completed")]
    return {
        "user": _display_user(cur, user_id),
        "checkinsCount": len(checkins),
        "completedDays": len(completed),
        "lastCheckinDate": checkins[0]["checkinDate"] if checkins else None,
        "encouragementText": "正在同行操练。" if checkins else "还没有记录，适合温柔提醒。",
    }


@router.get("/accountability/shares")
def list_attention_shares(request: Request, box: str = Query(default="received")) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if box == "sent":
                cur.execute(f"SELECT {_SHARE_COLUMNS} FROM attention_share_snapshots WHERE owner_user_id=%s ORDER BY created_at DESC LIMIT 100", (user_id,))
            else:
                partners, groups = _share_targets_for_user(cur, user_id)
                partner_ids = tuple(partners) or ("",)
                group_ids = tuple(groups) or ("",)
                cur.execute(
                    f"""SELECT {_SHARE_COLUMNS} FROM attention_share_snapshots
                    WHERE revoked_at IS NULL AND (
                      (target_user_id=%s AND (scope<>'partner' OR owner_user_id IN %s))
                      OR target_group_id::text IN %s
                    )
                    ORDER BY created_at DESC LIMIT 100""",
                    (user_id, partner_ids, group_ids),
                )
            shares = [_share_row_to_dto(cur, row) for row in cur.fetchall()]
        return {"shares": shares}
    finally:
        _state["release_db"](conn)


def _prepare_attention_share(cur, user_id: str, body: ShareCreateIn) -> dict:
    if body.scope not in SHARE_SCOPES:
        raise _json_error("VALIDATION_ERROR", "scope 不合法。", 400)
    if body.source_type not in SHARE_SOURCE_TYPES:
        raise _json_error("VALIDATION_ERROR", "sourceType 不合法。", 400)
    visibility = sanitize_visibility(body.visibility_level)
    settings = _get_or_create_privacy(cur, user_id)
    target_user_id = _resolve_user_id(cur, body.target_user_id) if body.target_user_id else None
    target_group_id = body.target_group_id
    if body.scope == "partner":
        if not target_user_id or not _has_active_relationship(cur, user_id, target_user_id):
            raise _json_error("FORBIDDEN", "只能分享给 active 守望伙伴。", 403)
    elif body.scope in {"group", "challenge"}:
        if not target_group_id:
            raise _json_error("VALIDATION_ERROR", "请选择守心小组。", 400)
        _require_group_member(cur, target_group_id, user_id)
    source = _load_share_source(cur, user_id, body)
    payload, redactions = build_share_payload(
        body.source_type,
        source,
        {
            "includeScore": body.include_score,
            "includeTopPulls": body.include_top_pulls,
            "includeNextPractice": body.include_next_practice,
            "customMessage": body.custom_message,
        },
        settings,
    )
    title = payload.get("title") or source.get("title") or source.get("summary") or "守心摘要分享"
    summary = payload.get("summary") or payload.get("encouragementText") or body.custom_message or "这份分享只包含用户选择公开的守心摘要。"
    return {
        "targetUserId": target_user_id,
        "targetGroupId": target_group_id,
        "visibilityLevel": visibility,
        "payload": payload,
        "redactions": redactions,
        "title": str(title)[:200],
        "summary": str(summary)[:1000],
    }


@router.post("/accountability/shares/preview")
def preview_attention_share(request: Request, body: ShareCreateIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            prepared = _prepare_attention_share(cur, user_id, body)
        conn.rollback()
        return {
            "preview": {
                "title": prepared["title"],
                "summary": prepared["summary"],
                "payload": prepared["payload"],
                "visibilityLevel": prepared["visibilityLevel"],
                "sensitiveRedactions": prepared["redactions"],
                "scoreIncluded": "scoreAverage" in prepared["payload"],
            }
        }
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/accountability/shares")
def create_attention_share(request: Request, body: ShareCreateIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            prepared = _prepare_attention_share(cur, user_id, body)
            cur.execute(
                f"""INSERT INTO attention_share_snapshots
                (owner_user_id, scope, target_user_id, target_group_id, source_type,
                 source_id, title, summary, payload, visibility_level, sensitive_redactions)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                RETURNING {_SHARE_COLUMNS}""",
                (user_id, body.scope, prepared["targetUserId"], prepared["targetGroupId"], body.source_type,
                 body.source_id, prepared["title"], prepared["summary"], _Json(prepared["payload"]),
                 prepared["visibilityLevel"], prepared["redactions"]),
            )
            share = _share_row_to_dto(cur, cur.fetchone())
        conn.commit()
        return {"share": share}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/accountability/shares/{share_id}")
def get_attention_share(share_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _require_share_access(cur, user_id, share_id)
            return {"share": _share_row_to_dto(cur, row)}
    finally:
        _state["release_db"](conn)


@router.delete("/accountability/shares/{share_id}")
def revoke_attention_share(share_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE attention_share_snapshots SET revoked_at=now() WHERE id=%s AND owner_user_id=%s RETURNING {_SHARE_COLUMNS}",
                (share_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到可撤回的分享。", 404)
            share = _share_row_to_dto(cur, row)
        conn.commit()
        return {"share": share}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/accountability/prayer-requests")
def list_attention_prayer_requests(request: Request, status: str = Query(default="open")) -> dict:
    user_id = _db_user_id(_require_user(request))
    if status not in PRAYER_STATUSES | {"all"}:
        raise _json_error("VALIDATION_ERROR", "status 不合法。", 400)
    status_clause = "" if status == "all" else "AND status=%s"
    params: list[Any] = [user_id, user_id, user_id]
    if status != "all":
        params.append(status)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT {_PRAYER_COLUMNS} FROM attention_prayer_requests
                WHERE (
                    owner_user_id=%s OR target_user_id=%s OR target_group_id IN (
                        SELECT group_id FROM attention_group_members WHERE user_id=%s AND status='active'
                    )
                ) {status_clause}
                ORDER BY created_at DESC LIMIT 100""",
                tuple(params),
            )
            prayers = [_prayer_row_to_dto(cur, row, user_id) for row in cur.fetchall()]
        return {"prayerRequests": prayers}
    finally:
        _state["release_db"](conn)


@router.post("/accountability/prayer-requests")
def create_attention_prayer_request(request: Request, body: PrayerRequestIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    if body.category not in PRAYER_CATEGORIES:
        raise _json_error("VALIDATION_ERROR", "category 不合法。", 400)
    visibility = sanitize_visibility(body.visibility_level)
    safety = safety_check(body.title, body.body)
    is_sensitive = body.is_sensitive or safety["level"] in {"sensitive", "crisis"}
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            target_user_id = _resolve_user_id(cur, body.target_user_id) if body.target_user_id else None
            if target_user_id and not _has_active_relationship(cur, user_id, target_user_id):
                raise _json_error("FORBIDDEN", "只能向 active 守望伙伴发送代祷请求。", 403)
            if body.target_group_id:
                _require_group_member(cur, body.target_group_id, user_id)
            if not target_user_id and not body.target_group_id:
                raise _json_error("VALIDATION_ERROR", "请选择守望伙伴或小组。", 400)
            cur.execute(
                f"""INSERT INTO attention_prayer_requests
                (owner_user_id, target_user_id, target_group_id, title, body, category,
                 visibility_level, is_sensitive)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING {_PRAYER_COLUMNS}""",
                (user_id, target_user_id, body.target_group_id, body.title.strip(), body.body, body.category, visibility, is_sensitive),
            )
            prayer = _prayer_row_to_dto(cur, cur.fetchone(), user_id)
        conn.commit()
        response = {"prayerRequest": prayer, "safetyLevel": safety["level"]}
        if safety["level"] == "crisis":
            response["safetyNotice"] = {
                "urgent": True,
                "message": "如果你正处于即时危险或有伤害自己/他人的冲动，请立即联系身边可信任的人、当地紧急服务或专业危机援助。代祷可以同行，但不能替代现实中的紧急帮助。",
            }
        return response
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.put("/accountability/prayer-requests/{prayer_id}")
def update_attention_prayer_request(prayer_id: str, request: Request, body: PrayerRequestUpdateIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    data = body.model_dump(by_alias=True, exclude_unset=True)
    if not data:
        raise _json_error("VALIDATION_ERROR", "没有可更新的代祷请求。", 400)
    allowed = {
        "title": "title", "body": "body", "category": "category",
        "visibilityLevel": "visibility_level", "isSensitive": "is_sensitive",
        "status": "status", "answeredNote": "answered_note",
    }
    if "action" in data:
        if data["action"] == "close":
            data["status"] = "closed"
        elif data["action"] == "answer":
            data["status"] = "answered"
    if "category" in data and data["category"] not in PRAYER_CATEGORIES:
        raise _json_error("VALIDATION_ERROR", "category 不合法。", 400)
    if "status" in data and data["status"] not in PRAYER_STATUSES:
        raise _json_error("VALIDATION_ERROR", "status 不合法。", 400)
    if "visibilityLevel" in data:
        data["visibilityLevel"] = sanitize_visibility(data["visibilityLevel"])
    fields = [(allowed[k], v) for k, v in data.items() if k in allowed]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_PRAYER_COLUMNS} FROM attention_prayer_requests WHERE id=%s AND owner_user_id=%s", (prayer_id, user_id))
            if not cur.fetchone():
                raise _json_error("NOT_FOUND", "没有找到这条代祷请求。", 404)
            assignments = ", ".join([f"{col}=%s" for col, _ in fields])
            values = [v for _, v in fields]
            closed_sql = ", closed_at=now()" if data.get("status") in {"closed", "answered"} else ""
            cur.execute(
                f"UPDATE attention_prayer_requests SET {assignments}{closed_sql} WHERE id=%s RETURNING {_PRAYER_COLUMNS}",
                values + [prayer_id],
            )
            prayer = _prayer_row_to_dto(cur, cur.fetchone(), user_id)
        conn.commit()
        return {"prayerRequest": prayer}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.delete("/accountability/prayer-requests/{prayer_id}")
def delete_attention_prayer_request(prayer_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM attention_prayer_requests WHERE id=%s AND owner_user_id=%s RETURNING id", (prayer_id, user_id))
            if not cur.fetchone():
                raise _json_error("NOT_FOUND", "没有找到可删除的代祷请求。", 404)
        conn.commit()
        return {"ok": True}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/accountability/prayer-requests/{prayer_id}/pray")
def mark_attention_prayer(prayer_id: str, request: Request, body: PrayerMarkIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_PRAYER_COLUMNS} FROM attention_prayer_requests WHERE id=%s", (prayer_id,))
            row = cur.fetchone()
            if not row or not _can_access_prayer(cur, user_id, row):
                raise _json_error("NOT_FOUND", "没有找到这条代祷请求。", 404)
            cur.execute(
                """INSERT INTO attention_prayer_marks (prayer_request_id, user_id, message)
                VALUES (%s,%s,%s)
                ON CONFLICT (prayer_request_id, user_id) DO UPDATE SET message=EXCLUDED.message
                RETURNING id, created_at""",
                (prayer_id, user_id, body.message),
            )
            mark = cur.fetchone()
        conn.commit()
        return {"mark": {"id": str(mark[0]), "createdAt": _iso(mark[1])}}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/groups")
def list_attention_groups(request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT {_GROUP_COLUMNS_G} FROM attention_groups g
                JOIN attention_group_members m ON m.group_id=g.id
                WHERE m.user_id=%s AND m.status='active' AND g.status='active'
                ORDER BY g.created_at DESC""",
                (user_id,),
            )
            groups = [_group_row_to_dto(cur, row, user_id) for row in cur.fetchall()]
        return {"groups": groups}
    finally:
        _state["release_db"](conn)


@router.post("/groups")
def create_attention_group(request: Request, body: GroupCreateIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    if body.group_type not in GROUP_TYPES:
        raise _json_error("VALIDATION_ERROR", "groupType 不合法。", 400)
    visibility = sanitize_visibility(body.default_member_visibility, allow_selected=False)
    invite_code = uuid.uuid4().hex[:10]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""INSERT INTO attention_groups
                (owner_user_id, name, description, group_type, invite_code,
                 default_member_visibility, guidelines)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                RETURNING {_GROUP_COLUMNS}""",
                (user_id, body.name.strip(), body.description, body.group_type, invite_code, visibility, body.guidelines),
            )
            row = cur.fetchone()
            cur.execute(
                """INSERT INTO attention_group_members (group_id, user_id, role, status, visibility_level)
                VALUES (%s,%s,'owner','active',%s)
                ON CONFLICT (group_id, user_id) DO UPDATE SET role='owner', status='active'""",
                (row[0], user_id, visibility),
            )
            group = _group_row_to_dto(cur, row, user_id)
        conn.commit()
        return {"group": group}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/groups/join")
def join_attention_group(request: Request, body: GroupJoinIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_GROUP_COLUMNS} FROM attention_groups WHERE invite_code=%s AND invite_enabled=true AND status='active'", (body.invite_code.strip(),))
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "邀请链接无效或已关闭。", 404)
            cur.execute(
                """INSERT INTO attention_group_members (group_id, user_id, role, status, visibility_level)
                VALUES (%s,%s,'member','active',%s)
                ON CONFLICT (group_id, user_id) DO UPDATE SET status='active', left_at=NULL, removed_at=NULL""",
                (row[0], user_id, row[7]),
            )
            group = _group_row_to_dto(cur, row, user_id)
        conn.commit()
        return {"group": group}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/groups/{group_id}")
def get_attention_group(group_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_member(cur, group_id, user_id)
            cur.execute(f"SELECT {_GROUP_COLUMNS} FROM attention_groups WHERE id=%s", (group_id,))
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这个守心小组。", 404)
            return {"group": _group_row_to_dto(cur, row, user_id)}
    finally:
        _state["release_db"](conn)


@router.put("/groups/{group_id}")
def update_attention_group(group_id: str, request: Request, body: GroupUpdateIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    data = body.model_dump(by_alias=True, exclude_unset=True)
    if not data:
        raise _json_error("VALIDATION_ERROR", "没有可更新的小组设置。", 400)
    allowed = {
        "name": "name", "description": "description", "groupType": "group_type",
        "inviteEnabled": "invite_enabled", "defaultMemberVisibility": "default_member_visibility",
        "guidelines": "guidelines", "status": "status",
    }
    if "groupType" in data and data["groupType"] not in GROUP_TYPES:
        raise _json_error("VALIDATION_ERROR", "groupType 不合法。", 400)
    if "status" in data and data["status"] not in GROUP_STATUSES:
        raise _json_error("VALIDATION_ERROR", "status 不合法。", 400)
    if "defaultMemberVisibility" in data:
        data["defaultMemberVisibility"] = sanitize_visibility(data["defaultMemberVisibility"], allow_selected=False)
    fields = [(allowed[k], v) for k, v in data.items() if k in allowed]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_manager(cur, group_id, user_id)
            assignments = ", ".join([f"{col}=%s" for col, _ in fields])
            cur.execute(
                f"UPDATE attention_groups SET {assignments} WHERE id=%s RETURNING {_GROUP_COLUMNS}",
                [v for _, v in fields] + [group_id],
            )
            group = _group_row_to_dto(cur, cur.fetchone(), user_id)
        conn.commit()
        return {"group": group}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.delete("/groups/{group_id}")
def archive_attention_group(group_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_owner(cur, group_id, user_id)
            cur.execute(f"UPDATE attention_groups SET status='archived' WHERE id=%s RETURNING {_GROUP_COLUMNS}", (group_id,))
            group = _group_row_to_dto(cur, cur.fetchone(), user_id)
        conn.commit()
        return {"group": group}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/groups/{group_id}/members")
def list_attention_group_members(group_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_member(cur, group_id, user_id)
            cur.execute(f"SELECT {_MEMBER_COLUMNS} FROM attention_group_members WHERE group_id=%s ORDER BY joined_at ASC", (group_id,))
            members = [_member_row_to_dto(cur, r) for r in cur.fetchall()]
        return {"members": members}
    finally:
        _state["release_db"](conn)


@router.put("/groups/{group_id}/members/{member_id}")
def update_attention_group_member(group_id: str, member_id: str, request: Request, body: MemberUpdateIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    data = body.model_dump(exclude_unset=True)
    if "role" in data and data["role"] not in GROUP_ROLES:
        raise _json_error("VALIDATION_ERROR", "role 不合法。", 400)
    if "status" in data and data["status"] not in MEMBER_STATUSES:
        raise _json_error("VALIDATION_ERROR", "status 不合法。", 400)
    fields = [(k, v) for k, v in data.items() if k in {"role", "status"}]
    if not fields:
        raise _json_error("VALIDATION_ERROR", "没有可更新的成员设置。", 400)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_manager(cur, group_id, user_id)
            if any(k == "role" and v == "owner" for k, v in fields):
                _require_group_owner(cur, group_id, user_id)
            assignments = ", ".join([f"{k}=%s" for k, _ in fields])
            cur.execute(
                f"UPDATE attention_group_members SET {assignments} WHERE id=%s AND group_id=%s RETURNING {_MEMBER_COLUMNS}",
                [v for _, v in fields] + [member_id, group_id],
            )
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这个成员。", 404)
            member = _member_row_to_dto(cur, row)
        conn.commit()
        return {"member": member}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.delete("/groups/{group_id}/members/{member_id}")
def remove_attention_group_member(group_id: str, member_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_MEMBER_COLUMNS} FROM attention_group_members WHERE id=%s AND group_id=%s", (member_id, group_id))
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这个成员。", 404)
            if row[2] != user_id:
                _require_group_manager(cur, group_id, user_id)
            if row[3] == "owner":
                cur.execute("SELECT COUNT(*) FROM attention_group_members WHERE group_id=%s AND role='owner' AND status='active'", (group_id,))
                if int(cur.fetchone()[0] or 0) <= 1:
                    raise _json_error("VALIDATION_ERROR", "小组至少需要保留一位 owner。", 400)
            cur.execute(
                f"UPDATE attention_group_members SET status=%s, left_at=now(), removed_at=now() WHERE id=%s RETURNING {_MEMBER_COLUMNS}",
                ("left" if row[2] == user_id else "removed", member_id),
            )
            member = _member_row_to_dto(cur, cur.fetchone())
        conn.commit()
        return {"member": member}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/groups/{group_id}/invitations")
def create_attention_group_invitation(group_id: str, request: Request, body: GroupInviteIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    invite_code = uuid.uuid4().hex[:10] if body.create_invite_code else None
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_manager(cur, group_id, user_id)
            invited_user_id = _resolve_user_id(cur, body.invited_user_id) if body.invited_user_id else None
            if invite_code:
                cur.execute("UPDATE attention_groups SET invite_code=%s, invite_enabled=true WHERE id=%s", (invite_code, group_id))
            cur.execute(
                """INSERT INTO attention_group_invitations
                (group_id, invited_by_user_id, invited_user_id, invited_email, invite_code, message)
                VALUES (%s,%s,%s,%s,%s,%s)
                RETURNING id, group_id, invited_user_id, invited_email, invite_code, status, message, created_at""",
                (group_id, user_id, invited_user_id, body.invited_email, invite_code, body.message),
            )
            row = cur.fetchone()
        conn.commit()
        return {"invitation": {
            "id": str(row[0]), "groupId": str(row[1]), "invitedUserId": row[2],
            "invitedEmail": row[3], "inviteCode": row[4], "status": row[5],
            "message": row[6], "createdAt": _iso(row[7]),
        }}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/challenges/templates")
def list_attention_challenge_templates(request: Request) -> dict:
    _require_user(request)
    return {"templates": CHALLENGE_TEMPLATES}


@router.get("/challenges/mine")
def list_my_attention_challenges(request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT {_CHALLENGE_COLUMNS_C} FROM attention_group_challenges c
                JOIN attention_challenge_participations p ON p.challenge_id=c.id
                WHERE p.user_id=%s AND p.status='active' AND c.status='active'
                ORDER BY c.start_date DESC""",
                (user_id,),
            )
            challenges = [_challenge_row_to_dto(cur, r, user_id) for r in cur.fetchall()]
        return {"challenges": challenges}
    finally:
        _state["release_db"](conn)


@router.get("/groups/{group_id}/challenges")
def list_attention_group_challenges(group_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_member(cur, group_id, user_id)
            cur.execute(f"SELECT {_CHALLENGE_COLUMNS} FROM attention_group_challenges WHERE group_id=%s AND status<>'archived' ORDER BY start_date DESC", (group_id,))
            challenges = [_challenge_row_to_dto(cur, r, user_id) for r in cur.fetchall()]
        return {"challenges": challenges}
    finally:
        _state["release_db"](conn)


@router.post("/groups/{group_id}/challenges")
def create_attention_group_challenge(group_id: str, request: Request, body: ChallengeCreateIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    if body.challenge_type not in CHALLENGE_TYPES:
        raise _json_error("VALIDATION_ERROR", "challengeType 不合法。", 400)
    if body.privacy_mode not in CHALLENGE_PRIVACY_MODES:
        raise _json_error("VALIDATION_ERROR", "privacyMode 不合法。", 400)
    start = _parse_date(body.start_date, "startDate")
    end = _parse_date(body.end_date, "endDate")
    if end < start:
        raise _json_error("VALIDATION_ERROR", "endDate 不能早于 startDate。", 400)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_manager(cur, group_id, user_id)
            cur.execute(
                f"""INSERT INTO attention_group_challenges
                (group_id, created_by_user_id, template_key, title, description,
                 challenge_type, start_date, end_date, target_days, target_minutes,
                 checkin_prompt, privacy_mode, allow_comments, allow_prayer_requests)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING {_CHALLENGE_COLUMNS}""",
                (group_id, user_id, body.template_key, body.title.strip(), body.description,
                 body.challenge_type, start, end, body.target_days, body.target_minutes,
                 body.checkin_prompt, body.privacy_mode, body.allow_comments, body.allow_prayer_requests),
            )
            row = cur.fetchone()
            cur.execute(
                """INSERT INTO attention_challenge_participations (challenge_id, user_id, status)
                VALUES (%s,%s,'active') ON CONFLICT (challenge_id, user_id) DO UPDATE SET status='active'""",
                (row[0], user_id),
            )
            challenge = _challenge_row_to_dto(cur, row, user_id)
        conn.commit()
        return {"challenge": challenge}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/groups/{group_id}/challenges/{challenge_id}")
def get_attention_group_challenge(group_id: str, challenge_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _challenge_access_row(cur, challenge_id, group_id, user_id)
            return {"challenge": _challenge_row_to_dto(cur, row, user_id)}
    finally:
        _state["release_db"](conn)


@router.put("/groups/{group_id}/challenges/{challenge_id}")
def update_attention_group_challenge(group_id: str, challenge_id: str, request: Request, body: ChallengeUpdateIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    data = body.model_dump(by_alias=True, exclude_unset=True)
    if not data:
        raise _json_error("VALIDATION_ERROR", "没有可更新的挑战设置。", 400)
    allowed = {
        "title": "title", "description": "description", "startDate": "start_date",
        "endDate": "end_date", "targetDays": "target_days", "targetMinutes": "target_minutes",
        "checkinPrompt": "checkin_prompt", "privacyMode": "privacy_mode",
        "allowComments": "allow_comments", "allowPrayerRequests": "allow_prayer_requests",
        "status": "status",
    }
    if "privacyMode" in data and data["privacyMode"] not in CHALLENGE_PRIVACY_MODES:
        raise _json_error("VALIDATION_ERROR", "privacyMode 不合法。", 400)
    if "status" in data and data["status"] not in CHALLENGE_STATUSES:
        raise _json_error("VALIDATION_ERROR", "status 不合法。", 400)
    if "startDate" in data:
        data["startDate"] = _parse_date(data["startDate"], "startDate")
    if "endDate" in data:
        data["endDate"] = _parse_date(data["endDate"], "endDate")
    fields = [(allowed[k], v) for k, v in data.items() if k in allowed]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_manager(cur, group_id, user_id)
            _challenge_access_row(cur, challenge_id, group_id, user_id)
            assignments = ", ".join([f"{col}=%s" for col, _ in fields])
            cur.execute(
                f"UPDATE attention_group_challenges SET {assignments} WHERE id=%s AND group_id=%s RETURNING {_CHALLENGE_COLUMNS}",
                [v for _, v in fields] + [challenge_id, group_id],
            )
            challenge = _challenge_row_to_dto(cur, cur.fetchone(), user_id)
        conn.commit()
        return {"challenge": challenge}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.delete("/groups/{group_id}/challenges/{challenge_id}")
def archive_attention_group_challenge(group_id: str, challenge_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_manager(cur, group_id, user_id)
            cur.execute(
                f"UPDATE attention_group_challenges SET status='archived' WHERE id=%s AND group_id=%s RETURNING {_CHALLENGE_COLUMNS}",
                (challenge_id, group_id),
            )
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这个挑战。", 404)
            challenge = _challenge_row_to_dto(cur, row, user_id)
        conn.commit()
        return {"challenge": challenge}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/groups/{group_id}/challenges/{challenge_id}/participants")
def list_attention_challenge_participants(group_id: str, challenge_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _challenge_access_row(cur, challenge_id, group_id, user_id)
            challenge = _challenge_row_to_dto(cur, row, user_id)
            if challenge["privacyMode"] == "anonymous_aggregate":
                return {"participants": [], "progress": challenge["progress"]}
            cur.execute("SELECT user_id FROM attention_challenge_participations WHERE challenge_id=%s AND status='active' ORDER BY joined_at ASC", (challenge_id,))
            participants = [_member_participant_summary(cur, challenge_id, r[0]) for r in cur.fetchall()]
        return {"participants": participants, "progress": challenge["progress"]}
    finally:
        _state["release_db"](conn)


@router.post("/groups/{group_id}/challenges/{challenge_id}/checkins")
def save_attention_challenge_checkin(group_id: str, challenge_id: str, request: Request, body: ChallengeCheckinIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    checkin_date = _parse_date(body.checkin_date, "checkinDate") if body.checkin_date else date.today()
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _challenge_access_row(cur, challenge_id, group_id, user_id)
            challenge = _challenge_row_to_dict(row)
            visibility = sanitize_visibility(body.visibility_level)
            if challenge["privacyMode"] in {"status_only", "anonymous_aggregate"}:
                visibility = "status_only"
            prayer_request_id = None
            if body.create_prayer_request:
                if not challenge["allowPrayerRequests"]:
                    raise _json_error("VALIDATION_ERROR", "这个挑战未开启代祷请求。", 400)
                cur.execute(
                    f"""INSERT INTO attention_prayer_requests
                    (owner_user_id, target_group_id, title, body, category, visibility_level, is_sensitive)
                    VALUES (%s,%s,%s,%s,'attention','summary',false)
                    RETURNING {_PRAYER_COLUMNS}""",
                    (
                        user_id,
                        group_id,
                        body.prayer_request_title or f"{challenge['title']} 的代祷请求",
                        body.prayer_request_body or "请为我在这个守心操练中继续归回祷告。",
                    ),
                )
                prayer_request_id = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO attention_challenge_participations (challenge_id, user_id, status)
                VALUES (%s,%s,'active')
                ON CONFLICT (challenge_id, user_id) DO UPDATE SET status='active', left_at=NULL""",
                (challenge_id, user_id),
            )
            cur.execute(
                f"""INSERT INTO attention_challenge_checkins
                (challenge_id, user_id, checkin_date, completed, value_minutes, value_count,
                 reflection, prayer_request_id, visibility_level)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (challenge_id, user_id, checkin_date) DO UPDATE SET
                    completed=EXCLUDED.completed,
                    value_minutes=EXCLUDED.value_minutes,
                    value_count=EXCLUDED.value_count,
                    reflection=EXCLUDED.reflection,
                    prayer_request_id=COALESCE(EXCLUDED.prayer_request_id, attention_challenge_checkins.prayer_request_id),
                    visibility_level=EXCLUDED.visibility_level
                RETURNING {_CHALLENGE_CHECKIN_COLUMNS}""",
                (challenge_id, user_id, checkin_date, body.completed, body.value_minutes, body.value_count,
                 body.reflection, prayer_request_id, visibility),
            )
            checkin = _challenge_checkin_row_to_dto(cur.fetchone(), include_reflection=True)
        conn.commit()
        return {"checkin": checkin}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)

# ---------------------------------------------------------------------------
# Batch 3: AI Spiritual Attention Diagnosis Agent (fallback-first)
# ---------------------------------------------------------------------------


def _fetch_entries_between(cur, user_id: str, start: date, end: date) -> list[dict]:
    cur.execute(
        f"SELECT {_ENTRY_COLUMNS} FROM attention_entries WHERE user_id=%s AND entry_date BETWEEN %s AND %s ORDER BY entry_date DESC, created_at DESC LIMIT 200",
        (user_id, start, end),
    )
    return [_entry_row_to_dto(r) for r in cur.fetchall()]


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


# ---------------------------------------------------------------------------
# Batch 4: Attention Warfare Map / Plans / Check-ins
# ---------------------------------------------------------------------------


@router.get("/warfare/pattern-library")
def get_warfare_pattern_library(request: Request) -> dict:
    _require_user(request)
    return {"patterns": pattern_definitions()}


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
