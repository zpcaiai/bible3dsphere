from __future__ import annotations
from typing import Any,Dict,Literal
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field
try:from backend.mission_bridge_auth import authorize
except Exception:from mission_bridge_auth import authorize
router=APIRouter(prefix='/api/mission-bridge/modules/reentry',tags=['mission-bridge-reentry']);_state:Dict[str,Any]={}
PRIVACY=['犯罪记录仅限授权角色查看','不向普通小组公开','不在见证或募款中暴露身份','不用犯罪经历作为长期标签','不使用AI预测再犯罪风险']
def init_mission_bridge_reentry_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
def _auth(cur,user,tenant):return authorize(cur,user,'program.read',tenant,platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])))
@router.get('/dashboard')
def dashboard(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("SELECT id,pseudonym,participant_type FROM mission_bridge_reentry_profiles WHERE tenant_id=%s AND owner_user_id=%s",(tenant,user['email']));p=cur.fetchone()
 finally:_state['release_db'](conn)
 return {'ok':True,'profile':{'id':str(p[0]),'pseudonym':p[1],'participantType':p[2]} if p else None,'features':['家庭关系修复','儿童支持','就业资源','技能培训','证件和公共服务导航','成瘾转介','债务转介','同伴导师','社区融入','自愿信仰探索'],'privacy':PRIVACY}
class ProfileBody(BaseModel):pseudonym:str=Field(min_length=2,max_length=80);participantType:Literal['incarcerated_family','released_person'];criminalRecordDetail:str=Field(default='',max_length=5000)
@router.put('/profile')
def profile(body:ProfileBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_reentry_profiles(tenant_id,owner_user_id,pseudonym,participant_type,criminal_record_encrypted,long_term_label) VALUES(%s,%s,%s,%s,%s,NULL) RETURNING id",(tenant,user['email'],body.pseudonym,body.participantType,body.criminalRecordDetail));pid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'profileId':str(pid),'criminalRecordVisibility':'authorized_only','longTermLabel':None}
class FaithChoiceBody(BaseModel):optIn:bool
@router.post('/faith-choice')
def faith_choice(body:FaithChoiceBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("SELECT id FROM mission_bridge_reentry_profiles WHERE tenant_id=%s AND owner_user_id=%s",(tenant,user['email']));p=cur.fetchone()
  if not p:raise HTTPException(409,detail='请先建立支持档案')
  with conn.cursor() as cur:cur.execute("INSERT INTO mission_bridge_reentry_faith_choices(tenant_id,profile_id,faith_exploration_opt_in) VALUES(%s,%s,%s) RETURNING id",(tenant,str(p[0]),body.optIn));fid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'choiceId':str(fid),'optIn':body.optIn}
def predict_recidivism(*args,**kwargs):raise RuntimeError('recidivism_prediction_prohibited')
