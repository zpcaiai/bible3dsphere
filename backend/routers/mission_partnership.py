"""Skill 54/56/58/59/60 API: team membership/covenant, partner approval, prayer updates."""
from __future__ import annotations
import json
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from core.tenancy import require_org_permission
from mission_bridge_auth import set_tenant_context
from mission_feature_guard import require_mission_feature
from mission_os.audit import audit
from mission_os.team import assert_membership_approval, assert_spouse_not_auto_member, validate_covenant
from mission_os.partnership import (
    assert_can_approve_partner, funding_grants_no_control, assert_agreement_complete,
    assert_safeguarding_not_funder_vetoable, assert_update_clean, scheduled_send_allowed,
)

_sending_gate = require_mission_feature('mission_sending_enabled')
teams_router = APIRouter(prefix='/api/v1/mission/teams', tags=['mission-partnership'], dependencies=[Depends(_sending_gate)])
partners_router = APIRouter(prefix='/api/v1/mission/local-partners', tags=['mission-partnership'], dependencies=[Depends(_sending_gate)])
support_router = APIRouter(prefix='/api/v1/mission/prayer-updates', tags=['mission-partnership'], dependencies=[Depends(_sending_gate)])
_state = {}


def init_mission_partnership_router(*, get_db, release_db, get_session_user, is_admin):
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


class TeamCreateBody(BaseModel):
    organizationId: str = Field(min_length=1,max_length=64)
    name: str = Field(min_length=1,max_length=200)
    teamType: str = Field(default='long_term_field_team',max_length=48)
    capacity: int | None = Field(default=None,ge=1,le=500)


