import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import digital_human

pytestmark = pytest.mark.no_db


@pytest.fixture
def client():
    app = FastAPI()
    digital_human.init_digital_human_router(get_session_user=lambda _request: {"email": "reader@example.test"})
    app.include_router(digital_human.router)
    with TestClient(app) as value:
        yield value


def test_followup_http_uses_topic_identifier_and_returns_actual_evidence(client):
    response = client.post("/api/v1/digital-human/turns", json={
        "characterId": "david", "question": "相关经文呢？",
        "context": {"characterId": "david", "topicIds": ["david-jonathan"]},
    })
    assert response.status_code == 200
    answer = response.json()["response"]
    assert "session-topic-context" in answer["warnings"]
    assert {ref["locator"] for ref in answer["references"]} == {"1 Samuel 18", "1 Samuel 20"}
    assert answer["speechApproved"] is False


@pytest.mark.parametrize("patch", [
    {"context": {"characterId": "paul", "topicIds": ["paul-conversion"]}},
    {"context": {"characterId": "david", "topicIds": ["paul-conversion"]}},
    {"context": {"characterId": "david", "topicIds": ["david-goliath"], "speechApproved": True}},
    {"context": {"characterId": "david", "topicIds": ["david-goliath"] * 5}},
    {"question": "   "},
])
def test_untrusted_context_and_blank_question_are_rejected(client, patch):
    response = client.post("/api/v1/digital-human/turns", json={"characterId": "david", "question": "出处呢？", **patch})
    assert response.status_code == 422
