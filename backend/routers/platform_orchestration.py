"""Spiritual Planet Batch 9 integration and unified orchestration API.

The router is the only platform boundary allowed to call source adapters. It
stores references and decisions, never full journals, prayers, crisis text or
unconfirmed hypotheses as facts.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from psycopg2.extras import Json

from platform_orchestration.arbitration import arbitrate_recommendations
from platform_orchestration.commands import validate_command
from platform_orchestration.context_broker import resolve_projection
from platform_orchestration.data_quality import scan_platform_contracts
from platform_orchestration.contracts import (
    Actor,
    ContextRequest,
    DeletionRequest,
    OrchestrationRequest,
    RecommendationCandidate,
    RebuildRequest,
    UnifiedCommand,
    UnifiedEventEnvelope,
    assert_platform_safe,
)
from platform_orchestration.orchestrator import run_workflow
from platform_orchestration.policy import decide_context_access
from platform_orchestration.registry import (
    AGENT_CAPABILITIES,
    EVENT_SCHEMAS,
    PROJECTIONS,
    SOURCE_OF_TRUTH,
    event_registration,
)


router = APIRouter(prefix="/api/v1/platform", tags=["spiritual-planet-platform"])
_state: dict[str, Any] = {}
ACTIVE_ACTION_STATUSES = ("CONFIRMED", "SCHEDULED", "IN_PROGRESS")
LOCAL_ACTION_MODULE = "platform_orchestrator"
FEATURE_FLAGS = {
    "orchestration": "SPIRITUAL_PLANET_UNIFIED_ORCHESTRATION_ENABLED",
    "context": "SPIRITUAL_PLANET_CONTEXT_BROKER_ENABLED",
    "arbitration": "SPIRITUAL_PLANET_RECOMMENDATION_ARBITRATION_ENABLED",
    "home": "SPIRITUAL_PLANET_UNIFIED_HOME_ENABLED",
    "search": "SPIRITUAL_PLANET_CROSS_MODULE_SEARCH_ENABLED",
    "deletion": "SPIRITUAL_PLANET_DELETION_COORDINATOR_ENABLED",
    "agents": "SPIRITUAL_PLANET_AGENT_REGISTRY_ENABLED",
    "health": "SPIRITUAL_PLANET_INTEGRATION_HEALTH_ENABLED",
}


def init_platform_orchestration_router(*, get_db, release_db, get_session_user, to_shanghai_iso, is_admin=None) -> None:
    _state.update(locals())


def _enabled(feature: str) -> bool:
    return os.getenv(FEATURE_FLAGS[feature], "true").strip().lower() in {"1", "true", "yes", "on"}


def _require_feature(feature: str) -> None:
    if not _enabled(feature):
        raise HTTPException(status_code=503, detail={"code": "FEATURE_DISABLED", "feature": feature})


def _user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _admin(request: Request) -> dict:
    user = _user(request)
    check = _state.get("is_admin")
    if not check or not check(user["email"]):
        raise HTTPException(status_code=403, detail="platform admin only")
    return user


def _identity(email: str) -> tuple[str, str]:
    return f"personal:{email.lower()}", email.lower()


def _owner(cur, email: str) -> None:
    cur.execute("SELECT set_config('app.current_user_email',%s,true)", (email,))


def _json(value: Any, fallback):
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value) if value is not None else fallback
    except Exception:
        return fallback


def _iso(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat() if value else None


def _publish(cur, *, email: str, event_type: str, payload: dict[str, Any], correlation_id: uuid.UUID | None = None) -> None:
    registration = event_registration(event_type)
    if not registration:
        raise RuntimeError("UNREGISTERED_PLATFORM_EVENT")
    assert_platform_safe(payload)
    extra = set(payload) - set(registration["allowed_payload_fields"])
    if extra:
        raise RuntimeError("EVENT_PAYLOAD_CONTRACT_VIOLATION:" + ",".join(sorted(extra)))
    event_id = uuid.uuid4()
    correlation_id = correlation_id or uuid.uuid4()
    now = datetime.now(timezone.utc)
    envelope = UnifiedEventEnvelope(
        event_id=event_id, event_type=event_type, event_version="1.0",
        tenant_id=_identity(email)[0], subject_user_id=email,
        actor=Actor(actor_type="USER", actor_id=email), producer="platform_orchestrator",
        occurred_at=now, published_at=now, correlation_id=correlation_id,
        trace_id=hashlib.sha256(f"{correlation_id}:{event_id}".encode()).hexdigest()[:32],
        data_classification="HIGHLY_SENSITIVE", purpose_tags=["PLATFORM_COORDINATION"],
        consent_reference_ids=[], schema_uri=registration["schema_uri"], payload=payload,
    )
    cur.execute(
        "INSERT INTO domain_events(aggregate_type,aggregate_id,event_type,payload) VALUES(%s,%s,%s,%s)",
        ("spiritual_planet", email, event_type, Json(envelope.model_dump(mode="json"))),
    )


def _safe_ref(record_id: Any, source_module: str, record_type: str, status: str = "OBSERVED") -> dict[str, str]:
    return {
        "source_module": source_module,
        "source_record_type": record_type,
        "source_record_id": str(record_id),
        "statement_status": status,
    }


def _source_adapter(cur, email: str, projection_name: str) -> tuple[dict, dict, list[dict]]:
    """The Context Broker's monolith adapter; callers must not use it directly."""
    confirmed: dict[str, Any] = {}
    pending: dict[str, Any] = {}
    refs: list[dict] = []

    cur.execute(
        "SELECT id,event_type,occurred_at,source_module,status FROM formation_twin_life_events "
        "WHERE email=%s AND deleted_at IS NULL AND status='ACCEPTED' AND exclude_from_twin_processing=FALSE "
        "AND processing_preference='ALLOW_FUTURE_ANALYSIS' "
        "ORDER BY occurred_at DESC LIMIT 20",
        (email,),
    )
    event_rows = cur.fetchall()
    timeline_refs = []
    for record_id, event_type, occurred_at, source_module, status in event_rows:
        refs.append(_safe_ref(record_id, source_module or "formation_twin", "life_event", "OBSERVED"))
        timeline_refs.append({
            "source_module": source_module or "formation_twin", "source_record_type": "life_event",
            "source_record_id": str(record_id), "event_type": event_type,
            "occurred_at": _iso(occurred_at), "status": status,
            "display_route": "/formation-twin/events",
        })

    cur.execute(
        "SELECT id,emotion_label,intensity,occurred_at FROM formation_twin_emotion_observations "
        "WHERE email=%s AND deleted_at IS NULL AND processing_status='ACTIVE' "
        "AND source_kind<>'MODEL' AND user_review_status IN('NOT_REQUIRED','CONFIRMED','ACCEPTED') "
        "ORDER BY occurred_at DESC LIMIT 5",
        (email,),
    )
    emotion_rows = cur.fetchall()
    confirmed_emotions = []
    for record_id, label, intensity, occurred_at in emotion_rows:
        confirmed_emotions.append({"reference_id": str(record_id), "label": label, "intensity": intensity, "occurred_at": _iso(occurred_at)})
        refs.append(_safe_ref(record_id, "formation_twin", "emotion_observation", "CONFIRMED"))

    cur.execute(
        "SELECT id,node_type,user_review_status,occurred_at FROM formation_twin_formation_nodes "
        "WHERE email=%s AND deleted_at IS NULL AND processing_status='ACTIVE' "
        "AND statement_type='USER_CONFIRMED_FORMATION_PATTERN' ORDER BY occurred_at DESC LIMIT 20",
        (email,),
    )
    node_rows = cur.fetchall()
    node_items: dict[str, list[dict]] = {}
    for record_id, node_type, review_status, occurred_at in node_rows:
        item = {"reference_id": str(record_id), "type": node_type, "occurred_at": _iso(occurred_at)}
        node_items.setdefault(node_type, []).append(item)
        refs.append(_safe_ref(record_id, "formation_twin", "formation_node", "CONFIRMED"))

    cur.execute(
        "SELECT id,node_type,occurred_at FROM formation_twin_formation_nodes WHERE email=%s AND deleted_at IS NULL "
        "AND processing_status='ACTIVE' AND source_kind='MODEL' AND user_review_status='PENDING' "
        "ORDER BY occurred_at DESC LIMIT 10",
        (email,),
    )
    pending_nodes = [{"reference_id": str(row[0]), "type": row[1], "occurred_at": _iso(row[2])} for row in cur.fetchall()]
    for item in pending_nodes:
        refs.append(_safe_ref(item["reference_id"], "formation_twin", "formation_node", "PENDING"))

    cur.execute(
        "SELECT id,pattern_type,scope_json,lifecycle_status,last_observed_at,is_alternative_response "
        "FROM formation_twin_patterns WHERE email=%s AND deleted_at IS NULL "
        "AND lifecycle_status IN('CONFIRMED_ACTIVE','CONFIRMED_CONTEXTUAL','WEAKENING') "
        "AND user_review_status IN('CONFIRMED','PARTIALLY_CONFIRMED','SCOPE_NARROWED','SCOPE_EXPANDED') "
        "ORDER BY last_observed_at DESC LIMIT 10",
        (email,),
    )
    long_term_patterns = [{
        "reference_id": str(row[0]), "type": row[1], "scope": _json(row[2], {}),
        "status": row[3], "last_observed_at": _iso(row[4]), "is_alternative_response": bool(row[5]),
    } for row in cur.fetchall()]
    for item in long_term_patterns:
        refs.append(_safe_ref(item["reference_id"], "formation_twin", "formation_pattern", "CONFIRMED"))

    cur.execute(
        "SELECT id,title,season_type,started_at FROM formation_twin_life_seasons "
        "WHERE email=%s AND deleted_at IS NULL AND active=TRUE AND user_review_status IN('CONFIRMED','PARTIALLY_CONFIRMED') "
        "ORDER BY started_at DESC LIMIT 5",
        (email,),
    )
    active_seasons = [{"reference_id": str(row[0]), "title": row[1], "type": row[2], "started_at": _iso(row[3])} for row in cur.fetchall()]
    for item in active_seasons:
        refs.append(_safe_ref(item["reference_id"], "formation_twin", "life_season", "CONFIRMED"))

    cur.execute(
        "SELECT energy_level,stress_level,occurred_at,id FROM formation_twin_energy_stress_observations "
        "WHERE email=%s AND deleted_at IS NULL ORDER BY occurred_at DESC LIMIT 1",
        (email,),
    )
    energy_row = cur.fetchone()
    capacity_mode = "NORMAL"
    if energy_row and energy_row[0] is not None:
        capacity_mode = "VERY_LOW" if energy_row[0] <= 3 else "LOW" if energy_row[0] <= 5 else "NORMAL"
        refs.append(_safe_ref(energy_row[3], "formation_twin", "energy_observation", "OBSERVED"))

    cur.execute(
        "SELECT safety_json FROM formation_twin_life_events WHERE email=%s AND deleted_at IS NULL "
        "ORDER BY occurred_at DESC LIMIT 1",
        (email,),
    )
    safety_row = cur.fetchone()
    safety_json = _json(safety_row[0], {}) if safety_row else {}
    safety_level = str(safety_json.get("safety_level") or safety_json.get("risk_level") or "NONE").upper()
    if safety_level not in {"NONE", "CONCERN", "ELEVATED", "IMMINENT"}:
        safety_level = "CONCERN"

    cur.execute(
        "SELECT id,source_module,source_record_id,title,action_type,status,estimated_duration_minutes,occurred_at "
        "FROM spiritual_planet_unified_actions WHERE email=%s AND deleted_at IS NULL "
        "AND status IN('CONFIRMED','SCHEDULED','IN_PROGRESS') ORDER BY focus_action DESC,created_at DESC LIMIT 3",
        (email,),
    )
    active_actions = [{
        "id": str(row[0]), "source_module": row[1], "source_record_id": row[2], "title": row[3],
        "action_type": row[4], "status": row[5], "estimated_duration_minutes": row[6], "occurred_at": _iso(row[7]),
    } for row in cur.fetchall()]

    confirmed.update({
        "user_selected_prayer_needs": [],
        "confirmed_emotional_context": confirmed_emotions,
        "confirmed_fears": node_items.get("FEAR", []),
        "grace_factors": node_items.get("GRACE_EVIDENCE", []),
        "selected_scripture_themes": [],
        "user_selected_goal": None,
        "capacity_mode": capacity_mode,
        "preferred_duration_minutes": 2 if capacity_mode != "NORMAL" else 10,
        "blocked_intervention_types": ["HIGH_BURDEN_ACTION"] if capacity_mode != "NORMAL" else [],
        "confirmed_alternative_response": next((item for item in long_term_patterns if item["is_alternative_response"]), None),
        "user_confirmed_attention_pattern": (node_items.get("ATTENTION_PATTERN") or [None])[0],
        "preferred_boundary_type": None, "risk_time_window": None, "sensitive_reason_included": False,
        "active_life_seasons": active_seasons,
        "user_confirmed_gifts": node_items.get("GIFT", []), "service_experience": [],
        "capacity_constraints": [capacity_mode] if capacity_mode != "NORMAL" else [], "unresolved_calling_questions": [],
        "participation_goals": [], "relationship_support_needs": [], "pastoral_conversation_questions": [], "church_experience_summaries": [],
        "confirmed_calling_directions": node_items.get("CALLING_DIRECTION", []), "equipping_progress": [],
        "language_culture_preparation": [], "family_health_readiness": [], "user_shared_constraints": [],
        "confirmed_patterns": long_term_patterns or [item for items in node_items.values() for item in items][:10],
        "confirmed_practices": node_items.get("SPIRITUAL_PRACTICE", []), "limitations": ["NO_RAW_SOURCE_TEXT"],
        "scripture_references": [],
        "today_report": timeline_refs[0] if timeline_refs else None,
        "safety_summary": {"level": safety_level, "details_included": False},
        "confirmed_theme": next(iter(node_items), None), "active_action_references": active_actions,
        "timeline_references": timeline_refs,
        "confirmed_search_references": [],
        "safety_level": safety_level, "safety_plan_available": safety_level in {"ELEVATED", "IMMINENT"},
        "human_connection_available": True, "professional_support_route": "/sos",
    })
    pending.update({"confirmed_patterns": pending_nodes, "confirmed_emotional_context": []})
    return confirmed, pending, refs


