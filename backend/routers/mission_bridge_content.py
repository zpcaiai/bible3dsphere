from __future__ import annotations
import hashlib,uuid
from typing import Any,Dict,Literal,Optional
from fastapi import APIRouter,Depends,HTTPException,Request
from mission_feature_guard import require_mission_os
from pydantic import BaseModel,Field
try:from backend.mission_bridge_auth import authorize
except Exception:from mission_bridge_auth import authorize
router=APIRouter(prefix='/api/mission-bridge/content',tags=['mission-bridge-content'],dependencies=[Depends(require_mission_os)]);_state:Dict[str,Any]={}
TYPES={'scripture','devotional','audio_lesson','video_lesson','case_study','discussion_guide','facilitator_guide','habit_practice','family_activity','professional_resource','referral_guide','testimony','faq'}
CLASSES={'scripture_text','interpretation','application','testimony','professional_advice'}
def init_mission_bridge_content_router(*,get_db,release_db,get_session_user,is_admin=None):_state.update(locals())
def _ctx(request):
 user=_state['get_session_user'](request)
 if not user or not user.get('email'):raise HTTPException(401,detail='请先登录')
 return user,(request.headers.get('X-Tenant-Id') or 'public')[:80]
def _admin(cur,user,tenant):return authorize(cur,user,'content.manage',tenant,platform_admin=bool(_state.get('is_admin') and _state['is_admin'](user['email'])))
class ContentBody(BaseModel):
 programId:Optional[str]=None;contentType:str;title:str=Field(min_length=3,max_length=240);language:Literal['zh-CN','zh-TW','en'];contentClass:str;body:str=Field(min_length=10,max_length=100000);readingLevel:str='standard';author:str=Field(min_length=2,max_length=240);sourceTitle:str=Field(min_length=2,max_length=500);sourceUrl:Optional[str]=None;copyrightHolder:str=Field(min_length=2,max_length=240);license:str=Field(min_length=2,max_length=120);citation:str=Field(min_length=2,max_length=1000)
@router.post('/items')
def create_item(body:ContentBody,request:Request):
 if body.contentType not in TYPES or body.contentClass not in CLASSES:raise HTTPException(422,detail='不支持的内容类型或内容分类')
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _admin(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_content_catalog(tenant_id,program_id,content_type,title,created_by) VALUES(%s,%s,%s,%s,%s) RETURNING id",(tenant,body.programId,body.contentType,body.title,user['email']));cid=cur.fetchone()[0];meaning=hashlib.sha256(body.body.strip().encode()).hexdigest();cur.execute("INSERT INTO mission_bridge_content_versions(tenant_id,content_id,version,language,content_class,body,core_meaning_hash,reading_level,created_by) VALUES(%s,%s,1,%s,%s,%s,%s,%s,%s) RETURNING id",(tenant,cid,body.language,body.contentClass,body.body,meaning,body.readingLevel,user['email']));vid=cur.fetchone()[0];cur.execute("INSERT INTO mission_bridge_content_sources(tenant_id,content_version_id,author,source_title,source_url,copyright_holder,license,citation) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",(tenant,vid,body.author,body.sourceTitle,body.sourceUrl,body.copyrightHolder,body.license,body.citation));sid=cur.fetchone()[0];conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'contentId':str(cid),'versionId':str(vid),'sourceId':str(sid),'version':1}
@router.post('/sources/{source_id}/verify')
def verify_source(source_id:uuid.UUID,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _admin(cur,user,tenant);cur.execute("UPDATE mission_bridge_content_sources SET verified=TRUE WHERE id=%s AND tenant_id=%s RETURNING id",(str(source_id),tenant));row=cur.fetchone()
   if not row:raise HTTPException(404,detail='内容来源不存在')
   conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'sourceId':str(source_id),'verified':True}
class ReviewBody(BaseModel):reviewType:Literal['theological','cultural','safeguarding','accessibility'];decision:Literal['approved','changes_requested','rejected'];notes:str=Field(min_length=4,max_length=2000)
class AdaptationBody(BaseModel):readingLevel:str=Field(min_length=2,max_length=40);body:str=Field(min_length=10,max_length=100000);meaningPreserved:bool;reviewNotes:str=Field(min_length=4,max_length=2000)
@router.post('/versions/{version_id}/adaptations')
def adaptation(version_id:uuid.UUID,body:AdaptationBody,request:Request):
 if not body.meaningPreserved:raise HTTPException(409,detail='阅读级适配必须由人工确认核心含义未改变')
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _admin(cur,user,tenant);cur.execute("SELECT content_id,version,language,content_class,body,core_meaning_hash FROM mission_bridge_content_versions WHERE id=%s AND tenant_id=%s",(str(version_id),tenant));original=cur.fetchone()
   if not original:raise HTTPException(404,detail='内容版本不存在')
   if original[3]=='scripture_text' and body.body.strip()!=original[4].strip():raise HTTPException(409,detail='经文原文不得通过阅读级适配修改')
   next_version=original[1]+1;cur.execute("INSERT INTO mission_bridge_content_versions(tenant_id,content_id,version,language,content_class,body,core_meaning_hash,reading_level,created_by) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",(tenant,str(original[0]),next_version,original[2],original[3],body.body,original[5],body.readingLevel,user['email']));adapted=cur.fetchone()[0];cur.execute("INSERT INTO mission_bridge_reading_level_scores(tenant_id,content_version_id,reading_level,meaning_preserved,reviewed_by) VALUES(%s,%s,%s,TRUE,%s)",(tenant,str(adapted),body.readingLevel,user['email']));cur.execute("INSERT INTO mission_bridge_content_sources(tenant_id,content_version_id,author,source_title,source_url,copyright_holder,license,citation,verified) SELECT tenant_id,%s,author,source_title,source_url,copyright_holder,license,citation,verified FROM mission_bridge_content_sources WHERE content_version_id=%s",(str(adapted),str(version_id)));conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'versionId':str(adapted),'version':next_version,'readingLevel':body.readingLevel,'meaningPreserved':True,'coreMeaningHash':original[5]}
