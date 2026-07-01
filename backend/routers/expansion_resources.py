"""Expansion resources router — 推荐书目 + 圣诗目录 (/api/resources)。content-theology-expansion 批次。"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:
    from backend import expansion_content as content
except Exception:  # pragma: no cover
    import expansion_content as content  # type: ignore

router = APIRouter(prefix="/api/resources", tags=["resources"])
_state: Dict[str, Any] = {}


def init_expansion_resources_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _Json(obj):
    try:
        from psycopg2.extras import Json
        return Json(obj)
    except Exception:
        import json as _json
        return _json.dumps(obj)


@router.get("/meta")
def get_meta() -> dict:
    return {"ok": True, **content.meta()}


@router.get("/books")
def books(continent: Optional[str] = Query(default=None), min_priority: int = Query(default=0, ge=0, le=3)) -> dict:
    return {"ok": True, "books": content.list_books(continent, min_priority)}


@router.get("/hymns")
def hymns() -> dict:
    return {"ok": True, "hymns": content.list_hymns()}


class BookmarkBody(BaseModel):
    slug: str = Field(max_length=120)
    kind: str = Field(default="book", max_length=16)  # book | hymn


@router.post("/bookmark")
def bookmark(request: Request, body: BookmarkBody) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO resource_bookmarks (id, email, slug, kind) VALUES (%s,%s,%s,%s) "
                "ON CONFLICT (email, slug) DO NOTHING",
                (uuid.uuid4().hex, user["email"], body.slug[:120], body.kind[:16]),
            )
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"save failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "slug": body.slug}


@router.get("/bookmarks")
def bookmarks(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT slug, kind, created_at FROM resource_bookmarks WHERE email=%s ORDER BY created_at DESC",
                (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    iso = _state["to_shanghai_iso"]
    return {"ok": True, "items": [{"slug": r[0], "kind": r[1], "created_at": iso(r[2])} for r in rows]}
