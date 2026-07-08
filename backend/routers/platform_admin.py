"""
Platform Admin router — 平台管理 / 审核台 (/api/platform) · B12-4

全部端点仅限 platform_admins(否则 403)。

  GET  /api/platform/overview                  平台级指标(组织/成员/订阅/待复核危机数)
  GET  /api/platform/moderation/crisis-queue   危机事件复核队列(仅安全元数据,绝不含用户危机正文)
  POST /api/platform/moderation/crisis/{id}/review  记录复核动作
  GET  /api/platform/orgs                       组织列表
  POST /api/platform/orgs/{org_id}/suspend      停用组织(账号级;危机/安全仍不受影响)
  POST /api/platform/orgs/{org_id}/reactivate   恢复组织
  GET  /api/platform/moderation/log             平台审核审计日志

隐私边界:危机队列只暴露 risk_level / risk_types / 状态 / 时间 / user_id(供安全团队跟进),
          绝不返回 triggering_message / evidence / system_response 等用户隐私正文。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/platform", tags=["platform-admin"])

_state: Dict[str, Any] = {}


def init_platform_admin_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _require_admin(cur, email: str) -> None:
    cur.execute("SELECT 1 FROM platform_admins WHERE email=%s AND status='active'", (email,))
    if not cur.fetchone():
        raise HTTPException(status_code=403, detail="platform admin only")


def _c(cur, sql, params=()) -> int:
    try:
        cur.execute(sql, params)
        r = cur.fetchone()
        return int(r[0] or 0) if r else 0
    except Exception:
        return 0


def _jl(v):
    if isinstance(v, (list, dict)):
        return v
    try:
        return json.loads(v)
    except Exception:
        return []


@router.get("/overview")
def overview(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_admin(cur, user["email"])
            data = {
                "organizations": _c(cur, "SELECT COUNT(*) FROM organizations WHERE status='active'"),
                "members": _c(cur, "SELECT COUNT(DISTINCT email) FROM organization_memberships WHERE status='active'"),
                "paid_subscriptions": _c(cur, "SELECT COUNT(*) FROM subscriptions WHERE status='active' AND plan_key <> 'free_individual'"),
                # 待复核危机:用 user_acknowledged=FALSE 作为"未结"代理(crisis_events 无 status 列)
                "crisis_unacked_30d": _c(cur, "SELECT COUNT(*) FROM crisis_events WHERE user_acknowledged=FALSE AND created_at >= NOW() - INTERVAL '30 days'"),
                "crisis_high_30d": _c(cur, "SELECT COUNT(*) FROM crisis_events WHERE risk_level IN ('orange','red') AND created_at >= NOW() - INTERVAL '30 days'"),
            }
    finally:
        _state["release_db"](conn)
    return {"ok": True, "metrics": data,
            "note": "危机指标用未确认作为未结代理;明细见复核队列,但用户危机正文不在平台侧暴露。"}


@router.get("/moderation/crisis-queue")
def crisis_queue(request: Request, days: int = Query(default=30, ge=1, le=180),
                 limit: int = Query(default=100, ge=1, le=300)) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_admin(cur, user["email"])
            cur.execute(
                "SELECT e.id, e.user_id, e.risk_level, e.risk_types, e.workflow_started, "
                "e.guardian_notified, e.user_acknowledged, e.created_at, "
                "(SELECT COUNT(*) FROM crisis_moderation_reviews r WHERE r.crisis_event_id=e.id), "
                "(SELECT action FROM crisis_moderation_reviews r WHERE r.crisis_event_id=e.id ORDER BY created_at DESC LIMIT 1) "
                "FROM crisis_events e WHERE e.created_at >= NOW() - INTERVAL '%s days' "
                "ORDER BY e.user_acknowledged ASC, e.created_at DESC LIMIT %s" % (int(days), int(limit)))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = [{"id": r[0], "user_id": r[1], "risk_level": r[2], "risk_types": _jl(r[3]),
              "workflow": r[4], "guardian_notified": bool(r[5]), "user_acknowledged": bool(r[6]),
              "created_at": to_iso(r[7]) if r[7] else None,
              "review_count": int(r[8] or 0), "last_action": r[9]} for r in rows]
    return {"ok": True, "queue": items, "count": len(items),
            "note": "仅安全元数据;triggering_message / evidence / system_response 等用户隐私正文不在此暴露。"}


class ReviewBody(BaseModel):
    action: str = Field(default="reviewed", max_length=30)
    note: str = Field(default="", max_length=1000)


@router.post("/moderation/crisis/{event_id}/review")
def review_crisis(event_id: str, request: Request, body: ReviewBody) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_admin(cur, user["email"])
            cur.execute("SELECT 1 FROM crisis_events WHERE id=%s", (event_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="crisis event not found")
            rid = uuid.uuid4().hex
            cur.execute("INSERT INTO crisis_moderation_reviews (id, crisis_event_id, reviewed_by_email, action, note) "
                        "VALUES (%s,%s,%s,%s,%s)", (rid, event_id, user["email"], body.action, body.note))
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": rid, "event_id": event_id, "action": body.action}


@router.get("/orgs")
def list_orgs(request: Request) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_admin(cur, user["email"])
            cur.execute("SELECT id, name, organization_type, owner_email, status, created_at "
                        "FROM organizations ORDER BY created_at DESC LIMIT 500")
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = [{"id": r[0], "name": r[1], "type": r[2], "owner": r[3], "status": r[4],
              "created_at": to_iso(r[5]) if r[5] else None} for r in rows]
    return {"ok": True, "organizations": items, "count": len(items)}


class SuspendBody(BaseModel):
    note: str = Field(default="", max_length=1000)


def _log(cur, admin_email: str, action: str, target_type: str, target_id: str, note: str) -> None:
    try:
        cur.execute("INSERT INTO platform_moderation_log (id, admin_email, action, target_type, target_id, note) "
                    "VALUES (%s,%s,%s,%s,%s,%s)", (uuid.uuid4().hex, admin_email, action, target_type, target_id, note))
    except Exception as exc:
        # 审计日志写入失败不应中断主流程，但必须记录，避免静默丢失审计轨迹
        print(f"[platform_admin][audit] moderation log write failed action={action!r}: {exc!r}", flush=True)


@router.post("/orgs/{org_id}/suspend")
def suspend_org(org_id: str, request: Request, body: SuspendBody) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_admin(cur, user["email"])
            cur.execute("UPDATE organizations SET status='suspended', updated_at=now() WHERE id=%s", (org_id,))
            _log(cur, user["email"], "org_suspend", "organization", org_id, body.note)
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "org_id": org_id, "status": "suspended",
            "note": "账号级停用;成员的危机/安全功能仍不受订阅或停用影响。"}


@router.post("/orgs/{org_id}/reactivate")
def reactivate_org(org_id: str, request: Request, body: SuspendBody) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_admin(cur, user["email"])
            cur.execute("UPDATE organizations SET status='active', updated_at=now() WHERE id=%s", (org_id,))
            _log(cur, user["email"], "org_reactivate", "organization", org_id, body.note)
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "org_id": org_id, "status": "active"}


@router.get("/moderation/log")
def moderation_log(request: Request, limit: int = Query(default=100, ge=1, le=500)) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_admin(cur, user["email"])
            cur.execute("SELECT admin_email, action, target_type, target_id, note, created_at "
                        "FROM platform_moderation_log ORDER BY created_at DESC LIMIT %s", (limit,))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = [{"admin": r[0], "action": r[1], "target_type": r[2], "target_id": r[3],
              "note": r[4], "created_at": to_iso(r[5]) if r[5] else None} for r in rows]
    return {"ok": True, "log": items, "count": len(items)}