@router.post('/versions/{version_id}/reviews')
def review(version_id:uuid.UUID,body:ReviewBody,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:_admin(cur,user,tenant);cur.execute("INSERT INTO mission_bridge_content_reviews(tenant_id,content_version_id,review_type,decision,reviewer_user_id,notes) SELECT %s,id,%s,%s,%s,%s FROM mission_bridge_content_versions WHERE id=%s AND tenant_id=%s ON CONFLICT(content_version_id,review_type) DO UPDATE SET decision=EXCLUDED.decision,reviewer_user_id=EXCLUDED.reviewer_user_id,notes=EXCLUDED.notes,created_at=now() RETURNING id",(tenant,body.reviewType,body.decision,user['email'],body.notes,str(version_id),tenant));row=cur.fetchone();
  if not row:raise HTTPException(404,detail='内容版本不存在')
  conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'reviewType':body.reviewType,'decision':body.decision}
@router.post('/versions/{version_id}/publish')
def publish(version_id:uuid.UUID,request:Request):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   _admin(cur,user,tenant);cur.execute("SELECT v.content_id,v.version,s.verified FROM mission_bridge_content_versions v JOIN mission_bridge_content_sources s ON s.content_version_id=v.id WHERE v.id=%s AND v.tenant_id=%s",(str(version_id),tenant));version=cur.fetchone()
   if not version:raise HTTPException(404,detail='内容版本不存在')
   if not version[2]:raise HTTPException(409,detail='内容来源尚未验证')
   cur.execute("SELECT review_type,decision FROM mission_bridge_content_reviews WHERE content_version_id=%s",(str(version_id),));reviews=dict(cur.fetchall());missing=[key for key in ('theological','cultural','safeguarding','accessibility') if reviews.get(key)!='approved']
   if missing:raise HTTPException(409,detail={'message':'四重审核未完成','missingReviews':missing})
   cur.execute("UPDATE mission_bridge_content_catalog SET status='published',published_version=%s WHERE id=%s",(version[1],version[0]));conn.commit()
 finally:_state['release_db'](conn)
 return {'ok':True,'published':True,'contentId':str(version[0]),'version':version[1]}
@router.get('/library')
def library(request:Request,content_type:Optional[str]=None):
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   authorize(cur,user,'program.read',tenant);cur.execute("SELECT c.id,c.title,c.content_type,v.language,v.reading_level FROM mission_bridge_content_catalog c JOIN mission_bridge_content_versions v ON v.content_id=c.id AND v.version=c.published_version WHERE c.tenant_id=%s AND c.status='published' AND (%s IS NULL OR c.content_type=%s) ORDER BY c.created_at DESC LIMIT 200",(tenant,content_type,content_type));items=[{'id':str(r[0]),'title':r[1],'contentType':r[2],'language':r[3],'readingLevel':r[4]} for r in cur.fetchall()]
 finally:_state['release_db'](conn)
 return {'ok':True,'items':items}
@router.get('/rag')
def rag(request:Request,q:str):
 if len(q.strip())<2:raise HTTPException(422,detail='查询过短')
 user,tenant=_ctx(request);conn=_state['get_db']()
 try:
  with conn.cursor() as cur:
   authorize(cur,user,'program.read',tenant);cur.execute("SELECT c.id,c.title,v.body,v.content_class,s.author,s.source_title,s.source_url,s.citation FROM mission_bridge_content_catalog c JOIN mission_bridge_content_versions v ON v.content_id=c.id AND v.version=c.published_version JOIN mission_bridge_content_sources s ON s.content_version_id=v.id WHERE c.tenant_id=%s AND c.status='published' AND s.verified=TRUE AND (to_tsvector('simple',c.title||' '||v.body) @@ plainto_tsquery('simple',%s) OR c.title ILIKE %s) ORDER BY c.created_at DESC LIMIT 5",(tenant,q,f'%{q}%'));rows=cur.fetchall()
 finally:_state['release_db'](conn)
 if not rows:return {'ok':True,'answer':'在已审核并发布的资料中找不到可靠依据，我不知道。请由人工核实后再使用。','citations':[],'grounded':False}
 return {'ok':True,'answer':'\n\n'.join(r[2][:600] for r in rows),'citations':[{'contentId':str(r[0]),'title':r[1],'class':r[3],'author':r[4],'sourceTitle':r[5],'sourceUrl':r[6],'citation':r[7]} for r in rows],'grounded':True}
