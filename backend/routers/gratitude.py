"""Gratitude router — 感恩日记 / 数算恩典 (/api/gratitude)."""
from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/gratitude", tags=["gratitude"])
_state: Dict[str, Any] = {}


def init_gratitude_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


class AddBody(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


@router.post("")
def add(request: Request, body: AddBody) -> dict:
    user = _require_user(request)
    gid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO gratitude_entries (id, email, content) VALUES (%s,%s,%s)",
                        (gid, user["email"], body.content.strip()))
            conn.commit()
    finally:
        _state["release_db"](conn)
    # 回流 formation：感恩 = 成长/灵性，loop_broken
    try:
        from formation_bridge import record_formation
        record_formation(user.get("id"), ["growth", "spiritual"], loop_broken=True,
                         reflection_active=True, emotional_intensity=4.0,
                         decision_category="gratitude")
    except Exception:
        pass
    return {"ok": True, "id": gid}


@router.get("/list")
def list_entries(request: Request, limit: int = Query(default=60, ge=1, le=200)) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, content, created_at FROM gratitude_entries "
                        "WHERE email=%s ORDER BY created_at DESC LIMIT %s",
                        (user["email"], limit))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "count": len(rows),
            "entries": [{"id": r[0], "content": r[1], "created_at": to_iso(r[2])} for r in rows]}


@router.delete("/{gid}")
def delete(gid: str, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM gratitude_entries WHERE id=%s AND email=%s",
                        (gid, user["email"]))
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True}