def _stored_consent(cur, email: str, body: ContextRequest) -> tuple[bool, list[str], set[str]]:
    cur.execute(
        "SELECT id,allowed_fields FROM spiritual_planet_context_consents WHERE email=%s AND requester_module=%s "
        "AND purpose=%s AND projection_name=%s AND consent_status='ACTIVE'",
        (email, body.requester_module, body.purpose, body.requested_projection),
    )
    row = cur.fetchone()
    if not row:
        return False, [], set()
    return True, [str(row[0])], set(_json(row[1], []))


def _resolve_context(cur, *, email: str, body: ContextRequest, interactive_user_request: bool = False):
    if body.subject_user_id and body.subject_user_id.lower() != email.lower():
        raise HTTPException(status_code=403, detail="cross-user context is forbidden")
    consent_active, consent_refs, consent_fields = _stored_consent(cur, email, body)
    if interactive_user_request and body.requester_module == LOCAL_ACTION_MODULE:
        consent_active = True
        consent_refs = [f"interactive:{body.correlation_id}"]
        consent_fields = set(PROJECTIONS.get(body.requested_projection, {}).get("fields", []))
    decision = decide_context_access(body, consent_active=consent_active, consent_fields=consent_fields)
    context_id = uuid.uuid4()
    response = None
    if decision.allowed:
        confirmed, pending, refs = _source_adapter(cur, email, body.requested_projection)
        response = resolve_projection(
            body, decision, confirmed_source=confirmed, pending_source=pending,
            source_references=refs, consent_reference_ids=consent_refs,
        )
        context_id = response.context_id
    cur.execute(
        "INSERT INTO spiritual_planet_context_access_audit(id,tenant_id,email,context_id,requester_module,purpose,projection_name,"
        "requested_fields,allowed_fields,denied_fields,decision,reason_codes,correlation_id,consent_reference_ids,expires_at) "
        "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            str(uuid.uuid4()), _identity(email)[0], email, str(context_id), body.requester_module, body.purpose,
            body.requested_projection, Json(body.requested_fields), Json(decision.allowed_fields), Json(decision.denied_fields),
            "ALLOWED" if decision.allowed else "DENIED", Json(decision.decision_reason_codes), str(body.correlation_id),
            Json(consent_refs), response.expires_at if response else None,
        ),
    )
    _publish(
        cur, email=email,
        event_type="spiritual_planet.context_projection_created" if decision.allowed else "spiritual_planet.context_access_denied",
        payload={
            "context_id": str(context_id), "projection_name": body.requested_projection,
            "requester_module": body.requester_module, "purpose": body.purpose,
            "reason_codes": decision.decision_reason_codes,
        }, correlation_id=body.correlation_id,
    )
    return decision, response


