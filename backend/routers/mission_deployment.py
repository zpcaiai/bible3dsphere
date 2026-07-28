"""Skill 65/66/68/69/71 API: identity path, credential, spouse review, deployment gate."""
from __future__ import annotations
import base64
import json
from datetime import date, datetime, timedelta, timezone
from core.timeutil import parse_iso8601_date as _parse_iso8601_date
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from core.tenancy import require_org_permission
from mission_bridge_auth import set_tenant_context
from mission_feature_guard import require_mission_feature
from mission_os.audit import audit
from mission_os.outbox import enqueue
from mission_os.identity import (
    IDENTITY_TYPES, assert_identity_consistent, assert_no_fake_identity, mask_identifier,
)
from mission_os import vault
from routers.mission_audit import _recent_mfa
from mission_os.health_family import assert_spouse_review_authentic, family_gate
from mission_os.deployment import run_gate, gate_ready_activates_deployment

_deployment_gate = require_mission_feature('mission_deployment_enabled')
identity_router = APIRouter(prefix='/api/v1/mission/legal-identity-paths', tags=['mission-deployment'], dependencies=[Depends(_deployment_gate)])
credential_router = APIRouter(prefix='/api/v1/mission/credentials', tags=['mission-deployment'], dependencies=[Depends(_deployment_gate)])
family_router = APIRouter(prefix='/api/v1/mission/family-readiness-plans', tags=['mission-deployment'], dependencies=[Depends(_deployment_gate)])
gate_router = APIRouter(prefix='/api/v1/mission/deployment-readiness-gates', tags=['mission-deployment'], dependencies=[Depends(_deployment_gate)])
compliance_router = APIRouter(prefix='/api/v1/mission/compliance-cases', tags=['mission-deployment'], dependencies=[Depends(_deployment_gate)])
_state = {}


def init_mission_deployment_router(*, get_db, release_db, get_session_user, is_admin):
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


class IdentityBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    workerProfileId: str = Field(min_length=1)
    identityType: str = Field(min_length=2, max_length=48)
    declaredActivity: str = Field(min_length=1, max_length=500)
    actualActivity: str = Field(min_length=1, max_length=500)
    intent: str = Field(default='real', max_length=48)


@identity_router.post('')
def create_identity_path(body: IdentityBody, request: Request):
    _user_obj, email = _user(request)
    if body.identityType not in IDENTITY_TYPES:
        raise HTTPException(422, detail='invalid identity type')
    try:
        assert_no_fake_identity(body.intent)
        assert_identity_consistent(declared_activity=body.declaredActivity, actual_activity=body.actualActivity)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute(
                "INSERT INTO mission_legal_identity_paths(tenant_id,worker_profile_id,identity_type,declared_activity_summary,actual_activity_summary,consistency_status,path_status) "
                "VALUES(%s,%s,%s,%s,%s,'consistent','research') RETURNING id",
                (body.organizationId, body.workerProfileId, body.identityType, body.declaredActivity, body.actualActivity))
            pid = cur.fetchone()[0]
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='create',
                  resource_type='mission_legal_identity_path', resource_id=str(pid), result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'identityPathId': str(pid), 'status': 'research'}


