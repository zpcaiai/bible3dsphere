"""Contract tests for platform_admin org suspend/reactivate (B12-4) — no real database.

Asserts: admin gate runs first; suspend/reactivate flips organizations.status and
writes a platform_moderation_log row; non-admin is 403 with no writes.
"""
import pytest
from fastapi import HTTPException

from routers import platform_admin as pa

pytestmark = pytest.mark.no_db

ADMIN = {"email": "root@test", "id": 1}


class FakeCursor:
    def __init__(self, is_admin=True):
        self._admin = (1,) if is_admin else None
        self.calls = []
        self.params = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self.calls.append(" ".join(str(sql).split()))
        self.params.append(params)

    def fetchone(self):
        # 仅 _require_admin 用 fetchone(SELECT 1 FROM platform_admins ...)
        return self._admin


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def rollback(self):
        pass


def wire(cursor, user=ADMIN):
    conn = FakeConn(cursor)
    pa.init_platform_admin_router(
        get_db=lambda: conn,
        release_db=lambda c: None,
        get_session_user=lambda request: user,
        to_shanghai_iso=lambda dt: dt,
    )
    return conn


def _find(cur, verb, needle):
    for c, p in zip(cur.calls, cur.params):
        cl = c.lower()
        if cl.startswith(verb) and needle in cl:
            return c, p
    return None, None


def test_admin_check_runs_first():
    cur = FakeCursor(is_admin=True)
    wire(cur)
    pa.suspend_org("ORGA", None, pa.SuspendBody(note="abuse"))
    assert any("platform_admins" in c.lower() for c in cur.calls), "must verify platform admin"


def test_suspend_flips_status_and_logs():
    cur = FakeCursor(is_admin=True)
    wire(cur)
    pa.suspend_org("ORGA", None, pa.SuspendBody(note="abuse"))
    usql, uparams = _find(cur, "update", "organizations")
    assert usql is not None, "must UPDATE organizations"
    assert "status='suspended'" in usql.lower() and "where id=%s" in usql.lower()
    assert uparams == ("ORGA",)
    lsql, lparams = _find(cur, "insert", "platform_moderation_log")
    assert lsql is not None, "must write a moderation log row"
    assert "org_suspend" in lparams and "ORGA" in lparams


def test_reactivate_flips_status_and_logs():
    cur = FakeCursor(is_admin=True)
    wire(cur)
    pa.reactivate_org("ORGA", None, pa.SuspendBody(note="resolved"))
    usql, uparams = _find(cur, "update", "organizations")
    assert usql is not None
    assert "status='active'" in usql.lower() and "where id=%s" in usql.lower()
    assert uparams == ("ORGA",)
    lsql, lparams = _find(cur, "insert", "platform_moderation_log")
    assert lsql is not None and "org_reactivate" in lparams


def test_non_admin_403_no_writes():
    cur = FakeCursor(is_admin=False)
    wire(cur)
    with pytest.raises(HTTPException) as ei:
        pa.suspend_org("ORGA", None, pa.SuspendBody())
    assert ei.value.status_code == 403
    assert not any(c.lower().startswith("update organizations") for c in cur.calls), \
        "non-admin must not flip org status"
    assert not any("platform_moderation_log" in c.lower() for c in cur.calls), \
        "non-admin must not write moderation log"
