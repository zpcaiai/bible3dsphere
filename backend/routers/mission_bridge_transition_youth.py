from __future__ import annotations
from typing import Any,Dict
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field
try:from backend.mission_bridge_auth import authorize
except Exception:from mission_bridge_auth import authorize
router=APIRouter(prefix='/api/mission-bridge/modules/transition-youth',tags=['mission-bridge-transition-youth']);_state:Dict[str,Any]={}
PROHIBITED=['未经监护人或机构同意直接接触儿童','私下接送','私人金钱往来','未记录的一对一封闭会面','未经同意使用儿童故事募款']
def init_mission_bridge_transition_youth_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
def _auth(cur,user,tenant):return authorize(cur,user,'program.read',tenant,platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])))
def _active_partner(cur,tenant):cur.execute("SELECT id,partner_name,partner_type FROM mission_bridge_youth_partner_agreements WHERE tenant_id=%s AND status='active' AND CURRENT_DATE BETWEEN valid_from AND valid_until LIMIT 1",(tenant,));return cur.fetchone()
@router.get('/dashboard')
def dashboard(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);partner=_active_partner(cur,tenant)
 finally:_state['release_db'](conn)
 return {'ok':True,'enabled':bool(partner),'partner':{'name':partner[1],'type':partner[2]} if partner else None,'ageRange':'16-25','features':['长期导师','导师背景审查','学业职业规划','居住就业资源','财务基础','人际边界','生活技能','成年过渡计划','紧急联系人','退出后持续支持'],'prohibited':PROHIBITED}
class ProfileBody(BaseModel):age:int=Field(ge=16,le=25);guardianOrAgencyConsent:bool;emergencyContact:str=Field(min_length=4,max_length=500)
@router.post('/profiles')
def profile(body:ProfileBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _auth(cur,user,tenant);partner=_active_partner(cur,tenant)
   if not partner:raise HTTPException(409,detail='必须先与合法儿童福利、学校或专业社工机构建立有效合作')
   if body.age<18 and not body.guardianOrAgencyConsent:raise HTTPException(409,detail='未成年人必须取得监护人或合作机构同意')
   cur.execute("INSERT INTO mission_bridge_transition_youth_profiles(tenant_id,user_id,age,partner_agreement_id,guardian_or_agency_consent,emergency_contact_encrypted) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id",(tenant,user['email'],body.age,str(partner[0]),body.guardianOrAgencyConsent,body.emergencyContact));pid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'profileId':str(pid),'partnerGatePassed':True}
def validate_assignment(clearance_status:str,private_transport:bool,private_money:bool)->None:
 if clearance_status!='cleared' or private_transport or private_money:raise ValueError('youth_safeguarding_assignment_rejected')