class ContextResolveBody(ContextRequest):
    interactive_user_confirmation: bool = False


class ConsentBody(BaseModel):
    requester_module: str = Field(min_length=1, max_length=80)
    purpose: str = Field(min_length=1, max_length=80)
    allowed_fields: list[str] = Field(default_factory=list, max_length=50)
    active: bool = True


class CandidateDecisionBody(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    estimated_duration_minutes: int | None = Field(default=None, ge=0, le=180)


class ActionFilter(BaseModel):
    pass


@router.get("/schemas/events")
def event_schemas(request: Request) -> dict:
    _user(request)
    return {"ok": True, "schemas": list(EVENT_SCHEMAS.values()), "count": len(EVENT_SCHEMAS)}


@router.get("/data-quality")
def platform_data_quality(request: Request) -> dict:
    _admin(request)
    return {"ok": True, "report": scan_platform_contracts(), "user_content_scanned": False}


@router.post("/context/resolve")
def context_resolve(body: ContextResolveBody, request: Request) -> dict:
    _require_feature("context")
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            decision, response = _resolve_context(
                cur, email=user["email"], body=ContextRequest.model_validate(body.model_dump(exclude={"interactive_user_confirmation"})),
                interactive_user_request=body.interactive_user_confirmation,
            )
        conn.commit()
    finally:
        _state["release_db"](conn)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail={"code": "CONTEXT_DENIED", "reason_codes": decision.decision_reason_codes})
    return {"ok": True, "context": response.model_dump(mode="json"), "decision": decision.model_dump(mode="json")}


@router.get("/context/access-log")
def context_access_log(request: Request, limit: int = Query(default=50, ge=1, le=200)) -> dict:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            cur.execute(
                "SELECT id,requester_module,purpose,projection_name,allowed_fields,denied_fields,decision,reason_codes,created_at,expires_at "
                "FROM spiritual_planet_context_access_audit WHERE email=%s ORDER BY created_at DESC LIMIT %s",
                (user["email"], limit),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "accesses": [{
        "id": str(r[0]), "requester_module": r[1], "purpose": r[2], "projection_name": r[3],
        "allowed_fields": _json(r[4], []), "denied_fields": _json(r[5], []), "decision": r[6],
        "reason_codes": _json(r[7], []), "created_at": _iso(r[8]), "expires_at": _iso(r[9]),
    } for r in rows]}


@router.get("/context/consents")
def list_consents(request: Request) -> dict:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            cur.execute(
                "SELECT id,requester_module,purpose,projection_name,allowed_fields,consent_status,updated_at FROM spiritual_planet_context_consents "
                "WHERE email=%s ORDER BY updated_at DESC", (user["email"],),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "consents": [{"id": str(r[0]), "requester_module": r[1], "purpose": r[2], "projection_name": r[3], "allowed_fields": _json(r[4], []), "status": r[5], "updated_at": _iso(r[6])} for r in rows]}


@router.put("/context/consents/{projection_name}")
def set_consent(projection_name: str, body: ConsentBody, request: Request) -> dict:
    user = _user(request)
    definition = PROJECTIONS.get(projection_name)
    if not definition:
        raise HTTPException(status_code=404, detail="projection not registered")
    requested = body.allowed_fields or definition["fields"]
    if set(requested) - set(definition["fields"]):
        raise HTTPException(status_code=422, detail="allowed_fields exceed projection allowlist")
    tenant, email = _identity(user["email"])
    consent_id = uuid.uuid4()
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, email)
            cur.execute(
                "INSERT INTO spiritual_planet_context_consents(id,tenant_id,email,requester_module,purpose,projection_name,allowed_fields,consent_status,revoked_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(tenant_id,email,requester_module,purpose,projection_name) "
                "DO UPDATE SET allowed_fields=EXCLUDED.allowed_fields,consent_status=EXCLUDED.consent_status,revoked_at=EXCLUDED.revoked_at,updated_at=NOW() RETURNING id",
                (str(consent_id), tenant, email, body.requester_module, body.purpose, projection_name, Json(requested), "ACTIVE" if body.active else "REVOKED", None if body.active else datetime.now(timezone.utc)),
            )
            consent_id = cur.fetchone()[0]
            propagation_id = None
            if not body.active:
                propagation_id = uuid.uuid4()
                affected = sorted({body.requester_module, definition["source_module"], LOCAL_ACTION_MODULE})
                cur.execute("UPDATE spiritual_planet_orchestration_runs SET status='CANCELLED',completed_at=NOW() WHERE email=%s AND status IN('QUEUED','RUNNING')", (email,))
                cancelled_runs = cur.rowcount
                cur.execute("UPDATE spiritual_planet_notification_candidates SET status='CANCELLED' WHERE email=%s AND status='PENDING' AND source_module=%s", (email, body.requester_module))
                cancelled_notifications = cur.rowcount
                cur.execute("UPDATE spiritual_planet_search_references SET excluded=TRUE,updated_at=NOW() WHERE email=%s AND source_module=%s", (email, body.requester_module))
                stale = cur.rowcount
                cur.execute(
                    "INSERT INTO spiritual_planet_consent_propagation_jobs(id,tenant_id,email,consent_id,affected_modules,invalidated_contexts,cancelled_workflows,cancelled_notifications,stale_derived_outputs,status,completed_at) "
                    "VALUES(%s,%s,%s,%s,%s,0,%s,%s,%s,'COMPLETED',NOW())",
                    (str(propagation_id), tenant, email, str(consent_id), Json(affected), cancelled_runs, cancelled_notifications, stale),
                )
                _publish(cur, email=email, event_type="spiritual_planet.consent_propagation_completed", payload={"status": "COMPLETED", "result_code": "CONSENT_REVOKED"})
        conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "consent_id": str(consent_id), "status": "ACTIVE" if body.active else "REVOKED", "propagation_id": str(propagation_id) if propagation_id else None}


