"""
Prayer wall router.
Covers: /api/prayers (CRUD + amen + status)
"""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["prayer"])
_state: dict[str, Any] = {}


def init_prayer_router(*, get_db, release_db, get_session_user, is_admin, sanitize_text, to_shanghai_iso) -> None:
    _state.update(locals())


class PrayerSubmitRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    is_anonymous: bool = False


class PrayerUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)


def _row_to_prayer(row, viewer_email: str = "") -> dict:
    pid, email, nickname, content, is_anon, amen, created_at, updated_at, deleted_at, status = row
    return {
        "id": pid, "email": email,
        "nickname": nickname or "弟兄姐妹",
        "content": content,
        "is_own": email == viewer_email,
        "amen_count": amen, "status": status,
        "created_at": _state["to_shanghai_iso"](created_at),
        "updated_at": _state["to_shanghai_iso"](updated_at),
        "deleted_at": _state["to_shanghai_iso"](deleted_at),
    }


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
            cur.execute(
                "SELECT id, email, nickname, content, is_anonymous, amen_count, "
                "created_at, updated_at, deleted_at, status "
                "FROM prayers WHERE deleted_at IS NULL ORDER BY updated_at DESC LIMIT %s OFFSET %s",
                (min(limit, 100), offset),
            )
            rows = cur.fetchall()
            cur.execute("SELECT COUNT(*) FROM prayers WHERE deleted_at IS NULL")
            total = cur.fetchone()[0]
        return {
            "ok": True,
            "items": [_row_to_prayer(r, email) for r in rows],
            "total": total,
            "is_admin": _state["is_admin"](email),
        }
    finally:
        _state["release_db"](conn)


@router.post("/prayers")
def post_prayer(payload: PrayerSubmitRequest, request: Request) -> dict:
    user = _state["get_session_user"](request)
    email = user.get("email", "") if user else ""
    nickname = user.get("nickname", "") if user else "guest"
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO prayers (email, nickname, content, is_anonymous, amen_count) "
                "VALUES (%s,%s,%s,%s,0) RETURNING id",
                (email, _state["sanitize_text"](nickname),
                 _state["sanitize_text"](payload.content.strip()), False),
            )
            prayer_id = cur.fetchone()[0]
            conn.commit()
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
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
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
