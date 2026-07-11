"""Mission OS safeguarding API with explicit human-owned transitions."""
from __future__ import annotations
import uuid
from typing import Literal
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field
from mission_os.audit import audit
from mission_os.incidents import IncidentState,authorize_view,l3_close_ready,validate_risk_change,validate_transition
from mission_os.outbox import enqueue

router=APIRouter(prefix='/api/v1/mission/incidents',tags=['mission-incidents']);_state={}
def init_mission_incidents_router(*,get_db,release_db,get_session_user,is_admin):_state.update(locals())
def _identity(request):
    user=_state['get_session_user'](request);email=str((user or {}).get('email') or '')
    if not email:raise HTTPException(401,detail='请先登录')
    return user,email
def _tenant(request):return (request.headers.get('X-Tenant-Id') or 'public')[:80]
def _role(cur,tenant,email):
    if _state['is_admin'](email):return 'platform_admin'
    cur.execute("SELECT role_key FROM mission_bridge_tenant_memberships WHERE tenant_id=%s AND user_id=%s AND status='active' ORDER BY created_at DESC LIMIT 1",(tenant,email));row=cur.fetchone()
    return str(row[0]) if row else ('participant' if tenant=='public' else '')
def _load(cur,tenant,incident_id,lock=False):
    cur.execute("SELECT id,reporter_user_id,risk_level,category,summary,status,assigned_to,created_at FROM incident_reports WHERE id=%s AND tenant_id=%s"+(" FOR UPDATE" if lock else ""),(incident_id,tenant));row=cur.fetchone()
    if not row:raise HTTPException(404,detail='事件不存在')
    return row
def _check(state,role,is_reporter=False):
    try:authorize_view(state,role,is_reporter)
    except PermissionError as exc:raise HTTPException(403,detail=str(exc))