def _candidate_dict(row) -> dict:
    return {
        "id": str(row[0]), "source_module": row[1], "recommendation_type": row[2], "title": row[3],
        "description": row[4], "purpose": row[5], "estimated_duration_minutes": row[6],
        "burden_level": row[7], "safety_priority": row[8], "urgency": row[9],
        "requires_user_confirmation": row[10], "supporting_context_ids": _json(row[11], []),
        "target_module": row[12], "proposed_payload": _json(row[13], {}), "uses_pending_context": row[14],
        "expires_at": _iso(row[15]), "decision_status": row[16], "orchestration_run_id": str(row[17]),
    }


CANDIDATE_SELECT = (
    "SELECT id,source_module,recommendation_type,title,description,purpose,estimated_duration_minutes,burden_level,"
    "safety_priority,urgency,requires_user_confirmation,supporting_context_ids,target_module,proposed_payload,uses_pending_context,"
    "expires_at,decision_status,orchestration_run_id FROM spiritual_planet_recommendation_candidates"
)


@router.post("/orchestrations/run")
def run_orchestration(body: OrchestrationRequest, request: Request) -> dict:
    _require_feature("orchestration")
    _require_feature("arbitration")
    user = _user(request)
    tenant, email = _identity(user["email"])
    run_id, trace_id = uuid.uuid4(), uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, email)
            cur.execute("SELECT COUNT(*) FROM spiritual_planet_unified_actions WHERE email=%s AND deleted_at IS NULL AND status IN('CONFIRMED','SCHEDULED','IN_PROGRESS')", (email,))
            active_count = int(cur.fetchone()[0])
            cur.execute(
                "INSERT INTO spiritual_planet_orchestration_runs(id,tenant_id,email,trigger_type,trigger_reference_id,user_intent_present,requested_outcome_code,correlation_id,trace_id,status,safety_state,capacity_mode,max_nodes,max_model_calls,started_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'RUNNING',%s,%s,%s,%s,NOW())",
                (str(run_id), tenant, email, body.trigger_type, body.trigger_reference_id, bool(body.user_intent), body.requested_outcome, str(body.correlation_id), trace_id, body.safety_state, body.capacity_mode, body.max_nodes, body.max_model_calls),
            )
            _publish(cur, email=email, event_type="spiritual_planet.orchestration_started", payload={"run_id": str(run_id), "status": "RUNNING"}, correlation_id=body.correlation_id)
            result = run_workflow(body, active_action_count=active_count)
            for candidate in body.candidate_recommendations:
                cur.execute(
                    "INSERT INTO spiritual_planet_recommendation_candidates(id,tenant_id,email,orchestration_run_id,source_module,recommendation_type,title,description,purpose,estimated_duration_minutes,burden_level,safety_priority,urgency,requires_user_confirmation,supporting_context_ids,target_module,proposed_payload,uses_pending_context,expires_at) "
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (str(candidate.id), tenant, email, str(run_id), candidate.source_module, candidate.recommendation_type, candidate.title, candidate.description, candidate.purpose, candidate.estimated_duration_minutes, candidate.burden_level, candidate.safety_priority, candidate.urgency, candidate.requires_user_confirmation, Json([str(v) for v in candidate.supporting_context_ids]), candidate.target_module, Json(candidate.proposed_payload), candidate.uses_pending_context, candidate.expires_at),
                )
            arb = result.get("arbitration") or {"selected_recommendation": None, "merged_candidates": [], "suppressed_candidates": [], "selection_rationale": [], "no_action_selected": True}
            selected = arb.get("selected_recommendation")
            cur.execute(
                "INSERT INTO spiritual_planet_arbitration_results(tenant_id,email,orchestration_run_id,selected_recommendation_id,merged_candidate_ids,suppressed_candidates,selection_rationale,no_action_selected) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (tenant, email, str(run_id), selected.get("id") if selected else None, Json(arb.get("merged_candidates", [])), Json(arb.get("suppressed_candidates", [])), Json(arb.get("selection_rationale", [])), bool(arb.get("no_action_selected", True))),
            )
            status = result["status"]
            cur.execute("UPDATE spiritual_planet_orchestration_runs SET status=%s,steps=%s,result_summary=%s,completed_at=NOW() WHERE id=%s AND email=%s", (status, Json(result.get("steps", [])), Json({"no_action_selected": arb.get("no_action_selected", True), "selected_recommendation_id": selected.get("id") if selected else None, "reason_codes": arb.get("selection_rationale", [])}), str(run_id), email))
            _publish(cur, email=email, event_type="spiritual_planet.orchestration_completed", payload={"run_id": str(run_id), "status": status, "selected_candidate_id": selected.get("id") if selected else None}, correlation_id=body.correlation_id)
        conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "run_id": str(run_id), "result": result}


@router.get("/orchestrations/{run_id}")
def get_orchestration(run_id: uuid.UUID, request: Request) -> dict:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            cur.execute("SELECT id,trigger_type,correlation_id,trace_id,status,safety_state,capacity_mode,steps,result_summary,created_at,completed_at FROM spiritual_planet_orchestration_runs WHERE id=%s AND email=%s", (str(run_id), user["email"]))
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not row:
        raise HTTPException(status_code=404, detail="orchestration not found")
    return {"ok": True, "run": {"id": str(row[0]), "trigger_type": row[1], "correlation_id": str(row[2]), "trace_id": row[3], "status": row[4], "safety_state": row[5], "capacity_mode": row[6], "steps": _json(row[7], []), "result": _json(row[8], {}), "created_at": _iso(row[9]), "completed_at": _iso(row[10])}}


@router.post("/orchestrations/{run_id}/cancel")
def cancel_orchestration(run_id: uuid.UUID, request: Request) -> dict:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            cur.execute("UPDATE spiritual_planet_orchestration_runs SET status='CANCELLED',completed_at=NOW() WHERE id=%s AND email=%s AND status IN('QUEUED','RUNNING')", (str(run_id), user["email"]))
            changed = cur.rowcount
        conn.commit()
    finally:
        _state["release_db"](conn)
    if not changed:
        raise HTTPException(status_code=409, detail="run is not cancellable")
    return {"ok": True, "run_id": str(run_id), "status": "CANCELLED"}


