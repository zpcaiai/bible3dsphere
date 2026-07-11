from __future__ import annotations
import json
from typing import Any,Dict,Literal,List
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field
try:from backend.mission_bridge_auth import authorize
except Exception:from mission_bridge_auth import authorize
router=APIRouter(prefix='/api/mission-bridge/modules/mental-health-families',tags=['mission-bridge-mental-health-families']);_state:Dict[str,Any]={}
RULES=['永远不建议停药','不将精神疾病等同于犯罪、软弱或邪灵','AI不解释患者行为的属灵原因','明确危险优先专业和紧急支持','普通小组长不能查看完整医疗信息']
def init_mission_bridge_mental_health_families_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
def _auth(cur,user,tenant):return authorize(cur,user,'program.read',tenant,platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])))
@router.get('/dashboard')
def dashboard(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("SELECT reminder_type,label,schedule,explicitly_enabled FROM mission_bridge_care_reminders WHERE tenant_id=%s AND owner_user_id=%s",(tenant,user['email']));reminders=[{'type':r[0],'label':r[1],'schedule':r[2],'enabled':r[3]} for r in cur.fetchall()]
 finally:_state['release_db'](conn)
 return {'ok':True,'rules':RULES,'features':['家属教育','复发预警','主动启用就诊和服药提醒','专业机构目录','家庭沟通','危机计划','同伴支持','污名和内疚重建'],'reminders':reminders}
class ReminderBody(BaseModel):reminderType:Literal['appointment','medication'];label:str=Field(min_length=2,max_length=200);schedule:Dict[str,Any];explicitlyEnabled:bool
@router.post('/reminders')
def reminder(body:ReminderBody,request:Request):
 if not body.explicitlyEnabled:raise HTTPException(409,detail='就诊和服药提醒必须由用户主动启用')
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_care_reminders(tenant_id,owner_user_id,reminder_type,label,schedule,explicitly_enabled) VALUES(%s,%s,%s,%s,%s::jsonb,TRUE) RETURNING id",(tenant,user['email'],body.reminderType,body.label,json.dumps(body.schedule)));rid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'reminderId':str(rid),'enabled':True}
class WarningBody(BaseModel):warningCategory:str=Field(min_length=2,max_length=100);observation:str=Field(min_length=4,max_length=2000);riskLevel:Literal['L0','L1','L2','L3']='L1'
@router.post('/warnings')
def warning(body:WarningBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _auth(cur,user,tenant);cur.execute("SELECT id FROM mission_bridge_family_mental_health_profiles WHERE tenant_id=%s AND owner_user_id=%s LIMIT 1",(tenant,user['email']));profile=cur.fetchone()
   if not profile:cur.execute("INSERT INTO mission_bridge_family_mental_health_profiles(tenant_id,owner_user_id,care_recipient_alias) VALUES(%s,%s,'家人') RETURNING id",(tenant,user['email']));profile=cur.fetchone()
   cur.execute("INSERT INTO mission_bridge_relapse_warning_logs(tenant_id,profile_id,warning_category,observation,risk_level) VALUES(%s,%s,%s,%s,%s) RETURNING id",(tenant,str(profile[0]),body.warningCategory,body.observation,body.riskLevel));wid=cur.fetchone()[0];incident=None
   if body.riskLevel in ('L2','L3'):cur.execute("INSERT INTO incident_reports(tenant_id,participant_id,reporter_user_id,risk_level,category,summary,immediate_danger) VALUES(%s,%s,%s,%s,'mental_health_crisis','家属记录明确危险，需专业和紧急支持',%s) RETURNING id",(tenant,user['email'],user['email'],body.riskLevel,body.riskLevel=='L3'));incident=cur.fetchone()[0]
   conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'warningId':str(wid),'incidentId':str(incident) if incident else None,'professionalFirst':body.riskLevel in ('L2','L3')}
def validate_ai_guidance(text:str)->None:
 forbidden=('停药','不要吃药','邪灵附体','因为犯罪','信心软弱导致')
 if any(term in text for term in forbidden):raise ValueError('mental_health_safety_policy_violation')
