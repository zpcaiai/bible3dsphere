from __future__ import annotations
import hashlib,json
from typing import Any,Dict,Literal
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field
try:from backend.mission_bridge_auth import authorize
except Exception:from mission_bridge_auth import authorize
router=APIRouter(prefix='/api/mission-bridge/pilots/ai-faith',tags=['mission-bridge-ai-faith']);_state:Dict[str,Any]={}
SESSIONS=['AI能否理解，还是只是在预测？','人的价值是否来自生产力？','意识、自由意志和责任','科技进步为何没有消除焦虑','道德能否只由社会共识产生','苦难是否推翻上帝存在','耶稣是宗教教师还是历史中的主','信仰、理性和个人回应']
def init_mission_bridge_ai_faith_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
def _auth(cur,user,tenant):return authorize(cur,user,'program.read',tenant,program_id='ai-faith-dialogue-8',platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])))
@router.get('/dashboard')
def dashboard(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _auth(cur,user,tenant);cur.execute("SELECT session_number,position,claim,evidence_type,source_content_id FROM mission_bridge_discussion_viewpoints WHERE tenant_id=%s ORDER BY session_number,position",(tenant,));views=[{'session':r[0],'position':r[1],'claim':r[2],'evidenceType':r[3],'sourceContentId':str(r[4]) if r[4] else None} for r in cur.fetchall()];cur.execute("SELECT invitation_type,status FROM mission_bridge_followup_invitations WHERE tenant_id=%s AND user_id=%s ORDER BY created_at DESC",(tenant,user['email']));followups=[{'type':r[0],'status':r[1]} for r in cur.fetchall()]
 finally:_state['release_db'](conn)
 return {'ok':True,'sessions':[{'number':i+1,'title':x} for i,x in enumerate(SESSIONS)],'viewpoints':views,'followups':followups,'boundaries':['公平呈现重要反对意见','区分哲学推论与实证结论','引用已审核来源','不判断用户信仰状态'],'excludedMetric':'决志数量'}
class QuestionBody(BaseModel):sessionNumber:int=Field(ge=1,le=8);question:str=Field(min_length=4,max_length=2000)
@router.post('/questions')
def question(body:QuestionBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']();anon=hashlib.sha256(f"{tenant}:{user['email']}".encode()).hexdigest()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_anonymous_questions(tenant_id,session_number,user_id_hash,question) VALUES(%s,%s,%s,%s) RETURNING id",(tenant,body.sessionNumber,anon,body.question));qid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'questionId':str(qid),'anonymous':True}
class FollowupBody(BaseModel):invitationType:Literal['further_reading','one_to_one','gospel_core_course'];participantRequested:bool
@router.post('/followups')
def followup(body:FollowupBody,request:Request):
 if not body.participantRequested:raise HTTPException(409,detail='后续邀请只能由参与者主动选择')
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_followup_invitations(tenant_id,user_id,invitation_type,participant_requested,status) VALUES(%s,%s,%s,TRUE,'requested') RETURNING id",(tenant,user['email'],body.invitationType));fid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'followupId':str(fid),'participantRequested':True}
class LearningBody(BaseModel):sessionNumber:int=Field(ge=1,le=8);understandingBefore:int=Field(ge=1,le=5);understandingAfter:int=Field(ge=1,le=5);questionAsked:bool=False;completed:bool=True
@router.post('/learning')
def learning(body:LearningBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_viewpoint_learning(tenant_id,user_id,session_number,understanding_before,understanding_after,question_asked,completed) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id",(tenant,user['email'],body.sessionNumber,body.understandingBefore,body.understandingAfter,body.questionAsked,body.completed));lid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'learningId':str(lid)}
