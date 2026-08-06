"""Live PostgreSQL acceptance for the Batch 01-12 trust boundaries."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

import main


ROOT = Path(__file__).parents[1]
BASE = "/api/v1/sunday-school/ai-formation"
_test_client_ip_counter = 10


@pytest.fixture(scope="module", autouse=True)
def ai_formation_schema(_test_db_session):
    """Apply only this module's self-contained migrations to the test DB."""

    conn = main._get_db()
    try:
        with conn.cursor() as cur:
            for filename in (
                "0238_sunday_school_ai_formation_batches_01_12.sql",
                "0239_ai_formation_production_workflows.sql",
                "0240_ai_formation_reviewed_asset_catalog.sql",
                "0241_ai_formation_five_role_content_review.sql",
            ):
                cur.execute((ROOT / "migrations" / filename).read_text(encoding="utf-8"))
        conn.commit()
    finally:
        main._release_db(conn)


def _register(client, label: str) -> tuple[str, dict[str, str]]:
    global _test_client_ip_counter
    _test_client_ip_counter += 1
    # These are distinct human roles, so model them as distinct clients instead
    # of defeating the production five-per-minute verification-code limiter.
    client_headers = {"X-Forwarded-For": f"198.51.100.{_test_client_ip_counter}"}
    email = f"ai-formation-{label}-{uuid.uuid4().hex[:10]}@example.com"
    sent = client.post("/api/auth/email/send-code", json={"email": email}, headers=client_headers)
    assert sent.status_code == 200
    registered = client.post(
        "/api/auth/email/register",
        json={"email": email, "code": sent.json()["dev_code"], "password": "testpassword123", "nickname": label},
        headers=client_headers,
    )
    assert registered.status_code == 200
    token = client.cookies.get("biblesphere_session")
    assert token
    return email, {"Authorization": f"Bearer {token}", **client_headers}


def _make_admin(email: str) -> None:
    conn = main._get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET is_admin=TRUE WHERE LOWER(email)=LOWER(%s)", (email,))
        conn.commit()
    finally:
        main._release_db(conn)
    main._ADMIN_CACHE.pop(email, None)


def _context(age_band: str = "adult") -> dict:
    return {
        "role": "learner",
        "age_band": age_band,
        "locale": "zh-CN",
        "goals": ["ai_discernment"],
        "accessibility_needs": [],
        "device_context": "prefer_not_to_say",
        "consent": {
            "data_minimization_accepted": True,
            "guardian_confirmed": True if age_band != "adult" else None,
            "pastoral_followup_allowed": False,
        },
    }


