"""Strict, versioned trust-boundary contracts for Batches 01-12."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class RecordType(StrEnum):
    LEARNER_CONTEXT = "learner_context"
    FORMATION_PLAN = "formation_plan"
    PRACTICE_CHECKIN = "practice_checkin"
    AI_USE_INTENT = "ai_use_intent"
    RECOVERY_BOUNDARY_PLAN = "recovery_boundary_plan"
    PARENT_FORMATION_PLAN = "parent_formation_plan"
    FAMILY_COVENANT = "family_covenant"
    CHILD_CAREGIVER_PLAN = "child_caregiver_plan"
    YOUTH_AUTONOMY_PLAN = "youth_autonomy_plan"
    CURRICULUM_DRAFT = "curriculum_draft"
    SCENARIO_SESSION = "scenario_session"
    TWIN_CONSENT = "twin_consent"


class LearnerConsent(StrictModel):
    data_minimization_accepted: bool
    guardian_confirmed: bool | None = None
    pastoral_followup_allowed: bool = False


class LearnerContextV1(StrictModel):
    version: Literal["1.0.0"] = "1.0.0"
    role: Literal["learner", "parent", "teacher", "pastor", "guardian"]
    age_band: Literal["0_6", "7_12", "13_15", "16_18", "adult"]
    locale: str = Field(min_length=2, max_length=20)
    goals: list[Literal[
        "attention", "digital_habits", "body_rhythm", "sexual_integrity",
        "ai_discernment", "family_liturgy", "parent_modeling", "identity",
        "relationships", "teacher_preparation",
    ]] = Field(min_length=1, max_length=6)
    accessibility_needs: list[str] = Field(default_factory=list, max_length=8)
    device_context: Literal["shared_device", "personal_device", "mixed", "none", "prefer_not_to_say"] = "prefer_not_to_say"
    consent: LearnerConsent

    @field_validator("goals")
    @classmethod
    def unique_goals(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("goals must be unique")
        return value

    @model_validator(mode="after")
    def consent_gate(self):
        if self.age_band != "adult" and self.consent.guardian_confirmed is not True:
            raise ValueError("minor access requires guardian confirmation")
        if not self.consent.data_minimization_accepted:
            raise ValueError("data minimization consent is required")
        return self


class FormationPlanV1(StrictModel):
    version: Literal["1.0.0"] = "1.0.0"
    horizon_days: Literal[7, 14, 30, 90]
    priority_domains: list[str] = Field(min_length=1, max_length=3)
    practice_ids: list[str] = Field(min_length=1, max_length=3)
    status: Literal["draft", "active", "paused", "completed", "archived"] = "draft"
    starts_on: date
    grace_before_practice: Literal[True] = True
    spiritual_score_generated: Literal[False] = False

    @field_validator("priority_domains", "practice_ids")
    @classmethod
    def unique_values(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("values must be unique")
        return value


class PracticeCheckInV1(StrictModel):
    version: Literal["1.0.0"] = "1.0.0"
    plan_id: str = Field(min_length=3, max_length=100)
    practice_id: str = Field(min_length=3, max_length=100)
    status: Literal["completed", "partial", "not_attempted", "intentionally_resting", "not_applicable"]
    observed_fruit: list[str] = Field(default_factory=list, max_length=4)
    private_note_policy: Literal["none", "local_only"] = "none"
    analytics_includes_entry_details: Literal[False] = False
    checked_in_at: datetime


class AiUseIntentV1(StrictModel):
    version: Literal["1.0.0"] = "1.0.0"
    task_category: Literal["research", "learning", "writing", "planning", "spiritual_content", "decision_support"]
    stakes: Literal["low", "medium", "high", "emergency"]
    requested_role: Literal[
        "tool", "tutor", "collaborator", "critic", "verifier", "recommender",
        "final_moral_authority", "pastoral_diagnostician", "divine_messenger", "secret_minor_companion",
    ]
    delegation_level: Literal["assist", "draft", "compare", "verify", "decide"]
    privacy_class: Literal["public", "ordinary", "sensitive", "minor_sensitive"]
    raw_prompt_persisted: Literal[False] = False
    final_decision_owner: Literal["human"] = "human"


class BoundaryPlanV1(StrictModel):
    version: Literal["1.0.0"] = "1.0.0"
    categories: list[str] = Field(min_length=1, max_length=8)
    protective_actions: list[str] = Field(min_length=1, max_length=8)
    support_roles: list[Literal["trusted_friend", "spouse", "parent_guardian", "pastor", "mentor", "licensed_professional"]] = Field(default_factory=list, max_length=4)
    stores_explicit_content: Literal[False] = False
    stores_third_party_identity: Literal[False] = False


class FamilyCovenantV1(StrictModel):
    version: Literal["1.0.0"] = "1.0.0"
    device_zones: list[str] = Field(default_factory=list, max_length=8)
    ai_boundaries: list[str] = Field(default_factory=list, max_length=8)
    review_cadence_days: Literal[7, 14, 30, 90]
    exception_categories: list[str] = Field(default_factory=list, max_length=6)
    child_voice_included: bool
    covert_monitoring_allowed: Literal[False] = False


class CurriculumDraftV1(StrictModel):
    version: Literal["1.0.0"] = "1.0.0"
    content_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,100}$")
    age_bands: list[Literal["0_6", "7_12", "13_15", "16_18", "adult"]] = Field(min_length=1)
    authority_level: Literal["SCRIPTURE_EXPLICIT", "THEOLOGICAL_INFERENCE", "PASTORAL_WISDOM", "PRODUCT_DEFAULT"]
    review_status: Literal["draft", "theology_review", "pastoral_review", "approved", "rejected"] = "draft"
    scripture_references: list[str] = Field(default_factory=list, max_length=12)
    auto_publish_allowed: Literal[False] = False


class ScenarioSessionV1(StrictModel):
    version: Literal["1.0.0"] = "1.0.0"
    scenario_id: str = Field(min_length=3, max_length=100)
    scenario_version: str = Field(min_length=1, max_length=30)
    current_node_id: str = Field(min_length=1, max_length=100)
    choice_ids: list[str] = Field(default_factory=list, max_length=40)
    status: Literal["active", "paused", "completed", "safety_interrupted"]
    raw_free_text_persisted: Literal[False] = False
    personality_profile_generated: Literal[False] = False


class TwinConsentV1(StrictModel):
    version: Literal["1.0.0"] = "1.0.0"
    selected_domains: list[Literal["attention", "habits", "relationships", "formation_reviews"]] = Field(min_length=1, max_length=4)
    status: Literal["active", "paused", "withdrawn"]
    allows_device_telemetry: Literal[False] = False
    allows_browsing_history: Literal[False] = False
    allows_private_chat_access: Literal[False] = False


class RecordEnvelopeCreate(StrictModel):
    record_type: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9._-]{2,120}$")
    schema_name: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._-]{3,140}$")
    payload: dict[str, Any]
    idempotency_key: str = Field(min_length=8, max_length=120)
    retention_days: int = Field(default=90, ge=1, le=365)


class RecordEnvelopePatch(StrictModel):
    payload: dict[str, Any]
    expected_revision: int = Field(ge=1)


class RecordStateTransition(StrictModel):
    transition: Literal["activate", "pause", "resume", "complete", "archive"]
    expected_revision: int = Field(ge=1)


class ScenarioStartRequest(StrictModel):
    scenario_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,120}$")
    idempotency_key: str = Field(min_length=8, max_length=120)
    retention_days: int = Field(default=30, ge=1, le=90)


class ScenarioChoiceRequest(StrictModel):
    choice: Literal["observe", "pause", "seek_help", "repair", "skip", "complete", "safety_interrupt"]
    expected_revision: int = Field(ge=1)


class ContentReviewCreate(StrictModel):
    reviewer_role: Literal[
        "theology_reviewer", "pastoral_reviewer", "child_safety_reviewer",
        "rights_reviewer", "accessibility_reviewer", "release_reviewer",
    ]
    decision: Literal["approve", "request_changes", "reject"]
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reason_codes: list[str] = Field(min_length=1, max_length=20)
    note: str = Field(default="", max_length=500)


class ContentPublicationRequest(StrictModel):
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_review_status: Literal["approved"] = "approved"
    reason_code: str = Field(min_length=3, max_length=120)


class ReleaseDecisionCreate(StrictModel):
    artifact_id: str = Field(min_length=3, max_length=160)
    artifact_version: str = Field(min_length=1, max_length=80)
    environment: Literal["staging", "production"]
    artifact_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    decision: Literal["blocked", "limited_rollout", "approved", "rolled_back"]
    rollout_percent: int = Field(ge=0, le=100)
    rollback_owner: str = Field(min_length=3, max_length=160)
    incident_owner: str = Field(min_length=3, max_length=160)
    reason_codes: list[str] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def release_shape(self):
        if self.decision == "approved" and self.rollout_percent != 100:
            raise ValueError("approved release requires rollout_percent=100")
        if self.decision == "limited_rollout" and not 1 <= self.rollout_percent < 100:
            raise ValueError("limited rollout requires rollout_percent between 1 and 99")
        if self.decision in {"blocked", "rolled_back"} and self.rollout_percent != 0:
            raise ValueError("blocked or rolled_back decision requires rollout_percent=0")
        return self


class SafetyCheckRequest(StrictModel):
    text: str = Field(min_length=1, max_length=4000)
    locale: str = Field(default="zh-CN", min_length=2, max_length=20)
    age_band: Literal["0_6", "7_12", "13_15", "16_18", "adult"]


class ReleaseEvidenceV1(StrictModel):
    version: Literal["1.0.0"] = "1.0.0"
    artifact_id: str = Field(min_length=3, max_length=160)
    artifact_version: str = Field(min_length=1, max_length=80)
    environment: Literal["local", "ci", "staging", "production"]
    artifact_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    gate: Literal[
        "theology", "pastoral_safety", "child_safety", "privacy_security",
        "tenant_isolation", "accessibility_automated", "accessibility_manual",
        "content_quality", "skill_evals", "rollback_rehearsal",
    ]
    result: Literal["passed", "failed", "not_run", "blocked"]
    command: str = Field(min_length=1, max_length=500)
    exit_code: int | None = None
    executed_at: datetime
    human_reviewer: str | None = Field(default=None, max_length=160)


RECORD_MODELS: dict[RecordType, type[StrictModel]] = {
    RecordType.LEARNER_CONTEXT: LearnerContextV1,
    RecordType.FORMATION_PLAN: FormationPlanV1,
    RecordType.PRACTICE_CHECKIN: PracticeCheckInV1,
    RecordType.AI_USE_INTENT: AiUseIntentV1,
    RecordType.RECOVERY_BOUNDARY_PLAN: BoundaryPlanV1,
    RecordType.PARENT_FORMATION_PLAN: BoundaryPlanV1,
    RecordType.FAMILY_COVENANT: FamilyCovenantV1,
    RecordType.CHILD_CAREGIVER_PLAN: BoundaryPlanV1,
    RecordType.YOUTH_AUTONOMY_PLAN: BoundaryPlanV1,
    RecordType.CURRICULUM_DRAFT: CurriculumDraftV1,
    RecordType.SCENARIO_SESSION: ScenarioSessionV1,
    RecordType.TWIN_CONSENT: TwinConsentV1,
}


def validate_record_payload(record_type: RecordType, payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a record without accepting unknown fields."""

    return RECORD_MODELS[record_type].model_validate(payload).model_dump(mode="json")
