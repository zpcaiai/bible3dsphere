from __future__ import annotations
import json,time,uuid
from typing import Any,Dict,Literal,Optional
from fastapi import APIRouter,Depends,HTTPException,Request
from mission_feature_guard import require_mission_os
from pydantic import BaseModel,Field
try:
 from backend.mission_bridge_agents import AGENTS,input_hash,orchestrate
 from backend.mission_bridge_auth import authorize
except Exception:
 from mission_bridge_agents import AGENTS,input_hash,orchestrate
 from mission_bridge_auth import authorize
router=APIRouter(prefix='/api/mission-bridge/agents',tags=['mission-bridge-agents'],dependencies=[Depends(require_mission_os)]);_state:Dict[str,Any]={}
def init_mission_bridge_agents_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
def _auth(cur,user,permission,tenant):return authorize(cur,user,permission,tenant,platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])))
class RunBody(BaseModel):
 agentKey:str;message:str=Field(min_length=2,max_length=8000);programId:Optional[str]=None;goal:Optional[str]=Field(default=None,max_length=1000);currentRisk:Literal['L0','L1','L2','L3']='L0'
class ProgramSettingBody(BaseModel):aiEnabled:bool
@router.put('/programs/{program_id}/settings')
def program_setting(program_id:str,body:ProgramSettingBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,'agent.manage',tenant);cur.execute("INSERT INTO mission_bridge_agent_program_settings(tenant_id,program_id,ai_enabled,auto_messages_enabled,updated_by) VALUES(%s,%s,%s,FALSE,%s) ON CONFLICT(tenant_id,program_id) DO UPDATE SET ai_enabled=EXCLUDED.ai_enabled,auto_messages_enabled=FALSE,updated_by=EXCLUDED.updated_by,updated_at=now()",(tenant,program_id,body.aiEnabled,user['email']));conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'programId':program_id,'aiEnabled':body.aiEnabled,'autoMessagesEnabled':False}
@router.get('/catalog')
def catalog(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,'agent.use',tenant)
 finally:_state['release_db'](conn)
 return {'ok':True,'agents':[{'key':key,**value} for key,value in AGENTS.items()]}
