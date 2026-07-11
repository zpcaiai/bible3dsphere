from __future__ import annotations
import json,uuid
from typing import Any,Dict
from fastapi import APIRouter,Depends,HTTPException,Request
from mission_feature_guard import require_mission_os
from pydantic import BaseModel,Field
try:
 from backend.mission_bridge_auth import authorize
 from backend.mission_bridge_training import evaluate_trainer_evidence
except Exception:
 from mission_bridge_auth import authorize
 from mission_bridge_training import evaluate_trainer_evidence
router=APIRouter(prefix='/api/mission-bridge/training',tags=['mission-bridge-training'],dependencies=[Depends(require_mission_os)]);_state:Dict[str,Any]={}
def init_mission_bridge_training_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
def _admin(cur,user,tenant):return authorize(cur,user,'program.manage',tenant,platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])))
@router.get('/dashboard')
def dashboard(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _admin(cur,user,tenant);counts={}
   for key,table in [('cohorts','mission_bridge_cohorts'),('mentors','mission_bridge_mentor_profiles'),('assignments','mission_bridge_mentor_assignments'),('candidates','mission_bridge_trainer_candidates')]:cur.execute(f'SELECT COUNT(*) FROM {table} WHERE tenant_id=%s',(tenant,));counts[key]=int(cur.fetchone()[0])
   cur.execute("SELECT id,title,program_id,capacity,status,starts_at FROM mission_bridge_cohorts WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 100",(tenant,));cohorts=[{'id':str(r[0]),'title':r[1],'programId':r[2],'capacity':r[3],'status':r[4],'startsAt':r[5].isoformat() if r[5] else None} for r in cur.fetchall()]
 finally:_state['release_db'](conn)
 return {'ok':True,'metrics':counts,'cohorts':cohorts}
class CohortBody(BaseModel):programId:str=Field(min_length=3,max_length=80);title:str=Field(min_length=3,max_length=160);capacity:int=Field(ge=2,le=200)
@router.post('/cohorts')
def create_cohort(body:CohortBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _admin(cur,user,tenant);cur.execute("SELECT active_version FROM mission_bridge_program_definitions WHERE id=%s AND status='published'",(body.programId,));row=cur.fetchone()
   if not row:raise HTTPException(404,detail='已发布项目不存在')
   cur.execute("INSERT INTO mission_bridge_cohorts(tenant_id,program_id,program_version,title,capacity,created_by) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id",(tenant,body.programId,row[0],body.title,body.capacity,user['email']));cid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'cohortId':str(cid),'programVersion':row[0]}
class MentorBody(BaseModel):userId:str=Field(min_length=3,max_length=255);capacity:int=Field(ge=1,le=20);matchingPreferences:dict=Field(default_factory=dict)
@router.post('/mentors')
def upsert_mentor(body:MentorBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_admin(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_mentor_profiles(tenant_id,user_id,capacity,matching_preferences) VALUES(%s,%s,%s,%s::jsonb) ON CONFLICT(tenant_id,user_id) DO UPDATE SET capacity=EXCLUDED.capacity,matching_preferences=EXCLUDED.matching_preferences RETURNING id",(tenant,body.userId,body.capacity,json.dumps(body.matchingPreferences)));mid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'mentorProfileId':str(mid)}
class AssignmentBody(BaseModel):mentorUserId:str;participantUserId:str;programId:str;preferenceMatch:dict=Field(default_factory=dict)
@router.post('/mentor-assignments')
def assign_mentor(body:AssignmentBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _admin(cur,user,tenant);cur.execute("SELECT capacity,(SELECT COUNT(*) FROM mission_bridge_mentor_assignments a WHERE a.tenant_id=p.tenant_id AND a.mentor_user_id=p.user_id AND a.status='active') FROM mission_bridge_mentor_profiles p WHERE tenant_id=%s AND user_id=%s AND status IN('approved','active')",(tenant,body.mentorUserId));row=cur.fetchone()
   if not row:raise HTTPException(409,detail='导师尚未通过人工审核')
   if int(row[1])>=int(row[0]):raise HTTPException(409,detail='导师已达到容量上限')
   cur.execute("INSERT INTO mission_bridge_mentor_assignments(tenant_id,mentor_user_id,participant_user_id,program_id,preference_match) VALUES(%s,%s,%s,%s,%s::jsonb) RETURNING id",(tenant,body.mentorUserId,body.participantUserId,body.programId,json.dumps(body.preferenceMatch)));aid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'assignmentId':str(aid),'requiresParticipantConsent':True}
class CandidateBody(BaseModel):userId:str; evidence:dict
@router.post('/trainer-candidates')
def submit_candidate(body:CandidateBody,request:Request):
 evaluation=evaluate_trainer_evidence(body.evidence);user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_admin(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_trainer_candidates(tenant_id,user_id,evidence,status,submitted_at) VALUES(%s,%s,%s::jsonb,%s,now()) RETURNING id",(tenant,body.userId,json.dumps(body.evidence),'under_review' if evaluation['eligibleForHumanReview'] else 'incomplete'));cid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'candidateId':str(cid),'evaluation':evaluation}
class ApprovalBody(BaseModel):decision:str=Field(pattern='^(approved|rejected|more_evidence)$');rationale:str=Field(min_length=10,max_length=2000)
@router.post('/trainer-candidates/{candidate_id}/decision')
def decide(candidate_id:uuid.UUID,body:ApprovalBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _admin(cur,user,tenant);cur.execute("SELECT evidence FROM mission_bridge_trainer_candidates WHERE id=%s AND tenant_id=%s FOR UPDATE",(str(candidate_id),tenant));row=cur.fetchone()
   if not row:raise HTTPException(404,detail='候选人不存在')
   evaluation=evaluate_trainer_evidence(row[0] or {})
   if body.decision=='approved' and not evaluation['eligibleForHumanReview']:raise HTTPException(409,detail='人工认证证据不完整')
   cur.execute("INSERT INTO mission_bridge_trainer_approvals(tenant_id,candidate_id,decision,reviewer_user_id,rationale) VALUES(%s,%s,%s,%s,%s)",(tenant,str(candidate_id),body.decision,user['email'],body.rationale));cur.execute("UPDATE mission_bridge_trainer_candidates SET status=%s WHERE id=%s",(body.decision,str(candidate_id)));conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'decision':body.decision,'humanApproved':body.decision=='approved','automaticApproval':False}
