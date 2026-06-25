"""
Prayer wall router.
教会隔离：祷告默认仅同教会可见；is_public=True 时跨教会公开。
发帖须已登录且有教会；阿们/评论须可见性检查。

Covers: /api/prayers (CRUD + amen + status)
"""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["prayer"])
_state: dict[str, Any] = {}

# 延迟导入 church 缓存（双路径）
try:
    from core.deps import get_user_church_id
except ImportError:
    try:
        from backend.core.deps import get_user_church_id
    except ImportError:
        def get_user_church_id(cur, email, *, use_cache=True):  # type: ignore[misc]
            return None


def init_prayer_router(*, get_db, release_db, get_session_user, is_admin, sanitize_text, to_shanghai_iso) -> None:
    _state.update(locals())


class PrayerSubmitRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    is_anonymous: bool = False
    is_public: bool = False


class PrayerUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)


def _row_to_prayer(row, viewer_email: str = "", viewer_cid=None) -> dict:
    pid, email, nickname, content, is_anon, amen, created_at, updated_at, deleted_at, status, is_public, post_church_id = row
    # 匿名且公开的祷告，对外隐藏 email
    display_email = "" if (is_anon and is_public and email != viewer_email) else email
    same_church = (
        viewer_cid is not None
        and post_church_id is not None
        and viewer_cid == post_church_id
    )
    return {
        "id": pid,
        "email": display_email,
        "nickname": nickname or "弟兄姐妹",
        "content": content,
        "is_own": email == viewer_email,
        "amen_count": amen,
        "status": status,
        "is_public": is_public,
        "same_church": same_church,
        "created_at": _state["to_shanghai_iso"](created_at),
        "updated_at": _state["to_shanghai_iso"](updated_at),
        "deleted_at": _state["to_shanghai_iso"](deleted_at),
    }


def _visible_prayer(cur, prayer_id: int, cid) -> bool:
    """可见性：公开 OR 同教会（deleted_at IS NULL 已含）。"""
    effective_cid = cid if cid is not None else -1
    cur.execute(
        "SELECT 1 FROM prayers "
        "WHERE id=%s AND deleted_at IS NULL "
        "AND (is_public = TRUE OR (church_id IS NOT NULL AND church_id = %s))",
        (prayer_id, effective_cid),
    )
    return cur.fetchone() is not None


