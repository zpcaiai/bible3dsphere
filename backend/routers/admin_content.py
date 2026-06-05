"""
admin_content.py — 管理端：内容管理（帖子/评论/祷告/语音群/好友/聊天/推送）。

prefix: /api/admin
鉴权：每个端点首先调用 require_admin(request)。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

try:
    from routers.admin_common import _state, require_admin, audit, paginate
except ImportError:
    from backend.routers.admin_common import _state, require_admin, audit, paginate

router = APIRouter(prefix="/api/admin", tags=["admin-content"])

# 白名单：wall 参数到实际表名的映射（禁止拼接用户输入）
_PRAYER_TABLE_MAP: dict[str, str] = {
    "prayers": "prayers",
    "evangelism": "evangelism_prayers",
}

# evangelism_prayers 不含 church_id / is_public 列
_PRAYER_NO_CHURCH = {"evangelism_prayers"}


# ─────────────────────────────────────────────────────────────────────────────
# 帖子管理
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/posts")
def admin_list_posts(
    request: Request,
    q: str = Query(default=""),
    church_id: int | None = Query(default=None),
    include_deleted: bool = Query(default=False),
    is_public: bool | None = Query(default=None),
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
            if not include_deleted:
                filters.append("p.deleted_at IS NULL")
            if q:
                filters.append("p.content ILIKE %s")
                params.append(f"%{q}%")
            if church_id is not None:
                filters.append("p.church_id = %s")
                params.append(church_id)
            if is_public is not None:
                filters.append("p.is_public = %s")
                params.append(is_public)
            where = ("WHERE " + " AND ".join(filters)) if filters else ""

            cur.execute(
                f"SELECT COUNT(*) FROM community_posts p {where}", params
            )
            total = cur.fetchone()[0]

            cur.execute(
                f"""
                SELECT p.id, p.email, p.nickname, p.content,
                       p.amen_count, p.comment_count,
                       p.created_at, p.deleted_at, p.pinned_at,
                       p.is_public, p.church_id, c.name AS church_name
                FROM community_posts p
                LEFT JOIN churches c ON c.id = p.church_id
                {where}
                ORDER BY p.created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "email": r[1], "nickname": r[2],
                    "content": r[3][:200],
                    "amen_count": r[4], "comment_count": r[5],
                    "created_at": iso(r[6]), "deleted_at": iso(r[7]),
                    "pinned_at": iso(r[8]), "is_public": r[9],
                    "church_id": r[10], "church_name": r[11],
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.post("/posts/{post_id}/delete")
def admin_delete_post(request: Request, post_id: int) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT content FROM community_posts WHERE id = %s AND deleted_at IS NULL",
                (post_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="帖子不存在或已删除")
            snapshot = (row[0] or "")[:200]
            cur.execute(
                "UPDATE community_posts SET deleted_at = now() WHERE id = %s",
                (post_id,),
            )
            audit(cur, admin["email"], "post.delete", "post", str(post_id),
                  {"content_snapshot": snapshot})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


@router.post("/posts/{post_id}/restore")
def admin_restore_post(request: Request, post_id: int) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE community_posts SET deleted_at = NULL WHERE id = %s AND deleted_at IS NOT NULL",
                (post_id,),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="帖子不存在或未被删除")
            audit(cur, admin["email"], "post.restore", "post", str(post_id), {})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


@router.post("/posts/{post_id}/pin")
def admin_pin_post(request: Request, post_id: int) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE community_posts SET pinned_at = now() WHERE id = %s AND deleted_at IS NULL",
                (post_id,),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="帖子不存在")
            audit(cur, admin["email"], "post.pin", "post", str(post_id), {})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


