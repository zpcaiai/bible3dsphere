from __future__ import annotations
from typing import Any,Dict
from fastapi import APIRouter,Request
from pydantic import BaseModel,Field
try:from backend.mission_bridge_auth import authorize
except Exception:from mission_bridge_auth import authorize
router=APIRouter(prefix='/api/mission-bridge/modules/elder-caregivers',tags=['mission-bridge-elder-caregivers']);_state:Dict[str,Any]={}
AI_BOUNDARIES=['不诊断失智','不提供药物方案','不承诺病情改善','不责备照护者产生愤怒','严重耗竭或自伤信号转真人处理']
def init_mission_bridge_elder_caregivers_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):from fastapi import HTTPException;raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
def _auth(cur,user,tenant):return authorize(cur,user,'program.read',tenant,platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])))
@router.get('/dashboard')
def dashboard(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("SELECT stress_level,sleep_minutes,fatigue,anger_present,created_at FROM mission_bridge_caregiver_assessments WHERE tenant_id=%s AND user_id=%s ORDER BY created_at DESC LIMIT 12",(tenant,user['email']));rows=cur.fetchall();cur.execute("SELECT resource_type,name,contact_summary,source_url FROM mission_bridge_caregiver_resources WHERE tenant_id=%s AND verified=TRUE",(tenant,));resources=[{'type':r[0],'name':r[1],'contact':r[2],'sourceUrl':r[3]} for r in cur.fetchall()]
 finally:_state['release_db'](conn)
 return {'ok':True,'project':'照护者也需要被照护','assessments':[{'stress':r[0],'sleepMinutes':r[1],'fatigue':r[2],'angerPresent':r[3],'createdAt':r[4].isoformat()} for r in rows],'resources':resources,'features':['每周支持小组','临终和哀伤资源','家庭责任分配会议','志愿者短时支持','医疗社工法律目录','祷告和情绪表达'],'aiBoundaries':AI_BOUNDARIES}
class AssessmentBody(BaseModel):stressLevel:int=Field(ge=1,le=5);sleepMinutes:int|None=Field(default=None,ge=0,le=1440);fatigue:int=Field(ge=1,le=5);angerPresent:bool=False;selfHarmSignal:bool=False
@router.post('/assessments')
def assessment(body:AssessmentBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']();level='L3' if body.selfHarmSignal else ('L2' if body.stressLevel==5 and body.fatigue==5 else 'L1')
 try:
  with conn.cursor() as cur:
   _auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_caregiver_assessments(tenant_id,user_id,stress_level,sleep_minutes,fatigue,anger_present,self_harm_signal) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id",(tenant,user['email'],body.stressLevel,body.sleepMinutes,body.fatigue,body.angerPresent,body.selfHarmSignal));aid=cur.fetchone()[0]
   incident=None
   if level in ('L2','L3'):cur.execute("INSERT INTO incident_reports(tenant_id,participant_id,reporter_user_id,risk_level,category,summary,immediate_danger,location_scope) VALUES(%s,%s,%s,%s,'caregiver_exhaustion','照护者评估触发真人关怀升级',%s,'undisclosed') RETURNING id",(tenant,user['email'],user['email'],level,level=='L3'));incident=cur.fetchone()[0]
   conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'assessmentId':str(aid),'supportLevel':level,'incidentId':str(incident) if incident else None,'diagnosis':None}
class RespiteBody(BaseModel):durationMinutes:int=Field(ge=30,le=480);supportScope:str=Field(min_length=4,max_length=1000)
@router.post('/respite')
def respite(body:RespiteBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_respite_requests(tenant_id,user_id,duration_minutes,support_scope) VALUES(%s,%s,%s,%s) RETURNING id",(tenant,user['email'],body.durationMinutes,body.supportScope));rid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'requestId':str(rid),'status':'requested'}
