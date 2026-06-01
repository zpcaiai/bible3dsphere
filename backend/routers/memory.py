"""
Memory-verse router — 背经（SM-2 间隔重复） (/api/memory)

  POST   /api/memory/verses          新增一节背经
  GET    /api/memory/due             今天到期需复习的卡片
  GET    /api/memory/list            全部卡片
  POST   /api/memory/review          复习评分（SM-2 更新到期日）
  DELETE /api/memory/verses/{vid}    删除
用户以 email 标识，日期 Asia/Shanghai。
"""
from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:
    from backend import sm2_engine as sm2
except Exception:  # pragma: no cover
    import sm2_engine as sm2  # type: ignore

router = APIRouter(prefix="/api/memory", tags=["memory"])
_state: Dict[str, Any] = {}


def init_memory_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _row(r) -> dict:
    return {
        "id": r[0], "reference": r[1], "verse_text": r[2],
        "ease": r[3], "interval_days": r[4], "repetitions": r[5],
        "due_date": str(r[6]) if r[6] else "",
    }


_COLS = "id, reference, verse_text, ease, interval_days, repetitions, due_date"


class VerseBody(BaseModel):
    reference: str = Field(min_length=1, max_length=120)
    verse_text: str = Field(min_length=1, max_length=2000)


class ReviewBody(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    grade: int = Field(ge=0, le=3)


@router.post("/verses")
def add_verse(request: Request, body: VerseBody) -> dict:
    user = _require_user(request)
    vid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO memory_verses (id, email, reference, verse_text) "
                "VALUES (%s,%s,%s,%s)",
                (vid, user["email"], body.reference.strip(), body.verse_text.strip()),
            )
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"add failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": vid}


@router.get("/due")
def due(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLS} FROM memory_verses "
                "WHERE email=%s AND due_date <= (NOW() AT TIME ZONE 'Asia/Shanghai')::date "
                "ORDER BY due_date, created_at",
                (user["email"],),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "count": len(rows), "cards": [_row(r) for r in rows]}


@router.get("/list")
def list_verses(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLS} FROM memory_verses WHERE email=%s ORDER BY created_at DESC",
                (user["email"],),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "count": len(rows), "cards": [_row(r) for r in rows]}


@router.post("/review")
def review(request: Request, body: ReviewBody) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ease, interval_days, repetitions FROM memory_verses "
                "WHERE id=%s AND email=%s",
                (body.id, user["email"]),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="card not found")
            nxt = sm2.review(row[0], row[1], row[2], body.grade)
            cur.execute(
                "UPDATE memory_verses SET ease=%s, interval_days=%s, repetitions=%s, "
                "due_date=(NOW() AT TIME ZONE 'Asia/Shanghai')::date + %s, "
                "last_reviewed=NOW() WHERE id=%s AND email=%s",
                (nxt["ease"], nxt["interval_days"], nxt["repetitions"],
                 int(nxt["due_offset_days"]), body.id, user["email"]),
            )
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"review failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, **nxt}


@router.delete("/verses/{vid}")
def delete_verse(vid: str, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM memory_verses WHERE id=%s AND email=%s",
                        (vid, user["email"]))
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True}
