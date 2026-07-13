"""Skill 50/52/53 API: church confirmation, candidate application and committee decision."""
from __future__ import annotations
import json
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from core.tenancy import require_org_permission
from mission_bridge_auth import set_tenant_context
from mission_feature_guard import require_mission_feature
from mission_os.audit import audit
from mission_os.outbox import enqueue
from mission_os.sending import (
    assert_church_confirmation_valid, assert_can_submit, requires_new_version,
    assert_quorum, assert_can_approve, validate_conditional_approval, approval_unlocks_batch6_only,
)

router = APIRouter(prefix='/api/v1/mission/sending', tags=['mission-sending'], dependencies=[Depends(require_mission_feature('mission_sending_enabled'))])
_state = {}


def init_mission_sending_router(*, get_db, release_db, get_session_user, is_admin):
    _state.update(locals())


def _user(request):
    user = _state['get_session_user'](request)
    email = str((user or {}).get('email') or '')
    if not email:
        raise HTTPException(401, detail='请先登录')
    return user, email


def _role(cur, email, org_id):
    if _state['is_admin'](email):
        return 'platform_admin'
    return require_org_permission(cur, email, org_id, 'manage_settings')['role']


class ChurchConfirmBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    churchOrganizationId: str = Field(min_length=1)
    reviewerIds: list[str] = Field(default_factory=list)
    familyReviewerIds: list[str] = Field(default_factory=list)
    observationMonths: int = Field(ge=0, le=600)
    supportLevel: Literal['unable_to_confirm', 'insufficient_observation', 'support_exploration', 'support_with_conditions', 'support_sending_process', 'recommend_pause']


@router.post('/church-confirmations')
def create_church_confirmation(body: ChurchConfirmBody, request: Request):
    _user_obj, email = _user(request)
    try:
        assert_church_confirmation_valid(reviewer_ids=body.reviewerIds, family_reviewer_ids=body.familyReviewerIds,
                                         observation_months=body.observationMonths)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute(
                "INSERT INTO mission_church_confirmations(tenant_id,church_organization_id,confirmation_status,observation_period_months,support_level) "
                "VALUES(%s,%s,'submitted',%s,%s) RETURNING id",
                (body.organizationId, body.churchOrganizationId, body.observationMonths, body.supportLevel))
            cid = cur.fetchone()[0]
            for rid in set(body.reviewerIds):
                cur.execute("INSERT INTO mission_church_confirmation_reviews(tenant_id,church_confirmation_id,reviewer_id) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
                            (body.organizationId, cid, rid))
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='approve',
                  resource_type='mission_church_confirmation', resource_id=str(cid), result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'confirmationId': str(cid), 'supportLevel': body.supportLevel}


class SubmitAppBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    applicationId: str = Field(min_length=1)
    presentSections: list[str] = Field(default_factory=list)
    expiredSections: list[str] = Field(default_factory=list)
    blockingSections: list[str] = Field(default_factory=list)
    readinessExpired: bool = False
    localPartnerPresent: bool = True
    fieldRequiresPartner: bool = True


class CreateAppBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    workerProfileId: str = Field(min_length=1)
    sendingJourneyId: str | None = None
    targetFieldId: str | None = None
    targetRoleId: str | None = None


