"""Contract tests for org-console progress endpoints (B12 多租户) — no real database.

Mirrors test_gift_calling_router: inject fake get_db / release_db / session-user
into the router and call handlers directly with a recording FakeCursor.

These tests are the CI guard for the two isolation invariants on the progress reads:
  1. RBAC 强制   —— 每个端点先跑 require_org_permission(组织成员关系查询)。
  2. org 作用域 —— 数据查询带 org_id=%s 过滤,且 params 就是该 org_id。
  3. 非成员在任何数据查询之前就被 403 挡下(不泄漏)。
  4. 隐私   —— 数据查询绝不取会谈/步骤正文(agenda/summary/prayer_notes/reflection/...)。
"""
import re

import pytest
from fastapi import HTTPException

from routers import org_console as oc

pytestmark = pytest.mark.no_db

USER = {"email": "leader@test", "id": 7}
BANNED = ("agenda", "summary", "prayer_notes", "reflection", "step_description",
          "risk_flags", "gratitude", "struggle", "prayer_request")


class FakeCursor:
    """记录所有 execute 的 SQL 与 params;fetchone 返回预置角色行(供 require_org_permission)。"""
    def __init__(self, role_row=("owner",)):
        self.role_row = role_row
        self.calls = []     # 规范化 SQL
        self.params = []    # 每次 execute 的 params

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
        return []


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
    oc.init_org_console_router(
        get_db=lambda: conn,
        release_db=lambda c: None,
        get_session_user=lambda request: user,
        to_shanghai_iso=lambda dt: (dt if isinstance(dt, str) else (dt.isoformat() if dt else None)),
    )
    return conn


def _role_query_ran(cur):
    return any("organization_memberships" in c and "role_key" in c.lower() for c in cur.calls)


def _data_query(cur, table):
    hits = [(c, cur.params[i]) for i, c in enumerate(cur.calls) if table in c.lower()]
    return hits[0] if hits else (None, None)


# ── discipleship progress ────────────────────────────────────────────────────
def test_discipleship_progress_rbac_and_org_scoped():
    cur = FakeCursor(("owner",))
    wire(cur)
    oc.discipleship_progress("ORGA", None)
    # 1) RBAC gate ran
    assert _role_query_ran(cur), "must call require_org_permission (role lookup)"
    # 2) data query is org-scoped
    sql, params = _data_query(cur, "user_discipleship_paths")
    assert sql is not None, "must query user_discipleship_paths"
    assert "p.org_id=%s" in sql.lower(), "discipleship data query must filter by org_id"
    assert params == ("ORGA",), "org_id param must be bound to the caller's org"
    # 4) privacy: no personal content columns
    low = sql.lower()
    assert not any(b in low for b in BANNED), "must not select personal/step content"


def test_discipleship_progress_non_member_blocked_before_data():
    cur = FakeCursor(role_row=None)   # 非成员
    wire(cur)
    with pytest.raises(HTTPException) as ei:
        oc.discipleship_progress("ORGA", None)
    assert ei.value.status_code == 403
    assert not any("user_discipleship_paths" in c.lower() for c in cur.calls), \
        "data query must NOT run when caller is not a member"


# ── mentor progress ──────────────────────────────────────────────────────────
def test_mentor_progress_rbac_and_org_scoped():
    cur = FakeCursor(("pastor",))   # pastor 有 manage_groups
    wire(cur)
    oc.mentor_progress("ORGB", None)
    assert _role_query_ran(cur)
    sql, params = _data_query(cur, "mentor_relationships")
    assert sql is not None, "must query mentor_relationships"
    assert "r.org_id=%s" in sql.lower(), "mentor data query must filter by org_id"
    assert params == ("ORGB",)
    low = sql.lower()
    assert not any(b in low for b in BANNED), "must not select session content"


def test_mentor_progress_non_member_blocked_before_data():
    cur = FakeCursor(role_row=None)
    wire(cur)
    with pytest.raises(HTTPException) as ei:
        oc.mentor_progress("ORGB", None)
    assert ei.value.status_code == 403
    assert not any("mentor_relationships" in c.lower() for c in cur.calls), \
        "data query must NOT run when caller is not a member"


def test_member_without_manage_groups_is_denied():
    """member 角色无 manage_groups → 进度端点 403(角色分级生效)。"""
    cur = FakeCursor(("member",))
    wire(cur)
    with pytest.raises(HTTPException) as ei:
        oc.discipleship_progress("ORGA", None)
    assert ei.value.status_code == 403


# ── church attendance trend ──────────────────────────────────────────────────
def test_church_trend_rbac_and_org_scoped():
    cur = FakeCursor(("org_admin",))
    wire(cur)
    oc.church_trend("ORGA", None, weeks=12)
    assert _role_query_ran(cur)
    sql, params = _data_query(cur, "church_life_checkins")
    assert sql is not None, "must query church_life_checkins"
    assert "org_id=%s" in sql.lower(), "church trend must filter by org_id"
    assert params == ("ORGA",)
    low = sql.lower()
    assert "reflection" not in low and "next_step" not in low, "must not select church check-in text"


def test_church_trend_non_member_blocked_before_data():
    cur = FakeCursor(role_row=None)
    wire(cur)
    with pytest.raises(HTTPException) as ei:
        oc.church_trend("ORGA", None, weeks=12)
    assert ei.value.status_code == 403
    assert not any("church_life_checkins" in c.lower() for c in cur.calls)


# ── group health ─────────────────────────────────────────────────────────────
def test_group_health_rbac_and_org_scoped():
    cur = FakeCursor(("leader",))
    wire(cur)
    oc.group_health("ORGA", None)
    assert _role_query_ran(cur)
    sql, params = _data_query(cur, "accountability_groups")
    assert sql is not None, "must query accountability_groups"
    assert "g.org_id=%s" in sql.lower(), "group health must filter groups by org_id"
    assert params == ("ORGA",)
    low = sql.lower()
    assert not any(b in low for b in ("gratitude", "struggle", "prayer_request", "reflection")), \
        "must not select check-in content (support_needed boolean count is OK)"


def test_group_health_non_member_blocked_before_data():
    cur = FakeCursor(role_row=None)
    wire(cur)
    with pytest.raises(HTTPException) as ei:
        oc.group_health("ORGA", None)
    assert ei.value.status_code == 403
    assert not any("accountability_groups" in c.lower() for c in cur.calls)


# ── cross-domain activity trend ──────────────────────────────────────────────
def test_activity_trend_rbac_and_org_scoped():
    cur = FakeCursor(("owner",))
    wire(cur)
    oc.activity_trend("ORGA", None, weeks=12)
    assert _role_query_ran(cur)
    sql, params = _data_query(cur, "church_life_checkins")   # UNION 引用它
    assert sql is not None, "must query church_life_checkins in the union"
    low = sql.lower()
    assert "org_id=%s" in low and "g.org_id=%s" in low, "must filter BOTH sources by org_id"
    assert params == ("ORGA", "ORGA"), "both union arms bound to caller's org"
    assert not any(b in low for b in ("gratitude", "struggle", "prayer_request", "reflection", "next_step")), \
        "must not select any check-in content"
    assert "filter (where src='church')" in low and "filter (where src='group')" in low, \
        "activity trend must split church vs group counts"


def test_activity_trend_non_member_blocked_before_data():
    cur = FakeCursor(role_row=None)
    wire(cur)
    with pytest.raises(HTTPException) as ei:
        oc.activity_trend("ORGA", None, weeks=12)
    assert ei.value.status_code == 403
    assert not any("church_life_checkins" in c.lower() for c in cur.calls)