@router.get("/recommendations/current")
def current_recommendation(request: Request) -> dict:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            cur.execute(CANDIDATE_SELECT + " WHERE email=%s AND decision_status='PENDING' AND (expires_at IS NULL OR expires_at>NOW()) ORDER BY safety_priority ASC,created_at DESC LIMIT 1", (user["email"],))
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "recommendation": _candidate_dict(row) if row else None}


@router.get("/recommendations/{recommendation_id}")
def get_recommendation(recommendation_id: uuid.UUID, request: Request) -> dict:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            cur.execute(CANDIDATE_SELECT + " WHERE id=%s AND email=%s", (str(recommendation_id), user["email"]))
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not row:
        raise HTTPException(status_code=404, detail="recommendation not found")
    return {"ok": True, "recommendation": _candidate_dict(row)}


def _decision(recommendation_id: uuid.UUID, body: CandidateDecisionBody, request: Request, action: str) -> dict:
    user = _user(request)
    tenant, email = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, email)
            cur.execute(CANDIDATE_SELECT + " WHERE id=%s AND email=%s FOR UPDATE", (str(recommendation_id), email))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="recommendation not found")
            item = _candidate_dict(row)
            if item["decision_status"] != "PENDING":
                raise HTTPException(status_code=409, detail="recommendation already decided")
            if action in {"SKIPPED", "REJECTED"}:
                cur.execute("UPDATE spiritual_planet_recommendation_candidates SET decision_status=%s,decision_at=NOW() WHERE id=%s", (action, str(recommendation_id)))
                conn.commit()
                return {"ok": True, "recommendation_id": str(recommendation_id), "decision": action, "command": None}
            if action == "ALTERNATIVE_REQUESTED":
                cur.execute("UPDATE spiritual_planet_recommendation_candidates SET decision_status='ALTERNATIVE_REQUESTED',decision_at=NOW() WHERE id=%s", (str(recommendation_id),))
                cur.execute(CANDIDATE_SELECT + " WHERE email=%s AND orchestration_run_id=%s AND id<>%s AND decision_status='PENDING' ORDER BY safety_priority,estimated_duration_minutes LIMIT 1", (email, item["orchestration_run_id"], str(recommendation_id)))
                alternative = cur.fetchone()
                conn.commit()
                return {"ok": True, "recommendation_id": str(recommendation_id), "decision": action, "alternative": _candidate_dict(alternative) if alternative else None}
            title = body.title or item["title"]
            duration = body.estimated_duration_minutes if body.estimated_duration_minutes is not None else item["estimated_duration_minutes"]
            if action == "SMALLER_REQUESTED":
                duration = min(duration, 2)
                title = "保留一个两分钟以内、可随时停止的小行动"
            if action == "MODIFIED":
                cur.execute("UPDATE spiritual_planet_recommendation_candidates SET title=%s,estimated_duration_minutes=%s,decision_status='MODIFIED',decision_at=NOW() WHERE id=%s", (title, duration, str(recommendation_id)))
            else:
                cur.execute("UPDATE spiritual_planet_recommendation_candidates SET decision_status=%s,decision_at=NOW() WHERE id=%s", (action, str(recommendation_id)))
            if item["uses_pending_context"]:
                raise HTTPException(status_code=409, detail="pending context cannot drive a command")
            target = item["target_module"] or item["source_module"]
            confirmation_id, command_id = uuid.uuid4(), uuid.uuid4()
            allowed_payload = item["proposed_payload"] if isinstance(item["proposed_payload"], dict) else {}
            if target == LOCAL_ACTION_MODULE:
                allowed_payload = {"title": title, "duration_minutes": duration, "action_type": item["recommendation_type"], "source_reference_id": str(recommendation_id)}
            command = UnifiedCommand(
                command_id=command_id, command_type="CREATE_UNIFIED_ACTION", target_module=target,
                payload=allowed_payload, payload_schema=f"spiritual-planet://commands/{target}/create-action/1.0",
                user_confirmation_reference_id=confirmation_id, purpose=item["purpose"],
                idempotency_key=f"recommendation:{recommendation_id}:{action.lower()}",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=15), source_recommendation_id=recommendation_id,
            )
            errors = validate_command(command, confirmation_active=True, consent_active=True)
            status = "REJECTED" if errors else "EXECUTED" if target == LOCAL_ACTION_MODULE else "DEGRADED"
            reasons = errors or ([] if status == "EXECUTED" else ["TARGET_ADAPTER_UNAVAILABLE"])
            cur.execute(
                "INSERT INTO spiritual_planet_unified_commands(id,tenant_id,email,source_recommendation_id,command_type,target_module,payload,payload_schema,user_confirmation_reference_id,purpose,idempotency_key,status,expires_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(tenant_id,email,idempotency_key) DO UPDATE SET updated_at=NOW() RETURNING id",
                (str(command_id), tenant, email, str(recommendation_id), command.command_type, target, Json(command.payload), command.payload_schema, str(confirmation_id), command.purpose, command.idempotency_key, status, command.expires_at),
            )
            command_id = cur.fetchone()[0]
            target_record_id = None
            if status == "EXECUTED":
                action_id = uuid.uuid4()
                cur.execute(
                    "INSERT INTO spiritual_planet_unified_actions(id,tenant_id,email,source_module,source_record_id,source_recommendation_id,title,action_type,status,estimated_duration_minutes,focus_action) "
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'CONFIRMED',%s,NOT EXISTS(SELECT 1 FROM spiritual_planet_unified_actions WHERE email=%s AND focus_action AND status IN('CONFIRMED','SCHEDULED','IN_PROGRESS') AND deleted_at IS NULL)) RETURNING id",
                    (str(action_id), tenant, email, LOCAL_ACTION_MODULE, str(command_id), str(recommendation_id), title, item["recommendation_type"], duration, email),
                )
                target_record_id = str(cur.fetchone()[0])
                cur.execute("INSERT INTO spiritual_planet_search_references(tenant_id,email,source_module,source_record_type,source_record_id,confirmed_title,confirmed_summary,sensitivity,display_route,occurred_at) VALUES(%s,%s,%s,%s,%s,%s,%s,'SENSITIVE','/spiritual-planet/actions',NOW()) ON CONFLICT DO NOTHING", (tenant, email, LOCAL_ACTION_MODULE, "unified_action", target_record_id, title, "用户确认的统一行动"))
            cur.execute("INSERT INTO spiritual_planet_command_results(tenant_id,email,command_id,target_module,target_record_id,result_status,reason_codes) VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(command_id) DO NOTHING", (tenant, email, str(command_id), target, target_record_id, status, Json(reasons)))
            _publish(cur, email=email, event_type="spiritual_planet.command_executed" if status == "EXECUTED" else "spiritual_planet.command_failed", payload={"command_id": str(command_id), "target_module": target, "target_record_id": target_record_id, "status": status, "result_code": reasons[0] if reasons else "EXECUTED"})
        conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "recommendation_id": str(recommendation_id), "decision": action, "command": {"id": str(command_id), "status": status, "target_module": target, "target_record_id": target_record_id, "reason_codes": reasons}}


