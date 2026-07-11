from __future__ import annotations
from typing import Any,Dict
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field
try:from backend.mission_bridge_auth import authorize
except Exception:from mission_bridge_auth import authorize
router=APIRouter(prefix='/api/mission-bridge/modules/church-harm',tags=['mission-bridge-church-harm']);_state:Dict[str,Any]={}
STAGES=['安全和倾听','事件和影响梳理','区分基督、教会和具体权力结构','识别操控、羞耻和不健康权威','重建个人信仰实践','自主决定是否进入新的群体']
PRINCIPLES=['不默认离开是悖逆','不首先劝回原教会','不要求立即与伤害者和解','原教会领袖不自动获得记录','允许匿名或化名参与','区分饶恕、和解、恢复信任和重新进入关系']
def init_mission_bridge_church_harm_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
def _auth(cur,user,tenant):return authorize(cur,user,'program.read',tenant,platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])))
@router.get('/dashboard')
def dashboard(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("SELECT id,pseudonym,current_stage FROM mission_bridge_church_harm_profiles WHERE tenant_id=%s AND owner_user_id=%s AND share_with_original_church=FALSE",(tenant,user['email']));p=cur.fetchone()
 finally:_state['release_db'](conn)
 return {'ok':True,'project':'信仰重建与安全对话','profile':{'id':str(p[0]),'pseudonym':p[1],'currentStage':p[2]} if p else None,'stages':[{'number':i+1,'title':x} for i,x in enumerate(STAGES)],'principles':PRINCIPLES}
class ProfileBody(BaseModel):pseudonym:str=Field(min_length=2,max_length=80)
@router.put('/profile')
def profile(body:ProfileBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_church_harm_profiles(tenant_id,owner_user_id,pseudonym,share_with_original_church) VALUES(%s,%s,%s,FALSE) ON CONFLICT(tenant_id,owner_user_id) DO UPDATE SET pseudonym=EXCLUDED.pseudonym RETURNING id",(tenant,user['email'],body.pseudonym));pid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'profileId':str(pid),'sharedWithOriginalChurch':False}
class ComplaintBody(BaseModel):summary:str=Field(min_length=10,max_length=5000);requestedOutcome:str=Field(min_length=4,max_length=2000)
@router.post('/complaints')
def complaint(body:ComplaintBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("SELECT id FROM mission_bridge_church_harm_profiles WHERE tenant_id=%s AND owner_user_id=%s",(tenant,user['email']));p=cur.fetchone()
  if not p:raise HTTPException(409,detail='请先建立化名档案')
  with conn.cursor() as cur:cur.execute("INSERT INTO mission_bridge_church_harm_complaints(tenant_id,profile_id,summary,requested_outcome) VALUES(%s,%s,%s,%s) RETURNING id",(tenant,str(p[0]),body.summary,body.requestedOutcome));cid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'complaintId':str(cid),'reviewChannel':'independent','sharedWithOriginalChurch':False}
