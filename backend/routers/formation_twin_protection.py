"""Formation Twin Batch 7 user-confirmed risk and protection API."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator, model_validator
from psycopg2.extras import Json, RealDictCursor

from formation_twin.temptation_risk import (
    ACTIVE_CYCLE_STATUSES,
    ENGINE_VERSION,
    PUBLISHED_EVENTS,
    RULE_VERSION,
    SENSITIVE_CYCLE_TYPES,
    WORKFLOW_NODES,
    ActiveProtection,
    CycleCondition,
    EvidenceReference,
    ProtectionAction,
    TemptationCycle,
    apply_warning_policy,
    build_protection_route,
    generate_warning,
    learn_warning_feedback,
    make_protection_action_smaller,
    match_risk_context,
    risk_data_quality,
    sanitize_notification_content,
    select_protection_action,
    start_recovery,
    validate_model_candidates,
    validate_passive_signal,
    validate_safe_text,
)


router = APIRouter(prefix="/api/v1/formation-twin", tags=["formation-twin-protection"])
_state: dict[str, Any] = {}


def init_formation_twin_protection_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _user(request: Request) -> dict[str, Any]:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _identity(email: str) -> tuple[str, str]:
    normalized = email.lower()
    return f"personal:{normalized}", str(uuid.uuid5(uuid.NAMESPACE_URL, f"formation-twin:{normalized}"))


def _cursor(conn):
    return conn.cursor(cursor_factory=RealDictCursor)


def _owner(cur, email: str) -> None:
    cur.execute("SELECT set_config('app.current_user_email',%s,true)", (email,))


def _json(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(item) for item in value]
    return value


def _publish(cur, email: str, event_type: str, payload: dict[str, Any]) -> None:
    if event_type not in PUBLISHED_EVENTS:
        raise ValueError("unregistered Formation Twin protection event")
    allowed = {
        "cycle_id", "snapshot_id", "warning_id", "action_id", "plan_id", "request_id",
        "recovery_id", "review_id", "status", "warning_level", "action_type",
        "target_module", "delivery_status", "engine_version", "rule_version",
    }
    safe = {key: _json(value) for key, value in payload.items() if key in allowed}
    cur.execute(
        "INSERT INTO domain_events (aggregate_type,aggregate_id,event_type,payload) VALUES (%s,%s,%s,%s)",
        ("formation_twin", email, event_type, Json(safe)),
    )


def _ensure_settings(cur, email: str) -> dict[str, Any]:
    tenant, profile = _identity(email)
    cur.execute(
        "INSERT INTO formation_twin_risk_settings (id,tenant_id,profile_id,email) "
        "VALUES (%s,%s,%s,%s) ON CONFLICT (tenant_id,profile_id) DO NOTHING",
        (str(uuid.uuid4()), tenant, profile, email),
    )
    cur.execute("SELECT * FROM formation_twin_risk_settings WHERE email=%s", (email,))
    return dict(cur.fetchone())


def _cycle_from_row(row: dict[str, Any], nodes: list[dict[str, Any]] | None = None) -> TemptationCycle:
    rule = dict(row.get("rule_json") or {})
    nodes = nodes or []
    return TemptationCycle(
        cycle_id=str(row["id"]), title=row["title"], cycle_type=row["cycle_type"],
        trigger_conditions=row.get("trigger_conditions_json") or [],
        vulnerability_conditions=row.get("vulnerability_conditions_json") or [],
        emotional_conditions=row.get("emotional_conditions_json") or [],
        environmental_conditions=row.get("environmental_conditions_json") or [],
        temptation_nodes=[item for item in nodes if item.get("node_type") in {"URGE", "TEMPTATION", "CHOICE_POINT"}],
        choice_points=[item for item in nodes if item.get("node_type") == "CHOICE_POINT"],
        behavior_path=[item for item in nodes if item.get("node_type") in {"BEHAVIOR_INITIATION", "BEHAVIOR_CONTINUATION", "BEHAVIOR_OCCURRED"}],
        protective_factors=row.get("protective_factors_json") or [],
        interruption_points=row.get("interruption_points_json") or [],
        recovery_paths=row.get("recovery_paths_json") or [],
        required_conditions=rule.get("required_conditions") or [],
        optional_conditions=rule.get("optional_conditions") or [],
        minimum_independent_conditions=rule.get("minimum_independent_conditions", 2),
        scope=row.get("scope_json") or {}, lifecycle_status=row["lifecycle_status"],
        source_kind=row["source_kind"], statement_type=row["statement_type"],
        user_review_status=row["user_review_status"],
        evidence_references=row.get("evidence_references_json") or [],
        counterevidence_references=row.get("counterevidence_references_json") or [],
        limitations=row.get("limitations_json") or [], version=row["version"],
        supersedes_cycle_id=str(row["supersedes_cycle_id"]) if row.get("supersedes_cycle_id") else None,
        user_confirmed=bool(row["user_confirmed"]),
    )


def _get_cycle(cur, email: str, cycle_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cur.execute(
        "SELECT * FROM formation_twin_temptation_cycles WHERE email=%s AND id=%s AND deleted_at IS NULL",
        (email, cycle_id),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Temptation cycle not found")
    cur.execute(
        "SELECT * FROM formation_twin_temptation_cycle_nodes WHERE email=%s AND cycle_id=%s AND deleted_at IS NULL ORDER BY sequence_order,id",
        (email, cycle_id),
    )
    return dict(row), [dict(item) for item in cur.fetchall()]


def _public_snapshot(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    blocked = {"internal_risk_band", "email", "tenant_id", "profile_id"}
    return {key: _json(value) for key, value in row.items() if key not in blocked}


class CycleNodeBody(BaseModel):
    node_type: Literal[
        "BASELINE", "TRIGGER", "VULNERABILITY", "EMOTIONAL_ESCALATION", "URGE",
        "TEMPTATION", "CHOICE_POINT", "BEHAVIOR_INITIATION", "BEHAVIOR_CONTINUATION",
        "BEHAVIOR_OCCURRED", "IMMEDIATE_OUTCOME", "SHAME_OR_CONCEALMENT", "ISOLATION",
        "RECOVERY", "RECONNECTION", "LEARNING", "INTERRUPTION", "PROTECTION",
    ]
    condition_code: str | None = Field(default=None, max_length=100)
    content: str = Field(min_length=1, max_length=500)

    @field_validator("content")
    @classmethod
    def safe_content(cls, value: str) -> str:
        validate_safe_text(value)
        return value


class CycleBody(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    cycle_type: str = Field(min_length=1, max_length=80)
    trigger_conditions: list[str] = Field(default_factory=list, max_length=20)
    vulnerability_conditions: list[str] = Field(default_factory=list, max_length=20)
    emotional_conditions: list[str] = Field(default_factory=list, max_length=20)
    environmental_conditions: list[str] = Field(default_factory=list, max_length=20)
    protective_factors: list[str] = Field(default_factory=list, max_length=20)
    interruption_points: list[str] = Field(default_factory=list, max_length=12)
    recovery_paths: list[str] = Field(default_factory=list, max_length=12)
    required_conditions: list[str] = Field(default_factory=list, max_length=20)
    optional_conditions: list[str] = Field(default_factory=list, max_length=20)
    minimum_independent_conditions: int = Field(default=2, ge=2, le=12)
    nodes: list[CycleNodeBody] = Field(default_factory=list, max_length=50)
    scope: dict[str, Any] = Field(default_factory=lambda: {"type": "CURRENT_SEASON"})
    source_kind: Literal["USER_BUILT", "USER_CONFIRMED_RULE_SUGGESTION", "USER_CONFIRMED_MODEL_SUGGESTION", "PASTORAL_CO_CREATED"] = "USER_BUILT"
    user_confirmed: bool = False
    limitations: list[str] = Field(default_factory=lambda: ["风险不是命运；循环只描述用户确认的有限情境。"], max_length=12)

    @field_validator("title")
    @classmethod
    def safe_title(cls, value: str) -> str:
        validate_safe_text(value)
        return value

    @model_validator(mode="after")
    def sensitive_confirmation(self):
        if self.cycle_type in SENSITIVE_CYCLE_TYPES and not self.user_confirmed:
            raise ValueError("sensitive cycle types require explicit user confirmation")
        if self.source_kind == "PASTORAL_CO_CREATED" and not self.user_confirmed:
            raise ValueError("pastoral co-created cycles require final user confirmation")
        return self


class CyclePatchBody(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    trigger_conditions: list[str] | None = Field(default=None, max_length=20)
    vulnerability_conditions: list[str] | None = Field(default=None, max_length=20)
    emotional_conditions: list[str] | None = Field(default=None, max_length=20)
    environmental_conditions: list[str] | None = Field(default=None, max_length=20)
    protective_factors: list[str] | None = Field(default=None, max_length=20)
    interruption_points: list[str] | None = Field(default=None, max_length=12)
    recovery_paths: list[str] | None = Field(default=None, max_length=12)
    required_conditions: list[str] | None = Field(default=None, max_length=20)
    optional_conditions: list[str] | None = Field(default=None, max_length=20)
    minimum_independent_conditions: int | None = Field(default=None, ge=2, le=12)
    scope: dict[str, Any] | None = None
    limitations: list[str] | None = Field(default=None, max_length=12)


class ConditionInput(BaseModel):
    condition_type: str = Field(min_length=1, max_length=80)
    condition_code: str = Field(min_length=1, max_length=100)
    user_visible_description: str = Field(min_length=1, max_length=240)
    source_kind: Literal["USER_REPORTED", "CONFIRMED_EMOTIONAL_STATE", "CONFIRMED_FORMATION_PATTERN", "CONSENTED_ENVIRONMENT_METADATA", "RULE_TIME_CONTEXT"] = "USER_REPORTED"
    statement_type: Literal["USER_REPORTED_FACT", "USER_CONFIRMED_INTERPRETATION"] = "USER_REPORTED_FACT"
    occurred_at: datetime | None = None
    expires_at: datetime | None = None
    evidence_references: list[EvidenceReference] = Field(default_factory=list, max_length=8)
    independence_group: str | None = Field(default=None, max_length=160)
    user_confirmed: bool = True
    passive_signal_type: str | None = None
    raw_content_uploaded: bool = False

    @field_validator("user_visible_description")
    @classmethod
    def safe_description(cls, value: str) -> str:
        validate_safe_text(value)
        return value


class ProtectionInput(BaseModel):
    protection_type: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=240)
    active: bool = True
    evidence_references: list[EvidenceReference] = Field(default_factory=list, max_length=8)


class StatusUpdateBody(BaseModel):
    conditions: list[ConditionInput] = Field(default_factory=list, max_length=20)
    active_protections: list[ProtectionInput] = Field(default_factory=list, max_length=12)
    explicit_urge: bool = False
    behavior_started: bool = False
    continuation_risk: bool = False
    crisis_level: Literal["NONE", "LOW", "ELEVATED", "IMMINENT"] = "NONE"
    user_requested_help: bool = False


class WarningFeedbackBody(BaseModel):
    feedback_type: Literal[
        "ACCURATE_AND_HELPFUL", "ACCURATE_NOT_HELPFUL", "TOO_EARLY", "TOO_LATE",
        "INACCURATE", "TOO_FREQUENT", "TOO_INTRUSIVE", "SENSITIVE_CONTENT_EXPOSED", "NO_FEEDBACK",
    ]
    user_comment: str | None = Field(default=None, max_length=1000)


class SnoozeBody(BaseModel):
    duration: Literal["10_MINUTES", "30_MINUTES", "TONIGHT", "24_HOURS", "THIS_CYCLE", "ALL_WARNINGS"] = "10_MINUTES"


class ActionDecisionBody(BaseModel):
    request_id: str | None = None
    user_confirmed: bool = True
    execution_mode: Literal["REMINDER_ONLY", "SOFT_BLOCK", "HARD_BLOCK", "ACCOUNTABILITY_UNLOCK"] = "REMINDER_ONLY"
    recovery_method_visible: bool = True


class ProtectionPlanBody(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    cycle_ids: list[str] = Field(default_factory=list, max_length=12)
    early_signs: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    high_risk_contexts: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    protective_actions: list[dict[str, Any]] = Field(default_factory=list, min_length=1, max_length=4)
    environment_boundaries: list[dict[str, Any]] = Field(default_factory=list, max_length=8)
    support_contact_ids: list[str] = Field(default_factory=list, max_length=8)
    spiritual_supports: list[dict[str, Any]] = Field(default_factory=list, max_length=8)
    professional_supports: list[dict[str, Any]] = Field(default_factory=list, max_length=8)
    sharing_policy: dict[str, Any] = Field(default_factory=lambda: {"mode": "PRIVATE_ONLY"})
    escalation_rules: list[dict[str, Any]] = Field(default_factory=list, max_length=8)
    user_confirmed: bool = False

    @model_validator(mode="after")
    def private_by_default(self):
        mode = self.sharing_policy.get("mode", "PRIVATE_ONLY")
        if mode != "PRIVATE_ONLY" and not self.user_confirmed:
            raise ValueError("sharing requires explicit user confirmation")
        return self


class ProtectionPlanPatchBody(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    early_signs: list[dict[str, Any]] | None = Field(default=None, max_length=20)
    high_risk_contexts: list[dict[str, Any]] | None = Field(default=None, max_length=20)
    protective_actions: list[dict[str, Any]] | None = Field(default=None, min_length=1, max_length=4)
    environment_boundaries: list[dict[str, Any]] | None = Field(default=None, max_length=8)
    support_contact_ids: list[str] | None = Field(default=None, max_length=8)
    sharing_policy: dict[str, Any] | None = None
    escalation_rules: list[dict[str, Any]] | None = Field(default=None, max_length=8)
    user_confirmed: bool = False


class SharePlanBody(BaseModel):
    support_contact_id: str
    share_fields: list[str] = Field(min_length=1, max_length=8)
    expires_at: datetime
    user_confirmed: Literal[True] = True

    @field_validator("expires_at")
    @classmethod
    def aware_expiry(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None or value <= datetime.now(timezone.utc):
            raise ValueError("future timezone-aware expiry required")
        return value


class SupportContactBody(BaseModel):
    contact_reference_id: str | None = Field(default=None, max_length=200)
    display_alias: str = Field(min_length=1, max_length=120)
    support_role: Literal[
        "ACCOUNTABILITY_PARTNER", "PASTOR", "MENTOR", "SPOUSE", "FAMILY_MEMBER",
        "FRIEND", "SMALL_GROUP_LEADER", "THERAPIST_OR_COUNSELOR",
        "MEDICAL_PROFESSIONAL", "USER_DEFINED",
    ]
    allowed_share_fields: list[str] = Field(default_factory=list, max_length=8)
    allowed_actions: list[str] = Field(default_factory=lambda: ["DRAFT_MESSAGE_ONLY"], max_length=6)
    sharing_expires_at: datetime | None = None


class SupportContactPatchBody(BaseModel):
    display_alias: str | None = Field(default=None, min_length=1, max_length=120)
    support_role: str | None = Field(default=None, max_length=60)
    allowed_share_fields: list[str] | None = Field(default=None, max_length=8)
    allowed_actions: list[str] | None = Field(default=None, max_length=6)
    sharing_expires_at: datetime | None = None
    active: bool | None = None


class DraftMessageBody(BaseModel):
    request_type: Literal["ONE_TIME_HELP_REQUEST", "ONE_TIME_STATUS_SHARE"] = "ONE_TIME_HELP_REQUEST"
    message: str = Field(default="我现在需要有人陪我说五分钟。", min_length=1, max_length=240)

    @field_validator("message")
    @classmethod
    def safe_message(cls, value: str) -> str:
        validate_safe_text(value)
        return value


class ShareRequestBody(BaseModel):
    request_type: Literal["ONE_TIME_HELP_REQUEST", "ONE_TIME_STATUS_SHARE", "TIME_LIMITED_PLAN_ACCESS"]
    share_fields: list[str] = Field(default_factory=list, max_length=8)
    expires_at: datetime | None = None
    user_confirmed: Literal[True] = True

    @model_validator(mode="after")
    def validate_expiry(self):
        if self.request_type == "TIME_LIMITED_PLAN_ACCESS":
            if self.expires_at is None or self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
                raise ValueError("time-limited sharing requires a timezone-aware expiry")
            if self.expires_at <= datetime.now(timezone.utc):
                raise ValueError("sharing expiry must be in the future")
        return self


class RecoveryStartBody(BaseModel):
    event_type: Literal["BEHAVIOR_STARTED", "USER_REPORTED_RELAPSE", "USER_REQUESTED_RECOVERY"]
    occurred_at: datetime
    immediate_safety_status: Literal["UNKNOWN", "SAFE", "UNSAFE", "CRISIS"] = "UNKNOWN"
    continuation_risk: Literal["UNKNOWN", "LOW", "ELEVATED", "IMMEDIATE"] = "UNKNOWN"
    user_reported_behavior_encrypted_ref: uuid.UUID | None = None
    shame_state: dict[str, Any] | None = None
    isolation_state: dict[str, Any] | None = None
    processing_preference: Literal["STORE_ONLY", "ALLOW_RECOVERY_SUPPORT", "ALLOW_LATER_REVIEW"] = "STORE_ONLY"

    @field_validator("occurred_at")
    @classmethod
    def aware_occurrence(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timezone-aware recovery occurrence required")
        return value


class SafetyStatusBody(BaseModel):
    safety_status: Literal["SAFE", "UNSAFE", "CRISIS"]


class BehaviorStoppedBody(BaseModel):
    stopped: bool


class RecoverySupportBody(BaseModel):
    support_contact_id: str


class RecoveryActionBody(BaseModel):
    action: Literal[
        "STOP_CONTINUATION", "LEAVE_ENVIRONMENT", "REMOVE_ACCESS", "CONTACT_SUPPORT",
        "HYDRATE_AND_REST", "MEDICAL_SUPPORT", "CRISIS_HANDOFF", "HONEST_DISCLOSURE",
        "CONFESSION_USER_CHOSEN", "REPAIR_PREPARATION", "PROTECTION_PLAN_UPDATE",
        "NO_FURTHER_ANALYSIS_TODAY",
    ]


class RecoveryReviewBody(BaseModel):
    answers: list[dict[str, Any]] = Field(default_factory=list, max_length=4)
    cycle_updates: list[dict[str, Any]] = Field(default_factory=list, max_length=8)


class RiskSettingsBody(BaseModel):
    warnings_enabled: bool | None = None
    enabled_cycle_ids: list[str] | None = Field(default=None, max_length=30)
    delivery_channel: Literal["IN_APP_ONLY", "PUSH_GENERIC", "USER_OPENED_SESSION", "ACCOUNTABILITY_DRAFT"] | None = None
    quiet_hours: dict[str, str] | None = None
    cooldown_settings: dict[str, int] | None = None
    model_assistance_enabled: bool | None = None
    passive_metadata_enabled: bool | None = None
    passive_metadata_consent: bool | None = None
    effect_learning_enabled: bool | None = None
    accountability_drafts_enabled: bool | None = None
    blocked_action_types: list[str] | None = Field(default=None, max_length=30)

    @model_validator(mode="after")
    def passive_consent_gate(self):
        if self.passive_metadata_enabled is True and self.passive_metadata_consent is not True:
            raise ValueError("passive metadata requires separate consent")
        return self


def _insert_cycle(cur, email: str, body: CycleBody, *, cycle_id: str | None = None, version: int = 1, supersedes: str | None = None) -> str:
    tenant, profile = _identity(email)
    cycle_id = cycle_id or str(uuid.uuid4())
    lifecycle = "ACTIVE" if body.user_confirmed else "DRAFT"
    review = "USER_CONFIRMED" if body.user_confirmed else "PENDING"
    model = TemptationCycle(
        cycle_id=cycle_id, title=body.title, cycle_type=body.cycle_type,
        trigger_conditions=body.trigger_conditions, vulnerability_conditions=body.vulnerability_conditions,
        emotional_conditions=body.emotional_conditions, environmental_conditions=body.environmental_conditions,
        temptation_nodes=[item.model_dump(mode="json") for item in body.nodes if item.node_type in {"URGE", "TEMPTATION", "CHOICE_POINT"}],
        choice_points=[item.model_dump(mode="json") for item in body.nodes if item.node_type == "CHOICE_POINT"],
        behavior_path=[item.model_dump(mode="json") for item in body.nodes if item.node_type.startswith("BEHAVIOR")],
        protective_factors=body.protective_factors, interruption_points=body.interruption_points,
        recovery_paths=body.recovery_paths, required_conditions=body.required_conditions,
        optional_conditions=body.optional_conditions,
        minimum_independent_conditions=body.minimum_independent_conditions,
        scope=body.scope, lifecycle_status=lifecycle, source_kind=body.source_kind,
        user_review_status=review, limitations=body.limitations, version=version,
        supersedes_cycle_id=supersedes, user_confirmed=body.user_confirmed,
    )
    cur.execute(
        "INSERT INTO formation_twin_temptation_cycles "
        "(id,tenant_id,profile_id,email,title,cycle_type,trigger_conditions_json,vulnerability_conditions_json,"
        "emotional_conditions_json,environmental_conditions_json,protective_factors_json,interruption_points_json,"
        "recovery_paths_json,rule_json,scope_json,lifecycle_status,source_kind,statement_type,user_review_status,"
        "user_confirmed,evidence_references_json,counterevidence_references_json,limitations_json,version,supersedes_cycle_id) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (cycle_id,tenant,profile,email,model.title,model.cycle_type,Json(model.trigger_conditions),
         Json(model.vulnerability_conditions),Json(model.emotional_conditions),Json(model.environmental_conditions),
         Json(model.protective_factors),Json(model.interruption_points),Json(model.recovery_paths),
         Json({"required_conditions":model.required_conditions,"optional_conditions":model.optional_conditions,
               "minimum_independent_conditions":model.minimum_independent_conditions,"rule_version":RULE_VERSION}),
         Json(model.scope),model.lifecycle_status,model.source_kind,model.statement_type,model.user_review_status,
         model.user_confirmed,Json([]),Json([]),Json(model.limitations),version,supersedes),
    )
    for sequence, node in enumerate(body.nodes):
        cur.execute(
            "INSERT INTO formation_twin_temptation_cycle_nodes "
            "(id,tenant_id,profile_id,email,cycle_id,node_type,condition_code,content,source_kind,statement_type,user_review_status,sequence_order) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'USER_CONFIRMED_INTERPRETATION',%s,%s)",
            (str(uuid.uuid4()),tenant,profile,email,cycle_id,node.node_type,node.condition_code,node.content,
             body.source_kind,review,sequence),
        )
    return cycle_id


@router.get("/temptation-cycles")
def list_temptation_cycles(request: Request) -> dict[str, Any]:
    user = _user(request); conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"])
            cur.execute("SELECT * FROM formation_twin_temptation_cycles WHERE email=%s AND deleted_at IS NULL ORDER BY updated_at DESC",(user["email"],))
            cycles=[dict(row) for row in cur.fetchall()]
        return {"ok":True,"cycles":cycles,"risk_is_destiny":False,"numeric_probability":False}
    finally:_state["release_db"](conn)


@router.post("/temptation-cycles")
def create_temptation_cycle(request: Request, body: CycleBody) -> dict[str, Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);cycle_id=_insert_cycle(cur,user["email"],body)
            _publish(cur,user["email"],"formation_twin.temptation_cycle_created",{"cycle_id":cycle_id,"status":"ACTIVE" if body.user_confirmed else "DRAFT","rule_version":RULE_VERSION})
            conn.commit();row,nodes=_get_cycle(cur,user["email"],cycle_id)
        return {"ok":True,"cycle":row,"nodes":nodes,"sensitive_type_user_confirmed":body.user_confirmed}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.get("/temptation-cycles/{cycle_id}")
def get_temptation_cycle(request: Request, cycle_id: str) -> dict[str, Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);row,nodes=_get_cycle(cur,user["email"],cycle_id)
        return {"ok":True,"cycle":row,"nodes":nodes,"temptation_is_behavior":False}
    finally:_state["release_db"](conn)


@router.patch("/temptation-cycles/{cycle_id}")
def patch_temptation_cycle(request: Request, cycle_id: str, body: CyclePatchBody) -> dict[str, Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);old,nodes=_get_cycle(cur,user["email"],cycle_id);rule=dict(old.get("rule_json") or {})
            data=CycleBody(
                title=body.title or old["title"],cycle_type=old["cycle_type"],
                trigger_conditions=body.trigger_conditions if body.trigger_conditions is not None else old.get("trigger_conditions_json") or [],
                vulnerability_conditions=body.vulnerability_conditions if body.vulnerability_conditions is not None else old.get("vulnerability_conditions_json") or [],
                emotional_conditions=body.emotional_conditions if body.emotional_conditions is not None else old.get("emotional_conditions_json") or [],
                environmental_conditions=body.environmental_conditions if body.environmental_conditions is not None else old.get("environmental_conditions_json") or [],
                protective_factors=body.protective_factors if body.protective_factors is not None else old.get("protective_factors_json") or [],
                interruption_points=body.interruption_points if body.interruption_points is not None else old.get("interruption_points_json") or [],
                recovery_paths=body.recovery_paths if body.recovery_paths is not None else old.get("recovery_paths_json") or [],
                required_conditions=body.required_conditions if body.required_conditions is not None else rule.get("required_conditions") or [],
                optional_conditions=body.optional_conditions if body.optional_conditions is not None else rule.get("optional_conditions") or [],
                minimum_independent_conditions=body.minimum_independent_conditions or rule.get("minimum_independent_conditions",2),
                nodes=[CycleNodeBody(node_type=item["node_type"],condition_code=item.get("condition_code"),content=item["content"]) for item in nodes],
                scope=body.scope if body.scope is not None else old.get("scope_json") or {},source_kind=old["source_kind"],
                user_confirmed=bool(old["user_confirmed"]),limitations=body.limitations if body.limitations is not None else old.get("limitations_json") or [],
            )
            new_id=_insert_cycle(cur,user["email"],data,version=int(old["version"])+1,supersedes=cycle_id)
            cur.execute("UPDATE formation_twin_temptation_cycles SET lifecycle_status='SUPERSEDED',updated_at=now() WHERE email=%s AND id=%s",(user["email"],cycle_id))
            cur.execute("UPDATE formation_twin_risk_snapshots SET invalidated_at=now() WHERE email=%s AND matched_cycle_ids_json ? %s AND invalidated_at IS NULL",(user["email"],cycle_id))
            _publish(cur,user["email"],"formation_twin.temptation_cycle_updated",{"cycle_id":new_id,"status":"ACTIVE","rule_version":RULE_VERSION});conn.commit()
        return {"ok":True,"cycle_id":new_id,"supersedes_cycle_id":cycle_id,"version":int(old["version"])+1}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.delete("/temptation-cycles/{cycle_id}")
def delete_temptation_cycle(request: Request, cycle_id: str) -> dict[str, Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);_get_cycle(cur,user["email"],cycle_id)
            cur.execute("UPDATE formation_twin_temptation_cycles SET deleted_at=now(),lifecycle_status='DELETED' WHERE email=%s AND id=%s",(user["email"],cycle_id))
            cur.execute("UPDATE formation_twin_risk_snapshots SET invalidated_at=now() WHERE email=%s AND matched_cycle_ids_json ? %s AND invalidated_at IS NULL",(user["email"],cycle_id))
            cur.execute("UPDATE formation_twin_early_warnings SET deleted_at=now(),delivery_status='INVALIDATED' WHERE email=%s AND matched_cycle_ids_json ? %s AND deleted_at IS NULL",(user["email"],cycle_id));conn.commit()
        return {"ok":True,"deleted":True,"derived_snapshots_invalidated":True,"graph_cleanup_required":True}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


def _set_cycle_status(request: Request, cycle_id: str, status: str, confirmed: bool | None = None) -> dict[str, Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);row,_=_get_cycle(cur,user["email"],cycle_id)
            if status == "ACTIVE" and confirmed is not True and not row["user_confirmed"]:
                raise HTTPException(status_code=422,detail="Cycle requires explicit user confirmation")
            review="USER_CONFIRMED" if confirmed else row["user_review_status"]
            cur.execute("UPDATE formation_twin_temptation_cycles SET lifecycle_status=%s,user_confirmed=COALESCE(%s,user_confirmed),user_review_status=%s,updated_at=now() WHERE email=%s AND id=%s RETURNING *",(status,confirmed,review,user["email"],cycle_id));updated=dict(cur.fetchone())
            event={"ACTIVE":"formation_twin.temptation_cycle_confirmed" if confirmed else "formation_twin.temptation_cycle_updated","PAUSED":"formation_twin.temptation_cycle_paused","OUTDATED":"formation_twin.temptation_cycle_outdated"}[status]
            _publish(cur,user["email"],event,{"cycle_id":cycle_id,"status":status});conn.commit();return {"ok":True,"cycle":updated}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/temptation-cycles/{cycle_id}/confirm")
def confirm_temptation_cycle(request: Request, cycle_id: str) -> dict[str, Any]:return _set_cycle_status(request,cycle_id,"ACTIVE",True)


@router.post("/temptation-cycles/{cycle_id}/pause")
def pause_temptation_cycle(request: Request, cycle_id: str) -> dict[str, Any]:return _set_cycle_status(request,cycle_id,"PAUSED")


@router.post("/temptation-cycles/{cycle_id}/resume")
def resume_temptation_cycle(request: Request, cycle_id: str) -> dict[str, Any]:return _set_cycle_status(request,cycle_id,"ACTIVE")


@router.post("/temptation-cycles/{cycle_id}/mark-outdated")
def outdated_temptation_cycle(request: Request, cycle_id: str) -> dict[str, Any]:return _set_cycle_status(request,cycle_id,"OUTDATED")


@router.post("/temptation-cycles/{cycle_id}/rebuild")
def rebuild_temptation_cycle_context(request: Request, cycle_id: str) -> dict[str, Any]:
    _set_cycle_status(request,cycle_id,"ACTIVE")
    return recalculate_current_protection(request,StatusUpdateBody())


def _load_risk_inputs(cur, email: str, body: StatusUpdateBody) -> tuple[list[TemptationCycle],list[CycleCondition],list[ActiveProtection],dict[str,Any],str]:
    settings=_ensure_settings(cur,email)
    cur.execute("SELECT * FROM formation_twin_temptation_cycles WHERE email=%s AND lifecycle_status='ACTIVE' AND user_confirmed=TRUE AND deleted_at IS NULL",(email,));cycles=[_cycle_from_row(dict(row)) for row in cur.fetchall()]
    cur.execute("SELECT * FROM formation_twin_risk_conditions WHERE email=%s AND invalidated_at IS NULL AND expires_at>now() ORDER BY occurred_at DESC LIMIT 100",(email,));conditions=[]
    for row in cur.fetchall():
        item=dict(row);refs=item.get("evidence_references_json") or []
        if item.get("independence_group") and not refs:refs=[{"reference_type":"RISK_CONDITION","reference_id":str(item["id"]),"independence_group":item["independence_group"]}]
        conditions.append(CycleCondition(condition_type=item["condition_type"],condition_code=item["condition_code"],user_visible_description=item["user_visible_description"],source_kind=item["source_kind"],statement_type=item["statement_type"],occurred_at=item["occurred_at"],expires_at=item["expires_at"],evidence_references=refs,user_confirmed=item["user_confirmed"]))
    protections=[ActiveProtection(**item.model_dump()) for item in body.active_protections]
    cur.execute("SELECT protective_actions_json,environment_boundaries_json FROM formation_twin_protection_plans WHERE email=%s AND active=TRUE AND user_confirmed=TRUE AND deleted_at IS NULL ORDER BY updated_at DESC LIMIT 3",(email,))
    for row in cur.fetchall():
        for item in (row.get("protective_actions_json") or [])+(row.get("environment_boundaries_json") or []):
            description=str(item.get("description") or item.get("title") or item.get("action_type") or "已开启一个用户确认的保护条件")
            protections.append(ActiveProtection(protection_type=str(item.get("action_type") or item.get("boundary_type") or "USER_PLAN"),description=description,active=True))
    cur.execute("SELECT COALESCE(safety_json->>'safety_level','NONE') AS level FROM formation_twin_life_events WHERE email=%s AND deleted_at IS NULL ORDER BY occurred_at DESC LIMIT 1",(email,));safety=cur.fetchone();crisis=(safety or {}).get("level","NONE")
    return cycles,conditions,protections,settings,crisis


def _recalculate(cur, email: str, body: StatusUpdateBody) -> dict[str, Any]:
    tenant,profile=_identity(email);settings=_ensure_settings(cur,email)
    for item in body.conditions:
        occurred=item.occurred_at or datetime.now(timezone.utc);expires=item.expires_at or occurred+timedelta(hours=24)
        if item.source_kind=="CONSENTED_ENVIRONMENT_METADATA" and not item.passive_signal_type:
            raise HTTPException(status_code=422,detail="Allowlisted passive signal type is required")
        if item.passive_signal_type:
            passive=validate_passive_signal(item.passive_signal_type,consent=bool(settings.get("passive_metadata_consent")),raw_content_uploaded=item.raw_content_uploaded)
            if not passive["accepted"]:raise HTTPException(status_code=422,detail=passive["reason"])
        condition=CycleCondition(condition_type=item.condition_type,condition_code=item.condition_code,user_visible_description=item.user_visible_description,source_kind=item.source_kind,statement_type=item.statement_type,occurred_at=occurred,expires_at=expires,evidence_references=item.evidence_references,user_confirmed=item.user_confirmed)
        if not condition.user_confirmed:continue
        cur.execute("INSERT INTO formation_twin_risk_conditions (id,tenant_id,profile_id,email,condition_type,condition_code,user_visible_description,source_kind,statement_type,user_confirmed,consent_type,independence_group,occurred_at,expires_at,evidence_references_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE,%s,%s,%s,%s,%s)",(str(uuid.uuid4()),tenant,profile,email,condition.condition_type,condition.condition_code,condition.user_visible_description,condition.source_kind,condition.statement_type,"PASSIVE_RISK_METADATA_PROCESSING" if item.passive_signal_type else None,item.independence_group,condition.occurred_at,condition.expires_at,Json(_json(condition.evidence_references))))
        _publish(cur,email,"formation_twin.risk_condition_activated",{"status":"ACTIVE","engine_version":ENGINE_VERSION})
    cycles,conditions,protections,settings,stored_crisis=_load_risk_inputs(cur,email,body)
    crisis=body.crisis_level if body.crisis_level in {"ELEVATED","IMMINENT"} else stored_crisis
    paused=bool(settings.get("all_warnings_paused")) or bool(settings.get("paused_until") and settings["paused_until"]>datetime.now(timezone.utc))
    snapshot=match_risk_context(cycles=cycles,conditions=conditions,active_protections=protections,explicit_urge=body.explicit_urge,behavior_started=body.behavior_started,continuation_risk=body.continuation_risk,crisis_level=crisis,warnings_enabled=bool(settings.get("warnings_enabled")) or body.user_requested_help or crisis in {"ELEVATED","IMMINENT"},paused=paused and not body.user_requested_help and crisis not in {"ELEVATED","IMMINENT"})
    now=datetime.now(timezone.utc);cur.execute("INSERT INTO formation_twin_risk_snapshots (id,tenant_id,profile_id,email,window_start,window_end,matched_cycle_ids_json,active_conditions_json,active_protective_factors_json,missing_protective_factors_json,unknown_conditions_json,internal_risk_band,user_visible_warning_level,evidence_quality,explanation_json,counterevidence_json,limitations_json,warning_eligible,warning_suppression_reasons_json,engine_version) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(snapshot.snapshot_id,tenant,profile,email,now-timedelta(hours=24),now,Json(snapshot.matched_cycle_ids),Json(snapshot.active_conditions),Json(snapshot.active_protective_factors),Json(snapshot.missing_protective_factors),Json(snapshot.unknown_conditions),snapshot.internal_risk_band,snapshot.user_visible_warning_level,snapshot.evidence_quality,Json(snapshot.explanation),Json(snapshot.counterevidence),Json(snapshot.limitations),snapshot.warning_eligible,Json(snapshot.warning_suppression_reasons),ENGINE_VERSION));_publish(cur,email,"formation_twin.risk_snapshot_created",{"snapshot_id":snapshot.snapshot_id,"warning_level":snapshot.user_visible_warning_level,"engine_version":ENGINE_VERSION})
    cur.execute("SELECT created_at FROM formation_twin_early_warnings WHERE email=%s AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1",(email,));last=cur.fetchone();quiet=settings.get("quiet_hours_json") or {};cooldowns=settings.get("cooldown_settings_json") or {};policy=apply_warning_policy(snapshot,last_warning_at=last["created_at"] if last else None,cooldown_hours=cooldowns.get(snapshot.user_visible_warning_level),quiet_hours=quiet,user_requested_help=body.user_requested_help,false_positive_count=settings.get("false_positive_count",0))
    if not policy["deliver"]:
        _publish(cur,email,"formation_twin.early_warning_suppressed",{"snapshot_id":snapshot.snapshot_id,"warning_level":snapshot.user_visible_warning_level,"status":"SUPPRESSED"});return {"snapshot":snapshot,"warning":None,"action":None,"policy":policy}
    warning=generate_warning(snapshot);action=select_protection_action(snapshot,blocked_action_types=settings.get("blocked_action_types_json") or [],human_support_available=bool(settings.get("accountability_drafts_enabled")))
    cur.execute("INSERT INTO formation_twin_early_warnings (id,tenant_id,profile_id,email,risk_snapshot_id,warning_level,title,message,matched_cycle_ids_json,active_condition_summaries_json,active_protection_summaries_json,unknown_conditions_json,counterevidence_json,evidence_references_json,uncertainty_notes_json,delivery_channel,delivery_status,user_decision_status,sharing_status,expires_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'[]',%s,%s,'DELIVERED','PENDING','PRIVATE',%s)",(warning.warning_id,tenant,profile,email,snapshot.snapshot_id,warning.warning_level,warning.title,warning.message,Json(warning.matched_confirmed_cycles),Json(warning.active_conditions),Json(warning.active_protections),Json(warning.unknown_conditions),Json(warning.counterevidence),Json(warning.uncertainty_notes),settings.get("delivery_channel","IN_APP_ONLY"),warning.expires_at))
    cur.execute("INSERT INTO formation_twin_protection_actions (id,tenant_id,profile_id,email,warning_id,action_type,title,description,target_module,routing_payload_json,decision_status,execution_status,user_confirmed,sensitive_context_included) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING','NOT_STARTED',FALSE,FALSE)",(action.action_id,tenant,profile,email,warning.warning_id,action.action_type,action.title,action.description,action.target_module,Json(action.routing_payload)))
    cur.execute("UPDATE formation_twin_early_warnings SET proposed_protection_action_id=%s WHERE id=%s",(action.action_id,warning.warning_id));_publish(cur,email,"formation_twin.early_warning_created",{"warning_id":warning.warning_id,"snapshot_id":snapshot.snapshot_id,"warning_level":warning.warning_level});_publish(cur,email,"formation_twin.early_warning_delivered",{"warning_id":warning.warning_id,"delivery_status":"DELIVERED"});_publish(cur,email,"formation_twin.protection_action_proposed",{"action_id":action.action_id,"warning_id":warning.warning_id,"action_type":action.action_type,"target_module":action.target_module})
    if warning.warning_level=="CRISIS_HANDOFF":_publish(cur,email,"formation_twin.crisis_handoff_requested",{"warning_id":warning.warning_id,"status":"REQUESTED"})
    return {"snapshot":snapshot,"warning":warning,"action":action,"policy":policy}


@router.get("/protection/current")
def current_protection(request: Request) -> dict[str, Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);settings=_ensure_settings(cur,user["email"]);cur.execute("SELECT * FROM formation_twin_risk_snapshots WHERE email=%s AND invalidated_at IS NULL ORDER BY created_at DESC LIMIT 1",(user["email"],));snapshot=cur.fetchone();cur.execute("SELECT * FROM formation_twin_early_warnings WHERE email=%s AND deleted_at IS NULL AND expires_at>now() ORDER BY created_at DESC LIMIT 1",(user["email"],));warning=cur.fetchone();action=None
            if warning and warning.get("proposed_protection_action_id"):cur.execute("SELECT * FROM formation_twin_protection_actions WHERE email=%s AND id=%s AND deleted_at IS NULL",(user["email"],warning["proposed_protection_action_id"]));action=cur.fetchone()
            conn.commit()
        return {"ok":True,"snapshot":_public_snapshot(dict(snapshot)) if snapshot else None,"warning":dict(warning) if warning else None,"action":dict(action) if action else None,"settings":settings,"numeric_probability":False}
    finally:_state["release_db"](conn)


@router.post("/protection/current/recalculate")
def recalculate_current_protection(request: Request, body: StatusUpdateBody) -> dict[str, Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);result=_recalculate(cur,user["email"],body);conn.commit()
        return {"ok":True,"snapshot":_json(result["snapshot"]),"warning":_json(result["warning"]),"action":_json(result["action"]),"policy":result["policy"],"crisis_first":result["snapshot"].user_visible_warning_level=="CRISIS_HANDOFF"}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/protection/current/status-update")
def update_current_protection(request: Request, body: StatusUpdateBody) -> dict[str, Any]:return recalculate_current_protection(request,body)


def _warning(request: Request, warning_id: str) -> tuple[dict[str,Any],Any]:
    user=_user(request);conn=_state["get_db"]();cur=_cursor(conn);_owner(cur,user["email"]);cur.execute("SELECT * FROM formation_twin_early_warnings WHERE email=%s AND id=%s AND deleted_at IS NULL",(user["email"],warning_id));row=cur.fetchone()
    if not row:cur.close();_state["release_db"](conn);raise HTTPException(status_code=404,detail="Warning not found")
    cur.close();return dict(row),conn


@router.get("/protection/warnings")
def list_warnings(request: Request) -> dict[str, Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("SELECT * FROM formation_twin_early_warnings WHERE email=%s AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 100",(user["email"],));items=[dict(row) for row in cur.fetchall()]
        return {"ok":True,"warnings":items,"prediction_success_rate":None}
    finally:_state["release_db"](conn)


@router.get("/protection/warnings/current")
def current_warning(request: Request) -> dict[str, Any]:
    data=current_protection(request);return {"ok":True,"warning":data["warning"],"action":data["action"]}


@router.get("/protection/warnings/{warning_id}")
def get_warning(request: Request, warning_id: str) -> dict[str, Any]:
    row,conn=_warning(request,warning_id);_state["release_db"](conn);return {"ok":True,"warning":row,"internal_risk_band_exposed":False}


def _warning_feedback(request: Request, warning_id: str, feedback_type: str, comment: str | None = None) -> dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);cur.execute("SELECT id FROM formation_twin_early_warnings WHERE email=%s AND id=%s AND deleted_at IS NULL",(user["email"],warning_id))
            if not cur.fetchone():raise HTTPException(status_code=404,detail="Warning not found")
            tenant,profile=_identity(user["email"]);feedback_id=str(uuid.uuid4());cur.execute("INSERT INTO formation_twin_warning_feedback (id,tenant_id,profile_id,email,warning_id,feedback_type,user_comment) VALUES (%s,%s,%s,%s,%s,%s,%s)",(feedback_id,tenant,profile,user["email"],warning_id,feedback_type,comment));cur.execute("SELECT feedback_type FROM formation_twin_warning_feedback WHERE email=%s ORDER BY created_at DESC LIMIT 20",(user["email"],));learned=learn_warning_feedback([item["feedback_type"] for item in cur.fetchall()])
            if feedback_type in {"INACCURATE","TOO_FREQUENT","TOO_INTRUSIVE"}:cur.execute("UPDATE formation_twin_risk_settings SET false_positive_count=false_positive_count+1,updated_at=now() WHERE email=%s",(user["email"],))
            if learned["request_recalibration"]:cur.execute("UPDATE formation_twin_risk_settings SET cooldown_settings_json=jsonb_set(cooldown_settings_json,'{PROTECTION_SUGGESTED}','24'::jsonb),updated_at=now() WHERE email=%s",(user["email"],))
            if feedback_type=="INACCURATE":_publish(cur,user["email"],"formation_twin.early_warning_marked_inaccurate",{"warning_id":warning_id,"status":"INACCURATE"})
            conn.commit();return {"ok":True,"feedback_id":feedback_id,"learning":learned,"shared_model_training":False}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/protection/warnings/{warning_id}/acknowledge")
def acknowledge_warning(request: Request, warning_id: str) -> dict[str, Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("UPDATE formation_twin_early_warnings SET acknowledged_at=now(),user_decision_status='ACKNOWLEDGED' WHERE email=%s AND id=%s AND deleted_at IS NULL RETURNING id",(user["email"],warning_id));row=cur.fetchone();
        if not row:raise HTTPException(status_code=404,detail="Warning not found")
        with _cursor(conn) as cur:_publish(cur,user["email"],"formation_twin.early_warning_acknowledged",{"warning_id":warning_id,"status":"ACKNOWLEDGED"});conn.commit()
        return {"ok":True,"acknowledged":True}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/protection/warnings/{warning_id}/accurate")
def warning_accurate(request: Request, warning_id: str, body: WarningFeedbackBody) -> dict[str, Any]:
    if body.feedback_type not in {"ACCURATE_AND_HELPFUL", "ACCURATE_NOT_HELPFUL"}:
        raise HTTPException(status_code=422, detail="Accurate endpoint accepts accurate feedback only")
    return _warning_feedback(request,warning_id,body.feedback_type,body.user_comment)


@router.post("/protection/warnings/{warning_id}/inaccurate")
def warning_inaccurate(request: Request, warning_id: str, body: WarningFeedbackBody | None = None) -> dict[str, Any]:return _warning_feedback(request,warning_id,"INACCURATE",body.user_comment if body else None)


@router.post("/protection/warnings/{warning_id}/too-frequent")
def warning_too_frequent(request: Request, warning_id: str, body: WarningFeedbackBody | None = None) -> dict[str, Any]:return _warning_feedback(request,warning_id,"TOO_FREQUENT",body.user_comment if body else None)


@router.post("/protection/warnings/{warning_id}/snooze")
def snooze_warning(request: Request, warning_id: str, body: SnoozeBody) -> dict[str, Any]:
    user=_user(request);conn=_state["get_db"]();now=datetime.now(timezone.utc);durations={"10_MINUTES":timedelta(minutes=10),"30_MINUTES":timedelta(minutes=30),"TONIGHT":timedelta(hours=12),"24_HOURS":timedelta(hours=24),"THIS_CYCLE":timedelta(days=3650),"ALL_WARNINGS":timedelta(days=3650)};until=now+durations[body.duration]
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("UPDATE formation_twin_early_warnings SET snoozed_until=%s,user_decision_status='SNOOZED' WHERE email=%s AND id=%s AND deleted_at IS NULL RETURNING id",(until,user["email"],warning_id));row=cur.fetchone();
        if not row:raise HTTPException(status_code=404,detail="Warning not found")
        with _cursor(conn) as cur:
            if body.duration=="ALL_WARNINGS":cur.execute("UPDATE formation_twin_risk_settings SET all_warnings_paused=TRUE,paused_until=%s WHERE email=%s",(until,user["email"],))
            _publish(cur,user["email"],"formation_twin.early_warning_snoozed",{"warning_id":warning_id,"status":body.duration});conn.commit()
        return {"ok":True,"snoozed_until":until.isoformat()}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/protection/warnings/{warning_id}/dismiss")
def dismiss_warning(request: Request, warning_id: str) -> dict[str, Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("UPDATE formation_twin_early_warnings SET dismissed_at=now(),user_decision_status='DISMISSED' WHERE email=%s AND id=%s AND deleted_at IS NULL RETURNING id",(user["email"],warning_id));row=cur.fetchone();conn.commit()
        if not row:raise HTTPException(status_code=404,detail="Warning not found")
        return {"ok":True,"dismissed":True}
    finally:_state["release_db"](conn)


def _get_action(cur, email: str, action_id: str) -> dict[str, Any]:
    cur.execute("SELECT * FROM formation_twin_protection_actions WHERE email=%s AND id=%s AND deleted_at IS NULL",(email,action_id));row=cur.fetchone()
    if not row:raise HTTPException(status_code=404,detail="Protection action not found")
    return dict(row)


def _action_model(row: dict[str, Any]) -> ProtectionAction:
    return ProtectionAction(
        action_id=str(row["id"]),action_type=row["action_type"],title=row["title"],description=row["description"],
        target_module=row["target_module"],routing_payload=row.get("routing_payload_json") or {},
        high_impact=(row.get("routing_payload_json") or {}).get("execution_mode") in {"HARD_BLOCK","ACCOUNTABILITY_UNLOCK"},
        default_execution_mode=(row.get("routing_payload_json") or {}).get("execution_mode","REMINDER_ONLY"),
    )


@router.get("/protection/actions/current")
def current_protection_action(request: Request) -> dict[str, Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("SELECT * FROM formation_twin_protection_actions WHERE email=%s AND deleted_at IS NULL AND decision_status='PENDING' ORDER BY created_at DESC LIMIT 1",(user["email"],));row=cur.fetchone()
        return {"ok":True,"action":dict(row) if row else None,"requires_user_confirmation":True}
    finally:_state["release_db"](conn)


@router.post("/protection/actions/{action_id}/accept")
def accept_protection_action(request: Request, action_id: str, body: ActionDecisionBody) -> dict[str, Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);row=_get_action(cur,user["email"],action_id);payload=dict(row.get("routing_payload_json") or {});payload.update({"execution_mode":body.execution_mode,"recovery_method_visible":body.recovery_method_visible})
            action=ProtectionAction(action_id=action_id,action_type=row["action_type"],title=row["title"],description=row["description"],target_module=row["target_module"],routing_payload=payload,high_impact=body.execution_mode in {"HARD_BLOCK","ACCOUNTABILITY_UNLOCK"},default_execution_mode=body.execution_mode)
            route=build_protection_route(action,user_confirmed=body.user_confirmed,request_id=body.request_id);cur.execute("UPDATE formation_twin_protection_actions SET decision_status='ACCEPTED',execution_status='ROUTED',user_confirmed=TRUE,routing_payload_json=%s,request_id=%s,idempotency_key=%s,started_at=now() WHERE email=%s AND id=%s RETURNING *",(Json(route),route["request_id"],route["idempotency_key"],user["email"],action_id));updated=dict(cur.fetchone());_publish(cur,user["email"],"formation_twin.protection_action_accepted",{"action_id":action_id,"action_type":action.action_type,"target_module":action.target_module,"status":"ACCEPTED"});_publish(cur,user["email"],"formation_twin.protection_action_routed",{"action_id":action_id,"request_id":route["request_id"],"target_module":action.target_module,"status":"ROUTED"});conn.commit()
        return {"ok":True,"action":updated,"route":route,"external_action_executed":False,"support_message_sent":False}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/protection/actions/{action_id}/smaller")
def smaller_protection_action(request: Request, action_id: str) -> dict[str, Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);row=_get_action(cur,user["email"],action_id);smaller=make_protection_action_smaller(_action_model(row));tenant,profile=_identity(user["email"]);cur.execute("INSERT INTO formation_twin_protection_actions (id,tenant_id,profile_id,email,warning_id,action_type,title,description,target_module,routing_payload_json,decision_status,execution_status,user_confirmed,sensitive_context_included,version,supersedes_action_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING','NOT_STARTED',FALSE,FALSE,%s,%s)",(smaller.action_id,tenant,profile,user["email"],row.get("warning_id"),smaller.action_type,smaller.title,smaller.description,smaller.target_module,Json(smaller.routing_payload),int(row.get("version",1))+1,action_id));cur.execute("UPDATE formation_twin_protection_actions SET decision_status='REPLACED_BY_SMALLER' WHERE email=%s AND id=%s",(user["email"],action_id));_publish(cur,user["email"],"formation_twin.protection_action_proposed",{"action_id":smaller.action_id,"action_type":smaller.action_type,"target_module":smaller.target_module});conn.commit()
        return {"ok":True,"action":_json(smaller),"supersedes_action_id":action_id}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/protection/actions/{action_id}/alternative")
def alternative_protection_action(request: Request, action_id: str) -> dict[str, Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);row=_get_action(cur,user["email"],action_id);replacement_type="MESSAGE_SUPPORT_PERSON" if row["action_type"]!="MESSAGE_SUPPORT_PERSON" else "DELAY_DECISION";templates={"MESSAGE_SUPPORT_PERSON":("准备一条求助消息","只生成一句五分钟陪伴请求草稿；不会自动发送。","ACCOUNTABILITY"),"DELAY_DECISION":("先延迟十分钟","十分钟内先不作最终决定，之后再重新选择。","FORMATION_ENGINE")};title,description,target=templates[replacement_type];replacement=ProtectionAction(action_id=str(uuid.uuid4()),action_type=replacement_type,title=title,description=description,target_module=target,routing_payload={"request_id":str(uuid.uuid4()),"action_type":replacement_type,"execution_mode":"REMINDER_ONLY","start_now":True,"sensitive_reason_included":False,"user_confirmed":False});tenant,profile=_identity(user["email"]);cur.execute("INSERT INTO formation_twin_protection_actions (id,tenant_id,profile_id,email,warning_id,action_type,title,description,target_module,routing_payload_json,decision_status,execution_status,user_confirmed,sensitive_context_included,version,supersedes_action_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING','NOT_STARTED',FALSE,FALSE,%s,%s)",(replacement.action_id,tenant,profile,user["email"],row.get("warning_id"),replacement.action_type,replacement.title,replacement.description,replacement.target_module,Json(replacement.routing_payload),int(row.get("version",1))+1,action_id));cur.execute("UPDATE formation_twin_protection_actions SET decision_status='REPLACED_BY_ALTERNATIVE' WHERE email=%s AND id=%s",(user["email"],action_id));_publish(cur,user["email"],"formation_twin.protection_action_proposed",{"action_id":replacement.action_id,"action_type":replacement.action_type,"target_module":replacement.target_module});conn.commit()
        return {"ok":True,"action":_json(replacement),"supersedes_action_id":action_id}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/protection/actions/{action_id}/skip")
def skip_protection_action(request: Request, action_id: str) -> dict[str, Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("UPDATE formation_twin_protection_actions SET decision_status='SKIPPED',execution_status='NOT_STARTED' WHERE email=%s AND id=%s AND deleted_at IS NULL RETURNING id",(user["email"],action_id));row=cur.fetchone();conn.commit()
        if not row:raise HTTPException(status_code=404,detail="Protection action not found")
        return {"ok":True,"skipped":True,"user_failure_label":False}
    finally:_state["release_db"](conn)


def _set_action_execution(request: Request, action_id: str, status: str, event: str) -> dict[str,Any]:
    user=_user(request);conn=_state["get_db"]();column="completed_at" if status=="COMPLETED" else "stopped_at"
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute(f"UPDATE formation_twin_protection_actions SET execution_status=%s,{column}=now() WHERE email=%s AND id=%s AND deleted_at IS NULL RETURNING *",(status,user["email"],action_id));row=cur.fetchone();
        if not row:raise HTTPException(status_code=404,detail="Protection action not found")
        with _cursor(conn) as cur:_publish(cur,user["email"],event,{"action_id":action_id,"action_type":row["action_type"],"status":status});conn.commit()
        return {"ok":True,"action":dict(row),"completion_is_moral_score":False}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/protection/actions/{action_id}/complete")
def complete_protection_action(request: Request, action_id: str) -> dict[str, Any]:return _set_action_execution(request,action_id,"COMPLETED","formation_twin.protection_action_completed")


@router.post("/protection/actions/{action_id}/stop")
def stop_protection_action(request: Request, action_id: str) -> dict[str, Any]:return _set_action_execution(request,action_id,"STOPPED","formation_twin.protection_action_stopped")


def _get_plan(cur,email:str,plan_id:str)->dict[str,Any]:
    cur.execute("SELECT * FROM formation_twin_protection_plans WHERE email=%s AND id=%s AND deleted_at IS NULL",(email,plan_id));row=cur.fetchone()
    if not row:raise HTTPException(status_code=404,detail="Protection plan not found")
    return dict(row)


@router.get("/protection-plans")
def list_protection_plans(request: Request)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("SELECT * FROM formation_twin_protection_plans WHERE email=%s AND deleted_at IS NULL ORDER BY updated_at DESC",(user["email"],));items=[dict(row) for row in cur.fetchall()]
        return {"ok":True,"plans":items,"default_sharing":"PRIVATE_ONLY"}
    finally:_state["release_db"](conn)


@router.post("/protection-plans")
def create_protection_plan(request:Request,body:ProtectionPlanBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]();tenant,profile=_identity(user["email"]);plan_id=str(uuid.uuid4())
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("INSERT INTO formation_twin_protection_plans (id,tenant_id,profile_id,email,title,cycle_ids_json,early_signs_json,high_risk_contexts_json,protective_actions_json,environment_boundaries_json,support_contact_ids_json,spiritual_supports_json,professional_supports_json,sharing_policy_json,escalation_rules_json,user_confirmed,active) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,FALSE)",(plan_id,tenant,profile,user["email"],body.title,Json(body.cycle_ids),Json(body.early_signs),Json(body.high_risk_contexts),Json(body.protective_actions),Json(body.environment_boundaries),Json(body.support_contact_ids),Json(body.spiritual_supports),Json(body.professional_supports),Json(body.sharing_policy),Json(body.escalation_rules),body.user_confirmed));_publish(cur,user["email"],"formation_twin.protection_plan_created",{"plan_id":plan_id,"status":"DRAFT"});conn.commit();row=_get_plan(cur,user["email"],plan_id)
        return {"ok":True,"plan":row}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.get("/protection-plans/{plan_id}")
def get_protection_plan(request:Request,plan_id:str)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);row=_get_plan(cur,user["email"],plan_id)
        return {"ok":True,"plan":row}
    finally:_state["release_db"](conn)


@router.patch("/protection-plans/{plan_id}")
def patch_protection_plan(request:Request,plan_id:str,body:ProtectionPlanPatchBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);old=_get_plan(cur,user["email"],plan_id)
            sharing=body.sharing_policy if body.sharing_policy is not None else old.get("sharing_policy_json") or {"mode":"PRIVATE_ONLY"}
            if sharing.get("mode","PRIVATE_ONLY")!="PRIVATE_ONLY" and not body.user_confirmed:
                raise HTTPException(status_code=422,detail="Sharing changes require user confirmation")
            tenant,profile=_identity(user["email"]);new_id=str(uuid.uuid4());confirmed=bool(old["user_confirmed"] or body.user_confirmed)
            cur.execute(
                "INSERT INTO formation_twin_protection_plans "
                "(id,tenant_id,profile_id,email,title,cycle_ids_json,early_signs_json,high_risk_contexts_json,protective_actions_json,environment_boundaries_json,support_contact_ids_json,spiritual_supports_json,professional_supports_json,sharing_policy_json,escalation_rules_json,user_confirmed,active,version,supersedes_plan_id) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (new_id,tenant,profile,user["email"],body.title or old["title"],Json(old.get("cycle_ids_json") or []),
                 Json(body.early_signs if body.early_signs is not None else old.get("early_signs_json") or []),
                 Json(body.high_risk_contexts if body.high_risk_contexts is not None else old.get("high_risk_contexts_json") or []),
                 Json(body.protective_actions if body.protective_actions is not None else old.get("protective_actions_json") or []),
                 Json(body.environment_boundaries if body.environment_boundaries is not None else old.get("environment_boundaries_json") or []),
                 Json(body.support_contact_ids if body.support_contact_ids is not None else old.get("support_contact_ids_json") or []),
                 Json(old.get("spiritual_supports_json") or []),Json(old.get("professional_supports_json") or []),Json(sharing),
                 Json(body.escalation_rules if body.escalation_rules is not None else old.get("escalation_rules_json") or []),
                 confirmed,bool(old["active"] and confirmed),int(old["version"])+1,plan_id),
            )
            cur.execute("UPDATE formation_twin_protection_plans SET active=FALSE,updated_at=now() WHERE email=%s AND id=%s",(user["email"],plan_id));_publish(cur,user["email"],"formation_twin.protection_plan_updated",{"plan_id":new_id,"status":"UPDATED"});conn.commit();row=_get_plan(cur,user["email"],new_id)
        return {"ok":True,"plan":row,"supersedes_plan_id":plan_id}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.delete("/protection-plans/{plan_id}")
def delete_protection_plan(request:Request,plan_id:str)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("UPDATE formation_twin_protection_plans SET deleted_at=now(),active=FALSE WHERE email=%s AND id=%s AND deleted_at IS NULL RETURNING id",(user["email"],plan_id));row=cur.fetchone();conn.commit()
        if not row:raise HTTPException(status_code=404,detail="Protection plan not found")
        return {"ok":True,"deleted":True}
    finally:_state["release_db"](conn)


def _set_plan(request:Request,plan_id:str,active:bool,event:str)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);row=_get_plan(cur,user["email"],plan_id)
        if active and not row["user_confirmed"]:raise HTTPException(status_code=422,detail="Plan must be user confirmed before activation")
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("UPDATE formation_twin_protection_plans SET active=%s,updated_at=now() WHERE email=%s AND id=%s RETURNING *",(active,user["email"],plan_id));updated=dict(cur.fetchone());_publish(cur,user["email"],event,{"plan_id":plan_id,"status":"ACTIVE" if active else "PAUSED"});conn.commit();return {"ok":True,"plan":updated}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/protection-plans/{plan_id}/activate")
def activate_protection_plan(request:Request,plan_id:str)->dict[str,Any]:return _set_plan(request,plan_id,True,"formation_twin.protection_plan_activated")


@router.post("/protection-plans/{plan_id}/pause")
def pause_protection_plan(request:Request,plan_id:str)->dict[str,Any]:return _set_plan(request,plan_id,False,"formation_twin.protection_plan_paused")


@router.post("/protection-plans/{plan_id}/rehearse")
def rehearse_protection_plan(request:Request,plan_id:str)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);_get_plan(cur,user["email"],plan_id);cur.execute("UPDATE formation_twin_protection_plans SET last_rehearsed_at=now() WHERE email=%s AND id=%s",(user["email"],plan_id));_publish(cur,user["email"],"formation_twin.protection_plan_rehearsed",{"plan_id":plan_id,"status":"REHEARSED"});conn.commit()
        return {"ok":True,"rehearsed":True,"external_action_executed":False}
    finally:_state["release_db"](conn)


@router.post("/protection-plans/{plan_id}/share")
def share_protection_plan(request:Request,plan_id:str,body:SharePlanBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]();tenant,profile=_identity(user["email"]);request_id=str(uuid.uuid4())
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);_get_plan(cur,user["email"],plan_id);cur.execute("SELECT allowed_share_fields_json FROM formation_twin_support_contacts WHERE email=%s AND id=%s AND active=TRUE AND deleted_at IS NULL",(user["email"],body.support_contact_id));contact=cur.fetchone()
            if not contact:raise HTTPException(status_code=404,detail="Support contact not found")
            allowed=set(contact["allowed_share_fields_json"] or [])
            if not set(body.share_fields).issubset(allowed):raise HTTPException(status_code=422,detail="Requested fields exceed contact authorization")
            share={"plan_id":plan_id,"fields":body.share_fields,"expires_at":body.expires_at.isoformat()};cur.execute("INSERT INTO formation_twin_support_requests (id,tenant_id,profile_id,email,support_contact_id,request_type,share_payload_json,user_confirmed,delivery_status) VALUES (%s,%s,%s,%s,%s,'TIME_LIMITED_PLAN_ACCESS',%s,TRUE,'READY_FOR_USER_SEND')",(request_id,tenant,profile,user["email"],body.support_contact_id,Json(share)));_publish(cur,user["email"],"formation_twin.support_request_confirmed",{"request_id":request_id,"plan_id":plan_id,"status":"READY_FOR_USER_SEND"});conn.commit()
        return {"ok":True,"request_id":request_id,"delivery_status":"READY_FOR_USER_SEND","external_delivery_performed":False}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/protection-plans/{plan_id}/revoke-sharing")
def revoke_plan_sharing(request:Request,plan_id:str)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("UPDATE formation_twin_support_requests SET cancelled_at=now(),delivery_status='REVOKED' WHERE email=%s AND request_type='TIME_LIMITED_PLAN_ACCESS' AND share_payload_json->>'plan_id'=%s AND cancelled_at IS NULL",(user["email"],plan_id));count=cur.rowcount;conn.commit()
        return {"ok":True,"revoked_requests":count,"effective_immediately":True}
    finally:_state["release_db"](conn)


@router.get("/protection/support-contacts")
def list_support_contacts(request:Request)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("SELECT * FROM formation_twin_support_contacts WHERE email=%s AND deleted_at IS NULL ORDER BY created_at DESC",(user["email"],));items=[dict(row) for row in cur.fetchall()]
        return {"ok":True,"contacts":items,"full_twin_access":False}
    finally:_state["release_db"](conn)


@router.post("/protection/support-contacts")
def create_support_contact(request:Request,body:SupportContactBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]();tenant,profile=_identity(user["email"]);contact_id=str(uuid.uuid4())
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("INSERT INTO formation_twin_support_contacts (id,tenant_id,profile_id,email,contact_reference_id,display_alias,support_role,allowed_share_fields_json,allowed_actions_json,sharing_expires_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(contact_id,tenant,profile,user["email"],body.contact_reference_id,body.display_alias,body.support_role,Json(body.allowed_share_fields),Json(body.allowed_actions),body.sharing_expires_at));conn.commit();cur.execute("SELECT * FROM formation_twin_support_contacts WHERE id=%s",(contact_id,));row=dict(cur.fetchone())
        return {"ok":True,"contact":row,"default_action":"DRAFT_MESSAGE_ONLY"}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.patch("/protection/support-contacts/{contact_id}")
def patch_support_contact(request:Request,contact_id:str,body:SupportContactPatchBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);updates=[];values=[];mapping={"display_alias":"display_alias","support_role":"support_role","allowed_share_fields":"allowed_share_fields_json","allowed_actions":"allowed_actions_json","sharing_expires_at":"sharing_expires_at","active":"active"}
            for field,column in mapping.items():
                value=getattr(body,field)
                if value is not None:updates.append(f"{column}=%s");values.append(Json(value) if isinstance(value,list) else value)
            if not updates:raise HTTPException(status_code=422,detail="No changes supplied")
            cur.execute(f"UPDATE formation_twin_support_contacts SET {','.join(updates)} WHERE email=%s AND id=%s AND deleted_at IS NULL RETURNING *",(*values,user["email"],contact_id));row=cur.fetchone();
            if not row:raise HTTPException(status_code=404,detail="Support contact not found")
            conn.commit()
        return {"ok":True,"contact":dict(row)}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.delete("/protection/support-contacts/{contact_id}")
def delete_support_contact(request:Request,contact_id:str)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("UPDATE formation_twin_support_contacts SET active=FALSE,revoked_at=now(),deleted_at=now() WHERE email=%s AND id=%s AND deleted_at IS NULL RETURNING id",(user["email"],contact_id));row=cur.fetchone();cur.execute("UPDATE formation_twin_support_requests SET cancelled_at=now(),delivery_status='REVOKED' WHERE email=%s AND support_contact_id=%s AND cancelled_at IS NULL",(user["email"],contact_id));conn.commit()
        if not row:raise HTTPException(status_code=404,detail="Support contact not found")
        return {"ok":True,"deleted":True,"sharing_revoked":True}
    finally:_state["release_db"](conn)


@router.post("/protection/support-contacts/{contact_id}/draft-message")
def draft_support_message(request:Request,contact_id:str,body:DraftMessageBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]();tenant,profile=_identity(user["email"]);request_id=str(uuid.uuid4())
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("SELECT id FROM formation_twin_support_contacts WHERE email=%s AND id=%s AND active=TRUE AND deleted_at IS NULL",(user["email"],contact_id));contact=cur.fetchone()
        if not contact:raise HTTPException(status_code=404,detail="Support contact not found")
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("INSERT INTO formation_twin_support_requests (id,tenant_id,profile_id,email,support_contact_id,request_type,message_draft,share_payload_json,user_confirmed,delivery_status) VALUES (%s,%s,%s,%s,%s,%s,%s,'{}',FALSE,'DRAFT')",(request_id,tenant,profile,user["email"],contact_id,body.request_type,body.message));_publish(cur,user["email"],"formation_twin.support_request_drafted",{"request_id":request_id,"status":"DRAFT"});conn.commit()
        return {"ok":True,"request_id":request_id,"message_draft":body.message,"sent":False}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/protection/support-contacts/{contact_id}/request-share")
def request_support_share(request:Request,contact_id:str,body:ShareRequestBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]();tenant,profile=_identity(user["email"]);request_id=str(uuid.uuid4())
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("SELECT allowed_share_fields_json FROM formation_twin_support_contacts WHERE email=%s AND id=%s AND active=TRUE AND deleted_at IS NULL",(user["email"],contact_id));contact=cur.fetchone();
        if not contact:raise HTTPException(status_code=404,detail="Support contact not found")
        if not set(body.share_fields).issubset(set(contact["allowed_share_fields_json"] or [])):raise HTTPException(status_code=422,detail="Requested fields exceed authorization")
        payload={"fields":body.share_fields,"expires_at":body.expires_at.isoformat() if body.expires_at else None}
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("INSERT INTO formation_twin_support_requests (id,tenant_id,profile_id,email,support_contact_id,request_type,share_payload_json,user_confirmed,delivery_status) VALUES (%s,%s,%s,%s,%s,%s,%s,TRUE,'READY_FOR_USER_SEND')",(request_id,tenant,profile,user["email"],contact_id,body.request_type,Json(payload)));_publish(cur,user["email"],"formation_twin.support_request_confirmed",{"request_id":request_id,"status":"READY_FOR_USER_SEND"});conn.commit()
        return {"ok":True,"request_id":request_id,"delivery_status":"READY_FOR_USER_SEND","automatic_third_party_share":False}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


def _current_recovery(cur,email:str)->dict[str,Any]:
    cur.execute("SELECT * FROM formation_twin_recovery_records WHERE email=%s AND deleted_at IS NULL AND recovery_status NOT IN ('STABILIZED','CLOSED') ORDER BY created_at DESC LIMIT 1",(email,));row=cur.fetchone()
    if not row:raise HTTPException(status_code=404,detail="No active recovery")
    return dict(row)


@router.post("/recovery/start")
def start_relapse_recovery(request:Request,body:RecoveryStartBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]();tenant,profile=_identity(user["email"]);recovery_id=str(uuid.uuid4());crisis="ELEVATED" if body.immediate_safety_status=="CRISIS" else "NONE";flow=start_recovery(crisis_level=crisis)
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("INSERT INTO formation_twin_recovery_records (id,tenant_id,profile_id,email,event_type,occurred_at,immediate_safety_status,continuation_risk,user_reported_behavior_encrypted_ref,shame_state_json,isolation_state_json,statement_type,processing_preference,recovery_status,first_step,review_due_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'USER_REPORTED_FACT',%s,%s,'IMMEDIATE_SAFETY',%s)",(recovery_id,tenant,profile,user["email"],body.event_type,body.occurred_at,body.immediate_safety_status,body.continuation_risk,body.user_reported_behavior_encrypted_ref,Json(body.shame_state) if body.shame_state else None,Json(body.isolation_state) if body.isolation_state else None,body.processing_preference,flow["status"],datetime.now(timezone.utc)+timedelta(hours=24)));_publish(cur,user["email"],"formation_twin.recovery_started",{"recovery_id":recovery_id,"status":flow["status"]});
        if flow["status"]=="CRISIS_HANDOFF":
            with _cursor(conn) as cur:_publish(cur,user["email"],"formation_twin.crisis_handoff_requested",{"recovery_id":recovery_id,"status":"REQUESTED"})
        conn.commit();return {"ok":True,"recovery_id":recovery_id,"workflow":flow,"behavior_body_stored":False}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.get("/recovery/current")
def get_current_recovery(request:Request)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);row=_current_recovery(cur,user["email"])
        row.pop("user_reported_behavior_encrypted_ref",None)
        return {"ok":True,"recovery":row,"deep_analysis_allowed":False if not row.get("stabilized_at") else True}
    finally:_state["release_db"](conn)


@router.post("/recovery/current/safety-status")
def update_recovery_safety(request:Request,body:SafetyStatusBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);row=_current_recovery(cur,user["email"]);status="CRISIS_HANDOFF" if body.safety_status=="CRISIS" else "SAFETY_CHECKED";cur.execute("UPDATE formation_twin_recovery_records SET immediate_safety_status=%s,safety_checked_at=now(),recovery_status=%s WHERE email=%s AND id=%s",(body.safety_status,status,user["email"],row["id"]));_publish(cur,user["email"],"formation_twin.recovery_safety_checked",{"recovery_id":row["id"],"status":status});
        if status=="CRISIS_HANDOFF":
            with _cursor(conn) as cur:_publish(cur,user["email"],"formation_twin.crisis_handoff_requested",{"recovery_id":row["id"],"status":"REQUESTED"})
        conn.commit();return {"ok":True,"status":status,"crisis_first":status=="CRISIS_HANDOFF"}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/recovery/current/behavior-stopped")
def update_behavior_stopped(request:Request,body:BehaviorStoppedBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);row=_current_recovery(cur,user["email"]);status="BEHAVIOR_STOPPED" if body.stopped else "CONTINUATION_SUPPORT_REQUIRED";cur.execute("UPDATE formation_twin_recovery_records SET behavior_stopped_at=CASE WHEN %s THEN now() ELSE NULL END,continuation_risk=CASE WHEN %s THEN 'LOW' ELSE 'IMMEDIATE' END,recovery_status=%s WHERE email=%s AND id=%s",(body.stopped,body.stopped,status,user["email"],row["id"]));conn.commit()
        return {"ok":True,"status":status,"next_step":"HUMAN_CONNECTION" if body.stopped else "STOP_CONTINUATION"}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/recovery/current/connect-support")
def connect_recovery_support(request:Request,body:RecoverySupportBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]();tenant,profile=_identity(user["email"]);request_id=str(uuid.uuid4())
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);row=_current_recovery(cur,user["email"]);cur.execute("SELECT id FROM formation_twin_support_contacts WHERE email=%s AND id=%s AND active=TRUE AND deleted_at IS NULL",(user["email"],body.support_contact_id));contact=cur.fetchone()
        if not contact:raise HTTPException(status_code=404,detail="Support contact not found")
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("INSERT INTO formation_twin_support_requests (id,tenant_id,profile_id,email,support_contact_id,request_type,message_draft,share_payload_json,user_confirmed,delivery_status) VALUES (%s,%s,%s,%s,%s,'ONE_TIME_HELP_REQUEST','我现在需要有人陪我说五分钟。','{}',FALSE,'DRAFT')",(request_id,tenant,profile,user["email"],body.support_contact_id));cur.execute("UPDATE formation_twin_recovery_records SET support_connections_json=support_connections_json || %s::jsonb WHERE email=%s AND id=%s",(Json([{"support_request_id":request_id,"delivery_status":"DRAFT"}]),user["email"],row["id"]));_publish(cur,user["email"],"formation_twin.support_request_drafted",{"request_id":request_id,"recovery_id":row["id"],"status":"DRAFT"});conn.commit()
        return {"ok":True,"request_id":request_id,"delivery_status":"DRAFT","sent":False}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/recovery/current/choose-action")
def choose_recovery_action(request:Request,body:RecoveryActionBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);row=_current_recovery(cur,user["email"]);cur.execute("UPDATE formation_twin_recovery_records SET immediate_recovery_actions_json=immediate_recovery_actions_json || %s::jsonb,recovery_status='RECOVERY_ACTION_SELECTED' WHERE email=%s AND id=%s",(Json([{"action":body.action,"selected_by_user":True}]),user["email"],row["id"]));_publish(cur,user["email"],"formation_twin.recovery_action_selected",{"recovery_id":row["id"],"status":"SELECTED"});
        if body.action=="CRISIS_HANDOFF":
            with _cursor(conn) as cur:_publish(cur,user["email"],"formation_twin.crisis_handoff_requested",{"recovery_id":row["id"],"status":"REQUESTED"})
        conn.commit();return {"ok":True,"action":body.action,"deep_analysis_required":False}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/recovery/current/stabilized")
def stabilize_recovery(request:Request)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]();tenant,profile=_identity(user["email"]);review_id=str(uuid.uuid4());scheduled=datetime.now(timezone.utc)+timedelta(hours=24)
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);row=_current_recovery(cur,user["email"])
        if not row.get("safety_checked_at"):raise HTTPException(status_code=422,detail="Safety must be checked before stabilization")
        if row.get("event_type") in {"BEHAVIOR_STARTED","USER_REPORTED_RELAPSE"} and not row.get("behavior_stopped_at"):
            raise HTTPException(status_code=422,detail="Continuation status must be checked before stabilization")
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("UPDATE formation_twin_recovery_records SET recovery_status='STABILIZED',stabilized_at=now(),review_due_at=%s WHERE email=%s AND id=%s",(scheduled,user["email"],row["id"]));cur.execute("INSERT INTO formation_twin_recovery_reviews (id,tenant_id,profile_id,email,recovery_record_id,scheduled_for) VALUES (%s,%s,%s,%s,%s,%s)",(review_id,tenant,profile,user["email"],row["id"],scheduled));_publish(cur,user["email"],"formation_twin.recovery_stabilized",{"recovery_id":row["id"],"review_id":review_id,"status":"STABILIZED"});conn.commit()
        return {"ok":True,"status":"STABILIZED","review_id":review_id,"review_optional":True,"scheduled_for":scheduled.isoformat()}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/recovery/current/defer-review")
def defer_recovery_review(request:Request)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]();due=datetime.now(timezone.utc)+timedelta(hours=72)
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);row=_current_recovery(cur,user["email"]);cur.execute("UPDATE formation_twin_recovery_records SET review_due_at=%s,recovery_status='REVIEW_DEFERRED' WHERE email=%s AND id=%s",(due,user["email"],row["id"]));conn.commit()
        return {"ok":True,"review_due_at":due.isoformat(),"analysis_deferred":True}
    finally:_state["release_db"](conn)


@router.get("/recovery/reviews")
def list_recovery_reviews(request:Request)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("SELECT * FROM formation_twin_recovery_reviews WHERE email=%s AND deleted_at IS NULL ORDER BY scheduled_for DESC",(user["email"],));items=[dict(row) for row in cur.fetchall()]
        return {"ok":True,"reviews":items,"maximum_questions":4}
    finally:_state["release_db"](conn)


def _complete_recovery_review(request:Request,review_id:str,status:str,body:RecoveryReviewBody|None=None)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("SELECT * FROM formation_twin_recovery_reviews WHERE email=%s AND id=%s AND deleted_at IS NULL",(user["email"],review_id));row=cur.fetchone()
        if not row:raise HTTPException(status_code=404,detail="Recovery review not found")
        answers=body.answers if body else [];updates=body.cycle_updates if body else [];column="completed_at" if status=="COMPLETED" else "skipped_at";event="formation_twin.recovery_review_completed" if status=="COMPLETED" else "formation_twin.recovery_review_skipped"
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute(f"UPDATE formation_twin_recovery_reviews SET review_status=%s,answers_json=%s,cycle_updates_json=%s,{column}=now() WHERE email=%s AND id=%s",(status,Json(answers),Json(updates),user["email"],review_id));_publish(cur,user["email"],event,{"review_id":review_id,"recovery_id":row["recovery_record_id"],"status":status});conn.commit()
        return {"ok":True,"status":status,"cycle_updates_require_separate_user_confirmation":True}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/recovery/reviews/{review_id}/complete")
def complete_recovery_review(request:Request,review_id:str,body:RecoveryReviewBody)->dict[str,Any]:return _complete_recovery_review(request,review_id,"COMPLETED",body)


@router.post("/recovery/reviews/{review_id}/skip")
def skip_recovery_review(request:Request,review_id:str)->dict[str,Any]:return _complete_recovery_review(request,review_id,"SKIPPED")


@router.get("/protection/settings")
def get_risk_settings(request:Request)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);settings=_ensure_settings(cur,user["email"]);conn.commit()
        return {"ok":True,"settings":settings,"notification_content":sanitize_notification_content(),"passive_metadata_default":False,"sharing_default":"DRAFT_MESSAGE_ONLY"}
    finally:_state["release_db"](conn)


@router.patch("/protection/settings")
def patch_risk_settings(request:Request,body:RiskSettingsBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);current=_ensure_settings(cur,user["email"])
            if body.passive_metadata_enabled is True and body.passive_metadata_consent is not True and not current.get("passive_metadata_consent"):raise HTTPException(status_code=422,detail="Separate passive metadata consent required")
            updates=[];values=[];mapping={"warnings_enabled":"warnings_enabled","enabled_cycle_ids":"enabled_cycle_ids_json","delivery_channel":"delivery_channel","quiet_hours":"quiet_hours_json","cooldown_settings":"cooldown_settings_json","model_assistance_enabled":"model_assistance_enabled","passive_metadata_enabled":"passive_metadata_enabled","passive_metadata_consent":"passive_metadata_consent","effect_learning_enabled":"effect_learning_enabled","accountability_drafts_enabled":"accountability_drafts_enabled","blocked_action_types":"blocked_action_types_json"}
            for field,column in mapping.items():
                value=getattr(body,field)
                if value is not None:updates.append(f"{column}=%s");values.append(Json(value) if isinstance(value,(dict,list)) else value)
            if updates:cur.execute(f"UPDATE formation_twin_risk_settings SET {','.join(updates)},updated_at=now() WHERE email=%s RETURNING *",(*values,user["email"]));settings=dict(cur.fetchone())
            else:settings=current
            conn.commit()
        return {"ok":True,"settings":settings,"secret_monitoring":False}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/protection/settings/pause-all")
def pause_all_warnings(request:Request)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);_ensure_settings(cur,user["email"]);cur.execute("UPDATE formation_twin_risk_settings SET all_warnings_paused=TRUE,updated_at=now() WHERE email=%s",(user["email"],));conn.commit()
        return {"ok":True,"paused":True,"processing_stopped":True}
    finally:_state["release_db"](conn)


@router.post("/protection/settings/resume-all")
def resume_all_warnings(request:Request)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);_ensure_settings(cur,user["email"]);cur.execute("UPDATE formation_twin_risk_settings SET all_warnings_paused=FALSE,paused_until=NULL,updated_at=now() WHERE email=%s",(user["email"],));conn.commit()
        return {"ok":True,"paused":False}
    finally:_state["release_db"](conn)


@router.post("/protection/settings/reset-learning")
def reset_warning_learning(request:Request)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);_ensure_settings(cur,user["email"]);cur.execute("UPDATE formation_twin_warning_feedback SET deleted_at=now() WHERE email=%s AND deleted_at IS NULL",(user["email"],));count=cur.rowcount;cur.execute("UPDATE formation_twin_risk_settings SET false_positive_count=0,cooldown_settings_json=%s,updated_at=now() WHERE email=%s",(Json({"AWARENESS":12,"PROTECTION_SUGGESTED":4}),user["email"]));conn.commit()
        return {"ok":True,"deleted_feedback":count,"crisis_threshold_changed":False}
    finally:_state["release_db"](conn)


@router.delete("/protection/data")
def erase_protection_data(request:Request)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);deleted={}
            for table in ("formation_twin_recovery_reviews","formation_twin_warning_feedback","formation_twin_support_requests","formation_twin_protection_actions","formation_twin_early_warnings","formation_twin_risk_snapshots","formation_twin_risk_conditions","formation_twin_temptation_cycle_edges","formation_twin_temptation_cycle_nodes","formation_twin_protection_plans","formation_twin_support_contacts","formation_twin_temptation_cycles","formation_twin_recovery_records","formation_twin_risk_settings"):
                cur.execute(f"DELETE FROM {table} WHERE email=%s",(user["email"],));deleted[table]=cur.rowcount
            _publish(cur,user["email"],"formation_twin.protection_data_erased",{"status":"ERASED"});conn.commit()
        return {"ok":True,"deleted":deleted,"graph_nodes_deleted":0,"embedding_rows_deleted":0,"cache_and_pending_delivery_invalidated":True}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.get("/protection/data-quality")
def protection_data_quality(request:Request)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);cur.execute("SELECT * FROM formation_twin_temptation_cycles WHERE email=%s AND deleted_at IS NULL",(user["email"],));cycles=[dict(row) for row in cur.fetchall()];cur.execute("SELECT w.*,s.internal_risk_band FROM formation_twin_early_warnings w JOIN formation_twin_risk_snapshots s ON s.id=w.risk_snapshot_id WHERE w.email=%s AND w.deleted_at IS NULL",(user["email"],));warnings=[]
            for row in cur.fetchall():
                item=dict(row);item["explicit_user_help"]=item.get("internal_risk_band") in {"STRONG_URGE_SELF_REPORTED","BEHAVIOR_STARTED","CONTINUATION_RISK","CRISIS_RELATED"};warnings.append(item)
            cur.execute("SELECT * FROM formation_twin_support_requests WHERE email=%s AND deleted_at IS NULL",(user["email"],));requests=[dict(row) for row in cur.fetchall()];cur.execute("SELECT *,first_step FROM formation_twin_recovery_records WHERE email=%s AND deleted_at IS NULL",(user["email"],));recoveries=[dict(row) for row in cur.fetchall()];report=risk_data_quality(cycles,warnings,requests,recoveries)
        return {"ok":True,**report}
    finally:_state["release_db"](conn)


@router.get("/protection/workflows")
def protection_workflows(request:Request)->dict[str,Any]:
    _user(request);return {"ok":True,"workflows":WORKFLOW_NODES,"crisis_first":True,"model_optional":True,"scheduler_adapter":"existing scheduler / event consumer"}


@router.post("/protection/model-candidates/validate")
def validate_protection_model_candidates(request:Request,payload:dict[str,Any])->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);settings=_ensure_settings(cur,user["email"]);cur.execute("SELECT id FROM formation_twin_temptation_cycles WHERE email=%s AND lifecycle_status='ACTIVE' AND user_confirmed=TRUE AND deleted_at IS NULL",(user["email"],));ids=[str(row["id"]) for row in cur.fetchall()];conn.commit()
        return {"ok":True,**validate_model_candidates(payload,consent=bool(settings.get("model_assistance_enabled")) and os.getenv("FORMATION_TWIN_WARNING_MODEL_ENABLED","false").lower()=="true",allowed_cycle_ids=ids),"model_provider_configured":False}
    finally:_state["release_db"](conn)


@router.post("/protection/passive-signals/validate")
def validate_protection_passive_signal(request:Request,payload:dict[str,Any])->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);settings=_ensure_settings(cur,user["email"]);conn.commit()
        return {"ok":True,**validate_passive_signal(str(payload.get("signal_type","")),consent=bool(settings.get("passive_metadata_consent")),raw_content_uploaded=bool(payload.get("raw_content_uploaded")))}
    finally:_state["release_db"](conn)
