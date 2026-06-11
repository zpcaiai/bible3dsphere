"""
Push router — Web Push 晨更/晚祷提醒 (/api/push)

  GET  /api/push/vapid-public-key   前端订阅所需的 VAPID 公钥（未配置则 configured=false）
  GET  /api/push/prefs              当前用户的提醒偏好
  POST /api/push/subscribe          保存浏览器订阅 + 偏好
  POST /api/push/prefs              更新提醒时间/开关
  POST /api/push/unsubscribe        退订某端点
  POST /api/push/test               给自己发一条测试推送
  POST /api/push/run-due            (定时任务调用，需 X-Cron-Secret) 发送到点的提醒

优雅降级：未装 pywebpush 或未配置 VAPID 时，所有发送相关接口返回 configured=false，
不影响应用其余部分。提醒时间按 Asia/Shanghai 本地时间。
"""
from __future__ import annotations

import hmac
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

try:
    from backend.core.config import settings as _settings
except Exception:  # pragma: no cover
    try:
        from core.config import settings as _settings
    except Exception:
        _settings = None

router = APIRouter(prefix="/api/push", tags=["push"])

_state: Dict[str, Any] = {}

_SHANGHAI = timezone(timedelta(hours=8))

MORNING_MSGS = [
    {"title": "晨更 · 新的怜悯", "body": "每早晨都是新的。今天，先把这一天交给神。"},
    {"title": "晨更提醒", "body": "安静三分钟，让神的话语先于世界的喧嚣进入你心。"},
]
EVENING_MSGS = [
    {"title": "晚祷 · 与神同回顾", "body": "今天神在哪里？做一次今日省察，把心交还给祂。"},
    {"title": "晚祷提醒", "body": "数算今天的一件恩典，再安然睡去。"},
]


def init_push_router(*, get_db, release_db, get_session_user) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _configured() -> bool:
    if _settings is None:
        return False
    if not (getattr(_settings, "vapid_public_key", "") and getattr(_settings, "vapid_private_key", "")):
        return False
    try:
        import pywebpush  # noqa: F401
        return True
    except Exception:
        return False


def _send_one(sub: Dict[str, str], payload: Dict[str, Any]) -> str:
    """返回 'ok' | 'expired' | 'error'。"""
    try:
        from pywebpush import webpush, WebPushException
    except Exception:
        return "error"
    try:
        webpush(
            subscription_info={
                "endpoint": sub["endpoint"],
                "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
            },
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=_settings.vapid_private_key,
            vapid_claims={"sub": _settings.vapid_subject},
            timeout=10,
        )
        return "ok"
    except WebPushException as exc:  # type: ignore
        code = getattr(getattr(exc, "response", None), "status_code", None)
        return "expired" if code in (404, 410) else "error"
    except Exception:
        return "error"


# ── Models ──────────────────────────────────────────────────────────────────
class SubscribeBody(BaseModel):
    endpoint: str = Field(min_length=1, max_length=2000)
    p256dh: str = Field(min_length=1, max_length=400)
    auth: str = Field(min_length=1, max_length=400)
    morning_on: bool = True
    evening_on: bool = True
    morning_time: str = Field(default="07:00", max_length=5)
    evening_time: str = Field(default="21:30", max_length=5)


class PrefsBody(BaseModel):
    morning_on: bool = True
    evening_on: bool = True
    morning_time: str = Field(default="07:00", max_length=5)
    evening_time: str = Field(default="21:30", max_length=5)


class EndpointBody(BaseModel):
    endpoint: str = Field(min_length=1, max_length=2000)


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("/vapid-public-key")
def vapid_public_key() -> dict:
    if not _configured():
        return {"ok": True, "configured": False, "public_key": ""}
    return {"ok": True, "configured": True, "public_key": _settings.vapid_public_key}


@router.get("/prefs")
def get_prefs(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT enabled, morning_on, evening_on, morning_time, evening_time "
                "FROM push_subscriptions WHERE email=%s ORDER BY updated_at DESC LIMIT 1",
                (user["email"],),
            )
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not row:
        return {"ok": True, "configured": _configured(), "subscribed": False}
    return {"ok": True, "configured": _configured(), "subscribed": bool(row[0]),
            "morning_on": row[1], "evening_on": row[2],
            "morning_time": row[3], "evening_time": row[4]}


