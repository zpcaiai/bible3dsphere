"""
聚会日历 —— 语音群的例行/单次聚会排期 + Web Push 到点提醒。

  GET    /api/meetings?group_id=        群的聚会列表（成员可见）
  POST   /api/meetings                  创建（成员）：{group_id,title,weekday|once_date,time_hhmm,remind_minutes}
  DELETE /api/meetings/{mid}            删除（创建者或群主）
  GET    /api/meetings/upcoming         我所有群里最近的聚会（首页/群列表横幅用）

提醒：push.py 的 run_due cron 调用 notify_due_meetings()——
到点前 remind_minutes 分钟内，向群成员的推送订阅发一条提醒（每天最多一次）。
weekday: 0=周一 … 6=周日（Asia/Shanghai）；once_date 设置则为一次性聚会。
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone, date
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter(prefix="/api/meetings", tags=["meetings"])
_state: dict = {}
_SH = timezone(timedelta(hours=8))
WEEK_ZH = ["周一", "周二", "周三", "周四", "周五", "周六", "主日"]

_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS group_meetings (
  id SERIAL PRIMARY KEY,
  group_id VARCHAR(64) NOT NULL,
  title TEXT NOT NULL DEFAULT '',
  weekday SMALLINT,
  once_date DATE,
  time_hhmm VARCHAR(5) NOT NULL,
  remind_minutes SMALLINT NOT NULL DEFAULT 15,
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  last_reminded_on DATE
);
-- 就地迁移：早期版本误建为 INTEGER（voice_groups.id 实为 VARCHAR(64)），统一为 VARCHAR
ALTER TABLE group_meetings ALTER COLUMN group_id TYPE VARCHAR(64) USING group_id::varchar;
CREATE INDEX IF NOT EXISTS idx_group_meetings_group ON group_meetings(group_id);
"""


def init_meetings_router(*, get_db, release_db, get_session_user) -> None:
    _state.update(get_db=get_db, release_db=release_db, get_session_user=get_session_user)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(_TABLE_SQL)
        conn.commit()
    except Exception as exc:  # pragma: no cover
        print(f"[meetings] ensure_tables warning: {exc}", flush=True)
    finally:
        release_db(conn)


def _user(request: Request) -> str:
    user = _state["get_session_user"](request)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user["email"]


def _is_member(cur, gid: str, email: str) -> bool:
    cur.execute("SELECT 1 FROM voice_group_members WHERE group_id=%s AND email=%s", (gid, email))
    return cur.fetchone() is not None


def _next_occurrence(weekday: Optional[int], once_date: Optional[date], hhmm: str,
                     now: Optional[datetime] = None) -> Optional[datetime]:
    """计算下一次聚会时间（上海时区）；一次性聚会已过期返回 None。"""
    now = now or datetime.now(_SH)
    try:
        h, m = int(hhmm[:2]), int(hhmm[3:5])
    except Exception:
        return None
    if once_date is not None:
        dt = datetime(once_date.year, once_date.month, once_date.day, h, m, tzinfo=_SH)
        return dt if dt >= now - timedelta(hours=2) else None
    if weekday is None:
        return None
    days_ahead = (int(weekday) - now.weekday()) % 7
    dt = (now + timedelta(days=days_ahead)).replace(hour=h, minute=m, second=0, microsecond=0)
    if dt < now:
        dt += timedelta(days=7)
    return dt


def _dto(row) -> dict[str, Any]:
    mid, gid, title, weekday, once_date, hhmm, remind, created_by, gname = row
    nxt = _next_occurrence(weekday, once_date, hhmm)
    when_label = (f"{WEEK_ZH[int(weekday)]} {hhmm}" if weekday is not None
                  else f"{once_date.isoformat()} {hhmm}" if once_date else hhmm)
    return {
        "id": mid, "groupId": gid, "groupName": gname, "title": title,
        "weekday": weekday, "onceDate": once_date.isoformat() if once_date else None,
        "time": hhmm, "remindMinutes": remind, "createdBy": created_by,
        "whenLabel": when_label,
        "nextAt": nxt.isoformat() if nxt else None,
    }


@router.get("")
def list_meetings(request: Request, group_id: str = Query(..., min_length=1, max_length=64)) -> dict[str, Any]:
    email = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if not _is_member(cur, group_id, email):
                raise HTTPException(status_code=403, detail="非群成员")
            cur.execute(
                "SELECT m.id, m.group_id, m.title, m.weekday, m.once_date, m.time_hhmm, "
                " m.remind_minutes, m.created_by, g.name "
                "FROM group_meetings m JOIN voice_groups g ON g.id=m.group_id "
                "WHERE m.group_id=%s ORDER BY m.id", (group_id,))
            return {"success": True, "data": [_dto(r) for r in cur.fetchall()]}
    finally:
        _state["release_db"](conn)


