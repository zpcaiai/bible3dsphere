from __future__ import annotations
from typing import Any,Dict,Literal,Optional
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field,field_validator
try:from backend.mission_bridge_auth import authorize
except Exception:from mission_bridge_auth import authorize
router=APIRouter(prefix='/api/mission-bridge/pilots/attention-reset',tags=['mission-bridge-attention-pilot']);_state:Dict[str,Any]={}
FLOW=['触发识别','环境改造','替代行为','每日短操练','同伴守望','失败恢复','身份和价值重建']
def init_mission_bridge_attention_pilot_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
def _auth(cur,user,tenant):return authorize(cur,user,'program.read',tenant,program_id='attention-reset-30',platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])))
@router.get('/dashboard')
def dashboard(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _auth(cur,user,tenant);uid=user['email'];cur.execute("SELECT COUNT(*),COALESCE(AVG(EXTRACT(EPOCH FROM(recovered_at-started_at))/3600),0) FROM mission_bridge_recovery_plans WHERE tenant_id=%s AND user_id=%s",(tenant,uid));recovery=cur.fetchone();cur.execute("SELECT COUNT(*) FROM attention_focus_sessions WHERE user_id=%s AND started_at>=now()-interval '30 days'",(uid,));focus=cur.fetchone()[0];cur.execute("SELECT COUNT(*) FROM attention_accountability_relationships WHERE (requester_user_id=%s OR partner_user_id=%s) AND status='active'",(uid,uid));partners=cur.fetchone()[0]
 finally:_state['release_db'](conn)
 return {'ok':True,'flow':FLOW,'metrics':{'focusSessions30d':focus,'accountabilityPartners':partners,'recoveryPlans':recovery[0],'averageRecoveryHours':round(float(recovery[1]),1)},'existingModulePaths':{'focus':'/attention/focus','review':'/attention/review','accountability':'/attention/accountability','weeklyReport':'/attention/report'},'privacyRules':['不上传色情内容','不保存具体搜索词','失败记录仅自己可见','不使用羞辱排行榜']}
class TriggerBody(BaseModel):
 triggerCategory:Literal['time','emotion','place','social','fatigue','other']
 intensity:int=Field(ge=1,le=5)
 contextSummary:str=Field(default='',max_length=240)
 @field_validator('contextSummary')
 @classmethod
 def no_explicit_terms(cls,value):
  if any(x in value.lower() for x in ('http://','https://','.com','搜索词','关键词')):raise ValueError('只记录触发类别，不保存链接或具体搜索词')
  return value
@router.post('/triggers')
def trigger(body:TriggerBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_trigger_logs(tenant_id,user_id,trigger_category,intensity,context_summary) VALUES(%s,%s,%s,%s,%s) RETURNING id",(tenant,user['email'],body.triggerCategory,body.intensity,body.contextSummary));tid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'triggerId':str(tid)}
class RecoveryBody(BaseModel):category:Literal['short_video','gaming','sexual_content','other'];severity:int=Field(ge=1,le=5);graceStatement:str=Field(min_length=4,max_length=1000);environmentChange:str=Field(min_length=4,max_length=1000);replacementAction:str=Field(min_length=4,max_length=1000);supportRequest:str=Field(default='',max_length=1000)
@router.post('/recovery')
def recovery(body:RecoveryBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_relapse_events(tenant_id,user_id,category,occurred_at,severity) VALUES(%s,%s,%s,now(),%s) RETURNING id",(tenant,user['email'],body.category,body.severity));eid=cur.fetchone()[0];cur.execute("INSERT INTO mission_bridge_recovery_plans(tenant_id,user_id,relapse_event_id,grace_statement,immediate_environment_change,replacement_action,support_request) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id",(tenant,user['email'],str(eid),body.graceStatement,body.environmentChange,body.replacementAction,body.supportRequest));pid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'recoveryPlanId':str(pid),'message':'复发不等于没有得救。现在从一个具体、可完成的恢复行动重新开始。','private':True}