@router.post("/posts/{post_id}/unpin")
def admin_unpin_post(request: Request, post_id: int) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE community_posts SET pinned_at = NULL WHERE id = %s",
                (post_id,),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="帖子不存在")
            audit(cur, admin["email"], "post.unpin", "post", str(post_id), {})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# 评论管理
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/posts/{post_id}/comments")
def admin_list_post_comments(
    request: Request,
    post_id: int,
    include_deleted: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            where = "" if include_deleted else "AND deleted_at IS NULL"
            cur.execute(
                f"SELECT COUNT(*) FROM community_comments WHERE post_id = %s {where}",
                (post_id,),
            )
            total = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT id, email, nickname, content, created_at, deleted_at
                FROM community_comments
                WHERE post_id = %s {where}
                ORDER BY created_at ASC
                LIMIT %s OFFSET %s
                """,
                (post_id, limit, offset),
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "email": r[1], "nickname": r[2],
                    "content": r[3], "created_at": iso(r[4]), "deleted_at": iso(r[5]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.post("/comments/{cid}/delete")
def admin_delete_comment(request: Request, cid: int) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE community_comments SET deleted_at = now() "
                "WHERE id = %s AND deleted_at IS NULL",
                (cid,),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="评论不存在或已删除")
            audit(cur, admin["email"], "comment.delete", "comment", str(cid), {})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


@router.post("/comments/{cid}/restore")
def admin_restore_comment(request: Request, cid: int) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE community_comments SET deleted_at = NULL "
                "WHERE id = %s AND deleted_at IS NOT NULL",
                (cid,),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="评论不存在或未被删除")
            audit(cur, admin["email"], "comment.restore", "comment", str(cid), {})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# 祷告管理
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/prayers")
def admin_list_prayers(
    request: Request,
    wall: str = Query(default="prayers"),
    q: str = Query(default=""),
    church_id: int | None = Query(default=None),
    is_public: bool | None = Query(default=None),
    include_deleted: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    tbl = _PRAYER_TABLE_MAP.get(wall)
    if tbl is None:
        raise HTTPException(status_code=400, detail="wall 参数无效，仅支持 prayers / evangelism")
    limit, offset = paginate(page, page_size)
    no_church = tbl in _PRAYER_NO_CHURCH
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            filters = []
            params: list = []
            if not include_deleted:
                filters.append("deleted_at IS NULL")
            if q:
                filters.append("content ILIKE %s")
                params.append(f"%{q}%")
            if church_id is not None and not no_church:
                filters.append("church_id = %s")
                params.append(church_id)
            if is_public is not None and not no_church:
                filters.append("is_public = %s")
                params.append(is_public)
            where = ("WHERE " + " AND ".join(filters)) if filters else ""

            cur.execute(f"SELECT COUNT(*) FROM {tbl} {where}", params)
            total = cur.fetchone()[0]

            cur.execute(
                f"""
                SELECT id, email, nickname, content, amen_count,
                       created_at, deleted_at
                FROM {tbl}
                {where}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "email": r[1], "nickname": r[2],
                    "content": r[3], "amen_count": r[4],
                    "created_at": iso(r[5]), "deleted_at": iso(r[6]),
                    "wall": wall,
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.post("/prayers/{prayer_id}/delete")
def admin_delete_prayer(
    request: Request, prayer_id: int, wall: str = Query(default="prayers")
) -> dict:
    admin = require_admin(request)
    tbl = _PRAYER_TABLE_MAP.get(wall)
    if tbl is None:
        raise HTTPException(status_code=400, detail="wall 参数无效")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE {tbl} SET deleted_at = now() WHERE id = %s AND deleted_at IS NULL",
                (prayer_id,),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="祷告不存在或已删除")
            audit(cur, admin["email"], "prayer.delete", tbl, str(prayer_id), {"wall": wall})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