@router.post("/recommendations/{recommendation_id}/accept")
def accept_recommendation(recommendation_id: uuid.UUID, request: Request, body: CandidateDecisionBody = CandidateDecisionBody()) -> dict:
    return _decision(recommendation_id, body, request, "ACCEPTED")


@router.post("/recommendations/{recommendation_id}/modify")
def modify_recommendation(recommendation_id: uuid.UUID, body: CandidateDecisionBody, request: Request) -> dict:
    return _decision(recommendation_id, body, request, "MODIFIED")


@router.post("/recommendations/{recommendation_id}/smaller")
def smaller_recommendation(recommendation_id: uuid.UUID, request: Request) -> dict:
    return _decision(recommendation_id, CandidateDecisionBody(), request, "SMALLER_REQUESTED")


@router.post("/recommendations/{recommendation_id}/alternative")
def alternative_recommendation(recommendation_id: uuid.UUID, request: Request) -> dict:
    return _decision(recommendation_id, CandidateDecisionBody(), request, "ALTERNATIVE_REQUESTED")


@router.post("/recommendations/{recommendation_id}/skip")
def skip_recommendation(recommendation_id: uuid.UUID, request: Request) -> dict:
    return _decision(recommendation_id, CandidateDecisionBody(), request, "SKIPPED")


@router.post("/recommendations/{recommendation_id}/reject")
def reject_recommendation(recommendation_id: uuid.UUID, request: Request) -> dict:
    return _decision(recommendation_id, CandidateDecisionBody(), request, "REJECTED")


def _action_dict(row) -> dict:
    return {"id": str(row[0]), "source_module": row[1], "source_record_id": row[2], "title": row[3], "action_type": row[4], "status": row[5], "estimated_duration_minutes": row[6], "scheduled_at": _iso(row[7]), "one_time": row[8], "recurrence_summary": row[9], "sensitivity": row[10], "user_visible_context": row[11], "focus_action": row[12], "created_at": _iso(row[13]), "updated_at": _iso(row[14])}


ACTION_SELECT = "SELECT id,source_module,source_record_id,title,action_type,status,estimated_duration_minutes,scheduled_at,one_time,recurrence_summary,sensitivity,user_visible_context,focus_action,created_at,updated_at FROM spiritual_planet_unified_actions"


@router.get("/actions")
def list_actions(request: Request, status: str | None = None, limit: int = Query(default=50, ge=1, le=200)) -> dict:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            params: list[Any] = [user["email"]]
            where = " WHERE email=%s AND deleted_at IS NULL"
            if status:
                where += " AND status=%s"
                params.append(status.upper())
            params.append(limit)
            cur.execute(ACTION_SELECT + where + " ORDER BY focus_action DESC,created_at DESC LIMIT %s", tuple(params))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "actions": [_action_dict(row) for row in rows], "active_limit": 3, "focus_limit": 1, "note": "状态不带道德意义，也不形成属灵分数。"}


@router.get("/actions/current")
def current_actions(request: Request) -> dict:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            cur.execute(ACTION_SELECT + " WHERE email=%s AND deleted_at IS NULL AND status IN('CONFIRMED','SCHEDULED','IN_PROGRESS') ORDER BY focus_action DESC,created_at DESC LIMIT 3", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "actions": [_action_dict(row) for row in rows], "focus_action": _action_dict(rows[0]) if rows else None}


@router.get("/actions/{action_id}")
def get_action(action_id: uuid.UUID, request: Request) -> dict:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            cur.execute(ACTION_SELECT + " WHERE id=%s AND email=%s AND deleted_at IS NULL", (str(action_id), user["email"]))
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not row:
        raise HTTPException(status_code=404, detail="action not found")
    return {"ok": True, "action": _action_dict(row)}


def _transition_action(action_id: uuid.UUID, request: Request, status: str) -> dict:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            cur.execute("SELECT source_module FROM spiritual_planet_unified_actions WHERE id=%s AND email=%s AND deleted_at IS NULL FOR UPDATE", (str(action_id), user["email"]))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="action not found")
            if row[0] != LOCAL_ACTION_MODULE:
                raise HTTPException(status_code=409, detail={"code": "SOURCE_MODULE_OWNS_STATUS", "source_module": row[0]})
            cur.execute("UPDATE spiritual_planet_unified_actions SET status=%s,focus_action=CASE WHEN %s IN('COMPLETED','SKIPPED','CANCELLED','STOPPED') THEN FALSE ELSE focus_action END,updated_at=NOW() WHERE id=%s AND email=%s", (status, status, str(action_id), user["email"]))
        conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "action_id": str(action_id), "status": status, "note": "该状态不表达道德评价。"}


@router.post("/actions/{action_id}/start")
def start_action(action_id: uuid.UUID, request: Request) -> dict:
    return _transition_action(action_id, request, "IN_PROGRESS")


@router.post("/actions/{action_id}/complete")
def complete_action(action_id: uuid.UUID, request: Request) -> dict:
    return _transition_action(action_id, request, "COMPLETED")


@router.post("/actions/{action_id}/skip")
def skip_action(action_id: uuid.UUID, request: Request) -> dict:
    return _transition_action(action_id, request, "SKIPPED")


@router.post("/actions/{action_id}/cancel")
def cancel_action(action_id: uuid.UUID, request: Request) -> dict:
    return _transition_action(action_id, request, "CANCELLED")


@router.get("/home")
def unified_home(request: Request) -> dict:
    _require_feature("home")
    user = _user(request)
    body = ContextRequest(requester_module=LOCAL_ACTION_MODULE, purpose="GENERATE_UNIFIED_HOME", requested_projection="unified_home_context_v1")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            _, response = _resolve_context(cur, email=user["email"], body=body, interactive_user_request=True)
        conn.commit()
    finally:
        _state["release_db"](conn)
    context = response.confirmed_context
    enough = bool(context.get("today_report") or context.get("active_action_references") or context.get("confirmed_theme"))
    return {"ok": True, "home": {
        "data_status": "AVAILABLE" if enough else "INSUFFICIENT_DATA",
        "message": None if enough else "目前没有足够记录形成完整镜像。你可以进行一次简短签到，或直接进入需要的模块。",
        "current_state": {"today_report": context.get("today_report"), "capacity_mode": context.get("capacity_mode", "NORMAL"), "safety_summary": context.get("safety_summary", {"level": "NONE", "details_included": False}), "confirmed_theme": context.get("confirmed_theme")},
        "mirror": {"summary": "以下是已确认记录的简短镜像，不是属灵裁决。" if enough else None, "question": "此刻什么最值得你温柔地留意？" if enough else None},
        "actions": context.get("active_action_references", [])[:3],
        "focus_action": (context.get("active_action_references") or [None])[0],
        "grace_and_protection": (context.get("grace_factors") or [None])[0],
        "crisis_entry": {"route": "/sos", "always_available": True},
    }}


@router.get("/timeline")
def unified_timeline(request: Request, module: str | None = None, limit: int = Query(default=50, ge=1, le=100)) -> dict:
    user = _user(request)
    body = ContextRequest(requester_module=LOCAL_ACTION_MODULE, purpose="GENERATE_UNIFIED_TIMELINE", requested_projection="unified_timeline_context_v1")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            _, response = _resolve_context(cur, email=user["email"], body=body, interactive_user_request=True)
        conn.commit()
    finally:
        _state["release_db"](conn)
    items = response.confirmed_context.get("timeline_references", [])
    if module:
        items = [item for item in items if item.get("source_module") == module]
    return {"ok": True, "timeline": items[:limit], "raw_content_included": False, "limitations": response.limitations}