def test_owner_scoped_record_lifecycle_age_gate_and_data_rights(client, monkeypatch):
    monkeypatch.setenv("SUNDAY_SCHOOL_AI_FORMATION_ENABLED", "true")
    _email, headers = _register(client, "learner")
    body = {
        "record_type": "learner_context",
        "payload": _context(),
        "idempotency_key": f"context-{uuid.uuid4()}",
        "retention_days": 30,
    }
    created = client.post(f"{BASE}/records", json=body, headers=headers)
    assert created.status_code == 201, created.text
    record = created.json()["record"]
    replay = client.post(f"{BASE}/records", json=body, headers=headers)
    assert replay.status_code == 201
    assert replay.json()["idempotentReplay"] is True

    changed = _context()
    changed["goals"] = ["attention", "ai_discernment"]
    updated = client.patch(
        f"{BASE}/records/{record['id']}",
        json={"payload": changed, "expected_revision": 1},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["record"]["revision"] == 2
    stale = client.patch(
        f"{BASE}/records/{record['id']}",
        json={"payload": changed, "expected_revision": 1},
        headers=headers,
    )
    assert stale.status_code == 409
    paused = client.post(
        f"{BASE}/records/{record['id']}/transition",
        json={"transition": "pause", "expected_revision": 2},
        headers=headers,
    )
    assert paused.status_code == 200
    assert paused.json()["record"]["status"] == "paused"

    mismatch = client.get(f"{BASE}/content?age_band=13_15", headers=headers)
    assert mismatch.status_code == 403
    export = client.get(f"{BASE}/data-rights/export", headers=headers)
    assert export.status_code == 200
    assert [item["id"] for item in export.json()["records"]] == [record["id"]]
    deleted = client.delete(f"{BASE}/data-rights/records", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["deletedRecords"] == 1
    assert client.get(f"{BASE}/data-rights/export", headers=headers).json()["records"] == []


def test_content_requires_named_distinct_reviewers_and_separate_publisher(client, monkeypatch):
    monkeypatch.setenv("SUNDAY_SCHOOL_AI_FORMATION_ENABLED", "true")
    reviewers = {
        role: _register(client, role)
        for role in (
            "theology_reviewer", "pastoral_reviewer", "child_safety_reviewer",
            "rights_reviewer", "content_reviewer",
        )
    }
    publisher_email, publisher_headers = _register(client, "publisher")
    for email, _headers in (*reviewers.values(), (publisher_email, publisher_headers)):
        _make_admin(email)
    reviewer_env = {
        "theology_reviewer": "AI_FORMATION_THEOLOGY_REVIEWERS",
        "pastoral_reviewer": "AI_FORMATION_PASTORAL_REVIEWERS",
        "child_safety_reviewer": "AI_FORMATION_CHILD_SAFETY_REVIEWERS",
        "rights_reviewer": "AI_FORMATION_PRIVACY_RIGHTS_REVIEWERS",
        "content_reviewer": "AI_FORMATION_CONTENT_REVIEWERS",
    }
    for role, (email, _headers) in reviewers.items():
        monkeypatch.setenv(reviewer_env[role], email)
    monkeypatch.setenv("AI_FORMATION_PUBLISHERS", publisher_email)
    # The product intentionally prefers its HttpOnly browser cookie over a
    # Bearer token. Clear the last registration cookie so each test request can
    # exercise a distinct native-client identity through Authorization.
    client.cookies.clear()

    theology_email, theology_headers = reviewers["theology_reviewer"]
    queue = client.get(f"{BASE}/content/review-queue?batch_id=01", headers=theology_headers)
    assert queue.status_code == 200
    required_roles = [
        "theology_reviewer", "pastoral_reviewer", "child_safety_reviewer",
        "rights_reviewer", "content_reviewer",
    ]
    content = next(item for item in queue.json()["content"] if item["required_reviews_json"] == required_roles)
    path = f"{BASE}/content/{content['id']}/versions/{content['version']}"
    unauthorized = client.post(
        f"{path}/reviews",
        json={
            "reviewer_role": "pastoral_reviewer", "decision": "approve",
            "content_sha256": content["content_sha256"], "reason_codes": ["TEST_ROLE_BOUNDARY"],
        },
        headers=theology_headers,
    )
    assert unauthorized.status_code == 403
    missing_attestations = client.post(
        f"{path}/reviews",
        json={
            "reviewer_role": "theology_reviewer", "decision": "approve",
            "content_sha256": content["content_sha256"], "reason_codes": ["TEST_APPROVAL"],
        },
        headers=theology_headers,
    )
    assert missing_attestations.status_code == 422
    assert missing_attestations.json()["detail"]["missingAttestations"]

    from ai_formation.content_audit import REQUIRED_REVIEW_ATTESTATIONS

    for role in required_roles:
        _email, headers = reviewers[role]
        reviewed = client.post(
            f"{path}/reviews",
            json={
                "reviewer_role": role, "decision": "approve",
                "content_sha256": content["content_sha256"],
                "reason_codes": REQUIRED_REVIEW_ATTESTATIONS[role],
            },
            headers=headers,
        )
        assert reviewed.status_code == 201, reviewed.text
    assert reviewed.json()["reviewStatus"] == "approved"
    detail = client.get(path, headers=theology_headers).json()
    assert detail["reviewSummary"]["pendingRoles"] == []
    assert set(detail["reviewSummary"]["approvedRoles"]) == set(required_roles)

    reviewer_publish = client.post(
        f"{path}/publish",
        json={"content_sha256": content["content_sha256"], "reason_code": "TEST_PUBLISH"},
        headers=theology_headers,
    )
    assert reviewer_publish.status_code == 403
    published = client.post(
        f"{path}/publish",
        json={"content_sha256": content["content_sha256"], "reason_code": "TEST_PUBLISH"},
        headers=publisher_headers,
    )
    assert published.status_code == 200, published.text
    retired = client.post(f"{path}/retire", headers=publisher_headers)
    assert retired.status_code == 200


def test_release_decision_fails_closed_without_exact_evidence(client, monkeypatch):
    release_email, headers = _register(client, "release")
    _make_admin(release_email)
    monkeypatch.setenv("AI_FORMATION_RELEASE_AUTHORITIES", release_email)
    artifact_sha = "a" * 64
    decision = {
        "artifact_id": "ai-formation-web-api",
        "artifact_version": "test-1",
        "environment": "staging",
        "artifact_sha256": artifact_sha,
        "decision": "approved",
        "rollout_percent": 100,
        "rollback_owner": "rollback@example.com",
        "incident_owner": "incident@example.com",
        "reason_codes": ["TEST_ONLY"],
    }
    blocked = client.post(f"{BASE}/certification/release-decisions", json=decision, headers=headers)
    assert blocked.status_code == 409
    detail = blocked.json()["detail"]
    assert detail["message"] == "Release gates are not ready"
    assert len(detail["blockers"]) == 10


def test_scenario_runtime_pins_approved_version_and_accepts_bounded_choices_only(client, monkeypatch):
    monkeypatch.setenv("SUNDAY_SCHOOL_AI_FORMATION_ENABLED", "true")
    _email, headers = _register(client, "scenario")
    context = client.post(
        f"{BASE}/records",
        json={
            "record_type": "learner_context", "payload": _context(),
            "idempotency_key": f"scenario-context-{uuid.uuid4()}", "retention_days": 30,
        },
        headers=headers,
    )
    assert context.status_code == 201

    # Content review/publisher separation is accepted above. This test fixture
    # activates the exact immutable scenario seed only to exercise the runtime.
    conn = main._get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sunday_school_ai_formation_content SET review_status='approved',published_at=NOW(),retired_at=NULL "
                "WHERE batch_id='10' AND content_kind='scenario-runtime-scenarios.seed'"
            )
        conn.commit()
    finally:
        main._release_db(conn)

    available = client.get(f"{BASE}/scenarios", headers=headers)
    assert available.status_code == 200
    scenario = available.json()["scenarios"][0]
    started = client.post(
        f"{BASE}/scenarios/sessions",
        json={"scenario_id": scenario["id"], "idempotency_key": f"scenario-{uuid.uuid4()}", "retention_days": 30},
        headers=headers,
    )
    assert started.status_code == 201, started.text
    session = started.json()["session"]
    assert started.json()["scenario"]["contentSha256"] == scenario["contentSha256"]
    assert {item["id"] for item in started.json()["choices"]} == {"observe", "pause", "seek_help", "repair", "skip", "complete"}

    paused = client.post(
        f"{BASE}/scenarios/sessions/{session['id']}/choices",
        json={"choice": "pause", "expected_revision": 1}, headers=headers,
    )
    assert paused.status_code == 200
    assert paused.json()["rawFreeTextPersisted"] is False
    stale = client.post(
        f"{BASE}/scenarios/sessions/{session['id']}/choices",
        json={"choice": "observe", "expected_revision": 1}, headers=headers,
    )
    assert stale.status_code == 409
    completed = client.post(
        f"{BASE}/scenarios/sessions/{session['id']}/choices",
        json={"choice": "complete", "expected_revision": 2}, headers=headers,
    )
    assert completed.status_code == 200
    assert completed.json()["session"]["status"] == "completed"
