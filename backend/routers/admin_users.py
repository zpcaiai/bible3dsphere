"""
admin_users.py — 管理端：用户管理 + 教会管理 + 审计日志。

prefix: /api/admin
鉴权：每个端点首先调用 require_admin(request)。
"""
from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:
    from routers.admin_common import _state, require_admin, audit, paginate
except ImportError:
    from backend.routers.admin_common import _state, require_admin, audit, paginate

router = APIRouter(prefix="/api/admin", tags=["admin-users"])

_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
_PROTECTED_EMAIL = "zpclord@sina.com"


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/dashboard")
def admin_dashboard(request: Request) -> dict:
    require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            # 总用户数 & 今日新增（上海时区）
            cur.execute("""
                SELECT COUNT(*) AS total,
                       COUNT(*) FILTER (
                           WHERE created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Shanghai'
                               >= CURRENT_DATE AT TIME ZONE 'Asia/Shanghai'
                       ) AS today
                FROM users
            """)
            r = cur.fetchone()
            user_total, user_today = r[0], r[1]

            # 日活：近 24h 活跃 token（user_tokens 有 created_at）
            cur.execute("""
                SELECT COUNT(DISTINCT email)
                FROM user_tokens
                WHERE created_at >= NOW() - INTERVAL '24 hours'
            """)
            dau = cur.fetchone()[0]

            # community_posts 统计
            cur.execute("""
                SELECT COUNT(*) AS total,
                       COUNT(*) FILTER (
                           WHERE created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Shanghai'
                               >= CURRENT_DATE AT TIME ZONE 'Asia/Shanghai'
                       ) AS today
                FROM community_posts WHERE deleted_at IS NULL
            """)
            r = cur.fetchone()
            post_total, post_today = r[0], r[1]

            # prayers 统计
            cur.execute("""
                SELECT COUNT(*) AS total,
                       COUNT(*) FILTER (
                           WHERE created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Shanghai'
                               >= CURRENT_DATE AT TIME ZONE 'Asia/Shanghai'
                       ) AS today
                FROM prayers WHERE deleted_at IS NULL
            """)
            r = cur.fetchone()
            prayer_total, prayer_today = r[0], r[1]

            # 教会数
            cur.execute("SELECT COUNT(*) FROM churches WHERE is_active = TRUE")
            church_count = cur.fetchone()[0]

            # 今日评论
            cur.execute("""
                SELECT COUNT(*) FROM community_comments
                WHERE deleted_at IS NULL
                  AND created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Shanghai'
                      >= CURRENT_DATE AT TIME ZONE 'Asia/Shanghai'
            """)
            comment_today = cur.fetchone()[0]

            # 近 30 天注册趋势
            cur.execute("""
                SELECT (created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Shanghai')::date AS d,
                       COUNT(*) AS cnt
                FROM users
                WHERE created_at >= NOW() - INTERVAL '30 days'
                GROUP BY d
                ORDER BY d
            """)
            trend = [{"date": str(row[0]), "count": row[1]} for row in cur.fetchall()]

        return {
            "ok": True,
            "stats": {
                "user_total": user_total,
                "user_today": user_today,
                "dau": dau,
                "post_total": post_total,
                "post_today": post_today,
                "prayer_total": prayer_total,
                "prayer_today": prayer_today,
                "church_count": church_count,
                "comment_today": comment_today,
            },
            "trend": trend,
        }
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# 用户列表
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/users")
def admin_list_users(
    request: Request,
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    banned: bool | None = Query(default=None),
    admin: bool | None = Query(default=None),
    church_id: int | None = Query(default=None),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            filters = []
            params: list = []

            if q:
                filters.append(
                    "(u.email ILIKE %s OR u.nickname ILIKE %s)"
                )
                like = f"%{q}%"
                params += [like, like]
            if banned is not None:
                filters.append("u.is_banned = %s")
                params.append(banned)
            if admin is not None:
                filters.append("u.is_admin = %s")
                params.append(admin)
            if church_id is not None:
                filters.append("cm.church_id = %s")
                params.append(church_id)

            where = ("WHERE " + " AND ".join(filters)) if filters else ""

            count_sql = f"""
                SELECT COUNT(*)
                FROM users u
                LEFT JOIN church_members cm ON cm.email = u.email
                {where}
            """
            cur.execute(count_sql, params)
            total = cur.fetchone()[0]

            list_sql = f"""
                SELECT u.id, u.email, u.nickname, u.avatar, u.login_type,
                       u.is_admin, u.is_banned, u.ban_reason, u.banned_at,
                       u.created_at,
                       cm.church_id, c.name AS church_name, cm.role AS church_role
                FROM users u
                LEFT JOIN church_members cm ON cm.email = u.email
                LEFT JOIN churches c ON c.id = cm.church_id
                {where}
                ORDER BY u.created_at DESC
                LIMIT %s OFFSET %s
            """
            cur.execute(list_sql, params + [limit, offset])
            rows = cur.fetchall()
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "email": r[1], "nickname": r[2], "avatar": r[3],
                    "login_type": r[4], "is_admin": r[5], "is_banned": r[6],
                    "ban_reason": r[7] or "", "banned_at": iso(r[8]),
                    "created_at": iso(r[9]),
                    "church_id": r[10], "church_name": r[11], "church_role": r[12],
                }
                for r in rows
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# 用户详情
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/users/{email}")
def admin_user_detail(request: Request, email: str) -> dict:
    require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.id, u.email, u.nickname, u.avatar, u.login_type,
                       u.is_admin, u.is_banned, u.ban_reason, u.banned_at, u.created_at,
                       cm.church_id, c.name AS church_name, cm.role AS church_role,
                       ur.role AS sys_role
                FROM users u
                LEFT JOIN church_members cm ON cm.email = u.email
                LEFT JOIN churches c ON c.id = cm.church_id
                LEFT JOIN user_roles ur ON ur.email = u.email
                WHERE u.email = %s
                """,
                (email,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="用户不存在")
            iso = _state["to_shanghai_iso"]
            user = {
                "id": row[0], "email": row[1], "nickname": row[2], "avatar": row[3],
                "login_type": row[4], "is_admin": row[5], "is_banned": row[6],
                "ban_reason": row[7] or "", "banned_at": iso(row[8]),
                "created_at": iso(row[9]),
                "church_id": row[10], "church_name": row[11], "church_role": row[12],
                "sys_role": row[13] or "user",
            }

            # 活跃度
            cur.execute(
                "SELECT MAX(created_at) FROM user_tokens WHERE email = %s", (email,)
            )
            last_login = cur.fetchone()[0]
            user["last_login"] = iso(last_login)

            for col, tbl, where in [
                ("checkins", "user_checkins", "email"),
                ("posts", "community_posts", "email"),
                ("prayers", "prayers", "email"),
                ("journals", "devotion_journals", "email"),
            ]:
                try:
                    cur.execute(
                        f"SELECT COUNT(*) FROM {tbl} WHERE {where} = %s", (email,)
                    )
                    user[f"{col}_count"] = cur.fetchone()[0]
                except Exception:
                    user[f"{col}_count"] = None

        return {"ok": True, "user": user}
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# 封禁 / 解封
# ─────────────────────────────────────────────────────────────────────────────
class BanRequest(BaseModel):
    reason: str = Field(default="", max_length=500)


@router.post("/users/{email}/ban")
def admin_ban_user(request: Request, email: str, body: BanRequest) -> dict:
    admin = require_admin(request)
    if email == admin["email"]:
        raise HTTPException(status_code=400, detail="不能封禁自己")
    if email == _PROTECTED_EMAIL:
        raise HTTPException(status_code=400, detail="不能封禁超级管理员")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users SET is_banned = TRUE, banned_at = now(), ban_reason = %s
                WHERE email = %s
                """,
                (body.reason, email),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="用户不存在")
            audit(cur, admin["email"], "user.ban", "user", email,
                  {"reason": body.reason})
            conn.commit()
        _state["revoke_user_sessions"](email)
        return {"ok": True}
    finally:
        _state["release_db"](conn)


