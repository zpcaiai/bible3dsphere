"""Batch 10 finite-scenario, evaluation, release and compliance APIs.

Governance routes expose technical evidence only.  They never return evaluation
inputs, prompt bodies, incident identity lists, or user Formation Twin content.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from psycopg2.extras import Json, RealDictCursor

from platform_orchestration.contracts import assert_platform_safe
from platform_orchestration.data_quality import scan_platform_contracts
from platform_orchestration.registry import event_registration
from production_governance import emd_assurance_profiles as emd_assurance_profiles_module
from production_governance import emd_certification
from production_governance.evaluation import (
    EvaluationDatasetSpec, run_builtin_red_team, run_evaluation,
)
from production_governance.release import (
    GovernedComponentVersion, ReleaseCandidateSpec, RightsRequestSpec, SLO_TARGETS,
    canary_bucket, cost_route, evaluate_release_candidate, kill_switch_degradation,
    processing_transparency, sanitize_governance_metadata, validate_canary_selector,
)
from production_governance.scenarios import (
    FormationScenarioSimulation, ScenarioBranch, ScenarioCreate, add_user_branch,
    build_scenario, scenario_data_quality, scenario_to_proposal,
)


router = APIRouter(tags=["formation-twin-production-governance"])
_state: dict[str, Any] = {}
FEATURE_FLAGS = {
    "scenarios": "FORMATION_TWIN_SCENARIO_SIMULATION_ENABLED",
    "evaluations": "FORMATION_TWIN_EVALUATION_PLATFORM_ENABLED",
    "shadow": "FORMATION_TWIN_SHADOW_MODE_ENABLED",
    "canary": "FORMATION_TWIN_CANARY_RELEASE_ENABLED",
    "release_gates": "FORMATION_TWIN_PRODUCTION_GATES_ENABLED",
    "cost": "FORMATION_TWIN_COST_GOVERNANCE_ENABLED",
    "dr": "FORMATION_TWIN_DISASTER_RECOVERY_ENABLED",
    "compliance": "FORMATION_TWIN_COMPLIANCE_CENTER_ENABLED",
}


def init_production_governance_router(*, get_db, release_db, get_session_user, to_shanghai_iso, is_admin=None) -> None:
    _state.update(locals())


def _enabled(feature: str) -> bool:
    return os.getenv(FEATURE_FLAGS[feature], "true").strip().lower() in {"1", "true", "yes", "on"}


def _require_feature(feature: str) -> None:
    if not _enabled(feature):
        raise HTTPException(status_code=503, detail={"code": "FEATURE_DISABLED", "feature": feature})


def _user(request: Request) -> dict[str, Any]:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _admin(request: Request) -> dict[str, Any]:
    user = _user(request)
    checker = _state.get("is_admin")
    if not checker or not checker(user["email"]):
        raise HTTPException(status_code=403, detail="platform admin only")
    return user


def _identity(email: str) -> tuple[str, str]:
    normalized = email.lower()
    return f"personal:{normalized}", str(uuid.uuid5(uuid.NAMESPACE_URL, f"formation-twin:{normalized}"))


def _cursor(conn):
    return conn.cursor(cursor_factory=RealDictCursor)


def _owner(cur, email: str) -> None:
    cur.execute("SELECT set_config('app.current_user_email',%s,true)", (email,))


def _safe_row(row: dict[str, Any], *, admin: bool = False) -> dict[str, Any]:
    blocked = {"email", "tenant_id", "profile_id", "subject_user_id", "subject_reference_hash"}
    if admin:
        blocked.update({"comment", "user_impact_summary"})
    return {key: value for key, value in row.items() if key not in blocked}


def _publish(cur, event_type: str, aggregate_id: str, payload: dict[str, Any]) -> None:
    registration = event_registration(event_type)
    if not registration:
        raise RuntimeError("UNREGISTERED_GOVERNANCE_EVENT")
    assert_platform_safe(payload)
    extra = set(payload) - set(registration["allowed_payload_fields"])
    if extra:
        raise RuntimeError("EVENT_PAYLOAD_CONTRACT_VIOLATION:" + ",".join(sorted(extra)))
    cur.execute(
        "INSERT INTO domain_events(aggregate_type,aggregate_id,event_type,payload) VALUES(%s,%s,%s,%s)",
        ("production_governance", aggregate_id, event_type, Json(payload)),
    )


def _kill_switch_active(cur, switch_key: str) -> bool:
    cur.execute("SELECT active FROM governance_kill_switches WHERE switch_key=%s", (switch_key,))
    row = cur.fetchone()
    return bool(row and row["active"])


def _scenario_from_row(row: dict[str, Any]) -> FormationScenarioSimulation:
    return FormationScenarioSimulation(
        id=row["id"], title=row["title"], scenario_type=row["scenario_type"],
        baseline_snapshot_ids=row["baseline_snapshot_ids_json"] or [],
        baseline_generated_at=row["baseline_generated_at"], assumptions=row["assumptions_json"] or [],
        fixed_constraints=row["fixed_constraints_json"] or [], excluded_factors=row["excluded_factors_json"] or [],
        horizon=row["horizon"], branches=row["branches_json"] or [],
        evidence_matrix=row["evidence_matrix_json"] or {}, uncertainty_notes=row["uncertainty_notes_json"] or [],
        non_prediction_notice=row["non_prediction_notice"],
        prohibited_interpretations=row["prohibited_interpretations_json"] or [],
        generation_method=row["generation_method"], engine_version=row["engine_version"],
        model_version=row["model_version"], rule_version=row["rule_version"],
        user_review_status=row["user_review_status"], created_at=row["created_at"], expires_at=row["expires_at"],
        major_decision_limited=bool(row["major_decision_limited"]),
    )


def _validate_baseline_ownership(cur, email: str, ids: list[str]) -> None:
    if not ids:
        return
    for value in ids:
        try:
            uuid.UUID(str(value))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="baseline references must be UUIDs") from exc
    cur.execute(
        "SELECT id::text FROM formation_twin_emotional_snapshots WHERE email=%s AND id=ANY(%s::uuid[]) "
        "UNION SELECT id::text FROM formation_twin_formation_snapshots WHERE email=%s AND id=ANY(%s::uuid[]) "
        "UNION SELECT id::text FROM formation_twin_long_term_snapshots WHERE email=%s AND id=ANY(%s::uuid[])",
        (email, ids, email, ids, email, ids),
    )
    found = {row["id"] for row in cur.fetchall()}
    if found != set(ids):
        raise HTTPException(status_code=422, detail="baseline must reference current user's Formation Twin snapshots")


def _insert_scenario(cur, email: str, request: ScenarioCreate, simulation: FormationScenarioSimulation) -> None:
    tenant, profile = _identity(email)
    payload = simulation.model_dump(mode="json")
    cur.execute(
        "INSERT INTO formation_twin_scenarios(id,tenant_id,profile_id,email,title,question,scenario_type,"
        "baseline_snapshot_ids_json,baseline_generated_at,assumptions_json,fixed_constraints_json,excluded_factors_json,"
        "horizon,branches_json,evidence_matrix_json,uncertainty_notes_json,non_prediction_notice,"
        "prohibited_interpretations_json,generation_method,engine_version,model_version,rule_version,user_review_status,"
        "major_decision_limited,created_at,expires_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            str(simulation.id), tenant, profile, email, simulation.title, request.question,
            simulation.scenario_type.value, Json(payload["baseline_snapshot_ids"]), simulation.baseline_generated_at,
            Json(payload["assumptions"]), Json(simulation.fixed_constraints), Json(simulation.excluded_factors),
            simulation.horizon.value, Json(payload["branches"]), Json(payload["evidence_matrix"]),
            Json(simulation.uncertainty_notes), simulation.non_prediction_notice,
            Json(simulation.prohibited_interpretations), simulation.generation_method, simulation.engine_version,
            simulation.model_version, simulation.rule_version, simulation.user_review_status,
            simulation.major_decision_limited, simulation.created_at, simulation.expires_at,
        ),
    )


@router.post("/api/v1/formation-twin/scenarios")
def create_scenario(request: Request, body: ScenarioCreate) -> dict[str, Any]:
    _require_feature("scenarios")
    email = _user(request)["email"].lower(); conn = _state["get_db"]()
    try:
        cur = _cursor(conn); _owner(cur, email)
        if _kill_switch_active(cur, "formation-scenario-simulation"):
            raise HTTPException(status_code=503, detail={"code": "KILL_SWITCH_ACTIVE", **kill_switch_degradation("SCENARIO_SIMULATION")})
        _validate_baseline_ownership(cur, email, body.baseline_snapshot_ids)
        simulation = build_scenario(body)
        _insert_scenario(cur, email, body, simulation)
        _publish(cur, "formation_twin.scenario_created", email, {"scenario_id": str(simulation.id), "status": simulation.user_review_status})
        _publish(cur, "formation_twin.scenario_generated", email, {"scenario_id": str(simulation.id), "status": "GENERATED", "engine_version": simulation.engine_version})
        conn.commit(); return {"scenario": simulation.model_dump(mode="json")}
    except HTTPException:
        conn.rollback(); raise
    except ValueError as exc:
        conn.rollback(); raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        _state["release_db"](conn)


@router.get("/api/v1/formation-twin/scenarios")
def list_scenarios(request: Request) -> dict[str, Any]:
    email = _user(request)["email"].lower(); conn = _state["get_db"]()
    try:
        cur = _cursor(conn); _owner(cur, email)
        cur.execute("SELECT * FROM formation_twin_scenarios WHERE email=%s AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 100", (email,))
        return {"scenarios": [_scenario_from_row(dict(row)).model_dump(mode="json") for row in cur.fetchall()]}
    finally: _state["release_db"](conn)


def _scenario_row(cur, email: str, scenario_id: str) -> dict[str, Any]:
    cur.execute("SELECT * FROM formation_twin_scenarios WHERE email=%s AND id=%s AND deleted_at IS NULL", (email, scenario_id))
    row = cur.fetchone()
    if not row: raise HTTPException(status_code=404, detail="Scenario not found")
    return dict(row)


@router.get("/api/v1/formation-twin/scenarios/{scenario_id}")
def get_scenario(request: Request, scenario_id: str) -> dict[str, Any]:
    email = _user(request)["email"].lower(); conn = _state["get_db"]()
    try:
        cur = _cursor(conn); _owner(cur, email)
        return {"scenario": _scenario_from_row(_scenario_row(cur,email,scenario_id)).model_dump(mode="json")}
    finally: _state["release_db"](conn)


class ScenarioPatchBody(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    user_review_status: Literal["DRAFT", "USER_CONFIRMED", "INACCURATE"] | None = None


@router.patch("/api/v1/formation-twin/scenarios/{scenario_id}")
def patch_scenario(request: Request, scenario_id: str, body: ScenarioPatchBody) -> dict[str, Any]:
    email = _user(request)["email"].lower(); conn = _state["get_db"]()
    try:
        cur = _cursor(conn); _owner(cur,email); _scenario_row(cur,email,scenario_id)
        cur.execute("UPDATE formation_twin_scenarios SET title=COALESCE(%s,title),user_review_status=COALESCE(%s,user_review_status) WHERE email=%s AND id=%s", (body.title,body.user_review_status,email,scenario_id))
        conn.commit(); return {"scenario": _scenario_from_row(_scenario_row(cur,email,scenario_id)).model_dump(mode="json")}
    finally: _state["release_db"](conn)


@router.delete("/api/v1/formation-twin/scenarios/{scenario_id}")
def delete_scenario(request: Request, scenario_id: str) -> dict[str, Any]:
    email = _user(request)["email"].lower(); conn = _state["get_db"]()
    try:
        cur = _cursor(conn); _owner(cur,email); _scenario_row(cur,email,scenario_id)
        cur.execute("UPDATE formation_twin_scenarios SET deleted_at=now(),invalidated_at=now() WHERE email=%s AND id=%s", (email,scenario_id))
        _publish(cur,"formation_twin.scenario_invalidated",email,{"scenario_id":scenario_id,"status":"USER_DELETED"})
        conn.commit(); return {"ok": True, "scenario_id": scenario_id}
    finally: _state["release_db"](conn)


@router.post("/api/v1/formation-twin/scenarios/{scenario_id}/generate")
def regenerate_scenario(request: Request, scenario_id: str) -> dict[str, Any]:
    _require_feature("scenarios"); email = _user(request)["email"].lower(); conn = _state["get_db"]()
    try:
        cur = _cursor(conn); _owner(cur,email)
        if _kill_switch_active(cur,"formation-scenario-simulation"):
            raise HTTPException(status_code=503,detail={"code":"KILL_SWITCH_ACTIVE"})
        row=_scenario_row(cur,email,scenario_id); simulation=_scenario_from_row(row)
        quality=scenario_data_quality(simulation)
        if not quality["ok"]: raise HTTPException(status_code=409,detail={"code":"SCENARIO_QUALITY_BLOCKED","issues":quality["issues"]})
        _publish(cur,"formation_twin.scenario_generated",email,{"scenario_id":scenario_id,"status":"REVALIDATED","engine_version":simulation.engine_version})
        conn.commit(); return {"scenario":simulation.model_dump(mode="json"),"quality":quality}
    finally: _state["release_db"](conn)


@router.post("/api/v1/formation-twin/scenarios/{scenario_id}/add-branch")
def add_scenario_branch(request: Request, scenario_id: str, body: ScenarioBranch) -> dict[str, Any]:
    email=_user(request)["email"].lower(); conn=_state["get_db"]()
    try:
        cur=_cursor(conn);_owner(cur,email);simulation=_scenario_from_row(_scenario_row(cur,email,scenario_id))
        updated=add_user_branch(simulation,body)
        cur.execute("UPDATE formation_twin_scenarios SET branches_json=%s WHERE email=%s AND id=%s",(Json([item.model_dump(mode="json") for item in updated.branches]),email,scenario_id))
        conn.commit(); return {"scenario":updated.model_dump(mode="json")}
    except ValueError as exc:
        conn.rollback(); raise HTTPException(status_code=422,detail=str(exc)) from exc
    finally:_state["release_db"](conn)


class ConvertScenarioBody(BaseModel):
    branch_id: str
    user_confirmed_conversion: Literal[True]


@router.post("/api/v1/formation-twin/scenarios/{scenario_id}/convert-to-proposal")
def convert_scenario(request: Request, scenario_id: str, body: ConvertScenarioBody) -> dict[str, Any]:
    email=_user(request)["email"].lower();conn=_state["get_db"]()
    try:
        cur=_cursor(conn);_owner(cur,email);simulation=_scenario_from_row(_scenario_row(cur,email,scenario_id))
        proposal=scenario_to_proposal(simulation,body.branch_id);proposal_id=str(uuid.uuid4())
        cur.execute("UPDATE formation_twin_scenarios SET converted_proposal_reference=%s WHERE email=%s AND id=%s",(proposal_id,email,scenario_id))
        _publish(cur,"formation_twin.scenario_converted_to_proposal",email,{"scenario_id":scenario_id,"proposal_id":proposal_id,"status":"REQUIRES_BATCH_6_CONFIRMATION"})
        conn.commit(); return {"proposal":{**proposal,"proposal_id":proposal_id}}
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    finally:_state["release_db"](conn)


@router.post("/api/v1/formation-twin/scenarios/{scenario_id}/mark-inaccurate")
def mark_scenario_inaccurate(request: Request, scenario_id: str) -> dict[str, Any]:
    return patch_scenario(request,scenario_id,ScenarioPatchBody(user_review_status="INACCURATE"))


@router.post("/api/v1/governance/evaluation-datasets")
def register_dataset(request: Request, body: EvaluationDatasetSpec) -> dict[str, Any]:
    _require_feature("evaluations"); admin=_admin(request);conn=_state["get_db"](); dataset_id=str(uuid.uuid4())
    try:
        cur=_cursor(conn)
        cur.execute("INSERT INTO governance_evaluation_datasets(id,dataset_key,version,task_family,locale,data_source_type,sensitivity,schema_version,case_count,consent_basis,retention_policy,allowed_uses_json,owner_team,approved_by_json,status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(dataset_id,body.dataset_key,body.version,body.task_family,body.locale,body.data_source_type,body.sensitivity,body.schema_version,body.case_count,body.consent_basis,body.retention_policy,Json(body.allowed_uses),body.owner_team,Json(body.approved_by),"ACTIVE"))
        _publish(cur,"governance.evaluation_dataset_registered",body.dataset_key,{"dataset_id":dataset_id,"version":body.version,"status":"ACTIVE"})
        conn.commit();return {"dataset_id":dataset_id,"status":"ACTIVE","registered_by":admin["email"]}
    finally:_state["release_db"](conn)


@router.get("/api/v1/governance/evaluation-datasets")
def list_datasets(request: Request)->dict[str,Any]:
    _admin(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("SELECT * FROM governance_evaluation_datasets ORDER BY created_at DESC LIMIT 200")
        return {"datasets":[_safe_row(dict(row),admin=True) for row in cur.fetchall()]}
    finally:_state["release_db"](conn)


@router.get("/api/v1/governance/evaluation-datasets/{dataset_id}")
def get_dataset(request:Request,dataset_id:str)->dict[str,Any]:
    _admin(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("SELECT * FROM governance_evaluation_datasets WHERE id=%s",(dataset_id,));row=cur.fetchone()
        if not row:raise HTTPException(status_code=404,detail="Dataset not found")
        return {"dataset":_safe_row(dict(row),admin=True)}
    finally:_state["release_db"](conn)


class EvaluationRunBody(BaseModel):
    run_type: Literal["MODEL","RULE","PROMPT","WORKFLOW","PRIVACY","SAFETY"]
    component_type:str;component_id:str;component_version:str;dataset_id:str;dataset_version:str;task_family:str
    candidate_outputs:list[dict[str,Any]]=Field(default_factory=list,max_length=500)
    regression_comparison:dict[str,Any]=Field(default_factory=dict)


@router.post("/api/v1/governance/evaluation-runs")
def create_evaluation_run(request:Request,body:EvaluationRunBody)->dict[str,Any]:
    _require_feature("evaluations");_admin(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("SELECT 1 FROM governance_evaluation_datasets WHERE id=%s AND version=%s AND status='ACTIVE'",(body.dataset_id,body.dataset_version))
        if not cur.fetchone():raise HTTPException(status_code=422,detail="active dataset version not found")
        result=run_evaluation(component_type=body.component_type,component_id=body.component_id,component_version=body.component_version,task_family=body.task_family,outputs=body.candidate_outputs)
        data=result.model_dump(mode="json")
        cur.execute("INSERT INTO governance_evaluation_runs(id,run_type,component_type,component_id,component_version,dataset_id,dataset_version,metrics_json,safety_failures_json,regression_comparison_json,status,started_at,completed_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(str(result.run_id),body.run_type,body.component_type,body.component_id,body.component_version,body.dataset_id,body.dataset_version,Json(data["metrics"]),Json(data["safety_failures"]),Json(body.regression_comparison),result.status,result.started_at,result.completed_at))
        event="governance.evaluation_run_failed" if result.status=="BLOCKED" else "governance.evaluation_run_completed"
        _publish(cur,event,body.component_id,{"run_id":str(result.run_id),"component_id":body.component_id,"version":body.component_version,"status":result.status})
        conn.commit();return {"evaluation":data}
    except ValueError as exc:conn.rollback();raise HTTPException(status_code=422,detail=str(exc)) from exc
    finally:_state["release_db"](conn)


@router.get("/api/v1/governance/evaluation-runs")
def list_evaluation_runs(request:Request)->dict[str,Any]:
    _admin(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("SELECT * FROM governance_evaluation_runs ORDER BY started_at DESC LIMIT 200")
        return {"runs":[_safe_row(dict(row),admin=True) for row in cur.fetchall()]}
    finally:_state["release_db"](conn)


@router.get("/api/v1/governance/evaluation-runs/{run_id}")
def get_evaluation_run(request:Request,run_id:str)->dict[str,Any]:
    _admin(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("SELECT * FROM governance_evaluation_runs WHERE id=%s",(run_id,));row=cur.fetchone()
        if not row:raise HTTPException(status_code=404,detail="Evaluation run not found")
        return {"run":_safe_row(dict(row),admin=True)}
    finally:_state["release_db"](conn)


@router.post("/api/v1/governance/evaluation-runs/{run_id}/cancel")
def cancel_evaluation_run(request:Request,run_id:str)->dict[str,Any]:
    _admin(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("UPDATE governance_evaluation_runs SET status='CANCELLED',completed_at=now() WHERE id=%s AND status IN('QUEUED','RUNNING')",(run_id,));conn.commit()
        return {"ok":bool(cur.rowcount),"run_id":run_id}
    finally:_state["release_db"](conn)


@router.get("/api/v1/governance/evaluations/red-team")
def red_team_status(request:Request)->dict[str,Any]:
    _admin(request);return run_builtin_red_team()


@router.get("/api/v1/governance/components")
def list_components(request:Request)->dict[str,Any]:
    _admin(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("SELECT * FROM governance_component_versions ORDER BY created_at DESC LIMIT 300")
        return {"components":[_safe_row(dict(row),admin=True) for row in cur.fetchall()]}
    finally:_state["release_db"](conn)


@router.get("/api/v1/governance/components/{component_type}/{component_id}")
def get_component(request:Request,component_type:str,component_id:str)->dict[str,Any]:
    _admin(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("SELECT * FROM governance_component_versions WHERE component_type=%s AND component_id=%s ORDER BY created_at DESC",(component_type.upper(),component_id));return {"versions":[_safe_row(dict(row),admin=True) for row in cur.fetchall()]}
    finally:_state["release_db"](conn)


@router.post("/api/v1/governance/components/{component_type}/{component_id}/versions")
def register_component(request:Request,component_type:str,component_id:str,body:GovernedComponentVersion)->dict[str,Any]:
    admin=_admin(request)
    if body.component_type!=component_type.upper() or body.component_id!=component_id:raise HTTPException(status_code=422,detail="component path and body must match")
    conn=_state["get_db"]();version_id=str(uuid.uuid4())
    try:
        cur=_cursor(conn);cur.execute("INSERT INTO governance_component_versions(id,component_type,component_id,version,artifact_reference,checksum,evaluation_report_ids_json,approved_environments_json,risk_classification,approval_status,created_by,approved_by_json) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(version_id,body.component_type,body.component_id,body.version,body.artifact_reference,body.checksum,Json(body.evaluation_report_ids),Json(body.approved_environments),body.risk_classification,body.approval_status,admin["email"],Json(body.approved_by)))
        _publish(cur,"governance.component_version_registered",body.component_id,{"component_id":body.component_id,"version":body.version,"status":body.approval_status})
        conn.commit();return {"version_id":version_id,"status":body.approval_status}
    finally:_state["release_db"](conn)


def _component_transition(request:Request,component_type:str,component_id:str,action:str,version:str)->dict[str,Any]:
    admin=_admin(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn)
        if action=="activate":
            cur.execute("SELECT * FROM governance_component_versions WHERE component_type=%s AND component_id=%s AND version=%s",(component_type.upper(),component_id,version));row=cur.fetchone()
            if not row or row["approval_status"]!="APPROVED" or "PRODUCTION" not in (row["approved_environments_json"] or []):raise HTTPException(status_code=409,detail="only production-approved fixed versions may activate")
            cur.execute("UPDATE governance_component_versions SET activated_at=NULL WHERE component_type=%s AND component_id=%s",(component_type.upper(),component_id))
            cur.execute("UPDATE governance_component_versions SET activated_at=now() WHERE component_type=%s AND component_id=%s AND version=%s",(component_type.upper(),component_id,version))
            event="governance.component_version_activated"
        elif action=="deprecate":
            cur.execute("UPDATE governance_component_versions SET deprecated_at=now() WHERE component_type=%s AND component_id=%s AND version=%s",(component_type.upper(),component_id,version));event="governance.component_version_deprecated"
        else:
            cur.execute("SELECT version FROM governance_component_versions WHERE component_type=%s AND component_id=%s AND version=%s AND approval_status='APPROVED'",(component_type.upper(),component_id,version))
            if not cur.fetchone():raise HTTPException(status_code=409,detail="rollback target must be an approved fixed version")
            cur.execute("UPDATE governance_component_versions SET activated_at=NULL WHERE component_type=%s AND component_id=%s",(component_type.upper(),component_id))
            cur.execute("UPDATE governance_component_versions SET activated_at=now() WHERE component_type=%s AND component_id=%s AND version=%s",(component_type.upper(),component_id,version));event="governance.component_version_rolled_back"
        _publish(cur,event,component_id,{"component_id":component_id,"version":version,"status":action.upper(),"actor_id":hashlib.sha256(admin["email"].encode()).hexdigest()[:16]})
        conn.commit();return {"ok":True,"component_id":component_id,"version":version,"action":action}
    finally:_state["release_db"](conn)


class VersionActionBody(BaseModel):version:str


@router.post("/api/v1/governance/components/{component_type}/{component_id}/activate")
def activate_component(request:Request,component_type:str,component_id:str,body:VersionActionBody):return _component_transition(request,component_type,component_id,"activate",body.version)
@router.post("/api/v1/governance/components/{component_type}/{component_id}/deprecate")
def deprecate_component(request:Request,component_type:str,component_id:str,body:VersionActionBody):return _component_transition(request,component_type,component_id,"deprecate",body.version)
@router.post("/api/v1/governance/components/{component_type}/{component_id}/rollback")
def rollback_component(request:Request,component_type:str,component_id:str,body:VersionActionBody):return _component_transition(request,component_type,component_id,"rollback",body.version)


@router.post("/api/v1/governance/releases")
def create_release(request:Request,body:ReleaseCandidateSpec)->dict[str,Any]:
    _require_feature("release_gates");_admin(request);conn=_state["get_db"]();release_id=str(uuid.uuid4())
    try:
        cur=_cursor(conn);decision=evaluate_release_candidate(body,batch08_available=False)
        cur.execute("INSERT INTO governance_release_candidates(id,release_key,version,changed_components_json,migration_ids_json,evaluation_report_ids_json,security_scan_ids_json,performance_report_ids_json,gate_results_json,rollback_plan_reference,incident_owner,approval_status,deployment_stage,blocker_codes_json) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(release_id,body.release_key,body.version,Json(body.changed_components),Json(body.migration_ids),Json(body.evaluation_report_ids),Json(body.security_scan_ids),Json(body.performance_report_ids),Json(body.gate_results),body.rollback_plan_reference,body.incident_owner,"GATES_PASSED" if decision["passed"] else "BLOCKED","DEVELOPMENT",Json(decision["blockers"])))
        _publish(cur,"governance.release_candidate_created",release_id,{"release_id":release_id,"version":body.version,"status":"GATES_PASSED" if decision["passed"] else "BLOCKED"})
        conn.commit();return {"release_id":release_id,"gate_decision":decision}
    finally:_state["release_db"](conn)


@router.get("/api/v1/governance/releases")
def list_releases(request:Request)->dict[str,Any]:
    _admin(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("SELECT * FROM governance_release_candidates ORDER BY created_at DESC LIMIT 200");return {"releases":[_safe_row(dict(row),admin=True) for row in cur.fetchall()]}
    finally:_state["release_db"](conn)


@router.get("/api/v1/governance/releases/{release_id}")
def get_release(request:Request,release_id:str)->dict[str,Any]:
    _admin(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("SELECT * FROM governance_release_candidates WHERE id=%s",(release_id,));row=cur.fetchone()
        if not row:raise HTTPException(status_code=404,detail="Release not found")
        return {"release":_safe_row(dict(row),admin=True)}
    finally:_state["release_db"](conn)


class ReleaseApprovalBody(BaseModel):approver_role:str;decision:Literal["APPROVED","REJECTED"];comment:str|None=Field(default=None,max_length=1000)
@router.post("/api/v1/governance/releases/{release_id}/approve")
def approve_release(request:Request,release_id:str,body:ReleaseApprovalBody)->dict[str,Any]:
    admin=_admin(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("INSERT INTO governance_release_approvals(id,release_candidate_id,approver_role,approver_id,decision,comment) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(release_candidate_id,approver_role,approver_id) DO UPDATE SET decision=EXCLUDED.decision,comment=EXCLUDED.comment,created_at=now()",(str(uuid.uuid4()),release_id,body.approver_role,admin["email"],body.decision,body.comment));conn.commit();return {"ok":True,"decision":body.decision}
    finally:_state["release_db"](conn)


def _release_transition(request:Request,release_id:str,action:str)->dict[str,Any]:
    _admin(request);conn=_state["get_db"]()
    allowed={"evaluate":"EVALUATING","deploy-canary":"LIMITED_CANARY","expand":"EXPANDED_CANARY","pause":"PAUSED","rollback":"ROLLED_BACK"}
    try:
        cur=_cursor(conn);cur.execute("SELECT approval_status,blocker_codes_json FROM governance_release_candidates WHERE id=%s",(release_id,));row=cur.fetchone()
        if not row:raise HTTPException(status_code=404,detail="Release not found")
        if action in {"deploy-canary","expand"} and (row["approval_status"]!="GATES_PASSED" or row["blocker_codes_json"]):raise HTTPException(status_code=409,detail="release gates are not passed")
        stage=allowed[action]
        if action=="pause":
            cur.execute("UPDATE governance_release_candidates SET deployment_stage=%s,paused_at=now() WHERE id=%s",(stage,release_id))
        elif action=="rollback":
            cur.execute("UPDATE governance_release_candidates SET deployment_stage=%s,rolled_back_at=now() WHERE id=%s",(stage,release_id))
        else:
            cur.execute("UPDATE governance_release_candidates SET deployment_stage=%s WHERE id=%s",(stage,release_id))
        event={"deploy-canary":"governance.canary_started","expand":"governance.release_expanded","pause":"governance.canary_paused","rollback":"governance.release_rolled_back"}.get(action,"governance.release_gate_passed")
        _publish(cur,event,release_id,{"release_id":release_id,"status":stage});conn.commit();return {"ok":True,"stage":stage}
    finally:_state["release_db"](conn)


@router.post("/api/v1/governance/releases/{release_id}/evaluate")
def evaluate_release(request:Request,release_id:str):return _release_transition(request,release_id,"evaluate")
@router.post("/api/v1/governance/releases/{release_id}/deploy-canary")
def deploy_canary(request:Request,release_id:str):return _release_transition(request,release_id,"deploy-canary")
@router.post("/api/v1/governance/releases/{release_id}/expand")
def expand_release(request:Request,release_id:str):return _release_transition(request,release_id,"expand")
@router.post("/api/v1/governance/releases/{release_id}/pause")
def pause_release(request:Request,release_id:str):return _release_transition(request,release_id,"pause")
@router.post("/api/v1/governance/releases/{release_id}/rollback")
def rollback_release(request:Request,release_id:str):return _release_transition(request,release_id,"rollback")


@router.get("/api/v1/governance/kill-switches")
def list_kill_switches(request:Request)->dict[str,Any]:
    _admin(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("SELECT * FROM governance_kill_switches ORDER BY switch_key");return {"kill_switches":[_safe_row(dict(row),admin=True) for row in cur.fetchall()]}
    finally:_state["release_db"](conn)


class KillSwitchBody(BaseModel):reason_code:str=Field(min_length=3,max_length=100)
def _set_kill_switch(request:Request,switch_id:str,active:bool,body:KillSwitchBody)->dict[str,Any]:
    admin=_admin(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("SELECT * FROM governance_kill_switches WHERE id=%s",(switch_id,));row=cur.fetchone()
        if not row:raise HTTPException(status_code=404,detail="Kill switch not found")
        if active:cur.execute("UPDATE governance_kill_switches SET active=TRUE,reason_code=%s,activated_by=%s,activated_at=now(),updated_at=now() WHERE id=%s",(body.reason_code,admin["email"],switch_id))
        else:cur.execute("UPDATE governance_kill_switches SET active=FALSE,reason_code=%s,deactivated_by=%s,deactivated_at=now(),updated_at=now() WHERE id=%s",(body.reason_code,admin["email"],switch_id))
        cur.execute("INSERT INTO governance_kill_switch_audit(id,kill_switch_id,action,actor_id,reason_code,impact_scope_json) VALUES(%s,%s,%s,%s,%s,%s)",(str(uuid.uuid4()),switch_id,"ACTIVATE" if active else "DEACTIVATE",admin["email"],body.reason_code,Json(kill_switch_degradation(row["scope_reference"] or row["switch_key"]))))
        event="governance.kill_switch_activated" if active else "governance.kill_switch_deactivated";_publish(cur,event,switch_id,{"kill_switch_id":switch_id,"status":"ACTIVE" if active else "INACTIVE","reason_code":body.reason_code})
        conn.commit();return {"ok":True,"active":active,**kill_switch_degradation(row["scope_reference"] or row["switch_key"])}
    finally:_state["release_db"](conn)


@router.post("/api/v1/governance/kill-switches/{switch_id}/activate")
def activate_kill_switch(request:Request,switch_id:str,body:KillSwitchBody):return _set_kill_switch(request,switch_id,True,body)
@router.post("/api/v1/governance/kill-switches/{switch_id}/deactivate")
def deactivate_kill_switch(request:Request,switch_id:str,body:KillSwitchBody):return _set_kill_switch(request,switch_id,False,body)


@router.get("/api/v1/governance/data-quality")
def governance_data_quality(request:Request)->dict[str,Any]:
    _admin(request);platform=scan_platform_contracts();red_team=run_builtin_red_team();conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("SELECT severity,COUNT(*) count FROM governance_data_quality_issues WHERE status='OPEN' GROUP BY severity");counts={row["severity"]:row["count"] for row in cur.fetchall()}
        blockers=int(counts.get("HIGH",0))+int(counts.get("CRITICAL",0))
        return {"ok":platform["ok"] and red_team["pass"] and blockers==0,"platform_contracts":platform,"red_team":red_team,"open_issue_counts":counts,"publication_blockers":blockers}
    finally:_state["release_db"](conn)


@router.get("/api/v1/governance/data-quality/issues")
def list_quality_issues(request:Request)->dict[str,Any]:
    _admin(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("SELECT id,rule_id,affected_entity_type,affected_entity_reference,severity,status,redacted_details_json,detected_at,resolved_at FROM governance_data_quality_issues ORDER BY detected_at DESC LIMIT 300");return {"issues":[dict(row) for row in cur.fetchall()]}
    finally:_state["release_db"](conn)


@router.get("/api/v1/governance/data-quality/issues/{issue_id}")
def get_quality_issue(request:Request,issue_id:str)->dict[str,Any]:
    _admin(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("SELECT id,rule_id,affected_entity_type,affected_entity_reference,severity,status,redacted_details_json,detected_at,resolved_at FROM governance_data_quality_issues WHERE id=%s",(issue_id,));row=cur.fetchone()
        if not row:raise HTTPException(status_code=404,detail="Quality issue not found")
        return {"issue":dict(row)}
    finally:_state["release_db"](conn)


@router.post("/api/v1/governance/data-quality/issues/{issue_id}/remediate")
def remediate_quality_issue(request:Request,issue_id:str)->dict[str,Any]:
    _admin(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("UPDATE governance_data_quality_issues SET status='RESOLVED',resolved_at=now() WHERE id=%s",(issue_id,));_publish(cur,"governance.data_quality_issue_resolved",issue_id,{"issue_id":issue_id,"status":"RESOLVED"});conn.commit();return {"ok":bool(cur.rowcount)}
    finally:_state["release_db"](conn)


@router.get("/api/v1/governance/slo")
def get_slo(request:Request)->dict[str,Any]:
    _admin(request);return {"targets":SLO_TARGETS,"non_budgetable_safety_errors":["CROSS_TENANT_ACCESS","AUTOMATIC_THIRD_PARTY_SHARE","DIVINE_ORACLE","CRISIS_MISSED_ROUTE","SENSITIVE_LOG_LEAK"]}


@router.get("/api/v1/governance/cost-routing/{task_family}")
def get_cost_route(request:Request,task_family:str,budget_exceeded:bool=False,crisis_related:bool=False)->dict[str,str]:
    _admin(request);return cost_route(task_family,budget_exceeded=budget_exceeded,crisis_related=crisis_related)


class CanaryCheckBody(BaseModel):subject_reference:str;release_key:str;percentage:int=Field(ge=0,le=100);selector_fields:list[str]=Field(default_factory=list);opt_in:bool=False
@router.post("/api/v1/governance/canary/check")
def check_canary(request:Request,body:CanaryCheckBody)->dict[str,Any]:
    _require_feature("canary");_admin(request)
    try:validate_canary_selector(body.selector_fields)
    except ValueError as exc:raise HTTPException(status_code=422,detail=str(exc)) from exc
    return {"selected":canary_bucket(subject_reference=body.subject_reference,release_key=body.release_key,percentage=body.percentage,opt_in=body.opt_in),"selection_method":"OPT_IN" if body.opt_in else "NON_SENSITIVE_STABLE_HASH"}


class IncidentBody(BaseModel):incident_key:str;incident_type:str;severity:str;affected_components:list[str]=Field(default_factory=list);affected_tenant_count:int=Field(default=0,ge=0);incident_owner:str
@router.post("/api/v1/governance/incidents")
def create_incident(request:Request,body:IncidentBody)->dict[str,Any]:
    _admin(request);conn=_state["get_db"]();incident_id=str(uuid.uuid4())
    try:
        cur=_cursor(conn);cur.execute("INSERT INTO governance_incidents(id,incident_key,incident_type,severity,affected_components_json,affected_tenant_count,incident_owner) VALUES(%s,%s,%s,%s,%s,%s,%s)",(incident_id,body.incident_key,body.incident_type,body.severity,Json(body.affected_components),body.affected_tenant_count,body.incident_owner));_publish(cur,"governance.incident_created",incident_id,{"incident_id":incident_id,"status":"DETECTED","severity":body.severity});conn.commit();return {"incident_id":incident_id,"status":"DETECTED"}
    finally:_state["release_db"](conn)


@router.get("/api/v1/governance/incidents")
def list_incidents(request:Request)->dict[str,Any]:
    _admin(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("SELECT id,incident_key,incident_type,severity,affected_components_json,affected_tenant_count,status,incident_owner,containment_actions_json,postmortem_reference,detected_at,contained_at,resolved_at FROM governance_incidents ORDER BY detected_at DESC LIMIT 200");return {"incidents":[dict(row) for row in cur.fetchall()]}
    finally:_state["release_db"](conn)


@router.get("/api/v1/governance/incidents/{incident_id}")
def get_incident(request:Request,incident_id:str)->dict[str,Any]:
    _admin(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("SELECT id,incident_key,incident_type,severity,affected_components_json,affected_tenant_count,status,incident_owner,containment_actions_json,postmortem_reference,detected_at,contained_at,resolved_at FROM governance_incidents WHERE id=%s",(incident_id,));row=cur.fetchone()
        if not row:raise HTTPException(status_code=404,detail="Incident not found")
        return {"incident":dict(row)}
    finally:_state["release_db"](conn)


class IncidentActionBody(BaseModel):actions:list[str]=Field(default_factory=list,max_length=20);postmortem_reference:str|None=Field(default=None,max_length=500)
def _incident_transition(request:Request,incident_id:str,action:str,body:IncidentActionBody)->dict[str,Any]:
    _admin(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn)
        if action=="contain":cur.execute("UPDATE governance_incidents SET status='CONTAINED',containment_actions_json=%s,contained_at=now() WHERE id=%s",(Json(body.actions),incident_id));event="governance.incident_contained";status="CONTAINED"
        elif action=="resolve":cur.execute("UPDATE governance_incidents SET status='RESOLVED',resolved_at=now() WHERE id=%s",(incident_id,));event="governance.incident_resolved";status="RESOLVED"
        else:
            if not body.postmortem_reference:raise HTTPException(status_code=422,detail="postmortem reference required")
            cur.execute("UPDATE governance_incidents SET postmortem_reference=%s WHERE id=%s",(body.postmortem_reference,incident_id));event="governance.postmortem_published";status="POSTMORTEM_PUBLISHED"
        _publish(cur,event,incident_id,{"incident_id":incident_id,"status":status});conn.commit();return {"ok":bool(cur.rowcount),"status":status}
    finally:_state["release_db"](conn)


@router.post("/api/v1/governance/incidents/{incident_id}/contain")
def contain_incident(request:Request,incident_id:str,body:IncidentActionBody):return _incident_transition(request,incident_id,"contain",body)
@router.post("/api/v1/governance/incidents/{incident_id}/resolve")
def resolve_incident(request:Request,incident_id:str,body:IncidentActionBody):return _incident_transition(request,incident_id,"resolve",body)
@router.post("/api/v1/governance/incidents/{incident_id}/publish-postmortem")
def publish_postmortem(request:Request,incident_id:str,body:IncidentActionBody):return _incident_transition(request,incident_id,"postmortem",body)


@router.get("/api/v1/compliance/data-map")
def compliance_data_map(request:Request)->dict[str,Any]:
    _require_feature("compliance");_user(request)
    return {**processing_transparency(),"data_categories":[
        {"category":"用户主动记录","purpose":"形成可核对时间线","retention":"由用户设置","sharing":"默认不分享"},
        {"category":"派生状态与模式","purpose":"镜像与回顾","retention":"生命周期和删除传播","sharing":"仅按 Consent 投影"},
        {"category":"有限 Scenario","purpose":"比较短期可能性","retention":"默认 60 天","sharing":"默认不分享"},
        {"category":"访问与安全审计","purpose":"安全与用户权利","retention":"独立政策","sharing":"不含正文"},
    ]}


@router.get("/api/v1/compliance/processing-activities")
def processing_activities(request:Request)->dict[str,Any]:
    _user(request);return {"activities":[
        {"capability":"主动记录","processing":"RULE_ONLY","opt_out":False},
        {"capability":"情绪与形成候选","processing":"OPTIONAL_MODEL_AND_RULE","opt_out":True},
        {"capability":"有限 Scenario","processing":"RULE_ONLY","opt_out":True},
        {"capability":"关系分享","processing":"UNAVAILABLE_UNTIL_BATCH_08","opt_out":True},
    ]}


@router.get("/api/v1/compliance/third-parties")
def third_parties(request:Request)->dict[str,Any]:
    _user(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("SELECT provider_key,service_type,data_categories_json,processing_purposes_json,data_regions_json,retention_terms,training_usage_policy,subprocessor_reference,security_review_status,approved,review_due_at FROM governance_third_party_processors WHERE approved=TRUE ORDER BY provider_key");return {"third_parties":[dict(row) for row in cur.fetchall()]}
    finally:_state["release_db"](conn)


def _create_rights_request(request:Request,request_type:str,scope:dict[str,Any])->dict[str,Any]:
    email=_user(request)["email"].lower();tenant,profile=_identity(email);conn=_state["get_db"]();request_id=str(uuid.uuid4())
    try:
        RightsRequestSpec(request_type=request_type,scope=scope);cur=_cursor(conn);_owner(cur,email)
        immediate=request_type in {"RESTRICT_PROCESSING","OBJECT_TO_MODEL_PROCESSING","DISABLE_PROFILING","DISABLE_RELATIONAL_SHARING"}
        cur.execute("INSERT INTO compliance_rights_requests(id,tenant_id,subject_user_id,email,request_type,scope_json,status,access_restricted_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",(request_id,tenant,profile,email,request_type,Json(scope),"PROCESSING_RESTRICTED" if immediate else "REQUESTED",datetime.now(timezone.utc) if immediate else None))
        event="compliance.processing_restricted" if immediate else "compliance.rights_request_created";_publish(cur,event,email,{"request_id":request_id,"request_type":request_type,"status":"PROCESSING_RESTRICTED" if immediate else "REQUESTED"})
        conn.commit();return {"request_id":request_id,"status":"PROCESSING_RESTRICTED" if immediate else "REQUESTED"}
    finally:_state["release_db"](conn)


@router.post("/api/v1/compliance/requests/export")
def request_export(request:Request,scope:dict[str,Any]|None=None):return _create_rights_request(request,"EXPORT_DATA",scope or {})
@router.post("/api/v1/compliance/requests/delete")
def request_delete(request:Request,scope:dict[str,Any]|None=None):return _create_rights_request(request,"DELETE_DATA",scope or {})
@router.post("/api/v1/compliance/requests/restrict")
def request_restrict(request:Request,scope:dict[str,Any]|None=None):return _create_rights_request(request,"RESTRICT_PROCESSING",scope or {})
@router.post("/api/v1/compliance/requests/object-to-profiling")
def object_to_profiling(request:Request,scope:dict[str,Any]|None=None):return _create_rights_request(request,"OBJECT_TO_MODEL_PROCESSING",scope or {})


@router.get("/api/v1/compliance/requests/{request_id}")
def get_rights_request(request:Request,request_id:str)->dict[str,Any]:
    email=_user(request)["email"].lower();conn=_state["get_db"]()
    try:
        cur=_cursor(conn);_owner(cur,email);cur.execute("SELECT * FROM compliance_rights_requests WHERE email=%s AND id=%s AND deleted_at IS NULL",(email,request_id));row=cur.fetchone()
        if not row:raise HTTPException(status_code=404,detail="Rights request not found")
        return {"request":_safe_row(dict(row))}
    finally:_state["release_db"](conn)


@router.get("/api/v1/compliance/system-status")
def user_system_status(request:Request)->dict[str,Any]:
    _user(request);conn=_state["get_db"]()
    try:
        cur=_cursor(conn);cur.execute("SELECT switch_key,scope_reference,active,reason_code,updated_at FROM governance_kill_switches ORDER BY switch_key")
        switches=[dict(row) for row in cur.fetchall()]
        return {"status":"DEGRADED" if any(item["active"] for item in switches) else "AVAILABLE","feature_flags":{key:_enabled(key) for key in FEATURE_FLAGS},"kill_switches":switches,"batch_08_relational_collaboration":"NOT_AVAILABLE","notices":processing_transparency()["notices"]}
    finally:_state["release_db"](conn)


# ═════════════════════════════════════════════════════════════════════════════
# EMD-OS Batch 10 — emotional maturity production certification (/api/v1/assurance/emd)
#
# These routes are governance surfaces for the Emotional Maturity Diagnostic OS.
# They return technical evidence only: no user Formation Twin content, no prompt
# bodies, no incident identity lists.
# ═════════════════════════════════════════════════════════════════════════════

class EmdIntendedUseBody(BaseModel):
    release_id: str = Field(min_length=1, max_length=60)
    requested_features: list[str] = Field(default_factory=list, max_length=20)
    target_users: list[str] = Field(default_factory=list, max_length=10)
    deployment_regions: list[str] = Field(default_factory=list, max_length=20)
    data_categories: list[str] = Field(default_factory=list, max_length=20)
    external_actions: list[str] = Field(default_factory=list, max_length=10)
    sharing_modes: list[str] = Field(default_factory=list, max_length=10)
    stated_purposes: list[str] = Field(default_factory=list, max_length=10)


class EmdPsychometricBody(BaseModel):
    release_id: str = Field(min_length=1, max_length=60)
    instrument_version: str = Field(min_length=1, max_length=40)
    interpretation_claims: list[str] = Field(default_factory=list, max_length=10)
    content_expert_agreement: float | None = Field(default=None, ge=0, le=1)
    inter_rater_agreement: float | None = Field(default=None, ge=0, le=1)
    pilot_sample_per_locale: dict[str, int] = Field(default_factory=dict)
    cognitive_interviews_per_locale: dict[str, int] = Field(default_factory=dict)
    retest_reliability: float | None = Field(default=None, ge=0, le=1)
    responsiveness_days: int = Field(default=0, ge=0)
    self_report_only: bool = False


class EmdDataQualityBody(BaseModel):
    release_id: str = Field(min_length=1, max_length=60)
    findings: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    duplicate_real_event_rate: float = Field(default=0.0, ge=0, le=1)
    open_response_double_scored: float = Field(default=0.0, ge=0, le=1)
    critical_field_validity: float = Field(default=1.0, ge=0, le=1)


class EmdFairnessBody(BaseModel):
    release_id: str = Field(min_length=1, max_length=60)
    group_samples: dict[str, int] = Field(default_factory=dict)
    measurement_findings: list[dict[str, Any]] = Field(default_factory=list, max_length=30)
    safety_findings: list[dict[str, Any]] = Field(default_factory=list, max_length=30)
    hard_block_codes: list[str] = Field(default_factory=list, max_length=10)
    accessibility_passed: bool = True


class EmdDomainSafetyBody(BaseModel):
    release_id: str = Field(min_length=1, max_length=60)
    case_results: list[dict[str, Any]] = Field(default_factory=list, max_length=500)
    human_review_roles: list[str] = Field(default_factory=list, max_length=12)
    conflicted_reviewers: list[str] = Field(default_factory=list, max_length=10)


class EmdPrivacyBody(BaseModel):
    release_id: str = Field(min_length=1, max_length=60)
    data_inventory_complete: bool = False
    consent_matrix: dict[str, list[str]] = Field(default_factory=dict)
    retention_policies: dict[str, str] = Field(default_factory=dict)
    deletion_targets_covered: list[str] = Field(default_factory=list, max_length=20)
    model_training_default_on: bool = False
    cross_border_flows: list[str] = Field(default_factory=list, max_length=10)
    role_based_pastor_access: bool = False
    rights_supported: list[str] = Field(default_factory=list, max_length=10)


class EmdRedTeamBody(BaseModel):
    release_id: str = Field(min_length=1, max_length=60)
    attack_results: list[dict[str, Any]] = Field(default_factory=list, max_length=500)
    tool_permission_manifest: dict[str, str] = Field(default_factory=dict)


class EmdChangeBody(BaseModel):
    change_request_id: str = Field(min_length=1, max_length=80)
    current_release: str = Field(min_length=1, max_length=60)
    proposed_release: str = Field(min_length=1, max_length=60)
    changes: list[dict[str, Any]] = Field(default_factory=list, max_length=30)
    requested_change_level: str = "PATCH"


class EmdCertifyBody(BaseModel):
    release_id: str = Field(min_length=1, max_length=60)
    product_version: str = "0.1.0"
    intended_use_tier: str
    requested_release_level: str
    supported_locales: list[str] = Field(default_factory=list, max_length=12)
    deployment_jurisdictions: list[str] = Field(default_factory=list, max_length=12)
    gate_results: dict[str, str] = Field(default_factory=dict)
    obtained_signoffs: list[str] = Field(default_factory=list, max_length=12)
    known_limitations: list[str] = Field(default_factory=list, max_length=20)
    residual_risks: list[str] = Field(default_factory=list, max_length=20)
    valid_days: int = Field(default=90, ge=1, le=365)


class EmdIncidentBody(BaseModel):
    incident_id: str = Field(min_length=1, max_length=80)
    incident_type: str = Field(min_length=1, max_length=48)
    affected_release: str = Field(min_length=1, max_length=60)
    affected_users: int = Field(default=0, ge=0)
    affected_records: int = Field(default=0, ge=0)


def _emd_record_gate(cur, release_id: str, gate_code: str, report_id: str, status: str, summary: dict[str, Any]) -> None:
    blocking = gate_code in emd_certification.BLOCKING_GATES
    cur.execute(
        "INSERT INTO production_emd_gate_reports"
        "(id,release_id,gate_code,report_id,status,blocking,summary_json)"
        "VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(release_id,gate_code,report_id) DO NOTHING",
        (str(uuid.uuid4()), release_id, gate_code, report_id, status, blocking,
         Json(sanitize_governance_metadata(summary))),
    )


@router.get("/api/v1/assurance/emd/overview")
def emd_assurance_overview(request: Request) -> dict[str, Any]:
    _admin(request)
    return {"ok": True, **emd_certification.describe_certification_engine()}


@router.post("/api/v1/assurance/emd/classify-use")
def emd_classify_use(request: Request, body: EmdIntendedUseBody) -> dict[str, Any]:
    admin = _admin(request)
    result = emd_certification.classify_intended_use(
        release_id=body.release_id,
        requested_features=body.requested_features,
        target_users=body.target_users,
        deployment_regions=body.deployment_regions,
        data_categories=body.data_categories,
        external_actions=body.external_actions,
        sharing_modes=body.sharing_modes,
        stated_purposes=body.stated_purposes,
    )
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, admin["email"])
            cur.execute(
                "INSERT INTO production_emd_intended_use_profiles"
                "(id,release_id,classification_id,status,intended_use_tier,maximum_certifiable_level,"
                "risk_factors_json,hard_blocks_json,prohibited_uses_json)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), body.release_id, result["classification_id"], result["status"],
                 result["intended_use_tier"], result.get("maximum_certifiable_level"),
                 Json(result.get("risk_factors") or []), Json(result.get("hard_blocks") or []),
                 Json(result.get("prohibited_uses") or [])),
            )
            _emd_record_gate(
                cur, body.release_id, "G0_INTENDED_USE", result["classification_id"],
                "PASS" if result["status"] == "CLASSIFIED" else "BLOCKED",
                {"tier": result["intended_use_tier"]},
            )
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/api/v1/assurance/emd/psychometric-review")
def emd_psychometric_review(request: Request, body: EmdPsychometricBody) -> dict[str, Any]:
    admin = _admin(request)
    result = emd_certification.govern_psychometric_evidence(
        instrument_version=body.instrument_version,
        interpretation_claims=body.interpretation_claims,
        content_expert_agreement=body.content_expert_agreement,
        inter_rater_agreement=body.inter_rater_agreement,
        pilot_sample_per_locale=body.pilot_sample_per_locale,
        cognitive_interviews_per_locale=body.cognitive_interviews_per_locale,
        retest_reliability=body.retest_reliability,
        responsiveness_days=body.responsiveness_days,
        self_report_only=body.self_report_only,
    )
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, admin["email"])
            _emd_record_gate(
                cur, body.release_id, "G1_PSYCHOMETRIC", result["psychometric_governance_id"],
                "PASS_WITH_RESTRICTIONS" if result["restricted_interpretations"] else "PASS",
                {"evidence_level": result["evidence_level"], "recommendation": result["release_recommendation"]},
            )
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/api/v1/assurance/emd/data-quality-audit")
def emd_data_quality_audit(request: Request, body: EmdDataQualityBody) -> dict[str, Any]:
    admin = _admin(request)
    result = emd_certification.audit_data_quality(
        release_id=body.release_id,
        findings=body.findings,
        duplicate_real_event_rate=body.duplicate_real_event_rate,
        open_response_double_scored=body.open_response_double_scored,
        critical_field_validity=body.critical_field_validity,
    )
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, admin["email"])
            _emd_record_gate(
                cur, body.release_id, "G2_DATA_QUALITY", result["data_quality_report_id"],
                result["status"], {"critical": len(result["critical_findings"])},
            )
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/api/v1/assurance/emd/fairness-audit")
def emd_fairness_audit(request: Request, body: EmdFairnessBody) -> dict[str, Any]:
    admin = _admin(request)
    result = emd_certification.audit_fairness(
        release_id=body.release_id,
        group_samples=body.group_samples,
        measurement_findings=body.measurement_findings,
        safety_findings=body.safety_findings,
        hard_block_codes=body.hard_block_codes,
        accessibility_passed=body.accessibility_passed,
    )
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, admin["email"])
            _emd_record_gate(
                cur, body.release_id, "G3_FAIRNESS", result["fairness_report_id"],
                result["status"], {"blocked_scope": len(result["blocked_scope"])},
            )
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/api/v1/assurance/emd/domain-safety")
def emd_domain_safety(request: Request, body: EmdDomainSafetyBody) -> dict[str, Any]:
    admin = _admin(request)
    result = emd_certification.certify_domain_safety(
        release_id=body.release_id,
        case_results=body.case_results,
        human_review_roles=body.human_review_roles,
        conflicted_reviewers=body.conflicted_reviewers,
    )
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, admin["email"])
            _emd_record_gate(
                cur, body.release_id, "G4_DOMAIN_SAFETY", result["domain_safety_report_id"],
                result["status"], {"critical_failures": result["case_summary"]["critical_failures"]},
            )
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/api/v1/assurance/emd/privacy-assessment")
def emd_privacy_assessment(request: Request, body: EmdPrivacyBody) -> dict[str, Any]:
    admin = _admin(request)
    try:
        result = emd_certification.assess_privacy(
            release_id=body.release_id,
            data_inventory_complete=body.data_inventory_complete,
            consent_matrix=body.consent_matrix,
            retention_policies=body.retention_policies,
            deletion_targets_covered=body.deletion_targets_covered,
            model_training_default_on=body.model_training_default_on,
            cross_border_flows=body.cross_border_flows,
            role_based_pastor_access=body.role_based_pastor_access,
            rights_supported=body.rights_supported,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, admin["email"])
            _emd_record_gate(
                cur, body.release_id, "G5_PRIVACY", result["privacy_assessment_id"],
                result["status"], {"blocks": len(result["blocks"])},
            )
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/api/v1/assurance/emd/security-redteam")
def emd_security_redteam(request: Request, body: EmdRedTeamBody) -> dict[str, Any]:
    admin = _admin(request)
    try:
        result = emd_certification.orchestrate_red_team(
            release_id=body.release_id,
            attack_results=body.attack_results,
            tool_permission_manifest=body.tool_permission_manifest,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, admin["email"])
            _emd_record_gate(
                cur, body.release_id, "G6_LLM_SECURITY", result["security_red_team_report_id"],
                result["status"], {"successful_attacks": result["attack_summary"]["successful_attacks"]},
            )
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/api/v1/assurance/emd/changes")
def emd_change_control(request: Request, body: EmdChangeBody) -> dict[str, Any]:
    admin = _admin(request)
    try:
        result = emd_certification.control_change(
            change_request_id=body.change_request_id,
            current_release=body.current_release,
            proposed_release=body.proposed_release,
            changes=body.changes,
            requested_change_level=body.requested_change_level,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, admin["email"])
            cur.execute(
                "INSERT INTO production_emd_change_controls"
                "(id,change_control_id,change_request_id,current_release,proposed_release,"
                "requested_change_level,actual_change_level,reasons_json,required_retests_json,"
                "invalidated_certificates_json)VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), result["change_control_id"], body.change_request_id,
                 body.current_release, body.proposed_release, body.requested_change_level,
                 result["actual_change_level"], Json(result["reasons"]),
                 Json(result["required_retests"]), Json(result["invalidated_certificates"])),
            )
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/api/v1/assurance/emd/certify")
def emd_certify(request: Request, body: EmdCertifyBody) -> dict[str, Any]:
    admin = _admin(request)
    try:
        dossier = emd_certification.CertificationDossier(
            release_id=body.release_id,
            product_version=body.product_version,
            intended_use_tier=body.intended_use_tier,
            requested_release_level=body.requested_release_level,
            supported_locales=body.supported_locales,
            deployment_jurisdictions=body.deployment_jurisdictions,
            gate_results=body.gate_results,
            obtained_signoffs=body.obtained_signoffs,
            known_limitations=body.known_limitations,
            residual_risks=body.residual_risks,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = emd_certification.certify_release(dossier, valid_days=body.valid_days)
    status_map = {
        "GO": result.get("certified_level") or "NOT_EVALUATED",
        "PASS_WITH_RESTRICTIONS": result.get("certified_level") or "RESTRICTED_PILOT",
        "NO_GO": "NOT_EVALUATED",
    }
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, admin["email"])
            cur.execute(
                "INSERT INTO production_emd_release_certificates"
                "(id,certificate_id,release_id,product_version,intended_use_tier,certified_level,decision,"
                "certificate_status,supported_locales_json,deployment_jurisdictions_json,restricted_gates_json,"
                "known_limitations_json,residual_risks_json,obtained_signoffs_json,"
                "required_runtime_controls_json,valid_from,expires_at)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()), result["certificate_id"], body.release_id, body.product_version,
                 body.intended_use_tier, result.get("certified_level"), result["decision"],
                 status_map[result["decision"]], Json(body.supported_locales),
                 Json(body.deployment_jurisdictions), Json(result.get("restricted_gates") or []),
                 Json(body.known_limitations), Json(body.residual_risks), Json(body.obtained_signoffs),
                 Json(result.get("required_runtime_controls") or []),
                 result.get("valid_from"), result.get("expires_at")),
            )
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/api/v1/assurance/emd/incidents")
def emd_incident(request: Request, body: EmdIncidentBody) -> dict[str, Any]:
    admin = _admin(request)
    try:
        result = emd_certification.respond_to_incident(
            incident_id=body.incident_id,
            incident_type=body.incident_type,
            affected_release=body.affected_release,
            affected_users=body.affected_users,
            affected_records=body.affected_records,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    conn = _state["get_db"]()
    try:
        with _cursor(conn) as cur:
            _owner(cur, admin["email"])
            cur.execute(
                "INSERT INTO production_emd_incidents"
                "(id,incident_id,incident_response_id,incident_type,severity,affected_release,"
                "affected_users,affected_records,immediate_actions_json,kill_switches_json,"
                "certificate_action,recall_plan_json,user_notification_required,recertification_required)"
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT(incident_id) DO NOTHING",
                (str(uuid.uuid4()), body.incident_id, result["incident_response_id"],
                 result["incident_type"], result["severity"], body.affected_release,
                 body.affected_users, body.affected_records, Json(result["immediate_actions"]),
                 Json(result["kill_switches"]), result["certificate_action"],
                 Json(result["recall_plan"]), result["user_notification_required"],
                 result["recertification_required"]),
            )
            if result["certificate_action"] in {"SUSPENDED", "REVOKED"}:
                cur.execute(
                    "UPDATE production_emd_release_certificates SET certificate_status=%s "
                    "WHERE release_id=%s AND certificate_status NOT IN ('REVOKED','EXPIRED')",
                    (result["certificate_action"], body.affected_release),
                )
            conn.commit()
        return {"ok": True, **result}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


# ── EMD-OS 保障配置档与可执行清单 ─────────────────────────────────────────────

class EmdChecklistBody(BaseModel):
    profile: str = "PILOT"
    completed_ids: list[str] = Field(default_factory=list, max_length=30)


@router.get("/api/v1/assurance/emd/profiles")
def emd_assurance_profiles(request: Request) -> dict[str, Any]:
    _admin(request)
    return {"ok": True, **emd_assurance_profiles_module.describe_profiles()}


@router.post("/api/v1/assurance/emd/checklist")
def emd_assurance_checklist(request: Request, body: EmdChecklistBody) -> dict[str, Any]:
    _admin(request)
    try:
        return {
            "ok": True,
            **emd_assurance_profiles_module.generate_checklist(
                profile=body.profile, completed_ids=body.completed_ids
            ),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
