from __future__ import annotations
from typing import Any,Dict,Literal
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field
try:from backend.mission_bridge_auth import authorize
except Exception:from mission_bridge_auth import authorize
router=APIRouter(prefix='/api/mission-bridge/modules/ministry-families',tags=['mission-bridge-ministry-families']);_state:Dict[str,Any]={}
PRINCIPLES=['不自动共享给所在教会','导师尽量来自其他机构','可使用化名','牧者不能查询配偶或子女记录','处理角色压力、家庭缺席、公开期待和服事耗竭']
def init_mission_bridge_ministry_families_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
def _auth(cur,user,tenant):return authorize(cur,user,'program.read',tenant,platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])))
@router.get('/dashboard')
def dashboard(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("SELECT pseudonym,participant_type FROM mission_bridge_ministry_family_profiles WHERE tenant_id=%s AND owner_user_id=%s AND share_with_home_church=FALSE",(tenant,user['email']));p=cur.fetchone()
 finally:_state['release_db'](conn)
 return {'ok':True,'project':'服事者家庭保密支持网络','principles':PRINCIPLES,'profile':{'pseudonym':p[0],'participantType':p[1]} if p else None,'features':['跨机构小组','牧者配偶支持','成年牧者子女小组','家庭节奏评估','休息计划','冲突和边界工具','督导和专业转介']}
class ProfileBody(BaseModel):pseudonym:str=Field(min_length=2,max_length=80);participantType:Literal['pastor','spouse','adult_child'];homeChurchOrgId:str|None=None
@router.put('/profile')
def profile(body:ProfileBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_ministry_family_profiles(tenant_id,owner_user_id,pseudonym,participant_type,home_church_org_id,share_with_home_church) VALUES(%s,%s,%s,%s,%s,FALSE) ON CONFLICT(tenant_id,owner_user_id) DO UPDATE SET pseudonym=EXCLUDED.pseudonym,participant_type=EXCLUDED.participant_type,home_church_org_id=EXCLUDED.home_church_org_id RETURNING id",(tenant,user['email'],body.pseudonym,body.participantType,body.homeChurchOrgId));pid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'profileId':str(pid),'sharedWithHomeChurch':False,'familyAutoAccess':False}
