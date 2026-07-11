from __future__ import annotations
from typing import Any,Dict
from fastapi import APIRouter,HTTPException,Request
try:from backend.mission_bridge_auth import authorize
except Exception:from mission_bridge_auth import authorize
router=APIRouter(prefix='/api/mission-bridge/localization',tags=['mission-bridge-localization']);_state:Dict[str,Any]={}
REQUIRED_REVIEWS={'human_translation','local_culture','theological_terms'}
def init_mission_bridge_localization_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
@router.get('/catalog')
def catalog(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:authorize(cur,user,'program.read',tenant,platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])));cur.execute("SELECT locale,display_name,script,is_core FROM mission_bridge_languages WHERE status='active' ORDER BY is_core DESC,locale");languages=[{'locale':r[0],'displayName':r[1],'script':r[2],'core':r[3]} for r in cur.fetchall()];cur.execute("SELECT description FROM mission_bridge_localization_principles WHERE active=TRUE");principles=[r[0] for r in cur.fetchall()]
 finally:_state['release_db'](conn)
 return {'ok':True,'languages':languages,'principles':principles,'requiredReviews':sorted(REQUIRED_REVIEWS)}
def localization_publishable(review_types:set[str])->bool:return REQUIRED_REVIEWS.issubset(review_types)
