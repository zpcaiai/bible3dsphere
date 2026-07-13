"""Skill 15 invariants: step-up, sensitive-export approval and secure download."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from fastapi.routing import APIRoute
from mission_os import sensitive_export as se
from routers.mission_sensitive_export import router

pytestmark = pytest.mark.no_db


def test_token_hash_requires_high_entropy_and_is_one_way():
    with pytest.raises(ValueError):
        se.hash_token("short")
    h = se.hash_token("x" * 32)
    assert len(h) == 64 and h != "x" * 32


def test_only_declared_transitions_are_allowed():
    assert se.can_transition("requested", "step_up_pending")
    assert se.can_transition("step_up_pending", "approved")
    assert se.can_transition("approved", "ready")
    assert not se.can_transition("requested", "ready")   # cannot skip step-up + approval
    assert not se.can_transition("denied", "approved")
    with pytest.raises(ValueError):
        se.assert_transition("ready", "approved")


def test_step_up_must_be_recent():
    now = datetime.now(timezone.utc)
    assert se.step_up_fresh(now - timedelta(minutes=5), now=now)
    assert not se.step_up_fresh(now - timedelta(minutes=30), now=now)
    assert not se.step_up_fresh(None, now=now)


def test_approver_must_be_independent_and_stepped_up():
    now = datetime.now(timezone.utc)
    fresh = now - timedelta(minutes=1)
    with pytest.raises(ValueError):  # self-approval blocked
        se.can_approve(requester_id="a", approver_id="a", step_up_verified_at=fresh, now=now)
    with pytest.raises(ValueError):  # stale step-up blocked
        se.can_approve(requester_id="a", approver_id="b", step_up_verified_at=now - timedelta(hours=1), now=now)
    se.can_approve(requester_id="a", approver_id="b", step_up_verified_at=fresh, now=now)  # ok


def test_expiry_must_be_future_and_bounded():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        se.validate_expiry(now - timedelta(minutes=1), now=now)
    with pytest.raises(ValueError):
        se.validate_expiry(now + timedelta(days=3), now=now)  # exceeds 24h window
    assert se.validate_expiry(now + timedelta(hours=1), now=now)


def test_download_availability_fails_closed():
    now = datetime.now(timezone.utc)
    future = now + timedelta(minutes=30)
    assert se.download_available(status="ready", expires_at=future, downloads=0, max_downloads=1, now=now)
    assert not se.download_available(status="ready", expires_at=now - timedelta(minutes=1), downloads=0, max_downloads=1, now=now)
    assert not se.download_available(status="ready", expires_at=future, downloads=1, max_downloads=1, now=now)
    assert not se.download_available(status="revoked", expires_at=future, downloads=0, max_downloads=1, now=now)
    assert not se.download_available(status="ready", expires_at=future, downloads=0, max_downloads=1, revoked_at=now, now=now)


def test_watermark_required():
    with pytest.raises(ValueError):
        se.require_watermark("")
    assert se.require_watermark("tenant-X • 2026") == "tenant-X • 2026"


def test_migration_enforces_rls_and_independent_approver():
    sql = (Path(__file__).parents[1] / "migrations" / "0187_mission_os_sensitive_export.sql").read_text()
    assert sql.count("ENABLE ROW LEVEL SECURITY") == 2
    assert "token_hash TEXT UNIQUE" in sql
    assert "approver_id IS NULL OR approver_id<>requester_id" in sql
    assert "-- Rollback:" in sql


def test_router_returns_raw_token_once_but_stores_only_hash():
    src = (Path(__file__).parents[1] / "routers" / "mission_sensitive_export.py").read_text()
    assert "token_hash = se.hash_token(raw)" in src
    assert "'downloadToken': raw" in src
    # the stored/queried column is the hash, and revoke nulls the token hash
    assert "token_hash=NULL" in src
    assert "secrets.compare_digest" in src


def test_skill_15_api_contract_exists():
    routes = {(r.path, m) for r in router.routes if isinstance(r, APIRoute) for m in r.methods}
    expected = {
        ("/api/v1/mission/sensitive-exports", "POST"),
        ("/api/v1/mission/sensitive-exports/{request_id}/step-up", "POST"),
        ("/api/v1/mission/sensitive-exports/{request_id}/approve", "POST"),
        ("/api/v1/mission/sensitive-exports/{request_id}/deny", "POST"),
        ("/api/v1/mission/sensitive-exports/{request_id}/download", "GET"),
        ("/api/v1/mission/sensitive-exports/{request_id}/revoke", "POST"),
    }
    assert expected <= routes
