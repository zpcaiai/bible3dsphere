from __future__ import annotations
from typing import Any,Dict,Literal,Optional
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field
try:from backend.mission_bridge_auth import authorize
except Exception:from mission_bridge_auth import authorize
router=APIRouter(prefix='/api/mission-bridge/modules/mobile-families',tags=['mission-bridge-mobile-families']);_state:Dict[str,Any]={}
MODULES=['夫妻关系','亲子沟通','儿童阅读','城市适应','返乡适应','职业成长','家庭财务基础','信仰探索','家庭小组']
def init_mission_bridge_mobile_families_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
def _auth(cur,user,tenant):return authorize(cur,user,'program.read',tenant,platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])))
@router.get('/dashboard')
def dashboard(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _auth(cur,user,tenant);cur.execute("SELECT id,city_code,return_home_planned FROM mission_bridge_family_households WHERE tenant_id=%s AND owner_user_id=%s",(tenant,user['email']));home=cur.fetchone();children=[];tasks=[]
   if home:
    cur.execute("SELECT id,name_alias,age_band,school_name,guardian_consent FROM mission_bridge_family_children WHERE tenant_id=%s AND household_id=%s",(tenant,str(home[0])));children=[{'id':str(r[0]),'nameAlias':r[1],'ageBand':r[2],'schoolName':r[3],'guardianConsent':r[4]} for r in cur.fetchall()];cur.execute("SELECT id,module_key,title,status,voluntary_faith_content FROM mission_bridge_family_tasks WHERE tenant_id=%s AND household_id=%s ORDER BY created_at",(tenant,str(home[0])));tasks=[{'id':str(r[0]),'moduleKey':r[1],'title':r[2],'status':r[3],'voluntaryFaithContent':r[4]} for r in cur.fetchall()]
 finally:_state['release_db'](conn)
 return {'ok':True,'household':{'id':str(home[0]),'cityCode':home[1],'returnHomePlanned':home[2]} if home else None,'children':children,'tasks':tasks,'modules':MODULES,'boundaries':['儿童与父母信息分表','学校信息选填','不收集户籍','经济困难限制访问','儿童不得被单独营销或邀请']}
class HouseholdBody(BaseModel):cityCode:str=Field(min_length=2,max_length=40);returnHomePlanned:bool=False
@router.put('/household')
def household(body:HouseholdBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_family_households(tenant_id,owner_user_id,city_code,return_home_planned) VALUES(%s,%s,%s,%s) ON CONFLICT(tenant_id,owner_user_id) DO UPDATE SET city_code=EXCLUDED.city_code,return_home_planned=EXCLUDED.return_home_planned RETURNING id",(tenant,user['email'],body.cityCode,body.returnHomePlanned));hid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'householdId':str(hid)}
class ChildBody(BaseModel):nameAlias:str=Field(min_length=1,max_length=80);ageBand:Literal['0-5','6-9','10-12','13-15','16-17'];schoolName:Optional[str]=Field(default=None,max_length=160);guardianConsent:bool
@router.post('/children')
def child(body:ChildBody,request:Request):
 if not body.guardianConsent:raise HTTPException(409,detail='添加儿童信息需要监护人同意')
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("SELECT id FROM mission_bridge_family_households WHERE tenant_id=%s AND owner_user_id=%s",(tenant,user['email']));home=cur.fetchone()
  if not home:raise HTTPException(409,detail='请先建立家庭档案')
  with conn.cursor() as cur:cur.execute("INSERT INTO mission_bridge_family_children(tenant_id,household_id,name_alias,age_band,school_name,guardian_consent) VALUES(%s,%s,%s,%s,%s,TRUE) RETURNING id",(tenant,str(home[0]),body.nameAlias,body.ageBand,body.schoolName));cid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'childId':str(cid),'marketingEligible':False}
class TaskBody(BaseModel):moduleKey:Literal['couple_relationship','parent_child','child_reading','city_adaptation','return_home','career_growth','family_finance','faith_exploration','family_group'];title:str=Field(min_length=3,max_length=500);voluntaryFaithContent:bool=False
@router.post('/tasks')
def task(body:TaskBody,request:Request):
 if body.moduleKey=='faith_exploration' and not body.voluntaryFaithContent:raise HTTPException(409,detail='家庭信仰讨论必须由家庭主动选择')
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("SELECT id FROM mission_bridge_family_households WHERE tenant_id=%s AND owner_user_id=%s",(tenant,user['email']));home=cur.fetchone()
  if not home:raise HTTPException(409,detail='请先建立家庭档案')
  with conn.cursor() as cur:cur.execute("INSERT INTO mission_bridge_family_tasks(tenant_id,household_id,module_key,title,voluntary_faith_content) VALUES(%s,%s,%s,%s,%s) RETURNING id",(tenant,str(home[0]),body.moduleKey,body.title,body.voluntaryFaithContent));tid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'taskId':str(tid)}
