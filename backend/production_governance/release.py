"""Release, kill-switch, shadow, canary, SLO and compliance governance."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


COMPONENT_TYPES = {
    "MODEL", "PROMPT", "RULE", "POLICY", "CONTEXT_PROJECTION", "EVENT_SCHEMA",
    "WORKFLOW", "INTERVENTION_TEMPLATE", "THEOLOGICAL_SAFETY_POLICY", "CRISIS_POLICY",
}
HIGH_RISK_COMPONENTS = {"MODEL", "PROMPT", "CRISIS_POLICY", "THEOLOGICAL_SAFETY_POLICY", "WORKFLOW"}
REQUIRED_RELEASE_GATES = {
    "UNIT", "INTEGRATION", "CONTRACT", "E2E", "PRIVACY", "SECURITY", "RED_TEAM",
    "THEOLOGICAL_SAFETY", "CRISIS_SAFETY", "PERFORMANCE", "MIGRATION", "ROLLBACK",
    "DATA_QUALITY", "ACCESSIBILITY",
}
NON_BUDGETABLE_SAFETY_ERRORS = {
    "CROSS_TENANT_ACCESS", "AUTOMATIC_THIRD_PARTY_SHARE", "DIVINE_ORACLE",
    "CRISIS_MISSED_ROUTE", "SENSITIVE_LOG_LEAK", "CONSENT_BYPASS", "DELETION_RESIDUAL",
}
SLO_TARGETS = {
    "context_broker_availability": {"target": 0.999, "degrade": "SOURCE_MODULE_NAVIGATION"},
    "unified_home_availability": {"target": 0.999, "degrade": "SOURCE_MODULE_NAVIGATION"},
    "user_write_success": {"target": 0.9995, "degrade": "RETRYABLE_LOCAL_DRAFT"},
    "crisis_route_availability": {"target": 0.9999, "degrade": "STATIC_CRISIS_AND_HUMAN_SUPPORT"},
    "consent_revocation_p95_seconds": {"target": 60, "degrade": "FREEZE_DERIVED_PROCESSING"},
    "share_revocation_p95_seconds": {"target": 30, "degrade": "FREEZE_RELATIONAL_SHARING"},
    "context_broker_p95_ms": {"target": 500, "degrade": "SHORT_CACHED_PROJECTION"},
    "mirror_p95_ms": {"target": 5000, "degrade": "RULE_TEMPLATE_ONLY"},
    "cross_tenant_access": {"target": 0, "degrade": "GLOBAL_READ_KILL_SWITCH"},
    "sensitive_log_leak": {"target": 0, "degrade": "STOP_AFFECTED_PIPELINE"},
}


class GovernedComponentVersion(BaseModel):
    component_type: str
    component_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]+$", max_length=120)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    artifact_reference: str = Field(min_length=1, max_length=500)
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    evaluation_report_ids: list[str] = Field(default_factory=list, max_length=40)
    approved_environments: list[str] = Field(default_factory=list, max_length=8)
    risk_classification: str = "MEDIUM"
    approval_status: str = "DRAFT"
    created_by: str = Field(min_length=1, max_length=160)
    approved_by: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def production_rules(self):
        if self.component_type not in COMPONENT_TYPES:
            raise ValueError("unregistered governed component type")
        if self.version.lower() == "latest" or self.artifact_reference.rstrip("/").endswith("/latest"):
            raise ValueError("production components cannot use latest")
        if "PRODUCTION" in self.approved_environments:
            if self.approval_status != "APPROVED":
                raise ValueError("production component must be approved")
            if not self.evaluation_report_ids:
                raise ValueError("production component needs an evaluation report")
            required = 2 if self.component_type in HIGH_RISK_COMPONENTS or self.risk_classification in {"HIGH", "CRITICAL"} else 1
            if len(set(self.approved_by)) < required:
                raise ValueError("production approval count is insufficient")
        return self


class ReleaseCandidateSpec(BaseModel):
    release_key: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]+$", max_length=120)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    changed_components: list[str] = Field(min_length=1, max_length=100)
    migration_ids: list[str] = Field(default_factory=list, max_length=40)
    evaluation_report_ids: list[str] = Field(default_factory=list, max_length=100)
    security_scan_ids: list[str] = Field(default_factory=list, max_length=40)
    performance_report_ids: list[str] = Field(default_factory=list, max_length=40)
    rollback_plan_reference: str = Field(min_length=1, max_length=500)
    incident_owner: str = Field(min_length=1, max_length=160)
    gate_results: dict[str, str] = Field(default_factory=dict)
    approvals: dict[str, str] = Field(default_factory=dict)
    relational_collaboration_changed: bool = False
    crisis_changed: bool = False


def evaluate_release_candidate(
    candidate: ReleaseCandidateSpec, *, severe_failure_codes: list[str] | None = None,
    batch08_available: bool = False,
) -> dict[str, Any]:
    blockers: list[str] = []
    missing = sorted(REQUIRED_RELEASE_GATES - set(candidate.gate_results))
    failed = sorted(key for key, value in candidate.gate_results.items() if value != "PASSED")
    if missing: blockers.append("MISSING_GATES:" + ",".join(missing))
    if failed: blockers.append("FAILED_GATES:" + ",".join(failed))
    if not candidate.evaluation_report_ids: blockers.append("EVALUATION_REPORT_REQUIRED")
    if not candidate.security_scan_ids: blockers.append("SECURITY_SCAN_REQUIRED")
    if not candidate.performance_report_ids: blockers.append("PERFORMANCE_REPORT_REQUIRED")
    if not candidate.rollback_plan_reference: blockers.append("ROLLBACK_PLAN_REQUIRED")
    required_approvals = {"ENGINEERING", "SECURITY_PRIVACY", "PRODUCT", "PASTORAL_SAFETY"}
    if candidate.crisis_changed: required_approvals.add("CRISIS_SAFETY")
    if candidate.relational_collaboration_changed: required_approvals.add("RELATIONAL_SAFETY")
    missing_approvals = sorted(role for role in required_approvals if candidate.approvals.get(role) != "APPROVED")
    if missing_approvals: blockers.append("MISSING_APPROVALS:" + ",".join(missing_approvals))
    severe = sorted(set(severe_failure_codes or []))
    if severe: blockers.append("SEVERE_SAFETY_FAILURE:" + ",".join(severe))
    if candidate.relational_collaboration_changed and not batch08_available:
        blockers.append("BATCH_08_RELATIONAL_COLLABORATION_NOT_AVAILABLE")
    return {"passed": not blockers, "blockers": blockers, "required_gates": sorted(REQUIRED_RELEASE_GATES)}


class ShadowRunSpec(BaseModel):
    component_id: str
    production_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    candidate_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    consent_scope_hash: str = Field(min_length=32, max_length=128)
    side_effects: list[str] = Field(default_factory=list)
    writes_to_user_twin: bool = False
    sends_notification: bool = False
    creates_action: bool = False
    retention_days: int = Field(default=7, ge=1, le=30)

    @model_validator(mode="after")
    def no_side_effects(self):
        if self.side_effects or self.writes_to_user_twin or self.sends_notification or self.creates_action:
            raise ValueError("shadow mode must have no user-visible or source-module side effects")
        return self


def canary_bucket(*, subject_reference: str, release_key: str, percentage: int, opt_in: bool = False) -> bool:
    if not 0 <= percentage <= 100:
        raise ValueError("canary percentage must be between 0 and 100")
    if opt_in:
        return True
    digest = hashlib.sha256(f"{release_key}:{subject_reference}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % 100 < percentage


def validate_canary_selector(selector_fields: list[str]) -> None:
    sensitive = {
        "emotion", "temptation_type", "crisis_status", "church", "spiritual_pattern",
        "payment_capacity", "relapse_history", "relationship_status",
    }
    if {item.lower() for item in selector_fields} & sensitive:
        raise ValueError("canary selection cannot use sensitive user attributes")


def kill_switch_degradation(scope_reference: str) -> dict[str, Any]:
    mapping = {
        "SCENARIO_SIMULATION": ["MANUAL_RECORDING", "CURRENT_STATE", "CRISIS_ENTRY"],
        "MODEL_INFERENCE": ["USER_REPORTED_FACTS", "RULE_RESULTS", "CRISIS_ENTRY"],
        "RELATIONAL_SHARING": ["EXISTING_ACCESS_FROZEN", "AUDIT_VISIBLE", "CRISIS_ENTRY"],
        "EARLY_WARNING": ["PROTECTION_PLAN", "MANUAL_SUPPORT", "CRISIS_ENTRY"],
        "NOTIFICATIONS": ["IN_APP_STATUS", "CRISIS_ENTRY"],
    }
    return {"disabled": scope_reference, "remaining_capabilities": mapping.get(scope_reference, ["MANUAL_RECORDING", "CRISIS_ENTRY"])}


def cost_route(task_family: str, *, budget_exceeded: bool = False, crisis_related: bool = False) -> dict[str, str]:
    if crisis_related:
        return {"tier": "RULE_ONLY", "degradation": "NONE", "reason": "CRISIS_MUST_NOT_DEPEND_ON_MODEL_BUDGET"}
    deterministic = {"CONSENT", "DELETION", "RULE_REPLAY", "NOTIFICATION_REDACTION", "SCHEMA_VALIDATION"}
    if task_family in deterministic or budget_exceeded:
        return {"tier": "RULE_ONLY", "degradation": "RULE_OR_TEMPLATE", "reason": "DETERMINISTIC_OR_BUDGET_SAFE"}
    return {"tier": "SMALL_MODEL", "degradation": "RULE_OR_TEMPLATE", "reason": "BOUNDED_TASK"}


def error_budget_decision(error_codes: list[str]) -> dict[str, Any]:
    safety = sorted(set(error_codes) & NON_BUDGETABLE_SAFETY_ERRORS)
    return {"release_frozen": bool(safety), "non_budgetable_errors": safety, "ordinary_budget_allowed": not safety}


def sanitize_governance_metadata(value: dict[str, Any]) -> dict[str, Any]:
    prohibited = {
        "email", "user_id", "journal", "prayer", "confession", "temptation", "crisis_body",
        "feedback_body", "prompt", "exploit", "secret", "internal_risk_band",
    }
    if {key.lower() for key in value} & prohibited:
        raise ValueError("sensitive governance metrics or report metadata is prohibited")
    allowed = {"component", "version", "result", "reason_code", "latency_ms", "cost_tier", "release_id", "environment"}
    return {key: str(item)[:200] for key, item in value.items() if key in allowed}


class RightsRequestSpec(BaseModel):
    request_type: str
    scope: dict[str, Any] = Field(default_factory=dict)

    @field_validator("request_type")
    @classmethod
    def known_right(cls, value: str) -> str:
        allowed = {
            "VIEW_DATA", "EXPORT_DATA", "CORRECT_DATA", "DELETE_DATA", "RESTRICT_PROCESSING",
            "WITHDRAW_CONSENT", "OBJECT_TO_MODEL_PROCESSING", "DISABLE_PROFILING",
            "DISABLE_PASSIVE_METADATA", "DISABLE_RELATIONAL_SHARING", "REQUEST_PROCESSING_RECORD",
        }
        if value not in allowed:
            raise ValueError("unsupported rights request")
        return value


def processing_transparency() -> dict[str, Any]:
    return {
        "notices": [
            "Formation Pattern 是可修正假设。", "Scenario 是有限情景，不是预测。",
            "Warning 是条件提醒，不是复发概率。", "Mirror 不代表神的最终评价。",
        ],
        "rights": [
            "VIEW_DATA", "EXPORT_DATA", "CORRECT_DATA", "DELETE_DATA", "RESTRICT_PROCESSING",
            "WITHDRAW_CONSENT", "OBJECT_TO_MODEL_PROCESSING", "DISABLE_PROFILING",
        ],
        "legal_notice": "具体法律适用性需要由合格专业人员按运营地区确认。",
    }
