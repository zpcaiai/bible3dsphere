from __future__ import annotations
from typing import Any,Dict,Literal
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field
try:from backend.mission_bridge_auth import authorize
except Exception:from mission_bridge_auth import authorize
router=APIRouter(prefix='/api/mission-bridge/accessibility',tags=['mission-bridge-accessibility']);_state:Dict[str,Any]={}
FORMATS=['standard_text','plain_text','audio_only','captioned_video','sign_language_video','large_print']
STANDARDS=['WCAG 2.2 AA','键盘完整操作','屏幕阅读器标签','字幕与视频文本稿','音频描述','高对比度','200%字号','简明语言','低带宽','下载和离线']
def init_mission_bridge_accessibility_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
def _auth(cur,user,tenant):return authorize(cur,user,'program.read',tenant,platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])))
@router.get('/preferences')
def get_preferences(request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("SELECT high_contrast,font_scale,plain_language,low_bandwidth,preferred_format FROM mission_bridge_accessibility_preferences WHERE tenant_id=%s AND user_id=%s",(tenant,user['email']));r=cur.fetchone()
 finally:_state['release_db'](conn)
 return {'ok':True,'preferences':{'highContrast':r[0],'fontScale':float(r[1]),'plainLanguage':r[2],'lowBandwidth':r[3],'preferredFormat':r[4]} if r else {'highContrast':False,'fontScale':1,'plainLanguage':False,'lowBandwidth':False,'preferredFormat':'standard_text'},'formats':FORMATS,'standards':STANDARDS}
class PreferencesBody(BaseModel):highContrast:bool=False;fontScale:float=Field(default=1,ge=1,le=2);plainLanguage:bool=False;lowBandwidth:bool=False;preferredFormat:Literal['standard_text','plain_text','audio_only','captioned_video','sign_language_video','large_print']='standard_text'
@router.put('/preferences')
def save_preferences(body:PreferencesBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_accessibility_preferences(tenant_id,user_id,high_contrast,font_scale,plain_language,low_bandwidth,preferred_format) VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(tenant_id,user_id) DO UPDATE SET high_contrast=EXCLUDED.high_contrast,font_scale=EXCLUDED.font_scale,plain_language=EXCLUDED.plain_language,low_bandwidth=EXCLUDED.low_bandwidth,preferred_format=EXCLUDED.preferred_format,updated_at=now()",(tenant,user['email'],body.highContrast,body.fontScale,body.plainLanguage,body.lowBandwidth,body.preferredFormat));conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'preferences':body.model_dump()}
@router.get('/content/{content_version_id}/variants')
def variants(content_version_id:str,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_auth(cur,user,tenant);cur.execute("SELECT format,asset_url,transcript,caption_url,audio_description,downloadable,low_bandwidth_bytes FROM mission_bridge_accessible_content_variants WHERE tenant_id=%s AND content_version_id=%s",(tenant,content_version_id));items=[dict(zip(('format','assetUrl','transcript','captionUrl','audioDescription','downloadable','lowBandwidthBytes'),r)) for r in cur.fetchall()]
 finally:_state['release_db'](conn)
 return {'ok':True,'items':items,'missingFormats':[x for x in FORMATS if x not in {i['format'] for i in items}]}
