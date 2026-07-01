"""Creed & Catechism router — 信经与教理问答进度 (/api/creed-catechism).

Per-email completion state for catechism items. Content itself is served by the
client seed; this layer persists which items a user has completed + their path.
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/creed-catechism", tags=["creed-catechism"])
_state: Dict[str, Any] = {}


def init_creed_catechism_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    fn = _state.get("get_session_user")
    user = fn(request) if fn else None
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _iso(dt):
    fn = _state.get("to_shanghai_iso")
    try:
        return fn(dt) if fn else (dt.isoformat() if hasattr(dt, "isoformat") else dt)
    except Exception:
        return str(dt)


class CompleteIn(BaseModel):
    item_key: str = Field(min_length=1, max_length=80)
    pathway: str = Field(default="", max_length=40)


class UncompleteIn(BaseModel):
    item_key: str = Field(min_length=1, max_length=80)


@router.get("/state")
def state(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT item_key, pathway, completed_at FROM creed_catechism_progress "
                "WHERE email=%s ORDER BY completed_at DESC",
                (user["email"],),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    completed = [r[0] for r in rows]
    pathway = rows[0][1] if rows else ""
    items = [{"item_key": r[0], "pathway": r[1], "completed_at": _iso(r[2])} for r in rows]
    return {"ok": True, "completed": completed, "pathway": pathway, "items": items}


@router.post("/complete")
def complete(request: Request, body: CompleteIn) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO creed_catechism_progress (email, item_key, pathway) VALUES (%s,%s,%s) "
                "ON CONFLICT (email, item_key) DO UPDATE SET pathway=EXCLUDED.pathway, "
                "completed_at=CURRENT_TIMESTAMP",
                (user["email"], body.item_key, body.pathway),
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
    return {"ok": True, "item_key": body.item_key}


@router.post("/uncomplete")
def uncomplete(request: Request, body: UncompleteIn) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM creed_catechism_progress WHERE email=%s AND item_key=%s",
                (user["email"], body.item_key),
            )
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"delete failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "item_key": body.item_key}
