"""Skill 08 API: mission profiles and explicit inter-organization collaboration."""
from __future__ import annotations
import hashlib,secrets,uuid
from datetime import datetime,timedelta,timezone
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Request
from pydantic import BaseModel,Field,field_validator
from core.tenancy import require_org_permission
from mission_bridge_auth import set_tenant_context
from mission_feature_guard import require_mission_os
from mission_os.audit import audit
from mission_os.organizations import MissionOrganizationProfile,validate_relationship
from mission_os.outbox import enqueue

router=APIRouter(prefix='/api/v1/mission/organizations',tags=['mission-organizations'],dependencies=[Depends(require_mission_os)]);_state={}
def init_mission_organizations_router(*,get_db,release_db,get_session_user,is_admin):_state.update(locals())
def _user(request):
    user=_state['get_session_user'](request);email=str((user or {}).get('email') or '')
    if not email:raise HTTPException(401,detail='请先登录')
    return user,email
def _admin(cur,email,org_id):
    if _state['is_admin'](email):return 'platform_admin'
    return require_org_permission(cur,email,org_id,'manage_settings')['role']

class ProfileBody(BaseModel):
    organizationKind:Literal['church','mission_agency','receiving_church','team','training_provider','care_provider','professional_partner','funding_partner']
    legalName:str|None=Field(default=None,max_length=240);countryCode:str|None=Field(default=None,min_length=2,max_length=2)
    safeguardingContactUserId:str|None=Field(default=None,max_length=255);dataResidencyRegion:str|None=Field(default=None,max_length=80)
@router.put('/{organization_id}/profile')
def upsert_profile(organization_id:str,body:ProfileBody,request:Request):
    user,email=_user(request);MissionOrganizationProfile(organization_id,organization_id,body.organizationKind,body.countryCode).validate();conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            role=_admin(cur,email,organization_id);set_tenant_context(cur,organization_id)
            cur.execute("INSERT INTO mission_organization_profiles(organization_id,tenant_id,organization_kind,legal_name,country_code,safeguarding_contact_user_id,data_residency_region) VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(organization_id) DO UPDATE SET organization_kind=EXCLUDED.organization_kind,legal_name=EXCLUDED.legal_name,country_code=EXCLUDED.country_code,safeguarding_contact_user_id=EXCLUDED.safeguarding_contact_user_id,data_residency_region=EXCLUDED.data_residency_region,updated_at=now()",(organization_id,organization_id,body.organizationKind,body.legalName,body.countryCode.upper() if body.countryCode else None,body.safeguardingContactUserId,body.dataResidencyRegion))
            audit(cur,tenant_id=organization_id,actor_id=email,actor_role=role,action='update',resource_type='mission_organization_profile',resource_id=organization_id,result='success',changed_fields=['organization_kind','legal_name','country_code','safeguarding_contact_user_id','data_residency_region']);conn.commit()
    finally:_state['release_db'](conn)
    return {'ok':True,'organizationId':organization_id}

