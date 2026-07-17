"""Versioned, privacy-bounded contracts for Spiritual Planet integration.

These models intentionally carry references and short summaries only. Full
journals, prayers, transcripts, crisis narratives and model prompts remain in
their source modules and are rejected at every platform boundary.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


FORBIDDEN_KEY_RE = re.compile(
    r"(^|_)(full_?(journal|prayer|transcript)|journal_?(body|text|content)|"
    r"prayer_?(body|text|content)|confession_?(body|text|content)|"
    r"temptation_?(body|text|content)|crisis_?(body|text|content|narrative)|"
    r"third_party_?(identity|details|content)|collaborator_?(feedback|content)|"
    r"report_?(body|content)|model_?prompt|system_?prompt|internal_?risk_?score|"
    r"raw_?(audio|text|content))($|_)",
    re.IGNORECASE,
)
FORBIDDEN_PLATFORM_FIELDS = {
    "platform_spiritual_score", "unified_spiritual_health_score", "module_compliance_score",
    "agent_success_on_user_score", "obedience_score", "holiness_score", "salvation_probability",
    "spiritual_rank",
}


def find_forbidden_fields(value: Any, path: str = "payload") -> list[str]:
    """Return all forbidden paths, including nested lists and dictionaries."""
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key.lower() in FORBIDDEN_PLATFORM_FIELDS or FORBIDDEN_KEY_RE.search(key):
                found.append(child_path)
            found.extend(find_forbidden_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(find_forbidden_fields(child, f"{path}[{index}]"))
    return found


def assert_platform_safe(value: Any, *, label: str = "payload") -> Any:
    forbidden = find_forbidden_fields(value, label)
    if forbidden:
        raise ValueError(f"sensitive or prohibited platform fields: {', '.join(forbidden[:5])}")
    return value


class DataClassification(str, Enum):
    INTERNAL = "INTERNAL"
    SENSITIVE = "SENSITIVE"
    HIGHLY_SENSITIVE = "HIGHLY_SENSITIVE"


class Actor(BaseModel):
    actor_type: Literal["USER", "SYSTEM", "COLLABORATOR", "SERVICE"]
    actor_id: str | None = None


class UnifiedEventEnvelope(BaseModel):
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_type: str = Field(pattern=r"^[a-z][a-z0-9_.]+$", max_length=120)
    event_version: str = Field(default="1.0", pattern=r"^\d+\.\d+$")
    tenant_id: str = Field(min_length=1, max_length=255)
    subject_user_id: str = Field(min_length=1, max_length=255)
    actor: Actor
    producer: str = Field(min_length=1, max_length=80)
    occurred_at: datetime
    published_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    causation_id: uuid.UUID | None = None
    trace_id: str = Field(min_length=8, max_length=128)
    data_classification: DataClassification = DataClassification.HIGHLY_SENSITIVE
    purpose_tags: list[str] = Field(min_length=1, max_length=8)
    consent_reference_ids: list[str] = Field(default_factory=list, max_length=20)
    schema_uri: str = Field(min_length=1, max_length=240)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("payload")
    @classmethod
    def safe_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        return assert_platform_safe(value)

    @field_validator("occurred_at", "published_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event timestamps must include a timezone")
        return value


class TemporalScope(BaseModel):
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @model_validator(mode="after")
    def ordered(self):
        if self.starts_at and self.ends_at and self.starts_at > self.ends_at:
            raise ValueError("starts_at must be before ends_at")
        return self


class ContextRequest(BaseModel):
    requester_module: str = Field(min_length=1, max_length=80)
    purpose: str = Field(min_length=1, max_length=80)
    requested_projection: str = Field(min_length=1, max_length=100)
    requested_fields: list[str] = Field(default_factory=list, max_length=50)
    temporal_scope: TemporalScope | None = None
    correlation_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    subject_user_id: str | None = Field(default=None, max_length=255)


class ContextSourceReference(BaseModel):
    source_module: str
    source_record_type: str
    source_record_id: str
    statement_status: Literal["CONFIRMED", "PENDING", "OBSERVED"]


class ContextAccessDecision(BaseModel):
    allowed: bool
    decision_reason_codes: list[str]
    allowed_fields: list[str]
    denied_fields: list[str]
    maximum_ttl_seconds: int = Field(default=300, ge=30, le=900)
    user_confirmation_required: bool = False
    audit_required: bool = True


class ContextResponse(BaseModel):
    context_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    projection_name: str
    projection_version: str
    confirmed_context: dict[str, Any]
    pending_context: dict[str, Any]
    limitations: list[str]
    consent_reference_ids: list[str]
    source_references: list[ContextSourceReference]
    expires_at: datetime
    generated_at: datetime

    @field_validator("confirmed_context", "pending_context")
    @classmethod
    def safe_context(cls, value: dict[str, Any]) -> dict[str, Any]:
        return assert_platform_safe(value, label="context")


class AgentCapability(BaseModel):
    agent_id: str
    version: str
    owner_module: str
    capability_type: Literal[
        "ANALYZER", "REFLECTION_GENERATOR", "RECOMMENDATION_GENERATOR", "SAFETY_CLASSIFIER",
        "COMMAND_EXECUTOR", "CONTEXT_PROVIDER", "NOTIFICATION_GENERATOR", "REPORT_GENERATOR",
    ]
    accepted_input_schemas: list[str]
    output_schema: str
    allowed_purposes: list[str]
    allowed_context_projections: list[str]
    can_read_sensitive_content: bool = False
    can_create_proposals: bool = False
    can_execute_commands: bool = False
    requires_user_confirmation: bool = True
    safety_policy_ids: list[str] = Field(default_factory=lambda: ["global-safety-v1"])
    active: bool = True

    @model_validator(mode="after")
    def capability_separation(self):
        if self.capability_type == "ANALYZER" and self.can_execute_commands:
            raise ValueError("analyzers cannot execute commands")
        if self.capability_type == "RECOMMENDATION_GENERATOR" and self.can_execute_commands:
            raise ValueError("recommendation generators create proposals only")
        if self.capability_type == "COMMAND_EXECUTOR" and not self.requires_user_confirmation:
            raise ValueError("command executors require user confirmation")
        return self


class RecommendationCandidate(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    source_module: str = Field(min_length=1, max_length=80)
    recommendation_type: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=280)
    purpose: str
    estimated_duration_minutes: int = Field(default=2, ge=0, le=180)
    burden_level: Literal["VERY_LOW", "LOW", "MEDIUM", "HIGH"] = "LOW"
    safety_priority: int = Field(default=7, ge=1, le=8)
    urgency: Literal["IMMEDIATE", "TODAY", "THIS_WEEK", "WHEN_READY"] = "TODAY"
    supporting_context_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10)
    requires_user_confirmation: bool = True
    conflicts_with: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    duplicates: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    expires_at: datetime | None = None
    explicit_user_intent: bool = False
    capacity_mode: Literal["VERY_LOW", "LOW", "NORMAL"] = "NORMAL"
    dedupe_key: str | None = Field(default=None, max_length=80)
    target_module: str | None = Field(default=None, max_length=80)
    proposed_payload: dict[str, Any] = Field(default_factory=dict)
    uses_pending_context: bool = False

    @field_validator("proposed_payload")
    @classmethod
    def safe_proposal(cls, value: dict[str, Any]) -> dict[str, Any]:
        return assert_platform_safe(value, label="proposal")


class SuppressedRecommendation(BaseModel):
    candidate_id: uuid.UUID
    reason_code: str


class RecommendationArbitrationResult(BaseModel):
    selected_recommendation: RecommendationCandidate | None
    merged_candidates: list[uuid.UUID]
    suppressed_candidates: list[SuppressedRecommendation]
    selection_rationale: list[str]
    no_action_selected: bool


class UnifiedCommand(BaseModel):
    command_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    command_type: str = Field(min_length=1, max_length=80)
    target_module: str = Field(min_length=1, max_length=80)
    payload: dict[str, Any]
    payload_schema: str
    user_confirmation_reference_id: uuid.UUID
    purpose: str
    idempotency_key: str = Field(min_length=8, max_length=160)
    expires_at: datetime | None = None
    source_recommendation_id: uuid.UUID | None = None

    @field_validator("payload")
    @classmethod
    def safe_command(cls, value: dict[str, Any]) -> dict[str, Any]:
        return assert_platform_safe(value, label="command")


class OrchestrationRequest(BaseModel):
    trigger_type: Literal[
        "USER_REQUEST", "STATE_CHANGED", "PATTERN_CONFIRMED", "WARNING_TRIGGERED", "WEEKLY_REVIEW_DUE",
        "LIFE_SEASON_CHANGED", "COLLABORATOR_FEEDBACK_CONFIRMED", "CRISIS_STATE_CHANGED", "DATA_DELETED",
        "CONSENT_CHANGED",
    ]
    trigger_reference_id: str | None = None
    user_intent: str | None = Field(default=None, max_length=240)
    requested_outcome: str | None = Field(default=None, max_length=120)
    correlation_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    candidate_recommendations: list[RecommendationCandidate] = Field(default_factory=list, max_length=20)
    safety_state: Literal["NONE", "CONCERN", "ELEVATED", "IMMINENT"] = "NONE"
    capacity_mode: Literal["VERY_LOW", "LOW", "NORMAL"] = "NORMAL"
    max_nodes: int = Field(default=8, ge=1, le=20)
    max_model_calls: int = Field(default=1, ge=0, le=3)


class DeletionRequest(BaseModel):
    source_module: str
    source_record_type: str
    source_record_ids: list[str] = Field(min_length=1, max_length=100)
    deletion_scope: Literal["SOURCE_RECORDS", "MODULE_DATA", "FULL_USER_PLATFORM_STATE"] = "SOURCE_RECORDS"


class RebuildRequest(BaseModel):
    scope: Literal[
        "SINGLE_RECORD", "SINGLE_MODULE", "FORMATION_TWIN_STATE", "LONG_TERM_PATTERNS",
        "UNIFIED_CONTEXT", "FULL_USER_DERIVED_STATE", "TENANT_MIGRATION",
    ]
    source_module: str | None = None
    source_record_ids: list[str] = Field(default_factory=list, max_length=100)
    reason: str = Field(default="USER_REQUESTED", max_length=80)