@router.post("/users/{email}/unban")
def admin_unban_user(request: Request, email: str) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users SET is_banned = FALSE, banned_at = NULL, ban_reason = ''
                WHERE email = %s
                """,
                (email,),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="用户不存在")
            audit(cur, admin["email"], "user.unban", "user", email, {})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# 设置/取消管理员
# ─────────────────────────────────────────────────────────────────────────────
class SetAdminRequest(BaseModel):
    is_admin: bool


@router.post("/users/{email}/set-admin")
def admin_set_admin(request: Request, email: str, body: SetAdminRequest) -> dict:
    admin = require_admin(request)
    if email == admin["email"]:
        raise HTTPException(status_code=400, detail="不能修改自己的管理员状态")
    if email == _PROTECTED_EMAIL:
        raise HTTPException(status_code=400, detail="不能修改超级管理员状态")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_admin = %s WHERE email = %s",
                (body.is_admin, email),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="用户不存在")
            new_role = "admin" if body.is_admin else "user"
            cur.execute(
                """
                INSERT INTO user_roles (email, role, updated_at)
                VALUES (%s, %s, now())
                ON CONFLICT (email) DO UPDATE SET role = %s, updated_at = now()
                """,
                (email, new_role, new_role),
            )
            audit(cur, admin["email"], "user.set_admin", "user", email,
                  {"is_admin": body.is_admin})
            conn.commit()
        _state["invalidate_admin_cache"](email)
        return {"ok": True}
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# 重置密码
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/users/{email}/reset-password")
def admin_reset_password(request: Request, email: str) -> dict:
    admin = require_admin(request)
    tmp_plain = secrets.token_urlsafe(8)
    tmp_hash = _state["hash_password"](tmp_plain)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s WHERE email = %s",
                (tmp_hash, email),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="用户不存在")
            audit(cur, admin["email"], "user.reset_password", "user", email,
                  {"note": "临时密码已设置，明文不记录"})
            conn.commit()
        _state["revoke_user_sessions"](email)
        return {"ok": True, "tmp_password": tmp_plain}
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# 教会管理
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/churches")
def admin_list_churches(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM churches")
            total = cur.fetchone()[0]
            cur.execute(
                """
                SELECT c.id, c.name, c.owner_email, c.join_code,
                       c.is_default, c.is_active, c.created_at,
                       COUNT(cm.email) AS member_count
                FROM churches c
                LEFT JOIN church_members cm ON cm.church_id = c.id
                GROUP BY c.id
                ORDER BY c.created_at DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "name": r[1], "owner_email": r[2],
                    "join_code": r[3], "is_default": r[4], "is_active": r[5],
                    "created_at": iso(r[6]), "member_count": r[7],
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.get("/churches/{cid}/members")
def admin_church_members(request: Request, cid: int) -> dict:
    require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM churches WHERE id = %s", (cid,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="教会不存在")
            cur.execute(
                """
                SELECT cm.email, cm.role, cm.joined_at, u.nickname, u.avatar
                FROM church_members cm
                LEFT JOIN users u ON u.email = cm.email
                WHERE cm.church_id = %s
                ORDER BY (cm.role = 'owner') DESC, cm.joined_at ASC
                """,
                (cid,),
            )
            iso = _state["to_shanghai_iso"]
            members = [
                {
                    "email": r[0], "role": r[1], "joined_at": iso(r[2]),
                    "nickname": r[3] or r[0].split("@")[0], "avatar": r[4] or "",
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "members": members}
    finally:
        _state["release_db"](conn)


class RenameChurchRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


@router.post("/churches/{cid}/rename")
def admin_rename_church(request: Request, cid: int, body: RenameChurchRequest) -> dict:
    admin = require_admin(request)
    name = _state["sanitize_text"](body.name.strip())
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM churches WHERE id = %s", (cid,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="教会不存在")
            old_name = row[0]
            cur.execute("UPDATE churches SET name = %s WHERE id = %s", (name, cid))
            audit(cur, admin["email"], "church.rename", "church", str(cid),
                  {"old_name": old_name, "new_name": name})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


class ToggleActiveRequest(BaseModel):
    is_active: bool


@router.post("/churches/{cid}/toggle-active")
def admin_toggle_church_active(request: Request, cid: int, body: ToggleActiveRequest) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT is_default FROM churches WHERE id = %s", (cid,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="教会不存在")
            if row[0] and not body.is_active:
                raise HTTPException(status_code=400, detail="不能停用默认教会")
            cur.execute(
                "UPDATE churches SET is_active = %s WHERE id = %s",
                (body.is_active, cid),
            )
            audit(cur, admin["email"], "church.toggle_active", "church", str(cid),
                  {"is_active": body.is_active})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


@router.post("/churches/{cid}/regenerate-code")
def admin_regen_church_code(request: Request, cid: int) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM churches WHERE id = %s", (cid,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="教会不存在")
            # 生成未占用的邀请码
            for _ in range(12):
                code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
                cur.execute("SELECT 1 FROM churches WHERE join_code = %s", (code,))
                if cur.fetchone() is None:
                    break
            else:
                code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(10))
            cur.execute(
                "UPDATE churches SET join_code = %s WHERE id = %s", (code, cid)
            )
            audit(cur, admin["email"], "church.regen_code", "church", str(cid), {})
            conn.commit()
        return {"ok": True, "join_code": code}
    finally:
        _state["release_db"](conn)


