from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class DataLevel(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class ReviewLevel(str, Enum):
    R0 = "R0"
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"
    R4 = "R4"


class EscalationState(str, Enum):
    ROUTINE = "ROUTINE"
    REVIEW_NEEDED = "REVIEW_NEEDED"
    PASTORAL_REVIEW = "PASTORAL_REVIEW"
    SAFEGUARDING_REVIEW = "SAFEGUARDING_REVIEW"
    PROFESSIONAL_REFERRAL = "PROFESSIONAL_REFERRAL"
    EMERGENCY_ACTION = "EMERGENCY_ACTION"
    STABILIZED = "STABILIZED"
    FOLLOW_UP = "FOLLOW_UP"
    CLOSED = "CLOSED"
    CONFLICT_OF_INTEREST_HOLD = "CONFLICT_OF_INTEREST_HOLD"
    CONSENT_REVIEW = "CONSENT_REVIEW"
    LEGAL_DUTY_REVIEW = "LEGAL_DUTY_REVIEW"
    EXTERNAL_REPORT_REQUIRED = "EXTERNAL_REPORT_REQUIRED"
    APPEAL_OR_SECOND_REVIEW = "APPEAL_OR_SECOND_REVIEW"


class Actor(BaseModel):
    actor_id: str
    display_name: str
    roles: list[str]
    tenant_id: str
    church_relationships: list[dict] = Field(default_factory=list)
    professional_credentials: list[dict] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    status: str = "active"


class ConsentGrant(BaseModel):
    grant_id: str
    subject_user_id: str
    recipient_actor_id: str
    purpose: str
    allowed_categories: list[str]
    denied_categories: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    expires_at: str
    reshare_allowed: bool = False
    revocable: bool = True
    status: str = "active"
    limitations: list[str] = Field(default_factory=list)


class PastoralCase(BaseModel):
    case_id: str
    subject_user_id: str
    purpose: str
    sensitivity: DataLevel
    status: str
    assigned_roles: list[str]
    source_artifacts: list[str] = Field(default_factory=list)
    active_questions: list[str] = Field(default_factory=list)
    safety_flags: list[str] = Field(default_factory=list)
    retention_policy: dict = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class Disclosure(BaseModel):
    disclosure_id: str
    case_id: str
    recipient_actor_id: str
    purpose: str
    selected_fields: list[str]
    redacted_fields: list[str] = Field(default_factory=list)
    expires_at: str
    basis: str
    reshare_policy: str = "forbidden"
    audit_id: str
    limitations: list[str] = Field(default_factory=list)
