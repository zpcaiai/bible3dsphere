"""麦琴每日读经计划与 08:00 推送执行器。

日程按 ``public/mccheyne.json`` 的 366 个 MM-DD 键压缩为连续书卷段，使用
闰年模板计算索引，因此普通年份和闰年的固定月日都与前端计划一致。
"""
from __future__ import annotations

from bisect import bisect_right
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Callable, Dict, Optional


SHANGHAI = timezone(timedelta(hours=8))
PUSH_TIME = time(8, 0)

SLOT_LABELS = {
    "f1": "家庭读经 ①",
    "f2": "家庭读经 ②",
    "n1": "个人读经 ①",
    "ps": "个人读经 ②",
}

# (闰年模板日序, 书卷, 起始章)。数据与 bible3dsphereWeb/public/mccheyne.json 同源。
_SEGMENTS = {
    "f1": (
        (0, "创世记", 1), (50, "出埃及记", 1), (90, "利未记", 1),
        (117, "民数记", 1), (153, "申命记", 1), (187, "约书亚记", 1),
        (211, "士师记", 1), (232, "路得记", 1), (236, "撒母耳记上", 1),
        (267, "撒母耳记下", 1), (291, "列王纪上", 1),
        (313, "列王纪下", 1), (338, "创世记", 1),
    ),
    "f2": (
        (0, "历代志上", 1), (29, "历代志下", 1), (65, "以斯拉记", 1),
        (75, "尼希米记", 1), (88, "以斯帖记", 1), (98, "约伯记", 1),
        (140, "箴言", 1), (171, "传道书", 1), (183, "雅歌", 1),
        (191, "以赛亚书", 1), (257, "耶利米书", 1),
        (309, "耶利米哀歌", 1), (314, "以西结书", 1), (362, "但以理书", 1),
    ),
    "n1": (
        (0, "马太福音", 1), (28, "马可福音", 1), (44, "路加福音", 1),
        (68, "约翰福音", 1), (89, "使徒行传", 1), (117, "罗马书", 1),
        (133, "哥林多前书", 1), (149, "哥林多后书", 1),
        (162, "加拉太书", 1), (168, "以弗所书", 1), (174, "腓立比书", 1),
        (178, "歌罗西书", 1), (182, "帖撒罗尼迦前书", 1),
        (187, "帖撒罗尼迦后书", 1), (190, "提摩太前书", 1),
        (196, "提摩太后书", 1), (200, "提多书", 1), (203, "腓利门书", 1),
        (204, "希伯来书", 1), (217, "雅各书", 1), (222, "彼得前书", 1),
        (227, "彼得后书", 1), (230, "约翰一书", 1),
        (235, "约翰二书", 1), (236, "约翰三书", 1), (237, "犹大书", 1),
        (238, "启示录", 1), (260, "马太福音", 1), (288, "马可福音", 1),
        (304, "路加福音", 1), (328, "约翰福音", 1), (349, "使徒行传", 1),
    ),
    "ps": ((0, "诗篇", 1), (150, "诗篇", 1), (300, "诗篇", 1)),
}


def _template_day_index(day: date) -> int:
    template = date(2000, day.month, day.day)
    return (template - date(2000, 1, 1)).days


def readings_for(day: date) -> Dict[str, str]:
    """返回指定月日的四处麦琴读经，经文格式与前端保持一致。"""
    day_index = _template_day_index(day)
    readings: Dict[str, str] = {}
    for slot, segments in _SEGMENTS.items():
        starts = [segment[0] for segment in segments]
        segment_index = bisect_right(starts, day_index) - 1
        start_index, book, start_chapter = segments[segment_index]
        readings[slot] = f"{book}{start_chapter + day_index - start_index}"
    return readings


def notification_for(day: date) -> Dict[str, Any]:
    """生成适合 Web Push/FCM 大小限制的今日计划与查经入口。"""
    readings = readings_for(day)
    refs = [readings[slot] for slot in SLOT_LABELS]
    return {
        "title": f"📖 麦琴读经 · {day.month}月{day.day}日",
        "body": "今日：" + " · ".join(refs) + "。查经：观察神的作为、福音关联与今日顺服；点开查看逐章详解。",
        "url": "/?panel=mccheyne",
        "tag": f"mccheyne-{day.isoformat()}",
        "plan": "mccheyne",
        "date": day.isoformat(),
        "readings": readings,
    }


def _is_due(now: datetime) -> bool:
    local_now = now.astimezone(SHANGHAI)
    return local_now.time().replace(tzinfo=None) >= PUSH_TIME


def deliver_due(
    now: datetime,
    *,
    get_db: Callable[[], Any],
    release_db: Callable[[Any], None],
    send_web: Callable[[Dict[str, str], Dict[str, Any]], str],
    web_configured: bool,
    fcm_sender: Optional[Any] = None,
) -> Dict[str, Any]:
    """向所有已授权设备发送今日计划；按订阅/设备每天幂等。

    未到 08:00、推送通道未配置或发送失败时不会写入已发送日期，下一轮 cron
    可安全重试。失效端点/token 会被停用，避免后续重复失败。
    """
    local_now = now.astimezone(SHANGHAI)
    today = local_now.date()
    result: Dict[str, Any] = {
        "due": _is_due(local_now),
        "day": today.isoformat(),
        "web_sent": 0,
        "fcm_sent": 0,
        "expired": 0,
        "errors": 0,
    }
    if not result["due"]:
        return result

    payload = notification_for(today)

    if web_configured:
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, endpoint, p256dh, auth FROM push_subscriptions "
                    "WHERE enabled=TRUE AND COALESCE(mccheyne_on, TRUE)=TRUE "
                    "AND (last_mccheyne_sent IS NULL OR last_mccheyne_sent < %s)",
                    (today,),
                )
                subscriptions = cur.fetchall()
                for sid, endpoint, p256dh, auth in subscriptions:
                    status = send_web(
                        {"endpoint": endpoint, "p256dh": p256dh, "auth": auth},
                        payload,
                    )
                    if status == "ok":
                        result["web_sent"] += 1
                        cur.execute(
                            "UPDATE push_subscriptions SET last_mccheyne_sent=%s WHERE id=%s",
                            (today, sid),
                        )
                    elif status == "expired":
                        result["expired"] += 1
                        cur.execute("UPDATE push_subscriptions SET enabled=FALSE WHERE id=%s", (sid,))
                    else:
                        result["errors"] += 1
                conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            release_db(conn)

    fcm_configured = False
    try:
        fcm_configured = bool(fcm_sender is not None and fcm_sender.is_configured())
    except Exception:
        fcm_configured = False
    if fcm_configured:
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, token FROM fcm_device_tokens "
                    "WHERE revoked_at IS NULL AND COALESCE(mccheyne_on, TRUE)=TRUE "
                    "AND (last_mccheyne_sent IS NULL OR last_mccheyne_sent < %s)",
                    (today,),
                )
                devices = cur.fetchall()
                fcm_data = {"url": payload["url"], "plan": "mccheyne", "date": today.isoformat()}
                for device_id, token in devices:
                    status = fcm_sender.send_to_token(token, payload["title"], payload["body"], fcm_data)
                    if status == "ok":
                        result["fcm_sent"] += 1
                        cur.execute(
                            "UPDATE fcm_device_tokens SET last_mccheyne_sent=%s WHERE id=%s",
                            (today, device_id),
                        )
                    elif status == "unregistered":
                        result["expired"] += 1
                        cur.execute("UPDATE fcm_device_tokens SET revoked_at=NOW() WHERE id=%s", (device_id,))
                    else:
                        result["errors"] += 1
                conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            release_db(conn)

    return result
