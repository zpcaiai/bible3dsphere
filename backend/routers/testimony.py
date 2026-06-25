"""
Testimony wall router — 见证墙（生命改变的故事） (/api/testimonies)

引导式见证：信主前 / 如何遇见主 / 生命改变。
教会隔离：默认仅同教会可见；is_public=True 时跨教会公开。

  GET    /api/testimonies              列表（公开 OR 同教会）
  POST   /api/testimonies              发布见证
  POST   /api/testimonies/{tid}/amen   阿们（感恩回应）
  DELETE /api/testimonies/{tid}        删除（软删除，本人或管理员）
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["testimony"])
_state: dict[str, Any] = {}

try:
    from core.deps import get_user_church_id
except ImportError:
    try:
        from backend.core.deps import get_user_church_id
    except ImportError:
        def get_user_church_id(cur, email, *, use_cache=True):  # type: ignore[misc]
            return None


def init_testimony_router(*, get_db, release_db, get_session_user, is_admin,
                          sanitize_text, to_shanghai_iso) -> None:
    _state.update(locals())


class TestimonySubmitRequest(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    before_story: str = Field(default="", max_length=2000)
    how_story: str = Field(min_length=1, max_length=2000)
    after_story: str = Field(min_length=1, max_length=2000)
    is_anonymous: bool = False
    is_public: bool = False


_COLS = ("id, email, nickname, title, before_story, how_story, after_story, "
         "is_anonymous, is_public, amen_count, church_id, created_at, updated_at")


def _row_to_testimony(row, viewer_email: str = "") -> dict:
    (tid, email, nickname, title, before_story, how_story, after_story,
     is_anon, is_public, amen, _cid, created_at, updated_at) = row
    hide = is_anon and email != viewer_email
    return {
        "id": tid,
        "email": "" if hide else email,
        "nickname": "弟兄姐妹" if hide else (nickname or "弟兄姐妹"),
        "title": title,
        "before_story": before_story,
        "how_story": how_story,
        "after_story": after_story,
        "is_anonymous": is_anon,
        "is_public": is_public,
        "is_own": email == viewer_email,
        "amen_count": amen,
        "created_at": _state["to_shanghai_iso"](created_at),
        "updated_at": _state["to_shanghai_iso"](updated_at),
    }


@router.get("/testimonies")
def get_testimonies(
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
                f"SELECT {_COLS} FROM testimonies WHERE deleted_at IS NULL "
                "AND (is_public = TRUE OR email = %s "
                "OR (church_id IS NOT NULL AND church_id = %s)) "
                "ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (email, effective_cid, min(limit, 100), offset),
            )
            rows = cur.fetchall()
            cur.execute(
                "SELECT COUNT(*) FROM testimonies WHERE deleted_at IS NULL "
                "AND (is_public = TRUE OR email = %s "
                "OR (church_id IS NOT NULL AND church_id = %s))",
                (email, effective_cid),
            )
            total = cur.fetchone()[0]
        return {
            "ok": True,
            "items": [_row_to_testimony(r, email) for r in rows],
            "total": total,
        }
    finally:
        _state["release_db"](conn)


@router.post("/testimonies")
def post_testimony(payload: TestimonySubmitRequest, request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="请先登录")
    email = user["email"]
    nickname = user.get("nickname", "") or "弟兄姐妹"
    san = _state["sanitize_text"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cid = get_user_church_id(cur, email)
            cur.execute(
                "INSERT INTO testimonies (email, nickname, title, before_story, "
                "how_story, after_story, is_anonymous, is_public, church_id) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (email, san(nickname), san(payload.title.strip()),
                 san(payload.before_story.strip()), san(payload.how_story.strip()),
                 san(payload.after_story.strip()),
                 payload.is_anonymous, payload.is_public, cid),
            )
            tid = cur.fetchone()[0]
            conn.commit()
        try:
            import formation_events as _fe
            _fe.record_event(email, "testimony", "testimony", title="发布见证",
                             summary=(payload.title or "").strip()[:120] or None, severity="green",
                             ref_id="testimony:%s" % tid)
        except Exception:
            pass
        return {"ok": True, "id": tid}
    finally:
        _state["release_db"](conn)


@router.post("/testimonies/{tid}/amen")
def amen_testimony(tid: int, request: Request) -> dict:
    user = _state["get_session_user"](request)
    email = user.get("email", "") if user else ""
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cid = get_user_church_id(cur, email) if email else None
            effective_cid = cid if cid is not None else -1
            cur.execute(
                "UPDATE testimonies SET amen_count = amen_count + 1 "
                "WHERE id=%s AND deleted_at IS NULL "
                "AND (is_public = TRUE OR email = %s "
                "OR (church_id IS NOT NULL AND church_id = %s))",
                (tid, email, effective_cid),
            )
            if not cur.rowcount:
                raise HTTPException(status_code=404, detail="见证不存在或不可见")
            conn.commit()
            cur.execute("SELECT amen_count FROM testimonies WHERE id=%s", (tid,))
            row = cur.fetchone()
        return {"ok": True, "amen_count": row[0] if row else 0}
    finally:
        _state["release_db"](conn)


@router.delete("/testimonies/{tid}")
def delete_testimony(tid: int, request: Request) -> dict:
    user = _state["get_session_user"](request)
    email = user.get("email", "") if user else ""
    if not email:
        raise HTTPException(status_code=401, detail="请先登录")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT email FROM testimonies WHERE id=%s AND deleted_at IS NULL", (tid,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="见证不存在")
            if row[0] != email and not _state["is_admin"](email):
                raise HTTPException(status_code=403, detail="无权删除")
            cur.execute("UPDATE testimonies SET deleted_at=NOW() WHERE id=%s", (tid,))
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)
