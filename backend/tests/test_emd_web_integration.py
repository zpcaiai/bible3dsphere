"""Live PostgreSQL acceptance for the web-facing EMD assessment journey."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

import main


ROOT = Path(__file__).parents[1]
BASE = "/api/v1/formation-twin/emotional-maturity"


@pytest.fixture(scope="module", autouse=True)
def emd_schema(_test_db_session):
    conn = main._get_db()
    try:
        with conn.cursor() as cur:
            for filename in (
                "0223_formation_twin_emotional_maturity.sql",
                "0224_formation_twin_emd_item_bank.sql",
            ):
                cur.execute((ROOT / "migrations" / filename).read_text(encoding="utf-8"))
        conn.commit()
    finally:
        main._release_db(conn)


def _register(client) -> tuple[str, dict[str, str]]:
    email = f"emd-web-{uuid.uuid4().hex[:10]}@example.com"
    sent = client.post("/api/auth/email/send-code", json={"email": email})
    assert sent.status_code == 200
    registered = client.post(
        "/api/auth/email/register",
        json={
            "email": email,
            "code": sent.json()["dev_code"],
            "password": "testpassword123",
            "nickname": "EMD web acceptance",
        },
    )
    assert registered.status_code == 200
    token = client.cookies.get("biblesphere_session")
    assert token
    return email, {"Authorization": f"Bearer {token}"}


def _source_type(item_type: str) -> str:
    if item_type == "BE":
        return "recent_behavior"
    if item_type == "SF":
        return "scenario_intention"
    return "self_report"


def test_consent_to_profile_and_route_is_page_ready_and_side_effect_safe(client):
    email, headers = _register(client)
    client.cookies.clear()

    consent = client.post(
        f"{BASE}/consent",
        json={
            "requested_scopes": ["EMD_SELF_ASSESSMENT"],
            "granted_scopes": ["EMD_SELF_ASSESSMENT"],
            "user_acknowledged_limits": True,
        },
        headers=headers,
    )
    assert consent.status_code == 200, consent.text
    session_id = consent.json()["session_id"]
    assert session_id

    scopes = client.get(f"{BASE}/consent-scopes", headers=headers)
    assert scopes.status_code == 200
    assert "EMD_SELF_ASSESSMENT" in scopes.json()["granted_scopes"]

    triage = client.post(
        f"{BASE}/triage",
        json={"session_id": session_id, "free_text": ""},
        headers=headers,
    )
    assert triage.status_code == 200, triage.text
    assert triage.json()["assessment_allowed"] is True

    intake = client.post(
        f"{BASE}/intake",
        json={"session_id": session_id, "submitted": {}},
        headers=headers,
    )
    assert intake.status_code == 200, intake.text
    assert intake.json()["status"] == "READY"

    next_item = client.post(
        f"{BASE}/items/next",
        json={"session_id": session_id, "item_budget": 6, "reading_level": "standard"},
        headers=headers,
    )
    assert next_item.status_code == 200, next_item.text
    selected = next_item.json()
    assert selected["decision"] == "ask_item"
    rendered = selected["rendered_item"]
    assert rendered["item_type"] != "BE", "real-behavior questions require the separate consent scope"

    response = client.post(
        f"{BASE}/responses",
        json={
            "session_id": session_id,
            "item_id": rendered["item_id"],
            "dimension_code": rendered["dimension_code"],
            "source_type": _source_type(rendered["item_type"]),
            "context": "OTHER",
            "raw_response": "3" if rendered["response_mode"] in {"likert", "frequency"} else "我会暂停再回应。",
            "occurred_in_real_life": False,
            "response_time_ms": 2500,
            "skipped": False,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["raw_text_stored"] is False
    if rendered["response_mode"] in {"likert", "frequency"}:
        conn = main._get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT response_choice FROM formation_twin_emd_responses "
                    "WHERE email=%s AND response_id=%s",
                    (email, response.json()["response_id"]),
                )
                assert cur.fetchone()[0] == "3"
        finally:
            main._release_db(conn)

    scored = client.post(
        f"{BASE}/score",
        json={"session_id": session_id, "responses": [{"duration_ms": 2500}]},
        headers=headers,
    )
    assert scored.status_code == 200, scored.text
    emd_profile_id = scored.json()["emd_profile_id"]

    created_route = client.post(
        f"{BASE}/route",
        json={"emd_profile_id": emd_profile_id, "max_dimensions": 2},
        headers=headers,
    )
    assert created_route.status_code == 200, created_route.text

    profile = client.get(f"{BASE}/profile", headers=headers)
    assert profile.status_code == 200, profile.text
    dimensions = profile.json()["profile"]["dimensions"]
    assert dimensions
    for entry in dimensions:
        assert all(entry[field] for field in ("stage", "context", "timeframe", "confidence"))
        assert entry["score"] is None
        assert entry["render_as"] == "TEXT_WITH_CONTEXT"

    latest_route = client.get(f"{BASE}/route", headers=headers)
    assert latest_route.status_code == 200, latest_route.text
    assert latest_route.json()["route"]["emd_profile_id"] == emd_profile_id


def test_a_new_session_has_its_own_item_budget(client):
    _email, headers = _register(client)
    client.cookies.clear()

    def new_session() -> str:
        decision = client.post(
            f"{BASE}/consent",
            json={
                "requested_scopes": ["EMD_SELF_ASSESSMENT"],
                "granted_scopes": ["EMD_SELF_ASSESSMENT"],
                "user_acknowledged_limits": True,
            },
            headers=headers,
        )
        assert decision.status_code == 200
        session_id = decision.json()["session_id"]
        assert client.post(f"{BASE}/triage", json={"session_id": session_id, "free_text": ""}, headers=headers).status_code == 200
        assert client.post(f"{BASE}/intake", json={"session_id": session_id, "submitted": {}}, headers=headers).status_code == 200
        return session_id

    first_session = new_session()
    first = client.post(
        f"{BASE}/items/next",
        json={"session_id": first_session, "item_budget": 1},
        headers=headers,
    ).json()["rendered_item"]
    saved = client.post(
        f"{BASE}/responses",
        json={
            "session_id": first_session,
            "item_id": first["item_id"],
            "dimension_code": first["dimension_code"],
            "source_type": _source_type(first["item_type"]),
            "raw_response": "3",
            "response_time_ms": 2500,
        },
        headers=headers,
    )
    assert saved.status_code == 200, saved.text

    second_session = new_session()
    second = client.post(
        f"{BASE}/items/next",
        json={"session_id": second_session, "item_budget": 1},
        headers=headers,
    )
    assert second.status_code == 200, second.text
    assert second.json()["decision"] == "ask_item"


def test_response_is_bound_to_the_presented_item_and_server_metadata(client):
    _email, headers = _register(client)
    client.cookies.clear()
    decision = client.post(
        f"{BASE}/consent",
        json={
            "requested_scopes": ["EMD_SELF_ASSESSMENT"],
            "granted_scopes": ["EMD_SELF_ASSESSMENT"],
            "user_acknowledged_limits": True,
        },
        headers=headers,
    )
    session_id = decision.json()["session_id"]
    assert client.post(f"{BASE}/triage", json={"session_id": session_id, "free_text": ""}, headers=headers).status_code == 200
    assert client.post(f"{BASE}/intake", json={"session_id": session_id, "submitted": {}}, headers=headers).status_code == 200
    rendered = client.post(
        f"{BASE}/items/next",
        json={"session_id": session_id, "item_budget": 6},
        headers=headers,
    ).json()["rendered_item"]

    base_payload = {
        "session_id": session_id,
        "item_id": rendered["item_id"],
        "dimension_code": rendered["dimension_code"],
        "source_type": _source_type(rendered["item_type"]),
        "raw_response": "3" if rendered["response_mode"] in {"likert", "frequency"} else "我会先暂停并确认事实。",
        "response_time_ms": 1200,
        "skipped": False,
    }
    wrong_item = client.post(
        f"{BASE}/responses",
        json={**base_payload, "item_id": "D10-SR-001", "dimension_code": "D10", "source_type": "self_report"},
        headers=headers,
    )
    assert wrong_item.status_code == 409

    wrong_metadata = client.post(
        f"{BASE}/responses",
        json={**base_payload, "dimension_code": "D10"},
        headers=headers,
    )
    assert wrong_metadata.status_code == 400

    if rendered["response_mode"] in {"likert", "frequency"}:
        invalid_choice = client.post(
            f"{BASE}/responses",
            json={**base_payload, "raw_response": "8"},
            headers=headers,
        )
        assert invalid_choice.status_code == 400

    accepted = client.post(f"{BASE}/responses", json=base_payload, headers=headers)
    assert accepted.status_code == 200, accepted.text
    duplicate = client.post(f"{BASE}/responses", json=base_payload, headers=headers)
    assert duplicate.status_code == 409
