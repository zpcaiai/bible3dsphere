from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class Severity(str, Enum):
    C0 = "C0"
    C1 = "C1"
    C2 = "C2"
    C3 = "C3"
    C4 = "C4"


class ReleaseStatus(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    EVALUATING = "EVALUATING"
    BLOCKED = "BLOCKED"
    CONDITIONAL_APPROVAL = "CONDITIONAL_APPROVAL"
    APPROVED_FOR_PILOT = "APPROVED_FOR_PILOT"
    APPROVED_FOR_PRODUCTION = "APPROVED_FOR_PRODUCTION"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class ReleaseCandidate(BaseModel):
    release_id: str
    build_hash: str
    batch_manifests: list[dict]
    model_versions: list[dict]
    prompt_versions: list[dict] = Field(default_factory=list)
    policy_versions: list[dict]
    knowledge_versions: list[dict] = Field(default_factory=list)
    target_scope: str
    jurisdictions: list[str] = Field(default_factory=list)
    enabled_features: list[str] = Field(default_factory=list)
    disabled_features: list[str] = Field(default_factory=list)


class CertificationControl(BaseModel):
    control_id: str
    domain_id: str
    requirement: str
    severity: Severity
    automated: bool
    decision_rule: str
    required_evidence_types: list[str] = Field(default_factory=list)
    human_review_role: str = ""
    expires_after_days: int = 90
    references: list[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    evidence_id: str
    control_id: str
    evidence_type: str
    locator: str
    hash: str = ""
    status: str
    collected_at: str
    expires_at: str = ""
    reviewer: str = ""
    limitations: list[str] = Field(default_factory=list)


class Finding(BaseModel):
    finding_id: str
    control_id: str
    severity: Severity
    title: str
    description: str = ""
    status: str = "open"
    owner: str = ""
    due_at: str = ""
    mitigations: list[str] = Field(default_factory=list)
    verification_evidence_ids: list[str] = Field(default_factory=list)
    release_blocking: bool = False
    limitations: list[str] = Field(default_factory=list)


class DomainResult(BaseModel):
    result_id: str
    domain_id: str
    control_results: list[dict]
    critical_blockers: list[str] = Field(default_factory=list)
    score: float = 0
    decision: str
    limitations: list[str] = Field(default_factory=list)
    expires_at: str = ""


class ReleaseCertificate(BaseModel):
    certificate_id: str
    release_id: str
    status: ReleaseStatus
    issued_at: str
    expires_at: str
    scope: dict
    domain_results: list[dict]
    open_findings: list[str] = Field(default_factory=list)
    accepted_risks: list[dict] = Field(default_factory=list)
    feature_restrictions: list[str] = Field(default_factory=list)
    rollback_target: str
    recertification_triggers: list[str]
    signatories: list[dict]
    signature_hash: str