def _event(cur,tenant,incident_id,event_type,from_status,to_status,from_level,to_level,reason,email,role):
    cur.execute("INSERT INTO mission_incident_events(tenant_id,incident_id,event_type,from_status,to_status,from_risk_level,to_risk_level,reason,actor_id,actor_role) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(tenant,incident_id,event_type,from_status,to_status,from_level,to_level,reason,email,role))

class CreateBody(BaseModel):
    riskLevel:Literal['L0','L1','L2','L3'];category:str=Field(min_length=2,max_length=80);summary:str=Field(min_length=4,max_length=2000);immediateDanger:bool=False;subjectType:str='participant';subjectId:str|None=None
@router.post('')
def create(body:CreateBody,request:Request):
    user,email=_identity(request);tenant=_tenant(request);level='L3' if body.immediateDanger else body.riskLevel;conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO incident_reports(tenant_id,participant_id,reporter_user_id,risk_level,category,summary,immediate_danger,subject_type,subject_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",(tenant,body.subjectId or email,email,level,body.category,body.summary,body.immediateDanger,body.subjectType,body.subjectId));iid=cur.fetchone()[0]
            _event(cur,tenant,iid,'created',None,'open',None,level,'minimum necessary report',email,'participant')
            enqueue(cur,tenant_id=tenant,aggregate_type='MissionIncident',aggregate_id=str(iid),event_type='MissionIncidentCreated',event_version=1,actor_id=email,correlation_id=request.headers.get('X-Request-Id') or str(uuid.uuid4()),data={'incident_id':str(iid),'risk_level':level,'requires_human_review':level in {'L2','L3'}});conn.commit()
    finally:_state['release_db'](conn)
    return {'ok':True,'incidentId':str(iid),'riskLevel':level,'requiresHumanEscalation':level in {'L2','L3'},'emergencyNotice':level=='L3'}

@router.get('')
def list_items(request:Request,limit:int=100):
    user,email=_identity(request);tenant=_tenant(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            role=_role(cur,tenant,email)
            if role not in {'platform_admin','safeguarding_officer','child_protection_officer','incident_commander'}:raise HTTPException(403,detail='需要安全事件处理权限')
            cur.execute("SELECT id,risk_level,category,status,assigned_to,created_at FROM incident_reports WHERE tenant_id=%s ORDER BY CASE risk_level WHEN 'L3' THEN 3 WHEN 'L2' THEN 2 WHEN 'L1' THEN 1 ELSE 0 END DESC,created_at DESC LIMIT %s",(tenant,min(max(limit,1),200)));rows=cur.fetchall()
            items=[]
            for r in rows:
                try:authorize_view(IncidentState(r[3],r[1],r[2]),role)
                except PermissionError:continue
                items.append({'id':str(r[0]),'riskLevel':r[1],'category':r[2],'status':r[3],'assignedTo':r[4],'createdAt':r[5].isoformat()})
    finally:_state['release_db'](conn)
    return {'ok':True,'items':items}

@router.get('/{incident_id}')
def get(incident_id:uuid.UUID,request:Request):
    user,email=_identity(request);tenant=_tenant(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            row=_load(cur,tenant,str(incident_id));role=_role(cur,tenant,email);_check(IncidentState(row[5],row[2],row[3]),role,row[1]==email)
            audit(cur,tenant_id=tenant,actor_id=email,actor_role=role,action='view_sensitive_resource',resource_type='incident',resource_id=str(incident_id),result='success');conn.commit()
    finally:_state['release_db'](conn)
    return {'ok':True,'incident':{'id':str(row[0]),'riskLevel':row[2],'category':row[3],'summary':row[4],'status':row[5],'assignedTo':row[6],'createdAt':row[7].isoformat()}}

class TransitionBody(BaseModel):reason:str=Field(min_length=8,max_length=1000);assigneeId:str|None=None
def _transition(incident_id,body,request,to_status,event_type):
    user,email=_identity(request);tenant=_tenant(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            row=_load(cur,tenant,str(incident_id),True);role=_role(cur,tenant,email);state=IncidentState(row[5],row[2],row[3])
            try:validate_transition(state,to_status,role)
            except (ValueError,PermissionError) as exc:raise HTTPException(409 if isinstance(exc,ValueError) else 403,detail=str(exc))
            assigned=body.assigneeId if to_status=='assigned' else row[6]
            if to_status=='assigned' and not assigned:raise HTTPException(422,detail='指派必须提供 assigneeId')
            cur.execute("UPDATE incident_reports SET status=%s,assigned_to=%s,updated_at=now(),resolved_at=CASE WHEN %s='resolved' THEN now() ELSE resolved_at END WHERE id=%s",(to_status,assigned,to_status,str(incident_id)))
            _event(cur,tenant,str(incident_id),event_type,row[5],to_status,row[2],row[2],body.reason,email,role);conn.commit()
    finally:_state['release_db'](conn)
    return {'ok':True,'status':to_status}
@router.post('/{incident_id}/triage')
def triage(incident_id:uuid.UUID,body:TransitionBody,request:Request):return _transition(incident_id,body,request,'triaged','triaged')
@router.post('/{incident_id}/assign')
def assign(incident_id:uuid.UUID,body:TransitionBody,request:Request):return _transition(incident_id,body,request,'assigned','assigned')
@router.post('/{incident_id}/start')
def start(incident_id:uuid.UUID,body:TransitionBody,request:Request):return _transition(incident_id,body,request,'action_in_progress','action_started')
@router.post('/{incident_id}/monitor')
def monitor(incident_id:uuid.UUID,body:TransitionBody,request:Request):return _transition(incident_id,body,request,'monitoring','monitoring_started')
@router.post('/{incident_id}/resolve')
def resolve(incident_id:uuid.UUID,body:TransitionBody,request:Request):return _transition(incident_id,body,request,'resolved','resolved')

class RiskBody(BaseModel):toLevel:Literal['L0','L1','L2','L3'];reason:str=Field(min_length=12,max_length=1000)
@router.post('/{incident_id}/escalate')
def change_risk(incident_id:uuid.UUID,body:RiskBody,request:Request):
    user,email=_identity(request);tenant=_tenant(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            row=_load(cur,tenant,str(incident_id),True);role=_role(cur,tenant,email)
            if role not in {'platform_admin','safeguarding_officer','child_protection_officer','incident_commander'}:raise HTTPException(403,detail='风险变更必须人工安全角色处理')
            try:validate_risk_change(row[2],body.toLevel,'human',body.reason)
            except (ValueError,PermissionError) as exc:raise HTTPException(422,detail=str(exc))
            cur.execute("UPDATE incident_reports SET risk_level=%s,updated_at=now() WHERE id=%s",(body.toLevel,str(incident_id)));_event(cur,tenant,str(incident_id),'risk_changed',row[5],row[5],row[2],body.toLevel,body.reason,email,role);conn.commit()
    finally:_state['release_db'](conn)
    return {'ok':True,'riskLevel':body.toLevel}

class ReviewBody(BaseModel):decision:Literal['approve','reject'];reason:str=Field(min_length=8,max_length=1000)
@router.post('/{incident_id}/close-review')
def close_review(incident_id:uuid.UUID,body:ReviewBody,request:Request):
    user,email=_identity(request);tenant=_tenant(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            row=_load(cur,tenant,str(incident_id),True);role=_role(cur,tenant,email)
            if row[2]!='L3' or row[5]!='resolved':raise HTTPException(409,detail='仅已解决的 L3 需要关闭复核')
            if role not in {'platform_admin','safeguarding_officer','child_protection_officer','incident_commander'}:raise HTTPException(403,detail='需要独立安全复核人')
            cur.execute("INSERT INTO mission_incident_close_reviews(tenant_id,incident_id,reviewer_id,decision,reason) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(incident_id,reviewer_id) DO UPDATE SET decision=EXCLUDED.decision,reason=EXCLUDED.reason,updated_at=now()",(tenant,str(incident_id),email,body.decision,body.reason));conn.commit()
    finally:_state['release_db'](conn)
    return {'ok':True,'decision':body.decision}

@router.post('/{incident_id}/close')
def close(incident_id:uuid.UUID,body:TransitionBody,request:Request):
    user,email=_identity(request);tenant=_tenant(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            row=_load(cur,tenant,str(incident_id),True);role=_role(cur,tenant,email);state=IncidentState(row[5],row[2],row[3])
            try:validate_transition(state,'closed',role)
            except (ValueError,PermissionError) as exc:raise HTTPException(409 if isinstance(exc,ValueError) else 403,detail=str(exc))
            if row[2]=='L3':
                cur.execute("SELECT reviewer_id,decision FROM mission_incident_close_reviews WHERE incident_id=%s",(str(incident_id),))
                if not l3_close_ready(cur.fetchall(),email):raise HTTPException(409,detail='L3 关闭需要两名独立安全复核人批准')
            cur.execute("UPDATE incident_reports SET status='closed',closed_at=now(),updated_at=now() WHERE id=%s",(str(incident_id),));_event(cur,tenant,str(incident_id),'closed',row[5],'closed',row[2],row[2],body.reason,email,role);conn.commit()
    finally:_state['release_db'](conn)
    return {'ok':True,'status':'closed'}

@router.get('/{incident_id}/timeline')
def timeline(incident_id:uuid.UUID,request:Request):
    user,email=_identity(request);tenant=_tenant(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            row=_load(cur,tenant,str(incident_id));role=_role(cur,tenant,email);_check(IncidentState(row[5],row[2],row[3]),role,row[1]==email)
            cur.execute("SELECT event_type,from_status,to_status,from_risk_level,to_risk_level,reason,actor_role,created_at FROM mission_incident_events WHERE tenant_id=%s AND incident_id=%s ORDER BY created_at",(tenant,str(incident_id)));items=[{'eventType':r[0],'fromStatus':r[1],'toStatus':r[2],'fromRiskLevel':r[3],'toRiskLevel':r[4],'reason':r[5],'actorRole':r[6],'createdAt':r[7].isoformat()} for r in cur.fetchall()]
    finally:_state['release_db'](conn)
    return {'ok':True,'items':items}
