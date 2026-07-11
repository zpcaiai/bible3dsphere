from __future__ import annotations
import json
from typing import Any,Dict,List,Literal
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field
try:from backend.mission_bridge_auth import authorize
except Exception:from mission_bridge_auth import authorize
router=APIRouter(prefix='/api/mission-bridge/offline',tags=['mission-bridge-offline']);_state:Dict[str,Any]={}
def init_mission_bridge_offline_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
class Operation(BaseModel):clientOperationId:str;entityType:str;entityId:str;operation:Literal['create','update','checkin'];baseVersion:int=Field(ge=0);payload:Dict[str,Any]
class SyncBody(BaseModel):operations:List[Operation]=Field(max_length=500)
@router.post('/sync')
def sync(body:SyncBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']();applied=[];conflicts=[]
 try:
  with conn.cursor() as cur:
   authorize(cur,user,'program.read',tenant,platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])))
   for op in body.operations:
    risk=str(op.payload.get('riskLevel','L0'))
    if op.entityType in ('incident','safety_event') or risk in ('L2','L3'):raise HTTPException(409,detail='高风险事件不能通过普通离线队列同步，请立即联网提交或联系紧急支持')
    cur.execute("SELECT COALESCE(MAX(server_version),0) FROM mission_bridge_sync_operations WHERE tenant_id=%s AND entity_type=%s AND entity_id=%s",(tenant,op.entityType,op.entityId));server=cur.fetchone()[0]
    if op.operation!='create' and op.baseVersion!=server:cur.execute("INSERT INTO mission_bridge_sync_conflicts(tenant_id,user_id,client_operation_id,entity_type,entity_id,client_version,server_version) VALUES(%s,%s,%s,%s,%s,%s,%s)",(tenant,user['email'],op.clientOperationId,op.entityType,op.entityId,op.baseVersion,server));conflicts.append({'clientOperationId':op.clientOperationId,'serverVersion':server});continue
    next_version=server+1;cur.execute("INSERT INTO mission_bridge_sync_operations(tenant_id,user_id,client_operation_id,entity_type,entity_id,operation,base_version,payload,server_version) VALUES(%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s) ON CONFLICT(tenant_id,user_id,client_operation_id) DO NOTHING",(tenant,user['email'],op.clientOperationId,op.entityType,op.entityId,op.operation,op.baseVersion,json.dumps(op.payload,ensure_ascii=False),next_version));applied.append({'clientOperationId':op.clientOperationId,'serverVersion':next_version})
   conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'applied':applied,'conflicts':conflicts,'syncFailed':bool(conflicts)}