@identity_router.get('')
def list_identity_paths(organizationId:str,request:Request):
    _u,email=_user(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            _role(cur,email,organizationId);set_tenant_context(cur,organizationId)
            cur.execute("SELECT id,worker_profile_id,identity_type,consistency_status,path_status,created_at FROM mission_legal_identity_paths WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 200",(organizationId,));items=[{'id':str(r[0]),'workerProfileId':r[1],'identityType':r[2],'consistencyStatus':r[3],'pathStatus':r[4],'createdAt':r[5].isoformat()} for r in cur.fetchall()]
    finally:_state['release_db'](conn)
    return {'ok':True,'items':items}


class CredentialBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    portfolioId: str = Field(min_length=1)
    credentialType: str = Field(min_length=2, max_length=48)
    identifier: str = Field(min_length=1, max_length=64)
    issuingCountry: str | None = Field(default=None, max_length=2)
    expiresAt: str | None = None
    secureFileBase64: str | None = None
    secureFileName: str | None = Field(default=None, max_length=200)
    secureFileMediaType: str = Field(default='application/octet-stream', max_length=120)


@credential_router.post('')
def add_credential(body: CredentialBody, request: Request):
    _user_obj, email = _user(request)
    masked = mask_identifier(body.identifier)   # only masked form is stored in a normal column
    exp = None
    if body.expiresAt:
        try:
            exp = _parse_iso8601_date(body.expiresAt)
        except ValueError:
            raise HTTPException(422, detail='expiresAt must be ISO date')
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute(
                "INSERT INTO mission_credentials(tenant_id,credential_portfolio_id,credential_type,issuing_country,masked_identifier,expires_at,credential_status) "
                "VALUES(%s,%s,%s,%s,%s,%s,'issued') RETURNING id",
                (body.organizationId, body.portfolioId, body.credentialType, body.issuingCountry, masked, exp))
            cid = cur.fetchone()[0]
            ad=vault.aad(tenant_id=body.organizationId,resource_type='mission_credential',resource_id=str(cid),field_name='identifier')
            encrypted=vault.encrypt(body.identifier.encode(),associated_data=ad)
            cur.execute("INSERT INTO mission_vault_secrets(tenant_id,resource_type,resource_id,field_name,key_version,nonce,ciphertext,content_sha256,created_by) VALUES(%s,'mission_credential',%s,'identifier',%s,%s,%s,%s,%s) RETURNING id",(body.organizationId,str(cid),encrypted.key_version,encrypted.nonce,encrypted.ciphertext,encrypted.sha256,email))
            secret_id=cur.fetchone()[0]
            file_id=None
            if body.secureFileBase64:
                try:content=base64.b64decode(body.secureFileBase64,validate=True)
                except Exception as exc:raise HTTPException(422,detail='secureFileBase64 无效') from exc
                vault.validate_file(content)
                file_ad=vault.aad(tenant_id=body.organizationId,resource_type='mission_credential',resource_id=str(cid),field_name='file')
                file_env=vault.encrypt(content,associated_data=file_ad)
                cur.execute("INSERT INTO mission_vault_files(tenant_id,resource_type,resource_id,file_name,media_type,byte_size,key_version,nonce,ciphertext,content_sha256,created_by) VALUES(%s,'mission_credential',%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",(body.organizationId,str(cid),body.secureFileName or 'credential.bin',body.secureFileMediaType,len(content),file_env.key_version,file_env.nonce,file_env.ciphertext,file_env.sha256,email));file_id=cur.fetchone()[0]
            cur.execute("UPDATE mission_credentials SET encrypted_identifier_reference=%s,secure_file_reference=%s WHERE id=%s AND tenant_id=%s",(f'vault-secret:{secret_id}',f'vault-file:{file_id}' if file_id else None,cid,body.organizationId))
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='create',
                  resource_type='mission_credential', resource_id=str(cid), result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    # The raw identifier is never returned or stored in a normal column.
    return {'ok': True, 'credentialId': str(cid), 'maskedIdentifier': masked, 'encryptedAtRest': True, 'secureFileStored': bool(file_id)}


class VaultSessionBody(BaseModel):
    organizationId:str=Field(min_length=1,max_length=64)
    purpose:Literal['credential_download','medical_record_access']='credential_download'


@credential_router.post('/vault-session')
def open_vault_session(body:VaultSessionBody,request:Request):
    user,email=_user(request)
    if not _recent_mfa(user):raise HTTPException(403,detail='需要最近 10 分钟内完成真实二次认证')
    now=datetime.now(timezone.utc);expires=now+timedelta(minutes=10);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            role=_role(cur,email,body.organizationId);set_tenant_context(cur,body.organizationId)
            cur.execute("INSERT INTO mission_secure_sessions(tenant_id,user_id,purpose,step_up_method,verified_at,expires_at) VALUES(%s,%s,%s,'webauthn',%s,%s) RETURNING id",(body.organizationId,email,body.purpose,now,expires));sid=cur.fetchone()[0]
            audit(cur,tenant_id=body.organizationId,actor_id=email,actor_role=role,action='approve',resource_type='mission_secure_session',resource_id=str(sid),result='success',reason=body.purpose);conn.commit()
    finally:_state['release_db'](conn)
    return {'ok':True,'secureSessionId':str(sid),'expiresAt':expires.isoformat()}


@credential_router.get('/{credential_id}/secure-file')
def download_credential_file(credential_id:str,organizationId:str,secureSessionId:str,request:Request):
    _u,email=_user(request);now=datetime.now(timezone.utc);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            role=_role(cur,email,organizationId);set_tenant_context(cur,organizationId)
            cur.execute("SELECT user_id,purpose,expires_at,revoked_at FROM mission_secure_sessions WHERE id=%s AND tenant_id=%s",(secureSessionId,organizationId));s=cur.fetchone()
            if not s or not vault.secure_session_valid(user_id=email,session_user_id=s[0],purpose=s[1],expires_at=s[2],revoked_at=s[3],now=now):raise HTTPException(403,detail='安全会话无效或已过期')
            cur.execute("SELECT id,file_name,media_type,key_version,nonce,ciphertext,content_sha256 FROM mission_vault_files WHERE tenant_id=%s AND resource_type='mission_credential' AND resource_id=%s AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1",(organizationId,credential_id));row=cur.fetchone()
            if not row:raise HTTPException(404,detail='安全文件不存在')
            env=vault.Envelope(row[3],bytes(row[4]),bytes(row[5]),row[6]);ad=vault.aad(tenant_id=organizationId,resource_type='mission_credential',resource_id=credential_id,field_name='file');content=vault.decrypt(env,associated_data=ad)
            audit(cur,tenant_id=organizationId,actor_id=email,actor_role=role,action='download',resource_type='mission_vault_file',resource_id=str(row[0]),result='success',reason='credential_download');conn.commit()
    finally:_state['release_db'](conn)
    return {'ok':True,'fileName':row[1],'mediaType':row[2],'contentBase64':base64.b64encode(content).decode(),'watermarkedFor':email}


class SpouseReviewBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    familyPlanId: str = Field(min_length=1)
    spouseUserId: str = Field(min_length=1)
    willingnessStatus: Literal['not_asked', 'considering', 'supportive', 'supportive_with_conditions', 'not_ready', 'does_not_consent', 'withdrawn', 'review_required']
    concernSummary: str | None = Field(default=None, max_length=2000)


class FamilyPlanBody(BaseModel):
    organizationId:str=Field(min_length=1,max_length=64)
    workerProfileId:str=Field(min_length=1)
    householdType:str=Field(default='family',max_length=48)
    sendingJourneyId:str|None=None
    targetFieldId:str|None=None
    intendedMoveDate:str|None=None


@family_router.post('')
def create_family_plan(body:FamilyPlanBody,request:Request):
    _u,email=_user(request);move=None
    if body.intendedMoveDate:
        try:move=_parse_iso8601_date(body.intendedMoveDate)
        except ValueError:raise HTTPException(422,detail='intendedMoveDate must be ISO date')
    conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            role=_role(cur,email,body.organizationId);set_tenant_context(cur,body.organizationId)
            cur.execute("INSERT INTO mission_households(tenant_id,worker_profile_id,household_type) VALUES(%s,%s,%s) RETURNING id",(body.organizationId,body.workerProfileId,body.householdType));hid=cur.fetchone()[0]
            cur.execute("INSERT INTO mission_family_readiness_plans(tenant_id,household_id,sending_journey_id,target_field_id,intended_move_date) VALUES(%s,%s,%s,%s,%s) RETURNING id",(body.organizationId,hid,body.sendingJourneyId,body.targetFieldId,move));pid=cur.fetchone()[0]
            audit(cur,tenant_id=body.organizationId,actor_id=email,actor_role=role,action='create',resource_type='mission_family_readiness_plan',resource_id=str(pid),result='success');conn.commit()
    finally:_state['release_db'](conn)
    return {'ok':True,'familyPlanId':str(pid),'householdId':str(hid),'status':'draft'}


@family_router.get('')
def list_family_plans(organizationId:str,request:Request):
    _u,email=_user(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            _role(cur,email,organizationId);set_tenant_context(cur,organizationId)
            cur.execute("SELECT id,household_id,sending_journey_id,plan_status,target_field_id,intended_move_date,created_at FROM mission_family_readiness_plans WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 200",(organizationId,));items=[{'id':str(r[0]),'householdId':str(r[1]),'sendingJourneyId':r[2],'planStatus':r[3],'targetFieldId':r[4],'intendedMoveDate':r[5].isoformat() if r[5] else None,'createdAt':r[6].isoformat()} for r in cur.fetchall()]
    finally:_state['release_db'](conn)
    return {'ok':True,'items':items}


@family_router.post('/{family_plan_id}/spouse-review')
def submit_spouse_review(family_plan_id: str, body: SpouseReviewBody, request: Request):
    _user_obj, email = _user(request)
    try:
        # the review must be submitted by the spouse themselves, not the candidate
        assert_spouse_review_authentic(submitter_id=email, spouse_user_id=body.spouseUserId)
    except ValueError as exc:
        raise HTTPException(403, detail=str(exc))
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute(
                "INSERT INTO mission_spouse_readiness_reviews(tenant_id,family_plan_id,spouse_user_id,submitted_by,willingness_status,concern_summary) "
                "VALUES(%s,%s,%s,%s,%s,%s) RETURNING id",
                (body.organizationId, family_plan_id, body.spouseUserId, email, body.willingnessStatus, body.concernSummary))
            rid = cur.fetchone()[0]
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role, action='create',
                  resource_type='mission_spouse_readiness_review', resource_id=str(rid), result='success')
            conn.commit()
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'reviewId': str(rid)}


