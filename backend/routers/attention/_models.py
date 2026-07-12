"""Attention Stewardship / 守心 API — Pydantic request models.

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

