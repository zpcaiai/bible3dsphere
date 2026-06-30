"""
Org Console router — 组织管理台 (/api/org-console) · B12 真·多租户隔离的"组织侧窗口"

每个端点都:① require_org_permission(RBAC 强制) ② 按 org_id 过滤(跨组织不可见)。
因此 org A 的领袖永远看不到 org B 的社区数据。

硬边界:本路由只读"社区/组织"数据(小组/导师配对/门徒路径/教会出勤的【计数】)。
        绝不读取任何个人成长内容——不取 check-in 的 gratitude/struggle/prayer_request 正文、
        不取 church check-in 的 reflection、不碰省察/认罪/危机/记忆。牧者可见度不放开。
        危机/安全永远豁免租户与订阅限制(不经本路由)。
"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from core.tenancy import require_org_permission, resolve_role

router = APIRouter(prefix="/api/org-console", tags=["org-console"])

_state: Dict[str, Any] = {}


def init_org_console_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _c(cur, sql, params) -> int:
    try:
        cur.execute(sql, params)
        r = cur.fetchone()
        return int(r[0] or 0) if r else 0
    except Exception:
        return 0


@router.get("/{org_id}/my-role")
def my_role(org_id: str, request: Request) -> dict:
    """调用者在该 org 的角色(仅需是成员;非成员返回 role=None)。"""
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            role = resolve_role(cur, org_id, user["email"])
    finally:
        _state["release_db"](conn)
    return {"ok": True, "org_id": org_id, "role": role, "is_member": bool(role)}


@router.get("/{org_id}/summary")
def summary(org_id: str, request: Request) -> dict:
    """组织社区数据概览(仅计数,无个人内容)。需 manage_groups。"""
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            ctx = require_org_permission(cur, user["email"], org_id, "manage_groups")
            data = {
                "groups": _c(cur, "SELECT COUNT(*) FROM accountability_groups WHERE org_id=%s AND status='active'", (org_id,)),
                "members": _c(cur, "SELECT COUNT(*) FROM organization_memberships WHERE organization_id=%s AND status='active'", (org_id,)),
                "mentor_pairings": _c(cur, "SELECT COUNT(*) FROM mentor_relationships WHERE org_id=%s AND status='active'", (org_id,)),
                "discipleship_paths": _c(cur, "SELECT COUNT(*) FROM user_discipleship_paths WHERE org_id=%s AND status='active'", (org_id,)),
                "church_checkins_30d": _c(cur, "SELECT COUNT(*) FROM church_life_checkins WHERE org_id=%s AND checkin_date >= CURRENT_DATE - INTERVAL '30 days'", (org_id,)),
                "group_checkins_30d": _c(cur, "SELECT COUNT(*) FROM accountability_group_checkins c JOIN accountability_groups g ON g.id=c.group_id WHERE g.org_id=%s AND c.checkin_date >= CURRENT_DATE - INTERVAL '30 days'", (org_id,)),
            }
    finally:
        _state["release_db"](conn)
    return {"ok": True, "org_id": org_id, "role": ctx["role"], "metrics": data,
            "note": "仅组织社区数据的计数;成员的个人成长内容、check-in 正文、危机记录均不在此可见。"}


@router.get("/{org_id}/groups")
def groups(org_id: str, request: Request) -> dict:
    """组织内小组列表 + 成员/出勤【计数】(无 check-in 正文)。需 manage_groups。"""
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            require_org_permission(cur, user["email"], org_id, "manage_groups")
            cur.execute(
                "SELECT g.id, g.name, g.group_type, g.status, g.created_by_email, g.created_at, "
                "(SELECT COUNT(*) FROM accountability_group_members m WHERE m.group_id=g.id AND m.status='active'), "
                "(SELECT COUNT(*) FROM accountability_group_checkins c WHERE c.group_id=g.id AND c.checkin_date >= CURRENT_DATE - INTERVAL '30 days') "
                "FROM accountability_groups g WHERE g.org_id=%s ORDER BY g.created_at DESC LIMIT 200",
                (org_id,))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = [{"id": r[0], "name": r[1], "group_type": r[2], "status": r[3],
              "created_by": r[4], "created_at": to_iso(r[5]) if r[5] else None,
              "active_members": int(r[6] or 0), "checkins_30d": int(r[7] or 0)} for r in rows]
    return {"ok": True, "org_id": org_id, "groups": items, "count": len(items)}


class ClaimBody(BaseModel):
    group_id: str


@router.post("/{org_id}/groups/{group_id}/claim")
def claim_group(org_id: str, group_id: str, request: Request) -> dict:
    """把自己创建的小组归属到该组织(盖 org_id)。需 manage_groups;只能认领自己创建且未被他组占用的小组。"""
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            require_org_permission(cur, user["email"], org_id, "manage_groups")
            cur.execute(
                "UPDATE accountability_groups SET org_id=%s, updated_at=now() "
                "WHERE id=%s AND created_by_email=%s AND (org_id IS NULL OR org_id=%s) RETURNING id",
                (org_id, group_id, user["email"], org_id))
            row = cur.fetchone()
            conn.commit()
    finally:
        _state["release_db"](conn)
    if not row:
        raise HTTPException(status_code=403, detail="cannot claim this group (not creator, or already owned by another org)")
    return {"ok": True, "org_id": org_id, "group_id": group_id, "claimed": True}


@router.get("/{org_id}/mentor-relationships")
def mentor_relationships(org_id: str, request: Request) -> dict:
    """组织内导师配对(配对存在性 + 状态,无任何会谈正文/成长内容)。需 manage_groups。"""
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            require_org_permission(cur, user["email"], org_id, "manage_groups")
            cur.execute(
                "SELECT id, mentor_email, mentee_email, relationship_type, status, start_date "
                "FROM mentor_relationships WHERE org_id=%s ORDER BY created_at DESC LIMIT 300", (org_id,))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = [{"id": r[0], "mentor": r[1], "mentee": r[2], "type": r[3], "status": r[4],
              "start_date": str(r[5]) if r[5] else None} for r in rows]
    return {"ok": True, "org_id": org_id, "relationships": items, "count": len(items),
            "note": "仅显示配对与状态;会谈内容、成长记录、关怀标记不在此可见。"}


@router.get("/{org_id}/members")
def members(org_id: str, request: Request) -> dict:
    """组织成员与角色。需 manage_members。"""
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            require_org_permission(cur, user["email"], org_id, "manage_members")
            cur.execute(
                "SELECT email, role_key, status, created_at FROM organization_memberships "
                "WHERE organization_id=%s ORDER BY created_at ASC LIMIT 1000", (org_id,))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = [{"email": r[0], "role": r[1], "status": r[2], "joined_at": to_iso(r[3]) if r[3] else None} for r in rows]
    return {"ok": True, "org_id": org_id, "members": items, "count": len(items)}


@router.get("/{org_id}/discipleship")
def discipleship_progress(org_id: str, request: Request) -> dict:
    """组织内门徒路径进度(阶段 + 完成步数百分比,无步骤/反思内容)。需 manage_groups。"""
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            require_org_permission(cur, user["email"], org_id, "manage_groups")
            cur.execute(
                "SELECT p.id, p.email, p.title, p.current_stage_key, p.target_stage_key, p.status, p.start_date, "
                "(SELECT COUNT(*) FROM discipleship_path_steps s WHERE s.path_id=p.id), "
                "(SELECT COUNT(*) FROM discipleship_path_steps s WHERE s.path_id=p.id AND s.status='completed') "
                "FROM user_discipleship_paths p WHERE p.org_id=%s ORDER BY p.created_at DESC LIMIT 300", (org_id,))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = []
    for r in rows:
        total = int(r[7] or 0)
        done = int(r[8] or 0)
        items.append({"id": r[0], "member": r[1], "title": r[2], "current_stage": r[3],
                      "target_stage": r[4], "status": r[5], "start_date": str(r[6]) if r[6] else None,
                      "steps_total": total, "steps_done": done,
                      "progress_pct": round(100 * done / total) if total else 0})
    return {"ok": True, "org_id": org_id, "paths": items, "count": len(items),
            "note": "仅阶段与完成步数;步骤内容与个人反思不在此可见。"}


@router.get("/{org_id}/mentor-progress")
def mentor_progress(org_id: str, request: Request) -> dict:
    """组织内导师关系进度(会面计数 + 最近会面日期,无任何会谈正文)。需 manage_groups。"""
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            require_org_permission(cur, user["email"], org_id, "manage_groups")
            cur.execute(
                "SELECT r.id, r.mentor_email, r.mentee_email, r.relationship_type, r.status, "
                "(SELECT COUNT(*) FROM mentor_sessions s WHERE s.relationship_id=r.id), "
                "(SELECT MAX(s.session_date) FROM mentor_sessions s WHERE s.relationship_id=r.id) "
                "FROM mentor_relationships r WHERE r.org_id=%s ORDER BY r.created_at DESC LIMIT 300", (org_id,))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = [{"id": r[0], "mentor": r[1], "mentee": r[2], "type": r[3], "status": r[4],
              "sessions": int(r[5] or 0), "last_session": str(r[6]) if r[6] else None} for r in rows]
    return {"ok": True, "org_id": org_id, "relationships": items, "count": len(items),
            "note": "仅配对、会面计数与最近日期;会谈内容、成长记录、关怀标记不可见。"}


@router.get("/{org_id}/church-trend")
def church_trend(org_id: str, request: Request, weeks: int = Query(default=12, ge=4, le=52)) -> dict:
    """组织教会出勤周趋势(每周签到数 + 出勤数,只计数,无 reflection/next_step 正文)。需 manage_groups。"""
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            require_org_permission(cur, user["email"], org_id, "manage_groups")
            cur.execute(
                "SELECT to_char(date_trunc('week', checkin_date), 'MM-DD') wk, "
                "COUNT(*) total, COUNT(*) FILTER (WHERE attended) attended "
                "FROM church_life_checkins "
                "WHERE org_id=%s AND checkin_date >= CURRENT_DATE - INTERVAL '%d weeks' "
                "GROUP BY date_trunc('week', checkin_date) "
                "ORDER BY date_trunc('week', checkin_date)" % ("%s", int(weeks)),
                (org_id,))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    series = [{"week": r[0], "total": int(r[1] or 0), "attended": int(r[2] or 0)} for r in rows]
    return {"ok": True, "org_id": org_id, "weeks": weeks, "series": series,
            "note": "仅每周签到与出勤计数;成员的反思/下一步等正文不在此可见。"}


@router.get("/{org_id}/group-health")
def group_health(org_id: str, request: Request) -> dict:
    """组织各小组健康度(参与率、近 30 天打卡、关怀旗标【计数】、最近打卡)。需 manage_groups。
       关怀旗标为成员设置的 support_needed 布尔(求助信号),非内容;不取任何 check-in 正文。"""
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            require_org_permission(cur, user["email"], org_id, "manage_groups")
            cur.execute(
                "SELECT g.id, g.name, g.status, "
                "(SELECT COUNT(*) FROM accountability_group_members m WHERE m.group_id=g.id AND m.status='active'), "
                "(SELECT COUNT(*) FROM accountability_group_checkins c WHERE c.group_id=g.id AND c.checkin_date >= CURRENT_DATE - INTERVAL '30 days'), "
                "(SELECT COUNT(DISTINCT c.email) FROM accountability_group_checkins c WHERE c.group_id=g.id AND c.checkin_date >= CURRENT_DATE - INTERVAL '30 days'), "
                "(SELECT COUNT(*) FROM accountability_group_checkins c WHERE c.group_id=g.id AND c.support_needed=TRUE AND c.checkin_date >= CURRENT_DATE - INTERVAL '30 days'), "
                "(SELECT MAX(c.checkin_date) FROM accountability_group_checkins c WHERE c.group_id=g.id) "
                "FROM accountability_groups g WHERE g.org_id=%s AND g.status='active' "
                "ORDER BY g.created_at DESC LIMIT 200", (org_id,))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = []
    for r in rows:
        active = int(r[3] or 0)
        participants = int(r[5] or 0)
        support = int(r[6] or 0)
        last = r[7]
        pct = round(100 * participants / active) if active else 0
        if support > 0 or pct < 30:
            health = "needs_attention"
        elif pct < 60:
            health = "watch"
        else:
            health = "healthy"
        items.append({"id": r[0], "name": r[1], "active_members": active,
                      "checkins_30d": int(r[4] or 0), "participants_30d": participants,
                      "participation_pct": pct, "support_flags_30d": support,
                      "last_checkin": str(last) if last else None, "health": health})
    return {"ok": True, "org_id": org_id, "groups": items, "count": len(items),
            "note": "仅参与计数与求助旗标数;打卡的感恩/挣扎/代祷等正文一律不可见。"}


@router.get("/{org_id}/activity-trend")
def activity_trend(org_id: str, request: Request, weeks: int = Query(default=12, ge=4, le=52)) -> dict:
    """跨域社区活跃度周趋势 = 教会出勤 + 小组打卡(按周计数,UNION;只计数,无任何正文)。需 manage_groups。"""
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            require_org_permission(cur, user["email"], org_id, "manage_groups")
            cur.execute(
                "SELECT to_char(date_trunc('week', d), 'MM-DD') wk, "
                "COUNT(*) FILTER (WHERE src='church') church, "
                "COUNT(*) FILTER (WHERE src='group') grp FROM ("
                "  SELECT checkin_date d, 'church'::text src FROM church_life_checkins "
                "  WHERE org_id=%s AND checkin_date >= CURRENT_DATE - INTERVAL '%d weeks' "
                "  UNION ALL "
                "  SELECT c.checkin_date d, 'group'::text src FROM accountability_group_checkins c "
                "  JOIN accountability_groups g ON g.id=c.group_id "
                "  WHERE g.org_id=%s AND c.checkin_date >= CURRENT_DATE - INTERVAL '%d weeks' "
                ") x GROUP BY date_trunc('week', d) ORDER BY date_trunc('week', d)"
                % ("%s", int(weeks), "%s", int(weeks)),
                (org_id, org_id))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    series = [{"week": r[0], "church": int(r[1] or 0), "group": int(r[2] or 0),
               "total": int(r[1] or 0) + int(r[2] or 0)} for r in rows]
    return {"ok": True, "org_id": org_id, "weeks": weeks, "series": series,
            "note": "教会出勤 / 小组打卡的每周计数(分域);均为计数,任何 check-in 正文都不在此可见。"}
