from __future__ import annotations
import json
from typing import Any,Dict,List
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field
try:from backend.mission_bridge_auth import authorize
except Exception:from mission_bridge_auth import authorize
router=APIRouter(prefix='/api/mission-bridge/analytics',tags=['mission-bridge-analytics']);_state:Dict[str,Any]={}
ANALYSES=['cohort','step_funnel','exit_reasons','medium_effect','time_effect','group_difference','safety_trend','content_quality','mentor_capacity','referral_closure']
def init_mission_bridge_analytics_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
def _auth(cur,user,tenant):return authorize(cur,user,'operations.manage',tenant,platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])))
class ExperimentBody(BaseModel):programId:str;name:str=Field(min_length=3,max_length=200);hypothesis:str=Field(min_length=10,max_length=2000);primaryMetric:str;secondaryMetrics:List[str]=Field(default_factory=list);highRiskGroup:bool=False;safeguardingReviewStatus:str='not_required';researchDisclosure:str=Field(min_length=10,max_length=2000);basicCareUnaffected:bool=True;coerciveMessaging:bool=False
@router.post('/experiments')
def experiment(body:ExperimentBody,request:Request):
 if body.coerciveMessaging:raise HTTPException(422,detail='禁止实验强迫性信息')
 if not body.basicCareUnaffected:raise HTTPException(422,detail='实验不得影响基本关怀服务')
 if body.highRiskGroup and body.safeguardingReviewStatus!='approved':raise HTTPException(409,detail='高风险群体实验必须先通过安全审查')
 if body.primaryMetric=='conversion_rate' and not body.secondaryMetrics:raise HTTPException(422,detail='转化率不能作为唯一优化目标')
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_experiments(tenant_id,program_id,name,hypothesis,primary_metric,secondary_metrics,high_risk_group,safeguarding_review_status,research_disclosure,basic_care_unaffected,coercive_messaging,created_by) VALUES(%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,TRUE,FALSE,%s) RETURNING id",(tenant,body.programId,body.name,body.hypothesis,body.primaryMetric,json.dumps(body.secondaryMetrics),body.highRiskGroup,body.safeguardingReviewStatus,body.researchDisclosure,user['email']));eid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'experimentId':str(eid),'researchDisclosed':True,'basicCareUnaffected':True,'dataAnonymized':True}
@router.get('/catalog')
def catalog(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant)
 finally:_state['release_db'](conn)
 return {'ok':True,'analysisTypes':ANALYSES,'minimumCellSize':5,'personalIdentifiers':False}
