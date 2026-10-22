import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import digital_human

pytestmark = pytest.mark.no_db
PAYLOAD = {"characterId": "david", "topicId": "david-goliath"}


def client_for(*, admin=False):
    app = FastAPI()
    digital_human.init_digital_human_router(get_session_user=lambda _request: {"email": "reviewer@example.test"}, is_admin=lambda _email: admin)
    app.include_router(digital_human.router)
    return TestClient(app)


def test_only_platform_admin_can_prepare_or_generate_review_drafts():
    with client_for() as client:
        assert client.post("/api/v1/digital-human/draft-context", json=PAYLOAD).status_code == 403
        assert client.post("/api/v1/digital-human/drafts", json=PAYLOAD).status_code == 403


def test_admin_can_assemble_actual_persona_and_topic_without_model_execution():
    with client_for(admin=True) as client:
        response = client.post("/api/v1/digital-human/draft-context", json=PAYLOAD)
        assert response.status_code == 200
        data = response.json()
        assert data["allowedReferences"] == ["1 Samuel 17"]
        assert data["providerExecution"] == "NOT_RUN"
        assert data["speechApproved"] is False
        assert data["reviewState"] == "THEOLOGY_REVIEW"
        assert "大卫" in data["persona"]
        assert client.post("/api/v1/digital-human/draft-context", json={**PAYLOAD, "topicId": "david-height"}).status_code == 422
        assert client.post("/api/v1/digital-human/draft-context", json={**PAYLOAD, "topicId": "paul-conversion"}).status_code == 422


def test_generation_disabled_by_default_never_substitutes_a_mock(monkeypatch):
    monkeypatch.delenv("DIGITAL_HUMAN_DRAFT_GENERATION_ENABLED", raising=False)
    with client_for(admin=True) as client:
        response = client.post("/api/v1/digital-human/drafts", json=PAYLOAD)
        assert response.status_code == 503
        assert "response" not in response.json()
        assert client.post("/api/v1/digital-human/drafts", json={**PAYLOAD, "question": "private confession"}).status_code == 422
