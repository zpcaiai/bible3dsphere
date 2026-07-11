"""Mission audit, lineage and fail-closed break-glass workflows."""
from __future__ import annotations
import os,uuid
from datetime import datetime,timedelta,timezone
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field
from mission_os.audit import audit
from mission_os.outbox import enqueue

router=APIRouter(prefix="/api/v1/mission",tags=["mission-audit"]);_state={}
def init_mission_audit_router(*,get_db,release_db,get_session_user,is_admin):_state.update(locals())

def _identity(request):
    user=_state['get_session_user'](request);email=str((user or {}).get('email') or '')
    if not email:raise HTTPException(401,detail='请先登录')
    return user,email
def _tenant(request):return (request.headers.get('X-Tenant-Id') or 'public')[:80]
def _role(cur,tenant,email):
    if _state['is_admin'](email):return 'platform_admin'
    cur.execute("SELECT role_key FROM mission_bridge_tenant_memberships WHERE tenant_id=%s AND user_id=%s AND status='active' ORDER BY created_at DESC LIMIT 1",(tenant,email));row=cur.fetchone()
    return str(row[0]) if row else None
def _require(cur,tenant,email,allowed):
    role=_role(cur,tenant,email)
    if role not in allowed:raise HTTPException(403,detail='需要审计或安全权限')
    return role
def _recent_mfa(user):
    if not user.get('mfa_verified'):return False
    raw=user.get('mfa_verified_at')
    try:verified=datetime.fromisoformat(str(raw).replace('Z','+00:00'))
    except (TypeError,ValueError):return False
    return verified.tzinfo is not None and datetime.now(timezone.utc)-verified<=timedelta(minutes=10)

@router.get('/audit')
def list_audit(request:Request,action:str|None=None,resource_type:str|None=None,limit:int=100):
    user,email=_identity(request);tenant=_tenant(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            _require(cur,tenant,email,{'platform_admin','auditor','safeguarding_officer','child_protection_officer'})
            cur.execute("SELECT id,actor_id,actor_role,action,resource_type,resource_id,field_names_changed,reason,result,created_at FROM mission_audit_logs WHERE tenant_id=%s AND (%s IS NULL OR action=%s) AND (%s IS NULL OR resource_type=%s) ORDER BY created_at DESC LIMIT %s",(tenant,action,action,resource_type,resource_type,min(max(limit,1),200)))
            items=[{'id':str(r[0]),'actorId':r[1],'actorRole':r[2],'action':r[3],'resourceType':r[4],'resourceId':r[5],'changedFields':r[6],'reason':r[7],'result':r[8],'createdAt':r[9].isoformat()} for r in cur.fetchall()]
    finally:_state['release_db'](conn)
    return {'ok':True,'items':items}

@router.get('/data-lineage/{resource_type}/{resource_id}')
def lineage(resource_type:str,resource_id:str,request:Request):
    user,email=_identity(request);tenant=_tenant(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            _require(cur,tenant,email,{'platform_admin','auditor','safeguarding_officer'})
            cur.execute("WITH RECURSIVE graph AS (SELECT derived_resource_type,derived_resource_id,source_resource_type,source_resource_id,transformation_type,model_run_id,1 depth FROM mission_data_lineage WHERE tenant_id=%s AND derived_resource_type=%s AND derived_resource_id=%s UNION ALL SELECT l.derived_resource_type,l.derived_resource_id,l.source_resource_type,l.source_resource_id,l.transformation_type,l.model_run_id,g.depth+1 FROM mission_data_lineage l JOIN graph g ON l.derived_resource_type=g.source_resource_type AND l.derived_resource_id=g.source_resource_id WHERE l.tenant_id=%s AND g.depth<8) SELECT * FROM graph",(tenant,resource_type,resource_id,tenant));items=[{'derivedType':r[0],'derivedId':r[1],'sourceType':r[2],'sourceId':r[3],'transformation':r[4],'modelRunId':r[5],'depth':r[6]} for r in cur.fetchall()]
    finally:_state['release_db'](conn)
    return {'ok':True,'items':items}

class BreakGlassBody(BaseModel):
    targetType:str=Field(min_length=2,max_length=80);targetId:str=Field(min_length=1,max_length=128);reason:str=Field(min_length=12,max_length=500)
@router.post('/break-glass')
def break_glass(body:BreakGlassBody,request:Request):
    user,email=_identity(request)
    if not _recent_mfa(user):raise HTTPException(403,detail='Break-glass 需要最近 10 分钟内完成二次认证')
    tenant=_tenant(request);conn=_state['get_db']()
    try:
        with conn.cursor() as cur:
            role=_require(cur,tenant,email,{'platform_admin','safeguarding_officer','child_protection_officer'})
            cur.execute("INSERT INTO mission_break_glass_access(tenant_id,actor_id,target_type,target_id,reason,expires_at) VALUES(%s,%s,%s,%s,%s,now()+interval '30 minutes') RETURNING id,expires_at",(tenant,email,body.targetType,body.targetId,body.reason));row=cur.fetchone()
            cur.execute("INSERT INTO mission_post_access_reviews(tenant_id,break_glass_id) VALUES(%s,%s)",(tenant,row[0]))
            audit(cur,tenant_id=tenant,actor_id=email,actor_role=role,action='break_glass_access',resource_type=body.targetType,resource_id=body.targetId,result='granted',reason='life-safety emergency access',request_id=request.headers.get('X-Request-Id'))
            enqueue(cur,tenant_id=tenant,aggregate_type='BreakGlassAccess',aggregate_id=str(row[0]),event_type='MissionBreakGlassAccessGranted',event_version=1,actor_id=email,correlation_id=request.headers.get('X-Request-Id') or str(uuid.uuid4()),data={'break_glass_id':str(row[0]),'target_type':body.targetType,'review_required':True})
            conn.commit()
    finally:_state['release_db'](conn)
    return {'ok':True,'accessId':str(row[0]),'expiresAt':row[1].isoformat(),'postAccessReviewRequired':True}