@router.post("/subscribe")
def subscribe(request: Request, body: SubscribeBody) -> dict:
    user = _require_user(request)
    email = user["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO push_subscriptions "
                "(id, email, endpoint, p256dh, auth, enabled, morning_on, evening_on, "
                " morning_time, evening_time) "
                "VALUES (%s,%s,%s,%s,%s,TRUE,%s,%s,%s,%s) "
                "ON CONFLICT (email, endpoint) DO UPDATE SET "
                " p256dh=EXCLUDED.p256dh, auth=EXCLUDED.auth, enabled=TRUE, "
                " morning_on=EXCLUDED.morning_on, evening_on=EXCLUDED.evening_on, "
                " morning_time=EXCLUDED.morning_time, evening_time=EXCLUDED.evening_time, "
                " updated_at=NOW()",
                (uuid.uuid4().hex, email, body.endpoint, body.p256dh, body.auth,
                 body.morning_on, body.evening_on, body.morning_time, body.evening_time),
            )
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"subscribe failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "configured": _configured()}


@router.post("/prefs")
def set_prefs(request: Request, body: PrefsBody) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE push_subscriptions SET morning_on=%s, evening_on=%s, "
                "morning_time=%s, evening_time=%s, updated_at=NOW() WHERE email=%s",
                (body.morning_on, body.evening_on, body.morning_time,
                 body.evening_time, user["email"]),
            )
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True}


@router.post("/unsubscribe")
def unsubscribe(request: Request, body: EndpointBody) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE push_subscriptions SET enabled=FALSE, updated_at=NOW() "
                "WHERE email=%s AND endpoint=%s",
                (user["email"], body.endpoint),
            )
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True}


@router.post("/test")
def test_push(request: Request) -> dict:
    user = _require_user(request)
    if not _configured():
        return {"ok": False, "configured": False, "reason": "服务器未配置 VAPID 推送"}
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT endpoint, p256dh, auth FROM push_subscriptions "
                "WHERE email=%s AND enabled=TRUE",
                (user["email"],),
            )
            subs = cur.fetchall()
    finally:
        _state["release_db"](conn)
    sent = 0
    for endpoint, p256dh, auth in subs:
        if _send_one({"endpoint": endpoint, "p256dh": p256dh, "auth": auth},
                     {"title": "🔔 提醒已开启", "body": "你会在设定的晨更/晚祷时间收到温柔的提醒。",
                      "url": "/"}) == "ok":
            sent += 1
    return {"ok": True, "configured": True, "sent": sent}


