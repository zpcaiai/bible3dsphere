from __future__ import annotations
from typing import Any,Dict,Literal
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field
try:from backend.mission_bridge_auth import authorize
except Exception:from mission_bridge_auth import authorize
router=APIRouter(prefix='/api/mission-bridge/modules/family-transitions',tags=['mission-bridge-family-transitions']);_state:Dict[str,Any]={}
PATHWAYS={'single_parent':'单亲家庭支持','divorced':'离异后的身份和生活重建','widowed':'丧偶后的哀伤陪伴'}
def init_mission_bridge_family_transitions_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
def _auth(cur,user,tenant):return authorize(cur,user,'program.read',tenant,platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])))
@router.get('/dashboard')
def dashboard(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("SELECT pathway FROM mission_bridge_family_transition_profiles WHERE tenant_id=%s AND user_id=%s",(tenant,user['email']));p=cur.fetchone()
 finally:_state['release_db'](conn)
 return {'ok':True,'pathways':[{'key':k,'title':v} for k,v in PATHWAYS.items()],'selectedPathway':p[0] if p else None,'features':['儿童照看资源','家庭预算工具','哀伤进程记录','节庆孤独支持','家庭活动','同伴网络','法律转介'],'principle':'不以再婚作为默认目标'}
class ProfileBody(BaseModel):pathway:Literal['single_parent','divorced','widowed']
@router.put('/profile')
def profile(body:ProfileBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_family_transition_profiles(tenant_id,user_id,pathway,remarriage_goal) VALUES(%s,%s,%s,NULL) ON CONFLICT(tenant_id,user_id) DO UPDATE SET pathway=EXCLUDED.pathway,remarriage_goal=NULL",(tenant,user['email'],body.pathway));conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'pathway':body.pathway,'remarriageGoal':None}
class GriefBody(BaseModel):emotion:str=Field(min_length=2,max_length=80);lossImpact:str=Field(min_length=4,max_length=2000);supportNeeded:str=Field(default='',max_length=1000)
@router.post('/grief')
def grief(body:GriefBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_grief_logs(tenant_id,user_id,emotion,loss_impact,support_needed) VALUES(%s,%s,%s,%s,%s) RETURNING id",(tenant,user['email'],body.emotion,body.lossImpact,body.supportNeeded));gid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'griefLogId':str(gid)}
