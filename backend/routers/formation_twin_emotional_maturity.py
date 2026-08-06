"""EMD-OS Batch 1 API — emotional maturity diagnostic governance (EM-01 ~ EM-10)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from psycopg2.extras import Json, RealDictCursor

from formation_twin.emotional_maturity_erasure import (
    EMD_PERSONAL_TABLES, build_erasure_receipt, describe_deletion_plan,
)
from formation_twin.emotional_maturity_pilot_gate import (
    PilotGateError, available_consent_scopes, enforce_scope_request, feature_matrix, guard_feature,
)
from formation_twin.emotional_maturity_incident_drill import DrillRefused, run_drill
from formation_twin.emotional_maturity_presentation import (
    build_stage_display,
    display_contract,
    validate_ui_payload,
)
from formation_twin.emotional_maturity_privacy_assessment import build_privacy_assessment
from formation_twin.emotional_maturity_psychometrics import (
    agreement_report, analyse_interviews, build_interview_protocol, triage_disagreements,
)
from formation_twin.emotional_maturity_training_optout import (
    AUDIT_QUESTIONS, TrainingOptOutError, assert_no_training_material,
    audit_provider_config, describe_training_optout,
)
from formation_twin.emotional_maturity import (
    CONSENT_SCOPES,
    DIMENSION_CODES,
    ENGINE_VERSION,
    MODEL_VERSION,
    PUBLISHED_EVENTS,
    RULE_VERSION,
    ConsentRequest,
    DimensionSnapshot,
    EvidenceItem,
    UnsafeContentError,
    apply_correction,
    audit_response_validity,
    build_intake,
    describe_module,
    emd_data_quality,
    normalize_evidence,
    plan_growth_route,
    run_consent_gate,
    run_safety_triage,
    sanitize_event,
    schedule_reassessment,
    score_dimension,
    select_next_items,
    synthesize_profile,
    withdraw_consent,
)

from formation_twin.emotional_maturity_analytics import (
    MetricDefinition,
    analyze_generalization,
    analyze_trajectory,
    calibrate_attribution,
    compose_reassessment,
    describe_analytics_engine,
    publish_growth_report,
    reconcile_comparability,
    register_metric,
)

from formation_twin.emotional_maturity_integration import (
    withdraw_twin_evidence,
    TwinEvidence,
    bridge_to_twin,
    build_pastoral_summary,
    compile_rule_of_life,
    coordinate_handoff,
    describe_integration_engine,
    design_group_practice,
    map_identity_alignment,
    orchestrate_plan,
    reconcile_community_feedback,
    route_prayer,
)

from formation_twin.emotional_maturity_grief import (
    accompany_grief,
    build_rest_rhythm,
    calibrate_control,
    describe_grief_engine,
    design_ritual,
    discern_spiritual_bypassing,
    evaluate_integration,
    map_loss,
    process_ambiguous_loss,
)

from formation_twin.emotional_maturity_conflict import (
    build_apology,
    calibrate_motive_uncertainty,
    describe_conflict_engine,
    differentiate_forgiveness,
    facilitate_dialogue,
    frame_conflict_issue,
    map_boundary,
    plan_boundary_enforcement,
    plan_restitution,
    route_repair_outcome,
    train_perspective_taking,
)

from formation_twin.emotional_maturity_family import (
    GenogramMember,
    GenogramRelationship,
    analyze_family_scripts,
    assess_differentiation,
    build_genogram,
    build_true_self_compass,
    describe_family_engine,
    design_vulnerability_experiment,
    profile_attachment_cycle,
    profile_masks,
    reframe_survival_oath,
)

from formation_twin.emotional_maturity_regulation import (
    LabelingInput,
    SupportPerson,
    activation_band,
    build_pause_protocol,
    build_rehearsal,
    build_trigger_profile,
    confirm_emotions,
    describe_regulation_engine,
    interrupt_impulse,
    label_emotions,
    plan_recovery,
    route_coregulation,
    scan_body_signals,
)

from formation_twin.emotional_maturity_events import (
    EmotionalEventInput,
    RecoveryInput,
    analyze_recurrence,
    build_timeline,
    capture_event,
    event_to_batch1_evidence,
    compute_recovery_metrics,
    describe_event_engine,
    detect_transfer,
    evaluate_growth,
    handle_checkpoint_without_events,
    schedule_checkpoints,
    verify_repair,
)

from formation_twin.emotional_maturity_items import (
    BANK_VERSION,
    RUBRIC_BUNDLE_VERSION,
    AssessmentResponse,
    SelectionState,
    build_pressure_scenario,
    calibrate_consistency,
    describe_item_engine,
    evaluate_sufficiency,
    extract_evidence,
    generate_counterfactual_probe,
    register_item_bank,
    render_item,
    score_rubric,
    seed_item_bank,
    select_next_item,
    to_batch1_evidence,
)


router = APIRouter(prefix="/api/v1/formation-twin", tags=["formation-twin-emotional-maturity"])
_ITEM_BANK = {item.item_id: item for item in seed_item_bank()}
_ITEM_SOURCE_TYPE = {
    "SR": "self_report",
    "RV": "self_report",
    "BE": "recent_behavior",
    "SF": "scenario_intention",
    "CF": "counterfactual",
}
_state: dict[str, Any] = {}


def init_formation_twin_emotional_maturity_router(
    *, get_db, release_db, get_session_user, to_shanghai_iso
) -> None:
    _state.update(locals())


# ── helpers ──────────────────────────────────────────────────────────────────

def _user(request: Request) -> dict[str, Any]:
    getter = _state.get("get_session_user")
    user = getter(request) if getter else None
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
    """Make engine payloads JSON-safe (datetimes, UUIDs, pydantic models)."""
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


def _publish(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    if event_type not in PUBLISHED_EVENTS:
        raise ValueError("unregistered EMD-OS event")
    return sanitize_event(event_type, payload)


def _granted_scopes(cur, email: str) -> list[str]:
    cur.execute(
        "SELECT consent_scope FROM formation_twin_emd_consents "
        "WHERE email=%s AND status='GRANTED' ORDER BY consent_scope",
        (email,),
    )
    return [row["consent_scope"] for row in cur.fetchall()]


def _require_scope(cur, email: str, scope: str) -> list[str]:
    scopes = _granted_scopes(cur, email)
    if scope not in scopes:
        raise HTTPException(status_code=403, detail=f"consent required: {scope}")
    return scopes


def _load_session(cur, email: str, session_id: str) -> dict[str, Any]:
    cur.execute(
        "SELECT * FROM formation_twin_emd_sessions WHERE id=%s AND email=%s AND deleted_at IS NULL",
        (session_id, email),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="assessment session not found")
    return dict(row)


def _set_state(cur, session_id: str, state: str, email: str | None = None, **columns: Any) -> None:
    """Update a session's state.

    Every caller reaches here after `_load_session(cur, email, session_id)`, which already
    404s on someone else's session — so the ownership check is not new. Carrying the email
    into the predicate anyway means a future caller that forgets that ordering updates zero
    rows instead of another tenant's session. Cross-tenant writes are a zero-tolerance item;
    they should not depend on every future caller remembering the convention.
    """
    assignments = ["state=%s", "updated_at=now()"]
    values: list[Any] = [state]
    for key, value in columns.items():
        assignments.append(f"{key}=%s")
        values.append(value)
    values.append(session_id)
    predicate = "id=%s"
    if email is not None:
        predicate += " AND email=%s"
        values.append(email)
    cur.execute(f"UPDATE formation_twin_emd_sessions SET {','.join(assignments)} WHERE {predicate}", values)


def _load_evidence(cur, email: str) -> list[EvidenceItem]:
    cur.execute(
        "SELECT * FROM formation_twin_emd_evidence_items "
        "WHERE email=%s AND deleted_at IS NULL ORDER BY occurred_at",
        (email,),
    )
    items: list[EvidenceItem] = []
    for row in cur.fetchall():
        record = dict(row)
        items.append(EvidenceItem(
            evidence_id=record["evidence_id"],
            dimension_code=record["dimension_code"],
            evidence_kind=record["evidence_kind"],
            context=record["context"],
            stage_signal=record["stage_signal"],
            occurred_at=record["occurred_at"],
            recorded_at=record["recorded_at"],
            statement_type=record["statement_type"],
            user_confirmed=record["user_confirmed"],
            self_rated=record["self_rated"],
            independence_group=record["independence_group"],
            behavior_summary=record["behavior_summary"] or "",
            references=record["references_json"] or [],
            excluded=record["excluded"],
            exclusion_reason=record["exclusion_reason"],
        ))
    return items


# ── request models ───────────────────────────────────────────────────────────

class ConsentPayload(BaseModel):
    requested_scopes: list[str] = Field(min_length=1, max_length=8)
    granted_scopes: list[str] = Field(default_factory=list, max_length=8)
    user_acknowledged_limits: bool = False
    is_minor: bool = False
    locale: str = "zh-CN"


class WithdrawPayload(BaseModel):
    consent_scope: str


class TriagePayload(BaseModel):
    session_id: str
    free_text: str = Field(default="", max_length=4000)
    self_reported_flags: list[str] = Field(default_factory=list, max_length=10)


class IntakePayload(BaseModel):
    session_id: str
    submitted: dict[str, Any] = Field(default_factory=dict)


class EvidencePayload(BaseModel):
    session_id: str
    items: list[dict[str, Any]] = Field(default_factory=list, max_length=60)


class NextItemsPayload(BaseModel):
    session_id: str
    focus_dimensions: list[str] = Field(default_factory=list, max_length=10)
    fatigue_reported: bool = False


class ScorePayload(BaseModel):
    session_id: str
    responses: list[dict[str, Any]] = Field(default_factory=list, max_length=60)


class RoutePayload(BaseModel):
    emd_profile_id: str
    max_dimensions: int = Field(default=2, ge=1, le=3)


class CorrectionPayload(BaseModel):
    snapshot_id: str
    correction_type: str
    evidence_id: str | None = None
    context: str | None = None
    user_note: str = Field(default="", max_length=500)


class ReassessmentPayload(BaseModel):
    emd_profile_id: str


# ── EM-00 module description ─────────────────────────────────────────────────

@router.get("/emotional-maturity/overview")
def emotional_maturity_overview(request: Request) -> dict[str, Any]:
    _user(request)
    return {"ok": True, **describe_module()}


# ── EM-01 consent gate ───────────────────────────────────────────────────────

@router.post("/emotional-maturity/consent")
def emotional_maturity_consent(request: Request, payload: ConsentPayload) -> dict[str, Any]:
    user = _user(request)
    values = payload.model_dump()
    # 试点档不提供分享 / 小组同意项：即使客户端直接构造请求也拿不到。
    gate = enforce_scope_request(list(values.get("requested_scopes") or []))
    values["requested_scopes"] = gate["granted_scopes"]
    values["granted_scopes"] = [
        scope for scope in (values.get("granted_scopes") or []) if scope in gate["granted_scopes"]
    ]
    try:
        consent_request = ConsentRequest(**values)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    decision = run_consent_gate(consent_request)
    decision["blocked_by_profile"] = gate["blocked_by_profile"]
    decision["assurance_profile"] = gate["profile"]
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            for scope in decision["granted_scopes"]:
                cur.execute(
                    "INSERT INTO formation_twin_emd_consents"
                    "(id,tenant_id,profile_id,email,consent_scope,policy_version,status,limits_acknowledged)"
                    "VALUES(%s,%s,%s,%s,%s,%s,'GRANTED',%s) "
                    "ON CONFLICT(email,consent_scope,policy_version) DO UPDATE "
                    "SET status='GRANTED',withdrawn_at=NULL,limits_acknowledged=EXCLUDED.limits_acknowledged,updated_at=now()",
                    (str(uuid.uuid4()), tenant_id, profile_id, user["email"], scope,
                     decision["policy_version"], consent_request.user_acknowledged_limits),
                )
            session_id = None
            if decision["decision"] == "GRANTED":
                session_id = str(uuid.uuid4())
                cur.execute(
                    "INSERT INTO formation_twin_emd_sessions"
                    "(id,tenant_id,profile_id,email,state,granted_scopes_json,engine_version,rule_version)"
                    "VALUES(%s,%s,%s,%s,'CONSENT_GRANTED',%s,%s,%s)",
                    (session_id, tenant_id, profile_id, user["email"],
                     Json(decision["granted_scopes"]), ENGINE_VERSION, RULE_VERSION),
                )
            conn.commit()
        return {
            "ok": True,
            "session_id": session_id,
            **decision,
            "event": _publish("emd.consent_updated", {"status": decision["decision"]}),
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/consent/withdraw")
def emotional_maturity_consent_withdraw(request: Request, payload: WithdrawPayload) -> dict[str, Any]:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            scopes = _granted_scopes(cur, user["email"])
            try:
                result = withdraw_consent(scopes, payload.consent_scope)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            cur.execute(
                "UPDATE formation_twin_emd_consents SET status='WITHDRAWN',withdrawn_at=now(),updated_at=now() "
                "WHERE email=%s AND consent_scope=%s",
                (user["email"], payload.consent_scope),
            )
            if payload.consent_scope == "EMD_BEHAVIOR_EVIDENCE":
                cur.execute(
                    "UPDATE formation_twin_emd_evidence_items SET excluded=TRUE,exclusion_reason='CONSENT_WITHDRAWN' "
                    "WHERE email=%s AND evidence_kind IN ('RECENT_BEHAVIOR','REAL_LIFE_EVENT')",
                    (user["email"],),
                )
            withdrawals: list[dict[str, Any]] = []
            if payload.consent_scope == "EMD_LONGITUDINAL_TWIN":
                cur.execute(
                    "UPDATE formation_twin_emd_reassessment_plans SET status='CANCELLED',updated_at=now() "
                    "WHERE email=%s AND status='SCHEDULED'",
                    (user["email"],),
                )
                # 停掉复测还不够：已经写进 Twin 的证据必须撤回并触发重算，
                # 否则用户撤回同意后，旧结论仍在别处继续生效。
                cur.execute(
                    "SELECT bridge_id FROM formation_twin_emd_twin_bridges "
                    "WHERE email=%s AND status<>'WITHDRAWN'",
                    (user["email"],),
                )
                for row in cur.fetchall():
                    withdrawals.append(withdraw_twin_evidence(row["bridge_id"]))
                cur.execute(
                    "UPDATE formation_twin_emd_twin_bridges SET status='WITHDRAWN',updated_at=now() "
                    "WHERE email=%s AND status<>'WITHDRAWN'",
                    (user["email"],),
                )
            conn.commit()
        return {
            "ok": True, **result,
            "twin_withdrawals": withdrawals,
            "twin_evidence_withdrawn": len(withdrawals),
            "event": _publish("emd.consent_updated", {"status": "WITHDRAWN"}),
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


# ── EM-02 safety triage ──────────────────────────────────────────────────────

@router.post("/emotional-maturity/triage")
def emotional_maturity_triage(request: Request, payload: TriagePayload) -> dict[str, Any]:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            session = _load_session(cur, user["email"], payload.session_id)
            result = run_safety_triage(
                free_text=payload.free_text,
                self_reported_flags=payload.self_reported_flags,
                prior_safety_level=str(session.get("safety_level") or "NONE"),
            )
            _set_state(
                cur, payload.session_id,
                "ROUTED_TO_CRISIS" if not result["assessment_allowed"] else "SAFETY_TRIAGED",
                email=user["email"],
                safety_level=result["safety_level"],
                relationship_safety=result["relationship_safety"],
                triage_json=Json(_json(result)),
            )
            conn.commit()
        return {
            "ok": True, **result,
            "event": _publish("emd.safety_routed", {"safety_level": result["safety_level"], "status": result["route"]}),
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


# ── EM-03 intake ─────────────────────────────────────────────────────────────

@router.post("/emotional-maturity/intake")
def emotional_maturity_intake(request: Request, payload: IntakePayload) -> dict[str, Any]:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            session = _load_session(cur, user["email"], payload.session_id)
            triage = session.get("triage_json") or {"assessment_allowed": False}
            try:
                result = build_intake(triage=triage, submitted=payload.submitted)
            except UnsafeContentError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            if result["status"] == "READY":
                _set_state(cur, payload.session_id, "INTAKE_BUILT", email=user["email"],
                           intake_json=Json(_json(result)))
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


# ── EM-04 evidence ───────────────────────────────────────────────────────────

@router.post("/emotional-maturity/evidence")
def emotional_maturity_evidence(request: Request, payload: EvidencePayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            _load_session(cur, user["email"], payload.session_id)
            scopes = _require_scope(cur, user["email"], "EMD_SELF_ASSESSMENT")
            result = normalize_evidence(payload.items, consented_scopes=scopes)
            for item in result["accepted"]:
                cur.execute(
                    "INSERT INTO formation_twin_emd_evidence_items"
                    "(id,tenant_id,profile_id,email,session_id,evidence_id,dimension_code,evidence_kind,context,"
                    "stage_signal,statement_type,user_confirmed,self_rated,independence_group,behavior_summary,"
                    "references_json,occurred_at,recorded_at,excluded,exclusion_reason)"
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON CONFLICT(email,evidence_id) DO NOTHING",
                    (str(uuid.uuid4()), tenant_id, profile_id, user["email"], payload.session_id,
                     item["evidence_id"], item["dimension_code"], item["evidence_kind"], item["context"],
                     item["stage_signal"], item["statement_type"], item["user_confirmed"], item["self_rated"],
                     item["independence_group"], item["behavior_summary"], Json(item["references"]),
                     item["occurred_at"], item["recorded_at"], item["excluded"], item["exclusion_reason"]),
                )
            _set_state(cur, payload.session_id, "EVIDENCE_NORMALIZED", email=user["email"])
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


# ── EM-05 next items ─────────────────────────────────────────────────────────

@router.post("/emotional-maturity/next-items")
def emotional_maturity_next_items(request: Request, payload: NextItemsPayload) -> dict[str, Any]:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            session = _load_session(cur, user["email"], payload.session_id)
            evidence = _load_evidence(cur, user["email"])
            triage = session.get("triage_json") or {}
            result = select_next_items(
                evidence=evidence,
                focus_dimensions=payload.focus_dimensions or None,
                answered_count=int(session.get("answered_count") or 0),
                fatigue_reported=payload.fatigue_reported,
                restrictions=list(triage.get("restrictions") or []),
            )
            _set_state(cur, payload.session_id, "ASSESSING", email=user["email"])
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


# ── EM-06 / EM-07 / EM-08 score + audit + profile ────────────────────────────

@router.post("/emotional-maturity/score")
def emotional_maturity_score(request: Request, payload: ScorePayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            session = _load_session(cur, user["email"], payload.session_id)
            evidence = _load_evidence(cur, user["email"])
            validity = audit_response_validity(payload.responses, evidence)
            flags = validity["flag_codes"] if validity["cap_stage_required"] else []
            snapshots = [score_dimension(code, evidence, validity_flags=flags) for code in DIMENSION_CODES]
            triage = session.get("triage_json") or {}
            profile = synthesize_profile(snapshots, triage=triage, validity=validity)

            snapshot_ids: dict[str, str] = {}
            for snapshot in snapshots:
                snapshot_id = str(uuid.uuid4())
                snapshot_ids[snapshot.dimension_code] = snapshot_id
                cur.execute(
                    "INSERT INTO formation_twin_emd_dimension_snapshots"
                    "(id,tenant_id,profile_id,email,session_id,dimension_code,stage,confidence,evidence_count,"
                    "evidence_weight,evidence_kinds_json,contexts_json,context_differences_json,caps_applied_json,"
                    "uncertainty_json,user_review_status,rule_version,model_version,computed_at)"
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (snapshot_id, tenant_id, profile_id, user["email"], payload.session_id,
                     snapshot.dimension_code, snapshot.stage, snapshot.confidence, snapshot.evidence_count,
                     snapshot.evidence_weight, Json(_json(snapshot.evidence_kinds)), Json(_json(snapshot.contexts)),
                     Json(_json(snapshot.context_differences)), Json(_json(snapshot.caps_applied)), Json(_json(snapshot.uncertainty)),
                     snapshot.user_review_status, snapshot.rule_version, snapshot.model_version,
                     snapshot.computed_at),
                )
            emd_profile_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO formation_twin_emd_profiles"
                "(id,tenant_id,profile_id,email,session_id,model_version,engine_version,dimensions_json,"
                "strengths_json,growth_invitations_json,insufficient_dimensions_json,validity_flags_json,"
                "limitations_json,safety_level,relationship_safety,twin_update_allowed,input_hash)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (emd_profile_id, tenant_id, profile_id, user["email"], payload.session_id,
                 MODEL_VERSION, ENGINE_VERSION, Json(_json(profile["dimensions"])), Json(_json(profile["current_strengths"])),
                 Json(_json(profile["growth_invitations"])), Json(_json(profile["insufficient_evidence_dimensions"])),
                 Json(_json(profile["validity_flags"])), Json(_json(profile["limitations"])), profile["safety_level"],
                 profile["relationship_safety"], False, profile["input_hash"]),
            )
            _set_state(
                cur, payload.session_id, "PROFILE_SYNTHESIZED", email=user["email"],
                validity_json=Json(_json(validity)),
                answered_count=int(session.get("answered_count") or 0) + len(payload.responses),
            )
            conn.commit()
        return {
            "ok": True,
            "emd_profile_id": emd_profile_id,
            "snapshot_ids": snapshot_ids,
            "validity": validity,
            "profile": profile,
            "event": _publish("emd.profile_synthesized", {"profile_id": emd_profile_id, "status": "PENDING"}),
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


# ── EM-09 growth route ───────────────────────────────────────────────────────

@router.post("/emotional-maturity/route")
def emotional_maturity_route(request: Request, payload: RoutePayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "SELECT * FROM formation_twin_emd_profiles WHERE id=%s AND email=%s AND deleted_at IS NULL",
                (payload.emd_profile_id, user["email"]),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="profile not found")
            record = dict(row)
            profile = {
                "growth_invitations": record["growth_invitations_json"] or [],
                "safety_level": record["safety_level"],
                "relationship_safety": record["relationship_safety"],
            }
            result = plan_growth_route(profile, max_dimensions=payload.max_dimensions)
            route_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO formation_twin_emd_growth_routes"
                "(id,tenant_id,profile_id,email,emd_profile_id,route_type,schema_version,assignments_json,"
                "checkpoints_json,limitations_json)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (route_id, tenant_id, profile_id, user["email"], payload.emd_profile_id,
                 result.get("route_type", "TRAINING"), result.get("schema_version", ""),
                 Json(_json(result.get("assignments") or [])), Json(_json(result.get("checkpoints") or [])),
                 Json(_json(result.get("limitations") or []))),
            )
            cur.execute(
                "UPDATE formation_twin_emd_sessions SET state='ROUTE_PLANNED',updated_at=now() WHERE id=%s AND email=%s",
                (record["session_id"], user["email"]),
            )
            conn.commit()
        return {
            "ok": True, "route_record_id": route_id, **result,
            "event": _publish("emd.route_planned", {"route_id": route_id, "profile_id": payload.emd_profile_id}),
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/emotional-maturity/route")
def emotional_maturity_latest_route(request: Request) -> dict[str, Any]:
    """Return the latest saved route without creating a new recommendation.

    The page is allowed to read an existing route during load.  Re-running the
    POST planner on every render would create duplicate records and silently
    move the assessment session, so read and create remain separate methods on
    the same resource.
    """
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "SELECT id,emd_profile_id,route_type,schema_version,assignments_json,"
                "checkpoints_json,limitations_json,user_response,created_at "
                "FROM formation_twin_emd_growth_routes "
                "WHERE email=%s AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1",
                (user["email"],),
            )
            row = cur.fetchone()
        if not row:
            return {"ok": True, "route": None}
        record = dict(row)
        return {
            "ok": True,
            "route": {
                "route_record_id": str(record["id"]),
                "emd_profile_id": str(record["emd_profile_id"]),
                "route_type": record["route_type"],
                "schema_version": record["schema_version"],
                "assignments": record["assignments_json"] or [],
                "checkpoints": record["checkpoints_json"] or [],
                "limitations": record["limitations_json"] or [],
                "user_response": record["user_response"],
                "created_at": _state["to_shanghai_iso"](record["created_at"]),
            },
        }
    finally:
        _state["release_db"](conn)


# ── EM-10 correction + reassessment ──────────────────────────────────────────

@router.post("/emotional-maturity/corrections")
def emotional_maturity_correction(request: Request, payload: CorrectionPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "SELECT * FROM formation_twin_emd_dimension_snapshots "
                "WHERE id=%s AND email=%s AND deleted_at IS NULL",
                (payload.snapshot_id, user["email"]),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="snapshot not found")
            record = dict(row)
            snapshot = DimensionSnapshot(
                dimension_code=record["dimension_code"],
                dimension_name=record["dimension_code"],
                stage=record["stage"],
                stage_label="",
                confidence=record["confidence"],
                evidence_count=record["evidence_count"],
                evidence_weight=float(record["evidence_weight"]),
                evidence_kinds=record["evidence_kinds_json"] or [],
                contexts=record["contexts_json"] or [],
                context_differences=record["context_differences_json"] or [],
                caps_applied=record["caps_applied_json"] or [],
                uncertainty=record["uncertainty_json"] or [],
                user_review_status=record["user_review_status"],
                computed_at=record["computed_at"],
            )
            evidence = _load_evidence(cur, user["email"])
            try:
                result = apply_correction(snapshot, evidence, {
                    "correction_type": payload.correction_type,
                    "evidence_id": payload.evidence_id,
                    "context": payload.context,
                    "user_note": payload.user_note,
                })
            except UnsafeContentError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

            updated = result["snapshot"]
            new_snapshot_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO formation_twin_emd_dimension_snapshots"
                "(id,tenant_id,profile_id,email,session_id,dimension_code,stage,confidence,evidence_count,"
                "evidence_weight,evidence_kinds_json,contexts_json,context_differences_json,caps_applied_json,"
                "uncertainty_json,user_review_status,supersedes_snapshot_id,rule_version,model_version,computed_at)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (new_snapshot_id, tenant_id, profile_id, user["email"], record["session_id"],
                 updated["dimension_code"], updated["stage"], updated["confidence"], updated["evidence_count"],
                 updated["evidence_weight"], Json(updated["evidence_kinds"]), Json(updated["contexts"]),
                 Json(updated["context_differences"]), Json(updated["caps_applied"]), Json(updated["uncertainty"]),
                 updated["user_review_status"], payload.snapshot_id, updated["rule_version"],
                 updated["model_version"], updated["computed_at"]),
            )
            if payload.correction_type == "EXCLUDE_EVIDENCE" and payload.evidence_id:
                cur.execute(
                    "UPDATE formation_twin_emd_evidence_items SET excluded=TRUE,exclusion_reason='USER_EXCLUDED' "
                    "WHERE email=%s AND evidence_id=%s",
                    (user["email"], payload.evidence_id),
                )
            if payload.correction_type == "CORRECT_CONTEXT" and payload.evidence_id and payload.context:
                cur.execute(
                    "UPDATE formation_twin_emd_evidence_items SET context=%s WHERE email=%s AND evidence_id=%s",
                    (payload.context, user["email"], payload.evidence_id),
                )
            cur.execute(
                "INSERT INTO formation_twin_emd_corrections"
                "(id,tenant_id,profile_id,email,snapshot_id,dimension_code,correction_type,target_evidence_id,"
                "user_note,resulting_snapshot_id,twin_update_allowed)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], payload.snapshot_id,
                 record["dimension_code"], payload.correction_type, payload.evidence_id,
                 payload.user_note or None, new_snapshot_id, bool(result["twin_update_allowed"])),
            )
            conn.commit()
        return {
            "ok": True, "snapshot_id": new_snapshot_id, **result,
            "event": _publish("emd.profile_corrected", {"dimension_code": record["dimension_code"], "status": updated["user_review_status"]}),
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/reassessment")
def emotional_maturity_reassessment(request: Request, payload: ReassessmentPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "SELECT * FROM formation_twin_emd_profiles WHERE id=%s AND email=%s AND deleted_at IS NULL",
                (payload.emd_profile_id, user["email"]),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="profile not found")
            record = dict(row)
            scopes = _granted_scopes(cur, user["email"])
            result = schedule_reassessment(
                {"growth_invitations": record["growth_invitations_json"] or []},
                consented_scopes=scopes,
            )
            plan_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO formation_twin_emd_reassessment_plans"
                "(id,tenant_id,profile_id,email,emd_profile_id,status,dimensions_json,checkpoints_json,rubric_version)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (plan_id, tenant_id, profile_id, user["email"], payload.emd_profile_id,
                 result["status"], Json(result.get("dimensions") or []),
                 Json(result.get("checkpoints") or []), RULE_VERSION),
            )
            if result["status"] == "SCHEDULED":
                cur.execute(
                    "UPDATE formation_twin_emd_sessions SET state='REASSESSMENT_SCHEDULED',updated_at=now() "
                    "WHERE id=%s AND email=%s",
                    (record["session_id"], user["email"]),
                )
            conn.commit()
        return {
            "ok": True, "plan_record_id": plan_id, **result,
            "event": _publish("emd.reassessment_scheduled", {"plan_id": plan_id, "status": result["status"]}),
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


# ── read / governance surfaces ───────────────────────────────────────────────

@router.get("/emotional-maturity/profile")
def emotional_maturity_profile(request: Request) -> dict[str, Any]:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "SELECT * FROM formation_twin_emd_profiles WHERE email=%s AND deleted_at IS NULL "
                "ORDER BY created_at DESC LIMIT 1",
                (user["email"],),
            )
            row = cur.fetchone()
        if not row:
            return {"ok": True, "profile": None, "notes": ["还没有生成过情感成熟度画像。"]}
        record = dict(row)
        evaluated_at = _state["to_shanghai_iso"](record["created_at"])
        timeframe = f"本次评估 · {evaluated_at[:10]}"
        dimensions = []
        for entry in record["dimensions_json"] or []:
            contexts = [str(item) for item in (entry.get("contexts") or []) if str(item).strip()]
            dimensions.append(build_stage_display(
                dimension_code=str(entry["dimension_code"]),
                dimension_name=str(entry.get("dimension_name") or entry["dimension_code"]),
                stage=str(entry["stage"]),
                context="、".join(contexts) if contexts else "现有已授权证据",
                timeframe=timeframe,
                confidence=str(entry["confidence"]),
                evidence_count=int(entry.get("evidence_count") or 0),
            ))
        return {
            "ok": True,
            "profile": {
                "emd_profile_id": str(record["id"]),
                "dimensions": dimensions,
                "current_strengths": record["strengths_json"],
                "growth_invitations": record["growth_invitations_json"],
                "insufficient_evidence_dimensions": record["insufficient_dimensions_json"],
                "validity_flags": record["validity_flags_json"],
                "limitations": record["limitations_json"],
                "safety_level": record["safety_level"],
                "total_score": None,
                "created_at": _state["to_shanghai_iso"](record["created_at"]),
            },
        }
    finally:
        _state["release_db"](conn)


@router.get("/emotional-maturity/data-quality")
def emotional_maturity_data_quality(request: Request) -> dict[str, Any]:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "SELECT consent_scope FROM formation_twin_emd_consents WHERE email=%s AND status='GRANTED'",
                (user["email"],),
            )
            consents = [{"granted_scopes": [row["consent_scope"] for row in cur.fetchall()]}]
            cur.execute(
                "SELECT evidence_id,dimension_code,evidence_kind,independence_group,references_json AS references "
                "FROM formation_twin_emd_evidence_items WHERE email=%s AND deleted_at IS NULL",
                (user["email"],),
            )
            evidence = [dict(row) for row in cur.fetchall()]
            cur.execute(
                "SELECT dimension_code,stage,confidence FROM formation_twin_emd_dimension_snapshots "
                "WHERE email=%s AND deleted_at IS NULL",
                (user["email"],),
            )
            snapshots = [dict(row) for row in cur.fetchall()]
        return {"ok": True, **emd_data_quality(consent_records=consents, evidence=evidence, snapshots=snapshots)}
    finally:
        _state["release_db"](conn)


@router.delete("/emotional-maturity/data")
def emotional_maturity_erase(request: Request) -> dict[str, Any]:
    """Right to erasure for the EMD domain.

    The table list lives in `formation_twin.emotional_maturity_erasure` so the
    deletion-propagation test can re-derive it from the migration files; a new
    personal table that is not added there fails the suite instead of quietly
    surviving erasure. Account-level erasure (`erase_user_data`) discovers tables
    from the catalog and covers the same ground plus the user_id-keyed stores.
    """
    user = _user(request)
    conn = _state["get_db"]()
    deleted: dict[str, int] = {}
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            for table in EMD_PERSONAL_TABLES:
                cur.execute(f"DELETE FROM {table} WHERE email=%s", (user["email"],))
                deleted[table] = cur.rowcount
            conn.commit()
        receipt = build_erasure_receipt(deleted)
        return {
            "ok": True,
            "deleted": deleted,
            "receipt": receipt,
            "derived_profiles_invalidated": True,
            "shared_summaries_invalidated": True,
            "event": _publish("emd.data_erased", {"status": "ERASED", "complete": receipt["complete"]}),
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/emotional-maturity/consent-scopes")
def emotional_maturity_consent_scopes(request: Request) -> dict[str, Any]:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            granted_scopes = _granted_scopes(cur, user["email"])
        return {
            "ok": True,
            **available_consent_scopes(),
            "granted_scopes": granted_scopes,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        _state["release_db"](conn)


# ═════════════════════════════════════════════════════════════════════════════
# EMD-OS Batch 2 — item bank, adaptive assessment and behavior evidence
# ═════════════════════════════════════════════════════════════════════════════

class NextItemPayload(BaseModel):
    session_id: str
    priority_dimensions: list[str] = Field(default_factory=list, max_length=10)
    blocked_topics: list[str] = Field(default_factory=list, max_length=20)
    fatigue: float = Field(default=0.0, ge=0, le=1)
    item_budget: int = Field(default=24, ge=1, le=120)
    life_context: str | None = None
    reading_level: str = "standard"


class ScenarioPayload(BaseModel):
    session_id: str
    target_dimension: str
    axes: dict[str, str] = Field(default_factory=dict)
    previous_axes: dict[str, str] | None = None


class ItemResponsePayload(BaseModel):
    session_id: str
    item_id: str
    dimension_code: str
    source_type: str
    context: str = "OTHER"
    scenario_context: str | None = None
    raw_response: str = Field(default="", max_length=4000)
    occurred_in_real_life: bool = False
    response_time_ms: int | None = Field(default=None, ge=0)
    skipped: bool = False
    user_confidence: int | None = Field(default=None, ge=1, le=5)
    event_recency_days: int | None = Field(default=None, ge=0)


class ProbePayload(BaseModel):
    session_id: str
    base_item_id: str
    target_dimension: str
    base_response_summary: str = Field(default="", max_length=200)
    uncertainty_type: str = "unspecified"


class CalibratePayload(BaseModel):
    dimension_code: str


class SufficiencyPayload(BaseModel):
    session_id: str
    priority_dimensions: list[str] = Field(default_factory=list, max_length=10)
    fatigue: float = Field(default=0.0, ge=0, le=1)
    item_budget: int = Field(default=24, ge=1, le=120)


def _selection_state(
    cur,
    email: str,
    session: dict[str, Any],
    payload: NextItemPayload,
    granted_scopes: list[str],
) -> SelectionState:
    cur.execute(
        "SELECT item_id FROM formation_twin_emd_responses "
        "WHERE email=%s AND session_id=%s AND deleted_at IS NULL",
        (email, session["id"]),
    )
    asked = [row["item_id"] for row in cur.fetchall()]
    cur.execute(
        "SELECT dimension_code, source_type, context FROM formation_twin_emd_behavior_evidence "
        "WHERE email=%s AND deleted_at IS NULL",
        (email,),
    )
    sources: dict[str, list[str]] = {}
    contexts: dict[str, list[str]] = {}
    for row in cur.fetchall():
        record = dict(row)
        sources.setdefault(record["dimension_code"], []).append(record["source_type"])
        contexts.setdefault(record["dimension_code"], []).append(record["context"])
    cur.execute(
        "SELECT dimension_code FROM formation_twin_emd_calibrations "
        "WHERE email=%s AND clarification_needed=TRUE AND deleted_at IS NULL",
        (email,),
    )
    contradictions = [row["dimension_code"] for row in cur.fetchall()]
    return SelectionState(
        assessment_id=str(session["id"]),
        asked_item_ids=asked,
        priority_dimensions=payload.priority_dimensions,
        blocked_topics=payload.blocked_topics,
        evidence_by_dimension=sources,
        contexts_by_dimension=contexts,
        contradictions=contradictions,
        fatigue=payload.fatigue,
        item_budget=payload.item_budget,
        safety_level=str(session.get("safety_level") or "NONE"),
        relationship_safety=str(session.get("relationship_safety") or "STANDARD"),
        behavior_evidence_allowed="EMD_BEHAVIOR_EVIDENCE" in granted_scopes,
    )


def _coverage_by_dimension(cur, email: str) -> dict[str, dict[str, Any]]:
    cur.execute(
        "SELECT dimension_code, source_type, context, user_confirmed "
        "FROM formation_twin_emd_behavior_evidence WHERE email=%s AND deleted_at IS NULL",
        (email,),
    )
    coverage: dict[str, dict[str, Any]] = {}
    for row in cur.fetchall():
        record = dict(row)
        entry = coverage.setdefault(record["dimension_code"], {"contexts": [], "user_confirmed_evidence": 0})
        entry[record["source_type"]] = int(entry.get(record["source_type"], 0)) + 1
        if record["context"] not in entry["contexts"]:
            entry["contexts"].append(record["context"])
        if record["user_confirmed"]:
            entry["user_confirmed_evidence"] += 1
    cur.execute(
        "SELECT dimension_code, COUNT(*) AS open_count FROM formation_twin_emd_calibrations "
        "WHERE email=%s AND clarification_needed=TRUE AND deleted_at IS NULL GROUP BY dimension_code",
        (email,),
    )
    for row in cur.fetchall():
        record = dict(row)
        coverage.setdefault(record["dimension_code"], {"contexts": [], "user_confirmed_evidence": 0})
        coverage[record["dimension_code"]]["unresolved_contradictions"] = int(record["open_count"])
    return coverage


@router.get("/emotional-maturity/item-bank")
def emotional_maturity_item_bank(request: Request) -> dict[str, Any]:
    _user(request)
    registry = register_item_bank(list(_ITEM_BANK.values()))
    return {
        "ok": True,
        **describe_item_engine(),
        "registry_status": registry["status"],
        "coverage": registry["coverage"],
        "items": [
            {
                "item_id": item.item_id, "dimension_code": item.dimension_code,
                "item_type": item.item_type, "response_mode": item.response_mode,
                "reverse_keyed": item.reverse_keyed, "burden": item.burden,
                "canonical_text": item.canonical_text,
            }
            for item in _ITEM_BANK.values()
        ],
    }


@router.post("/emotional-maturity/items/next")
def emotional_maturity_next_item(request: Request, payload: NextItemPayload) -> dict[str, Any]:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            session = _load_session(cur, user["email"], payload.session_id)
            granted_scopes = _require_scope(cur, user["email"], "EMD_SELF_ASSESSMENT")
            state = _selection_state(cur, user["email"], session, payload, granted_scopes)
            selection: dict[str, Any]
            intake = session.get("intake_json") or {}
            framework = {"基督信仰语言": "faith", "中性语言": "neutral"}.get(
                str(intake.get("accepted", {}).get("spiritual_framework") or ""), "user_choice"
            )
            # An unsafe or leading item must never break the whole assessment. Skip
            # it within this deterministic selection pass and try the next eligible
            # item; do not persist it as answered and do not expose its wording.
            eligible_items = list(_ITEM_BANK.values())
            while True:
                selection = select_next_item(state, eligible_items)
                if selection["decision"] != "ask_item":
                    cur.execute(
                        "UPDATE formation_twin_emd_sessions "
                        "SET validity_json=COALESCE(validity_json,'{}'::jsonb)-'active_item_id',updated_at=now() "
                        "WHERE id=%s AND email=%s",
                        (payload.session_id, user["email"]),
                    )
                    conn.commit()
                    return {"ok": True, **selection}
                selected_item_id = str(selection["selected_item_id"])
                try:
                    rendered = render_item(
                        _ITEM_BANK[selected_item_id],
                        life_context=payload.life_context,
                        reading_level="simplified" if payload.reading_level == "simplified" else "standard",
                        spiritual_framework=framework,  # type: ignore[arg-type]
                    )
                except (UnsafeContentError, ValueError):
                    eligible_items = [item for item in eligible_items if item.item_id != selected_item_id]
                    continue
                # Store only the canonical item id, never the rendered wording. The
                # response endpoint then rejects valid-but-never-presented items.
                cur.execute(
                    "UPDATE formation_twin_emd_sessions "
                    "SET validity_json=jsonb_set(COALESCE(validity_json,'{}'::jsonb),"
                    "'{active_item_id}',to_jsonb(%s::text),true),updated_at=now() "
                    "WHERE id=%s AND email=%s",
                    (selected_item_id, payload.session_id, user["email"]),
                )
                conn.commit()
                return {"ok": True, **selection, "rendered_item": rendered}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/scenarios")
def emotional_maturity_scenario(request: Request, payload: ScenarioPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            session = _load_session(cur, user["email"], payload.session_id)
            try:
                scenario = build_pressure_scenario(
                    target_dimension=payload.target_dimension,
                    axes=payload.axes,
                    previous_axes=payload.previous_axes,
                    relationship_safety=str(session.get("relationship_safety") or "STANDARD"),
                    safety_level=str(session.get("safety_level") or "NONE"),
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            cur.execute(
                "INSERT INTO formation_twin_emd_scenarios"
                "(id,tenant_id,profile_id,email,session_id,scenario_id,target_dimension,axes_json,"
                "changed_axes_json,stages_json,restrictions_json,status)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], payload.session_id,
                 scenario["scenario_id"], payload.target_dimension, Json(scenario.get("axes") or {}),
                 Json(scenario.get("changed_axes") or []), Json(scenario.get("stages") or []),
                 Json(scenario.get("restrictions") or []), scenario["status"]),
            )
            conn.commit()
        return {"ok": True, **scenario}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/responses")
def emotional_maturity_item_response(request: Request, payload: ItemResponsePayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    response_id = f"resp_{uuid.uuid4().hex[:12]}"
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            session = _load_session(cur, user["email"], payload.session_id)
            scopes = _require_scope(cur, user["email"], "EMD_SELF_ASSESSMENT")
            item = _ITEM_BANK.get(payload.item_id)
            if item is None or item.status not in {"pilot", "active"}:
                raise HTTPException(status_code=400, detail="unknown or inactive assessment item")
            active_item_id = str((session.get("validity_json") or {}).get("active_item_id") or "")
            if active_item_id != payload.item_id:
                raise HTTPException(status_code=409, detail="assessment item was not presented for this session")
            expected_source_type = _ITEM_SOURCE_TYPE[item.item_type]
            if payload.dimension_code != item.dimension_code or payload.source_type != expected_source_type:
                raise HTTPException(status_code=400, detail="assessment item metadata mismatch")
            if item.item_type == "BE" and "EMD_BEHAVIOR_EVIDENCE" not in scopes:
                raise HTTPException(status_code=403, detail="consent required: EMD_BEHAVIOR_EVIDENCE")
            if payload.skipped and payload.raw_response:
                raise HTTPException(status_code=400, detail="skipped response must not contain answer text")
            if not payload.skipped and item.response_mode in {"likert", "frequency"} and payload.raw_response not in {"1", "2", "3", "4", "5"}:
                raise HTTPException(status_code=400, detail="structured response must be between 1 and 5")
            if not payload.skipped and item.response_mode == "open_text" and not payload.raw_response.strip():
                raise HTTPException(status_code=400, detail="answer text is required unless the item is skipped")
            cur.execute(
                "SELECT 1 FROM formation_twin_emd_responses "
                "WHERE email=%s AND session_id=%s AND item_id=%s AND deleted_at IS NULL LIMIT 1",
                (user["email"], payload.session_id, payload.item_id),
            )
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="assessment item already answered")
            if payload.occurred_in_real_life and "EMD_BEHAVIOR_EVIDENCE" not in scopes:
                raise HTTPException(status_code=403, detail="consent required: EMD_BEHAVIOR_EVIDENCE")
            submitted = datetime.now(timezone.utc)
            try:
                response = AssessmentResponse(
                    response_id=response_id,
                    assessment_id=payload.session_id,
                    item_id=payload.item_id,
                    raw_response=payload.raw_response,
                    response_time_ms=payload.response_time_ms,
                    skipped=payload.skipped,
                    user_confidence=payload.user_confidence,
                    occurred_in_real_life=payload.occurred_in_real_life,
                    event_recency_days=payload.event_recency_days,
                    submitted_at=submitted,
                )
                evidence = extract_evidence(
                    response,
                    dimension_code=item.dimension_code,
                    source_type=expected_source_type,
                    context=payload.context,
                    scenario_context=payload.scenario_context,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            rubric = score_rubric(evidence)

            cur.execute(
                "INSERT INTO formation_twin_emd_responses"
                "(id,tenant_id,profile_id,email,session_id,response_id,item_id,bank_version,dimension_code,"
                "response_length,response_choice,response_time_ms,skipped,user_confidence,context_tags_json,"
                "occurred_in_real_life,event_recency_days,submitted_at)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], payload.session_id, response_id,
                 payload.item_id, BANK_VERSION, item.dimension_code, len(payload.raw_response),
                 payload.raw_response if item.response_mode in {"likert", "frequency"} and not payload.skipped else None,
                 payload.response_time_ms, payload.skipped, payload.user_confidence,
                 Json([payload.context]), payload.occurred_in_real_life, payload.event_recency_days, submitted),
            )
            cur.execute(
                "INSERT INTO formation_twin_emd_behavior_evidence"
                "(id,tenant_id,profile_id,email,evidence_id,response_id,dimension_code,source_type,evidence_level,"
                "extracted_features_json,unsupported_fields_json,context,scenario_context,behavior_specificity,"
                "evidence_reliability,fact_inference_separated,requires_user_confirmation,extractor_version)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], evidence.evidence_id, response_id,
                 evidence.dimension_code, evidence.source_type, evidence.evidence_level,
                 Json(evidence.extracted_features), Json(evidence.unsupported_fields), evidence.context,
                 evidence.scenario_context, evidence.behavior_specificity, evidence.evidence_reliability,
                 evidence.fact_inference_separated, evidence.requires_user_confirmation,
                 evidence.extractor_version),
            )
            cur.execute(
                "INSERT INTO formation_twin_emd_rubric_results"
                "(id,tenant_id,profile_id,email,rubric_result_id,evidence_id,dimension_code,rubric_version,"
                "rubric_bundle_version,provisional_stage,supported_anchors_json,missing_anchors_json,"
                "harmful_markers_json,caps_applied_json,source_type,source_confidence,source_weight,context,"
                "is_stable_capacity)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], rubric["rubric_result_id"],
                 evidence.evidence_id, evidence.dimension_code, rubric["rubric_version"], RUBRIC_BUNDLE_VERSION,
                 rubric["provisional_stage"], Json(rubric["stage_support"]["supported_anchors"]),
                 Json(rubric["stage_support"]["missing_anchors"]), Json(rubric["harmful_markers"]),
                 Json(rubric["caps_applied"]), rubric["source_type"], rubric["source_confidence"],
                 rubric["source_weight"], rubric["context"], rubric["is_stable_capacity"]),
            )

            bridged = None
            if rubric["provisional_stage"] != "E0" and not payload.skipped:
                item = to_batch1_evidence(rubric, evidence, occurred_at=submitted)
                cur.execute(
                    "INSERT INTO formation_twin_emd_evidence_items"
                    "(id,tenant_id,profile_id,email,session_id,evidence_id,dimension_code,evidence_kind,context,"
                    "stage_signal,statement_type,user_confirmed,self_rated,independence_group,behavior_summary,"
                    "references_json,occurred_at,recorded_at,excluded,exclusion_reason)"
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON CONFLICT(email,evidence_id) DO NOTHING",
                    (str(uuid.uuid4()), tenant_id, profile_id, user["email"], payload.session_id,
                     item.evidence_id, item.dimension_code, item.evidence_kind, item.context,
                     item.stage_signal, item.statement_type, item.user_confirmed, item.self_rated,
                     item.independence_group, item.behavior_summary,
                     Json([reference.model_dump(mode="json") for reference in item.references]),
                     item.occurred_at, item.recorded_at, item.excluded, item.exclusion_reason),
                )
                bridged = item.evidence_id
            _set_state(
                cur, payload.session_id, "ASSESSING", email=user["email"],
                answered_count=int(session.get("answered_count") or 0) + 1,
            )
            cur.execute(
                "UPDATE formation_twin_emd_sessions "
                "SET validity_json=COALESCE(validity_json,'{}'::jsonb)-'active_item_id' "
                "WHERE id=%s AND email=%s",
                (payload.session_id, user["email"]),
            )
            conn.commit()
        return {
            "ok": True,
            "response_id": response_id,
            "evidence": evidence.model_dump(mode="json"),
            "rubric_result": rubric,
            "bridged_evidence_id": bridged,
            "raw_text_stored": False,
            "next_action": "CROSS_ITEM_CONSISTENCY_CALIBRATOR",
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/probes")
def emotional_maturity_probe(request: Request, payload: ProbePayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            session = _load_session(cur, user["email"], payload.session_id)
            cur.execute(
                "SELECT changed_variable FROM formation_twin_emd_counterfactual_probes "
                "WHERE email=%s AND base_item_id=%s AND deleted_at IS NULL",
                (user["email"], payload.base_item_id),
            )
            existing = [row["changed_variable"] for row in cur.fetchall()]
            probe = generate_counterfactual_probe(
                base_item_id=payload.base_item_id,
                target_dimension=payload.target_dimension,
                base_response_summary=payload.base_response_summary,
                uncertainty_type=payload.uncertainty_type,
                already_tested_variables=existing,
                probes_for_base_item=len(existing),
                relationship_safety=str(session.get("relationship_safety") or "STANDARD"),
            )
            if probe["decision"] == "ask_probe":
                cur.execute(
                    "INSERT INTO formation_twin_emd_counterfactual_probes"
                    "(id,tenant_id,profile_id,email,probe_id,base_item_id,target_dimension,changed_variable,"
                    "from_condition,to_condition,probe_text)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (str(uuid.uuid4()), tenant_id, profile_id, user["email"], probe["probe_id"],
                     payload.base_item_id, payload.target_dimension, probe["changed_variable"],
                     probe["from_condition"], probe["to_condition"], probe["probe_text"]),
                )
            conn.commit()
        return {"ok": True, **probe}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/calibrate")
def emotional_maturity_calibrate(request: Request, payload: CalibratePayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "SELECT provisional_stage, source_type, context, created_at FROM formation_twin_emd_rubric_results "
                "WHERE email=%s AND dimension_code=%s AND deleted_at IS NULL ORDER BY created_at",
                (user["email"], payload.dimension_code),
            )
            rows = [dict(row) for row in cur.fetchall()]
            results = [
                {
                    "provisional_stage": row["provisional_stage"],
                    "source_type": row["source_type"],
                    "context": row["context"],
                    "time_period": row["created_at"].date().isoformat(),
                }
                for row in rows
            ]
            try:
                calibration = calibrate_consistency(payload.dimension_code, results)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            cur.execute(
                "INSERT INTO formation_twin_emd_calibrations"
                "(id,tenant_id,profile_id,email,calibration_id,dimension_code,consistency_status,patterns_json,"
                "confidence_adjustment,clarification_needed)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], calibration["calibration_id"],
                 payload.dimension_code, calibration["consistency_status"], Json(calibration["patterns"]),
                 calibration["confidence_adjustments"]["general_stage_confidence"],
                 calibration["clarification_needed"]),
            )
            conn.commit()
        return {"ok": True, **calibration}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/sufficiency")
def emotional_maturity_sufficiency(request: Request, payload: SufficiencyPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            session = _load_session(cur, user["email"], payload.session_id)
            coverage = _coverage_by_dimension(cur, user["email"])
            result = evaluate_sufficiency(
                coverage_by_dimension=coverage,
                priority_dimensions=payload.priority_dimensions or None,
                fatigue=payload.fatigue,
                items_asked=int(session.get("answered_count") or 0),
                item_budget=payload.item_budget,
                safety_changed=str(session.get("safety_level") or "NONE") in {"ELEVATED", "IMMINENT"},
            )
            cur.execute(
                "INSERT INTO formation_twin_emd_sufficiency_runs"
                "(id,tenant_id,profile_id,email,session_id,evidence_bundle_id,decision,assessment_status,"
                "dimension_readiness_json,remaining_unknowns_json,items_asked,fatigue)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], payload.session_id,
                 result["evidence_bundle_id"], result["decision"], result["assessment_status"],
                 Json(result["dimension_readiness"]), Json(result["remaining_unknowns"]),
                 int(session.get("answered_count") or 0), payload.fatigue),
            )
            if result["decision"] in {"complete_assessment", "stop_assessment"}:
                _set_state(cur, payload.session_id, "EVIDENCE_NORMALIZED", email=user["email"])
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


# ═════════════════════════════════════════════════════════════════════════════
# EMD-OS Batch 3 — real-life events, recovery, repair and longitudinal growth
# ═════════════════════════════════════════════════════════════════════════════

class EventPayload(BaseModel):
    session_id: str | None = None
    occurred_at: datetime
    context: str = "other"
    objective_facts: list[str] = Field(default_factory=list, max_length=12)
    user_interpretations: list[str] = Field(default_factory=list, max_length=12)
    emotions: list[dict[str, Any]] = Field(default_factory=list, max_length=12)
    body_signals: list[str] = Field(default_factory=list, max_length=12)
    first_response: str | None = Field(default=None, max_length=240)
    regulation_attempts: list[str] = Field(default_factory=list, max_length=10)
    later_response: str | None = Field(default=None, max_length=240)
    relationship_outcome: str | None = None
    safety_flags: list[str] = Field(default_factory=list, max_length=8)
    urge_only_actions: list[str] = Field(default_factory=list, max_length=8)
    harmful_actions: list[str] = Field(default_factory=list, max_length=8)
    related_dimensions: list[str] = Field(default_factory=list, max_length=5)
    third_party_labels: list[str] = Field(default_factory=list, max_length=6)
    pre_event_factors: list[str] = Field(default_factory=list, max_length=8)
    stage_times: dict[str, datetime] = Field(default_factory=dict)
    # 提供 stage_signal 时，事件会回流成 Batch 1 证据参与阶段判定。
    stage_signal: str | None = None
    behavior_summary: str | None = Field(default=None, max_length=400)


class RecoveryPayload(BaseModel):
    event_id: str
    trigger_at: datetime
    first_regulation_at: datetime | None = None
    harmful_action_stopped_at: datetime | None = None
    functional_recovery_at: datetime | None = None
    emotional_recovery_at: datetime | None = None
    repair_initiated_at: datetime | None = None
    rumination_minutes: int | None = Field(default=None, ge=0)
    harmful_action_occurred: bool = False
    urge_without_action: bool = False
    relationship_resolution_status: str = "not_needed"


class RepairPayload(BaseModel):
    event_id: str
    repair_actions: list[str] = Field(default_factory=list, max_length=8)
    quality_flags: dict[str, bool] = Field(default_factory=dict)
    completed: bool = False
    follow_through_events: int = Field(default=0, ge=0)
    other_party_response: str | None = Field(default=None, max_length=40)
    safety_flags: list[str] = Field(default_factory=list, max_length=8)


class TransferPayload(BaseModel):
    skill_id: str = Field(min_length=1, max_length=80)
    trained_context: str = "family"
    days_since_training: int = Field(default=0, ge=0)
    events: list[dict[str, Any]] = Field(default_factory=list, max_length=40)


class PatternPayload(BaseModel):
    pattern_name: str | None = None
    dimension_code: str | None = None
    context: str | None = None


class CheckpointSchedulePayload(BaseModel):
    growth_plan_id: str | None = None
    plan_started_at: datetime | None = None


class GrowthEvaluationPayload(BaseModel):
    day: int
    baseline_metric_set_id: str | None = None
    checkpoint_metric_set_id: str | None = None
    transfer_id: str | None = None
    comparable_event_count: int = Field(default=0, ge=0)
    contexts_observed: list[str] = Field(default_factory=list, max_length=8)
    repair_stages: list[str] = Field(default_factory=list, max_length=20)


def _metric_row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "regulation_start_latency": row.get("regulation_start_latency_seconds"),
        "behavioral_control_recovery": row.get("behavioral_control_recovery_seconds"),
        "functional_recovery": row.get("functional_recovery_seconds"),
        "emotional_recovery": row.get("emotional_recovery_seconds"),
        "repair_initiation_latency": row.get("repair_initiation_latency_seconds"),
    }


@router.get("/emotional-maturity/events/overview")
def emotional_maturity_event_overview(request: Request) -> dict[str, Any]:
    _user(request)
    return {"ok": True, **describe_event_engine()}


@router.post("/emotional-maturity/events")
def emotional_maturity_capture_event(request: Request, payload: EventPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            scopes = _granted_scopes(cur, user["email"])
            safety_level = "NONE"
            if payload.session_id:
                session = _load_session(cur, user["email"], payload.session_id)
                safety_level = str(session.get("safety_level") or "NONE")
            captured_at = datetime.now(timezone.utc)
            try:
                event = EmotionalEventInput(
                    occurred_at=payload.occurred_at,
                    captured_at=captured_at,
                    context=payload.context,
                    objective_facts=payload.objective_facts,
                    user_interpretations=payload.user_interpretations,
                    emotions=payload.emotions,
                    body_signals=payload.body_signals,
                    first_response=payload.first_response,
                    regulation_attempts=payload.regulation_attempts,
                    later_response=payload.later_response,
                    relationship_outcome=payload.relationship_outcome,
                    safety_flags=payload.safety_flags,
                    urge_only_actions=payload.urge_only_actions,
                    harmful_actions=payload.harmful_actions,
                    related_dimensions=payload.related_dimensions,
                    third_party_labels=payload.third_party_labels,
                )
            except UnsafeContentError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

            capture = capture_event(event, consented_scopes=scopes, safety_level=safety_level)
            if capture["status"] != "CAPTURED":
                conn.commit()
                return {"ok": True, **capture}

            timeline = build_timeline(
                event, stage_times=payload.stage_times or None, pre_event_factors=payload.pre_event_factors
            )
            cur.execute(
                "INSERT INTO formation_twin_emd_real_life_events"
                "(id,tenant_id,profile_id,email,event_id,context,evidence_context,evidence_level,"
                "related_dimensions_json,objective_facts_json,user_interpretations_json,emotions_json,"
                "body_signals_json,regulation_attempts_json,first_response,later_response,relationship_outcome,"
                "safety_flags_json,urge_without_action,harmful_action_occurred,fact_interpretation_separated,"
                "private_mode,status,occurred_at,captured_at)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], event.event_id, event.context,
                 capture["evidence_context"], capture["evidence_level"], Json(capture["related_dimensions"]),
                 Json(event.objective_facts), Json(event.user_interpretations), Json(event.emotions),
                 Json(event.body_signals), Json(event.regulation_attempts), event.first_response,
                 event.later_response, event.relationship_outcome, Json(event.safety_flags),
                 capture["urge_recorded_without_action"], bool(event.harmful_actions),
                 capture["fact_interpretation_separated"], event.user_requested_private_mode,
                 capture["status"], event.occurred_at, captured_at),
            )
            cur.execute(
                "INSERT INTO formation_twin_emd_event_timelines"
                "(id,tenant_id,profile_id,email,timeline_id,event_id,nodes_json,unknown_nodes_json,"
                "pre_event_vulnerability_json,turning_point_json)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], timeline["timeline_id"],
                 event.event_id, Json(_json(timeline["nodes"])), Json(timeline["unknown_nodes"]),
                 Json(timeline["pre_event_vulnerability"]), Json(timeline["turning_point"])),
            )
            # 闭环：已核实的真实事件回流成 Batch 1 的 REAL_LIFE_EVENT 证据（EM-20 → EM-06）。
            # 没有这一步，Batch 4 采集的行为证据永远进不了阶段判定，个体只能停在 E3 上限。
            bridged: list[str] = []
            if payload.stage_signal and capture["related_dimensions"]:
                for dimension_code in capture["related_dimensions"]:
                    try:
                        evidence = event_to_batch1_evidence(
                            capture,
                            dimension_code=dimension_code,
                            stage_signal=payload.stage_signal,
                            occurred_at=event.occurred_at,
                            behavior_summary=payload.behavior_summary or (event.later_response or event.first_response or ""),
                        )
                    except (UnsafeContentError, ValueError):
                        continue
                    cur.execute(
                        "INSERT INTO formation_twin_emd_evidence_items"
                        "(id,tenant_id,profile_id,email,evidence_id,dimension_code,evidence_kind,context,"
                        "stage_signal,statement_type,independence_group,behavior_summary,references_json,"
                        "occurred_at,recorded_at)"
                        "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                        "ON CONFLICT DO NOTHING",
                        (str(uuid.uuid4()), tenant_id, profile_id, user["email"],
                         f"{evidence.evidence_id}:{dimension_code}", dimension_code, evidence.evidence_kind,
                         evidence.context, evidence.stage_signal, evidence.statement_type,
                         evidence.independence_group, evidence.behavior_summary,
                         Json(_json(evidence.references)), evidence.occurred_at, evidence.recorded_at),
                    )
                    bridged.append(dimension_code)
            conn.commit()
        return {
            "ok": True, **capture, "timeline": _json(timeline),
            "bridged_to_batch1_dimensions": bridged,
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/events/recovery")
def emotional_maturity_event_recovery(request: Request, payload: RecoveryPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "SELECT event_id FROM formation_twin_emd_real_life_events "
                "WHERE email=%s AND event_id=%s AND deleted_at IS NULL",
                (user["email"], payload.event_id),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="event not found")
            cur.execute(
                "SELECT * FROM formation_twin_emd_recovery_metric_sets "
                "WHERE email=%s AND event_id<>%s AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 10",
                (user["email"], payload.event_id),
            )
            history = [_metric_row_to_dict(dict(row)) for row in cur.fetchall()]
            try:
                metrics = compute_recovery_metrics(
                    RecoveryInput(**payload.model_dump(exclude={"event_id"})),
                    previous_events=history,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            seconds = metrics["metrics_seconds"]
            cur.execute(
                "INSERT INTO formation_twin_emd_recovery_metric_sets"
                "(id,tenant_id,profile_id,email,metric_set_id,event_id,regulation_start_latency_seconds,"
                "behavioral_control_recovery_seconds,functional_recovery_seconds,emotional_recovery_seconds,"
                "repair_initiation_latency_seconds,rumination_duration_seconds,buckets_json,"
                "harmful_action_occurrence,urge_without_action,relationship_resolution_status,"
                "within_user_comparison_json)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], metrics["metric_set_id"],
                 payload.event_id, seconds["regulation_start_latency"], seconds["behavioral_control_recovery"],
                 seconds["functional_recovery"], seconds["emotional_recovery"],
                 seconds["repair_initiation_latency"], seconds["rumination_duration"],
                 Json(metrics["buckets"]), metrics["harmful_action_occurrence"],
                 metrics["urge_without_action"], metrics["relationship_resolution_status"],
                 Json(metrics["within_user_comparison"])),
            )
            conn.commit()
        return {"ok": True, **metrics}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/events/repair")
def emotional_maturity_event_repair(request: Request, payload: RepairPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "SELECT safety_flags_json FROM formation_twin_emd_real_life_events "
                "WHERE email=%s AND event_id=%s AND deleted_at IS NULL",
                (user["email"], payload.event_id),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="event not found")
            stored_flags = list(dict(row).get("safety_flags_json") or [])
            cur.execute(
                "SELECT relationship_safety FROM formation_twin_emd_sessions "
                "WHERE email=%s AND deleted_at IS NULL ORDER BY updated_at DESC LIMIT 1",
                (user["email"],),
            )
            session_row = cur.fetchone()
            relationship_safety = str(dict(session_row).get("relationship_safety") if session_row else "STANDARD")
            result = verify_repair(
                repair_actions=payload.repair_actions,
                quality_flags=payload.quality_flags,
                completed=payload.completed,
                follow_through_events=payload.follow_through_events,
                other_party_response=payload.other_party_response,
                safety_flags=[*stored_flags, *payload.safety_flags],
                relationship_safety=relationship_safety,
            )
            cur.execute(
                "INSERT INTO formation_twin_emd_repair_verifications"
                "(id,tenant_id,profile_id,email,repair_result_id,event_id,repair_stage,quality_flags_json,"
                "missing_quality_elements_json,completed_by_user,follow_through_events,other_party_response,workflow)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["repair_result_id"],
                 payload.event_id, result["repair_stage"], Json(result.get("quality_flags") or {}),
                 Json(result.get("missing_quality_elements") or []), payload.completed,
                 payload.follow_through_events, payload.other_party_response,
                 result.get("workflow", "STANDARD")),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/transfer")
def emotional_maturity_transfer(request: Request, payload: TransferPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        result = detect_transfer(
            skill_id=payload.skill_id,
            events=payload.events,
            trained_context=payload.trained_context,
            days_since_training=payload.days_since_training,
        )
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_transfer_observations"
                "(id,tenant_id,profile_id,email,transfer_id,skill_id,transfer_stage,prompt_dependence,"
                "transfer_types_json,contexts_observed_json,evidence_event_ids_json,days_since_training)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["transfer_id"],
                 payload.skill_id, result["transfer_stage"], result["prompt_dependence"],
                 Json(result.get("transfer_types") or []), Json(result.get("contexts_observed") or []),
                 Json(result.get("evidence_event_ids") or []), payload.days_since_training),
            )
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/patterns")
def emotional_maturity_patterns(request: Request, payload: PatternPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            query = (
                "SELECT e.event_id, e.occurred_at, e.context, m.behavioral_control_recovery_seconds, "
                "r.repair_stage, e.regulation_attempts_json "
                "FROM formation_twin_emd_real_life_events e "
                "LEFT JOIN formation_twin_emd_recovery_metric_sets m "
                "  ON m.event_id=e.event_id AND m.email=e.email AND m.deleted_at IS NULL "
                "LEFT JOIN formation_twin_emd_repair_verifications r "
                "  ON r.event_id=e.event_id AND r.email=e.email AND r.deleted_at IS NULL "
                "WHERE e.email=%s AND e.deleted_at IS NULL AND e.status='CAPTURED'"
            )
            params: list[Any] = [user["email"]]
            if payload.context:
                query += " AND e.context=%s"
                params.append(payload.context)
            query += " ORDER BY e.occurred_at"
            cur.execute(query, params)
            events = [
                {
                    "event_id": record["event_id"],
                    "occurred_at": record["occurred_at"],
                    "context": record["context"],
                    "behavioral_control_recovery": record["behavioral_control_recovery_seconds"],
                    "repair_stage": record["repair_stage"] or "R0",
                    "regulation_attempted": bool(record["regulation_attempts_json"]),
                }
                for record in (dict(row) for row in cur.fetchall())
            ]
            result = analyze_recurrence(events, pattern_name=payload.pattern_name)
            if result.get("status") == "ANALYSED":
                cur.execute(
                    "INSERT INTO formation_twin_emd_patterns"
                    "(id,tenant_id,profile_id,email,pattern_id,pattern_name,recurrence_count,contexts_json,"
                    "context_generalization,intensity_trend,behavioral_recovery_trend,repair_trend,"
                    "event_ids_json,first_seen_at,last_seen_at)"
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["pattern_id"],
                     result.get("pattern_name"), result["recurrence_count"], Json(result["contexts"]),
                     result["context_generalization"], result["intensity_trend"],
                     result["behavioral_recovery_trend"], result["repair_trend"],
                     Json([event["event_id"] for event in events]),
                     result["first_seen_at"], result["last_seen_at"]),
                )
            conn.commit()
        return {"ok": True, **_json(result)}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/checkpoints")
def emotional_maturity_checkpoints(request: Request, payload: CheckpointSchedulePayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            scopes = _granted_scopes(cur, user["email"])
            started = payload.plan_started_at or datetime.now(timezone.utc)
            result = schedule_checkpoints(plan_started_at=started, consented_scopes=scopes)
            if result["status"] == "SCHEDULED":
                for checkpoint in result["checkpoints"]:
                    cur.execute(
                        "INSERT INTO formation_twin_emd_checkpoints"
                        "(id,tenant_id,profile_id,email,schedule_id,growth_plan_id,day,goal,due_at,opens_at,"
                        "closes_at,recommended_evidence_json)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                        "ON CONFLICT(email,schedule_id,day) DO NOTHING",
                        (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["schedule_id"],
                         payload.growth_plan_id, checkpoint["day"], checkpoint["goal"], checkpoint["due_at"],
                         checkpoint["opens_at"], checkpoint["closes_at"],
                         Json(checkpoint["recommended_evidence"])),
                    )
            conn.commit()
        return {"ok": True, **_json(result)}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/checkpoints/evaluate")
def emotional_maturity_evaluate_checkpoint(request: Request, payload: GrowthEvaluationPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            if payload.comparable_event_count < 1:
                conn.commit()
                return {"ok": True, **handle_checkpoint_without_events(payload.day)}

            def _metrics(metric_set_id: str | None, order: str) -> dict[str, Any]:
                if metric_set_id:
                    cur.execute(
                        "SELECT * FROM formation_twin_emd_recovery_metric_sets "
                        "WHERE email=%s AND metric_set_id=%s AND deleted_at IS NULL",
                        (user["email"], metric_set_id),
                    )
                else:
                    cur.execute(
                        "SELECT * FROM formation_twin_emd_recovery_metric_sets "
                        f"WHERE email=%s AND deleted_at IS NULL ORDER BY created_at {order} LIMIT 1",
                        (user["email"],),
                    )
                row = cur.fetchone()
                return _metric_row_to_dict(dict(row)) if row else {}

            baseline = _metrics(payload.baseline_metric_set_id, "ASC")
            checkpoint = _metrics(payload.checkpoint_metric_set_id, "DESC")

            transfer = None
            if payload.transfer_id:
                cur.execute(
                    "SELECT transfer_stage, prompt_dependence FROM formation_twin_emd_transfer_observations "
                    "WHERE email=%s AND transfer_id=%s AND deleted_at IS NULL",
                    (user["email"], payload.transfer_id),
                )
                row = cur.fetchone()
                transfer = dict(row) if row else None

            try:
                result = evaluate_growth(
                    day=payload.day,
                    baseline_metrics=baseline,
                    checkpoint_metrics=checkpoint,
                    transfer=transfer,
                    repair_stages=payload.repair_stages,
                    comparable_event_count=payload.comparable_event_count,
                    contexts_observed=payload.contexts_observed,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

            cur.execute(
                "INSERT INTO formation_twin_emd_growth_evaluations"
                "(id,tenant_id,profile_id,email,evaluation_id,day,result,metric_changes_json,"
                "comparable_event_count,contexts_observed_json,transfer_stage,prompt_dependence,"
                "highlights_json,attribution_limits_json)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["evaluation_id"],
                 payload.day, result["result"], Json(result["metric_changes"]),
                 payload.comparable_event_count, Json(result["contexts_observed"]),
                 result["transfer_stage"], result["prompt_dependence"], Json(result["highlights"]),
                 Json(result["attribution_limits"])),
            )
            cur.execute(
                "UPDATE formation_twin_emd_checkpoints SET status='COMPLETED' "
                "WHERE email=%s AND day=%s AND status IN ('SCHEDULED','OPEN')",
                (user["email"], payload.day),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


# ═════════════════════════════════════════════════════════════════════════════
# EMD-OS Batch 4 — emotion awareness and regulation training
# ═════════════════════════════════════════════════════════════════════════════

class LabelPayload(BaseModel):
    regulation_session_id: str | None = None
    mode: str = "REAL_TIME"
    raw_utterance: str = Field(default="", max_length=2000)
    context: str = "other"
    known_facts: list[str] = Field(default_factory=list, max_length=8)
    user_activation_level: int | None = Field(default=None, ge=0, le=10)
    safety_signals: list[str] = Field(default_factory=list, max_length=8)
    confirmed_emotion_codes: list[str] = Field(default_factory=list, max_length=5)
    user_emotion_words: list[str] = Field(default_factory=list, max_length=3)


class BodyScanPayload(BaseModel):
    regulation_session_id: str | None = None
    reported_signals: list[str] = Field(default_factory=list, max_length=12)
    activation_level: int | None = Field(default=None, ge=0, le=10)


class TriggerProfilePayload(BaseModel):
    events: list[dict[str, Any]] = Field(default_factory=list, max_length=40)


class PausePayload(BaseModel):
    regulation_session_id: str | None = None
    band: str
    both_parties_activated: bool = False
    pause_level: str | None = None


class ImpulseGuardPayload(BaseModel):
    regulation_session_id: str | None = None
    urge_type: str = Field(min_length=1, max_length=48)
    urgency: int = Field(ge=0, le=10)
    reversibility: str
    activation_level: int | None = Field(default=None, ge=0, le=10)
    safety_signals: list[str] = Field(default_factory=list, max_length=8)
    support_available: bool = False


class CoregulationPayload(BaseModel):
    regulation_session_id: str | None = None
    requested_support: list[str] = Field(default_factory=list, max_length=7)
    activation_level: int | None = Field(default=None, ge=0, le=10)


class RecoveryPlanPayload(BaseModel):
    regulation_session_id: str | None = None
    source_event_id: str | None = None
    activation_peak: int = Field(ge=0, le=10)
    activation_current: int = Field(ge=0, le=10)
    harmful_action_occurred: bool = False
    pause_protocol_completed: bool = False
    relationship_repair_needed: bool = False
    sleep_deprived: bool = False
    work_required_within_hours: int | None = Field(default=None, ge=0)


class RehearsalPayload(BaseModel):
    regulation_session_id: str | None = None
    level: int = Field(ge=1, le=3)
    trigger_description: str = Field(min_length=1, max_length=200)
    earliest_body_signal: str = Field(min_length=1, max_length=40)
    planned_action: str = Field(min_length=1, max_length=200)
    fallback_contact: str | None = Field(default=None, max_length=40)
    changed_variable: str | None = Field(default=None, max_length=48)
    violence_context: bool = False


def _spiritual_framework(cur, email: str) -> str:
    cur.execute(
        "SELECT intake_json FROM formation_twin_emd_sessions WHERE email=%s AND deleted_at IS NULL "
        "ORDER BY updated_at DESC LIMIT 1",
        (email,),
    )
    row = cur.fetchone()
    accepted = (dict(row).get("intake_json") or {}).get("accepted", {}) if row else {}
    return {"基督信仰语言": "faith", "中性语言": "neutral"}.get(
        str(accepted.get("spiritual_framework") or ""), "user_choice"
    )


def _relationship_safety(cur, email: str) -> str:
    cur.execute(
        "SELECT relationship_safety FROM formation_twin_emd_sessions WHERE email=%s AND deleted_at IS NULL "
        "ORDER BY updated_at DESC LIMIT 1",
        (email,),
    )
    row = cur.fetchone()
    return str(dict(row).get("relationship_safety") if row else "STANDARD")


def _upsert_regulation_session(
    cur, email: str, tenant_id: str, profile_id: str, session_id: str | None, **columns: Any
) -> str:
    identifier = session_id or f"reg_{uuid.uuid4().hex[:12]}"
    keys = list(columns)
    placeholders = ",".join(["%s"] * (5 + len(keys)))
    updates = ",".join(f"{key}=EXCLUDED.{key}" for key in keys) or "updated_at=now()"
    cur.execute(
        f"INSERT INTO formation_twin_emd_regulation_sessions"
        f"(id,tenant_id,profile_id,email,regulation_session_id{',' + ','.join(keys) if keys else ''})"
        f"VALUES({placeholders}) "
        f"ON CONFLICT(email,regulation_session_id) DO UPDATE SET {updates},updated_at=now()",
        (str(uuid.uuid4()), tenant_id, profile_id, email, identifier, *[columns[key] for key in keys]),
    )
    return identifier


@router.get("/emotional-maturity/regulation/overview")
def emotional_maturity_regulation_overview(request: Request) -> dict[str, Any]:
    _user(request)
    return {"ok": True, **describe_regulation_engine()}


@router.post("/emotional-maturity/regulation/label")
def emotional_maturity_label(request: Request, payload: LabelPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            result = label_emotions(LabelingInput(
                mode=payload.mode,
                raw_utterance=payload.raw_utterance,
                context=payload.context,
                known_facts=payload.known_facts,
                user_activation_level=payload.user_activation_level,
                safety_signals=payload.safety_signals,
            ))
            if payload.confirmed_emotion_codes or payload.user_emotion_words:
                result = confirm_emotions(
                    result, payload.confirmed_emotion_codes, user_words=payload.user_emotion_words
                )
        except UnsafeContentError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            session_id = _upsert_regulation_session(
                cur, user["email"], tenant_id, profile_id, payload.regulation_session_id,
                mode=payload.mode,
                activation_level=payload.user_activation_level,
                activation_band=result["activation"]["band"],
                confirmed_emotions_json=Json(result["confirmed_emotions"]),
                emotion_candidates_json=Json(result["emotion_candidates"]),
                action_urges_json=Json(result["action_urges"]),
                deep_dive_allowed=result["activation"]["deep_dive_allowed"],
                current_node="EMOTIONS_LABELLED",
                next_action=result["next_action"],
            )
            conn.commit()
        return {"ok": True, "regulation_session_id": session_id, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/regulation/body-scan")
def emotional_maturity_body_scan(request: Request, payload: BodyScanPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        result = scan_body_signals(payload.reported_signals, activation_level=payload.activation_level)
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            session_id = _upsert_regulation_session(
                cur, user["email"], tenant_id, profile_id, payload.regulation_session_id,
                activation_level=payload.activation_level,
                body_signals_json=Json(result.get("early_signals") or []),
                medical_red_flag=result["status"] == "EXIT_TO_MEDICAL_SAFETY",
                safety_status="NEEDS_CAUTION" if result["status"] == "EXIT_TO_MEDICAL_SAFETY" else "UNKNOWN",
                current_node="BODY_SCANNED",
                next_action=result["next_action"],
            )
            conn.commit()
        return {"ok": True, "regulation_session_id": session_id, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/regulation/trigger-profile")
def emotional_maturity_trigger_profile(request: Request, payload: TriggerProfilePayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            events = payload.events
            if not events:
                cur.execute(
                    "SELECT e.context, e.body_signals_json, e.regulation_attempts_json "
                    "FROM formation_twin_emd_real_life_events e "
                    "WHERE e.email=%s AND e.deleted_at IS NULL AND e.status='CAPTURED' "
                    "ORDER BY e.occurred_at DESC LIMIT 20",
                    (user["email"],),
                )
                events = [
                    {
                        "trigger_codes": [],
                        "context": record["context"],
                        "body_signals": record["body_signals_json"] or [],
                        "urges": [],
                    }
                    for record in (dict(row) for row in cur.fetchall())
                ]
            result = build_trigger_profile(events)
            if result["status"] == "DRAFT_AWAITING_USER_CONFIRMATION":
                cur.execute(
                    "INSERT INTO formation_twin_emd_trigger_profiles"
                    "(id,tenant_id,profile_id,email,trigger_profile_id,event_count,trigger_signature_json,"
                    "contexts_json,earliest_body_signals_json,typical_urges_json,median_escalation_minutes)"
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["profile_id"],
                     result["event_count"], Json(result["trigger_signature"]), Json(result["contexts"]),
                     Json(result["earliest_body_signals"]), Json(result["typical_urges"]),
                     result["median_escalation_minutes"]),
                )
            conn.commit()
        return {"ok": True, **_json(result)}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/regulation/pause")
def emotional_maturity_pause(request: Request, payload: PausePayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            try:
                result = build_pause_protocol(
                    band=payload.band,
                    relationship_safety=_relationship_safety(cur, user["email"]),
                    both_parties_activated=payload.both_parties_activated,
                    user_requested_level=payload.pause_level,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            if result["status"] == "READY":
                cur.execute(
                    "INSERT INTO formation_twin_emd_pause_protocols"
                    "(id,tenant_id,profile_id,email,protocol_id,regulation_session_id,pause_level,steps_json,"
                    "duration_seconds_json,return_commitment_required,status)"
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["protocol_id"],
                     payload.regulation_session_id, result["pause_level"], Json(result["steps"]),
                     Json(result["duration_seconds"]), result["return_commitment_required"], "READY"),
                )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/regulation/impulse-guard")
def emotional_maturity_impulse_guard(request: Request, payload: ImpulseGuardPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            result = interrupt_impulse(
                urge_type=payload.urge_type,
                urgency=payload.urgency,
                reversibility=payload.reversibility,
                activation_level=payload.activation_level,
                safety_signals=payload.safety_signals,
                support_available=payload.support_available,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            if result["status"] == "GUARDED":
                cur.execute(
                    "INSERT INTO formation_twin_emd_impulse_guards"
                    "(id,tenant_id,profile_id,email,guard_id,regulation_session_id,urge_type,urgency,"
                    "reversibility,strategies_json,delay_seconds,substitute_action,draft_saved,send_blocked)"
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["guard_id"],
                     payload.regulation_session_id, result["urge_type"], result["urgency"],
                     result["reversibility"], Json(result["strategies"]), result["delay_seconds"],
                     result.get("substitute_action"), True, True),
                )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/regulation/coregulation")
def emotional_maturity_coregulation(request: Request, payload: CoregulationPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "SELECT * FROM formation_twin_emd_support_persons "
                "WHERE email=%s AND deleted_at IS NULL AND revoked_at IS NULL",
                (user["email"],),
            )
            contacts = [
                SupportPerson(
                    support_person_id=record["support_person_id"],
                    relationship_role=record["relationship_role"],
                    allowed_support_types=record["allowed_support_types_json"] or [],
                    available_now=True,
                    content_sharing_scope=record["content_sharing_scope"],
                    person_has_consented=record["person_has_consented"],
                    user_has_consented=record["user_has_consented"],
                    is_conflict_party=record["is_conflict_party"],
                )
                for record in (dict(row) for row in cur.fetchall())
            ]
            try:
                result = route_coregulation(
                    requested_support=payload.requested_support,
                    contacts=contacts,
                    activation_level=payload.activation_level,
                    spiritual_framework=_spiritual_framework(cur, user["email"]),
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            cur.execute(
                "INSERT INTO formation_twin_emd_coregulation_requests"
                "(id,tenant_id,profile_id,email,plan_id,regulation_session_id,requested_support_json,"
                "eligible_contacts_json,excluded_contacts_json,activation_level,status)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["plan_id"],
                 payload.regulation_session_id, Json(result["requested_support"]),
                 Json(result["eligible_contacts"]), Json(result["excluded_contacts"]),
                 payload.activation_level, result["status"]),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/regulation/recovery-plan")
def emotional_maturity_recovery_plan(request: Request, payload: RecoveryPlanPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            result = plan_recovery(
                activation_peak=payload.activation_peak,
                activation_current=payload.activation_current,
                harmful_action_occurred=payload.harmful_action_occurred,
                pause_protocol_completed=payload.pause_protocol_completed,
                relationship_repair_needed=payload.relationship_repair_needed,
                relationship_safety=_relationship_safety(cur, user["email"]),
                sleep_deprived=payload.sleep_deprived,
                work_required_within_hours=payload.work_required_within_hours,
                spiritual_framework=_spiritual_framework(cur, user["email"]),
            )
            cur.execute(
                "INSERT INTO formation_twin_emd_recovery_plans"
                "(id,tenant_id,profile_id,email,recovery_plan_id,regulation_session_id,source_event_id,"
                "activation_peak,activation_current,horizons_json,recovery_kinds_json,"
                "optional_spiritual_support_json,harmful_action_occurred,relationship_repair_needed)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["recovery_plan_id"],
                 payload.regulation_session_id, payload.source_event_id, payload.activation_peak,
                 payload.activation_current, Json(result["horizons"]), Json(result["recovery_kinds"]),
                 Json(result["optional_spiritual_support"]), payload.harmful_action_occurred,
                 payload.relationship_repair_needed),
            )
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/regulation/rehearsal")
def emotional_maturity_rehearsal(request: Request, payload: RehearsalPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            result = build_rehearsal(
                level=payload.level,
                trigger_description=payload.trigger_description,
                earliest_body_signal=payload.earliest_body_signal,
                planned_action=payload.planned_action,
                fallback_contact=payload.fallback_contact,
                changed_variable=payload.changed_variable,
                violence_context=payload.violence_context,
            )
        except UnsafeContentError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_rehearsals"
                "(id,tenant_id,profile_id,email,rehearsal_id,regulation_session_id,level,changed_variable,"
                "cards_json,status)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["rehearsal_id"],
                 payload.regulation_session_id, payload.level, result.get("changed_variable"),
                 Json(result.get("cards") or []), result["status"]),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


# ═════════════════════════════════════════════════════════════════════════════
# EMD-OS Batch 5 — family scripts, attachment and true-self integration
# ═════════════════════════════════════════════════════════════════════════════

class GenogramPayload(BaseModel):
    members: list[dict[str, Any]] = Field(default_factory=list, max_length=40)
    relationships: list[dict[str, Any]] = Field(default_factory=list, max_length=60)


class FamilyScriptPayload(BaseModel):
    genogram_id: str | None = None
    script_candidates: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    roles_reported: list[str] = Field(default_factory=list, max_length=8)
    triangles: list[dict[str, Any]] = Field(default_factory=list, max_length=8)


class AttachmentCyclePayload(BaseModel):
    relationship_context: str = Field(min_length=1, max_length=32)
    trigger_condition: str = Field(min_length=1, max_length=160)
    events: list[dict[str, Any]] = Field(default_factory=list, max_length=40)
    pressure_level: str = "medium"
    timeframe_days: int = Field(default=90, ge=1, le=730)


class DifferentiationPayload(BaseModel):
    events: list[dict[str, Any]] = Field(default_factory=list, max_length=40)
    activation_level: int | None = Field(default=None, ge=0, le=10)


class OathPayload(BaseModel):
    oath_text: str = Field(min_length=1, max_length=200)
    memory_source: str
    current_repetition: str = Field(default="", max_length=240)
    user_consent: bool = False
    activation_level: int = Field(ge=0, le=10)
    in_crisis: bool = False
    preferred_language: str = "PAST_SELF"
    spiritual_integration_enabled: bool = False
    adult_commitment: str | None = Field(default=None, max_length=240)


class MaskPayload(BaseModel):
    mask_observations: list[dict[str, Any]] = Field(default_factory=list, max_length=10)


class TrueSelfPayload(BaseModel):
    parts: dict[str, list[str]] = Field(default_factory=dict)
    adult_commitment: str = Field(min_length=1, max_length=240)
    mask_codes: list[str] = Field(default_factory=list, max_length=8)


class VulnerabilityExperimentPayload(BaseModel):
    compass_id: str | None = None
    target_relationship_type: str = Field(min_length=1, max_length=32)
    safety_status: str = "UNKNOWN"
    target_issue: str = Field(min_length=1, max_length=240)
    preferred_depth: str = "V2"
    power_asymmetry: str = "LOW"
    activation_level: int = Field(default=3, ge=0, le=10)
    prior_experiment_count: int = Field(default=0, ge=0)


@router.get("/emotional-maturity/family/overview")
def emotional_maturity_family_overview(request: Request) -> dict[str, Any]:
    _user(request)
    return {"ok": True, **describe_family_engine()}


@router.post("/emotional-maturity/family/genogram")
def emotional_maturity_genogram(request: Request, payload: GenogramPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            members = [GenogramMember(**item) for item in payload.members]
            relationships = [GenogramRelationship(**item) for item in payload.relationships]
            result = build_genogram(members, relationships)
        except UnsafeContentError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_genograms"
                "(id,tenant_id,profile_id,email,genogram_id,member_count,generations_covered_json,"
                "members_json,relationships_json,memory_sources_used_json,status)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["genogram_id"],
                 result["member_count"], Json(result["generations_covered"]), Json(result["members"]),
                 Json(result["relationships"]), Json(result["memory_sources_used"]), result["status"]),
            )
            conn.commit()
        return {"ok": True, **_json(result)}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/family/scripts")
def emotional_maturity_family_scripts(request: Request, payload: FamilyScriptPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            result = analyze_family_scripts(
                script_candidates=payload.script_candidates,
                roles_reported=payload.roles_reported,
                triangles=payload.triangles,
            )
        except UnsafeContentError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            rows: list[tuple[str, str, str | None, str, bool, dict[str, Any]]] = []
            for item in result["scripts"]:
                rows.append(("SCRIPT", item["script_code"], item["script_text"],
                             item["evidence_level"], item["may_write_to_twin"], item))
            for item in result["roles"]:
                rows.append(("ROLE", item["code"], item["label"], "FP1", False, item))
            for item in result["triangles"]:
                rows.append(("TRIANGLE", item["user_function"], item["observable_pattern"], "FP1", False, item))
            for kind, code, text, level, writable, detail in rows:
                cur.execute(
                    "INSERT INTO formation_twin_emd_family_patterns"
                    "(id,tenant_id,profile_id,email,analysis_id,genogram_id,pattern_kind,pattern_code,"
                    "pattern_text,evidence_level,may_write_to_twin,detail_json)"
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["analysis_id"],
                     payload.genogram_id, kind, code, (text or "")[:200], level, writable, Json(detail)),
                )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/family/attachment-cycle")
def emotional_maturity_attachment_cycle(request: Request, payload: AttachmentCyclePayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            try:
                result = profile_attachment_cycle(
                    relationship_context=payload.relationship_context,
                    events=payload.events,
                    trigger_condition=payload.trigger_condition,
                    pressure_level=payload.pressure_level,
                    timeframe_days=payload.timeframe_days,
                    relationship_safety=_relationship_safety(cur, user["email"]),
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            if result["status"] == "DRAFT_AWAITING_USER_CONFIRMATION":
                cur.execute(
                    "INSERT INTO formation_twin_emd_attachment_cycles"
                    "(id,tenant_id,profile_id,email,cycle_id,relationship_context,trigger_condition,"
                    "pressure_level,timeframe_days,dominant_protective_action,event_count,repair_count,"
                    "other_contexts_json,evidence_level,may_write_to_twin)"
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["cycle_id"],
                     result["relationship_context"], result["trigger_condition"], result["pressure_level"],
                     result["timeframe_days"], result["dominant_protective_action"], result["event_count"],
                     result["repair_count"], Json(result["other_contexts_observed"]),
                     result["evidence_level"], result["may_write_to_twin"]),
                )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/family/differentiation")
def emotional_maturity_differentiation(request: Request, payload: DifferentiationPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        result = assess_differentiation(events=payload.events, activation_level=payload.activation_level)
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_differentiation_assessments"
                "(id,tenant_id,profile_id,email,assessment_id,stage,event_count,practice_blocked_while_activated)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["assessment_id"],
                 result["stage"], len(payload.events), result["practice_blocked_while_activated"]),
            )
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/family/oath-reframe")
def emotional_maturity_oath_reframe(request: Request, payload: OathPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            result = reframe_survival_oath(
                oath_text=payload.oath_text,
                memory_source=payload.memory_source,
                current_repetition=payload.current_repetition,
                user_consent=payload.user_consent,
                activation_level=payload.activation_level,
                in_crisis=payload.in_crisis,
                preferred_language=payload.preferred_language,
                spiritual_integration_enabled=payload.spiritual_integration_enabled,
                adult_commitment=payload.adult_commitment,
            )
        except UnsafeContentError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            if result["status"] == "REFRAMED_DRAFT":
                cur.execute(
                    "INSERT INTO formation_twin_emd_survival_oaths"
                    "(id,tenant_id,profile_id,email,oath_id,oath_text,memory_source,language_used,"
                    "current_cost,adult_commitment,spiritual_integration_enabled,status)"
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["oath_id"],
                     result["oath_text"], result["memory_source"], result["language_used"],
                     result["current_cost"], result["adult_commitment"],
                     payload.spiritual_integration_enabled, result["status"]),
                )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/family/masks")
def emotional_maturity_masks(request: Request, payload: MaskPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            result = profile_masks(payload.mask_observations)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            for record in result["masks"]:
                cur.execute(
                    "INSERT INTO formation_twin_emd_mask_profiles"
                    "(id,tenant_id,profile_id,email,mask_profile_id,mask_code,contexts_json,"
                    "evidence_level,may_write_to_twin)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["mask_profile_id"],
                     record["mask_code"], Json(record["contexts"]), record["evidence_level"],
                     record["may_write_to_twin"]),
                )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/family/true-self")
def emotional_maturity_true_self(request: Request, payload: TrueSelfPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            try:
                result = build_true_self_compass(
                    parts=payload.parts,
                    adult_commitment=payload.adult_commitment,
                    mask_codes=payload.mask_codes,
                    spiritual_framework=_spiritual_framework(cur, user["email"]),
                )
            except UnsafeContentError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            cur.execute(
                "INSERT INTO formation_twin_emd_true_self_compasses"
                "(id,tenant_id,profile_id,email,compass_id,parts_json,missing_parts_json,completeness,"
                "adult_commitment,masks_replaced_json)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["compass_id"],
                 Json(result["parts"]), Json(result["missing_parts"]), result["completeness"],
                 result["adult_commitment"], Json(result["masks_this_replaces"])),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/family/vulnerability-experiment")
def emotional_maturity_vulnerability_experiment(
    request: Request, payload: VulnerabilityExperimentPayload
) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            result = design_vulnerability_experiment(
                target_relationship_type=payload.target_relationship_type,
                safety_status=payload.safety_status,
                target_issue=payload.target_issue,
                preferred_depth=payload.preferred_depth,
                power_asymmetry=payload.power_asymmetry,
                activation_level=payload.activation_level,
                prior_experiment_count=payload.prior_experiment_count,
            )
        except UnsafeContentError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_vulnerability_experiments"
                "(id,tenant_id,profile_id,email,experiment_id,compass_id,target_relationship_type,"
                "safety_status,depth,depth_caps_json,target_issue,expression_structure_json,status)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["experiment_id"],
                 payload.compass_id, payload.target_relationship_type, payload.safety_status,
                 result.get("depth"), Json(result.get("depth_caps_applied") or []), payload.target_issue,
                 Json(result.get("expression_structure") or []), result["status"]),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


# ═════════════════════════════════════════════════════════════════════════════
# EMD-OS Batch 6 — empathy, boundaries, clean conflict, apology and repair
# ═════════════════════════════════════════════════════════════════════════════

class PerspectivePayload(BaseModel):
    situation: str = Field(min_length=1, max_length=400)
    user_experience: str = Field(min_length=1, max_length=400)
    possible_other_experience: str = Field(min_length=1, max_length=400)
    harmful_behaviors: list[str] = Field(default_factory=list, max_length=8)


class MotivePayload(BaseModel):
    statement: str = Field(min_length=1, max_length=400)


class BoundaryPayload(BaseModel):
    boundary_object: str
    scenario: str = Field(min_length=1, max_length=400)
    boundary_kind: str = "LIMIT"
    boundary_statement: str = Field(min_length=1, max_length=240)
    my_responsibilities: list[str] = Field(default_factory=list, max_length=8)
    their_responsibilities: list[str] = Field(default_factory=list, max_length=8)
    shared_responsibilities: list[str] = Field(default_factory=list, max_length=8)
    uncontrollable: list[str] = Field(default_factory=list, max_length=8)
    action_if_violated: str = Field(min_length=1, max_length=240)
    relationship_context: str | None = Field(default=None, max_length=32)
    power_asymmetry: str = "LOW"
    guilt_level: int | None = Field(default=None, ge=0, le=10)


class EnforcementPayload(BaseModel):
    boundary_id: str | None = None
    violation_count: int = Field(default=0, ge=0)
    previous_actions: list[str] = Field(default_factory=list, max_length=10)
    power_asymmetry: str = "LOW"
    retaliation_risk: str = "LOW"
    safety_risk: bool = False
    available_support: list[str] = Field(default_factory=list, max_length=8)


class ConflictIssuePayload(BaseModel):
    raw_complaint: str = Field(min_length=1, max_length=1000)
    activation_level: int = Field(ge=0, le=10)
    violence_risk: bool = False
    single_issue: str | None = Field(default=None, max_length=240)
    willing_to_hear_other: bool = True


class DialoguePayload(BaseModel):
    issue_id: str | None = None
    mode: str = "SOLO_REHEARSAL"
    single_issue: str = Field(min_length=1, max_length=240)
    both_parties_consented: bool = False


class ApologyPayload(BaseModel):
    event_id: str | None = None
    specific_behavior: str = Field(min_length=1, max_length=240)
    impact: str = Field(min_length=1, max_length=240)
    amends: str | None = Field(default=None, max_length=240)
    change_plan: str | None = Field(default=None, max_length=240)
    draft_text: str | None = Field(default=None, max_length=1000)


class ForgivenessPayload(BaseModel):
    event_id: str | None = None
    harm_type: str = Field(min_length=1, max_length=160)
    still_feels_anger: bool = False
    pursuing_destruction: bool = False
    can_separate_justice_from_revenge: bool = True
    framework_source: str = "GENERAL_RELATIONAL_PRINCIPLES"


class RestitutionPayload(BaseModel):
    event_id: str | None = None
    mode: str = "UNILATERAL"
    items: list[dict[str, Any]] = Field(default_factory=list, max_length=10)
    other_party_consented: bool = False


class OutcomePayload(BaseModel):
    domain: str
    apology_delivered: bool = False
    restitution_completed: bool = False
    old_behavior_stopped_weeks: int = Field(default=0, ge=0)
    boundary_respected: bool = False
    safety_concern: bool = False
    repeated_violation: bool = False


@router.get("/emotional-maturity/conflict/overview")
def emotional_maturity_conflict_overview(request: Request) -> dict[str, Any]:
    _user(request)
    return {"ok": True, **describe_conflict_engine()}


@router.post("/emotional-maturity/conflict/perspective")
def emotional_maturity_perspective(request: Request, payload: PerspectivePayload) -> dict[str, Any]:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            safety = _relationship_safety(cur, user["email"])
            conn.commit()
        try:
            result = train_perspective_taking(
                situation=payload.situation,
                user_experience=payload.user_experience,
                possible_other_experience=payload.possible_other_experience,
                harmful_behaviors=payload.harmful_behaviors,
                relationship_safety="CAUTION" if safety == "CAUTION" else "UNKNOWN",
            )
        except UnsafeContentError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/conflict/motive-calibration")
def emotional_maturity_motive_calibration(request: Request, payload: MotivePayload) -> dict[str, Any]:
    _user(request)
    try:
        return {"ok": True, **calibrate_motive_uncertainty(payload.statement)}
    except UnsafeContentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/emotional-maturity/conflict/boundary")
def emotional_maturity_boundary(request: Request, payload: BoundaryPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            safety = _relationship_safety(cur, user["email"])
            try:
                result = map_boundary(
                    boundary_object=payload.boundary_object,
                    scenario=payload.scenario,
                    boundary_kind=payload.boundary_kind,
                    boundary_statement=payload.boundary_statement,
                    my_responsibilities=payload.my_responsibilities,
                    their_responsibilities=payload.their_responsibilities,
                    shared_responsibilities=payload.shared_responsibilities,
                    uncontrollable=payload.uncontrollable,
                    action_if_violated=payload.action_if_violated,
                    relationship_safety=safety,
                    power_asymmetry=payload.power_asymmetry,
                    guilt_level=payload.guilt_level,
                )
            except UnsafeContentError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            cur.execute(
                "INSERT INTO formation_twin_emd_boundaries"
                "(id,tenant_id,profile_id,email,boundary_id,boundary_object,boundary_kind,boundary_statement,"
                "responsibility_map_json,action_if_violated,relationship_context,relationship_safety,power_asymmetry)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["boundary_id"],
                 payload.boundary_object, payload.boundary_kind, payload.boundary_statement,
                 Json(result["responsibility_map"]), payload.action_if_violated,
                 payload.relationship_context, safety, payload.power_asymmetry),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/conflict/enforcement")
def emotional_maturity_enforcement(request: Request, payload: EnforcementPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        result = plan_boundary_enforcement(
            violation_count=payload.violation_count,
            previous_actions=payload.previous_actions,
            power_asymmetry=payload.power_asymmetry,
            retaliation_risk=payload.retaliation_risk,
            safety_risk=payload.safety_risk,
            available_support=payload.available_support,
        )
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_boundary_enforcements"
                "(id,tenant_id,profile_id,email,plan_id,boundary_id,recommended_level,violation_count,"
                "previous_actions_json,retaliation_risk,available_support_json)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["plan_id"],
                 payload.boundary_id, result["recommended_level"], payload.violation_count,
                 Json(payload.previous_actions), payload.retaliation_risk, Json(payload.available_support)),
            )
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/conflict/issue")
def emotional_maturity_conflict_issue(request: Request, payload: ConflictIssuePayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            result = frame_conflict_issue(
                raw_complaint=payload.raw_complaint,
                activation_level=payload.activation_level,
                violence_risk=payload.violence_risk,
                single_issue=payload.single_issue,
                willing_to_hear_other=payload.willing_to_hear_other,
            )
        except UnsafeContentError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_conflict_issues"
                "(id,tenant_id,profile_id,email,issue_id,status,single_issue,dirty_components_json,"
                "cleaned_structure_json,blocks_json,activation_level)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["issue_id"],
                 result["status"], result.get("single_issue"), Json(result.get("dirty_components") or []),
                 Json(result.get("cleaned_structure") or {}), Json(result.get("blocks") or []),
                 payload.activation_level),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/conflict/dialogue")
def emotional_maturity_dialogue(request: Request, payload: DialoguePayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            safety = _relationship_safety(cur, user["email"])
            try:
                result = facilitate_dialogue(
                    mode=payload.mode,
                    single_issue=payload.single_issue,
                    both_parties_consented=payload.both_parties_consented,
                    relationship_safety="CAUTION" if safety == "CAUTION" else "UNKNOWN",
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            cur.execute(
                "INSERT INTO formation_twin_emd_dialogues"
                "(id,tenant_id,profile_id,email,dialogue_id,issue_id,mode,status,both_parties_consented,"
                "protocol_json,pause_contract_json)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["dialogue_id"],
                 payload.issue_id, payload.mode, result["status"], payload.both_parties_consented,
                 Json(result.get("protocol") or []), Json(result.get("pause_contract") or {})),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/conflict/apology")
def emotional_maturity_apology(request: Request, payload: ApologyPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            result = build_apology(
                specific_behavior=payload.specific_behavior,
                impact=payload.impact,
                amends=payload.amends,
                change_plan=payload.change_plan,
                draft_text=payload.draft_text,
            )
        except UnsafeContentError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_apologies"
                "(id,tenant_id,profile_id,email,apology_id,event_id,status,specific_behavior,impact,"
                "amends,change_plan,missing_parts_json,invalid_patterns_json,composed_draft)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["apology_id"],
                 payload.event_id, result["status"], payload.specific_behavior, payload.impact,
                 payload.amends, payload.change_plan, Json(result["missing_parts"]),
                 Json(result["invalid_patterns"]), result["composed_draft"]),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/conflict/forgiveness")
def emotional_maturity_forgiveness(request: Request, payload: ForgivenessPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            safety = _relationship_safety(cur, user["email"])
            try:
                result = differentiate_forgiveness(
                    harm_type=payload.harm_type,
                    still_feels_anger=payload.still_feels_anger,
                    pursuing_destruction=payload.pursuing_destruction,
                    can_separate_justice_from_revenge=payload.can_separate_justice_from_revenge,
                    relationship_safety="CAUTION" if safety == "CAUTION" else "UNKNOWN",
                    framework_source=payload.framework_source,
                )
            except UnsafeContentError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            cur.execute(
                "INSERT INTO formation_twin_emd_forgiveness_maps"
                "(id,tenant_id,profile_id,email,differentiation_id,event_id,harm_type,framework_source,"
                "separation_model_json,observed_json)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["differentiation_id"],
                 payload.event_id, payload.harm_type, payload.framework_source,
                 Json(result["separation_model"]), Json(result["observed"])),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/conflict/restitution")
def emotional_maturity_restitution(request: Request, payload: RestitutionPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            safety = _relationship_safety(cur, user["email"])
            try:
                result = plan_restitution(
                    mode=payload.mode,
                    items=payload.items,
                    other_party_consented=payload.other_party_consented,
                    relationship_safety="CAUTION" if safety == "CAUTION" else "UNKNOWN",
                )
            except UnsafeContentError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            cur.execute(
                "INSERT INTO formation_twin_emd_restitution_plans"
                "(id,tenant_id,profile_id,email,plan_id,event_id,mode,status,items_json)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["plan_id"],
                 payload.event_id, payload.mode, result["status"], Json(result.get("items") or [])),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/conflict/outcome")
def emotional_maturity_repair_outcome(request: Request, payload: OutcomePayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            result = route_repair_outcome(
                domain=payload.domain,
                apology_delivered=payload.apology_delivered,
                restitution_completed=payload.restitution_completed,
                old_behavior_stopped_weeks=payload.old_behavior_stopped_weeks,
                boundary_respected=payload.boundary_respected,
                safety_concern=payload.safety_concern,
                repeated_violation=payload.repeated_violation,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_trust_assessments"
                "(id,tenant_id,profile_id,email,routing_id,domain,trust_level,evidence_json,options_json)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["routing_id"],
                 payload.domain, result["trust_level"], Json(result["evidence"]), Json(result["options"])),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


# ═════════════════════════════════════════════════════════════════════════════
# EMD-OS Batch 7 — grief, limits, sabbath and spiritual-bypassing governance
# ═════════════════════════════════════════════════════════════════════════════

class LossPayload(BaseModel):
    loss_type: str
    what_was_lost: str = Field(min_length=1, max_length=240)
    secondary_losses: list[str] = Field(default_factory=list, max_length=9)
    concrete_impacts: list[str] = Field(default_factory=list, max_length=10)
    is_ambiguous: bool = False
    occurred_at: datetime | None = None


class GriefCompanionPayload(BaseModel):
    loss_id: str | None = None
    named_emotions: list[str] = Field(default_factory=list, max_length=10)
    wants_lament: bool = False
    days_since_loss: int | None = Field(default=None, ge=0)


class ControlCalibrationPayload(BaseModel):
    loss_id: str | None = None
    buckets: dict[str, list[str]] = Field(default_factory=dict)
    still_owed_actions: list[str] = Field(default_factory=list, max_length=10)
    surrender_statement: str | None = Field(default=None, max_length=400)


class AmbiguousLossPayload(BaseModel):
    loss_id: str | None = None
    kind: str
    what_is_unresolved: str = Field(min_length=1, max_length=240)
    wants_symbolic_goodbye: bool = False
    contact_is_safe: bool = False


class BypassingCheckPayload(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    source: str = "USER_TEXT"


class RitualPayload(BaseModel):
    loss_id: str | None = None
    kind: str
    what_it_marks: str = Field(min_length=1, max_length=240)
    elements: list[str] = Field(default_factory=list, max_length=8)
    include_others: bool = False


class RestRhythmPayload(BaseModel):
    available_slots: list[str] = Field(default_factory=list, max_length=6)
    weekly_sabbath_hours: int = Field(default=4, ge=0, le=72)
    current_measures: dict[str, Any] = Field(default_factory=dict)
    slots_kept_last_week: int = Field(default=0, ge=0)


class GriefIntegrationPayload(BaseModel):
    loss_id: str | None = None
    day: int
    loss_named: bool = False
    secondary_losses_named: int = Field(default=0, ge=0)
    responsibility_separated: bool = False
    grief_expressed_events: int = Field(default=0, ge=0)
    real_actions_taken: int = Field(default=0, ge=0)
    rest_slots_kept: int = Field(default=0, ge=0)
    rest_guilt_level: int | None = Field(default=None, ge=0, le=10)
    anniversary_reaction: bool = False
    comparable_event_count: int = Field(default=0, ge=0)


@router.get("/emotional-maturity/grief/overview")
def emotional_maturity_grief_overview(request: Request) -> dict[str, Any]:
    _user(request)
    return {"ok": True, **describe_grief_engine()}


@router.post("/emotional-maturity/grief/loss-map")
def emotional_maturity_loss_map(request: Request, payload: LossPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            result = map_loss(
                loss_type=payload.loss_type,
                what_was_lost=payload.what_was_lost,
                secondary_losses=payload.secondary_losses,
                concrete_impacts=payload.concrete_impacts,
                is_ambiguous=payload.is_ambiguous,
                occurred_at=payload.occurred_at,
            )
        except UnsafeContentError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_losses"
                "(id,tenant_id,profile_id,email,loss_id,loss_type,what_was_lost,secondary_losses_json,"
                "concrete_impacts_json,is_ambiguous,integration_level,occurred_at)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["loss_id"],
                 payload.loss_type, payload.what_was_lost, Json(result["secondary_losses"]),
                 Json(result["concrete_impacts"]), payload.is_ambiguous,
                 result["integration_level"], payload.occurred_at),
            )
            conn.commit()
        return {"ok": True, **_json(result)}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/grief/companion")
def emotional_maturity_grief_companion(request: Request, payload: GriefCompanionPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            try:
                result = accompany_grief(
                    named_emotions=payload.named_emotions,
                    wants_lament=payload.wants_lament,
                    spiritual_framework=_spiritual_framework(cur, user["email"]),
                    days_since_loss=payload.days_since_loss,
                )
            except UnsafeContentError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            cur.execute(
                "INSERT INTO formation_twin_emd_grief_sessions"
                "(id,tenant_id,profile_id,email,companion_id,loss_id,named_emotions_json,lament_used,"
                "days_since_loss)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["companion_id"],
                 payload.loss_id, Json(payload.named_emotions), bool(result["lament_structure"]),
                 payload.days_since_loss),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/grief/control-calibration")
def emotional_maturity_control_calibration(request: Request, payload: ControlCalibrationPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            result = calibrate_control(
                buckets=payload.buckets,
                still_owed_actions=payload.still_owed_actions,
                surrender_statement=payload.surrender_statement,
            )
        except UnsafeContentError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_control_calibrations"
                "(id,tenant_id,profile_id,email,calibration_id,loss_id,buckets_json,"
                "outstanding_responsibilities_json,integration_level)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["calibration_id"],
                 payload.loss_id, Json(result["buckets"]), Json(result["outstanding_responsibilities"]),
                 result["integration_level"]),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/grief/ambiguous-loss")
def emotional_maturity_ambiguous_loss(request: Request, payload: AmbiguousLossPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            result = process_ambiguous_loss(
                kind=payload.kind,
                what_is_unresolved=payload.what_is_unresolved,
                wants_symbolic_goodbye=payload.wants_symbolic_goodbye,
                contact_is_safe=payload.contact_is_safe,
            )
        except UnsafeContentError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_ambiguous_losses"
                "(id,tenant_id,profile_id,email,process_id,loss_id,kind,what_is_unresolved,options_json)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["process_id"],
                 payload.loss_id, payload.kind, payload.what_is_unresolved, Json(result["options"])),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/grief/bypassing-check")
def emotional_maturity_bypassing_check(request: Request, payload: BypassingCheckPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            result = discern_spiritual_bypassing(
                payload.text, spiritual_framework=_spiritual_framework(cur, user["email"])
            )
            cur.execute(
                "INSERT INTO formation_twin_emd_bypassing_checks"
                "(id,tenant_id,profile_id,email,discernment_id,flags_json,reframes_json,source)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["discernment_id"],
                 Json(result["flags"]), Json(result["reframes"]), payload.source),
            )
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/grief/ritual")
def emotional_maturity_ritual(request: Request, payload: RitualPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            try:
                result = design_ritual(
                    kind=payload.kind,
                    what_it_marks=payload.what_it_marks,
                    elements=payload.elements or None,
                    spiritual_framework=_spiritual_framework(cur, user["email"]),
                    include_others=payload.include_others,
                )
            except UnsafeContentError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            cur.execute(
                "INSERT INTO formation_twin_emd_rituals"
                "(id,tenant_id,profile_id,email,ritual_id,loss_id,kind,what_it_marks,elements_json,with_others)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["ritual_id"],
                 payload.loss_id, payload.kind, payload.what_it_marks, Json(result["elements"]),
                 payload.include_others),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/grief/rest-rhythm")
def emotional_maturity_rest_rhythm(request: Request, payload: RestRhythmPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            try:
                result = build_rest_rhythm(
                    available_slots=payload.available_slots,
                    weekly_sabbath_hours=payload.weekly_sabbath_hours,
                    current_measures=payload.current_measures,
                    spiritual_framework=_spiritual_framework(cur, user["email"]),
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            cur.execute(
                "INSERT INTO formation_twin_emd_rest_rhythms"
                "(id,tenant_id,profile_id,email,rhythm_id,plan_json,weekly_sabbath_hours,rest_measures_json,"
                "stopping_is_not_recovery,rest_guilt_level,slots_kept_last_week)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["rhythm_id"],
                 Json(result["plan"]), payload.weekly_sabbath_hours, Json(result["rest_measures"]),
                 result["stopping_is_not_recovery"], payload.current_measures.get("REST_GUILT"),
                 payload.slots_kept_last_week),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/grief/integration")
def emotional_maturity_grief_integration(request: Request, payload: GriefIntegrationPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            result = evaluate_integration(
                day=payload.day,
                loss_named=payload.loss_named,
                secondary_losses_named=payload.secondary_losses_named,
                responsibility_separated=payload.responsibility_separated,
                grief_expressed_events=payload.grief_expressed_events,
                real_actions_taken=payload.real_actions_taken,
                rest_slots_kept=payload.rest_slots_kept,
                rest_guilt_level=payload.rest_guilt_level,
                anniversary_reaction=payload.anniversary_reaction,
                comparable_event_count=payload.comparable_event_count,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_grief_integrations"
                "(id,tenant_id,profile_id,email,evaluation_id,loss_id,day,integration_level,concerns_json,"
                "attribution_limits_json,anniversary_reaction)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["evaluation_id"],
                 payload.loss_id, payload.day, result["integration_level"], Json(result["concerns"]),
                 Json(result["attribution_limits"]), payload.anniversary_reaction),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


# ═════════════════════════════════════════════════════════════════════════════
# EMD-OS Batch 8 — Twin, identity, prayer, habits, pastoral and community
# ═════════════════════════════════════════════════════════════════════════════

class TwinBridgePayload(BaseModel):
    evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=60)


class IdentityAlignmentPayload(BaseModel):
    layers: dict[str, list[str]] = Field(default_factory=dict)
    theology_pack_id: str | None = Field(default=None, max_length=80)


class PrayerRoutingPayload(BaseModel):
    confirmed_emotions: list[str] = Field(default_factory=list, max_length=6)
    theology_pack_id: str | None = Field(default=None, max_length=80)


class RuleOfLifePayload(BaseModel):
    goals: list[dict[str, Any]] = Field(default_factory=list, max_length=12)
    current_load: int = Field(default=0, ge=0)
    capacity: str = "NORMAL"


class FormationPlanPayload(BaseModel):
    requested_tracks: list[str] = Field(default_factory=list, max_length=6)
    priority_dimensions: list[str] = Field(default_factory=list, max_length=3)
    capacity: str = "NORMAL"


class PastoralSummaryPayload(BaseModel):
    selected_fields: list[str] = Field(default_factory=list, max_length=5)
    field_values: dict[str, str] = Field(default_factory=dict)
    recipient_label: str = Field(min_length=1, max_length=80)
    expires_in_days: int = Field(default=30, ge=1, le=180)


class HandoffPayload(BaseModel):
    signals: list[str] = Field(default_factory=list, max_length=8)
    church_involved_in_harm: bool = False
    user_consented_to_contact: bool = False


class GroupPracticePayload(BaseModel):
    kind: str
    group_size: int = Field(default=4, ge=1, le=40)
    disclosure_required: bool = False
    leader_can_view_records: bool = False


class CommunityFeedbackPayload(BaseModel):
    feedback_items: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    user_disputes: list[str] = Field(default_factory=list, max_length=20)


@router.get("/emotional-maturity/integration/overview")
def emotional_maturity_integration_overview(request: Request) -> dict[str, Any]:
    _user(request)
    return {"ok": True, **describe_integration_engine()}


@router.post("/emotional-maturity/integration/twin-bridge")
def emotional_maturity_twin_bridge(request: Request, payload: TwinBridgePayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            scopes = _granted_scopes(cur, user["email"])
            try:
                evidence = [TwinEvidence(**item) for item in payload.evidence]
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            result = bridge_to_twin(evidence, consented_scopes=scopes)
            cur.execute(
                "INSERT INTO formation_twin_emd_twin_bridges"
                "(id,tenant_id,profile_id,email,bridge_id,status,written_json,held_back_json,written_count)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["bridge_id"],
                 result["status"], Json(result["written"]), Json(result.get("held_back") or []),
                 len(result["written"])),
            )
            conn.commit()
        return {"ok": True, **_json(result)}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/integration/identity")
def emotional_maturity_identity(request: Request, payload: IdentityAlignmentPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            result = map_identity_alignment(
                layers=payload.layers, theology_pack_id=payload.theology_pack_id
            )
        except UnsafeContentError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_identity_alignments"
                "(id,tenant_id,profile_id,email,alignment_id,layers_json,gaps_json,missing_layers_json,"
                "theology_pack_id)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["alignment_id"],
                 Json(result["layers"]), Json(result["gaps"]), Json(result["missing_layers"]),
                 payload.theology_pack_id),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/integration/prayer")
def emotional_maturity_prayer(request: Request, payload: PrayerRoutingPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "SELECT safety_level FROM formation_twin_emd_sessions WHERE email=%s AND deleted_at IS NULL "
                "ORDER BY updated_at DESC LIMIT 1",
                (user["email"],),
            )
            row = cur.fetchone()
            safety_level = str(dict(row).get("safety_level") if row else "NONE")
            result = route_prayer(
                confirmed_emotions=payload.confirmed_emotions,
                theology_pack_id=payload.theology_pack_id,
                spiritual_framework=_spiritual_framework(cur, user["email"]),
                safety_level=safety_level,
            )
            cur.execute(
                "INSERT INTO formation_twin_emd_prayer_routings"
                "(id,tenant_id,profile_id,email,routing_id,status,forms_json,theology_pack_id)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["routing_id"],
                 result["status"], Json(result.get("forms") or []), payload.theology_pack_id),
            )
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/integration/rule-of-life")
def emotional_maturity_rule_of_life(request: Request, payload: RuleOfLifePayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            result = compile_rule_of_life(
                goals=payload.goals, current_load=payload.current_load, capacity=payload.capacity
            )
        except UnsafeContentError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_rules_of_life"
                "(id,tenant_id,profile_id,email,rule_id,capacity,habits_json,deferred_json,total_habits)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["rule_id"],
                 payload.capacity, Json(result["habits"]), Json(result["deferred"]), result["total_habits"]),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/integration/plan")
def emotional_maturity_formation_plan(request: Request, payload: FormationPlanPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            scopes = _granted_scopes(cur, user["email"])
            cur.execute(
                "SELECT safety_level FROM formation_twin_emd_sessions WHERE email=%s AND deleted_at IS NULL "
                "ORDER BY updated_at DESC LIMIT 1",
                (user["email"],),
            )
            row = cur.fetchone()
            try:
                result = orchestrate_plan(
                    requested_tracks=payload.requested_tracks,
                    priority_dimensions=payload.priority_dimensions,
                    capacity=payload.capacity,
                    safety_level=str(dict(row).get("safety_level") if row else "NONE"),
                    consented_scopes=scopes,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            cur.execute(
                "INSERT INTO formation_twin_emd_formation_plans"
                "(id,tenant_id,profile_id,email,plan_id,status,active_tracks_json,queued_tracks_json,"
                "dropped_tracks_json,priority_dimensions_json,max_active_tracks)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["plan_id"],
                 result["status"], Json(result["active_tracks"]), Json(result.get("queued_tracks") or []),
                 Json(result.get("dropped_tracks") or []), Json(result.get("priority_dimensions") or []),
                 result.get("max_active_tracks", 3)),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/integration/pastoral-summary")
def emotional_maturity_pastoral_summary(request: Request, payload: PastoralSummaryPayload) -> dict[str, Any]:
    user = _user(request)
    try:
        guard_feature("PASTORAL_SUMMARY")
    except PilotGateError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            scopes = _granted_scopes(cur, user["email"])
            try:
                result = build_pastoral_summary(
                    selected_fields=payload.selected_fields,
                    field_values=payload.field_values,
                    recipient_label=payload.recipient_label,
                    consented_scopes=scopes,
                    expires_in_days=payload.expires_in_days,
                )
            except UnsafeContentError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            if result["status"] != "BLOCKED_NO_CONSENT":
                cur.execute(
                    "INSERT INTO formation_twin_emd_pastoral_summaries"
                    "(id,tenant_id,profile_id,email,summary_id,recipient_label,status,content_json,"
                    "excluded_fields_json,expires_at)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["summary_id"],
                     payload.recipient_label, result["status"], Json(result["content"]),
                     Json(result["excluded_fields"]),
                     datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)),
                )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/integration/handoff")
def emotional_maturity_handoff(request: Request, payload: HandoffPayload) -> dict[str, Any]:
    user = _user(request)
    try:
        guard_feature("PASTORAL_HANDOFF")
    except PilotGateError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        result = coordinate_handoff(
            signals=payload.signals,
            church_involved_in_harm=payload.church_involved_in_harm,
            user_consented_to_contact=payload.user_consented_to_contact,
        )
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_handoffs"
                "(id,tenant_id,profile_id,email,handoff_id,targets_json,signals_json,"
                "church_involved_in_harm,user_consented)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["handoff_id"],
                 Json(result["targets"]), Json(payload.signals), payload.church_involved_in_harm,
                 payload.user_consented_to_contact),
            )
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/integration/group-practice")
def emotional_maturity_group_practice(request: Request, payload: GroupPracticePayload) -> dict[str, Any]:
    user = _user(request)
    try:
        guard_feature("GROUP_PRACTICE")
    except PilotGateError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            result = design_group_practice(
                kind=payload.kind,
                group_size=payload.group_size,
                disclosure_required=payload.disclosure_required,
                leader_can_view_records=payload.leader_can_view_records,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_group_practices"
                "(id,tenant_id,profile_id,email,practice_id,kind,group_size,status)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["practice_id"],
                 payload.kind, payload.group_size, result["status"]),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/integration/community-feedback")
def emotional_maturity_community_feedback(request: Request, payload: CommunityFeedbackPayload) -> dict[str, Any]:
    user = _user(request)
    try:
        guard_feature("COMMUNITY_FEEDBACK")
    except PilotGateError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "SELECT COUNT(*) AS total FROM formation_twin_emd_evidence_items "
                "WHERE email=%s AND deleted_at IS NULL AND excluded=FALSE",
                (user["email"],),
            )
            row = cur.fetchone()
            evidence_count = int(dict(row).get("total") if row else 0)
            try:
                result = reconcile_community_feedback(
                    feedback_items=payload.feedback_items,
                    user_evidence_count=evidence_count,
                    user_disputes=payload.user_disputes,
                )
            except UnsafeContentError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            for item in result["accepted"]:
                cur.execute(
                    "INSERT INTO formation_twin_emd_community_feedback"
                    "(id,tenant_id,profile_id,email,reconciliation_id,feedback_id,power_level,observation,"
                    "weight,status)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["reconciliation_id"],
                     item["feedback_id"], item["power_level"], item["observation"][:240], item["weight"],
                     "OBSERVATION_ONLY"),
                )
            for item in result["excluded"]:
                cur.execute(
                    "INSERT INTO formation_twin_emd_community_feedback"
                    "(id,tenant_id,profile_id,email,reconciliation_id,feedback_id,observation,weight,"
                    "status,exclusion_reason)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["reconciliation_id"],
                     item["feedback_id"], "", 0, "EXCLUDED", item["reason"]),
                )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


# ═════════════════════════════════════════════════════════════════════════════
# EMD-OS Batch 9 — measurement, longitudinal analytics and growth reporting
# ═════════════════════════════════════════════════════════════════════════════

class MetricPayload(BaseModel):
    definition: dict[str, Any] = Field(default_factory=dict)


class ReassessmentPayload(BaseModel):
    day: int
    baseline_item_ids: list[str] = Field(default_factory=list, max_length=60)
    priority_dimensions: list[str] = Field(default_factory=list, max_length=4)
    new_events_since_baseline: int = Field(default=0, ge=0)
    fatigue: float = Field(default=0.0, ge=0, le=1)
    skipped_last_time: list[str] = Field(default_factory=list, max_length=30)


class ComparabilityPayload(BaseModel):
    baseline: dict[str, Any] = Field(default_factory=dict)
    current: dict[str, Any] = Field(default_factory=dict)
    stage_change: int = 0
    measurement_error: int = Field(default=1, ge=0, le=5)


class TrajectoryPayload(BaseModel):
    domain: str
    points: list[dict[str, Any]] = Field(default_factory=list, max_length=60)
    lower_is_better: bool = True


class GeneralizationPayload(BaseModel):
    observations: list[dict[str, Any]] = Field(default_factory=list, max_length=60)
    longitudinal_days: int = Field(default=0, ge=0)


class AttributionPayload(BaseModel):
    observed_change: str = Field(min_length=1, max_length=240)
    concurrent_factors: list[str] = Field(default_factory=list, max_length=8)
    regression_signals: list[str] = Field(default_factory=list, max_length=6)
    comparable_event_count: int = Field(default=0, ge=0)


class GrowthReportPayload(BaseModel):
    view: str = "PRIVATE"
    sections: dict[str, str] = Field(default_factory=dict)
    selected_fields: list[str] | None = None
    approved_by_user: bool = False
    expires_in_days: int = Field(default=30, ge=1, le=180)


@router.get("/emotional-maturity/analytics/overview")
def emotional_maturity_analytics_overview(request: Request) -> dict[str, Any]:
    _user(request)
    return {"ok": True, **describe_analytics_engine()}


@router.post("/emotional-maturity/analytics/metrics")
def emotional_maturity_register_metric(request: Request, payload: MetricPayload) -> dict[str, Any]:
    user = _user(request)
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "SELECT metric_code,version,display_name,domain,description,unit,numerator_definition,"
                "denominator_definition,eligible_evidence_types_json,status FROM formation_twin_emd_metric_catalog"
            )
            catalog: dict[tuple[str, str], MetricDefinition] = {}
            for record in (dict(row) for row in cur.fetchall()):
                catalog[(record["metric_code"], record["version"])] = MetricDefinition(
                    metric_code=record["metric_code"], version=record["version"],
                    display_name=record["display_name"], domain=record["domain"],
                    description=record["description"], unit=record["unit"],
                    numerator_definition=record["numerator_definition"],
                    denominator_definition=record["denominator_definition"],
                    eligible_evidence_types=record["eligible_evidence_types_json"] or [],
                    status=record["status"],
                )
            try:
                definition = MetricDefinition(**payload.definition)
            except UnsafeContentError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

            result = register_metric(definition, catalog=catalog)
            if result["status"] == "REGISTERED":
                cur.execute(
                    "INSERT INTO formation_twin_emd_metric_catalog"
                    "(id,metric_code,version,display_name,domain,description,unit,numerator_definition,"
                    "denominator_definition,eligible_evidence_types_json,forbidden_interpretations_json,status)"
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON CONFLICT(metric_code,version) DO NOTHING",
                    (str(uuid.uuid4()), definition.metric_code, definition.version,
                     definition.display_name, definition.domain, definition.description, definition.unit,
                     definition.numerator_definition, definition.denominator_definition,
                     Json(definition.eligible_evidence_types), Json(definition.forbidden_interpretations),
                     definition.status),
                )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/analytics/reassessment")
def emotional_maturity_compose_reassessment(request: Request, payload: ReassessmentPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            result = compose_reassessment(
                day=payload.day,
                baseline_item_ids=payload.baseline_item_ids,
                priority_dimensions=payload.priority_dimensions,
                new_events_since_baseline=payload.new_events_since_baseline,
                fatigue=payload.fatigue,
                skipped_last_time=payload.skipped_last_time,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_reassessment_compositions"
                "(id,tenant_id,profile_id,email,composition_id,day,selected_items_json,"
                "excluded_skipped_json,item_budget)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["composition_id"],
                 payload.day, Json(result["selected_items"]), Json(result["excluded_previously_skipped"]),
                 result["item_budget"]),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/analytics/comparability")
def emotional_maturity_comparability(request: Request, payload: ComparabilityPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        result = reconcile_comparability(
            baseline=payload.baseline,
            current=payload.current,
            stage_change=payload.stage_change,
            measurement_error=payload.measurement_error,
        )
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_comparability_checks"
                "(id,tenant_id,profile_id,email,reconciliation_id,comparable,verdict,changed_components_json,"
                "stage_change,measurement_error)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["reconciliation_id"],
                 result["comparable"], result["verdict"], Json(result["changed_components"]),
                 payload.stage_change, payload.measurement_error),
            )
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/analytics/trajectory")
def emotional_maturity_trajectory(request: Request, payload: TrajectoryPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            result = analyze_trajectory(
                domain=payload.domain, points=payload.points, lower_is_better=payload.lower_is_better
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_trajectories"
                "(id,tenant_id,profile_id,email,trajectory_id,domain,status,direction,early_median,"
                "late_median,delta,point_count,change_point_json)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["trajectory_id"],
                 payload.domain, result["status"], result.get("direction"), result.get("early_median"),
                 result.get("late_median"), result.get("delta"), result.get("point_count", 0),
                 Json(_json(result.get("change_point")))),
            )
            conn.commit()
        return {"ok": True, **_json(result)}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/analytics/generalization")
def emotional_maturity_generalization(request: Request, payload: GeneralizationPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        result = analyze_generalization(
            observations=payload.observations, longitudinal_days=payload.longitudinal_days
        )
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_generalizations"
                "(id,tenant_id,profile_id,email,generalization_id,level,contexts_json,per_context_json,"
                "high_pressure_events)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["generalization_id"],
                 result["level"], Json(result["contexts_observed"]), Json(result["per_context"]),
                 result["high_pressure_events"]),
            )
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/analytics/attribution")
def emotional_maturity_attribution(request: Request, payload: AttributionPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        try:
            result = calibrate_attribution(
                observed_change=payload.observed_change,
                concurrent_factors=payload.concurrent_factors,
                regression_signals=payload.regression_signals,
                comparable_event_count=payload.comparable_event_count,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            cur.execute(
                "INSERT INTO formation_twin_emd_attributions"
                "(id,tenant_id,profile_id,email,attribution_id,observed_change,alternative_explanations_json,"
                "regression_signals_json,regression_severity,evidence_sufficiency)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["attribution_id"],
                 payload.observed_change, Json(result["alternative_explanations"]),
                 Json(result["regression_signals"]), result["regression_severity"],
                 result["evidence_sufficiency"]),
            )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/emotional-maturity/analytics/report")
def emotional_maturity_growth_report(request: Request, payload: GrowthReportPayload) -> dict[str, Any]:
    user = _user(request)
    tenant_id, profile_id = _identity(user["email"])
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, user["email"])
            scopes = _granted_scopes(cur, user["email"])
            try:
                result = publish_growth_report(
                    view=payload.view,
                    sections=payload.sections,
                    consented_scopes=scopes,
                    approved_by_user=payload.approved_by_user,
                    selected_fields=payload.selected_fields,
                    expires_in_days=payload.expires_in_days,
                )
            except UnsafeContentError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            if result["status"] != "BLOCKED_NO_CONSENT":
                expires_at = (
                    datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)
                    if payload.view != "PRIVATE" else None
                )
                cur.execute(
                    "INSERT INTO formation_twin_emd_growth_reports"
                    "(id,tenant_id,profile_id,email,report_id,view,status,sections_json,user_approved,expires_at)"
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (str(uuid.uuid4()), tenant_id, profile_id, user["email"], result["report_id"],
                     payload.view, result["status"], Json(result["sections"]),
                     payload.approved_by_user, expires_at),
                )
            conn.commit()
        return {"ok": True, **result}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


# ═════════════════════════════════════════════════════════════════════════════
# EMD-OS 试点就绪：展示契约、删除计划、供应商审计与配置档能力
# ═════════════════════════════════════════════════════════════════════════════

class ProviderAuditPayload(BaseModel):
    provider: str
    answers: dict[str, bool] = Field(default_factory=dict)
    verified_by: str = Field(min_length=1, max_length=120)


@router.get("/emotional-maturity/display-contract")
def emotional_maturity_display_contract(request: Request) -> dict[str, Any]:
    """What the UI must render, and what it may never render.

    Served rather than documented so the frontend has one source of truth: stage
    displays must carry context, timeframe and confidence, and no payload may
    contain a score, percentile, ranking or diagnosis.
    """
    _user(request)
    profile = feature_matrix()["profile"]
    return {"ok": True, **display_contract(profile)}


@router.post("/emotional-maturity/display-contract/validate")
def emotional_maturity_validate_display(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    """Let the frontend (or a contract test) check a rendered payload before shipping it."""
    _user(request)
    return {"ok": True, **validate_ui_payload(payload)}


@router.get("/emotional-maturity/deletion-plan")
def emotional_maturity_deletion_plan(request: Request) -> dict[str, Any]:
    _user(request)
    return {"ok": True, **describe_deletion_plan()}


@router.get("/emotional-maturity/pilot-capabilities")
def emotional_maturity_pilot_capabilities(request: Request) -> dict[str, Any]:
    _user(request)
    return {"ok": True, **feature_matrix()}


@router.get("/emotional-maturity/training-optout")
def emotional_maturity_training_optout(request: Request) -> dict[str, Any]:
    _user(request)
    return {
        "ok": True,
        **describe_training_optout(),
        "audit_questions": [{"key": key, "text": text} for key, text in AUDIT_QUESTIONS],
    }


@router.post("/emotional-maturity/training-optout/check-corpus")
def emotional_maturity_training_corpus_check(
    request: Request, payload: dict[str, Any]
) -> dict[str, Any]:
    """Anything that assembles a training corpus must pass through here first.

    Returns 422 rather than a warning: a corpus containing P2+ material is not a
    finding to triage later, it is a request that must not proceed.
    """
    _user(request)
    records = payload.get("records") or []
    if not isinstance(records, list):
        raise HTTPException(status_code=400, detail="records must be a list")
    try:
        return {"ok": True, **assert_no_training_material(records[:200])}
    except TrainingOptOutError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/emotional-maturity/training-optout/audit")
def emotional_maturity_training_optout_audit(
    request: Request, payload: ProviderAuditPayload
) -> dict[str, Any]:
    """Record the vendor-console verification the privacy assessment needs."""
    _user(request)
    return {
        "ok": True,
        **audit_provider_config(
            provider=payload.provider, answers=payload.answers, verified_by=payload.verified_by
        ),
    }


# ═════════════════════════════════════════════════════════════════════════════
# EMD-OS BEFORE_MORE_USERS：访谈、评分一致性、事故演练、隐私评估
# ═════════════════════════════════════════════════════════════════════════════

class InterviewProtocolPayload(BaseModel):
    item_id: str = Field(max_length=80)
    item_text: str = Field(max_length=600)
    dimension_code: str
    locale: str = "zh-CN"


class InterviewAnalysisPayload(BaseModel):
    findings: list[dict[str, Any]] = Field(default_factory=list, max_length=400)
    minimum_interviews: int = Field(default=5, ge=1, le=100)


class AgreementPayload(BaseModel):
    scorings: list[dict[str, Any]] = Field(default_factory=list, max_length=600)
    threshold: float = Field(default=0.70, ge=0, le=1)


class DrillPayload(BaseModel):
    severity: str = "SEV1"
    mode: str = "DRY_RUN"
    step_durations: dict[str, int] = Field(default_factory=dict)
    human_confirmations: dict[str, bool] = Field(default_factory=dict)
    conducted_by: str = Field(default="unspecified", max_length=120)


@router.post("/emotional-maturity/psychometrics/interview-protocol")
def emotional_maturity_interview_protocol(
    request: Request, payload: InterviewProtocolPayload
) -> dict[str, Any]:
    """What the interviewer reads aloud, and which words to probe."""
    _user(request)
    try:
        return {"ok": True, **build_interview_protocol(
            item_id=payload.item_id, item_text=payload.item_text,
            dimension_code=payload.dimension_code, locale=payload.locale,
        )}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/emotional-maturity/psychometrics/interview-analysis")
def emotional_maturity_interview_analysis(
    request: Request, payload: InterviewAnalysisPayload
) -> dict[str, Any]:
    _user(request)
    try:
        return {"ok": True, **analyse_interviews(
            payload.findings, minimum_interviews=payload.minimum_interviews,
        )}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/emotional-maturity/psychometrics/agreement")
def emotional_maturity_agreement(request: Request, payload: AgreementPayload) -> dict[str, Any]:
    """Cohen's κ plus percent agreement — and a flag when the two disagree."""
    _user(request)
    try:
        report = agreement_report(payload.scorings, threshold=payload.threshold)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, **report, "triage": triage_disagreements(report)}


@router.post("/emotional-maturity/incident-drill")
def emotional_maturity_incident_drill(request: Request, payload: DrillPayload) -> dict[str, Any]:
    """Run the containment drill. Production is refused, by design."""
    _user(request)
    try:
        return {"ok": True, **run_drill(
            severity=payload.severity, mode=payload.mode,
            step_durations=payload.step_durations,
            human_confirmations=payload.human_confirmations,
            conducted_by=payload.conducted_by,
        )}
    except DrillRefused as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/emotional-maturity/privacy-assessment")
def emotional_maturity_privacy_assessment_doc(request: Request) -> dict[str, Any]:
    """The derivable half of the PIA; the legal questions stay open on purpose."""
    _user(request)
    return {"ok": True, **build_privacy_assessment(profile=feature_matrix()["profile"])}
