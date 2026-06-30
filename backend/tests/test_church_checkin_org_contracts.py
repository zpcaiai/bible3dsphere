"""Contract tests for church check-in create-with-org (B12) — no real database.

create_checkin 把出勤签到自动归属到组织:
  · 显式 org_id → 必须是该组织 active 成员(否则 403,且 INSERT 不执行);成员 → INSERT 盖该 org_id。
  · 未给 org_id → 用户恰好属于 1 个 active 组织时自动盖其 org_id;0 或多个 → org_id=NULL(保持个人私有)。
"""
import pytest
from fastapi import HTTPException

from routers import church_integration as cg

pytestmark = pytest.mark.no_db

USER = {"email": "carol@test", "id": 9}


class FakeCursor:
    def __init__(self, role_row=("member",), member_rows=None):
        self.role_row = role_row          # require_membership/resolve_role 的 fetchone
        self.member_rows = member_rows or []  # list_memberships 的 fetchall
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
        return self.role_row

    def fetchall(self):
        return self.member_rows


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def rollback(self):
        pass


def wire(cursor, user=USER):
    conn = FakeConn(cursor)
    cg.init_church_integration_router(
        get_db=lambda: conn,
        release_db=lambda c: None,
        get_session_user=lambda request: user,
        to_shanghai_iso=lambda dt: (dt if isinstance(dt, str) else (dt.isoformat() if dt else None)),
    )
    return conn


def _insert(cur):
    for c, p in zip(cur.calls, cur.params):
        if "insert into church_life_checkins" in c.lower():
            return c, p
    return None, None


def test_explicit_org_member_stamps_org_id():
    cur = FakeCursor(role_row=("member",))   # require_membership 通过
    wire(cur)
    cg.create_checkin(None, cg.CheckinCreate(org_id="ORGA"))
    sql, params = _insert(cur)
    assert sql is not None, "INSERT must run"
    assert params[-1] == "ORGA", "explicit org_id must be stamped"


def test_explicit_org_non_member_403_no_insert():
    cur = FakeCursor(role_row=None)          # 非成员
    wire(cur)
    with pytest.raises(HTTPException) as ei:
        cg.create_checkin(None, cg.CheckinCreate(org_id="ORGB"))
    assert ei.value.status_code == 403
    assert not any("insert into church_life_checkins" in c.lower() for c in cur.calls), \
        "INSERT must NOT run when caller is not a member of the named org"


def test_auto_derive_sole_membership():
    cur = FakeCursor(member_rows=[("ORGA", "member", "active")])
    wire(cur)
    cg.create_checkin(None, cg.CheckinCreate())   # 无 org_id
    sql, params = _insert(cur)
    assert sql is not None
    assert params[-1] == "ORGA", "sole active org must be auto-stamped"


def test_multiple_memberships_leave_null():
    cur = FakeCursor(member_rows=[("ORGA", "member", "active"), ("ORGB", "leader", "active")])
    wire(cur)
    cg.create_checkin(None, cg.CheckinCreate())
    sql, params = _insert(cur)
    assert sql is not None
    assert params[-1] is None, "ambiguous membership must NOT auto-assign (stay personal)"


def test_no_membership_leaves_null():
    cur = FakeCursor(member_rows=[])
    wire(cur)
    cg.create_checkin(None, cg.CheckinCreate())
    sql, params = _insert(cur)
    assert sql is not None
    assert params[-1] is None, "no org → org_id NULL (personal)"