@router.get('/{organization_id}')
def get_organization(organization_id:str,request:Request):
    user,email=_user(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            _admin(cur,email,organization_id);set_tenant_context(cur,organization_id)
            cur.execute("SELECT o.id,o.name,o.organization_type,p.organization_kind,p.legal_name,p.country_code,p.status FROM organizations o LEFT JOIN mission_organization_profiles p ON p.organization_id=o.id WHERE o.id=%s",(organization_id,));row=cur.fetchone()
            if not row:raise HTTPException(404,detail='组织不存在')
            cur.execute("SELECT id,source_organization_id,target_organization_id,relationship_type,status,decision_rights,starts_at,ends_at FROM mission_organization_relationships WHERE tenant_id=%s ORDER BY created_at DESC",(organization_id,));rels=[{'id':str(r[0]),'sourceOrganizationId':r[1],'targetOrganizationId':r[2],'relationshipType':r[3],'status':r[4],'decisionRights':r[5],'startsAt':r[6].isoformat() if r[6] else None,'endsAt':r[7].isoformat() if r[7] else None} for r in cur.fetchall()]
    finally:_state['release_db'](conn)
    return {'ok':True,'organization':{'id':row[0],'name':row[1],'baseType':row[2],'missionKind':row[3],'legalName':row[4],'countryCode':row[5],'status':row[6]},'relationships':rels}

class RelationshipBody(BaseModel):
    targetOrganizationId:str=Field(min_length=1,max_length=64);relationshipType:Literal['sending','receiving','partner','training','member_care','professional_referral','funding'];decisionRights:dict=Field(default_factory=dict)
@router.post('/{organization_id}/relationships')
def create_relationship(organization_id:str,body:RelationshipBody,request:Request):
    user,email=_user(request);validate_relationship(organization_id,body.targetOrganizationId,body.relationshipType,body.decisionRights);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            role=_admin(cur,email,organization_id);set_tenant_context(cur,organization_id)
            cur.execute("SELECT 1 FROM organizations WHERE id=%s",(body.targetOrganizationId,))
            if not cur.fetchone():raise HTTPException(404,detail='合作组织不存在')
            cur.execute("INSERT INTO mission_organization_relationships(tenant_id,source_organization_id,target_organization_id,relationship_type,decision_rights,created_by) VALUES(%s,%s,%s,%s,%s::jsonb,%s) RETURNING id",(organization_id,organization_id,body.targetOrganizationId,body.relationshipType,__import__('json').dumps(body.decisionRights),email));rid=cur.fetchone()[0]
            audit(cur,tenant_id=organization_id,actor_id=email,actor_role=role,action='create',resource_type='mission_organization_relationship',resource_id=str(rid),result='success')
            enqueue(cur,tenant_id=organization_id,aggregate_type='MissionOrganizationRelationship',aggregate_id=str(rid),event_type='MissionOrganizationRelationshipProposed',event_version=1,actor_id=email,correlation_id=request.headers.get('X-Request-Id') or str(uuid.uuid4()),data={'relationship_id':str(rid),'relationship_type':body.relationshipType,'target_organization_id':body.targetOrganizationId});conn.commit()
    finally:_state['release_db'](conn)
    return {'ok':True,'relationshipId':str(rid),'status':'proposed'}

class InviteBody(BaseModel):
    email:str=Field(min_length=3,max_length=255);roleKey:str=Field(min_length=2,max_length=40);expiresHours:int=Field(default=72,ge=1,le=168)
    @field_validator('email')
    @classmethod
    def valid_email(cls,value):
        value=value.strip().lower()
        if value.count('@')!=1 or '.' not in value.rsplit('@',1)[1] or any(ch.isspace() for ch in value):raise ValueError('invalid email')
        return value
@router.post('/{organization_id}/invitations')
def invite(organization_id:str,body:InviteBody,request:Request):
    user,email=_user(request);conn=_state['get_db']();raw=secrets.token_urlsafe(32);digest=hashlib.sha256(raw.encode()).hexdigest()
    try:
        with conn.cursor() as cur:
            role=_admin(cur,email,organization_id);set_tenant_context(cur,organization_id)
            cur.execute("INSERT INTO mission_organization_invitations(tenant_id,organization_id,invited_email,role_key,token_hash,expires_at,invited_by) VALUES(%s,%s,%s,%s,%s,now()+(%s*interval '1 hour'),%s) RETURNING id,expires_at",(organization_id,organization_id,str(body.email).lower(),body.roleKey,digest,body.expiresHours,email));row=cur.fetchone()
            audit(cur,tenant_id=organization_id,actor_id=email,actor_role=role,action='create',resource_type='mission_organization_invitation',resource_id=str(row[0]),result='success');conn.commit()
    finally:_state['release_db'](conn)
    return {'ok':True,'invitationId':str(row[0]),'invitationToken':raw,'expiresAt':row[1].isoformat()}

class AcceptBody(BaseModel):tenantId:str;token:str=Field(min_length=20,max_length=200)
@router.post('/invitations/accept')
def accept(body:AcceptBody,request:Request):
    user,email=_user(request);conn=_state['get_db']();digest=hashlib.sha256(body.token.encode()).hexdigest()
    try:
        with conn.cursor() as cur:
            set_tenant_context(cur,body.tenantId);cur.execute("SELECT id,organization_id,role_key FROM mission_organization_invitations WHERE tenant_id=%s AND token_hash=%s AND invited_email=%s AND status='pending' AND expires_at>now() FOR UPDATE",(body.tenantId,digest,email.lower()));row=cur.fetchone()
            if not row:raise HTTPException(404,detail='邀请不存在、已过期或不属于当前用户')
            cur.execute("INSERT INTO organization_memberships(id,organization_id,email,role_key,status) VALUES(%s,%s,%s,%s,'active') ON CONFLICT(organization_id,email) DO UPDATE SET role_key=EXCLUDED.role_key,status='active',updated_at=CURRENT_TIMESTAMP",(str(uuid.uuid4()),row[1],email,row[2]));cur.execute("UPDATE mission_organization_invitations SET status='accepted',accepted_at=now(),updated_at=now() WHERE id=%s",(row[0],));conn.commit()
    finally:_state['release_db'](conn)
    return {'ok':True,'organizationId':row[1],'roleKey':row[2]}