@router.post("")
async def create_meeting(request: Request) -> dict[str, Any]:
    email = _user(request)
    body = await request.json()
    gid = str(body.get("group_id") or "").strip()[:64]
    if not gid:
        raise HTTPException(status_code=400, detail="缺少 group_id")
    title = re.sub(r"[\x00-\x1f<>]", "", str(body.get("title") or "聚会"))[:60]
    hhmm = str(body.get("time_hhmm") or "")
    if not re.fullmatch(r"\d{2}:\d{2}", hhmm):
        raise HTTPException(status_code=400, detail="时间格式应为 HH:MM")
    weekday = body.get("weekday")
    weekday = int(weekday) if weekday is not None and str(weekday) != "" else None
    if weekday is not None and not (0 <= weekday <= 6):
        raise HTTPException(status_code=400, detail="weekday 0-6")
    once_date = None
    if body.get("once_date"):
        try:
            once_date = date.fromisoformat(str(body["once_date"]))
        except Exception:
            raise HTTPException(status_code=400, detail="once_date 格式 YYYY-MM-DD")
    if weekday is None and once_date is None:
        raise HTTPException(status_code=400, detail="需指定每周几或具体日期")
    remind = max(0, min(120, int(body.get("remind_minutes") or 15)))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if not _is_member(cur, gid, email):
                raise HTTPException(status_code=403, detail="非群成员")
            cur.execute("SELECT COUNT(*) FROM group_meetings WHERE group_id=%s", (gid,))
            if cur.fetchone()[0] >= 10:
                raise HTTPException(status_code=400, detail="每群最多 10 个排期")
            cur.execute(
                "INSERT INTO group_meetings (group_id,title,weekday,once_date,time_hhmm,remind_minutes,created_by) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (gid, title, weekday, once_date, hhmm, remind, email))
            mid = cur.fetchone()[0]
        conn.commit()
        return {"success": True, "data": {"id": mid}}
    finally:
        _state["release_db"](conn)


@router.delete("/{mid}")
def delete_meeting(request: Request, mid: int) -> dict[str, Any]:
    email = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT m.created_by, g.owner FROM group_meetings m "
                "JOIN voice_groups g ON g.id=m.group_id WHERE m.id=%s", (mid,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="不存在")
            if email not in (row[0], row[1]):
                raise HTTPException(status_code=403, detail="仅创建者或群主可删除")
            cur.execute("DELETE FROM group_meetings WHERE id=%s", (mid,))
        conn.commit()
        return {"success": True}
    finally:
        _state["release_db"](conn)


@router.get("/upcoming")
def upcoming(request: Request) -> dict[str, Any]:
    email = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT m.id, m.group_id, m.title, m.weekday, m.once_date, m.time_hhmm, "
                " m.remind_minutes, m.created_by, g.name "
                "FROM group_meetings m JOIN voice_groups g ON g.id=m.group_id "
                "JOIN voice_group_members mem ON mem.group_id=m.group_id "
                "WHERE mem.email=%s", (email,))
            items = [_dto(r) for r in cur.fetchall()]
        items = [x for x in items if x["nextAt"]]
        items.sort(key=lambda x: x["nextAt"])
        return {"success": True, "data": items[:10]}
    finally:
        _state["release_db"](conn)


# ── 推送提醒：由 push.run_due cron 调用（与门徒塑造/守护者同一扩展点）──
def notify_due_meetings(get_db, release_db, send_one) -> dict[str, int]:
    now = datetime.now(_SH)
    today = now.date()
    sent = 0
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT m.id, m.group_id, m.title, m.weekday, m.once_date, m.time_hhmm, "
                " m.remind_minutes, g.name "
                "FROM group_meetings m JOIN voice_groups g ON g.id=m.group_id "
                "WHERE m.last_reminded_on IS DISTINCT FROM %s", (today,))
            for mid, gid, title, weekday, once_date, hhmm, remind, gname in cur.fetchall():
                nxt = _next_occurrence(weekday, once_date, hhmm, now)
                if not nxt or nxt.date() != today:
                    continue
                if not (timedelta(0) <= nxt - now <= timedelta(minutes=remind or 15)):
                    continue
                cur.execute(
                    "SELECT p.endpoint, p.p256dh, p.auth FROM push_subscriptions p "
                    "JOIN voice_group_members mem ON lower(mem.email)=lower(p.email) "
                    "WHERE mem.group_id=%s AND p.enabled=TRUE", (gid,))
                payload = {
                    "title": f"📅 {gname}", "body": f"{title} {hhmm} 即将开始，点按进入语音房",
                    "url": "/?panel=voice",
                }
                for endpoint, p256dh, auth in cur.fetchall():
                    if send_one({"endpoint": endpoint, "p256dh": p256dh, "auth": auth}, payload) == "ok":
                        sent += 1
                cur.execute("UPDATE group_meetings SET last_reminded_on=%s WHERE id=%s", (today, mid))
        conn.commit()
    except Exception as exc:  # pragma: no cover
        print(f"[meetings] notify warning: {exc}", flush=True)
    finally:
        release_db(conn)
    return {"sent": sent}
