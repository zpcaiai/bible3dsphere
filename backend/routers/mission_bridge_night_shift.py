from __future__ import annotations
import json
from typing import Any,Dict,Literal,List,Optional
from fastapi import APIRouter,Request
from pydantic import BaseModel,Field
try:from backend.mission_bridge_auth import authorize
except Exception:from mission_bridge_auth import authorize
router=APIRouter(prefix='/api/mission-bridge/modules/night-shift',tags=['mission-bridge-night-shift']);_state:Dict[str,Any]={}
def init_mission_bridge_night_shift_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):from fastapi import HTTPException;raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
def _auth(cur,user,tenant):return authorize(cur,user,'program.read',tenant,platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])))
@router.get('/dashboard')
def dashboard(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _auth(cur,user,tenant);cur.execute("SELECT shift_type,shift_start,shift_end,notifications_enabled FROM mission_bridge_shift_profiles WHERE tenant_id=%s AND user_id=%s",(tenant,user['email']));p=cur.fetchone();cur.execute("SELECT sleep_minutes,fatigue,loneliness,trusted_relationship,shift_started_at FROM mission_bridge_shift_checkins WHERE tenant_id=%s AND user_id=%s ORDER BY shift_started_at DESC LIMIT 30",(tenant,user['email']));rows=cur.fetchall()
 finally:_state['release_db'](conn)
 return {'ok':True,'profile':{'shiftType':p[0],'shiftStart':str(p[1]) if p[1] else None,'shiftEnd':str(p[2]) if p[2] else None,'notificationsEnabled':p[3]} if p else None,'metrics':{'checkins':len(rows),'averageSleepMinutes':round(sum((r[0] or 0) for r in rows)/len(rows)) if rows else 0,'averageLoneliness':round(sum(r[2] for r in rows)/len(rows),1) if rows else 0,'trustedRelationship':any(r[3] for r in rows)},'cadence':'按班次记录，不按自然日计算连续签到','features':['夜班前3分钟预备','休息时间音频','下班后情绪卸载','异地夫妻沟通','赌博与债务求助','职业成长','轮班式小组']}
class ProfileBody(BaseModel):shiftType:Literal['night','rotating','irregular'];shiftStart:Optional[str]=None;shiftEnd:Optional[str]=None;notificationsEnabled:bool=False
@router.put('/profile')
def profile(body:ProfileBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_shift_profiles(tenant_id,user_id,shift_type,shift_start,shift_end,notifications_enabled) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(tenant_id,user_id) DO UPDATE SET shift_type=EXCLUDED.shift_type,shift_start=EXCLUDED.shift_start,shift_end=EXCLUDED.shift_end,notifications_enabled=EXCLUDED.notifications_enabled,updated_at=now()",(tenant,user['email'],body.shiftType,body.shiftStart,body.shiftEnd,body.notificationsEnabled));conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True}
class CheckinBody(BaseModel):sleepMinutes:Optional[int]=Field(default=None,ge=0,le=1440);fatigue:int=Field(ge=1,le=5);loneliness:int=Field(ge=1,le=5);trustedRelationship:bool=False
@router.post('/checkins')
def checkin(body:CheckinBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_shift_checkins(tenant_id,user_id,shift_started_at,sleep_minutes,fatigue,loneliness,trusted_relationship) VALUES(%s,%s,now(),%s,%s,%s,%s) RETURNING id",(tenant,user['email'],body.sleepMinutes,body.fatigue,body.loneliness,body.trustedRelationship));cid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'checkinId':str(cid),'preparationMinutes':3}
class DebriefBody(BaseModel):checkinId:Optional[str]=None;emotionLabel:str=Field(min_length=2,max_length=80);releaseNote:str=Field(min_length=2,max_length=2000);familyContacted:bool=False;helpRequested:bool=False;riskCategories:List[Literal['gaming','gambling','debt','exhaustion','other']]=Field(default_factory=list)
@router.post('/debriefs')
def debrief(body:DebriefBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_post_shift_debriefs(tenant_id,user_id,shift_checkin_id,emotion_label,release_note,family_contacted,help_requested,risk_categories) VALUES(%s,%s,%s,%s,%s,%s,%s,%s::jsonb) RETURNING id",(tenant,user['email'],body.checkinId,body.emotionLabel,body.releaseNote,body.familyContacted,body.helpRequested,json.dumps(body.riskCategories)));did=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'debriefId':str(did),'humanFollowup':body.helpRequested}
