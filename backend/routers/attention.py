"""Attention Stewardship / 守心 API."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
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
except Exception:  # pragma: no cover
    from attention_suggest import ATTENTION_PULLS, build_attention_suggestion  # type: ignore
    from attention_domain import (  # type: ignore
        ATTENTION_CATEGORIES, ATTENTION_STATES, PULL_LABELS, SCRIPTURE_LIBRARY,
        clean_pulls, calculate_daily_summary, compact_context_summary,
        generate_fallback_diagnosis, safety_check, build_warfare_map,
        pattern_definitions,
    )

router = APIRouter(prefix="/api/attention", tags=["attention"])
_state: Dict[str, Any] = {}
DEFAULT_TIMEZONE = "Asia/Taipei"


def init_attention_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail={"error": "UNAUTHORIZED", "message": "请先登录。"})
    return user


def _db_user_id(user: dict) -> str:
    return str(user.get("email") or user.get("id") or "")


def _local_date(request: Request, user: dict) -> date:
    tz_name = (
        user.get("timezone")
        or request.headers.get("X-Timezone")
        or request.cookies.get("timezone")
        or DEFAULT_TIMEZONE
    )
    try:
        tz = ZoneInfo(str(tz_name))
    except Exception:
        tz = ZoneInfo(DEFAULT_TIMEZONE)
    return datetime.now(tz).date()


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
        entries = _load_entries_for_date(user_id, today)
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_FOCUS_COLUMNS} FROM attention_focus_sessions WHERE user_id=%s AND started_at::date=%s", (user_id, today))
            sessions = [_focus_row_to_dto(r) for r in cur.fetchall()]
            cur.execute(f"SELECT {_REVIEW_COLUMNS} FROM attention_reviews WHERE user_id=%s AND review_date=%s LIMIT 1", (user_id, today))
            review = cur.fetchone()
            cur.execute(f"SELECT {_DIAGNOSIS_COLUMNS} FROM attention_ai_diagnoses WHERE user_id=%s AND diagnosis_date=%s ORDER BY created_at DESC LIMIT 1", (user_id, today))
            diagnosis = cur.fetchone()
            cur.execute(f"SELECT {_PLAN_COLUMNS} FROM attention_warfare_plans WHERE user_id=%s AND status='active' ORDER BY created_at DESC", (user_id,))
            plans = [_plan_row_to_dto(r) for r in cur.fetchall()]
        summary = calculate_daily_summary(entries)
        completed = [s for s in sessions if s.get("endedAt")]
        return {
            "date": today.isoformat(),
            "covenant": (get_today_covenant(request)).get("covenant"),
            "ledger": summary,
            "focus": {
                "completedSessions": len(completed),
                "totalActualMinutes": sum(int(s.get("actualMinutes") or 0) for s in completed),
                "interruptedSessions": len([s for s in sessions if s.get("interrupted")]),
                "activeSessionExists": any(not s.get("endedAt") for s in sessions),
            },
            "review": {"exists": bool(review), "review": _review_row_to_dto(review) if review else None},
            "diagnosis": _diagnosis_row_to_dto(diagnosis) if diagnosis else None,
            "warfare": {"activePlansCount": len(plans), "todayCheckinsCount": 0, "primaryPattern": None},
        }
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