@router.post('/runs')
def run_agent(body:RunBody,request:Request):
 if body.agentKey not in AGENTS:raise HTTPException(422,detail='不支持的 Agent')
 user,tenant=_ctx(request);conn=_state['get_db']();started=time.monotonic();digest=input_hash(body.message)
 try:
  with conn.cursor() as cur:
   _auth(cur,user,'agent.use',tenant);cur.execute("SELECT granted FROM mission_bridge_consent_records WHERE tenant_id=%s AND user_id=%s AND consent_type='ai_assistance'",(tenant,user['email']));consent=cur.fetchone()
   if not consent or not consent[0]:raise HTTPException(409,detail='请先在隐私中心明确开启 AI 辅助同意')
   if body.programId:
    cur.execute("SELECT ai_enabled FROM mission_bridge_agent_program_settings WHERE tenant_id=%s AND program_id=%s",(tenant,body.programId));setting=cur.fetchone()
    if setting and not setting[0]:raise HTTPException(409,detail='该项目已关闭 AI')
   cur.execute("SELECT id,title FROM mission_bridge_programs WHERE tenant_id=%s AND status='published' ORDER BY created_at DESC LIMIT 3",(tenant,));programs=[{'id':str(r[0]),'title':r[1]} for r in cur.fetchall()]
   referrals=[]
   if body.agentKey=='referral_assistant':cur.execute("SELECT name,region,professional_type,opening_hours,phone,address,source_url,verified FROM mission_bridge_referral_directory WHERE tenant_id=%s AND verified=TRUE LIMIT 3",(tenant,));referrals=[dict(zip(('name','region','professionalType','openingHours','phone','address','sourceUrl','verified'),r)) for r in cur.fetchall()]
   cur.execute("SELECT prompt_version FROM mission_bridge_prompt_registry WHERE tenant_id IN(%s,'public') AND agent_key=%s AND active=TRUE ORDER BY CASE WHEN tenant_id=%s THEN 0 ELSE 1 END LIMIT 1",(tenant,body.agentKey,tenant));prompt=cur.fetchone();prompt_version=prompt[0] if prompt else '1.0.0';result=orchestrate(body.agentKey,body.message,body.goal,programs,referrals,body.currentRisk);status='human_review_required' if result['output']['requiresHumanReview'] else 'draft'
   cur.execute("INSERT INTO mission_bridge_agent_runs(tenant_id,user_id,program_id,agent_key,status,request_class,input_hash,risk_level,structured_output,safety_flags) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb) RETURNING id,created_at",(tenant,user['email'],body.programId,body.agentKey,status,'user_request',digest,result['riskLevel'],json.dumps(result['output'],ensure_ascii=False),json.dumps(result['safetyFlags'])));row=cur.fetchone();latency=int((time.monotonic()-started)*1000)
   input_tokens=max(1,len(body.message)//4);output_tokens=max(1,len(json.dumps(result['output'],ensure_ascii=False))//4);cur.execute("INSERT INTO mission_bridge_model_runs(tenant_id,agent_run_id,model,prompt_version,input_hash,output,token_usage,latency_ms,safety_flags) VALUES(%s,%s,'deterministic-safety-orchestrator',%s,%s,%s::jsonb,%s::jsonb,%s,%s::jsonb)",(tenant,str(row[0]),prompt_version,digest,json.dumps(result['output'],ensure_ascii=False),json.dumps({'inputTokens':input_tokens,'outputTokens':output_tokens}),latency,json.dumps(result['safetyFlags'])));cur.execute("INSERT INTO mission_bridge_model_cost_events(tenant_id,agent_run_id,model,input_tokens,output_tokens,estimated_cost_usd,latency_ms) VALUES(%s,%s,'deterministic-safety-orchestrator',%s,%s,0,%s)",(tenant,str(row[0]),input_tokens,output_tokens,latency));cur.execute("INSERT INTO mission_bridge_agent_audit_log(tenant_id,agent_run_id,actor_user_id,event_type,metadata) VALUES(%s,%s,%s,'agent.run.created',%s::jsonb)",(tenant,str(row[0]),user['email'],json.dumps({'inputHash':digest,'agentKey':body.agentKey,'riskLevel':result['riskLevel'],'promptVersion':prompt_version})));conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'runId':str(row[0]),'status':status,'result':result['output'],'safetyFlags':result['safetyFlags'],'createdAt':row[1].isoformat()}
class ReviewBody(BaseModel):decision:Literal['approved','amended','rejected'];amendedOutput:Optional[Dict[str,Any]]=None;notes:str=Field(min_length=4,max_length=2000)
@router.post('/runs/{run_id}/reviews')
def review_run(run_id:uuid.UUID,body:ReviewBody,request:Request):
 if body.decision=='amended' and not body.amendedOutput:raise HTTPException(422,detail='修改审核必须提交 amendedOutput')
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _auth(cur,user,'agent.review',tenant);cur.execute("SELECT id FROM mission_bridge_agent_runs WHERE id=%s AND tenant_id=%s FOR UPDATE",(str(run_id),tenant))
   if not cur.fetchone():raise HTTPException(404,detail='Agent 运行不存在')
   cur.execute("SELECT COALESCE(MAX(revision),0)+1 FROM mission_bridge_human_reviews WHERE agent_run_id=%s",(str(run_id),));revision=cur.fetchone()[0];cur.execute("INSERT INTO mission_bridge_human_reviews(tenant_id,agent_run_id,reviewer_user_id,decision,amended_output,notes,revision) VALUES(%s,%s,%s,%s,%s::jsonb,%s,%s)",(tenant,str(run_id),user['email'],body.decision,json.dumps(body.amendedOutput,ensure_ascii=False) if body.amendedOutput else None,body.notes,revision));status='approved' if body.decision in ('approved','amended') else 'rejected';cur.execute("UPDATE mission_bridge_agent_runs SET status=%s,human_override_locked=%s WHERE id=%s",(status,body.decision=='amended',str(run_id)));conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'runId':str(run_id),'status':status,'revision':revision,'humanOverrideLocked':body.decision=='amended'}
@router.get('/runs')
def history(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _auth(cur,user,'agent.use',tenant);cur.execute("SELECT r.id,r.agent_key,r.status,r.risk_level,COALESCE(h.amended_output,r.structured_output),r.created_at FROM mission_bridge_agent_runs r LEFT JOIN LATERAL(SELECT amended_output FROM mission_bridge_human_reviews WHERE agent_run_id=r.id AND decision='amended' ORDER BY revision DESC LIMIT 1)h ON TRUE WHERE r.tenant_id=%s AND r.user_id=%s ORDER BY r.created_at DESC LIMIT 50",(tenant,user['email']));items=[{'id':str(x[0]),'agentKey':x[1],'status':x[2],'riskLevel':x[3],'result':x[4],'createdAt':x[5].isoformat()} for x in cur.fetchall()]
 finally:_state['release_db'](conn)
 return {'ok':True,'items':items}
