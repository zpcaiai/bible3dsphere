from __future__ import annotations
import json
from typing import Any,Dict,List
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field
try:
 from backend.mission_bridge_auth import authorize
 from backend.routers.mission_audit import _recent_mfa
except Exception:
 from mission_bridge_auth import authorize
 from routers.mission_audit import _recent_mfa
router=APIRouter(prefix='/api/mission-bridge/operations',tags=['mission-bridge-operations']);_state:Dict[str,Any]={}
PAGES=['Dashboard','Programs','Participants','Cohorts','Sessions','Mentors','Facilitators','Content','Referrals','Incidents','Consent','Audit Logs','Analytics','Settings']
def init_mission_bridge_operations_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
def _auth(cur,user,tenant,permission='operations.manage'):return authorize(cur,user,permission,tenant,platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])))
def _step_up(user):
 if not _recent_mfa(user):raise HTTPException(403,detail='敏感页面需要最近10分钟内完成二次认证')
def _mask(value):
 value=str(value or '');return f'{value[:2]}***{value[-2:]}' if len(value)>4 else '***'
@router.get('/dashboard')
def dashboard(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _auth(cur,user,tenant);counts={}
   for key,table in [('programs','mission_bridge_program_definitions'),('participants','mission_bridge_enrollments'),('cohorts','mission_bridge_cohorts'),('incidents','incident_reports'),('content','mission_bridge_content_catalog')]:cur.execute(f"SELECT COUNT(*) FROM {table}"+(" WHERE tenant_id=%s" if table!='mission_bridge_program_definitions' else ''),(tenant,) if table!='mission_bridge_program_definitions' else ());counts[key]=cur.fetchone()[0]
 finally:_state['release_db'](conn)
 return {'ok':True,'pages':PAGES,'counts':counts,'sensitiveListsMasked':True}
@router.get('/participants')
def participants(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("SELECT id,user_id,program_id,status FROM mission_bridge_enrollments WHERE tenant_id=%s ORDER BY enrolled_at DESC LIMIT 200",(tenant,));items=[{'id':str(r[0]),'participant':_mask(r[1]),'programId':r[2],'status':r[3]} for r in cur.fetchall()]
 finally:_state['release_db'](conn)
 return {'ok':True,'items':items,'masked':True}
@router.get('/incidents')
def incidents(request:Request):
 user,tenant=_ctx(request);_step_up(user);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("SELECT id,risk_level,category,status FROM incident_reports WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 200",(tenant,));items=[{'id':str(r[0]),'riskLevel':r[1],'category':r[2],'status':r[3]} for r in cur.fetchall()]
 finally:_state['release_db'](conn)
 return {'ok':True,'items':items,'stepUpVerified':True}
class ExportBody(BaseModel):exportType:str=Field(min_length=2,max_length=80);filters:Dict[str,Any]={}
@router.post('/exports')
def export(body:ExportBody,request:Request):
 user,tenant=_ctx(request);_step_up(user);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant,'operations.export');cur.execute("INSERT INTO mission_bridge_data_exports(tenant_id,requested_by,export_type,filters) VALUES(%s,%s,%s,%s::jsonb) RETURNING id",(tenant,user['email'],body.exportType,json.dumps(body.filters)));eid=cur.fetchone()[0];cur.execute("INSERT INTO mission_bridge_audit_log(tenant_id,actor_user_id,action,target_type,target_id,metadata) VALUES(%s,%s,'operations.export.requested','data_export',%s,%s::jsonb)",(tenant,user['email'],str(eid),json.dumps({'exportType':body.exportType})));conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'exportId':str(eid),'audited':True}
class ImportRow(BaseModel):participantRef:str;consentSourceReference:str|None=None
class ImportBody(BaseModel):programId:str;sourceName:str;rows:List[ImportRow]=Field(max_length=5000)
@router.post('/imports')
def bulk_import(body:ImportBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']();valid=sum(bool(r.consentSourceReference) for r in body.rows)
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_bulk_imports(tenant_id,program_id,source_name,row_count,valid_consent_rows,rejected_rows,status,created_by) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",(tenant,body.programId,body.sourceName,len(body.rows),valid,len(body.rows)-valid,'ready' if valid==len(body.rows) else 'rejected',user['email']));iid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'importId':str(iid),'validConsentRows':valid,'rejectedRows':len(body.rows)-valid,'ready':valid==len(body.rows)}
class CampaignBody(BaseModel):programId:str;templateId:str
@router.post('/campaigns')
def campaign(body:CampaignBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant,'operations.campaign');cur.execute("SELECT review_status,unsubscribe_required FROM mission_bridge_message_templates WHERE id=%s AND tenant_id=%s",(body.templateId,tenant));template=cur.fetchone()
  if not template or template[0]!='approved' or not template[1]:raise HTTPException(409,detail='群发模板必须经过审核并支持取消订阅')
 finally:_state['release_db'](conn)
 return {'ok':True,'status':'ready','unsubscribeRequired':True}