@router.get("/search")
def unified_search(request: Request, q: str = Query(min_length=1, max_length=120), modules: str | None = None, limit: int = Query(default=20, ge=1, le=50)) -> dict:
    _require_feature("search")
    user = _user(request)
    selected = {item.strip() for item in (modules or "").split(",") if item.strip()}
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            params: list[Any] = [user["email"], f"%{q}%", f"%{q}%"]
            sql = "SELECT source_module,source_record_type,source_record_id,confirmed_title,confirmed_summary,occurred_at,sensitivity,display_route FROM spiritual_planet_search_references WHERE email=%s AND deleted_at IS NULL AND excluded=FALSE AND (confirmed_title ILIKE %s OR COALESCE(confirmed_summary,'') ILIKE %s)"
            if selected:
                sql += " AND source_module IN %s"
                params.append(tuple(selected))
            sql += " ORDER BY occurred_at DESC NULLS LAST LIMIT %s"
            params.append(limit)
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    # The query itself is deliberately absent from logs and audit metadata.
    return {"ok": True, "results": [{"source_module": r[0], "source_record_type": r[1], "source_record_id": r[2], "title": r[3], "snippet": r[4], "occurred_at": _iso(r[5]), "sensitivity": r[6], "access_reason": "CURRENT_USER_CONFIRMED_REFERENCE", "display_route": r[7]} for r in rows], "scope": "CURRENT_USER_ONLY", "query_logged": False}


def _deletion_progress(cur, deletion_id: uuid.UUID | str, email: str) -> tuple[str, list[dict]]:
    cur.execute("SELECT module,status,deleted_reference_count,reason_code,updated_at FROM spiritual_planet_deletion_acknowledgements WHERE deletion_id=%s AND email=%s ORDER BY module", (str(deletion_id), email))
    rows = cur.fetchall()
    acks = [{"module": r[0], "status": r[1], "deleted_reference_count": r[2], "reason_code": r[3], "updated_at": _iso(r[4])} for r in rows]
    if rows and all(row[1] == "COMPLETED" for row in rows):
        status = "COMPLETED"
    elif any(row[1] in {"FAILED_MANUAL_REVIEW"} for row in rows):
        status = "FAILED_MANUAL_REVIEW"
    else:
        status = "PARTIALLY_COMPLETED"
    cur.execute("UPDATE spiritual_planet_deletion_manifests SET status=%s,completed_at=CASE WHEN %s='COMPLETED' THEN NOW() ELSE NULL END,updated_at=NOW() WHERE id=%s AND email=%s", (status, status, str(deletion_id), email))
    return status, acks


def _apply_deletion(cur, *, deletion_id: uuid.UUID, email: str, source_module: str, record_ids: list[str]) -> tuple[str, list[dict]]:
    targets = [source_module, "platform_context", "unified_search", "notification", "jobs", "embeddings", "graph", "cache"]
    for target in dict.fromkeys(targets):
        status, count, reason = "COMPLETED", 0, None
        if target == "unified_search":
            cur.execute("UPDATE spiritual_planet_search_references SET deleted_at=NOW(),updated_at=NOW() WHERE email=%s AND source_module=%s AND source_record_id IN %s AND deleted_at IS NULL", (email, source_module, tuple(record_ids)))
            count = cur.rowcount
        elif target == "notification":
            cur.execute("UPDATE spiritual_planet_notification_candidates SET status='CANCELLED' WHERE email=%s AND source_module=%s AND status='PENDING'", (email, source_module))
            count = cur.rowcount
        elif target == "jobs":
            cur.execute("UPDATE spiritual_planet_orchestration_runs SET status='CANCELLED',completed_at=NOW() WHERE email=%s AND trigger_reference_id IN %s AND status IN('QUEUED','RUNNING')", (email, tuple(record_ids)))
            count = cur.rowcount
        elif target == "platform_context":
            count = 0  # Contexts are not persisted; TTL and consent checks invalidate reads.
        elif target == "cache":
            count = 0  # No platform user-content cache exists.
        elif target == source_module and source_module == LOCAL_ACTION_MODULE:
            cur.execute("UPDATE spiritual_planet_unified_actions SET deleted_at=NOW(),focus_action=FALSE,updated_at=NOW() WHERE email=%s AND id::text IN %s AND deleted_at IS NULL", (email, tuple(record_ids)))
            count = cur.rowcount
        elif target in {"embeddings", "graph"}:
            flag = os.getenv(f"SPIRITUAL_PLANET_{target.upper()}_DELETION_ADAPTER_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
            if not flag:
                status, reason = "NOT_AVAILABLE", "DELETION_ADAPTER_NOT_REGISTERED"
        else:
            status, reason = "NOT_AVAILABLE", "SOURCE_MODULE_DELETION_ADAPTER_NOT_REGISTERED"
        cur.execute("INSERT INTO spiritual_planet_deletion_acknowledgements(tenant_id,email,deletion_id,module,status,deleted_reference_count,reason_code,acknowledged_at) VALUES(%s,%s,%s,%s,%s,%s,%s,CASE WHEN %s='COMPLETED' THEN NOW() ELSE NULL END) ON CONFLICT(deletion_id,module) DO UPDATE SET status=EXCLUDED.status,deleted_reference_count=EXCLUDED.deleted_reference_count,reason_code=EXCLUDED.reason_code,acknowledged_at=EXCLUDED.acknowledged_at,updated_at=NOW()", (_identity(email)[0], email, str(deletion_id), target, status, count, reason, status))
    return _deletion_progress(cur, deletion_id, email)


@router.post("/deletions")
def create_deletion(body: DeletionRequest, request: Request) -> dict:
    _require_feature("deletion")
    user = _user(request)
    tenant, email = _identity(user["email"])
    deletion_id = uuid.uuid4()
    required = list(dict.fromkeys([body.source_module, "platform_context", "unified_search", "notification", "jobs", "embeddings", "graph", "cache"]))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, email)
            cur.execute("INSERT INTO spiritual_planet_deletion_manifests(id,tenant_id,email,source_module,source_record_type,source_record_ids,deletion_scope,status,required_modules) VALUES(%s,%s,%s,%s,%s,%s,%s,'PROPAGATING',%s)", (str(deletion_id), tenant, email, body.source_module, body.source_record_type, Json(body.source_record_ids), body.deletion_scope, Json(required)))
            _publish(cur, email=email, event_type="spiritual_planet.deletion_manifest_created", payload={"deletion_id": str(deletion_id), "status": "PROPAGATING"})
            status, acks = _apply_deletion(cur, deletion_id=deletion_id, email=email, source_module=body.source_module, record_ids=body.source_record_ids)
            _publish(cur, email=email, event_type="spiritual_planet.deletion_propagation_completed" if status == "COMPLETED" else "spiritual_planet.deletion_propagation_failed", payload={"deletion_id": str(deletion_id), "status": status, "result_code": "ALL_ACKNOWLEDGED" if status == "COMPLETED" else "ACKNOWLEDGEMENTS_PENDING"})
        conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "deletion_id": str(deletion_id), "status": status, "acknowledgements": acks}


