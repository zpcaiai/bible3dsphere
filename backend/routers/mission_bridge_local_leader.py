from __future__ import annotations
import json
from typing import Any,Dict,List,Optional
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field
try:from backend.mission_bridge_auth import authorize
except Exception:from mission_bridge_auth import authorize
router=APIRouter(prefix='/api/mission-bridge/pilots/local-leader',tags=['mission-bridge-local-leader']);_state:Dict[str,Any]={}
WEEKS=['带领者身份、呼召与边界','如何观察经文而不是先讲观点','经文背景、上下文和结构','从经文到中心信息','从真理到具体实践','如何提出开放式问题','如何倾听而不是立即教训','小组冲突与修复','识别精神健康和危机转介','培养副组长','权力、保密和反操控','设计下一轮门徒训练']
def init_mission_bridge_local_leader_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
def _auth(cur,user,tenant):return authorize(cur,user,'program.read',tenant,program_id='local-leader-90',platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])))
@router.get('/dashboard')
def dashboard(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _auth(cur,user,tenant);cur.execute("SELECT week,what_happened,next_change FROM mission_bridge_leadership_reviews WHERE tenant_id=%s AND user_id=%s ORDER BY week",(tenant,user['email']));reviews=[{'week':r[0],'whatHappened':r[1],'nextChange':r[2]} for r in cur.fetchall()];cur.execute("SELECT id,apprentice_name,development_goal,status FROM mission_bridge_apprentice_plans WHERE tenant_id=%s AND leader_user_id=%s",(tenant,user['email']));apprentices=[{'id':str(r[0]),'name':r[1],'goal':r[2],'status':r[3]} for r in cur.fetchall()]
 finally:_state['release_db'](conn)
 return {'ok':True,'programId':'local-leader-90','weeks':[{'week':i+1,'title':title} for i,title in enumerate(WEEKS)],'reviews':reviews,'apprentices':apprentices,'aiBoundary':'AI 只帮助观察、提问与标记争议，不默认生成可照读讲章。'}
class ObservationBody(BaseModel):passageReference:str=Field(min_length=2,max_length=100);observation:str=Field(min_length=5,max_length=5000);contextNotes:str='';structureNotes:str='';centralMessage:str='';applicationQuestions:List[str]=Field(default_factory=list,max_length=12)
@router.post('/observations')
def observation(body:ObservationBody,request:Request):
 forbidden=('神告诉你','神明确对你说','God told you');flags=['可能存在权威化表达，请人工修订'] if any(x.lower() in (body.centralMessage+' '+body.observation).lower() for x in forbidden) else []
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_leader_workspaces(tenant_id,user_id,passage_reference) VALUES(%s,%s,%s) RETURNING id",(tenant,user['email'],body.passageReference));wid=cur.fetchone()[0];cur.execute("INSERT INTO mission_bridge_scripture_observations(tenant_id,workspace_id,observation,context_notes,structure_notes,central_message,application_questions,controversy_flags) VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb) RETURNING id",(tenant,str(wid),body.observation,body.contextNotes,body.structureNotes,body.centralMessage,json.dumps(body.applicationQuestions,ensure_ascii=False),json.dumps(flags,ensure_ascii=False)));oid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'workspaceId':str(wid),'observationId':str(oid),'flags':flags,'observationPrompts':['这段经文重复了什么？','上下文限制了哪些解释？','作者原本要回应什么？']}
class ReviewBody(BaseModel):week:int=Field(ge=1,le=12);whatHappened:str=Field(min_length=5,max_length=3000);whatWasHeard:str=Field(min_length=5,max_length=3000);nextChange:str=Field(min_length=5,max_length=3000);referralCategories:List[str]=Field(default_factory=list,max_length=20)
@router.post('/weekly-reviews')
def weekly_review(body:ReviewBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_leadership_reviews(tenant_id,user_id,week,what_happened,what_was_heard,next_change,referral_categories) VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT(tenant_id,user_id,week) DO UPDATE SET what_happened=EXCLUDED.what_happened,what_was_heard=EXCLUDED.what_was_heard,next_change=EXCLUDED.next_change,referral_categories=EXCLUDED.referral_categories",(tenant,user['email'],body.week,body.whatHappened,body.whatWasHeard,body.nextChange,json.dumps(body.referralCategories,ensure_ascii=False)));conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'week':body.week}
class ApprenticeBody(BaseModel):name:str=Field(min_length=2,max_length=120);developmentGoal:str=Field(min_length=5,max_length=1000);practiceSteps:List[str]=Field(min_length=1,max_length=20);consentConfirmed:bool
@router.post('/apprentices')
def apprentice(body:ApprenticeBody,request:Request):
 if not body.consentConfirmed:raise HTTPException(409,detail='副组长本人必须知情同意')
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_apprentice_plans(tenant_id,leader_user_id,apprentice_name,consent_confirmed,development_goal,practice_steps) VALUES(%s,%s,%s,TRUE,%s,%s::jsonb) RETURNING id",(tenant,user['email'],body.name,body.developmentGoal,json.dumps(body.practiceSteps,ensure_ascii=False)));pid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'planId':str(pid)}
