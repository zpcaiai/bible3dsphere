"""Sacrament & Church-Calendar router — 圣礼与教会年历 (/api/sacrament-calendar).

Server-authoritative liturgical season (Western calendar, Easter via computus).
"""
from __future__ import annotations

import json
import uuid
from datetime import date, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/sacrament-calendar", tags=["sacrament-calendar"])
_state: Dict[str, Any] = {}

SEASON_META = {
    "advent": ("将临期", "等候君王来临"),
    "christmas": ("圣诞期", "道成肉身住在我们中间"),
    "epiphany": ("显现期", "基督向万民显明"),
    "lent": ("大斋期", "悔改、简朴、跟随十架道路"),
    "holy_week": ("受难周", "基督为罪人舍己"),
    "easter": ("复活期", "死亡没有最后一句话"),
    "pentecost": ("五旬节", "圣灵赐下，教会被差遣"),
    "ordinary_time": ("常年期", "在日常中忠心跟随基督"),
}


def init_sacrament_calendar_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    fn = _state.get("get_session_user")
    user = fn(request) if fn else None
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _Json(obj):
    try:
        from psycopg2.extras import Json
        return Json(obj)
    except Exception:
        return json.dumps(obj, ensure_ascii=False)


def _load(v, default):
    if v is None:
        return default
    if isinstance(v, (dict, list)):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return default
    return v


def _iso(dt):
    fn = _state.get("to_shanghai_iso")
    try:
        return fn(dt) if fn else (dt.isoformat() if hasattr(dt, "isoformat") else dt)
    except Exception:
        return str(dt)


def _easter(year: int) -> date:
    """Anonymous Gregorian computus."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    ll = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ll) // 451
    month = (h + ll - 7 * m + 114) // 31
    day = ((h + ll - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _advent_sunday(year: int) -> date:
    dec24 = date(year, 12, 24)
    sunday_on_or_before = dec24 - timedelta(days=(dec24.weekday() + 1) % 7)
    return sunday_on_or_before - timedelta(weeks=3)


def current_season_key(dt: Optional[date] = None) -> str:
    d = dt or date.today()
    y = d.year
    easter = _easter(y)
    ash_wed = easter - timedelta(days=46)
    palm = easter - timedelta(days=7)
    pentecost = easter + timedelta(days=49)
    advent = _advent_sunday(y)

    if date(y, 1, 1) <= d <= date(y, 1, 5):
        return "christmas"
    if date(y, 1, 6) <= d < ash_wed:
        return "epiphany"
    if ash_wed <= d < palm:
        return "lent"
    if palm <= d < easter:
        return "holy_week"
    if easter <= d < pentecost:
        return "easter"
    if pentecost <= d <= pentecost + timedelta(days=6):
        return "pentecost"
    if advent <= d <= date(y, 12, 24):
        return "advent"
    if date(y, 12, 25) <= d <= date(y, 12, 31):
        return "christmas"
    return "ordinary_time"


def _season_payload(key: str) -> dict:
    zh, theme = SEASON_META.get(key, SEASON_META["ordinary_time"])
    return {"key": key, "displayNameZh": zh, "gospelTheme": theme}


class LordDayIn(BaseModel):
    season_key: str = Field(default="", max_length=40)
    prep: Dict[str, Any] = Field(default_factory=dict)


@router.get("/current")
def current(request: Request) -> dict:
    key = current_season_key()
    return {"ok": True, "date": date.today().isoformat(), "season": _season_payload(key)}


@router.post("/lord-day")
def save_lord_day(request: Request, body: LordDayIn) -> dict:
    user = _require_user(request)
    season = body.season_key or current_season_key()
    rid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sacrament_lord_day (id, email, season_key, prep) VALUES (%s,%s,%s,%s)",
                (rid, user["email"], season, _Json(body.prep)),
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
    return {"ok": True, "id": rid, "season_key": season}


@router.get("/lord-day/history")
def lord_day_history(request: Request, limit: int = Query(default=20, ge=1, le=100)) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT season_key, prep, created_at FROM sacrament_lord_day "
                "WHERE email=%s ORDER BY created_at DESC LIMIT %s",
                (user["email"], limit),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = [{"season_key": r[0], "prep": _load(r[1], {}), "created_at": _iso(r[2])} for r in rows]
    return {"ok": True, "items": items}