class GateRunBody(BaseModel):
    organizationId: str = Field(min_length=1, max_length=64)
    sendingJourneyId: str = Field(min_length=1)
    hardBlocks: list[str] = Field(default_factory=list)
    isPanel: bool = False
    candidateId: str = Field(min_length=1)


@gate_router.post('/run')
def run_deployment_gate(body: GateRunBody, request: Request):
    _user_obj, email = _user(request)
    try:
        result = run_gate(hard_blocks=body.hardBlocks, decider_type='human', is_panel=body.isPanel,
                          candidate_id=body.candidateId, decider_id=email)
    except ValueError as exc:
        raise HTTPException(403, detail=str(exc))
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            role = _role(cur, email, body.organizationId)
            set_tenant_context(cur, body.organizationId)
            cur.execute(
                "INSERT INTO mission_deployment_readiness_gates(tenant_id,sending_journey_id,gate_status,blocking_findings,unlocks,decided_by_panel_id,decided_at) "
                "VALUES(%s,%s,%s,%s::jsonb,%s,%s,now()) RETURNING id",
                (body.organizationId, body.sendingJourneyId, result['status'], json.dumps(result['blocking']),
                 result['unlocks'], email if result['status'] == 'ready_for_deployment_planning' else None))
            gid = cur.fetchone()[0]
            audit(cur, tenant_id=body.organizationId, actor_id=email, actor_role=role,
                  action='approve' if result['status'] == 'ready_for_deployment_planning' else 'reject',
                  resource_type='mission_deployment_readiness_gate', resource_id=str(gid), result='success', reason=result['status'])
            enqueue(cur, tenant_id=body.organizationId, aggregate_type='MissionDeploymentReadinessGate', aggregate_id=str(gid),
                    event_type='MissionDeploymentReadinessGateRun', event_version=1, actor_id=email,
                    correlation_id=request.headers.get('X-Request-Id') or str(gid),
                    data={'status': result['status'], 'unlocks': result['unlocks']})
            conn.commit()
    finally:
        _state['release_db'](conn)
    # Ready only unlocks the operational deployment-planning stage; never activates a deployment.
    return {'ok': True, 'gateId': str(gid), 'status': result['status'], 'unlocks': result['unlocks'],
            'activatesDeployment': gate_ready_activates_deployment()}


