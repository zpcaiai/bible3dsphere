"""
Guardian × Web Push 整合层 — 守护者主动关怀的云推送。

仿 disciple_integration.notify_pending_push 模式：
复用 routers/push.py 的发送器 send_one(sub, payload) -> 'ok'|'expired'|'error'，
由 /api/push/run-due 的 cron 统一调用，无需新增定时任务。

三类关怀（按优先级取一条，每人每日最多 1 条）：
  1. emotion  情绪低谷跟进 — 12~48h 前有强度>=7 的负面情绪事件，次日温柔回访
  2. prayer   祷告守望     — 7 天前的未应允祷告，提醒「守护者仍在守望」
  3. absence  久别问候     — 3 天以上没有任何互动（最多每 3 天一次）

安全设计：
  - 仅 09:00–21:30 (Asia/Shanghai) 发送，夜间静默
  - guardian_profiles.care_push_on 可关；last_care_push 每日去重
  - 推送同时写入 guardian_messages，widget 聊天记录可见同一句话
  - 缺表/未订阅/未配置 VAPID 时自然 0 条，绝不抛错
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict

_SHANGHAI = timezone(timedelta(hours=8))

_NEGATIVE = ("sadness", "anxiety", "shame", "fear", "loneliness", "anger")

_EMOTION_MSGS = {
    "sadness":    "昨天你心里难过。我没有忘记。「耶和华靠近伤心的人。」(诗34:18) 今天感觉如何？",
    "anxiety":    "昨天你提到焦虑。「应当一无挂虑……神所赐出人意外的平安，必保守你们的心怀意念。」(腓4:6-7) 我在这里。",
    "shame":      "昨天那份羞愧的感觉，还压着你吗？「神差他的儿子降世，不是要定世人的罪。」(约3:17) 回来坐一会儿吧。",
    "fear":       "昨天你害怕。「你不要害怕，因为我与你同在。」(赛41:10) 今天我还陪着你。",
    "loneliness": "昨天你说到孤单。「我总不撇下你，也不丢弃你。」(来13:5) 想你了，回来聊聊？",
    "anger":      "昨天那股怒气，今天平息些了吗？「生气却不要犯罪，不可含怒到日落。」(弗4:26) 我在听。",
}

_PRAYER_MSG = "你 7 天前交托的祷告「{title}」，守护者仍在守望。「耶和华啊，我仰望你。」(诗38:15) 要不要更新一下它的进展？"

_ABSENCE_MSGS = [
    "好几天没见了，守护者一直在原地等你。「他必不叫你的脚摇动，保护你的必不打盹。」(诗121:3)",
    "想你了。无论这几天发生了什么，回来坐一会儿吧。「到我这里来……我就使你们得安息。」(太11:28)",
]


def _payload(name: str, body: str) -> Dict[str, str]:
    return {"title": f"🕊️ {name or '守护者'}", "body": body, "url": "/"}


def notify_care_push(get_db, release_db, send_one, max_users: int = 200) -> Dict[str, Any]:
    """run-due cron 入口。返回 {sent, expired, skipped?}。"""
    now = datetime.now(_SHANGHAI)
    hhmm = now.strftime("%H:%M")
    if not ("09:00" <= hhmm <= "21:30"):
        return {"sent": 0, "expired": 0, "skipped": "quiet-hours"}
    today = now.date()

    conn = get_db()
    sent = expired = 0
    try:
        with conn.cursor() as cur:
            # 候选用户：开了关怀推送、今日未推过、且有有效订阅
            try:
                cur.execute(
                    "SELECT p.email, p.name, p.last_care_push, s.last_interaction_at "
                    "FROM guardian_profiles p "
                    "LEFT JOIN guardian_states s ON s.email = p.email "
                    "WHERE COALESCE(p.care_push_on, TRUE) "
                    "  AND (p.last_care_push IS NULL OR p.last_care_push < %s) "
                    "  AND EXISTS (SELECT 1 FROM push_subscriptions ps "
                    "              WHERE ps.email = p.email AND ps.enabled = TRUE) "
                    "LIMIT %s",
                    (today, max_users),
                )
                candidates = cur.fetchall()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                return {"sent": 0, "expired": 0, "skipped": "no-tables"}

            for email, name, last_care, last_seen in candidates:
                body = None
                # 1) 情绪低谷跟进（12~48h 前，强度>=7 的负面情绪）
                cur.execute(
                    "SELECT emotion_type FROM guardian_emotion_events "
                    "WHERE email=%s AND intensity >= 7 AND emotion_type = ANY(%s) "
                    "  AND created_at BETWEEN NOW() - interval '48 hours' "
                    "                     AND NOW() - interval '12 hours' "
                    "ORDER BY created_at DESC LIMIT 1",
                    (email, list(_NEGATIVE)),
                )
                row = cur.fetchone()
                if row:
                    body = _EMOTION_MSGS.get(row[0])
                # 2) 祷告守望（恰好 7~8 天前的 ongoing 祷告）
                if not body:
                    cur.execute(
                        "SELECT title, content FROM guardian_prayer_entries "
                        "WHERE email=%s AND status='ongoing' "
                        "  AND created_at BETWEEN NOW() - interval '8 days' "
                        "                     AND NOW() - interval '7 days' "
                        "ORDER BY created_at DESC LIMIT 1",
                        (email,),
                    )
                    row = cur.fetchone()
                    if row:
                        title = (row[0] or row[1] or "")[:20] or "你的祷告"
                        body = _PRAYER_MSG.format(title=title)
                # 3) 久别问候（>=3 天没互动；最多每 3 天一次）
                if not body and last_seen is not None:
                    gap_ok = last_care is None or (today - last_care).days >= 3
                    seen = last_seen if last_seen.tzinfo else last_seen.replace(tzinfo=timezone.utc)
                    if gap_ok and (datetime.now(timezone.utc) - seen) > timedelta(days=3):
                        body = _ABSENCE_MSGS[today.toordinal() % len(_ABSENCE_MSGS)]
                if not body:
                    continue

                cur.execute(
                    "SELECT id, endpoint, p256dh, auth FROM push_subscriptions "
                    "WHERE email=%s AND enabled=TRUE",
                    (email,),
                )
                delivered = False
                for sub_id, endpoint, p256dh, auth in cur.fetchall():
                    try:
                        res = send_one(
                            {"endpoint": endpoint, "p256dh": p256dh, "auth": auth},
                            _payload(name, body),
                        )
                    except Exception:
                        res = "error"
                    if res == "ok":
                        sent += 1
                        delivered = True
                    elif res == "expired":
                        expired += 1
                        try:
                            cur.execute(
                                "UPDATE push_subscriptions SET enabled=FALSE WHERE id=%s",
                                (sub_id,),
                            )
                        except Exception:
                            pass
                if delivered:
                    cur.execute(
                        "UPDATE guardian_profiles SET last_care_push=%s, updated_at=NOW() "
                        "WHERE email=%s",
                        (today, email),
                    )
                    # 同步写进聊天记录，widget 打开即可看到同一句关怀
                    try:
                        cur.execute(
                            "INSERT INTO guardian_messages (id, email, role, content, mode) "
                            "VALUES (%s,%s,'assistant',%s,'companion')",
                            (uuid.uuid4().hex, email, body),
                        )
                    except Exception:
                        pass
            conn.commit()
    finally:
        release_db(conn)
    return {"sent": sent, "expired": expired}