@router.post("/run-due")
def run_due(request: Request) -> dict:
    """定时任务入口：发送到点的提醒。需 X-Cron-Secret 头匹配 PUSH_CRON_SECRET。"""
    secret = getattr(_settings, "push_cron_secret", "") if _settings else ""
    provided = request.headers.get("X-Cron-Secret", "")
    if not secret or not hmac.compare_digest(provided, secret):
        raise HTTPException(status_code=403, detail="forbidden")
    if not _configured():
        return {"ok": True, "configured": False, "sent": 0}

    now = datetime.now(_SHANGHAI)
    now_hhmm = now.strftime("%H:%M")
    today = now.date()

    conn = _state["get_db"]()
    sent = expired = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, endpoint, p256dh, auth, morning_on, evening_on, "
                " morning_time, evening_time, last_morning_sent, last_evening_sent "
                "FROM push_subscriptions WHERE enabled=TRUE"
            )
            rows = cur.fetchall()
            import random
            for (sid, endpoint, p256dh, auth, m_on, e_on, m_t, e_t,
                 last_m, last_e) in rows:
                sub = {"endpoint": endpoint, "p256dh": p256dh, "auth": auth}
                # 晨更
                if m_on and m_t and now_hhmm >= m_t and last_m != today:
                    res = _send_one(sub, {**random.choice(MORNING_MSGS), "url": "/"})
                    if res == "ok":
                        sent += 1
                        cur.execute("UPDATE push_subscriptions SET last_morning_sent=%s WHERE id=%s",
                                    (today, sid))
                    elif res == "expired":
                        expired += 1
                        cur.execute("UPDATE push_subscriptions SET enabled=FALSE WHERE id=%s", (sid,))
                # 晚祷
                if e_on and e_t and now_hhmm >= e_t and last_e != today:
                    res = _send_one(sub, {**random.choice(EVENING_MSGS), "url": "/"})
                    if res == "ok":
                        sent += 1
                        cur.execute("UPDATE push_subscriptions SET last_evening_sent=%s WHERE id=%s",
                                    (today, sid))
                    elif res == "expired":
                        expired += 1
                        cur.execute("UPDATE push_subscriptions SET enabled=FALSE WHERE id=%s", (sid,))
            conn.commit()
    finally:
        _state["release_db"](conn)
    # 门徒塑造 nudge/里程碑推送（整合层复用同一 cron，无需再注册定时任务）
    disciple_sent = 0
    try:
        from disciple_integration import notify_pending_push
        disciple_sent = notify_pending_push(_state["get_db"], _state["release_db"], _send_one).get("sent", 0)
    except Exception:
        pass
    # 守护者主动关怀推送（情绪跟进/祷告守望/久别问候，同一 cron）
    guardian_sent = 0
    try:
        try:
            from guardian_integration import notify_care_push
        except ImportError:
            from backend.guardian_integration import notify_care_push
        guardian_sent = notify_care_push(_state["get_db"], _state["release_db"], _send_one).get("sent", 0)
    except Exception:
        pass
    # 灵修周报：主日 20:00 后推送一次（统计本周日志/祷告/读经）
    weekly_sent = 0
    try:
        if now.weekday() == 6 and now_hhmm >= "20:00":
            conn2 = _state["get_db"]()
            try:
                with conn2.cursor() as cur:
                    cur.execute("ALTER TABLE push_subscriptions ADD COLUMN IF NOT EXISTS last_weekly_sent DATE")
                    cur.execute(
                        "SELECT id, email, endpoint, p256dh, auth FROM push_subscriptions "
                        "WHERE enabled=TRUE AND email IS NOT NULL "
                        "AND (last_weekly_sent IS NULL OR last_weekly_sent < %s)", (today,))
                    subs = cur.fetchall()
                    for sid, email, endpoint, p256dh, auth in subs:
                        cur.execute("SELECT COUNT(*) FROM devotion_journals WHERE email=%s AND deleted_at IS NULL "
                                    "AND created_at >= now() - interval '7 days'", (email,))
                        nj = cur.fetchone()[0]
                        cur.execute("SELECT COUNT(*) FROM prayers WHERE email=%s AND deleted_at IS NULL "
                                    "AND created_at >= now() - interval '7 days'", (email,))
                        np_ = cur.fetchone()[0]
                        cur.execute("SELECT COUNT(*) FROM prayers WHERE email=%s AND status='answered' "
                                    "AND created_at >= now() - interval '7 days'", (email,))
                        na = cur.fetchone()[0]
                        if nj + np_ == 0:
                            body = "本周暂无灵修记录——新的一周，从明早与主相遇开始？"
                        else:
                            body = f"本周灵修 {nj} 篇 · 祷告 {np_} 条" + (f" · {na} 个蒙应允 🎉" if na else "") + "。「到如今耶和华都帮助我们。」"
                        res = _send_one({"endpoint": endpoint, "p256dh": p256dh, "auth": auth},
                                        {"title": "📒 本周灵修回顾", "body": body, "url": "/"})
                        if res == "ok":
                            weekly_sent += 1
                            cur.execute("UPDATE push_subscriptions SET last_weekly_sent=%s WHERE id=%s", (today, sid))
                        elif res == "expired":
                            cur.execute("UPDATE push_subscriptions SET enabled=FALSE WHERE id=%s", (sid,))
                conn2.commit()
            finally:
                _state["release_db"](conn2)
    except Exception as exc:
        print(f"[push] weekly digest warning: {exc}", flush=True)

    # 聚会日历到点提醒（同一 cron）
    meeting_sent = 0
    try:
        from routers.meetings import notify_due_meetings
        meeting_sent = notify_due_meetings(_state["get_db"], _state["release_db"], _send_one).get("sent", 0)
    except Exception:
        pass
    return {"ok": True, "configured": True, "sent": sent, "expired": expired,
            "disciple_sent": disciple_sent, "guardian_sent": guardian_sent,
            "meeting_sent": meeting_sent, "weekly_sent": weekly_sent}
