from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import digital_human

pytestmark = pytest.mark.no_db


def test_official_embed_selects_face_animation_and_custom_model(monkeypatch):
    monkeypatch.setenv(
        "DIGITAL_HUMAN_LIVESPEAK_EMBED_URL",
        "https://metaperson.avatarsdk.com/livespeak/index.html?mode=raw_stream&framing=bust",
    )
    monkeypatch.delenv("DIGITAL_HUMAN_LIVESPEAK_ALLOWED_ORIGINS", raising=False)
    embed, origin = digital_human._public_livespeak_config()
    assert origin == "https://metaperson.avatarsdk.com"
    assert parse_qs(urlparse(embed).query, keep_blank_values=True) == {
        "mode": ["tts_azure2"], "custom_model": [""], "framing": ["bust"],
    }


@pytest.mark.parametrize(("user", "character", "status"), [
    (None, "david", 401),
    ({"email": "reader@example.test"}, "not-a-character", 404),
    ({"email": "reader@example.test"}, "david", 403),
])
def test_token_endpoint_rejects_unapproved_or_unauthenticated_requests(monkeypatch, user, character, status):
    monkeypatch.delenv("DIGITAL_HUMAN_RELEASE_CERTIFICATE_PATH", raising=False)
    monkeypatch.delenv("DIGITAL_HUMAN_ASSET_MANIFEST_JSON", raising=False)
    monkeypatch.setitem(digital_human._state, "get_session_user", lambda _request: user)
    app = FastAPI()
    app.include_router(digital_human.router)
    with TestClient(app) as client:
        response = client.post(f"/api/v1/digital-human/livespeak/token/{character}")
    assert response.status_code == status
    assert "accessToken" not in response.json()
