from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


SubjectType = Literal["idea", "person", "event", "product", "media", "self_reflection", "mixed"]
FaithContext = Literal["christian", "seeker", "unknown", "other"]
Sensitivity = Literal["normal", "pastoral", "mental_health", "abuse", "crisis", "reputation_sensitive", "legal_sensitive", "minor_involved"]


class ConsentScope(BaseModel):
    allow_spiritual_analysis: bool = False
    allow_gospel_bridge: bool = False
    allow_public_content_analysis: bool = False
    allow_longitudinal_memory: bool = False


class SourceItem(BaseModel):
    source_type: str = Field(min_length=1, max_length=80)
    locator: str = Field(min_length=1, max_length=1000)
    quote: str | None = Field(default=None, max_length=2000)
    evidence_level: Literal["E0", "E1", "E2", "E3", "E4", "P0", "P1", "P2", "P3", "P4"] = "E1"
    independence_group: str | None = Field(default=None, max_length=120)
    limitations: list[str] = Field(default_factory=list, max_length=20)


class DiscernmentCaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    subject_type: SubjectType
    raw_input: str = Field(min_length=1, max_length=12000)
    user_goal: str = Field(min_length=1, max_length=1000)
    faith_context: FaithContext = "unknown"
    consent_scope: ConsentScope
    sensitivity: Sensitivity = "normal"
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    source_items: list[SourceItem] = Field(default_factory=list, max_length=100)

    @field_validator("title", "raw_input", "user_goal")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.strip().split())


class DialogueStart(BaseModel):
    preferred_depth: Literal["brief", "standard", "deep"] = "standard"


class DialogueTurn(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)
    gospel_consent: Literal["not_asked", "accepted", "declined", "later", "unclear"] | None = None


class ReviewRequest(BaseModel):
    action: Literal["REQUEST_REVIEW", "CORRECT", "WITHDRAW"]
    note: str = Field(default="", max_length=4000)
    correction: dict[str, Any] = Field(default_factory=dict)


class AdminReviewDecision(BaseModel):
    decision: Literal["APPROVED", "CHANGES_REQUIRED", "BLOCKED"]
    note: str = Field(min_length=1, max_length=4000)


class GospelPathRequest(BaseModel):
    preferred_depth: Literal["brief", "standard", "deep"] = "standard"
    church_context: str = Field(default="", max_length=1000)


class FormationEventCreate(BaseModel):
    case_id: UUID | None = None
    occurred_at: datetime
    context: str = Field(min_length=1, max_length=500)
    trigger: str = Field(min_length=1, max_length=1000)
    automatic_interpretation: str = Field(default="", max_length=2000)
    desire_or_fear: list[str] = Field(default_factory=list, max_length=20)
    active_belief: list[str] = Field(default_factory=list, max_length=20)
    emotion: list[str] = Field(default_factory=list, max_length=20)
    body_signal: list[str] = Field(default_factory=list, max_length=20)
    chosen_action: list[str] = Field(default_factory=list, max_length=20)
    avoided_action: list[str] = Field(default_factory=list, max_length=20)
    relationship_effect: list[str] = Field(default_factory=list, max_length=20)
    immediate_reward: list[str] = Field(default_factory=list, max_length=20)
    delayed_cost: list[str] = Field(default_factory=list, max_length=20)
    gospel_truth_recalled: list[str] = Field(default_factory=list, max_length=20)
    repair_action: list[str] = Field(default_factory=list, max_length=20)
    outcome: str = Field(default="", max_length=2000)
    source_type: Literal["self_report", "mentor_feedback", "system_inference"] = "self_report"
    evidence_quality: Literal["E0", "E1", "E2", "E3", "E4"] = "E1"
    data_level: Literal["L0", "L1", "L2", "L3"] = "L1"
    consent_to_tracking: bool = False
    limitations: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include timezone")
        return value


class FormationReviewRequest(BaseModel):
    window_days: Literal[14, 30, 90]


class RelapseTransitionRequest(BaseModel):
    current: str = Field(min_length=1, max_length=50)
    target: str = Field(min_length=1, max_length=50)


class RelationshipRepairRequest(BaseModel):
    relationship_id: str = Field(min_length=1, max_length=160)
    harm_named: bool
    responsibility_taken: bool
    excuse_free: bool
    behavior_change: bool
    boundary_respected: bool
    restitution_or_compensation: list[str] = Field(default_factory=list, max_length=20)
    third_party_accountability: list[str] = Field(default_factory=list, max_length=20)
    status: Literal["started", "in_progress", "completed", "paused_for_safety"] = "started"
    limitations: list[str] = Field(default_factory=list, max_length=20)


class IdentityMigrationRequest(BaseModel):
    old_identity_basis: list[str] = Field(default_factory=list, max_length=20)
    gospel_identity_truth: list[str] = Field(default_factory=list, max_length=20)
    interpretation_shift: list[str] = Field(default_factory=list, max_length=20)
    desire_shift: list[str] = Field(default_factory=list, max_length=20)
    action_shift: list[str] = Field(default_factory=list, max_length=20)
    relationship_shift: list[str] = Field(default_factory=list, max_length=20)
    relapse_response_shift: list[str] = Field(default_factory=list, max_length=20)
    evidence_dimensions: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=20)