@router.get("/deletions/{deletion_id}")
def get_deletion(deletion_id: uuid.UUID, request: Request) -> dict:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            cur.execute("SELECT source_module,source_record_type,source_record_ids,deletion_scope,status,required_modules,requested_at,completed_at FROM spiritual_planet_deletion_manifests WHERE id=%s AND email=%s", (str(deletion_id), user["email"]))
            row = cur.fetchone()
            if row:
                _, acks = _deletion_progress(cur, deletion_id, user["email"])
        conn.commit()
    finally:
        _state["release_db"](conn)
    if not row:
        raise HTTPException(status_code=404, detail="deletion not found")
    return {"ok": True, "deletion": {"id": str(deletion_id), "source_module": row[0], "source_record_type": row[1], "source_record_ids": _json(row[2], []), "deletion_scope": row[3], "status": row[4], "required_modules": _json(row[5], []), "requested_at": _iso(row[6]), "completed_at": _iso(row[7]), "acknowledgements": acks}}


@router.post("/deletions/{deletion_id}/retry")
def retry_deletion(deletion_id: uuid.UUID, request: Request) -> dict:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            cur.execute("SELECT source_module,source_record_ids FROM spiritual_planet_deletion_manifests WHERE id=%s AND email=%s FOR UPDATE", (str(deletion_id), user["email"]))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="deletion not found")
            status, acks = _apply_deletion(cur, deletion_id=deletion_id, email=user["email"], source_module=row[0], record_ids=_json(row[1], []))
        conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "deletion_id": str(deletion_id), "status": status, "acknowledgements": acks}


@router.post("/rebuilds")
def create_rebuild(body: RebuildRequest, request: Request) -> dict:
    user = _user(request)
    tenant, email = _identity(user["email"])
    rebuild_id = uuid.uuid4()
    immediate = body.scope == "UNIFIED_CONTEXT"
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, email)
            cur.execute("SELECT COUNT(*) FILTER(WHERE review_action IN('CONFIRM','PARTIALLY_CONFIRM')),COUNT(*) FILTER(WHERE review_action IN('REJECT','DISMISS')),COUNT(*) FILTER(WHERE review_action IN('RELABEL','CHANGE_SCOPE')) FROM formation_twin_formation_reviews WHERE email=%s AND revoked_at IS NULL", (email,))
            preserved = cur.fetchone() or (0, 0, 0)
            cur.execute("INSERT INTO spiritual_planet_rebuild_jobs(id,tenant_id,email,scope,source_module,source_record_ids,reason_code,status,preserved_confirmations,preserved_rejections,preserved_corrections,engine_versions,started_at,completed_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (str(rebuild_id), tenant, email, body.scope, body.source_module, Json(body.source_record_ids), body.reason, "COMPLETED" if immediate else "QUEUED", preserved[0], preserved[1], preserved[2], Json({"platform_contract": "1.0", "formation_engine": "batch-04"}), datetime.now(timezone.utc) if immediate else None, datetime.now(timezone.utc) if immediate else None))
            _publish(cur, email=email, event_type="spiritual_planet.rebuild_completed" if immediate else "spiritual_planet.rebuild_started", payload={"rebuild_id": str(rebuild_id), "status": "COMPLETED" if immediate else "QUEUED", "schema_version": "1.0"})
        conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "rebuild_id": str(rebuild_id), "status": "COMPLETED" if immediate else "QUEUED", "preserved": {"confirmations": preserved[0], "rejections": preserved[1], "corrections": preserved[2]}, "note": None if immediate else "等待对应 Source Module 的已注册重建 worker；平台不会伪报完成。"}


@router.get("/rebuilds/{rebuild_id}")
def get_rebuild(rebuild_id: uuid.UUID, request: Request) -> dict:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            cur.execute("SELECT scope,source_module,source_record_ids,reason_code,status,preserved_confirmations,preserved_rejections,preserved_corrections,new_derived_references,invalidated_derived_references,engine_versions,created_at,completed_at FROM spiritual_planet_rebuild_jobs WHERE id=%s AND email=%s", (str(rebuild_id), user["email"]))
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not row:
        raise HTTPException(status_code=404, detail="rebuild not found")
    return {"ok": True, "rebuild": {"id": str(rebuild_id), "scope": row[0], "source_module": row[1], "source_record_ids": _json(row[2], []), "reason_code": row[3], "status": row[4], "preserved_confirmations": row[5], "preserved_rejections": row[6], "preserved_corrections": row[7], "new_derived_references": _json(row[8], []), "invalidated_derived_references": _json(row[9], []), "engine_versions": _json(row[10], {}), "created_at": _iso(row[11]), "completed_at": _iso(row[12])}}


@router.post("/rebuilds/{rebuild_id}/cancel")
def cancel_rebuild(rebuild_id: uuid.UUID, request: Request) -> dict:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _owner(cur, user["email"])
            cur.execute("UPDATE spiritual_planet_rebuild_jobs SET status='CANCELLED',completed_at=NOW(),updated_at=NOW() WHERE id=%s AND email=%s AND status='QUEUED'", (str(rebuild_id), user["email"]))
            changed = cur.rowcount
        conn.commit()
    finally:
        _state["release_db"](conn)
    if not changed:
        raise HTTPException(status_code=409, detail="rebuild is not cancellable")
    return {"ok": True, "rebuild_id": str(rebuild_id), "status": "CANCELLED"}


def _module_health(module: str) -> dict:
    adapter_available = module in {"formation_twin", "platform_orchestrator"}
    registered = module in SOURCE_OF_TRUTH or module == "platform_orchestrator"
    if not registered:
        status, reasons = "NOT_REGISTERED", ["CAPABILITY_NOT_REGISTERED"]
    elif not adapter_available:
        status, reasons = "DEGRADED", ["CONTEXT_OR_COMMAND_ADAPTER_NOT_REGISTERED"]
    else:
        status, reasons = "HEALTHY", []
    return {"module": module, "status": status, "reason_codes": reasons, "contract_version": "1.0" if registered else None, "user_content_included": False}


@router.get("/integrations/health/all")
def all_integration_health(request: Request) -> dict:
    _require_feature("health")
    _admin(request)
    modules = list(SOURCE_OF_TRUTH) + [LOCAL_ACTION_MODULE]
    return {"ok": True, "integrations": [_module_health(module) for module in modules], "technical_metadata_only": True}


@router.get("/integrations/health")
def integration_health(request: Request) -> dict:
    return all_integration_health(request)


@router.get("/integrations/health/{module}")
def module_integration_health(module: str, request: Request) -> dict:
    _require_feature("health")
    _admin(request)
    return {"ok": True, "integration": _module_health(module), "technical_metadata_only": True}


@router.get("/agents")
def list_agents(request: Request) -> dict:
    _require_feature("agents")
    _user(request)
    return {"ok": True, "agents": [item.model_dump(mode="json") for item in AGENT_CAPABILITIES]}


@router.get("/agents/{agent_id}")
def get_agent(agent_id: str, request: Request) -> dict:
    _require_feature("agents")
    _user(request)
    item = next((value for value in AGENT_CAPABILITIES if value.agent_id == agent_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="agent capability not registered")
    return {"ok": True, "agent": item.model_dump(mode="json")}
