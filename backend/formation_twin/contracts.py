"""Versioned Formation Twin life-event contracts."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator


class LifeEventType(str, Enum):
    DAILY_CHECKIN = "DAILY_CHECKIN"
    JOURNAL_ENTRY = "JOURNAL_ENTRY"
    VOICE_JOURNAL = "VOICE_JOURNAL"
    PRAYER_ACTIVITY = "PRAYER_ACTIVITY"
    DEVOTION_ACTIVITY = "DEVOTION_ACTIVITY"
    HABIT_ACTIVITY = "HABIT_ACTIVITY"
    ATTENTION_ACTIVITY = "ATTENTION_ACTIVITY"
    CHURCH_ACTIVITY = "CHURCH_ACTIVITY"
    RELATIONSHIP_EVENT = "RELATIONSHIP_EVENT"
    CALLING_ACTIVITY = "CALLING_ACTIVITY"
    FORMATION_ACTIVITY = "FORMATION_ACTIVITY"
    CRISIS_STATUS_EVENT = "CRISIS_STATUS_EVENT"
    USER_CORRECTION = "USER_CORRECTION"
    EXTERNAL_MODULE_EVENT = "EXTERNAL_MODULE_EVENT"
    OTHER = "OTHER"


class LifeEventStatus(str, Enum):
    RECEIVED = "RECEIVED"
    BLOCKED_NO_CONSENT = "BLOCKED_NO_CONSENT"
    ROUTED_TO_CRISIS = "ROUTED_TO_CRISIS"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"
    SUPERSEDED = "SUPERSEDED"
    EXCLUDED = "EXCLUDED"
    DELETED = "DELETED"


class SourceType(str, Enum):
    USER_MANUAL_INPUT = "USER_MANUAL_INPUT"
    USER_STRUCTURED_INPUT = "USER_STRUCTURED_INPUT"
    USER_VOICE_INPUT = "USER_VOICE_INPUT"
    PRAYER_OS = "PRAYER_OS"
    DEVOTION_SYSTEM = "DEVOTION_SYSTEM"
    HOLY_HABIT_ENGINE = "HOLY_HABIT_ENGINE"
    ATTENTION_OS = "ATTENTION_OS"
    CRISIS_CARE_SYSTEM = "CRISIS_CARE_SYSTEM"
    FORMATION_ENGINE = "FORMATION_ENGINE"
    WORLDVIEW_OS = "WORLDVIEW_OS"
    GIFT_CALLING_OS = "GIFT_CALLING_OS"
    CHURCH_HEALTH_OS = "CHURCH_HEALTH_OS"
    OTHER = "OTHER"


class ProcessingPreference(str, Enum):
    STORE_ONLY = "STORE_ONLY"
    ALLOW_FUTURE_ANALYSIS = "ALLOW_FUTURE_ANALYSIS"
    EXCLUDE_FROM_TWIN = "EXCLUDE_FROM_TWIN"


class StatementType(str, Enum):
    USER_REPORTED_FACT = "USER_REPORTED_FACT"
    OBSERVED_EVENT = "OBSERVED_EVENT"
    USER_CONFIRMED_PATTERN = "USER_CONFIRMED_PATTERN"


class LifeEventSource(BaseModel):
    source_type: SourceType
    source_module: str = Field(min_length=1, max_length=80)
    source_record_id: str | None = Field(default=None, max_length=160)
    source_event_id: str | None = Field(default=None, max_length=160)
    source_version: str = Field(default="1.0", max_length=20)


class SelfReportedEmotion(BaseModel):
    emotion: str = Field(min_length=1, max_length=48)
    intensity: int | None = Field(default=None, ge=0, le=10)
    statement_type: Literal[StatementType.USER_REPORTED_FACT] = StatementType.USER_REPORTED_FACT


class SafetyMetadata(BaseModel):
    screened: bool = True
    safety_level: Literal["NONE", "CONCERN", "ELEVATED", "IMMINENT"] = "NONE"
    route_reference: str | None = None


class ConsentMetadata(BaseModel):
    consent_scope: str = Field(min_length=1, max_length=100)
    policy_version: str = "1.0"
    processing_preference: ProcessingPreference = ProcessingPreference.STORE_ONLY


class ProvenanceMetadata(BaseModel):
    statement_types: list[StatementType]
    normalization_version: str = "life-event-normalizer-1.0"
    processing_steps: list[str]
    accepted_fields: list[str] = Field(default_factory=list)
    discarded_field_names: list[str] = Field(default_factory=list)
    discarded_values_stored: Literal[False] = False


class CanonicalLifeEvent(BaseModel):
    event_id: UUID
    tenant_id: str
    profile_id: str
    subject_user_id: str
    event_type: LifeEventType
    event_subtype: str | None = Field(default=None, max_length=80)
    event_version: str = "1.0"
    occurred_at: datetime
    recorded_at: datetime
    timezone: str
    source: LifeEventSource
    context: dict[str, Any] = Field(default_factory=dict)
    self_report: dict[str, Any] | None = None
    behavioral_facts: list[dict[str, Any]] = Field(default_factory=list)
    spiritual_practice_facts: list[dict[str, Any]] = Field(default_factory=list)
    relationship_facts: list[dict[str, Any]] = Field(default_factory=list)
    content_reference: dict[str, Any] | None = None
    safety: SafetyMetadata
    consent: ConsentMetadata
    provenance: ProvenanceMetadata
    data_classification: Literal["HIGHLY_SENSITIVE"] = "HIGHLY_SENSITIVE"
    status: LifeEventStatus
    created_at: datetime

    @field_validator("occurred_at", "recorded_at", "created_at")
    @classmethod
    def require_aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timezone-aware datetime required")
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("valid IANA timezone required") from exc
        return value

    @model_validator(mode="after")
    def reject_sensitive_content(self):
        forbidden = {
            "content", "raw_content", "full_text", "journal_text", "prayer_text", "transcript", "crisis_text",
            "private_note", "confession_text", "medical_details", "legal_details", "method_details",
        }

        def contains_forbidden(value: Any) -> bool:
            if isinstance(value, dict):
                return bool(forbidden.intersection(value.keys())) or any(contains_forbidden(item) for item in value.values())
            if isinstance(value, list):
                return any(contains_forbidden(item) for item in value)
            return False

        for container in (self.self_report or {}, *self.behavioral_facts, *self.spiritual_practice_facts, *self.relationship_facts):
            if contains_forbidden(container):
                raise ValueError("canonical event contains sensitive body")
        if not self.provenance.statement_types:
            raise ValueError("at least one statement type is required")
        return self
