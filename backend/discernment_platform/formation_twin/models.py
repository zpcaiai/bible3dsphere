from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class EvidenceQuality(str, Enum):
    E0 = "E0"
    E1 = "E1"
    E2 = "E2"
    E3 = "E3"
    E4 = "E4"


class RelapseState(str, Enum):
    STABLE = "STABLE"
    VULNERABLE = "VULNERABLE"
    TRIGGERED = "TRIGGERED"
    OLD_PATTERN_ACTIVE = "OLD_PATTERN_ACTIVE"
    CONSEQUENCE_VISIBLE = "CONSEQUENCE_VISIBLE"
    AWARENESS = "AWARENESS"
    RETURN_TO_GOSPEL = "RETURN_TO_GOSPEL"
    REPAIR = "REPAIR"
    REINTEGRATED = "REINTEGRATED"
    UNACKNOWLEDGED = "UNACKNOWLEDGED"
    SHAME_SPIRAL = "SHAME_SPIRAL"
    AVOIDANCE = "AVOIDANCE"
    SAFETY_HOLD = "SAFETY_HOLD"
    HUMAN_SUPPORT_REQUIRED = "HUMAN_SUPPORT_REQUIRED"


class FormationEvent(BaseModel):
    event_id: str
    user_id: str
    occurred_at: str
    context: str
    trigger: str
    automatic_interpretation: str = ""
    desire_or_fear: list[str] = Field(default_factory=list)
    active_belief: list[str] = Field(default_factory=list)
    emotion: list[str] = Field(default_factory=list)
    body_signal: list[str] = Field(default_factory=list)
    chosen_action: list[str] = Field(default_factory=list)
    avoided_action: list[str] = Field(default_factory=list)
    relationship_effect: list[str] = Field(default_factory=list)
    immediate_reward: list[str] = Field(default_factory=list)
    delayed_cost: list[str] = Field(default_factory=list)
    gospel_truth_recalled: list[str] = Field(default_factory=list)
    repair_action: list[str] = Field(default_factory=list)
    outcome: str = ""
    source_type: str = "self_report"
    evidence_quality: EvidenceQuality = EvidenceQuality.E1
    consent_scope: dict = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class FormationChain(BaseModel):
    chain_id: str
    event_id: str
    trigger: str
    interpretation: str
    desire: list[str]
    belief: list[str]
    emotion_body: list[str]
    action: list[str]
    relationship_effect: list[str]
    short_reward: list[str]
    long_cost: list[str]
    fruit: list[str]
    gospel_alternative: dict = Field(default_factory=dict)
    hypotheses: list[dict] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class WindowReview(BaseModel):
    review_id: str
    user_id: str
    window_days: int
    findings: list[dict]
    recovery_metrics: dict = Field(default_factory=dict)
    transfer_evidence: list[dict] = Field(default_factory=list)
    relational_feedback: list[dict] = Field(default_factory=list)
    identity_migration: dict = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class RelationshipRepair(BaseModel):
    repair_id: str
    relationship_id: str
    harm_named: bool
    responsibility_taken: bool
    excuse_free: bool
    behavior_change: bool
    boundary_respected: bool
    restitution_or_compensation: list[str] = Field(default_factory=list)
    third_party_accountability: list[str] = Field(default_factory=list)
    status: str
    limitations: list[str] = Field(default_factory=list)


class IdentityMigration(BaseModel):
    migration_id: str
    old_identity_basis: list[str]
    gospel_identity_truth: list[str]
    interpretation_shift: list[str] = Field(default_factory=list)
    desire_shift: list[str] = Field(default_factory=list)
    action_shift: list[str] = Field(default_factory=list)
    relationship_shift: list[str] = Field(default_factory=list)
    relapse_response_shift: list[str] = Field(default_factory=list)
    evidence_dimensions: list[dict] = Field(default_factory=list)
    status: str = "unassessed"
    limitations: list[str] = Field(default_factory=list)
