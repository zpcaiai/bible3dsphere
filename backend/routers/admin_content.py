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
                       COALESCE(mccheyne_on, TRUE), last_mccheyne_sent,
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
                    "mccheyne_on": r[6],
                    "last_mccheyne_sent": r[7].isoformat() if r[7] else None,
                    "created_at": iso(r[8]), "updated_at": iso(r[9]),
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


# ─────────────────────────────────────────────────────────────────────────────
# 见证墙管理
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/testimonies")
def admin_list_testimonies(
    request: Request,
    q: str = Query(default=""),
    email: str = Query(default=""),
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
                filters.append("deleted_at IS NULL")
            if q:
                filters.append("(title ILIKE %s OR before_story ILIKE %s OR how_story ILIKE %s OR after_story ILIKE %s)")
                params += [f"%{q}%"] * 4
            if email:
                filters.append("email = %s")
                params.append(email)
            if is_public is not None:
                filters.append("is_public = %s")
                params.append(is_public)
            where = ("WHERE " + " AND ".join(filters)) if filters else ""

            cur.execute(f"SELECT COUNT(*) FROM testimonies {where}", params)
            total = cur.fetchone()[0]

            cur.execute(
                f"""
                SELECT id, email, nickname, title, before_story, how_story, after_story,
                       is_anonymous, is_public, amen_count, church_id,
                       created_at, updated_at, deleted_at
                FROM testimonies
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
                    "title": r[3],
                    "before_story": (r[4] or "")[:120] if r[4] else "",
                    "how_story": (r[5] or "")[:120] if r[5] else "",
                    "after_story": (r[6] or "")[:120] if r[6] else "",
                    "is_anonymous": r[7], "is_public": r[8],
                    "amen_count": r[9], "church_id": r[10],
                    "created_at": iso(r[11]), "updated_at": iso(r[12]),
                    "deleted_at": iso(r[13]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.post("/testimonies/{tid}/delete")
def admin_delete_testimony(request: Request, tid: int) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT title, email FROM testimonies WHERE id=%s AND deleted_at IS NULL", (tid,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="见证不存在或已删除")
            title, owner = row
            cur.execute("UPDATE testimonies SET deleted_at=NOW() WHERE id=%s", (tid,))
            audit(cur, admin["email"], "testimony.delete", "testimonies", str(tid),
                  {"title": title, "owner": owner})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


@router.post("/testimonies/{tid}/restore")
def admin_restore_testimony(request: Request, tid: int) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT title, email FROM testimonies WHERE id=%s AND deleted_at IS NOT NULL", (tid,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="见证不存在或未删除")
            title, owner = row
            cur.execute("UPDATE testimonies SET deleted_at=NULL WHERE id=%s", (tid,))
            audit(cur, admin["email"], "testimony.restore", "testimonies", str(tid),
                  {"title": title, "owner": owner})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# 回收站（全局）
# ─────────────────────────────────────────────────────────────────────────────
_RECYCLE_TABLES = [
    ("prayer", "prayers", "content", "nickname", "代祷"),
    ("evangelism", "evangelism_prayers", "content", "nickname", "传FY"),
    ("devotion", "devotion_journals", "title", "scripture_text", "灵修日记"),
    ("personal", "personal_notes", "scripture", "mood", "我的日记"),
    ("sermon", "sermon_journals", "title", "preacher", "主日信息"),
    ("testimony", "testimonies", "title", "email", "见证"),
]


@router.get("/recycle-bin")
def admin_list_recycle_bin(
    request: Request,
    email: str = Query(default=""),
    type: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    # Bound rows scanned per table to avoid loading the entire recycle bin into memory.
    # The global top (offset+limit) by deleted_at is contained in each table's top (offset+limit).
    _fetch_cap = min(offset + limit, 2000)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            items = []
            total = 0
            iso = _state["to_shanghai_iso"]
            for tkey, tbl, title_col, sub_col, label in _RECYCLE_TABLES:
                if type and tkey != type:
                    continue
                email_filter = "AND email = %s" if email else ""
                params = [email] if email else []
                # Accurate total via COUNT (cheap) so pagination metadata stays correct.
                cur.execute(
                    f"SELECT COUNT(*) FROM {tbl} WHERE deleted_at IS NOT NULL {email_filter}",
                    params,
                )
                total += int(cur.fetchone()[0] or 0)
                cur.execute(
                    f"SELECT id, {title_col}, {sub_col}, email, deleted_at FROM {tbl} "
                    f"WHERE deleted_at IS NOT NULL {email_filter} "
                    "ORDER BY deleted_at DESC LIMIT %s",
                    params + [_fetch_cap],
                )
                for r in cur.fetchall():
                    items.append({
                        "type": tkey,
                        "type_label": label,
                        "id": r[0],
                        "title": (r[1] or "")[:80],
                        "subtitle": (r[2] or "")[:40],
                        "email": r[3],
                        "deleted_at": iso(r[4]),
                    })
            items.sort(key=lambda x: x["deleted_at"] or "", reverse=True)
            sliced = items[offset:offset + limit]
        return {"ok": True, "items": sliced, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.post("/recycle-bin/{item_type}/{item_id}/restore")
def admin_restore_recycle_item(request: Request, item_type: str, item_id: str) -> dict:
    admin = require_admin(request)
    table_map = {t[0]: t[1] for t in _RECYCLE_TABLES}
    table = table_map.get(item_type)
    if not table:
        raise HTTPException(status_code=400, detail=f"Unknown type: {item_type}")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT deleted_at FROM {table} WHERE id=%s", (item_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Item not found")
            if not row[0]:
                raise HTTPException(status_code=400, detail="Item is not deleted")
            cur.execute(f"UPDATE {table} SET deleted_at=NULL WHERE id=%s", (item_id,))
            audit(cur, admin["email"], "recycle.restore", table, item_id,
                  {"type": item_type})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# Guardian 属灵守护者管理
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/guardian/emotions")
def admin_list_guardian_emotions(
    request: Request,
    email: str = Query(default=""),
    emotion_type: str = Query(default=""),
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
                filters.append("email = %s")
                params.append(email)
            if emotion_type:
                filters.append("emotion_type = %s")
                params.append(emotion_type)
            if from_time:
                filters.append("created_at >= %s::timestamptz")
                params.append(from_time)
            if to_time:
                filters.append("created_at <= %s::timestamptz")
                params.append(to_time)
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            cur.execute(f"SELECT COUNT(*) FROM guardian_emotion_events {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT id, email, emotion_type, intensity, trigger, note, source, created_at
                FROM guardian_emotion_events {where}
                ORDER BY created_at DESC LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "email": r[1], "emotion_type": r[2], "intensity": r[3],
                    "trigger": r[5] or "", "note": r[5] or "", "source": r[6] or "",
                    "created_at": iso(r[7]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.get("/guardian/spiritual-checkins")
def admin_list_guardian_spiritual(
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
            cur.execute(f"SELECT COUNT(*) FROM guardian_spiritual_checkins {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT id, email, faith_level, hope_level, love_level, spiritual_state, note, created_at
                FROM guardian_spiritual_checkins {where}
                ORDER BY created_at DESC LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "email": r[1], "faith_level": r[2], "hope_level": r[3],
                    "love_level": r[4], "spiritual_state": r[5] or "", "note": r[6] or "",
                    "created_at": iso(r[7]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.get("/guardian/prayers")
def admin_list_guardian_prayers(
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
                filters.append("email = %s")
                params.append(email)
            if status:
                filters.append("status = %s")
                params.append(status)
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            cur.execute(f"SELECT COUNT(*) FROM guardian_prayer_entries {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT id, email, title, content, category, status, answered_at, created_at
                FROM guardian_prayer_entries {where}
                ORDER BY created_at DESC LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "email": r[1], "title": r[2], "content": (r[3] or "")[:200],
                    "category": r[4] or "", "status": r[5], "answered_at": iso(r[6]),
                    "created_at": iso(r[7]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.get("/guardian/messages")
def admin_list_guardian_messages(
    request: Request,
    email: str = Query(default=""),
    mode: str = Query(default=""),
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
                filters.append("email = %s")
                params.append(email)
            if mode:
                filters.append("mode = %s")
                params.append(mode)
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            cur.execute(f"SELECT COUNT(*) FROM guardian_messages {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT id, email, role, content, mode, created_at
                FROM guardian_messages {where}
                ORDER BY created_at DESC LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "email": r[1], "role": r[2], "content": (r[3] or "")[:300],
                    "mode": r[4] or "companion", "created_at": iso(r[5]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# 分享墙管理
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/shared-notes")
def admin_list_shared_notes(
    request: Request,
    q: str = Query(default=""),
    email: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            filters = ["pn.shared=TRUE", "pn.deleted_at IS NULL"]
            params: list = []
            if q:
                filters.append("(pn.scripture ILIKE %s OR pn.observation ILIKE %s OR pn.reflection ILIKE %s)")
                params += [f"%{q}%"] * 3
            if email:
                filters.append("pn.email = %s")
                params.append(email)
            where = "WHERE " + " AND ".join(filters)
            cur.execute(
                f"""
                SELECT COUNT(*) FROM personal_notes pn {where}
                """,
                params,
            )
            total = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT pn.id, pn.email, pn.note_date, pn.scripture, pn.observation, pn.reflection,
                       pn.application, pn.prayer, pn.mood, pn.author, pn.avatar,
                       pn.shared_at, pn.created_at, pn.updated_at,
                       COALESCE(ni.amen_count, 0) AS amen_count
                FROM personal_notes pn
                LEFT JOIN (
                    SELECT note_id, COUNT(*) AS amen_count
                    FROM note_interactions WHERE action='amen'
                    GROUP BY note_id
                ) ni ON ni.note_id = pn.id
                {where}
                ORDER BY pn.shared_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "email": r[1], "note_date": str(r[2]) if r[2] else "",
                    "scripture": r[3] or "", "observation": (r[4] or "")[:120],
                    "reflection": (r[5] or "")[:120], "application": (r[6] or "")[:120],
                    "prayer": (r[7] or "")[:120], "mood": r[8] or "",
                    "author": r[9] or "", "avatar": r[10] or "",
                    "shared_at": iso(r[11]), "created_at": iso(r[12]), "updated_at": iso(r[13]),
                    "amen_count": r[14],
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.post("/shared-notes/{note_id}/unshare")
def admin_unshare_note(request: Request, note_id: str) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT email, shared FROM personal_notes WHERE id=%s", (note_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="笔记不存在")
            owner, currently_shared = row
            if not currently_shared:
                raise HTTPException(status_code=400, detail="笔记未处于分享状态")
            cur.execute(
                "UPDATE personal_notes SET shared=FALSE, shared_at=NULL WHERE id=%s",
                (note_id,)
            )
            audit(cur, admin["email"], "shared_note.unshare", "personal_notes", note_id,
                  {"owner": owner})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# 灵修日记 / 讲道笔记管理
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/devotion-journals")
def admin_list_devotion_journals(
    request: Request,
    q: str = Query(default=""),
    email: str = Query(default=""),
    include_deleted: bool = Query(default=False),
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
                filters.append("deleted_at IS NULL")
            if q:
                filters.append("(title ILIKE %s OR scripture_text ILIKE %s OR observation ILIKE %s)")
                params += [f"%{q}%"] * 3
            if email:
                filters.append("email = %s")
                params.append(email)
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            cur.execute(f"SELECT COUNT(*) FROM devotion_journals {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT id, email, journal_date, title, scripture_text, observation,
                       reflection, application, prayer, mood, created_at, updated_at, deleted_at
                FROM devotion_journals {where}
                ORDER BY updated_at DESC LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "email": r[1], "journal_date": str(r[2]) if r[2] else "",
                    "title": r[3] or "", "scripture": r[4] or "",
                    "observation": (r[5] or "")[:120], "reflection": (r[6] or "")[:120],
                    "application": (r[7] or "")[:120], "prayer": (r[8] or "")[:120],
                    "mood": r[9] or "", "created_at": iso(r[10]),
                    "updated_at": iso(r[11]), "deleted_at": iso(r[12]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.get("/sermon-journals")
def admin_list_sermon_journals(
    request: Request,
    q: str = Query(default=""),
    email: str = Query(default=""),
    include_deleted: bool = Query(default=False),
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
                filters.append("deleted_at IS NULL")
            if q:
                filters.append("(title ILIKE %s OR scripture ILIKE %s OR outline ILIKE %s OR reflection ILIKE %s)")
                params += [f"%{q}%"] * 4
            if email:
                filters.append("email = %s")
                params.append(email)
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            cur.execute(f"SELECT COUNT(*) FROM sermon_journals {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT id, email, title, preacher, scripture, outline, reflection, application,
                       prayer, tags, is_shared, created_at, updated_at, deleted_at
                FROM sermon_journals {where}
                ORDER BY updated_at DESC LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "email": r[1], "title": r[2] or "", "preacher": r[3] or "",
                    "scripture": r[4] or "", "outline": (r[5] or "")[:120],
                    "reflection": (r[6] or "")[:120], "application": (r[7] or "")[:120],
                    "prayer": (r[8] or "")[:120], "tags": r[9] or [],
                    "is_shared": r[10] or False, "created_at": iso(r[11]),
                    "updated_at": iso(r[12]), "deleted_at": iso(r[13]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.post("/devotion-journals/{jid}/delete")
def admin_delete_devotion_journal(request: Request, jid: int) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT title, email FROM devotion_journals WHERE id=%s AND deleted_at IS NULL", (jid,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="日记不存在或已删除")
            title, owner = row
            cur.execute("UPDATE devotion_journals SET deleted_at=NOW() WHERE id=%s", (jid,))
            audit(cur, admin["email"], "devotion_journal.delete", "devotion_journals", str(jid),
                  {"title": title, "owner": owner})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


@router.post("/devotion-journals/{jid}/restore")
def admin_restore_devotion_journal(request: Request, jid: int) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT title, email FROM devotion_journals WHERE id=%s AND deleted_at IS NOT NULL", (jid,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="日记不存在或未删除")
            title, owner = row
            cur.execute("UPDATE devotion_journals SET deleted_at=NULL WHERE id=%s", (jid,))
            audit(cur, admin["email"], "devotion_journal.restore", "devotion_journals", str(jid),
                  {"title": title, "owner": owner})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


@router.post("/sermon-journals/{jid}/delete")
def admin_delete_sermon_journal(request: Request, jid: int) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT title, email FROM sermon_journals WHERE id=%s AND deleted_at IS NULL", (jid,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="笔记不存在或已删除")
            title, owner = row
            cur.execute("UPDATE sermon_journals SET deleted_at=NOW() WHERE id=%s", (jid,))
            audit(cur, admin["email"], "sermon_journal.delete", "sermon_journals", str(jid),
                  {"title": title, "owner": owner})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


@router.post("/sermon-journals/{jid}/restore")
def admin_restore_sermon_journal(request: Request, jid: int) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT title, email FROM sermon_journals WHERE id=%s AND deleted_at IS NOT NULL", (jid,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="笔记不存在或未删除")
            title, owner = row
            cur.execute("UPDATE sermon_journals SET deleted_at=NULL WHERE id=%s", (jid,))
            audit(cur, admin["email"], "sermon_journal.restore", "sermon_journals", str(jid),
                  {"title": title, "owner": owner})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)
# 第三批功能 Admin API - 背经、习惯追踪、读经计划、签到、感恩日记

# 背经管理 (Memory Verses)
@router.get("/memory-verses")
def admin_list_memory_verses(
    request: Request,
    q: str = Query(default=""),
    email: str = Query(default=""),
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
            if q:
                filters.append("(reference ILIKE %s OR verse_text ILIKE %s)")
                params += [f"%{q}%"] * 2
            if email:
                filters.append("email = %s")
                params.append(email)
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            cur.execute(f"SELECT COUNT(*) FROM memory_verses {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"SELECT id, email, reference, verse_text, ease, interval_days, repetitions, due_date, last_reviewed, created_at FROM memory_verses {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [{"id": r[0], "email": r[1], "reference": r[2], "verse_text": (r[3] or "")[:200], "ease": r[4], "interval_days": r[5], "repetitions": r[6], "due_date": str(r[7]) if r[7] else "", "last_reviewed": iso(r[8]), "created_at": iso(r[9])} for r in cur.fetchall()]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.delete("/memory-verses/{vid}")
def admin_delete_memory_verse(request: Request, vid: str) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT reference, email FROM memory_verses WHERE id=%s", (vid,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="经文不存在")
            ref, owner = row
            cur.execute("DELETE FROM memory_verses WHERE id=%s", (vid,))
            audit(cur, admin["email"], "memory_verse.delete", "memory_verses", vid, {"reference": ref, "owner": owner})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


# 习惯追踪管理 (Habit Tracking)
@router.get("/habits")
def admin_list_habits(
    request: Request,
    q: str = Query(default=""),
    user_id: str = Query(default=""),
    is_active: str = Query(default=""),
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
            if q:
                filters.append("habit_name ILIKE %s")
                params.append(f"%{q}%")
            if user_id:
                filters.append("user_id = %s")
                params.append(user_id)
            if is_active:
                filters.append("is_active = %s")
                params.append(is_active == 'true')
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            cur.execute(f"SELECT COUNT(*) FROM habit_state_machines {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"SELECT id, user_id, habit_name, deterministic_anchor, is_active, current_streak_days, total_executions, last_execution_at, created_at FROM habit_state_machines {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [{"id": r[0], "user_id": r[1], "habit_name": r[2], "anchor": r[3] or "", "is_active": r[4], "streak": r[5], "total": r[6], "last_at": iso(r[7]), "created_at": iso(r[8])} for r in cur.fetchall()]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.get("/habits/{habit_id}/executions")
def admin_list_habit_executions(
    request: Request, habit_id: int, page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, tier_executed, was_completed, completion_percentage, mood_before, mood_after, tokens_earned, executed_at FROM habit_executions WHERE habit_id=%s ORDER BY executed_at DESC LIMIT %s OFFSET %s",
                (habit_id, limit, offset),
            )
            iso = _state["to_shanghai_iso"]
            items = [{"id": r[0], "tier": r[1], "completed": r[2], "percentage": r[3], "mood_before": r[4], "mood_after": r[5], "tokens": r[6], "executed_at": iso(r[7])} for r in cur.fetchall()]
            cur.execute("SELECT COUNT(*) FROM habit_executions WHERE habit_id=%s", (habit_id,))
            total = cur.fetchone()[0]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


# 读经计划管理 (Reading Plans)
@router.get("/reading-enrollments")
def admin_list_reading_enrollments(
    request: Request,
    email: str = Query(default=""),
    plan_id: str = Query(default=""),
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
                filters.append("email = %s")
                params.append(email)
            if plan_id:
                filters.append("plan_id ILIKE %s")
                params.append(f"%{plan_id}%")
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            cur.execute(f"SELECT COUNT(*) FROM reading_plan_enrollment {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"SELECT email, plan_id, active, start_date FROM reading_plan_enrollment {where} ORDER BY start_date DESC LIMIT %s OFFSET %s",
                params + [limit, offset],
            )
            items = [{"email": r[0], "plan_id": r[1], "active": r[2], "start_date": str(r[3]) if r[3] else ""} for r in cur.fetchall()]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.get("/reading-progress")
def admin_list_reading_progress(
    request: Request,
    email: str = Query(default=""),
    plan_id: str = Query(default=""),
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
                filters.append("email = %s")
                params.append(email)
            if plan_id:
                filters.append("plan_id ILIKE %s")
                params.append(f"%{plan_id}%")
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            cur.execute(f"SELECT COUNT(*) FROM reading_plan_progress {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"SELECT email, plan_id, day_key, completed_at FROM reading_plan_progress {where} ORDER BY completed_at DESC LIMIT %s OFFSET %s",
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [{"email": r[0], "plan_id": r[1], "day_key": r[2], "completed_at": iso(r[3])} for r in cur.fetchall()]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.get("/bible-reading-progress")
def admin_list_bible_reading_progress(
    request: Request,
    email: str = Query(default=""),
    book: str = Query(default=""),
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
                filters.append("email = %s")
                params.append(email)
            if book:
                filters.append("book ILIKE %s")
                params.append(f"%{book}%")
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            cur.execute(f"SELECT COUNT(*) FROM bible_reading_progress {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"SELECT email, book, chapter, highlight, read_at, plan_id FROM bible_reading_progress {where} ORDER BY read_at DESC LIMIT %s OFFSET %s",
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [{"email": r[0], "book": r[1], "chapter": r[2], "highlight": (r[3] or "")[:100], "read_at": iso(r[4]), "plan_id": r[5] or ""} for r in cur.fetchall()]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


# 签到管理 (Check-ins)
@router.get("/checkins")
def admin_list_checkins(
    request: Request,
    email: str = Query(default=""),
    emotion_label: str = Query(default=""),
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
                filters.append("email = %s")
                params.append(email)
            if emotion_label:
                filters.append("emotion_label ILIKE %s")
                params.append(f"%{emotion_label}%")
            if from_time:
                filters.append("checkin_at >= %s::timestamptz")
                params.append(from_time)
            if to_time:
                filters.append("checkin_at <= %s::timestamptz")
                params.append(to_time)
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            cur.execute(f"SELECT COUNT(*) FROM user_checkins {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"SELECT id, email, checkin_at, emotion_label, mood, data FROM user_checkins {where} ORDER BY checkin_at DESC LIMIT %s OFFSET %s",
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [{"id": r[0], "email": r[1], "checkin_at": iso(r[2]), "emotion_label": r[3] or "", "mood": r[4] or "", "data_preview": str(r[5])[:200] if r[5] else ""} for r in cur.fetchall()]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


# 感恩日记管理 (Gratitude Journal)
@router.get("/gratitude-entries")
def admin_list_gratitude_entries(
    request: Request,
    email: str = Query(default=""),
    q: str = Query(default=""),
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
                filters.append("email = %s")
                params.append(email)
            if q:
                filters.append("content ILIKE %s")
                params.append(f"%{q}%")
            if from_time:
                filters.append("created_at >= %s::timestamptz")
                params.append(from_time)
            if to_time:
                filters.append("created_at <= %s::timestamptz")
                params.append(to_time)
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            cur.execute(f"SELECT COUNT(*) FROM gratitude_entries {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"SELECT id, email, content, created_at FROM gratitude_entries {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [{"id": r[0], "email": r[1], "content": (r[2] or "")[:300], "created_at": iso(r[3])} for r in cur.fetchall()]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.delete("/gratitude-entries/{gid}")
def admin_delete_gratitude_entry(request: Request, gid: str) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT content, email FROM gratitude_entries WHERE id=%s", (gid,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="条目不存在")
            content, owner = row
            cur.execute("DELETE FROM gratitude_entries WHERE id=%s", (gid,))
            audit(cur, admin["email"], "gratitude.delete", "gratitude_entries", gid, {"content_preview": (content or "")[:100], "owner": owner})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)