@router.post('/applications')
def create_application(body: CreateAppBody, request: Request):
    _user_obj,email=_user(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            role=_role(cur,email,body.organizationId);set_tenant_context(cur,body.organizationId)
            cur.execute("INSERT INTO mission_candidate_applications(tenant_id,sending_journey_id,worker_profile_id,target_field_id,target_role_id,application_status) VALUES(%s,%s,%s,%s,%s,'draft') RETURNING id",(body.organizationId,body.sendingJourneyId,body.workerProfileId,body.targetFieldId,body.targetRoleId))
            aid=cur.fetchone()[0]
            audit(cur,tenant_id=body.organizationId,actor_id=email,actor_role=role,action='create',resource_type='mission_candidate_application',resource_id=str(aid),result='success');conn.commit()
    finally:_state['release_db'](conn)
    return {'ok':True,'applicationId':str(aid),'status':'draft'}


@router.get('/applications')
def list_applications(organizationId: str, request: Request):
    _user_obj,email=_user(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            _role(cur,email,organizationId);set_tenant_context(cur,organizationId)
            cur.execute("SELECT id,worker_profile_id,target_field_id,target_role_id,application_status,created_at FROM mission_candidate_applications WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 200",(organizationId,))
            items=[{'id':str(r[0]),'workerProfileId':r[1],'targetFieldId':r[2],'targetRoleId':r[3],'applicationStatus':r[4],'createdAt':r[5].isoformat()} for r in cur.fetchall()]
    finally:_state['release_db'](conn)
    return {'ok':True,'items':items}


@router.post('/applications/submit')
def submit_application(body: SubmitAppBody, request: Request):
    _user_obj, email = _user(request)
    try:
        assert_can_submit(present_sections=body.presentSections, expired_sections=body.expiredSections,
                          blocking_sections=body.blockingSections, readiness_expired=body.readinessExpired,
                          local_partner_present=body.localPartnerPresent, field_requires_partner=body.fieldRequiresPartner)
    except ValueError as exc:
        raise HTTPException(409, detail=str(exc))
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute("UPDATE mission_candidate_applications SET application_status='committee_ready',submitted_at=now(),updated_at=now() WHERE id=%s AND tenant_id=%s",
                        (body.applicationId, body.organizationId))
            if cur.rowcount == 0:
                raise HTTPException(404, detail='申请不存在')
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='update',
                  resource_type='mission_candidate_application', resource_id=str(body.applicationId), result='success', reason='committee_ready')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'status': 'committee_ready'}


class CommitteeDecisionBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    applicationId: str = Field(min_length=1)
    candidateId: str = Field(min_length=1)
    members: list[dict] = Field(default_factory=list)
    minQuorum: int = Field(default=4, ge=2, le=50)
    decisionType: Literal['approved_for_next_stage', 'conditionally_approved', 'deferred', 'revision_required', 'declined_current_application']
    spouseOpposed: bool = False
    localPartnerOpposed: bool = False
    unresolvedHardBlocks: int = 0
    conditions: list[dict] = Field(default_factory=list)


@router.post('/committee-decisions')
def committee_decision(body: CommitteeDecisionBody, request: Request):
    _user_obj, email = _user(request)
    approving = body.decisionType in ('approved_for_next_stage', 'conditionally_approved')
    try:
        if approving:
            assert_quorum(body.members, body.candidateId, min_quorum=body.minQuorum)
            assert_can_approve(spouse_opposed=body.spouseOpposed, local_partner_opposed=body.localPartnerOpposed,
                               unresolved_hard_blocks=body.unresolvedHardBlocks)
        if body.decisionType == 'conditionally_approved':
            validate_conditional_approval(body.conditions)
    except ValueError as exc:
        raise HTTPException(409, detail=str(exc))
    unlocks = approval_unlocks_batch6_only() if approving else 'none'
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute(
                "INSERT INTO mission_sending_decisions(tenant_id,application_id,decision_type,rationale_summary,conditions,unlocks) "
                "VALUES(%s,%s,%s,%s,%s::jsonb,%s) RETURNING id",
                (body.organizationId, body.applicationId, body.decisionType, 'committee decision', json.dumps(body.conditions), unlocks))
            did = cur.fetchone()[0]
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='approve' if approving else 'reject',
                  resource_type='mission_sending_decision', resource_id=str(did), result='success', reason=body.decisionType)
            enqueue(cur, tenant_id=body.organizationId, aggregate_type='MissionSendingDecision', aggregate_id=str(did),
                    event_type='MissionSendingDecisionRecorded', event_version=1, actor_id=email,
                    correlation_id=request.headers.get('X-Request-Id') or str(did),
                    data={'decision_type': body.decisionType, 'unlocks': unlocks})
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'decisionId': str(did), 'decisionType': body.decisionType, 'unlocks': unlocks}


@router.get('/committee-decisions')
def list_committee_decisions(organizationId:str,request:Request):
    _u,email=_user(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            _role(cur,email,organizationId);set_tenant_context(cur,organizationId)
            cur.execute("SELECT id,application_id,decision_type,conditions,unlocks,effective_at,expires_at FROM mission_sending_decisions WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 200",(organizationId,));items=[{'id':str(r[0]),'applicationId':str(r[1]),'decisionType':r[2],'conditions':r[3],'unlocks':r[4],'effectiveAt':r[5].isoformat() if r[5] else None,'expiresAt':r[6].isoformat() if r[6] else None} for r in cur.fetchall()]
    finally:_state['release_db'](conn)
    return {'ok':True,'items':items}