@teams_router.post('')
def create_team(body:TeamCreateBody,request:Request):
    _u,email=_user(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            role=_role(cur,email,body.organizationId);set_tenant_context(cur,body.organizationId)
            cur.execute("INSERT INTO mission_teams(tenant_id,team_type,name,lead_organization_id,capacity) VALUES(%s,%s,%s,%s,%s) RETURNING id",(body.organizationId,body.teamType,body.name,body.organizationId,body.capacity));tid=cur.fetchone()[0]
            audit(cur,tenant_id=body.organizationId,actor_id=email,actor_role=role,action='create',resource_type='mission_team',resource_id=str(tid),result='success');conn.commit()
    finally:_state['release_db'](conn)
    return {'ok':True,'teamId':str(tid),'status':'forming'}


@teams_router.get('')
def list_teams(organizationId:str,request:Request):
    _u,email=_user(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            _role(cur,email,organizationId);set_tenant_context(cur,organizationId)
            cur.execute("SELECT id,name,team_type,team_status,capacity,created_at FROM mission_teams WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 200",(organizationId,));items=[{'id':str(r[0]),'name':r[1],'teamType':r[2],'teamStatus':r[3],'capacity':r[4],'createdAt':r[5].isoformat()} for r in cur.fetchall()]
    finally:_state['release_db'](conn)
    return {'ok':True,'items':items}


class PartnerCreateBody(BaseModel):
    organizationId:str=Field(min_length=1,max_length=64)
    internalAlias:str=Field(min_length=1,max_length=200)
    publicName:str|None=Field(default=None,max_length=200)
    partnerType:str=Field(default='local_church',max_length=48)


@partners_router.post('')
def create_partner(body:PartnerCreateBody,request:Request):
    _u,email=_user(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            role=_role(cur,email,body.organizationId);set_tenant_context(cur,body.organizationId)
            cur.execute("INSERT INTO mission_local_partner_profiles(tenant_id,organization_id,partner_type,public_name,internal_alias) VALUES(%s,%s,%s,%s,%s) RETURNING id",(body.organizationId,body.organizationId,body.partnerType,body.publicName,body.internalAlias));pid=cur.fetchone()[0]
            audit(cur,tenant_id=body.organizationId,actor_id=email,actor_role=role,action='create',resource_type='mission_local_partner',resource_id=str(pid),result='success');conn.commit()
    finally:_state['release_db'](conn)
    return {'ok':True,'partnerProfileId':str(pid),'status':'candidate'}


@partners_router.get('')
def list_partners(organizationId:str,request:Request):
    _u,email=_user(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            _role(cur,email,organizationId);set_tenant_context(cur,organizationId)
            cur.execute("SELECT id,internal_alias,public_name,partner_type,profile_status,created_at FROM mission_local_partner_profiles WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 200",(organizationId,));items=[{'id':str(r[0]),'internalAlias':r[1],'publicName':r[2],'partnerType':r[3],'profileStatus':r[4],'createdAt':r[5].isoformat()} for r in cur.fetchall()]
    finally:_state['release_db'](conn)
    return {'ok':True,'items':items}


class MembershipApproveBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    teamId: str = Field(min_length=1)
    candidateId: str = Field(min_length=1)
    isSpouse: bool = False
    hasOwnMembershipDecision: bool = True
    isLeaderSelf: bool = False


@teams_router.post('/memberships/approve')
def approve_membership(body: MembershipApproveBody, request: Request):
    _user_obj, email = _user(request)
    try:
        assert_membership_approval(approver_id=email, candidate_id=body.candidateId, is_leader_self=body.isLeaderSelf)
        assert_spouse_not_auto_member(is_spouse=body.isSpouse, has_own_membership_decision=body.hasOwnMembershipDecision)
    except ValueError as exc:
        raise HTTPException(403, detail=str(exc))
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute("UPDATE mission_team_memberships SET membership_stage='provisional',approved_by=%s,updated_at=now() WHERE team_id=%s AND worker_profile_id=%s AND tenant_id=%s",
                        (email, body.teamId, body.candidateId, body.organizationId))
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='approve',
                  resource_type='mission_team_membership', resource_id=f'{body.teamId}:{body.candidateId}', result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'stage': 'provisional'}


class CovenantBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    teamId: str = Field(min_length=1)
    sections: list[str] = Field(default_factory=list)
    clauses: list[str] = Field(default_factory=list)


@teams_router.post('/covenants')
def create_covenant(body: CovenantBody, request: Request):
    _user_obj, email = _user(request)
    try:
        validate_covenant(clauses=body.clauses, sections=body.sections)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute("INSERT INTO mission_team_covenants(tenant_id,team_id,covenant_status,sections,clauses) VALUES(%s,%s,'draft',%s::jsonb,%s::jsonb) RETURNING id",
                        (body.organizationId, body.teamId, json.dumps(body.sections), json.dumps(body.clauses)))
            cid = cur.fetchone()[0]
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='create',
                  resource_type='mission_team_covenant', resource_id=str(cid), result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'covenantId': str(cid)}


class PartnerApproveBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    partnerProfileId: str = Field(min_length=1)
    hasMutualAssessment: bool = False
    statusTarget: Literal['approved_for_limited_collaboration', 'approved', 'conditional']
    decisionRights: dict = Field(default_factory=dict)
    providingPartyRole: str = 'partner'


@partners_router.post('/approve')
def approve_partner(body: PartnerApproveBody, request: Request):
    _user_obj, email = _user(request)
    try:
        assert_can_approve_partner(has_mutual_assessment=body.hasMutualAssessment, status_target=body.statusTarget)
        funding_grants_no_control(body.decisionRights, body.providingPartyRole)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute("UPDATE mission_local_partner_profiles SET profile_status=%s,updated_at=now() WHERE id=%s AND tenant_id=%s",
                        (body.statusTarget, body.partnerProfileId, body.organizationId))
            if cur.rowcount == 0:
                raise HTTPException(404, detail='伙伴不存在')
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='approve',
                  resource_type='mission_local_partner', resource_id=str(body.partnerProfileId), result='success', reason=body.statusTarget)
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'status': body.statusTarget}


class PrayerUpdateBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    supportNetworkId: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)
    updateType: str = Field(min_length=2, max_length=48)
    fieldKeys: list[str] = Field(default_factory=list)
    visibility: Literal['public', 'registered_supporters', 'sending_church_only', 'care_team_only', 'restricted_named_audience', 'emergency_team_only'] = 'registered_supporters'
    crisisActive: bool = False
    scheduled: bool = False


@support_router.post('')
def create_prayer_update(body: PrayerUpdateBody, request: Request):
    _user_obj, email = _user(request)
    try:
        assert_update_clean(body.fieldKeys)   # no P3/P4 (locations, contacts) in normal updates
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))
    if body.scheduled and not scheduled_send_allowed(crisis_active=body.crisisActive):
        raise HTTPException(409, detail='危机期间暂停预定通讯')
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute("INSERT INTO mission_prayer_updates(tenant_id,support_network_id,title,update_type,visibility,review_status) VALUES(%s,%s,%s,%s,%s,'draft') RETURNING id",
                        (body.organizationId, body.supportNetworkId, body.title, body.updateType, body.visibility))
            uid = cur.fetchone()[0]
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='create',
                  resource_type='mission_prayer_update', resource_id=str(uid), result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'prayerUpdateId': str(uid), 'reviewStatus': 'draft'}