class DissolveChurchRequest(BaseModel):
    confirm_name: str


@router.post("/churches/{cid}/dissolve")
def admin_dissolve_church(request: Request, cid: int, body: DissolveChurchRequest) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name, is_default FROM churches WHERE id = %s", (cid,)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="教会不存在")
            name, is_default = row
            if is_default:
                raise HTTPException(status_code=400, detail="不能解散默认教会")
            if body.confirm_name != name:
                raise HTTPException(status_code=400, detail="confirm_name 与教会名不符")

            # 获取默认教会 id
            cur.execute("SELECT id FROM churches WHERE is_default = TRUE LIMIT 1")
            default_row = cur.fetchone()
            default_cid = default_row[0] if default_row else None

            # 快照成员
            cur.execute(
                "SELECT email, role FROM church_members WHERE church_id = %s", (cid,)
            )
            member_snapshot = [{"email": r[0], "role": r[1]} for r in cur.fetchall()]

            # 将成员迁移到默认教会
            if default_cid:
                cur.execute(
                    """
                    INSERT INTO church_members (church_id, email, role)
                    SELECT %s, email, 'member' FROM church_members WHERE church_id = %s
                    ON CONFLICT (email) DO NOTHING
                    """,
                    (default_cid, cid),
                )

            # 软停用教会
            cur.execute(
                "UPDATE churches SET is_active = FALSE WHERE id = %s", (cid,)
            )
            audit(cur, admin["email"], "church.dissolve", "church", str(cid),
                  {"name": name, "members": member_snapshot})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# 审计日志
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/audit-log")
def admin_audit_log(
    request: Request,
    action: str = Query(default=""),
    admin_email: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            filters = []
            params: list = []
            if action:
                filters.append("action ILIKE %s")
                params.append(f"%{action}%")
            if admin_email:
                filters.append("admin_email = %s")
                params.append(admin_email)
            where = ("WHERE " + " AND ".join(filters)) if filters else ""

            cur.execute(f"SELECT COUNT(*) FROM admin_audit_log {where}", params)
            total = cur.fetchone()[0]

            cur.execute(
                f"""
                SELECT id, admin_email, action, target_type, target_id, detail, created_at
                FROM admin_audit_log
                {where}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "admin_email": r[1], "action": r[2],
                    "target_type": r[3], "target_id": r[4],
                    "detail": r[5] if isinstance(r[5], dict) else {},
                    "created_at": iso(r[6]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)
