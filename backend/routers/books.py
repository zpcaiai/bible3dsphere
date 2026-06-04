"""Books router — 属灵书籍 评分/想读/已读 (/api/books)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/books", tags=["books"])
_state: Dict[str, Any] = {}


def init_books_router(*, get_db, release_db, get_session_user) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


class MarkBody(BaseModel):
    book_id: str = Field(min_length=1, max_length=64)
    status: str = ""          # 'want' | 'read' | '' (清除)
    rating: int = Field(default=0, ge=0, le=5)  # 0 = 清除/未评分


@router.post("/mark")
def set_mark(request: Request, body: MarkBody) -> dict:
    """整体 upsert 当前用户对一本书的标记（status+rating 都按提交值落库）。"""
    user = _require_user(request)
    if body.status not in ("", "want", "read"):
        raise HTTPException(status_code=400, detail="status 必须是 want / read / 空")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO book_marks (email, book_id, status, rating, updated_at)
                VALUES (%s, %s, NULLIF(%s,''), NULLIF(%s,0), now())
                ON CONFLICT (email, book_id)
                DO UPDATE SET status = NULLIF(%s,''), rating = NULLIF(%s,0), updated_at = now()
                """,
                (user["email"], body.book_id, body.status, body.rating,
                 body.status, body.rating),
            )
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "book_id": body.book_id,
            "status": body.status or None, "rating": body.rating or None}


@router.get("/marks")
def my_marks(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT book_id, status, rating FROM book_marks WHERE email=%s",
                        (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"marks": {r[0]: {"status": r[1], "rating": r[2]} for r in rows}}


@router.get("/stats")
def stats() -> dict:
    """公开聚合：每本书的平均分/评分人数/想读数/已读数。"""
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT book_id,
                       COUNT(*) FILTER (WHERE status = 'want')          AS want_cnt,
                       COUNT(*) FILTER (WHERE status = 'read')          AS read_cnt,
                       ROUND(AVG(rating)::numeric, 1)                   AS avg_rating,
                       COUNT(rating)                                    AS rating_count
                FROM book_marks
                GROUP BY book_id
                """
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"stats": {r[0]: {"want": r[1], "read_cnt": r[2],
                             "avg_rating": float(r[3]) if r[3] is not None else None,
                             "rating_count": r[4]} for r in rows}}
