"""麦琴日程与每日 08:00 Web Push/FCM 发送器的无数据库测试。"""
from __future__ import annotations

from datetime import date, datetime

import pytest

from mccheyne_push import SHANGHAI, deliver_due, notification_for, readings_for


pytestmark = pytest.mark.no_db


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2026, 1, 1), {"f1": "创世记1", "f2": "历代志上1", "n1": "马太福音1", "ps": "诗篇1"}),
        (date(2024, 2, 29), {"f1": "出埃及记10", "f2": "历代志下31", "n1": "路加福音16", "ps": "诗篇60"}),
        (date(2026, 3, 1), {"f1": "出埃及记11", "f2": "历代志下32", "n1": "路加福音17", "ps": "诗篇61"}),
        (date(2026, 7, 22), {"f1": "约书亚记17", "f2": "以赛亚书13", "n1": "腓利门书1", "ps": "诗篇54"}),
        (date(2026, 12, 31), {"f1": "创世记28", "f2": "但以理书4", "n1": "使徒行传17", "ps": "诗篇66"}),
    ],
)
def test_readings_match_frontend_calendar(day, expected):
    assert readings_for(day) == expected


def test_notification_contains_readings_study_prompt_and_deep_link():
    payload = notification_for(date(2026, 7, 22))

    assert payload["title"] == "📖 麦琴读经 · 7月22日"
    for ref in ("约书亚记17", "以赛亚书13", "腓利门书1", "诗篇54"):
        assert ref in payload["body"]
    assert "查经" in payload["body"]
    assert payload["url"] == "/?panel=mccheyne"
    assert payload["tag"] == "mccheyne-2026-07-22"


class _Cursor:
    def __init__(self, store):
        self.store = store
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split())
        self.store["executed"].append((normalized, params))
        if "FROM push_subscriptions" in normalized:
            self.rows = list(self.store["web_rows"])
        elif "FROM fcm_device_tokens" in normalized:
            self.rows = list(self.store["fcm_rows"])
        else:
            self.rows = []

    def fetchall(self):
        return self.rows


class _Connection:
    def __init__(self, store):
        self.store = store

    def cursor(self):
        return _Cursor(self.store)

    def commit(self):
        self.store["commits"] += 1

    def rollback(self):
        self.store["rollbacks"] += 1


class _Fcm:
    def __init__(self):
        self.calls = []

    @staticmethod
    def is_configured():
        return True

    def send_to_token(self, token, title, body, data):
        self.calls.append((token, title, body, data))
        return "unregistered" if token == "dead-token" else "ok"


def _store():
    return {
        "web_rows": [("web-1", "https://push/ok", "p1", "a1"), ("web-2", "https://push/dead", "p2", "a2")],
        "fcm_rows": [("fcm-1", "live-token"), ("fcm-2", "dead-token")],
        "executed": [],
        "commits": 0,
        "rollbacks": 0,
        "released": 0,
    }


def test_delivery_waits_until_eight_am_without_touching_database():
    store = _store()
    result = deliver_due(
        datetime(2026, 7, 22, 7, 59, tzinfo=SHANGHAI),
        get_db=lambda: _Connection(store),
        release_db=lambda conn: store.__setitem__("released", store["released"] + 1),
        send_web=lambda sub, payload: "ok",
        web_configured=True,
        fcm_sender=_Fcm(),
    )

    assert result["due"] is False
    assert result["web_sent"] == result["fcm_sent"] == 0
    assert store["executed"] == []


def test_delivery_sends_all_active_devices_and_records_idempotency():
    store = _store()
    web_payloads = []
    fcm = _Fcm()

    def send_web(sub, payload):
        web_payloads.append(payload)
        return "expired" if sub["endpoint"].endswith("dead") else "ok"

    result = deliver_due(
        datetime(2026, 7, 22, 8, 0, tzinfo=SHANGHAI),
        get_db=lambda: _Connection(store),
        release_db=lambda conn: store.__setitem__("released", store["released"] + 1),
        send_web=send_web,
        web_configured=True,
        fcm_sender=fcm,
    )

    assert result == {
        "due": True,
        "day": "2026-07-22",
        "web_sent": 1,
        "fcm_sent": 1,
        "expired": 2,
        "errors": 0,
    }
    assert len(web_payloads) == 2 and "查经" in web_payloads[0]["body"]
    assert len(fcm.calls) == 2 and fcm.calls[0][3]["url"] == "/?panel=mccheyne"
    sql = "\n".join(statement for statement, _ in store["executed"])
    assert "last_mccheyne_sent IS NULL OR last_mccheyne_sent < %s" in sql
    assert "UPDATE push_subscriptions SET last_mccheyne_sent=%s" in sql
    assert "UPDATE fcm_device_tokens SET last_mccheyne_sent=%s" in sql
    assert "SET enabled=FALSE" in sql and "SET revoked_at=NOW()" in sql
    assert store["commits"] == 2 and store["released"] == 2
