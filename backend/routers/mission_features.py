"""Mission OS feature flag administration."""
from datetime import datetime
from typing import Literal
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field
router=APIRouter(prefix="/api/v1/mission/features",tags=["mission-features"]); _state={}
def init_mission_features_router(*,get_db,release_db,get_session_user,is_admin):_state.update(locals())
def _admin(request):
    user=_state["get_session_user"](request); email=str((user or {}).get("email") or "")
    if not email:raise HTTPException(401,detail="请先登录")
    if not _state["is_admin"](email):raise HTTPException(403,detail="需要平台管理员权限")
    return email
@router.get("")
def list_flags(request:Request):
    _admin(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id,key,description,default_value,risk_level,updated_at FROM mission_feature_flags ORDER BY key")
            flags=[{"id":str(r[0]),"key":r[1],"description":r[2],"defaultValue":r[3],"riskLevel":r[4],"updatedAt":r[5].isoformat()} for r in cur.fetchall()]
            cur.execute("SELECT o.id,f.key,o.scope_type,o.scope_id,o.value,o.reason,o.starts_at,o.expires_at,o.created_by FROM mission_feature_flag_overrides o JOIN mission_feature_flags f ON f.id=o.flag_id ORDER BY o.created_at DESC LIMIT 500")
            overrides=[{"id":str(r[0]),"key":r[1],"scopeType":r[2],"scopeId":r[3],"value":r[4],"reason":r[5],"startsAt":r[6].isoformat(),"expiresAt":r[7].isoformat() if r[7] else None,"createdBy":r[8]} for r in cur.fetchall()]
    finally:_state["release_db"](conn)
    return {"ok":True,"flags":flags,"overrides":overrides}
class OverrideBody(BaseModel):
    scopeType:Literal["global","tenant","organization","program","user","environment"]
    scopeId:str=Field(min_length=1,max_length=128); value:bool; reason:str=Field(min_length=4,max_length=500)
    startsAt:datetime|None=None; expiresAt:datetime|None=None
@router.put("/{key}/overrides")
def set_override(key:str,body:OverrideBody,request:Request):
    actor=_admin(request); conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM mission_feature_flags WHERE key=%s",(key,)); row=cur.fetchone()
            if not row:raise HTTPException(404,detail="Feature Flag 不存在")
            cur.execute("INSERT INTO mission_feature_flag_overrides(flag_id,scope_type,scope_id,value,reason,starts_at,expires_at,created_by) VALUES(%s,%s,%s,%s,%s,COALESCE(%s,now()),%s,%s) RETURNING id",(row[0],body.scopeType,body.scopeId,body.value,body.reason,body.startsAt,body.expiresAt,actor)); oid=cur.fetchone()[0]
            cur.execute("INSERT INTO mission_bridge_audit_log(tenant_id,actor_user_id,action,target_type,target_id,metadata) VALUES('public',%s,'feature_flag.override','feature_flag',%s,jsonb_build_object('scopeType',%s,'scopeId',%s,'value',%s,'reason',%s))",(actor,key,body.scopeType,body.scopeId,body.value,body.reason));conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"overrideId":str(oid)}