class CollaborationConsentCreate(BaseModel):
    recipient_email: str = Field(min_length=3, max_length=320)
    recipient_role: Literal[
        "accountability_partner", "small_group_leader", "mentor_discipler", "pastor_elder",
        "safeguarding_officer", "licensed_professional", "governance_review_panel",
    ]
    purpose: str = Field(min_length=3, max_length=500)
    allowed_categories: list[Literal["L0", "L1", "L2", "L3"]] = Field(min_length=1, max_length=4)
    allowed_actions: list[str] = Field(default_factory=list, max_length=20)
    expires_at: datetime
    reshare_allowed: bool = False

    @field_validator("recipient_email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("recipient_email must be an email address")
        return normalized


class DisclosureCreate(BaseModel):
    consent_id: UUID
    case_id: UUID | None = None
    purpose: str = Field(min_length=3, max_length=500)
    requested_fields: list[str] = Field(min_length=1, max_length=50)
    data_level: Literal["L0", "L1", "L2", "L3"]
    expires_at: datetime


class MeetingPrepCreate(BaseModel):
    consent_id: UUID
    case_id: UUID
    meeting_purpose: str = Field(min_length=3, max_length=500)
    user_selected_focus: list[str] = Field(default_factory=list, max_length=10)
    last_agreements: list[str] = Field(default_factory=list, max_length=10)
    uncertainties: list[str] = Field(default_factory=list, max_length=10)
    priority_question: str = Field(min_length=1, max_length=1000)
    gospel_truth: str = Field(default="", max_length=1000)
    action_option: str = Field(default="", max_length=1000)
    do_not_use_language: list[str] = Field(default_factory=list, max_length=20)


class TheologySourceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    source_type: str = Field(min_length=1, max_length=80)
    language: str = Field(min_length=1, max_length=40)
    rights_status: Literal[
        "public_domain", "open_license", "licensed_internal", "user_owned", "quotation_only",
        "metadata_only", "prohibited_for_embedding", "prohibited_for_generation",
    ]
    version: str = Field(min_length=1, max_length=120)
    author: list[str] = Field(default_factory=list, max_length=20)
    edition: str = Field(default="", max_length=300)
    publisher: str = Field(default="", max_length=300)
    year: str = Field(default="", max_length=20)
    quality_tier: Literal["Q0", "Q1", "Q2", "Q3", "Q4"] = "Q1"
    limitations: list[str] = Field(default_factory=list, max_length=20)
    user_confirms_rights: bool = False


class TheologyCitationInput(BaseModel):
    source_id: UUID
    locator: str = Field(min_length=1, max_length=1000)
    quote_text: str = Field(min_length=1, max_length=2000)
    extraction_method: Literal["manual", "licensed_retrieval", "user_upload"] = "manual"
    verification_status: Literal["unverified", "user_verified", "human_verified"] = "unverified"
    limitations: list[str] = Field(default_factory=list, max_length=20)


class TheologyQueryCreate(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    intent: Literal["scripture_exegesis", "doctrine", "pastoral_application", "misuse_review"]
    source_ids: list[UUID] = Field(default_factory=list, max_length=50)
    citations: list[TheologyCitationInput] = Field(default_factory=list, max_length=50)
    allowed_rights: list[str] = Field(default_factory=lambda: ["public_domain", "open_license", "licensed_internal", "user_owned", "quotation_only"], max_length=8)
    required_source_types: list[str] = Field(default_factory=list, max_length=20)
    scripture_refs: list[str] = Field(default_factory=list, max_length=20)
    scripture_context: dict[str, str] = Field(default_factory=dict)
    tradition_scope: list[str] = Field(default_factory=list, max_length=20)
    doctrine_tier: Literal["D1", "D2", "D3"] = "D3"
    consensus_level: str = Field(default="open_question", max_length=80)
    used_as_salvation_test: bool = False
    proposed_application: str = Field(default="", max_length=2000)
    depth: Literal["brief", "standard", "deep"] = "standard"
    human_review_level: Literal["R0", "R1", "R2", "R3", "R4"] = "R0"


class CertificationEvaluationCreate(BaseModel):
    build_hash: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    target_scope: Literal["pilot", "production"]
    model_versions: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    prompt_versions: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    policy_versions: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    knowledge_versions: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    jurisdictions: list[str] = Field(default_factory=list, max_length=20)
    enabled_features: list[str] = Field(default_factory=list, max_length=100)
    disabled_features: list[str] = Field(default_factory=list, max_length=100)
    evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=1000)
    findings: list[dict[str, Any]] = Field(default_factory=list, max_length=500)
    signatories: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    rollback_ready: bool = False
    rollback_target: str = Field(default="", max_length=500)
    recertification_enabled: bool = False
    recertification_triggers: list[str] = Field(default_factory=list, max_length=30)
    expires_at: datetime
    accepted_risks: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    feature_restrictions: list[str] = Field(default_factory=list, max_length=100)


class RecertificationTriggerCreate(BaseModel):
    trigger_type: Literal[
        "model_change", "prompt_change", "policy_change", "pack_change", "new_jurisdiction",
        "new_high_risk_feature", "incident", "authorization_change", "data_migration", "scheduled_expiry",
    ]
    details: dict[str, Any] = Field(default_factory=dict)
