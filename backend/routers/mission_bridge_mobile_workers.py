from __future__ import annotations
from typing import Any,Dict,Literal
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field,field_validator
try:from backend.mission_bridge_auth import authorize
except Exception:from mission_bridge_auth import authorize
router=APIRouter(prefix='/api/mission-bridge/modules/mobile-workers',tags=['mission-bridge-mobile-workers']);_state:Dict[str,Any]={}
def init_mission_bridge_mobile_workers_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
def _auth(cur,user,tenant):return authorize(cur,user,'program.read',tenant,platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])))
def _driving(cur,tenant,user_id):cur.execute("SELECT driving_mode FROM mission_bridge_mobile_worker_profiles WHERE tenant_id=%s AND user_id=%s",(tenant,user_id));row=cur.fetchone();return bool(row and row[0])
class ProfileBody(BaseModel):
 workerType:Literal['delivery','courier','ride_hailing','freight']
 cityCode:str=Field(min_length=2,max_length=40)
 drivingMode:bool=False
 @field_validator('cityCode')
 @classmethod
 def city_only(cls,value):
  if ',' in value or any(x in value.lower() for x in ('lat','lng','longitude','latitude')):raise ValueError('仅允许城市级位置')
  return value
@router.put('/profile')
def profile(body:ProfileBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_mobile_worker_profiles(tenant_id,user_id,worker_type,city_code,driving_mode) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(tenant_id,user_id) DO UPDATE SET worker_type=EXCLUDED.worker_type,city_code=EXCLUDED.city_code,driving_mode=EXCLUDED.driving_mode,updated_at=now()",(tenant,user['email'],body.workerType,body.cityCode,body.drivingMode));conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'drivingMode':body.drivingMode,'interactionMode':'audio_only' if body.drivingMode else 'full'}
@router.get('/dashboard')
def dashboard(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _auth(cur,user,tenant);driving=_driving(cur,tenant,user['email']);cur.execute("SELECT a.id,a.title,a.duration_minutes,a.audio_url,COALESCE(p.position_seconds,0),COALESCE(p.completed,FALSE) FROM mission_bridge_micro_audio a LEFT JOIN mission_bridge_audio_progress p ON p.audio_id=a.id AND p.user_id=%s AND p.tenant_id=%s WHERE a.tenant_id=%s AND a.published=TRUE ORDER BY a.duration_minutes,a.title",(user['email'],tenant,tenant));audio=[{'id':str(r[0]),'title':r[1],'durationMinutes':r[2],'audioUrl':r[3],'positionSeconds':r[4],'completed':r[5]} for r in cur.fetchall()]
 finally:_state['release_db'](conn)
 return {'ok':True,'drivingMode':driving,'interactionMode':'audio_only' if driving else 'full','audio':audio,'safety':['行驶中禁止文本输入','不追踪实时轨迹','位置仅保存城市级','不把劳动困境归因于个人属灵问题'],'cadence':'不要求每日固定时间签到'}
class ProgressBody(BaseModel):positionSeconds:int=Field(ge=0,le=86400);completed:bool=False
@router.put('/audio/{audio_id}/progress')
def progress(audio_id:str,body:ProgressBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_audio_progress(tenant_id,user_id,audio_id,position_seconds,completed) SELECT %s,%s,id,%s,%s FROM mission_bridge_micro_audio WHERE id=%s AND tenant_id=%s AND published=TRUE ON CONFLICT(tenant_id,user_id,audio_id) DO UPDATE SET position_seconds=EXCLUDED.position_seconds,completed=EXCLUDED.completed,updated_at=now() RETURNING id",(tenant,user['email'],body.positionSeconds,body.completed,audio_id,tenant));row=cur.fetchone();conn.commit()
 finally:_state['release_db'](conn)
 if not row:raise HTTPException(404,detail='音频不存在')
 return {'ok':True}
@router.post('/callback')
def callback(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_callback_requests(tenant_id,user_id) VALUES(%s,%s) RETURNING id",(tenant,user['email']));cid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'callbackId':str(cid)}
class TextRequest(BaseModel):text:str=Field(min_length=2,max_length=1000)
@router.post('/text-note')
def text_note(body:TextRequest,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _auth(cur,user,tenant)
   if _driving(cur,tenant,user['email']):raise HTTPException(409,detail='行驶状态下禁止文本输入，请停车后再操作')
 finally:_state['release_db'](conn)
 return {'ok':True,'accepted':True}
