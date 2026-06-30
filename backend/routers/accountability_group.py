"""
Accountability Group router — 属灵同伴 / 小组监督 (/api/accountability-group)

  POST /api/accountability-group/groups                建群（创建者成为 leader）
  GET  /api/accountability-group/groups                我的群
  GET  /api/accountability-group/groups/{id}           群详情（须成员）
  POST /api/accountability-group/groups/{id}/members   加成员（leader）
  POST /api/accountability-group/groups/{id}/goals     建目标
  GET  /api/accountability-group/groups/{id}/goals     目标列表
  POST /api/accountability-group/groups/{id}/checkins  打卡（危机扫描）
  GET  /api/accountability-group/groups/{id}/checkins  可见打卡
  POST /api/accountability-group/groups/{id}/prayer-requests  加代祷
  GET  /api/accountability-group/groups/{id}/prayer-requests  代祷板
  POST /api/accountability-group/groups/{id}/review    群组回顾（去敏）

监督是为了坚固爱与信,不是羞辱或掌控;私密认罪/危机不入群;鼓励、代祷、智慧提问。email 标识用户。
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/accountability-group", tags=["accountability-group"])

_state: Dict[str, Any] = {}


def init_accountability_group_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _member(cur, gid: str, email: str) -> Optional[str]:
    cur.execute("SELECT role FROM accountability_group_members WHERE group_id=%s AND email=%s AND status='active'", (gid, email))
    r = cur.fetchone()
    return r[0] if r else None


class GroupCreate(BaseModel):
    name: str = Field(..., max_length=160)
    description: str = Field(default="", max_length=2000)
    group_type: str = Field(default="small_group", max_length=24)


@router.post("/groups")
def create_group(request: Request, body: GroupCreate) -> dict:
    user = _require_user(request); email = user["email"]
    gid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO accountability_groups (id, name, description, group_type, created_by_email) "
                        "VALUES (%s,%s,%s,%s,%s)", (gid, body.name, body.description, body.group_type, email))
            cur.execute("INSERT INTO accountability_group_members (id, group_id, email, role, status, sharing_scope) "
                        "VALUES (%s,%s,%s,'leader','active','formation_summary')", (uuid.uuid4().hex, gid, email))
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "group_id": gid}


@router.get("/groups")
def list_groups(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT g.id, g.name, g.description, g.group_type, g.status, m.role "
                        "FROM accountability_groups g JOIN accountability_group_members m ON g.id=m.group_id "
                        "WHERE m.email=%s AND m.status='active' ORDER BY g.created_at DESC", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "groups": [
        {"id": r[0], "name": r[1], "description": r[2] or "", "group_type": r[3], "status": r[4], "my_role": r[5]} for r in rows
    ]}


@router.get("/groups/{gid}")
def get_group(gid: str, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            role = _member(cur, gid, user["email"])
            if not role:
                raise HTTPException(status_code=404, detail="no permission")
            cur.execute("SELECT id, name, description, group_type, status, group_rule, confidentiality_commitment FROM accountability_groups WHERE id=%s", (gid,))
            g = cur.fetchone()
            cur.execute("SELECT email, role, status, sharing_scope FROM accountability_group_members WHERE group_id=%s AND status='active'", (gid,))
            members = [{"email": m[0], "role": m[1], "status": m[2], "sharing_scope": m[3]} for m in cur.fetchall()]
    except HTTPException:
        raise
    finally:
        _state["release_db"](conn)
    return {"ok": True, "group": {"id": g[0], "name": g[1], "description": g[2] or "", "group_type": g[3],
            "status": g[4], "group_rule": g[5] or "", "confidentiality_commitment": g[6] or "",
            "my_role": role, "members": members}}


class MemberAdd(BaseModel):
    email: str = Field(..., max_length=255)
    role: str = Field(default="member", max_length=12)
    sharing_scope: str = Field(default="checkin_only", max_length=24)


@router.post("/groups/{gid}/members")
def add_member(gid: str, request: Request, body: MemberAdd) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            role = _member(cur, gid, user["email"])
            if role not in ("leader", "admin"):
                raise HTTPException(status_code=403, detail="only leader can add members")
            cur.execute("INSERT INTO accountability_group_members (id, group_id, email, role, sharing_scope) "
                        "VALUES (%s,%s,%s,%s,%s)", (uuid.uuid4().hex, gid, body.email, body.role, body.sharing_scope))
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"add failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True}


class GoalCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: str = Field(default="", max_length=2000)
    goal_type: str = Field(default="prayer", max_length=20)


@router.post("/groups/{gid}/goals")
def create_goal(gid: str, request: Request, body: GoalCreate) -> dict:
    user = _require_user(request)
    goid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if not _member(cur, gid, user["email"]):
                raise HTTPException(status_code=404, detail="no permission")
            cur.execute("INSERT INTO accountability_group_goals (id, group_id, email, title, description, goal_type) "
                        "VALUES (%s,%s,%s,%s,%s,%s)", (goid, gid, user["email"], body.title, body.description, body.goal_type))
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "goal_id": goid}


@router.get("/groups/{gid}/goals")
def list_goals(gid: str, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if not _member(cur, gid, user["email"]):
                raise HTTPException(status_code=404, detail="no permission")
            cur.execute("SELECT id, email, title, description, goal_type, status FROM accountability_group_goals "
                        "WHERE group_id=%s AND status='active' ORDER BY created_at DESC", (gid,))
            rows = cur.fetchall()
    except HTTPException:
        raise
    finally:
        _state["release_db"](conn)
    return {"ok": True, "goals": [
        {"id": r[0], "email": r[1], "title": r[2], "description": r[3] or "", "goal_type": r[4], "status": r[5]} for r in rows
    ]}


class CheckinCreate(BaseModel):
    checkin_type: str = Field(default="weekly", max_length=12)
    gratitude: str = Field(default="", max_length=2000)
    struggle: str = Field(default="", max_length=2000)
    prayer_request: str = Field(default="", max_length=2000)
    support_needed: bool = Field(default=False)
    visibility: str = Field(default="group_visible", max_length=20)


@router.post("/groups/{gid}/checkins")
def create_checkin(gid: str, request: Request, body: CheckinCreate) -> dict:
    user = _require_user(request)
    cid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if not _member(cur, gid, user["email"]):
                raise HTTPException(status_code=404, detail="no permission")
            cur.execute(
                "INSERT INTO accountability_group_checkins (id, group_id, email, checkin_type, gratitude, struggle, "
                "prayer_request, support_needed, visibility) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (cid, gid, user["email"], body.checkin_type, body.gratitude, body.struggle,
                 body.prayer_request, body.support_needed, body.visibility),
            )
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"checkin failed: {exc}")
    finally:
        _state["release_db"](conn)
    out = {"ok": True, "id": cid}
    try:
        from safety_scan import scan_crisis
        c = scan_crisis(body.struggle, body.prayer_request)
        if c:
            out["crisis"] = c
            out["note"] = "你提到的重担可能需要超出小组的即时帮助——危机内容不该只在群里流转,请同时寻求牧养/危机陪伴。"
    except Exception:
        pass
    return out


@router.get("/groups/{gid}/checkins")
def list_checkins(gid: str, request: Request) -> dict:
    user = _require_user(request); to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            role = _member(cur, gid, user["email"])
            if not role:
                raise HTTPException(status_code=404, detail="no permission")
            cur.execute("SELECT id, email, checkin_date, checkin_type, gratitude, struggle, prayer_request, support_needed, visibility "
                        "FROM accountability_group_checkins WHERE group_id=%s ORDER BY checkin_date DESC LIMIT 100", (gid,))
            rows = cur.fetchall()
    except HTTPException:
        raise
    finally:
        _state["release_db"](conn)
    out = []
    me = user["email"]
    for r in rows:
        own = r[1] == me
        # private_to_leader 仅本人/leader 可见
        if r[8] == "private_to_leader" and not own and role not in ("leader", "admin"):
            continue
        out.append({"id": r[0], "email": r[1] if (own or role in ("leader", "admin")) else "(匿名)",
                    "checkin_date": str(r[2]), "checkin_type": r[3], "gratitude": r[4] or "",
                    "struggle": r[5] or "", "prayer_request": r[6] or "", "support_needed": bool(r[7])})
    return {"ok": True, "checkins": out}


class PrayerCreate(BaseModel):
    title: str = Field(..., max_length=200)
    request_text: str = Field(default="", max_length=2000)
    privacy_level: str = Field(default="group_visible", max_length=16)


@router.post("/groups/{gid}/prayer-requests")
def add_prayer(gid: str, request: Request, body: PrayerCreate) -> dict:
    user = _require_user(request)
    pid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if not _member(cur, gid, user["email"]):
                raise HTTPException(status_code=404, detail="no permission")
            cur.execute("INSERT INTO group_prayer_requests (id, group_id, email, title, request_text, privacy_level) "
                        "VALUES (%s,%s,%s,%s,%s,%s)", (pid, gid, user["email"], body.title, body.request_text, body.privacy_level))
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": pid}


@router.get("/groups/{gid}/prayer-requests")
def list_prayers(gid: str, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            role = _member(cur, gid, user["email"])
            if not role:
                raise HTTPException(status_code=404, detail="no permission")
            cur.execute("SELECT id, email, title, request_text, privacy_level, status FROM group_prayer_requests "
                        "WHERE group_id=%s AND status='active' ORDER BY created_at DESC", (gid,))
            rows = cur.fetchall()
    except HTTPException:
        raise
    finally:
        _state["release_db"](conn)
    me = user["email"]
    out = []
    for r in rows:
        anon = r[4] == "anonymized" and r[1] != me
        leader_only = r[4] == "leader_only" and r[1] != me and role not in ("leader", "admin")
        if leader_only:
            continue
        out.append({"id": r[0], "by": "(匿名)" if anon else r[1], "title": r[2],
                    "request_text": r[3] or "", "status": r[5]})
    return {"ok": True, "prayer_requests": out}


@router.post("/groups/{gid}/review")
def review(gid: str, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if not _member(cur, gid, user["email"]):
                raise HTTPException(status_code=404, detail="no permission")
            cur.execute("SELECT COUNT(*) FROM accountability_group_checkins WHERE group_id=%s AND checkin_date >= CURRENT_DATE - INTERVAL '7 days'", (gid,))
            checkins = cur.fetchone()[0] or 0
            cur.execute("SELECT COUNT(*) FROM accountability_group_checkins WHERE group_id=%s AND support_needed=TRUE AND checkin_date >= CURRENT_DATE - INTERVAL '7 days'", (gid,))
            support = cur.fetchone()[0] or 0
            cur.execute("SELECT COUNT(*) FROM group_prayer_requests WHERE group_id=%s AND status='active'", (gid,))
            prayers = cur.fetchone()[0] or 0
    except HTTPException:
        raise
    finally:
        _state["release_db"](conn)
    enc, risk, nxt = [], [], []
    if checkins:
        enc.append("成员在持续诚实地打卡。")
    else:
        nxt.append("本周打卡较少——可以简化、温柔提醒,而非施压。")
    if support:
        nxt.append(f"有 {support} 次请求支持,记得跟进。")
    risk.append("避免把打卡变成表现报告或彼此比较。")
    return {"ok": True, "summary": {"checkins_7d": checkins, "support_requests": support, "active_prayers": prayers},
            "encouragement": enc, "risks": risk, "next_steps": nxt}
