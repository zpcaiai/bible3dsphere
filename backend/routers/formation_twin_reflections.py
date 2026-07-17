"""Formation Twin Batch 6 reflection and consent-gated intervention API."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator, model_validator
from psycopg2.extras import Json, RealDictCursor

from formation_twin.reflection_interventions import (
    CAPACITY_MODES,
    ENGINE_VERSION,
    PUBLISHED_EVENTS,
    SCHEDULED_JOBS,
    TEMPLATE_VERSION,
    EffectReview,
    MicroIntervention,
    ReflectionContext,
    ReflectionMirror,
    ReflectionQuestion,
    assemble_reflection_context,
    build_routing_command,
    build_user_capacity,
    decide_intervention,
    generate_daily_mirror,
    generate_intervention_candidates,
    generate_weekly_review,
    learn_intervention_preferences,
    make_action_smaller,
    reflection_data_quality,
    reminder_allowed,
    sanitize_notification_content,
    select_minimum_action,
    validate_engagement_proposal,
    validate_safe_text,
)


router = APIRouter(prefix="/api/v1/formation-twin", tags=["formation-twin-reflections"])
_state: dict[str, Any] = {}


def init_formation_twin_reflections_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
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
        raise ValueError("unregistered Formation Twin reflection event")
    allowed = {
        "context_id", "mirror_id", "question_id", "proposal_id", "decision_id", "execution_id",
        "review_id", "preference_id", "request_id", "status", "decision_status", "execution_status",
        "target_module", "intervention_type", "action", "engine_version",
    }
    safe = {key: _json(value) for key, value in payload.items() if key in allowed}
    cur.execute(
        "INSERT INTO domain_events (aggregate_type,aggregate_id,event_type,payload) VALUES (%s,%s,%s,%s)",
        ("formation_twin", email, event_type, Json(safe)),
    )


def _ensure_settings(cur, email: str) -> dict[str, Any]:
    tenant, profile = _identity(email)
    cur.execute(
        "INSERT INTO formation_twin_reflection_settings (id,tenant_id,profile_id,email) "
        "VALUES (%s,%s,%s,%s) ON CONFLICT (tenant_id,profile_id) DO NOTHING",
        (str(uuid.uuid4()), tenant, profile, email),
    )
    cur.execute("SELECT * FROM formation_twin_reflection_settings WHERE email=%s", (email,))
    return dict(cur.fetchone())


class GenerateReflectionBody(BaseModel):
    user_selected_mode: Literal["MICRO_ONLY", "NORMAL", "REFLECTION_ONLY", "STORE_ONLY"] | None = None
    available_minutes: int | None = Field(default=None, ge=0, le=1440)
    energy_level: int | None = Field(default=None, ge=0, le=10)
    stress_level: int | None = Field(default=None, ge=0, le=10)
    sleep_quality: int | None = Field(default=None, ge=0, le=10)


class MirrorCorrectionBody(BaseModel):
    headline: str | None = Field(default=None, min_length=1, max_length=160)
    mirror_text: str = Field(min_length=1, max_length=600)
    reason_code: str = Field(default="USER_CORRECTION", max_length=80)

    @field_validator("headline", "mirror_text")
    @classmethod
    def safe_text(cls, value: str | None) -> str | None:
        if value: validate_safe_text(value)
        return value


class WeeklyCorrectionBody(BaseModel):
    focus_theme: str | None = Field(default=None, max_length=400)
    important_observations: list[dict[str, Any]] | None = Field(default=None, max_length=3)
    reason_code: str = Field(default="USER_CORRECTION", max_length=80)


class QuestionAnswerBody(BaseModel):
    answer_text: str | None = Field(default=None, max_length=4000)
    answer_type: Literal["TEXT", "CHOICE", "NO_ANSWER", "PRIVATE_NOTE"] = "TEXT"
    processing_preference: Literal["STORE_ONLY", "ALLOW_REFLECTION", "ALLOW_TWIN_PROCESSING"] = "STORE_ONLY"


class ProposalDecisionBody(BaseModel):
    request_id: str | None = None
    modifications: dict[str, Any] = Field(default_factory=dict)
    habit_confirmation: dict[str, Any] | None = None
    allow_cross_module_write: bool = True
    reason_code: str | None = Field(default=None, max_length=80)
    user_comment: str | None = Field(default=None, max_length=1000)
    defer_until: datetime | None = None

    @field_validator("defer_until")
    @classmethod
    def aware_if_present(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("timezone-aware defer time required")
        return value


class ProposalModificationBody(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, min_length=1, max_length=600)
    estimated_duration_minutes: int | None = Field(default=None, ge=0, le=30)
    target_module: Literal[
        "FORMATION_ENGINE", "PRAYER_OS", "HOLY_HABIT_ENGINE", "ATTENTION_OS", "REST",
        "RELATIONAL_SUPPORT", "PROFESSIONAL_SUPPORT", "NO_ACTION",
    ] | None = None

    @field_validator("title", "description")
    @classmethod
    def safe_text(cls, value: str | None) -> str | None:
        if value: validate_safe_text(value)
        return value


class EffectReviewBody(BaseModel):
    execution_status: Literal[
        "COMPLETED", "PARTIALLY_COMPLETED", "NOT_STARTED", "STOPPED", "FORGOTTEN",
        "NO_LONGER_RELEVANT", "DECLINED_AFTER_ACCEPTANCE", "UNKNOWN",
    ]
    helpfulness: Literal["NOT_HELPFUL", "SLIGHTLY_HELPFUL", "HELPFUL", "VERY_HELPFUL", "UNCERTAIN"] | None = None
    burden: Literal["VERY_LOW", "LOW", "ACCEPTABLE", "HIGH", "TOO_HIGH"] | None = None
    emotional_effect: dict[str, Any] | None = None
    formation_effect: dict[str, Any] | None = None
    practical_effect: dict[str, Any] | None = None
    what_helped: str | None = Field(default=None, max_length=1000)
    what_did_not_help: str | None = Field(default=None, max_length=1000)
    preferred_adjustment: str | None = Field(default=None, max_length=1000)


class PreferencePatchBody(BaseModel):
    reflection_only: bool | None = None
    preferred_intervention_types: list[str] | None = Field(default=None, max_length=20)
    blocked_intervention_types: list[str] | None = Field(default=None, max_length=20)
    maximum_action_minutes: int | None = Field(default=None, ge=0, le=30)
    preference_learning_enabled: bool | None = None


class ReflectionSettingsBody(BaseModel):
    daily_mirror_mode: Literal["ON_DEMAND", "REMINDER_OPT_IN", "REFLECTION_ONLY", "PAUSED"] | None = None
    weekly_review_enabled: bool | None = None
    effect_review_enabled: bool | None = None
    cross_module_routing_enabled: bool | None = None
    preference_learning_enabled: bool | None = None
    interventions_paused: bool | None = None
    reminder_settings: dict[str, Any] | None = None
    quiet_hours: dict[str, Any] | None = None
    capacity_default: Literal["MICRO_ONLY", "NORMAL", "REFLECTION_ONLY", "STORE_ONLY"] | None = None
    maximum_action_minutes: int | None = Field(default=None, ge=0, le=30)
    preferred_intervention_types: list[str] | None = Field(default=None, max_length=20)
    blocked_intervention_types: list[str] | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def validate_reminder_privacy(self):
        if self.reminder_settings:
            content = str(self.reminder_settings.get("content", ""))
            if content and sanitize_notification_content(content) != content:
                raise ValueError("custom reminder content must use the generic privacy-safe template")
        if self.quiet_hours:
            for key in ("start", "end", "timezone"):
                if key not in self.quiet_hours:
                    raise ValueError("quiet hours require start, end, and timezone")
            reminder_allowed(
                now=datetime.now(timezone.utc), timezone_name=str(self.quiet_hours["timezone"]),
                quiet_hours_start=str(self.quiet_hours["start"]), quiet_hours_end=str(self.quiet_hours["end"]),
                reminder_enabled=True,
            )
        return self


def _load_reflection_context(cur, email: str, context_type: str, overrides: GenerateReflectionBody | None = None) -> tuple[ReflectionContext, dict[str, Any]]:
    settings = _ensure_settings(cur, email)
    cur.execute(
        "SELECT id,canonical_event_id,energy_level,stress_level,sleep_quality,self_report_json,processing_preference,occurred_at "
        "FROM formation_twin_daily_checkins WHERE email=%s AND deleted_at IS NULL ORDER BY occurred_at DESC LIMIT 1",
        (email,),
    )
    checkin = dict(cur.fetchone() or {})
    self_report = dict(checkin.get("self_report_json") or {})
    override = overrides or GenerateReflectionBody()
    mode = override.user_selected_mode or self_report.get("capacity_mode") or settings.get("capacity_default") or "NORMAL"
    if checkin.get("processing_preference") == "STORE_ONLY" and not override.user_selected_mode:
        mode = "STORE_ONLY"
    if mode not in CAPACITY_MODES:
        mode = "NORMAL"
    capacity = build_user_capacity(
        energy_level=override.energy_level if override.energy_level is not None else checkin.get("energy_level"),
        stress_level=override.stress_level if override.stress_level is not None else checkin.get("stress_level"),
        sleep_quality=override.sleep_quality if override.sleep_quality is not None else checkin.get("sleep_quality"),
        available_minutes=override.available_minutes if override.available_minutes is not None else self_report.get("available_minutes"),
        user_selected_mode=mode,
        source_event_ids=[str(checkin.get("canonical_event_id") or checkin.get("id"))] if checkin else [],
    )
    cur.execute(
        "SELECT COALESCE(safety_json->>'safety_level','NONE') AS safety_level,id "
        "FROM formation_twin_life_events WHERE email=%s AND deleted_at IS NULL ORDER BY occurred_at DESC LIMIT 1",
        (email,),
    )
    safety = dict(cur.fetchone() or {"safety_level": "NONE"})
    cur.execute(
        "SELECT id,title,pattern_type,description,scope_json,lifecycle_status,user_review_status,statement_type,source_kind "
        "FROM formation_twin_patterns WHERE email=%s AND deleted_at IS NULL "
        "AND lifecycle_status NOT IN ('REJECTED','OUTDATED','INVALIDATED','RESOLVED','ARCHIVED') "
        "ORDER BY last_observed_at DESC LIMIT 12",
        (email,),
    )
    patterns = [dict(row) for row in cur.fetchall()]
    for item in patterns: item["pattern_id"] = str(item["id"])
    cur.execute(
        "SELECT id,title,season_type,life_domains,user_review_status,active FROM formation_twin_life_seasons "
        "WHERE email=%s AND deleted_at IS NULL AND active=TRUE ORDER BY started_at DESC LIMIT 4",
        (email,),
    )
    seasons = [dict(row) for row in cur.fetchall()]
    cur.execute(
        "SELECT id,alternative_responses_json,grace_patterns_json,recovery_patterns_json,counterevidence_json "
        "FROM formation_twin_long_term_snapshots WHERE email=%s AND superseded_at IS NULL ORDER BY created_at DESC LIMIT 1",
        (email,),
    )
    long_term = dict(cur.fetchone() or {})
    cur.execute("SELECT id FROM formation_twin_emotional_snapshots WHERE email=%s ORDER BY created_at DESC LIMIT 1", (email,))
    emotional_snapshot = cur.fetchone()
    cur.execute("SELECT id FROM formation_twin_formation_snapshots WHERE email=%s AND superseded_at IS NULL ORDER BY created_at DESC LIMIT 1", (email,))
    formation_snapshot = cur.fetchone()
    cur.execute(
        "SELECT preference_type,preference_value_json FROM formation_twin_intervention_preferences "
        "WHERE email=%s AND active=TRUE ORDER BY created_at DESC LIMIT 20",
        (email,),
    )
    learned = [dict(row) for row in cur.fetchall()]
    preferences = {
        "reflection_only": settings.get("daily_mirror_mode") == "REFLECTION_ONLY" or settings.get("interventions_paused"),
        "blocked_intervention_types": settings.get("blocked_intervention_types_json") or [],
        "preferred_intervention_types": settings.get("preferred_intervention_types_json") or [],
        "maximum_action_minutes": settings.get("maximum_action_minutes", 10),
        "learning_enabled": settings.get("preference_learning_enabled", True),
        "learned": learned[:3],
    }
    recent_effects: list[dict[str, Any]] = []
    cur.execute(
        "SELECT r.id,r.helpfulness,r.burden,p.intervention_type FROM formation_twin_intervention_effect_reviews r "
        "JOIN formation_twin_intervention_executions e ON e.id=r.intervention_id "
        "JOIN formation_twin_intervention_proposals p ON p.id=e.proposal_id "
        "WHERE r.email=%s AND r.deleted_at IS NULL ORDER BY r.created_at DESC LIMIT 3",
        (email,),
    )
    recent_effects = [dict(row) for row in cur.fetchall()]
    now = datetime.now(timezone.utc)
    window = timedelta(days=7 if context_type == "WEEKLY" else 1)
    emotional_state = None
    if checkin:
        emotional_state = {
            "id": str(checkin["id"]), "energy_level": capacity.energy_level,
            "stress_level": capacity.stress_level, "sleep_quality": capacity.sleep_quality,
            "statement_type": "USER_REPORTED_FACT",
        }
    context = assemble_reflection_context(
        context_type=context_type, window_start=now-window, window_end=now,
        emotional_state=emotional_state,
        formation_state={"id": str(formation_snapshot["id"]), "statement_type": "STRUCTURED_SNAPSHOT"} if formation_snapshot else None,
        patterns=patterns, life_seasons=seasons, capacity=capacity, preferences=preferences,
        safety_status=safety,
        protective_factors=(long_term.get("counterevidence_json") or [])[:3],
        grace_recovery_factors=((long_term.get("grace_patterns_json") or []) + (long_term.get("recovery_patterns_json") or []))[:3],
        alternative_responses=(long_term.get("alternative_responses_json") or [])[:3], recent_effects=recent_effects,
    )
    ids = {
        "emotional_snapshot_id": str(emotional_snapshot["id"]) if emotional_snapshot else None,
        "formation_snapshot_id": str(formation_snapshot["id"]) if formation_snapshot else None,
        "long_term_snapshot_id": str(long_term["id"]) if long_term else None,
    }
    return context, ids


def _insert_context(cur, email: str, context: ReflectionContext, ids: dict[str, Any]) -> None:
    tenant, profile = _identity(email)
    cur.execute(
        "INSERT INTO formation_twin_reflection_contexts "
        "(id,tenant_id,profile_id,email,context_type,window_start,window_end,emotional_snapshot_id,formation_snapshot_id,long_term_snapshot_id,"
        "active_life_seasons_json,confirmed_patterns_json,risk_factors_json,protective_factors_json,grace_recovery_json,"
        "user_capacity_json,user_preferences_json,safety_status_json,data_coverage_json,limitations_json,allowed_output,engine_version) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            context.context_id,tenant,profile,email,context.context_type,context.window_start,context.window_end,
            ids.get("emotional_snapshot_id"),ids.get("formation_snapshot_id"),ids.get("long_term_snapshot_id"),
            Json(_json(context.active_life_seasons)),Json(_json(context.confirmed_patterns)),Json(_json(context.current_risk_factors)),
            Json(_json(context.current_protective_factors)),Json(_json(context.grace_and_recovery_factors)),
            Json(_json(context.user_capacity)),Json(_json(context.user_preferences)),Json(_json(context.safety_status)),
            Json(_json(context.data_coverage)),Json(_json(context.limitations)),context.allowed_output,ENGINE_VERSION,
        ),
    )
    _publish(cur,email,"formation_twin.reflection_context_created",{"context_id":context.context_id,"status":context.allowed_output,"engine_version":ENGINE_VERSION})


def _insert_question(cur, email: str, question: ReflectionQuestion, mirror_id: str | None) -> None:
    tenant, profile = _identity(email)
    cur.execute(
        "INSERT INTO formation_twin_reflection_questions "
        "(id,tenant_id,profile_id,email,mirror_id,question_type,question_text,selection_rationale_json,source_references_json,burden_level,template_version,status) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING')",
        (question.question_id,tenant,profile,email,mirror_id,question.question_type,question.question_text,
         Json(question.selection_rationale),Json(_json(question.source_references)),question.burden_level,question.template_version),
    )
    _publish(cur,email,"formation_twin.reflection_question_created",{"question_id":question.question_id,"mirror_id":mirror_id,"status":"PENDING"})


def _insert_proposal(cur, email: str, context_id: str, mirror_id: str | None, intervention: MicroIntervention, *, supersedes_id: str | None = None, version: int = 1) -> None:
    tenant, profile = _identity(email)
    cur.execute(
        "INSERT INTO formation_twin_intervention_proposals "
        "(id,tenant_id,profile_id,email,context_id,mirror_id,template_key,intervention_type,title,description,rationale,estimated_duration_minutes,"
        "effort_level,target_module,routing_payload_json,source_pattern_ids_json,source_factor_ids_json,safety_classification,contraindications_json,"
        "generation_method,statement_type,decision_status,lifecycle_status,required_user_confirmation,one_time,reminder_enabled,requires_second_confirmation,version,supersedes_proposal_id,expires_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING','PROPOSED',TRUE,%s,FALSE,%s,%s,%s,%s)",
        (intervention.intervention_id,tenant,profile,email,context_id,mirror_id,intervention.intervention_type.lower(),intervention.intervention_type,
         intervention.title,intervention.description,intervention.rationale,intervention.estimated_duration_minutes,intervention.effort_level,
         intervention.target_module,Json(_json(intervention.routing_payload)),Json(intervention.source_pattern_ids),Json(intervention.source_factor_ids),
         intervention.safety_classification,Json(intervention.contraindications),intervention.generation_method,intervention.statement_type,
         intervention.one_time,intervention.requires_second_confirmation,version,supersedes_id,intervention.expires_at),
    )
    _publish(cur,email,"formation_twin.intervention_proposed",{"proposal_id":intervention.intervention_id,"intervention_type":intervention.intervention_type,"target_module":intervention.target_module,"status":"PROPOSED"})


def _insert_mirror_bundle(cur, email: str, context: ReflectionContext, output: dict[str, Any]) -> dict[str, Any]:
    mirror: ReflectionMirror = output["mirror"]
    question: ReflectionQuestion | None = output.get("question")
    intervention: MicroIntervention | None = output.get("intervention")
    tenant, profile = _identity(email)
    cur.execute(
        "INSERT INTO formation_twin_reflection_mirrors "
        "(id,tenant_id,profile_id,email,context_id,mirror_type,headline,mirror_text,confirmed_observations_json,pending_items_json,grace_protection_json,"
        "source_references_json,limitations_json,generation_method,template_version,user_review_status,status) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING','ACTIVE')",
        (mirror.mirror_id,tenant,profile,email,context.context_id,mirror.mirror_type,mirror.headline,mirror.mirror_text,
         Json(_json(mirror.confirmed_observations)),Json(_json(mirror.pending_items)),Json(_json(mirror.grace_and_protection)),
         Json(_json(mirror.source_references)),Json(mirror.limitations),mirror.generation_method,mirror.template_version),
    )
    if question: _insert_question(cur,email,question,mirror.mirror_id)
    if intervention: _insert_proposal(cur,email,context.context_id,mirror.mirror_id,intervention)
    _publish(cur,email,"formation_twin.daily_mirror_created",{"mirror_id":mirror.mirror_id,"context_id":context.context_id,"status":"ACTIVE"})
    return {"mirror_id":mirror.mirror_id,"question_id":question.question_id if question else None,"proposal_id":intervention.intervention_id if intervention else None}


def _proposal_model(row: dict[str, Any]) -> MicroIntervention:
    return MicroIntervention(
        intervention_id=str(row["id"]), intervention_type=row["intervention_type"], title=row["title"],
        description=row["description"], rationale=row["rationale"], intended_support=[],
        estimated_duration_minutes=row["estimated_duration_minutes"], effort_level=row["effort_level"],
        target_module=row["target_module"], routing_payload=row.get("routing_payload_json") or {},
        source_pattern_ids=[str(item) for item in (row.get("source_pattern_ids_json") or [])],
        source_factor_ids=[str(item) for item in (row.get("source_factor_ids_json") or [])],
        safety_classification=row["safety_classification"], contraindications=row.get("contraindications_json") or [],
        generation_method=row["generation_method"], statement_type=row["statement_type"],
        one_time=row["one_time"], reminder_enabled=row["reminder_enabled"],
        requires_second_confirmation=row["requires_second_confirmation"], lifecycle_status=row["lifecycle_status"],
        created_at=row["created_at"], expires_at=row.get("expires_at"),
    )


def _context_from_row(row: dict[str, Any]) -> ReflectionContext:
    capacity = dict(row.get("user_capacity_json") or {})
    emotional = {
        "id": capacity.get("source_event_ids", [str(row["id"])])[0] if capacity.get("source_event_ids") else str(row["id"]),
        "energy_level": capacity.get("energy_level"), "stress_level": capacity.get("stress_level"),
        "sleep_quality": capacity.get("sleep_quality"), "statement_type": "USER_REPORTED_FACT",
    }
    return ReflectionContext(
        context_id=str(row["id"]), context_type=row["context_type"], window_start=row["window_start"], window_end=row["window_end"],
        current_emotional_state=emotional, current_formation_state={"id":str(row["formation_snapshot_id"])} if row.get("formation_snapshot_id") else None,
        active_life_seasons=row.get("active_life_seasons_json") or [], confirmed_patterns=row.get("confirmed_patterns_json") or [],
        current_risk_factors=row.get("risk_factors_json") or [], current_protective_factors=row.get("protective_factors_json") or [],
        grace_and_recovery_factors=row.get("grace_recovery_json") or [], user_capacity=capacity,
        user_preferences=row.get("user_preferences_json") or {}, safety_status=row.get("safety_status_json") or {"safety_level":"NONE"},
        data_coverage=row.get("data_coverage_json") or {}, limitations=row.get("limitations_json") or [],
        allowed_output=row["allowed_output"], generated_at=row["created_at"],
    )


def _mirror_bundle(cur, email: str, mirror_id: str) -> dict[str, Any]:
    cur.execute("SELECT * FROM formation_twin_reflection_mirrors WHERE email=%s AND id=%s AND deleted_at IS NULL", (email,mirror_id))
    mirror = cur.fetchone()
    if not mirror: raise HTTPException(status_code=404, detail="Reflection mirror not found")
    cur.execute("SELECT * FROM formation_twin_reflection_questions WHERE email=%s AND mirror_id=%s AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1", (email,mirror_id))
    question = cur.fetchone()
    cur.execute("SELECT * FROM formation_twin_intervention_proposals WHERE email=%s AND mirror_id=%s AND deleted_at IS NULL ORDER BY version DESC,created_at DESC LIMIT 1", (email,mirror_id))
    proposal = cur.fetchone()
    return {"mirror":dict(mirror),"question":dict(question) if question else None,"proposal":dict(proposal) if proposal else None,
            "required_user_confirmation":True,"pending_context_not_used":True}


@router.get("/reflections/daily/current")
def get_current_daily_reflection(request: Request) -> dict[str, Any]:
    user=_user(request); conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]); cur.execute("SELECT id FROM formation_twin_reflection_mirrors WHERE email=%s AND mirror_type='DAILY' AND status='ACTIVE' AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1",(user["email"],)); row=cur.fetchone()
            if not row: return {"ok":True,"data_status":"INSUFFICIENT_DATA","mirror":None,"no_action_available":True}
            return {"ok":True,"data_status":"AVAILABLE",**_mirror_bundle(cur,user["email"],str(row["id"]))}
    finally: _state["release_db"](conn)


@router.post("/reflections/daily/generate")
def generate_daily_reflection(request: Request, body: GenerateReflectionBody) -> dict[str, Any]:
    user=_user(request); conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]); context,ids=_load_reflection_context(cur,user["email"],"DAILY",body); _insert_context(cur,user["email"],context,ids)
            cur.execute("SELECT question_type,status,created_at FROM formation_twin_reflection_questions WHERE email=%s ORDER BY created_at DESC LIMIT 20",(user["email"],)); recent=[dict(row) for row in cur.fetchall()]
            output=generate_daily_mirror(context,recent_questions=recent)
            if not output.get("mirror"):
                event="formation_twin.reflection_processing_skipped"
                _publish(cur,user["email"],event,{"context_id":context.context_id,"status":output["status"]}); conn.commit()
                return {"ok":True,"context":_json(context),"status":output["status"],"crisis_first":output["status"]=="CRISIS_ROUTED","ordinary_intervention_suppressed":output.get("ordinary_intervention_suppressed",False)}
            ids_out=_insert_mirror_bundle(cur,user["email"],context,output); conn.commit()
            return {"ok":True,"status":"AVAILABLE","context":_json(context),"validation":output["validation"],**ids_out,**_mirror_bundle(cur,user["email"],ids_out["mirror_id"])}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.get("/reflections/daily/{mirror_id}")
def get_daily_reflection(request: Request, mirror_id: str) -> dict[str, Any]:
    user=_user(request); conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur: _owner(cur,user["email"]); return {"ok":True,**_mirror_bundle(cur,user["email"],mirror_id)}
    finally: _state["release_db"](conn)


@router.post("/reflections/daily/{mirror_id}/correct")
def correct_daily_reflection(request: Request, mirror_id: str, body: MirrorCorrectionBody) -> dict[str, Any]:
    user=_user(request); conn=_state["get_db"](); tenant,profile=_identity(user["email"])
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]); cur.execute("SELECT * FROM formation_twin_reflection_mirrors WHERE email=%s AND id=%s AND deleted_at IS NULL",(user["email"],mirror_id)); old=cur.fetchone()
            if not old: raise HTTPException(status_code=404,detail="Reflection mirror not found")
            new_id=str(uuid.uuid4()); cur.execute(
                "INSERT INTO formation_twin_reflection_mirrors (id,tenant_id,profile_id,email,context_id,mirror_type,headline,mirror_text,confirmed_observations_json,pending_items_json,grace_protection_json,source_references_json,limitations_json,generation_method,template_version,user_review_status,status,version,supersedes_mirror_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'RULE',%s,'CORRECTED','ACTIVE',%s,%s)",
                (new_id,tenant,profile,user["email"],old["context_id"],old["mirror_type"],body.headline or old["headline"],body.mirror_text,Json(old["confirmed_observations_json"]),Json([]),Json(old["grace_protection_json"]),Json(old["source_references_json"]),Json(list(old["limitations_json"])+["用户已纠正镜像文本。"]),TEMPLATE_VERSION,int(old["version"])+1,mirror_id))
            cur.execute("UPDATE formation_twin_reflection_mirrors SET status='SUPERSEDED',user_review_status='CORRECTED' WHERE id=%s",(mirror_id,)); _publish(cur,user["email"],"formation_twin.daily_mirror_corrected",{"mirror_id":new_id,"status":"ACTIVE"}); conn.commit(); return {"ok":True,"supersedes_mirror_id":mirror_id,**_mirror_bundle(cur,user["email"],new_id)}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


@router.post("/reflections/daily/{mirror_id}/dismiss")
def dismiss_daily_reflection(request: Request, mirror_id: str) -> dict[str, Any]:
    user=_user(request); conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]); cur.execute("UPDATE formation_twin_reflection_mirrors SET status='DISMISSED',user_review_status='DISMISSED',dismissed_at=now() WHERE email=%s AND id=%s AND deleted_at IS NULL RETURNING id",(user["email"],mirror_id))
            if not cur.fetchone(): raise HTTPException(status_code=404,detail="Reflection mirror not found")
            _publish(cur,user["email"],"formation_twin.daily_mirror_dismissed",{"mirror_id":mirror_id,"status":"DISMISSED"}); conn.commit(); return {"ok":True,"dismissed":True,"negative_label_created":False}
    except Exception:
        conn.rollback(); raise
    finally: _state["release_db"](conn)


def _weekly_bundle(cur,email: str,review_id: str) -> dict[str,Any]:
    cur.execute("SELECT * FROM formation_twin_weekly_reviews WHERE email=%s AND id=%s AND deleted_at IS NULL",(email,review_id)); review=cur.fetchone()
    if not review: raise HTTPException(status_code=404,detail="Weekly review not found")
    question=None; proposal=None
    if review.get("question_id"):
        cur.execute("SELECT * FROM formation_twin_reflection_questions WHERE email=%s AND id=%s",(email,review["question_id"])); question=cur.fetchone()
    if review.get("proposal_id"):
        cur.execute("SELECT * FROM formation_twin_intervention_proposals WHERE email=%s AND id=%s",(email,review["proposal_id"])); proposal=cur.fetchone()
    return {"review":dict(review),"question":dict(question) if question else None,"proposal":dict(proposal) if proposal else None,"completion_is_not_growth":True}


@router.get("/reflections/weekly/current")
def get_current_weekly_review(request: Request) -> dict[str,Any]:
    user=_user(request); conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]); cur.execute("SELECT id FROM formation_twin_weekly_reviews WHERE email=%s AND deleted_at IS NULL ORDER BY window_end DESC LIMIT 1",(user["email"],)); row=cur.fetchone()
            return {"ok":True,"data_status":"AVAILABLE",**_weekly_bundle(cur,user["email"],str(row["id"]))} if row else {"ok":True,"data_status":"INSUFFICIENT_DATA","review":None}
    finally:_state["release_db"](conn)


@router.post("/reflections/weekly/generate")
def generate_weekly_reflection(request: Request, body: GenerateReflectionBody) -> dict[str,Any]:
    user=_user(request); conn=_state["get_db"](); tenant,profile=_identity(user["email"])
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]); context,ids=_load_reflection_context(cur,user["email"],"WEEKLY",body); _insert_context(cur,user["email"],context,ids)
            cur.execute("SELECT COUNT(DISTINCT occurred_at::date) AS days FROM formation_twin_daily_checkins WHERE email=%s AND deleted_at IS NULL AND occurred_at>=%s",(user["email"],context.window_start)); active_days=int((cur.fetchone() or {}).get("days") or 0)
            output=generate_weekly_review(context,active_days=active_days)
            if output.get("status")=="CRISIS_ROUTED":
                _publish(cur,user["email"],"formation_twin.reflection_processing_skipped",{"context_id":context.context_id,"status":"CRISIS_ROUTED"}); conn.commit(); return {"ok":True,**output}
            question=output.get("high_value_question"); proposal=output.get("proposed_intervention")
            if question:_insert_question(cur,user["email"],question,None)
            if proposal:_insert_proposal(cur,user["email"],context.context_id,None,proposal)
            review_id=str(uuid.uuid4()); cur.execute("INSERT INTO formation_twin_weekly_reviews (id,tenant_id,profile_id,email,context_id,window_start,window_end,important_observations_json,burden_factors_json,grace_protection_json,emerging_alternatives_json,focus_theme,question_id,proposal_id,data_coverage_json,limitations_json,status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING')",(review_id,tenant,profile,user["email"],context.context_id,context.window_start,context.window_end,Json(_json(output["important_observations"])),Json(_json(output["burden_factors"])),Json(_json(output["grace_and_protection"])),Json(_json(output["emerging_alternatives"])),output["focus_theme"],question.question_id if question else None,proposal.intervention_id if proposal else None,Json(_json(output["data_coverage"])),Json(_json(output["limitations"]))))
            _publish(cur,user["email"],"formation_twin.weekly_review_created",{"review_id":review_id,"context_id":context.context_id,"status":"PENDING"}); conn.commit(); return {"ok":True,**_weekly_bundle(cur,user["email"],review_id)}
    except Exception: conn.rollback(); raise
    finally:_state["release_db"](conn)


@router.get("/reflections/weekly/{review_id}")
def get_weekly_reflection(request: Request,review_id: str)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);return {"ok":True,**_weekly_bundle(cur,user["email"],review_id)}
    finally:_state["release_db"](conn)


def _weekly_status(request: Request,review_id: str,status: str,event: str)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);column="completed_at" if status=="COMPLETED" else "skipped_at";cur.execute(f"UPDATE formation_twin_weekly_reviews SET status=%s,{column}=now() WHERE email=%s AND id=%s AND deleted_at IS NULL RETURNING id",(status,user["email"],review_id))
            if not cur.fetchone():raise HTTPException(status_code=404,detail="Weekly review not found")
            _publish(cur,user["email"],event,{"review_id":review_id,"status":status});conn.commit();return {"ok":True,"status":status,"negative_label_created":False}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/reflections/weekly/{review_id}/complete")
def complete_weekly_reflection(request: Request,review_id: str)->dict[str,Any]:return _weekly_status(request,review_id,"COMPLETED","formation_twin.weekly_review_completed")


@router.post("/reflections/weekly/{review_id}/skip")
def skip_weekly_reflection(request: Request,review_id: str)->dict[str,Any]:return _weekly_status(request,review_id,"SKIPPED","formation_twin.weekly_review_skipped")


@router.post("/reflections/weekly/{review_id}/correct")
def correct_weekly_reflection(request: Request,review_id: str,body: WeeklyCorrectionBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]();tenant,profile=_identity(user["email"])
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);cur.execute("SELECT * FROM formation_twin_weekly_reviews WHERE email=%s AND id=%s AND deleted_at IS NULL",(user["email"],review_id));old=cur.fetchone()
            if not old:raise HTTPException(status_code=404,detail="Weekly review not found")
            new_id=str(uuid.uuid4());cur.execute("INSERT INTO formation_twin_weekly_reviews (id,tenant_id,profile_id,email,context_id,window_start,window_end,important_observations_json,burden_factors_json,grace_protection_json,emerging_alternatives_json,focus_theme,question_id,proposal_id,data_coverage_json,limitations_json,status,version,supersedes_review_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING',%s,%s)",(new_id,tenant,profile,user["email"],old["context_id"],old["window_start"],old["window_end"],Json(body.important_observations if body.important_observations is not None else old["important_observations_json"]),Json(old["burden_factors_json"]),Json(old["grace_protection_json"]),Json(old["emerging_alternatives_json"]),body.focus_theme if body.focus_theme is not None else old["focus_theme"],old["question_id"],old["proposal_id"],Json(old["data_coverage_json"]),Json(list(old["limitations_json"])+["用户已纠正周回顾。"]),int(old["version"])+1,review_id));cur.execute("UPDATE formation_twin_weekly_reviews SET status='SUPERSEDED' WHERE id=%s",(review_id,));conn.commit();return {"ok":True,"supersedes_review_id":review_id,**_weekly_bundle(cur,user["email"],new_id)}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.get("/reflection-questions/{question_id}")
def get_reflection_question(request: Request,question_id: str)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("SELECT * FROM formation_twin_reflection_questions WHERE email=%s AND id=%s AND deleted_at IS NULL",(user["email"],question_id));row=cur.fetchone()
        if not row:raise HTTPException(status_code=404,detail="Reflection question not found")
        return {"ok":True,"question":dict(row)}
    finally:_state["release_db"](conn)


@router.post("/reflection-questions/{question_id}/answer")
def answer_reflection_question(request: Request,question_id: str,body: QuestionAnswerBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]();tenant,profile=_identity(user["email"])
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);cur.execute("SELECT id FROM formation_twin_reflection_questions WHERE email=%s AND id=%s AND deleted_at IS NULL",(user["email"],question_id))
            if not cur.fetchone():raise HTTPException(status_code=404,detail="Reflection question not found")
            answer_id=str(uuid.uuid4());cur.execute("INSERT INTO formation_twin_reflection_answers (id,tenant_id,profile_id,email,question_id,answer_text,answer_type,processing_preference,statement_type) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'USER_REPORTED_FACT')",(answer_id,tenant,profile,user["email"],question_id,body.answer_text,body.answer_type,body.processing_preference));cur.execute("UPDATE formation_twin_reflection_questions SET status='ANSWERED',answered_at=now() WHERE id=%s",(question_id,));_publish(cur,user["email"],"formation_twin.reflection_question_answered",{"question_id":question_id,"status":"ANSWERED"});conn.commit();return {"ok":True,"answer_id":answer_id,"statement_type":"USER_REPORTED_FACT","answer_not_published":True}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


def _skip_question(request: Request,question_id: str,permanent: bool)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]();status="DO_NOT_ASK_AGAIN" if permanent else "SKIPPED"
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);cur.execute("UPDATE formation_twin_reflection_questions SET status=%s,skipped_at=now(),cooldown_until=%s WHERE email=%s AND id=%s AND deleted_at IS NULL RETURNING id",(status,datetime.now(timezone.utc)+timedelta(days=3650 if permanent else 7),user["email"],question_id))
            if not cur.fetchone():raise HTTPException(status_code=404,detail="Reflection question not found")
            _publish(cur,user["email"],"formation_twin.reflection_question_skipped",{"question_id":question_id,"status":status});conn.commit();return {"ok":True,"status":status,"synonym_followup_suppressed":True}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/reflection-questions/{question_id}/skip")
def skip_reflection_question(request: Request,question_id: str)->dict[str,Any]:return _skip_question(request,question_id,False)


@router.post("/reflection-questions/{question_id}/do-not-ask-again")
def block_reflection_question(request: Request,question_id: str)->dict[str,Any]:return _skip_question(request,question_id,True)


@router.get("/interventions/proposals/current")
def get_current_intervention_proposal(request: Request)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("SELECT * FROM formation_twin_intervention_proposals WHERE email=%s AND decision_status='PENDING' AND lifecycle_status='PROPOSED' AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1",(user["email"],));row=cur.fetchone()
        return {"ok":True,"proposal":dict(row) if row else None,"no_action_available":True,"required_user_confirmation":True}
    finally:_state["release_db"](conn)


@router.get("/interventions/proposals/{proposal_id}")
def get_intervention_proposal(request: Request,proposal_id: str)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("SELECT * FROM formation_twin_intervention_proposals WHERE email=%s AND id=%s AND deleted_at IS NULL",(user["email"],proposal_id));row=cur.fetchone()
        if not row:raise HTTPException(status_code=404,detail="Intervention proposal not found")
        return {"ok":True,"proposal":dict(row),"required_user_confirmation":True,"default_once":True,"default_reminder":False}
    finally:_state["release_db"](conn)


def _proposal(cur,email: str,proposal_id: str)->dict[str,Any]:
    cur.execute("SELECT * FROM formation_twin_intervention_proposals WHERE email=%s AND id=%s AND deleted_at IS NULL",(email,proposal_id));row=cur.fetchone()
    if not row:raise HTTPException(status_code=404,detail="Intervention proposal not found")
    return dict(row)


def _save_decision(cur,email: str,proposal_id: str,decision: str,body: ProposalDecisionBody)->str:
    tenant,profile=_identity(email);decision_id=str(uuid.uuid4());cur.execute("INSERT INTO formation_twin_intervention_decisions (id,tenant_id,profile_id,email,proposal_id,decision_status,user_modifications_json,habit_confirmation_json,reason_code,user_comment) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(decision_id,tenant,profile,email,proposal_id,decision,Json(_json(body.modifications)),Json(_json(body.habit_confirmation)) if body.habit_confirmation else None,body.reason_code,body.user_comment));cur.execute("UPDATE formation_twin_intervention_proposals SET decision_status=%s WHERE email=%s AND id=%s",(decision,email,proposal_id));return decision_id


@router.post("/interventions/proposals/{proposal_id}/accept")
def accept_intervention_proposal(request: Request,proposal_id: str,body: ProposalDecisionBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]();tenant,profile=_identity(user["email"])
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);row=_proposal(cur,user["email"],proposal_id);intervention=_proposal_model(row);decision=decide_intervention(intervention,"ACCEPTED_WITH_MODIFICATION" if body.modifications else "ACCEPTED",modifications=body.modifications,habit_confirmation=body.habit_confirmation);decision_id=_save_decision(cur,user["email"],proposal_id,decision["decision_status"],body);_publish(cur,user["email"],"formation_twin.intervention_accepted",{"proposal_id":proposal_id,"decision_id":decision_id,"decision_status":decision["decision_status"]})
            if intervention.target_module=="NO_ACTION":
                _publish(cur,user["email"],"formation_twin.no_action_selected",{"proposal_id":proposal_id,"decision_id":decision_id,"status":"NO_ACTION_SELECTED"});conn.commit();return {"ok":True,"decision_id":decision_id,"routing":{"routed":False,"status":"NO_ACTION_SELECTED"}}
            settings=_ensure_settings(cur,user["email"])
            if not body.allow_cross_module_write and not settings.get("cross_module_routing_enabled"):
                conn.commit();return {"ok":True,"decision_id":decision_id,"routing":{"routed":False,"status":"EXPLICIT_ROUTING_CONFIRMATION_REQUIRED"}}
            request_id=body.request_id or str(uuid.uuid4());cur.execute("SELECT * FROM formation_twin_intervention_executions WHERE email=%s AND request_id=%s",(user["email"],request_id));existing=cur.fetchone()
            if existing:
                conn.commit();return {"ok":True,"decision_id":decision_id,"routing":{"routed":True,"idempotent_replay":True,"execution":dict(existing)}}
            command=build_routing_command(intervention,user_confirmed=True,request_id=request_id,habit_confirmation=body.habit_confirmation);execution_id=str(uuid.uuid4());cur.execute("INSERT INTO formation_twin_intervention_executions (id,tenant_id,profile_id,email,proposal_id,request_id,idempotency_key,target_module,execution_status,routing_payload_json,routed_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'ROUTED',%s,now())",(execution_id,tenant,profile,user["email"],proposal_id,command["request_id"],command["idempotency_key"],intervention.target_module,Json(command["payload"])));_publish(cur,user["email"],"formation_twin.intervention_routed",{"proposal_id":proposal_id,"execution_id":execution_id,"request_id":request_id,"target_module":intervention.target_module,"status":"ROUTED"});conn.commit();return {"ok":True,"decision_id":decision_id,"execution_id":execution_id,"routing":command}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/interventions/proposals/{proposal_id}/modify")
def modify_intervention_proposal(request: Request,proposal_id: str,body: ProposalModificationBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);row=_proposal(cur,user["email"],proposal_id);old=_proposal_model(row);update={key:value for key,value in body.model_dump().items() if value is not None};payload={**old.routing_payload,**{key:update[key] for key in ("title","description") if key in update}}
            if "estimated_duration_minutes" in update:payload["estimated_minutes"]=update["estimated_duration_minutes"]
            if "target_module" in update and update["target_module"]=="HOLY_HABIT_ENGINE":raise HTTPException(status_code=422,detail="Habit conversion requires a separate second-confirmation flow")
            changed=old.model_copy(update={"intervention_id":str(uuid.uuid4()),**update,"routing_payload":payload,"generation_method":"USER_MODIFIED","created_at":datetime.now(timezone.utc)});_insert_proposal(cur,user["email"],str(row["context_id"]),str(row["mirror_id"]) if row.get("mirror_id") else None,changed,supersedes_id=proposal_id,version=int(row["version"])+1);cur.execute("UPDATE formation_twin_intervention_proposals SET lifecycle_status='SUPERSEDED',decision_status='ACCEPTED_WITH_MODIFICATION' WHERE id=%s",(proposal_id,));_publish(cur,user["email"],"formation_twin.intervention_modified",{"proposal_id":changed.intervention_id,"status":"PROPOSED"});conn.commit();return {"ok":True,"proposal_id":changed.intervention_id,"supersedes_proposal_id":proposal_id,"proposal":_json(changed)}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


def _new_candidate(cur,email: str,row: dict[str,Any],smaller: bool)->MicroIntervention:
    cur.execute("SELECT * FROM formation_twin_reflection_contexts WHERE email=%s AND id=%s",(email,row["context_id"]));context_row=cur.fetchone()
    if not context_row:raise HTTPException(status_code=409,detail="Reflection context is no longer available")
    context=_context_from_row(dict(context_row));current=_proposal_model(row)
    if smaller:return make_action_smaller(current,context)
    candidates=[item for item in generate_intervention_candidates(context) if item.intervention_type!=current.intervention_type]
    return select_minimum_action(context,candidates)["selected"] if candidates else make_action_smaller(current,context)


@router.post("/interventions/proposals/{proposal_id}/alternative")
def alternative_intervention_proposal(request: Request,proposal_id: str)->dict[str,Any]:
    return _replace_candidate(request,proposal_id,False)


@router.post("/interventions/proposals/{proposal_id}/smaller")
def smaller_intervention_proposal(request: Request,proposal_id: str)->dict[str,Any]:
    return _replace_candidate(request,proposal_id,True)


def _replace_candidate(request: Request,proposal_id: str,smaller: bool)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);row=_proposal(cur,user["email"],proposal_id);new=_new_candidate(cur,user["email"],row,smaller);_insert_proposal(cur,user["email"],str(row["context_id"]),str(row["mirror_id"]) if row.get("mirror_id") else None,new,supersedes_id=proposal_id,version=int(row["version"])+1);cur.execute("UPDATE formation_twin_intervention_proposals SET lifecycle_status='SUPERSEDED',decision_status=%s WHERE id=%s",("ACCEPTED_WITH_MODIFICATION" if smaller else "REQUESTED_ALTERNATIVE",proposal_id));_publish(cur,user["email"],"formation_twin.intervention_modified",{"proposal_id":new.intervention_id,"status":"PROPOSED"});conn.commit();return {"ok":True,"proposal":_json(new),"supersedes_proposal_id":proposal_id,"smaller":smaller}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


def _simple_decision(request: Request,proposal_id: str,status: str,event: str,body: ProposalDecisionBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);row=_proposal(cur,user["email"],proposal_id);decision_id=_save_decision(cur,user["email"],proposal_id,status,body)
            if status=="REJECTED":
                tenant,profile=_identity(user["email"]);preference_id=str(uuid.uuid4());cur.execute("INSERT INTO formation_twin_intervention_preferences (id,tenant_id,profile_id,email,preference_type,preference_value_json,source_review_ids_json,scope,active) VALUES (%s,%s,%s,%s,'BLOCKED_INTERVENTION_TYPE',%s,'[]','CURRENT_USER',TRUE)",(preference_id,tenant,profile,user["email"],Json({"intervention_type":row["intervention_type"]})))
            _publish(cur,user["email"],event,{"proposal_id":proposal_id,"decision_id":decision_id,"decision_status":status});conn.commit();return {"ok":True,"decision_id":decision_id,"decision_status":status,"routed":False,"negative_label_created":False}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/interventions/proposals/{proposal_id}/defer")
def defer_intervention_proposal(request: Request,proposal_id: str,body: ProposalDecisionBody)->dict[str,Any]:return _simple_decision(request,proposal_id,"DEFERRED","formation_twin.intervention_deferred",body)
@router.post("/interventions/proposals/{proposal_id}/skip")
def skip_intervention_proposal(request: Request,proposal_id: str,body: ProposalDecisionBody)->dict[str,Any]:return _simple_decision(request,proposal_id,"SKIPPED","formation_twin.intervention_skipped",body)
@router.post("/interventions/proposals/{proposal_id}/reject")
def reject_intervention_proposal(request: Request,proposal_id: str,body: ProposalDecisionBody)->dict[str,Any]:return _simple_decision(request,proposal_id,"REJECTED","formation_twin.intervention_rejected",body)
@router.post("/interventions/proposals/{proposal_id}/no-action")
def no_action_intervention_proposal(request: Request,proposal_id: str,body: ProposalDecisionBody)->dict[str,Any]:return _simple_decision(request,proposal_id,"NO_ACTION_SELECTED","formation_twin.no_action_selected",body)


@router.get("/interventions")
def list_interventions(request: Request)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("SELECT e.*,p.title,p.intervention_type,p.estimated_duration_minutes FROM formation_twin_intervention_executions e JOIN formation_twin_intervention_proposals p ON p.id=e.proposal_id WHERE e.email=%s ORDER BY e.created_at DESC",(user["email"],));items=[dict(row) for row in cur.fetchall()]
        return {"ok":True,"interventions":items,"completion_is_not_effect":True,"unfinished_is_not_failure":True}
    finally:_state["release_db"](conn)


@router.get("/interventions/{intervention_id}")
def get_intervention(request: Request,intervention_id: str)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("SELECT e.*,p.title,p.description,p.intervention_type FROM formation_twin_intervention_executions e JOIN formation_twin_intervention_proposals p ON p.id=e.proposal_id WHERE e.email=%s AND e.id=%s",(user["email"],intervention_id));row=cur.fetchone()
        if not row:raise HTTPException(status_code=404,detail="Intervention not found")
        return {"ok":True,"intervention":dict(row),"completion_is_not_effect":True}
    finally:_state["release_db"](conn)


def _execution_status(request: Request,intervention_id: str,status: str,event: str,column: str)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);cur.execute(f"UPDATE formation_twin_intervention_executions SET execution_status=%s,{column}=now(),updated_at=now() WHERE email=%s AND id=%s RETURNING id",(status,user["email"],intervention_id))
            if not cur.fetchone():raise HTTPException(status_code=404,detail="Intervention not found")
            _publish(cur,user["email"],event,{"execution_id":intervention_id,"execution_status":status});conn.commit();return {"ok":True,"execution_status":status,"effect_not_inferred":True}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/interventions/{intervention_id}/start")
def start_intervention(request: Request,intervention_id: str)->dict[str,Any]:return _execution_status(request,intervention_id,"STARTED","formation_twin.intervention_started","started_at")
@router.post("/interventions/{intervention_id}/complete")
def complete_intervention(request: Request,intervention_id: str)->dict[str,Any]:return _execution_status(request,intervention_id,"COMPLETED","formation_twin.intervention_completed","completed_at")
@router.post("/interventions/{intervention_id}/stop")
def stop_intervention(request: Request,intervention_id: str)->dict[str,Any]:return _execution_status(request,intervention_id,"STOPPED","formation_twin.intervention_stopped","stopped_at")
@router.post("/interventions/{intervention_id}/cancel")
def cancel_intervention(request: Request,intervention_id: str)->dict[str,Any]:return _execution_status(request,intervention_id,"CANCELLED","formation_twin.intervention_cancelled","cancelled_at")


@router.get("/interventions/{intervention_id}/effect-review")
def get_effect_review(request: Request,intervention_id: str)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("SELECT * FROM formation_twin_intervention_effect_reviews WHERE email=%s AND intervention_id=%s AND deleted_at IS NULL",(user["email"],intervention_id));row=cur.fetchone()
        return {"ok":True,"review":dict(row) if row else None,"maximum_questions":3,"causality_inferred":False}
    finally:_state["release_db"](conn)


@router.post("/interventions/{intervention_id}/effect-review")
def create_effect_review(request: Request,intervention_id: str,body: EffectReviewBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]();tenant,profile=_identity(user["email"])
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);cur.execute("SELECT e.id,p.intervention_type FROM formation_twin_intervention_executions e JOIN formation_twin_intervention_proposals p ON p.id=e.proposal_id WHERE e.email=%s AND e.id=%s",(user["email"],intervention_id));execution=cur.fetchone()
            if not execution:raise HTTPException(status_code=404,detail="Intervention not found")
            settings=_ensure_settings(cur,user["email"])
            if not settings.get("effect_review_enabled"):raise HTTPException(status_code=409,detail="Effect review tracking is disabled")
            review=EffectReview(review_id=str(uuid.uuid4()),intervention_id=intervention_id,execution_status=body.execution_status,user_reported_helpfulness=body.helpfulness,user_reported_burden=body.burden,emotional_effect=body.emotional_effect,formation_effect=body.formation_effect,practical_effect=body.practical_effect,what_helped=body.what_helped,what_did_not_help=body.what_did_not_help,preferred_adjustment=body.preferred_adjustment,reviewed_at=datetime.now(timezone.utc));cur.execute("INSERT INTO formation_twin_intervention_effect_reviews (id,tenant_id,profile_id,email,intervention_id,execution_status,helpfulness,burden,emotional_effect_json,formation_effect_json,practical_effect_json,what_helped,what_did_not_help,preferred_adjustment,statement_type) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'USER_REPORTED_FACT') ON CONFLICT(email,intervention_id) DO UPDATE SET execution_status=EXCLUDED.execution_status,helpfulness=EXCLUDED.helpfulness,burden=EXCLUDED.burden,emotional_effect_json=EXCLUDED.emotional_effect_json,formation_effect_json=EXCLUDED.formation_effect_json,practical_effect_json=EXCLUDED.practical_effect_json,what_helped=EXCLUDED.what_helped,what_did_not_help=EXCLUDED.what_did_not_help,preferred_adjustment=EXCLUDED.preferred_adjustment,created_at=now(),deleted_at=NULL RETURNING id",(review.review_id,tenant,profile,user["email"],intervention_id,body.execution_status,body.helpfulness,body.burden,Json(_json(body.emotional_effect)) if body.emotional_effect else None,Json(_json(body.formation_effect)) if body.formation_effect else None,Json(_json(body.practical_effect)) if body.practical_effect else None,body.what_helped,body.what_did_not_help,body.preferred_adjustment));saved_id=str(cur.fetchone()["id"]);updates=learn_intervention_preferences(review,intervention_type=execution["intervention_type"],learning_enabled=bool(settings.get("preference_learning_enabled")))
            for update in updates:
                preference_id=str(uuid.uuid4());cur.execute("INSERT INTO formation_twin_intervention_preferences (id,tenant_id,profile_id,email,preference_type,preference_value_json,source_review_ids_json,confidence,scope,active) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'CURRENT_USER',TRUE)",(preference_id,tenant,profile,user["email"],update["preference_type"],Json(update["preference_value"]),Json([saved_id]),update["confidence"]));_publish(cur,user["email"],"formation_twin.intervention_preference_updated",{"preference_id":preference_id,"review_id":saved_id,"status":"ACTIVE"})
            _publish(cur,user["email"],"formation_twin.intervention_effect_reviewed",{"review_id":saved_id,"execution_id":intervention_id,"execution_status":body.execution_status});conn.commit();return {"ok":True,"review":_json(review),"preference_updates":updates,"causality_inferred":False,"user_failure_label":False}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.delete("/interventions/{intervention_id}/effect-review")
def delete_effect_review(request: Request,intervention_id: str)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("UPDATE formation_twin_intervention_effect_reviews SET deleted_at=now() WHERE email=%s AND intervention_id=%s AND deleted_at IS NULL RETURNING id",(user["email"],intervention_id));row=cur.fetchone();conn.commit()
        return {"ok":True,"deleted":bool(row),"learned_preferences_require_separate_reset":True}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.get("/intervention-preferences")
def get_intervention_preferences(request: Request)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);settings=_ensure_settings(cur,user["email"]);cur.execute("SELECT * FROM formation_twin_intervention_preferences WHERE email=%s AND active=TRUE ORDER BY created_at DESC",(user["email"],));items=[dict(row) for row in cur.fetchall()]
        return {"ok":True,"settings":settings,"learned_preferences":items,"shared_model_training":False}
    finally:_state["release_db"](conn)


@router.patch("/intervention-preferences")
def patch_intervention_preferences(request: Request,body: PreferencePatchBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);_ensure_settings(cur,user["email"]);updates=[];values=[]
            mapping={"preferred_intervention_types":"preferred_intervention_types_json","blocked_intervention_types":"blocked_intervention_types_json","maximum_action_minutes":"maximum_action_minutes","preference_learning_enabled":"preference_learning_enabled"}
            for field,column in mapping.items():
                value=getattr(body,field)
                if value is not None:updates.append(f"{column}=%s");values.append(Json(value) if isinstance(value,list) else value)
            if body.reflection_only is not None:updates.append("daily_mirror_mode=%s");values.append("REFLECTION_ONLY" if body.reflection_only else "ON_DEMAND")
            if updates:cur.execute(f"UPDATE formation_twin_reflection_settings SET {','.join(updates)},updated_at=now() WHERE email=%s RETURNING *",(*values,user["email"]));settings=dict(cur.fetchone())
            else:settings=_ensure_settings(cur,user["email"])
            conn.commit();return {"ok":True,"settings":settings,"safety_thresholds_unchanged":True}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.post("/intervention-preferences/reset")
def reset_intervention_preferences(request: Request)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);cur.execute("UPDATE formation_twin_intervention_preferences SET active=FALSE,revoked_at=now() WHERE email=%s AND active=TRUE",(user["email"],));count=cur.rowcount;cur.execute("UPDATE formation_twin_reflection_settings SET preferred_intervention_types_json='[]',blocked_intervention_types_json='[]',updated_at=now() WHERE email=%s",(user["email"],));conn.commit();return {"ok":True,"revoked_preferences":count,"learning_can_be_disabled_in_settings":True}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.get("/reflection-settings")
def get_reflection_settings(request: Request)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:_owner(cur,user["email"]);settings=_ensure_settings(cur,user["email"]);conn.commit();return {"ok":True,"settings":settings,"notification_content":sanitize_notification_content(),"daily_push_default":False}
    finally:_state["release_db"](conn)


@router.patch("/reflection-settings")
def patch_reflection_settings(request: Request,body: ReflectionSettingsBody)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);_ensure_settings(cur,user["email"]);mapping={"daily_mirror_mode":"daily_mirror_mode","weekly_review_enabled":"weekly_review_enabled","effect_review_enabled":"effect_review_enabled","cross_module_routing_enabled":"cross_module_routing_enabled","preference_learning_enabled":"preference_learning_enabled","interventions_paused":"interventions_paused","reminder_settings":"reminder_settings_json","quiet_hours":"quiet_hours_json","capacity_default":"capacity_default","maximum_action_minutes":"maximum_action_minutes","preferred_intervention_types":"preferred_intervention_types_json","blocked_intervention_types":"blocked_intervention_types_json"};updates=[];values=[]
            for field,column in mapping.items():
                value=getattr(body,field)
                if value is not None:updates.append(f"{column}=%s");values.append(Json(value) if isinstance(value,(dict,list)) else value)
            if updates:cur.execute(f"UPDATE formation_twin_reflection_settings SET {','.join(updates)},updated_at=now() WHERE email=%s RETURNING *",(*values,user["email"]));settings=dict(cur.fetchone())
            else:settings=_ensure_settings(cur,user["email"])
            conn.commit();return {"ok":True,"settings":settings,"notification_content":sanitize_notification_content(),"hidden_automation":False}
    except Exception:conn.rollback();raise
    finally:_state["release_db"](conn)


@router.get("/reflections/data-quality")
def get_reflection_data_quality(request: Request)->dict[str,Any]:
    user=_user(request);conn=_state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur,user["email"]);cur.execute("SELECT id,source_references_json FROM formation_twin_reflection_mirrors WHERE email=%s AND status='ACTIVE' AND deleted_at IS NULL",(user["email"],));mirrors=[dict(row) for row in cur.fetchall()];cur.execute("SELECT id,intervention_type,estimated_duration_minutes,target_module,routing_payload_json,decision_status FROM formation_twin_intervention_proposals WHERE email=%s AND lifecycle_status='PROPOSED' AND deleted_at IS NULL",(user["email"],));proposals=[dict(row) for row in cur.fetchall()];settings=_ensure_settings(cur,user["email"]);cur.execute("SELECT COALESCE(safety_json->>'safety_level','NONE') AS level FROM formation_twin_life_events WHERE email=%s AND deleted_at IS NULL ORDER BY occurred_at DESC LIMIT 1",(user["email"],));safety=cur.fetchone();report=reflection_data_quality(mirrors,proposals,safety_level=(safety or {}).get("level","NONE"),effect_tracking_enabled=bool(settings.get("effect_review_enabled")))
        return {"ok":True,**report}
    finally:_state["release_db"](conn)


@router.get("/reflection-jobs")
def get_reflection_jobs(request: Request)->dict[str,Any]:
    _user(request)
    return {"ok":True,"jobs":SCHEDULED_JOBS,"daily_mirror_default":"ON_DEMAND","notification_content":sanitize_notification_content(),"scheduler_adapter":"existing scheduler / opt-in reminders"}


@router.post("/engagement-safety/validate")
def validate_engagement(request: Request,proposal: dict[str,Any])->dict[str,Any]:
    _user(request)
    return {"ok":True,**validate_engagement_proposal(proposal)}