class ComplianceBody(BaseModel):
    organizationId:str=Field(min_length=1,max_length=64)
    sendingJourneyId:str|None=None
    targetFieldId:str|None=None
    activityScope:str=Field(min_length=3,max_length=2000)
    domains:list[str]=Field(default_factory=lambda:['immigration','tax','employment','data_transfer'])


@compliance_router.post('')
def create_compliance_case(body:ComplianceBody,request:Request):
    _u,email=_user(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            role=_role(cur,email,body.organizationId);set_tenant_context(cur,body.organizationId)
            cur.execute("INSERT INTO mission_compliance_cases(tenant_id,sending_journey_id,target_field_id,case_status,activity_scope) VALUES(%s,%s,%s,'scoping',%s) RETURNING id",(body.organizationId,body.sendingJourneyId,body.targetFieldId,body.activityScope));cid=cur.fetchone()[0]
            for domain in sorted(set(body.domains)):
                cur.execute("INSERT INTO mission_compliance_domains(tenant_id,compliance_case_id,domain_key) VALUES(%s,%s,%s)",(body.organizationId,cid,domain))
            audit(cur,tenant_id=body.organizationId,actor_id=email,actor_role=role,action='create',resource_type='mission_compliance_case',resource_id=str(cid),result='success');conn.commit()
    finally:_state['release_db'](conn)
    return {'ok':True,'complianceCaseId':str(cid),'status':'scoping','domainCount':len(set(body.domains))}


@compliance_router.get('')
def list_compliance_cases(organizationId:str,request:Request):
    _u,email=_user(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            _role(cur,email,organizationId);set_tenant_context(cur,organizationId)
            cur.execute("SELECT c.id,c.sending_journey_id,c.target_field_id,c.case_status,c.activity_scope,c.created_at,count(d.id) FROM mission_compliance_cases c LEFT JOIN mission_compliance_domains d ON d.compliance_case_id=c.id AND d.tenant_id=c.tenant_id WHERE c.tenant_id=%s GROUP BY c.id ORDER BY c.created_at DESC LIMIT 200",(organizationId,));items=[{'id':str(r[0]),'sendingJourneyId':r[1],'targetFieldId':r[2],'caseStatus':r[3],'activityScope':r[4],'createdAt':r[5].isoformat(),'domainCount':r[6]} for r in cur.fetchall()]
    finally:_state['release_db'](conn)
    return {'ok':True,'items':items}


@gate_router.get('')
def list_gates(organizationId: str, request: Request):
    _user_obj, email = _user(request)
    conn = _state['get_db']()
    try:
        with conn.cursor() as cur:
            _role(cur, email, organizationId)
            set_tenant_context(cur, organizationId)
            cur.execute("SELECT id,sending_journey_id,gate_status,unlocks,blocking_findings,created_at FROM mission_deployment_readiness_gates WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 200", (organizationId,))
            rows = [{'id': str(r[0]), 'sendingJourneyId': r[1], 'gateStatus': r[2], 'unlocks': r[3],
                     'blockingFindings': r[4], 'createdAt': r[5].isoformat() if r[5] else None} for r in cur.fetchall()]
    finally:
        _state['release_db'](conn)
    return {'ok': True, 'items': rows}
