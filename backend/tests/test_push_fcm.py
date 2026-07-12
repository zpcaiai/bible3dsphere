"""FCM 设备推送路由 + fcm_sender no-op 行为的最小 no_db 测试。

参照 test_speech_router.py 模式：TestClient 单挂 push router，DB 以假连接注入
（init_push_router 与生产同一注入口），不需要 PostgreSQL。
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import fcm_sender
from routers import push

pytestmark = pytest.mark.no_db

_USER = {"email": "u@example.com", "id": 1, "nickname": "tester"}


class _FakeCursor:
    def __init__(self, store):
        self._store = store

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self._store["executed"].append((" ".join(sql.split()), params))

    def fetchall(self):
        return list(self._store.get("rows", []))

    def fetchone(self):
        rows = self._store.get("rows", [])
        return rows[0] if rows else None


class _FakeConn:
    def __init__(self, store):
        self._store = store

    def cursor(self):
        return _FakeCursor(self._store)

    def commit(self):
        self._store["commits"] += 1

    def rollback(self):
        self._store["rollbacks"] += 1


def _store(rows=None) -> dict:
    return {"executed": [], "commits": 0, "rollbacks": 0, "released": 0, "rows": rows or []}


def _client(store, user=_USER) -> TestClient:
    push.init_push_router(
        get_db=lambda: _FakeConn(store),
        release_db=lambda conn: store.__setitem__("released", store["released"] + 1),
        get_session_user=lambda request: user,
    )
    app = FastAPI()
    app.include_router(push.router)
    return TestClient(app)


# ── /api/push/fcm/register ───────────────────────────────────────────────────
def test_fcm_register_upserts_token(monkeypatch):
    monkeypatch.delenv("FCM_SERVICE_ACCOUNT_JSON", raising=False)
    fcm_sender._reset_cache()
    store = _store()

    resp = _client(store).post(
        "/api/push/fcm/register", json={"token": "tok-abc", "platform": "ios"}
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "configured": False}
    assert store["commits"] == 1 and store["released"] == 1
    sql, params = store["executed"][0]
    assert "INSERT INTO fcm_device_tokens" in sql
    assert "ON CONFLICT (token) DO UPDATE" in sql
    assert "revoked_at=NULL" in sql
    assert params[1:] == ("u@example.com", "tok-abc", "ios")


def test_fcm_register_rejects_unknown_platform():
    store = _store()
    resp = _client(store).post(
        "/api/push/fcm/register", json={"token": "tok-abc", "platform": "windows"}
    )
    assert resp.status_code == 400
    assert store["executed"] == []  # 参数校验先于 DB


def test_fcm_register_requires_login():
    store = _store()
    resp = _client(store, user=None).post(
        "/api/push/fcm/register", json={"token": "tok-abc", "platform": "android"}
    )
    assert resp.status_code == 401
    assert store["executed"] == []


# ── /api/push/fcm/unregister ─────────────────────────────────────────────────
def test_fcm_unregister_marks_revoked():
    store = _store()
    resp = _client(store).post("/api/push/fcm/unregister", json={"token": "tok-abc"})

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    sql, params = store["executed"][0]
    assert "UPDATE fcm_device_tokens SET revoked_at=NOW()" in sql
    assert params == ("u@example.com", "tok-abc")
    assert store["commits"] == 1 and store["released"] == 1


# ── /api/push/fcm/status ─────────────────────────────────────────────────────
def test_fcm_status_counts_active_devices(monkeypatch):
    monkeypatch.delenv("FCM_SERVICE_ACCOUNT_JSON", raising=False)
    fcm_sender._reset_cache()
    store = _store(rows=[("android", 2), ("ios", 1)])

    resp = _client(store).get("/api/push/fcm/status")

    assert resp.status_code == 200
    assert resp.json() == {
        "ok": True,
        "configured": False,
        "devices": 3,
        "by_platform": {"android": 2, "ios": 1},
    }
    sql, params = store["executed"][0]
    assert "revoked_at IS NULL" in sql and params == ("u@example.com",)


# ── fcm_sender：未配置时安全 no-op ───────────────────────────────────────────
def test_fcm_sender_noop_when_unconfigured(monkeypatch):
    monkeypatch.delenv("FCM_SERVICE_ACCOUNT_JSON", raising=False)
    fcm_sender._reset_cache()

    assert fcm_sender.is_configured() is False
    assert fcm_sender.send_to_token("tok", "t", "b") == "skipped"
    out = fcm_sender.send_to_user("u@example.com", "t", "b")
    assert out == {"configured": False, "sent": 0, "revoked": 0, "errors": 0}


def test_fcm_sender_marks_unregistered_tokens_revoked(monkeypatch):
    """已配置 + FCM 返回 UNREGISTERED 时，token 应被标记 revoked。"""
    monkeypatch.setenv(
        "FCM_SERVICE_ACCOUNT_JSON",
        '{"project_id": "p1", "client_email": "svc@p1.iam", "private_key": "k"}',
    )
    fcm_sender._reset_cache()
    monkeypatch.setattr(fcm_sender, "send_to_token", lambda *a, **k: "unregistered")

    store = _store(rows=[("tok-dead",)])
    out = fcm_sender.send_to_user(
        "u@example.com", "t", "b",
        get_db=lambda: _FakeConn(store),
        release_db=lambda conn: store.__setitem__("released", store["released"] + 1),
    )

    assert out["configured"] is True and out["sent"] == 0 and out["revoked"] == 1
    revoke_sql, revoke_params = store["executed"][-1]
    assert "SET revoked_at=NOW()" in revoke_sql and revoke_params == (("tok-dead",),)
    assert store["commits"] == 1 and store["released"] == 2
    fcm_sender._reset_cache()