@router.get("/prayers")
def get_prayers(
    request: Request,
    limit: int = Query(default=40, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    user = _state["get_session_user"](request)
    email = user.get("email", "") if user else ""
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cid = get_user_church_id(cur, email) if email else None
            effective_cid = cid if cid is not None else -1

            cur.execute(
                "SELECT id, email, nickname, content, is_anonymous, amen_count, "
                "created_at, updated_at, deleted_at, status, is_public, church_id "
                "FROM prayers WHERE deleted_at IS NULL "
                "AND (is_public = TRUE OR (church_id IS NOT NULL AND church_id = %s)) "
                "ORDER BY updated_at DESC LIMIT %s OFFSET %s",
                (effective_cid, min(limit, 100), offset),
            )
            rows = cur.fetchall()
            cur.execute(
                "SELECT COUNT(*) FROM prayers WHERE deleted_at IS NULL "
                "AND (is_public = TRUE OR (church_id IS NOT NULL AND church_id = %s))",
                (effective_cid,),
            )
            total = cur.fetchone()[0]
        return {
            "ok": True,
            "items": [_row_to_prayer(r, email, cid) for r in rows],
            "total": total,
            "is_admin": _state["is_admin"](email),
        }
    finally:
        _state["release_db"](conn)


@router.post("/prayers")
def post_prayer(payload: PrayerSubmitRequest, request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="请先登录")
    email = user.get("email", "")
    nickname = user.get("nickname", "") or "弟兄姐妹"
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cid = get_user_church_id(cur, email)
            if cid is None:
                raise HTTPException(status_code=400, detail="请先加入或创建教会")
            cur.execute(
                "INSERT INTO prayers (email, nickname, content, is_anonymous, amen_count, church_id, is_public) "
                "VALUES (%s,%s,%s,%s,0,%s,%s) RETURNING id",
                (
                    email,
                    _state["sanitize_text"](nickname),
                    _state["sanitize_text"](payload.content.strip()),
                    payload.is_anonymous,
                    cid,
                    payload.is_public,
                ),
            )
            prayer_id = cur.fetchone()[0]
            conn.commit()
        try:
            import formation_events as _fe
            _fe.record_event(email, "prayer", "prayer", title="发布祷告",
                             summary=(payload.content or "").strip()[:120] or None, severity="green",
                             ref_id="prayer:%s" % prayer_id)
        except Exception:
            pass
        return {"ok": True, "id": prayer_id}
    finally:
        _state["release_db"](conn)


@router.patch("/prayers/{prayer_id}/status")
async def update_prayer_status(prayer_id: int, request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Login required")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    new_status = body.get("status", "")
    if new_status not in ("waiting", "answered", None, ""):
        raise HTTPException(status_code=400, detail="Invalid status")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT email, deleted_at FROM prayers WHERE id=%s", (prayer_id,))
            row = cur.fetchone()
            if not row or row[1]:
                raise HTTPException(status_code=404, detail="Prayer not found")
            if row[0] != user["email"]:
                raise HTTPException(status_code=403, detail="Not authorized")
            cur.execute(
                "UPDATE prayers SET status=%s, updated_at=NOW() WHERE id=%s",
                (new_status or None, prayer_id),
            )
            conn.commit()
        return {"ok": True, "status": new_status or None}
    finally:
        _state["release_db"](conn)


@router.post("/prayers/{prayer_id}/amen")
def amen_prayer(prayer_id: int, request: Request) -> dict:
    user = _state["get_session_user"](request)
    email = user.get("email", "") if user else ""
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cid = get_user_church_id(cur, email) if email else None
            if not _visible_prayer(cur, prayer_id, cid):
                raise HTTPException(status_code=404, detail="Prayer not found")
            cur.execute(
                "UPDATE prayers SET amen_count = amen_count + 1 "
                "WHERE id=%s AND deleted_at IS NULL",
                (prayer_id,),
            )
            if not cur.rowcount:
                raise HTTPException(status_code=404, detail="Prayer not found")
            conn.commit()
            cur.execute(
                "SELECT amen_count FROM prayers WHERE id=%s AND deleted_at IS NULL",
                (prayer_id,),
            )
            row = cur.fetchone()
        return {"ok": True, "amen_count": row[0] if row else 0}
    finally:
        _state["release_db"](conn)


@router.put("/prayers/{prayer_id}")
def update_prayer(prayer_id: int, payload: PrayerUpdateRequest, request: Request) -> dict:
    user = _state["get_session_user"](request)
    email = user.get("email", "") if user else ""
    if not email:
        raise HTTPException(status_code=401, detail="Login required")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT email, deleted_at FROM prayers WHERE id=%s", (prayer_id,))
            row = cur.fetchone()
            if not row or row[1]:
                raise HTTPException(status_code=404, detail="Prayer not found")
            if row[0] != email:
                raise HTTPException(status_code=403, detail="Not authorized")
            cur.execute(
                "UPDATE prayers SET content=%s, updated_at=NOW() WHERE id=%s",
                (_state["sanitize_text"](payload.content.strip()), prayer_id),
            )
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


@router.delete("/prayers/{prayer_id}")
def delete_prayer(prayer_id: int, request: Request) -> dict:
    user = _state["get_session_user"](request)
    email = user.get("email", "") if user else ""
    if not email:
        raise HTTPException(status_code=401, detail="Login required")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT email FROM prayers WHERE id=%s AND deleted_at IS NULL", (prayer_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Prayer not found")
            if row[0] != email and not _state["is_admin"](email):
                raise HTTPException(status_code=403, detail="Not authorized")
            cur.execute("UPDATE prayers SET deleted_at=NOW() WHERE id=%s", (prayer_id,))
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


# ── 代祷分享链接 ──────────────────────────────────────────────────────────────
# 发起人为自己的祷告生成稳定分享令牌；任何人无需登录可经 /p/{token} 查看并「同心」。
# share_token 列首次使用时幂等添加（与 push.last_weekly_sent 同模式）。
import secrets

_share_col_ready = False


def _ensure_share_column(cur) -> None:
    global _share_col_ready
    if _share_col_ready:
        return
    cur.execute("ALTER TABLE prayers ADD COLUMN IF NOT EXISTS share_token TEXT")
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_prayers_share_token "
        "ON prayers(share_token) WHERE share_token IS NOT NULL"
    )
    _share_col_ready = True


@router.post("/prayers/{prayer_id}/share")
def share_prayer(prayer_id: int, request: Request) -> dict:
    """生成（或复用）分享令牌 — 仅祷告发起人可调用。"""
    user = _state["get_session_user"](request)
    email = user.get("email", "") if user else ""
    if not email:
        raise HTTPException(status_code=401, detail="Login required")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _ensure_share_column(cur)
            cur.execute(
                "SELECT email, share_token FROM prayers WHERE id=%s AND deleted_at IS NULL",
                (prayer_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Prayer not found")
            if row[0] != email:
                raise HTTPException(status_code=403, detail="Not authorized")
            token = row[1]
            if not token:
                token = secrets.token_urlsafe(12)
                cur.execute(
                    "UPDATE prayers SET share_token=%s WHERE id=%s", (token, prayer_id)
                )
            conn.commit()
        return {"ok": True, "share_token": token}
    finally:
        _state["release_db"](conn)


@router.get("/prayer-share/{share_token}")
def get_shared_prayer(share_token: str) -> dict:
    """公开查看分享的代祷 — 无需登录；匿名祷告不暴露身份。"""
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _ensure_share_column(cur)
            conn.commit()  # DDL 不留在事务里
            cur.execute(
                "SELECT nickname, content, is_anonymous, amen_count, status, created_at "
                "FROM prayers WHERE share_token=%s AND deleted_at IS NULL",
                (share_token,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Prayer not found")
            nickname, content, is_anon, amen, status, created_at = row
        return {
            "nickname": "弟兄姐妹" if is_anon else (nickname or "弟兄姐妹"),
            "content": content,
            "amen_count": amen,
            "status": status,
            "created_at": _state["to_shanghai_iso"](created_at),
        }
    finally:
        _state["release_db"](conn)


@router.post("/prayer-share/{share_token}/amen")
def amen_shared_prayer(share_token: str) -> dict:
    """通过分享链接「同心代祷」— 无需登录。"""
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _ensure_share_column(cur)
            cur.execute(
                "UPDATE prayers SET amen_count = amen_count + 1 "
                "WHERE share_token=%s AND deleted_at IS NULL "
                "RETURNING amen_count",
                (share_token,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Prayer not found")
            conn.commit()
        return {"ok": True, "amen_count": row[0]}
    finally:
        _state["release_db"](conn)
