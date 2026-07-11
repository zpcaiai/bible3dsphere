from __future__ import annotations
from typing import Any,Dict
from fastapi import APIRouter,HTTPException,Request
try:from backend.mission_bridge_auth import authorize
except Exception:from mission_bridge_auth import authorize
router=APIRouter(prefix='/api/mission-bridge/outcomes',tags=['mission-bridge-outcomes']);_state:Dict[str,Any]={}
FORBIDDEN_RANKINGS=['属灵程度排行榜','带人信主排行榜','奉献排行榜','连续不犯罪排行榜','基于AI推测的信心分数']
def init_mission_bridge_outcomes_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
@router.get('/dashboard')
def dashboard(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   authorize(cur,user,'operations.manage',tenant,platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])));cur.execute("SELECT d.layer,d.metric_key,d.label,s.aggregate_value,s.sample_size,s.suppressed FROM mission_bridge_metric_definitions d LEFT JOIN LATERAL(SELECT aggregate_value,sample_size,suppressed FROM mission_bridge_metric_snapshots WHERE tenant_id=%s AND metric_key=d.metric_key ORDER BY period_end DESC LIMIT 1)s ON TRUE WHERE d.active=TRUE ORDER BY d.layer,d.label",(tenant,));rows=cur.fetchall()
 finally:_state['release_db'](conn)
 layers={}
 for r in rows:layers.setdefault(r[0],[]).append({'key':r[1],'label':r[2],'value':None if r[5] or r[4] is None or r[4]<5 else float(r[3]),'sampleSize':r[4] or 0,'suppressed':bool(r[5] or (r[4] is not None and r[4]<5))})
 return {'ok':True,'layers':layers,'forbiddenRankings':FORBIDDEN_RANKINGS,'personalRankings':False}
