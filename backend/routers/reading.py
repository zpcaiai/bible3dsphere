"""
Reading-plan router — 读经计划进度 (/api/reading)

后端只管「报名 + 进度 + 连续天数」；计划内容（经文清单）由前端静态定义。
  POST /api/reading/enroll       报名/切换计划
  GET  /api/reading/status       某计划的进度（completed_keys + streak）
  POST /api/reading/complete     标记某天完成
  POST /api/reading/uncomplete   取消某天
用户以 email 标识，日期 Asia/Shanghai。
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/reading", tags=["reading"])
_state: Dict[str, Any] = {}


def init_reading_router(*, get_db, release_db, get_session_user) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _streak(dates: List[date]) -> int:
    """连续天数：从今天(或最近完成日)往回数不断的天数。"""
    if not dates:
        return 0
    s = set(dates)
    today = max(dates)  # 以最近一次完成为锚（昨天完成今天没背也算延续）
    # 若最近完成不是今天或昨天，连续中断
    from datetime import datetime, timezone
    sh_today = (datetime.now(timezone(timedelta(hours=8)))).date()
    if today < sh_today - timedelta(days=1):
        return 0
    streak, cur = 0, today
    while cur in s:
        streak += 1
        cur -= timedelta(days=1)
    return streak


class EnrollBody(BaseModel):
    plan_id: str = Field(min_length=1, max_length=40)


class DayBody(BaseModel):
    plan_id: str = Field(min_length=1, max_length=40)
    day_key: str = Field(min_length=1, max_length=20)


@router.post("/enroll")
def enroll(request: Request, body: EnrollBody) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO reading_plan_enrollment (email, plan_id) VALUES (%s,%s) "
                "ON CONFLICT (email, plan_id) DO UPDATE SET active=TRUE",
                (user["email"], body.plan_id),
            )
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True}


@router.get("/status")
def status(request: Request, plan_id: str = Query(...)) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT start_date FROM reading_plan_enrollment WHERE email=%s AND plan_id=%s",
                (user["email"], plan_id),
            )
            er = cur.fetchone()
            cur.execute(
                "SELECT day_key, completed_at::date FROM reading_plan_progress "
                "WHERE email=%s AND plan_id=%s",
                (user["email"], plan_id),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    keys = [r[0] for r in rows]
    dates = [r[1] for r in rows]
    return {
        "ok": True,
        "enrolled": er is not None,
        "start_date": str(er[0]) if er else None,
        "completed_keys": keys,
        "completed_count": len(keys),
        "streak": _streak(dates),
    }


@router.post("/complete")
def complete(request: Request, body: DayBody) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            # 确保已报名
            cur.execute(
                "INSERT INTO reading_plan_enrollment (email, plan_id) VALUES (%s,%s) "
                "ON CONFLICT (email, plan_id) DO NOTHING",
                (user["email"], body.plan_id),
            )
            cur.execute(
                "INSERT INTO reading_plan_progress (id, email, plan_id, day_key) "
                "VALUES (%s,%s,%s,%s) ON CONFLICT (email, plan_id, day_key) DO NOTHING",
                (uuid.uuid4().hex, user["email"], body.plan_id, body.day_key),
            )
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True}


@router.post("/uncomplete")
def uncomplete(request: Request, body: DayBody) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM reading_plan_progress WHERE email=%s AND plan_id=%s AND day_key=%s",
                (user["email"], body.plan_id, body.day_key),
            )
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True}
