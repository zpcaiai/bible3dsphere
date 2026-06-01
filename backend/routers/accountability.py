"""Accountability router — 灵修问责（属灵目标 + 打卡） (/api/accountability)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/accountability", tags=["accountability"])
_state: Dict[str, Any] = {}
_SH = timezone(timedelta(hours=8))


def init_accountability_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


class GoalBody(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    detail: str = Field(default="", max_length=1000)
    cadence: str = Field(default="daily", max_length=20)


class CheckinBody(BaseModel):
    goal_id: str = Field(min_length=1, max_length=64)
    status: str = Field(default="done", max_length=20)
    note: str = Field(default="", max_length=1000)


def _streak(dates: List, cadence: str) -> int:
    if not dates:
        return 0
    days = sorted({d for d in dates}, reverse=True)
    today = datetime.now(_SH).date()
    step = 1 if cadence != "weekly" else 7
    if (today - days[0]).days > step:
        return 0
    streak, cur = 0, days[0]
    s = set(days)
    while cur in s:
        streak += 1
        cur = cur - timedelta(days=step)
    return streak


@router.get("/goals")
def goals(request: Request) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, detail, cadence, active, created_at "
                        "FROM accountability_goals WHERE email=%s AND active=TRUE "
                        "ORDER BY created_at", (user["email"],))
            grows = cur.fetchall()
            out = []
            for g in grows:
                cur.execute("SELECT status, created_at::date, created_at FROM accountability_checkins "
                            "WHERE goal_id=%s ORDER BY created_at DESC LIMIT 30", (g[0],))
                cks = cur.fetchall()
                done_dates = [c[1] for c in cks if c[0] == "done"]
                out.append({
                    "id": g[0], "title": g[1], "detail": g[2], "cadence": g[3],
                    "created_at": to_iso(g[5]),
                    "streak": _streak(done_dates, g[3]),
                    "total_checkins": len(cks),
                    "recent": [{"status": c[0], "at": to_iso(c[2])} for c in cks[:7]],
                })
    finally:
        _state["release_db"](conn)
    return {"ok": True, "goals": out}


@router.post("/goals")
def add_goal(request: Request, body: GoalBody) -> dict:
    user = _require_user(request)
    gid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO accountability_goals (id, email, title, detail, cadence) "
                        "VALUES (%s,%s,%s,%s,%s)",
                        (gid, user["email"], body.title.strip(), body.detail.strip(), body.cadence))
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": gid}


@router.post("/checkin")
def checkin(request: Request, body: CheckinBody) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM accountability_goals WHERE id=%s AND email=%s",
                        (body.goal_id, user["email"]))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="goal not found")
            cur.execute("INSERT INTO accountability_checkins (id, goal_id, email, status, note) "
                        "VALUES (%s,%s,%s,%s,%s)",
                        (uuid.uuid4().hex, body.goal_id, user["email"], body.status, body.note.strip()))
            conn.commit()
    except HTTPException:
        raise
    finally:
        _state["release_db"](conn)
    # 回流 formation：忠心守约=成长
    if body.status == "done":
        try:
            from formation_bridge import record_formation
            record_formation(user.get("id"), ["growth"], loop_broken=True,
                             reflection_active=True, emotional_intensity=4.0,
                             decision_category="accountability")
        except Exception:
            pass
    return {"ok": True}


@router.delete("/goals/{gid}")
def delete_goal(gid: str, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE accountability_goals SET active=FALSE WHERE id=%s AND email=%s",
                        (gid, user["email"]))
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True}
