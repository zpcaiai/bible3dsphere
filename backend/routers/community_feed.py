"""
Community feed router — 在线社区：个人状态 + 消息 + 评论 + 阿们。
浏览公开，发帖/评论/阿们需登录。仿 prayer.py 的 _state 注入模式。

Endpoints (prefix /api):
  GET    /community/feed                         浏览信息流（公开）
  POST   /community/feed                         发帖（状态 + 消息）
  DELETE /community/feed/{post_id}               删除自己的帖子
  POST   /community/feed/{post_id}/amen          阿们（点赞）切换
  GET    /community/feed/{post_id}/comments      查看评论（公开）
  POST   /community/feed/{post_id}/comments      评论
  DELETE /community/feed/comments/{comment_id}   删除自己的评论
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["community-feed"])
_state: dict[str, Any] = {}


def init_community_feed_router(*, get_db, release_db, get_session_user, is_admin, sanitize_text, to_shanghai_iso) -> None:
    _state.update(locals())


class PostCreate(BaseModel):
    content: str = Field(default="", max_length=1000)
    status_key: str = Field(default="", max_length=64)
    status_label: str = Field(default="", max_length=64)
    status_emoji: str = Field(default="", max_length=16)


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def _post_row(row, viewer_email: str, amened_ids: set) -> dict:
    (pid, email, nickname, avatar, skey, slabel, semoji, content, amen, ccount, created_at) = row
    return {
        "id": pid,
        "nickname": nickname or "弟兄姐妹",
        "avatar": avatar or "",
        "status": {"key": skey, "label": slabel, "emoji": semoji},
        "content": content,
        "amen_count": amen,
        "comment_count": ccount,
        "is_own": bool(viewer_email) and email == viewer_email,
        "amened": pid in amened_ids,
        "created_at": _state["to_shanghai_iso"](created_at),
    }


@router.get("/community/feed")
def list_feed(
    request: Request,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> dict:
    user = _state["get_session_user"](request)
    email = user.get("email", "") if user else ""
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id,email,nickname,avatar,status_key,status_label,status_emoji,content,"
                "amen_count,comment_count,created_at "
                "FROM community_posts WHERE deleted_at IS NULL "
                "ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (limit, offset),
            )
            rows = cur.fetchall()
            cur.execute("SELECT COUNT(*) FROM community_posts WHERE deleted_at IS NULL")
            total = cur.fetchone()[0]
            amened: set = set()
            if email and rows:
                ids = tuple(r[0] for r in rows)
                # 注意：不可用 ANY(%s)+list——项目的 psycopg2 把 list 适配成 JSON 文本('[1]')，
                # 会触发 malformed array literal。tuple 走标准 IN (...) 适配。
                cur.execute(
                    "SELECT post_id FROM community_post_amens WHERE email=%s AND post_id IN %s",
                    (email, ids),
                )
                amened = {r[0] for r in cur.fetchall()}
        return {"ok": True, "items": [_post_row(r, email, amened) for r in rows], "total": total}
    finally:
        _state["release_db"](conn)


@router.post("/community/feed")
def create_post(payload: PostCreate, request: Request) -> dict:
    user = _require_user(request)
    s = _state["sanitize_text"]
    content = (payload.content or "").strip()
    if not content and not payload.status_key:
        raise HTTPException(status_code=400, detail="请选择一个状态，或写点什么")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO community_posts "
                "(email,nickname,avatar,status_key,status_label,status_emoji,content) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (
                    user.get("email", ""),
                    s(user.get("nickname", "") or "弟兄姐妹"),
                    user.get("avatar", "") or "",
                    payload.status_key[:64],
                    s(payload.status_label)[:64],
                    payload.status_emoji[:16],
                    s(content),
                ),
            )
            pid = cur.fetchone()[0]
            conn.commit()
        return {"ok": True, "id": pid}
    finally:
        _state["release_db"](conn)


@router.delete("/community/feed/{post_id}")
def delete_post(post_id: int, request: Request) -> dict:
    user = _require_user(request)
    email = user.get("email", "")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT email FROM community_posts WHERE id=%s AND deleted_at IS NULL", (post_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="帖子不存在")
            if row[0] != email and not _state["is_admin"](email):
                raise HTTPException(status_code=403, detail="无权删除")
            cur.execute("UPDATE community_posts SET deleted_at=now() WHERE id=%s", (post_id,))
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


@router.post("/community/feed/{post_id}/amen")
def toggle_amen(post_id: int, request: Request) -> dict:
    user = _require_user(request)
    email = user.get("email", "")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM community_posts WHERE id=%s AND deleted_at IS NULL", (post_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="帖子不存在")
            cur.execute("SELECT 1 FROM community_post_amens WHERE post_id=%s AND email=%s", (post_id, email))
            if cur.fetchone():
                cur.execute("DELETE FROM community_post_amens WHERE post_id=%s AND email=%s", (post_id, email))
                cur.execute(
                    "UPDATE community_posts SET amen_count=GREATEST(amen_count-1,0) WHERE id=%s RETURNING amen_count",
                    (post_id,),
                )
                amened = False
            else:
                cur.execute("INSERT INTO community_post_amens (post_id,email) VALUES (%s,%s)", (post_id, email))
                cur.execute(
                    "UPDATE community_posts SET amen_count=amen_count+1 WHERE id=%s RETURNING amen_count",
                    (post_id,),
                )
                amened = True
            count = cur.fetchone()[0]
            conn.commit()
        return {"ok": True, "amened": amened, "amen_count": count}
    finally:
        _state["release_db"](conn)


@router.get("/community/feed/{post_id}/comments")
def list_comments(post_id: int, request: Request) -> dict:
    user = _state["get_session_user"](request)
    email = user.get("email", "") if user else ""
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id,email,nickname,avatar,content,created_at FROM community_comments "
                "WHERE post_id=%s AND deleted_at IS NULL ORDER BY created_at ASC",
                (post_id,),
            )
            rows = cur.fetchall()
        items = [
            {
                "id": r[0],
                "nickname": r[2] or "弟兄姐妹",
                "avatar": r[3] or "",
                "content": r[4],
                "is_own": bool(email) and r[1] == email,
                "created_at": _state["to_shanghai_iso"](r[5]),
            }
            for r in rows
        ]
        return {"ok": True, "items": items}
    finally:
        _state["release_db"](conn)


@router.post("/community/feed/{post_id}/comments")
def create_comment(post_id: int, payload: CommentCreate, request: Request) -> dict:
    user = _require_user(request)
    s = _state["sanitize_text"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM community_posts WHERE id=%s AND deleted_at IS NULL", (post_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="帖子不存在")
            cur.execute(
                "INSERT INTO community_comments (post_id,email,nickname,avatar,content) "
                "VALUES (%s,%s,%s,%s,%s) RETURNING id,created_at",
                (
                    post_id,
                    user.get("email", ""),
                    s(user.get("nickname", "") or "弟兄姐妹"),
                    user.get("avatar", "") or "",
                    s(payload.content.strip()),
                ),
            )
            cid, created_at = cur.fetchone()
            cur.execute("UPDATE community_posts SET comment_count=comment_count+1 WHERE id=%s", (post_id,))
            conn.commit()
        return {"ok": True, "id": cid, "created_at": _state["to_shanghai_iso"](created_at)}
    finally:
        _state["release_db"](conn)


@router.delete("/community/feed/comments/{comment_id}")
def delete_comment(comment_id: int, request: Request) -> dict:
    user = _require_user(request)
    email = user.get("email", "")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT email,post_id FROM community_comments WHERE id=%s AND deleted_at IS NULL", (comment_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="评论不存在")
            if row[0] != email and not _state["is_admin"](email):
                raise HTTPException(status_code=403, detail="无权删除")
            cur.execute("UPDATE community_comments SET deleted_at=now() WHERE id=%s", (comment_id,))
            cur.execute("UPDATE community_posts SET comment_count=GREATEST(comment_count-1,0) WHERE id=%s", (row[1],))
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)
