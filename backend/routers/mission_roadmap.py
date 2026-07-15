"""Read-only, evidence-backed Mission OS roadmap projection."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from core.tenancy import require_org_permission
from mission_bridge_auth import set_tenant_context
from mission_feature_guard import require_mission_os
from mission_os.roadmap import build_roadmap


router = APIRouter(
    prefix="/api/v1/mission/roadmap",
    tags=["mission-roadmap"],
    dependencies=[Depends(require_mission_os)],
)
_state = {}


def init_mission_roadmap_router(*, get_db, release_db, get_session_user, is_admin):
    _state.update(locals())


def _user(request):
    user = _state["get_session_user"](request)
    email = str((user or {}).get("email") or "")
    if not email:
        raise HTTPException(401, detail="请先登录")
    return email


def _one(cur, query, params, default=None):
    cur.execute(query, params)
    row = cur.fetchone()
    return row if row is not None else default


@router.get("")
def get_roadmap(organizationId: str, request: Request):
    email = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if not _state["is_admin"](email):
                require_org_permission(cur, email, organizationId, "view_dashboard")
            set_tenant_context(cur, organizationId)

            journey = _one(
                cur,
                "SELECT id,journey_status FROM mission_calling_journeys "
                "WHERE tenant_id=%s AND user_id=%s ORDER BY started_at DESC LIMIT 1",
                (organizationId, email),
            )
            worker = _one(
                cur,
                "SELECT id FROM mission_worker_profiles WHERE tenant_id=%s AND user_id=%s LIMIT 1",
                (organizationId, email),
            )
            worker_id = str(worker[0]) if worker else None
            journey_id = str(journey[0]) if journey else None

            facts = {
                "calling": {}, "readiness": {}, "training": {}, "sending": {},
                "team": {}, "preparation": {}, "gate": {},
            }
            if journey:
                reflection_count = _one(cur, "SELECT count(*) FROM mission_calling_reflections WHERE tenant_id=%s AND calling_journey_id=%s", (organizationId, journey_id), (0,))[0]
                evidence = _one(cur, "SELECT count(*),bool_or(evidence_type IN ('church_feedback','mentor_feedback')) FROM mission_calling_evidence WHERE tenant_id=%s AND calling_journey_id=%s", (organizationId, journey_id), (0, False))
                hard_blocks = _one(cur, "SELECT count(*) FROM mission_calling_blockers WHERE tenant_id=%s AND calling_journey_id=%s AND severity='hard_block' AND status<>'cleared'", (organizationId, journey_id), (0,))[0]
                facts["calling"] = {
                    "id": journey_id, "status": journey[1], "reflections": int(reflection_count),
                    "evidence": int(evidence[0]), "hasCommunityEvidence": bool(evidence[1]),
                    "hardBlocks": int(hard_blocks),
                }

            sending_journey_id = None
            if worker_id:
                readiness = _one(cur, "SELECT id,assessment_status,readiness_level FROM mission_readiness_assessments WHERE tenant_id=%s AND worker_profile_id=%s ORDER BY created_at DESC LIMIT 1", (organizationId, worker_id))
                if readiness:
                    dimensions = _one(cur, "SELECT count(*) FROM mission_readiness_dimensions WHERE tenant_id=%s AND assessment_id=%s AND final_level IS NOT NULL", (organizationId, str(readiness[0])), (0,))[0]
                    facts["readiness"] = {"id": str(readiness[0]), "status": readiness[1], "level": readiness[2], "dimensions": int(dimensions)}

                training = _one(cur, "SELECT id,plan_status FROM mission_training_plans WHERE tenant_id=%s AND worker_profile_id=%s ORDER BY created_at DESC LIMIT 1", (organizationId, worker_id))
                if training:
                    modules = _one(cur, "SELECT count(*) FILTER (WHERE requirement_level='required'),count(*) FILTER (WHERE requirement_level='required' AND status='completed') FROM mission_training_plan_modules WHERE tenant_id=%s AND training_plan_id=%s", (organizationId, str(training[0])), (0, 0))
                    gaps = _one(cur, "SELECT count(*) FROM mission_training_plan_gaps WHERE tenant_id=%s AND training_plan_id=%s AND blocking=TRUE AND status<>'closed'", (organizationId, str(training[0])), (0,))[0]
                    facts["training"] = {"id": str(training[0]), "status": training[1], "requiredModules": int(modules[0]), "completedModules": int(modules[1]), "blockingGaps": int(gaps)}

                application = _one(cur, "SELECT id,sending_journey_id,application_status FROM mission_candidate_applications WHERE tenant_id=%s AND worker_profile_id=%s ORDER BY created_at DESC LIMIT 1", (organizationId, worker_id))
                if application:
                    sending_journey_id = application[1]
                    decision = _one(cur, "SELECT decision_type FROM mission_sending_decisions WHERE tenant_id=%s AND application_id=%s ORDER BY created_at DESC LIMIT 1", (organizationId, str(application[0])))
                    facts["sending"] = {"applicationId": str(application[0]), "applicationStatus": application[2], "decision": decision[0] if decision else None}

                membership = _one(cur, "SELECT membership_stage FROM mission_team_memberships WHERE tenant_id=%s AND worker_profile_id=%s ORDER BY created_at DESC LIMIT 1", (organizationId, worker_id))
                partners = _one(cur, "SELECT count(*),count(*) FILTER (WHERE profile_status IN ('approved_for_limited_collaboration','approved','conditional')) FROM mission_local_partner_profiles WHERE tenant_id=%s", (organizationId,), (0, 0))
                facts["team"] = {"membershipStatus": membership[0] if membership else None, "partners": int(partners[0]), "approvedPartners": int(partners[1])}

                identity = _one(cur, "SELECT path_status FROM mission_legal_identity_paths WHERE tenant_id=%s AND worker_profile_id=%s ORDER BY created_at DESC LIMIT 1", (organizationId, worker_id))
                finance = _one(cur, "SELECT plan_status FROM mission_financial_plans WHERE tenant_id=%s AND worker_profile_id=%s ORDER BY created_at DESC LIMIT 1", (organizationId, worker_id))
                household = _one(cur, "SELECT id FROM mission_households WHERE tenant_id=%s AND worker_profile_id=%s ORDER BY created_at DESC LIMIT 1", (organizationId, worker_id))
                family = _one(cur, "SELECT plan_status FROM mission_family_readiness_plans WHERE tenant_id=%s AND household_id=%s ORDER BY created_at DESC LIMIT 1", (organizationId, str(household[0]))) if household else None
                compliance = _one(cur, "SELECT case_status FROM mission_compliance_cases WHERE tenant_id=%s AND sending_journey_id=%s ORDER BY created_at DESC LIMIT 1", (organizationId, sending_journey_id)) if sending_journey_id else None
                facts["preparation"] = {
                    "identityStatus": identity[0] if identity else None,
                    "financeStatus": finance[0] if finance else None,
                    "familyStatus": family[0] if family else None,
                    "complianceStatus": compliance[0] if compliance else None,
                }

            if sending_journey_id:
                gate = _one(cur, "SELECT gate_status,blocking_findings FROM mission_deployment_readiness_gates WHERE tenant_id=%s AND sending_journey_id=%s ORDER BY created_at DESC LIMIT 1", (organizationId, sending_journey_id))
                if gate:
                    facts["gate"] = {"status": gate[0], "blockingFindings": gate[1] or []}
    finally:
        _state["release_db"](conn)

    roadmap = build_roadmap(facts)
    roadmap["organizationId"] = organizationId
    roadmap["workerProfileId"] = worker_id
    return {"ok": True, "roadmap": roadmap}
