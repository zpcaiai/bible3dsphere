#!/usr/bin/env python3
"""
Disciple Worker — 独立异步事件工作者
====================================

把"事件消费 + 通知"从请求路径里解耦出来，作为一个后台守护线程周期运行：

    每 interval 秒：
      1. 扫描所有用户的未处理 domain_events
      2. 逐用户跑 process_user_events（规则 Agent → agent_runs）
      3. notify_pending_push（把 nudge/里程碑经 Web Push 推出）

为什么要独立 worker：
  - assess 里的 inline 消费只覆盖"当前正在反思的用户"；worker 兜住一切来源/一切用户。
  - 通知不再依赖晨更/晚祷那条 push cron 的时点，自己按 interval 推送。

安全：
  - 由 env DISCIPLE_WORKER_ENABLED=1 显式开启（serverless/无持久进程的环境不要开）。
  - 守护线程、整圈 try/except，任何异常只记日志，绝不影响主 web 进程。
  - 也提供 run_once 供 cron / 手动端点调用（不依赖常驻线程）。
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Callable, Dict

try:
    from backend import disciple_integration as di
except Exception:  # pragma: no cover
    import disciple_integration as di  # type: ignore

logger = logging.getLogger("disciple_worker")
_started = False


def _send_one_and_configured():
    """惰性取 Web Push 发送器；未配置/缺依赖返回 (None, False)。"""
    try:
        try:
            from routers.push import _send_one, _configured
        except Exception:
            from backend.routers.push import _send_one, _configured  # type: ignore
        return (_send_one, _configured())
    except Exception:
        return (None, False)


def run_once(get_db: Callable, release_db: Callable, max_users: int = 1000) -> Dict[str, Any]:
    """跑一圈：消费所有未处理事件 + 推送。返回统计。可被 cron/端点直接调用。"""
    users = []
    reactions = 0
    conn = get_db()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT DISTINCT aggregate_id FROM domain_events "
                    "WHERE processed = FALSE LIMIT %s", (max_users,))
                users = [r[0] for r in cur.fetchall()]
            except Exception:
                users = []
        # 逐用户处理，单用户失败不影响其他人（每人独立提交）
        for email in users:
            try:
                with conn.cursor() as cur:
                    reactions += len(di.process_user_events(cur, email))
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
    finally:
        release_db(conn)

    sent = 0
    send_one, configured = _send_one_and_configured()
    if send_one and configured:
        try:
            sent = di.notify_pending_push(get_db, release_db, send_one).get("sent", 0)
        except Exception:
            pass

    stats = {"users": len(users), "reactions": reactions, "notified": sent}
    if users:
        logger.info("[disciple_worker] run_once %s", stats)
    return stats


def start_background_worker(get_db: Callable, release_db: Callable,
                            interval: int = 300) -> bool:
    """启动常驻守护线程（仅当 DISCIPLE_WORKER_ENABLED 为真）。返回是否启动。"""
    global _started
    if _started:
        return False
    flag = os.environ.get("DISCIPLE_WORKER_ENABLED", "").strip().lower()
    if flag not in ("1", "true", "yes", "on"):
        return False
    try:
        interval = int(os.environ.get("DISCIPLE_WORKER_INTERVAL", interval))
    except Exception:
        pass
    _started = True

    def _loop():
        # 启动后稍等，让 web 进程先就绪
        time.sleep(15)
        while True:
            try:
                run_once(get_db, release_db)
            except Exception as exc:
                logger.warning("[disciple_worker] loop error: %s", exc)
            time.sleep(interval)

    t = threading.Thread(target=_loop, daemon=True, name="disciple-worker")
    t.start()
    logger.info("[disciple_worker] background worker started (interval=%ss)", interval)
    return True
