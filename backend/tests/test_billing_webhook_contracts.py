"""Contract tests for billing webhook persistence (B12-4) — no real database, no Stripe.

We test billing._apply_event directly (the part that writes subscriptions),
bypassing signature verification / the stripe SDK. Asserts the upsert SQL + params
for the events we handle.
"""
import pytest

from routers import billing as bl

pytestmark = pytest.mark.no_db


class FakeCursor:
    def __init__(self, existing=None):
        self.existing = existing          # row returned by "SELECT id FROM subscriptions ..."
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
        return self.existing


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def rollback(self):
        pass


def wire(cursor):
    conn = FakeConn(cursor)
    bl.init_billing_router(
        get_db=lambda: conn,
        release_db=lambda c: None,
        get_session_user=lambda request: {"email": "x@test"},
        to_shanghai_iso=lambda dt: dt,
    )
    return conn


def _find(cur, verb, table):
    for c, p in zip(cur.calls, cur.params):
        cl = c.lower()
        if cl.startswith(verb) and table in cl:
            return c, p
    return None, None


def test_checkout_completed_inserts_new_subscription():
    cur = FakeCursor(existing=None)   # 该 email 尚无订阅 → INSERT
    wire(cur)
    bl._apply_event("checkout.session.completed", {
        "metadata": {"email": "buyer@test", "plan_key": "church_pro"},
        "subscription": "sub_123", "customer": "cus_1",
    })
    sql, params = _find(cur, "insert", "subscriptions")
    assert sql is not None, "must INSERT a new subscription"
    assert "buyer@test" in params and "church_pro" in params
    assert "sub_123" in params and "cus_1" in params


def test_checkout_completed_updates_existing_subscription():
    cur = FakeCursor(existing=("existing_id",))   # 已有订阅 → UPDATE
    wire(cur)
    bl._apply_event("checkout.session.completed", {
        "metadata": {"email": "buyer@test", "plan_key": "church_pro"},
        "subscription": "sub_999", "customer": "cus_9",
    })
    sql, params = _find(cur, "update", "subscriptions")
    assert sql is not None, "must UPDATE the existing subscription"
    assert "where id=%s" in sql.lower()
    assert "existing_id" in params and "active" in params and "sub_999" in params


def test_subscription_deleted_marks_canceled_by_stripe_id():
    cur = FakeCursor()
    wire(cur)
    bl._apply_event("customer.subscription.deleted", {"id": "sub_777", "customer": "cus_7", "status": "canceled"})
    sql, params = _find(cur, "update", "subscriptions")
    assert sql is not None, "must UPDATE subscription by stripe id"
    assert "where stripe_subscription_id=%s" in sql.lower()
    assert "canceled" in params and "sub_777" in params


def test_subscription_updated_sets_status_by_stripe_id():
    cur = FakeCursor()
    wire(cur)
    bl._apply_event("customer.subscription.updated", {"id": "sub_555", "customer": "cus_5", "status": "active"})
    sql, params = _find(cur, "update", "subscriptions")
    assert sql is not None
    assert "where stripe_subscription_id=%s" in sql.lower()
    assert "sub_555" in params


def test_unknown_event_is_noop():
    cur = FakeCursor()
    wire(cur)
    bl._apply_event("invoice.payment_failed", {"id": "in_1"})
    assert cur.calls == [], "unhandled events must not touch the database"