@router.post("/prayers/{prayer_id}/restore")
def admin_restore_prayer(
    request: Request, prayer_id: int, wall: str = Query(default="prayers")
) -> dict:
    admin = require_admin(request)
    tbl = _PRAYER_TABLE_MAP.get(wall)
    if tbl is None:
        raise HTTPException(status_code=400, detail="wall 参数无效")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE {tbl} SET deleted_at = NULL WHERE id = %s AND deleted_at IS NOT NULL",
                (prayer_id,),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="祷告不存在或未被删除")
            audit(cur, admin["email"], "prayer.restore", tbl, str(prayer_id), {"wall": wall})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# 语音群管理（只读 + 删除）
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/voice-groups")
def admin_list_voice_groups(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM voice_groups")
            total = cur.fetchone()[0]
            cur.execute(
                """
                SELECT vg.id, vg.name, vg.owner, vg.join_code,
                       vg.is_active, vg.created_at, vg.church_id,
                       c.name AS church_name,
                       COUNT(vm.email) AS member_count
                FROM voice_groups vg
                LEFT JOIN churches c ON c.id = vg.church_id
                LEFT JOIN voice_group_members vm ON vm.group_id = vg.id
                GROUP BY vg.id, c.name
                ORDER BY vg.created_at DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "name": r[1], "owner": r[2], "join_code": r[3],
                    "is_active": r[4], "created_at": iso(r[5]),
                    "church_id": r[6], "church_name": r[7], "member_count": r[8],
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.post("/voice-groups/{gid}/delete")
def admin_delete_voice_group(request: Request, gid: str) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT name, owner FROM voice_groups WHERE id = %s", (gid,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="语音群不存在")
            name, owner = row
            cur.execute(
                "SELECT email, role FROM voice_group_members WHERE group_id = %s", (gid,)
            )
            members_snapshot = [{"email": r[0], "role": r[1]} for r in cur.fetchall()]
            cur.execute("DELETE FROM voice_group_members WHERE group_id = %s", (gid,))
            cur.execute("DELETE FROM voice_groups WHERE id = %s", (gid,))
            audit(cur, admin["email"], "voice_group.delete", "voice_group", gid,
                  {"name": name, "owner": owner, "members": members_snapshot})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# 好友 / 聊天（只读）
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/friendships")
def admin_list_friendships(
    request: Request,
    email: str = Query(default=""),
    status: str = Query(default=""),
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
            if email:
                filters.append("(requester = %s OR addressee = %s)")
                params += [email, email]
            if status:
                filters.append("status = %s")
                params.append(status)
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            cur.execute(f"SELECT COUNT(*) FROM friendships {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT id, requester, addressee, status, created_at, updated_at
                FROM friendships {where}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "requester": r[1], "addressee": r[2],
                    "status": r[3], "created_at": iso(r[4]), "updated_at": iso(r[5]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.get("/chat-messages")
def admin_list_chat_messages(
    request: Request,
    email: str = Query(default=""),
    from_time: str = Query(default=""),
    to_time: str = Query(default=""),
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
            if email:
                filters.append("(sender = %s OR recipient = %s)")
                params += [email, email]
            if from_time:
                filters.append("created_at >= %s::timestamptz")
                params.append(from_time)
            if to_time:
                filters.append("created_at <= %s::timestamptz")
                params.append(to_time)
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            cur.execute(f"SELECT COUNT(*) FROM chat_messages {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT id, sender, recipient, body, kind, created_at
                FROM chat_messages {where}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "sender": r[1], "recipient": r[2],
                    "body": r[3], "kind": r[4], "created_at": iso(r[5]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit,
                "note": "只读，不提供删除接口"}
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# Push 订阅管理
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/push-subscriptions")
def admin_list_push_subscriptions(
    request: Request,
    email: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            where = "WHERE email = %s" if email else ""
            params = [email] if email else []
            cur.execute(f"SELECT COUNT(*) FROM push_subscriptions {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT id, email, endpoint, enabled, morning_on, evening_on,
                       created_at, updated_at
                FROM push_subscriptions {where}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "email": r[1], "endpoint": r[2][:60] + "...",
                    "enabled": r[3], "morning_on": r[4], "evening_on": r[5],
                    "created_at": iso(r[6]), "updated_at": iso(r[7]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.delete("/push-subscriptions")
def admin_delete_push_subscriptions(
    request: Request, email: str = Query(...)
) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM push_subscriptions WHERE email = %s", (email,))
            count = cur.fetchone()[0]
            cur.execute("DELETE FROM push_subscriptions WHERE email = %s", (email,))
            audit(cur, admin["email"], "push.delete", "push_subscriptions", email,
                  {"deleted_count": count})
            conn.commit()
        return {"ok": True, "deleted": count}
    finally:
        _state["release_db"](conn)
