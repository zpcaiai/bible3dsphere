from __future__ import annotations
from fastapi import APIRouter,Depends,HTTPException,Request
from pydantic import BaseModel,Field
from core.tenancy import require_org_permission
from mission_bridge_auth import set_tenant_context
from mission_feature_guard import require_mission_feature
from mission_os.audit import audit

course_router=APIRouter(prefix='/api/v1/mission/courses',tags=['mission-learning'],dependencies=[Depends(require_mission_feature('mission_training_enabled'))])
supporter_router=APIRouter(prefix='/api/v1/mission/supporter-portal',tags=['mission-supporters'],dependencies=[Depends(require_mission_feature('mission_sending_enabled'))]);_state={}
def init_mission_learning_portal_router(**kw):_state.update(kw)
def _ctx(request):
 u=_state['get_session_user'](request);email=str((u or {}).get('email') or '')
 if not email:raise HTTPException(401,detail='请先登录')
 return email
def _role(cur,email,org,perm='view_dashboard'):
 if _state['is_admin'](email):return 'platform_admin'
 return require_org_permission(cur,email,org,perm)['role']
class CourseBody(BaseModel):organizationId:str;courseKey:str=Field(min_length=2,max_length=80);title:str=Field(min_length=2,max_length=200);summary:str|None=None
@course_router.post('')
def create_course(b:CourseBody,request:Request):
 e=_ctx(request);c=_state['get_db']()
 try:
  with c.cursor() as x:r=_role(x,e,b.organizationId,'manage_settings');set_tenant_context(x,b.organizationId);x.execute("INSERT INTO mission_course_catalog(tenant_id,course_key,title,summary,created_by) VALUES(%s,%s,%s,%s,%s) RETURNING id",(b.organizationId,b.courseKey,b.title,b.summary,e));i=x.fetchone()[0];audit(x,tenant_id=b.organizationId,actor_id=e,actor_role=r,action='create',resource_type='mission_course',resource_id=str(i),result='success');c.commit()
 finally:_state['release_db'](c)
 return {'ok':True,'courseId':str(i),'status':'draft'}
class LessonBody(BaseModel):organizationId:str;lessonKey:str;title:str;bodyMarkdown:str=Field(min_length=1,max_length=100000);sequenceOrder:int=0;estimatedMinutes:int=Field(default=15,ge=1,le=600);requiresHumanObservation:bool=False
@course_router.post('/{course_id}/lessons')
def add_lesson(course_id:str,b:LessonBody,request:Request):
 e=_ctx(request);c=_state['get_db']()
 try:
  with c.cursor() as x:r=_role(x,e,b.organizationId,'manage_settings');set_tenant_context(x,b.organizationId);x.execute("INSERT INTO mission_course_lessons(tenant_id,course_id,lesson_key,title,body_markdown,sequence_order,estimated_minutes,requires_human_observation) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",(b.organizationId,course_id,b.lessonKey,b.title,b.bodyMarkdown,b.sequenceOrder,b.estimatedMinutes,b.requiresHumanObservation));i=x.fetchone()[0];audit(x,tenant_id=b.organizationId,actor_id=e,actor_role=r,action='create',resource_type='mission_course_lesson',resource_id=str(i),result='success');c.commit()
 finally:_state['release_db'](c)
 return {'ok':True,'lessonId':str(i)}
class OrgBody(BaseModel):organizationId:str
@course_router.post('/{course_id}/publish')
def publish(course_id:str,b:OrgBody,request:Request):
 e=_ctx(request);c=_state['get_db']()
 try:
  with c.cursor() as x:r=_role(x,e,b.organizationId,'manage_settings');set_tenant_context(x,b.organizationId);x.execute("SELECT count(*) FROM mission_course_lessons WHERE tenant_id=%s AND course_id=%s",(b.organizationId,course_id));n=x.fetchone()[0]
  if not n:raise HTTPException(409,detail='课程至少需要一个课时')
  with c.cursor() as x:x.execute("UPDATE mission_course_catalog SET status='published',published_at=now(),updated_at=now() WHERE tenant_id=%s AND id=%s",(b.organizationId,course_id));c.commit()
 finally:_state['release_db'](c)
 return {'ok':True,'status':'published'}
@course_router.get('')
def courses(organizationId:str,request:Request):
 e=_ctx(request);c=_state['get_db']()
 try:
  with c.cursor() as x:_role(x,e,organizationId);set_tenant_context(x,organizationId);x.execute("SELECT id,course_key,title,summary,course_version,status FROM mission_course_catalog WHERE tenant_id=%s ORDER BY created_at DESC",(organizationId,));items=[{'id':str(r[0]),'courseKey':r[1],'title':r[2],'summary':r[3],'version':r[4],'status':r[5]} for r in x.fetchall()]
 finally:_state['release_db'](c)
 return {'ok':True,'items':items}
class JoinBody(BaseModel):organizationId:str;supportNetworkId:str;digestFrequency:str='weekly'
@supporter_router.post('/join')
def join(b:JoinBody,request:Request):
 e=_ctx(request);c=_state['get_db']()
 try:
  with c.cursor() as x:_role(x,e,b.organizationId);set_tenant_context(x,b.organizationId);x.execute("INSERT INTO mission_supporter_memberships(tenant_id,support_network_id,user_id,status) VALUES(%s,%s,%s,'active') ON CONFLICT(tenant_id,support_network_id,user_id) DO UPDATE SET status='active',unsubscribed_at=NULL RETURNING id",(b.organizationId,b.supportNetworkId,e));i=x.fetchone()[0];x.execute("INSERT INTO mission_supporter_preferences(tenant_id,membership_id,digest_frequency) VALUES(%s,%s,%s) ON CONFLICT(tenant_id,membership_id) DO UPDATE SET digest_frequency=excluded.digest_frequency",(b.organizationId,i,b.digestFrequency));c.commit()
 finally:_state['release_db'](c)
 return {'ok':True,'membershipId':str(i),'status':'active'}
@supporter_router.post('/{membership_id}/unsubscribe')
def unsubscribe(membership_id:str,b:OrgBody,request:Request):
 e=_ctx(request);c=_state['get_db']()
 try:
  with c.cursor() as x:set_tenant_context(x,b.organizationId);x.execute("UPDATE mission_supporter_memberships SET status='unsubscribed',unsubscribed_at=now() WHERE id=%s AND tenant_id=%s AND user_id=%s",(membership_id,b.organizationId,e));n=x.rowcount;c.commit()
 finally:_state['release_db'](c)
 if not n:raise HTTPException(404,detail='支持者成员不存在')
 return {'ok':True,'status':'unsubscribed'}
