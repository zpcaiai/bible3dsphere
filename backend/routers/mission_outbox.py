"""Read-only payload inspection and audited dead-letter replay."""
from fastapi import APIRouter,HTTPException,Request
router=APIRouter(prefix="/api/v1/mission/system/outbox",tags=["mission-outbox"]);_state={}
def init_mission_outbox_router(*,get_db,release_db,get_session_user,is_admin):_state.update(locals())
def _admin(request):
    user=_state["get_session_user"](request);email=str((user or {}).get("email") or "")
    if not email:raise HTTPException(401,detail="请先登录")
    if not _state["is_admin"](email):raise HTTPException(403,detail="需要平台管理员权限")
    return email
@router.get("")
def list_events(request:Request,status:str="failed",limit:int=50):
    _admin(request);conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT o.id,o.tenant_id,o.event_type,o.event_version,o.attempts,o.occurred_at,o.published_at,o.last_error,(d.event_id IS NOT NULL) FROM mission_outbox_events o LEFT JOIN mission_dead_letter_events d ON d.event_id=o.id WHERE (%s='all' OR (%s='failed' AND o.last_error IS NOT NULL) OR (%s='pending' AND o.published_at IS NULL)) ORDER BY o.occurred_at DESC LIMIT %s",(status,status,status,min(max(limit,1),200)))
            items=[{"id":str(r[0]),"tenantId":r[1],"eventType":r[2],"version":r[3],"attempts":r[4],"occurredAt":r[5].isoformat(),"publishedAt":r[6].isoformat() if r[6] else None,"error":r[7],"deadLetter":r[8]} for r in cur.fetchall()]
    finally:_state["release_db"](conn)
    return {"ok":True,"items":items}
@router.post("/{event_id}/replay")
def replay(event_id:str,request:Request):
    actor=_admin(request);conn=_state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE mission_dead_letter_events SET replayed_at=now(),replayed_by=%s WHERE event_id=%s RETURNING event_id",(actor,event_id));row=cur.fetchone()
            if not row:raise HTTPException(404,detail="Dead Letter 不存在")
            cur.execute("UPDATE mission_outbox_events SET attempts=0,next_attempt_at=now(),last_error=NULL,published_at=NULL,updated_at=now() WHERE id=%s",(event_id,))
            cur.execute("INSERT INTO mission_bridge_audit_log(tenant_id,actor_user_id,action,target_type,target_id,metadata) SELECT tenant_id,%s,'outbox.replay','outbox_event',id,'{}'::jsonb FROM mission_outbox_events WHERE id=%s",(actor,event_id));conn.commit()
    finally:_state["release_db"](conn)
    return {"ok":True,"eventId":event_id}
