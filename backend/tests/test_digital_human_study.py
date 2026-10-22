import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from digital_human.registry import catalog_artifact
from digital_human.scripture import resolve_reference
from digital_human.study import study_material
from routers import digital_human

pytestmark = pytest.mark.no_db


def test_all_100_real_character_studies_expose_532_review_pending_topics():
    studies = [study_material(item["id"]) for item in catalog_artifact()["characters"]]
    assert len(studies) == 100
    assert sum(len(item["topics"]) for item in studies) == 532
    assert sum(item["preparedAnswerCount"] for item in studies) == 5
    for study in studies:
        assert study["speechApproved"] is False
        assert study["contentReviewState"] == "THEOLOGY_REVIEW"
        assert study["relationships"]
        for topic in study["topics"]:
            assert topic["speechApproved"] is False
            assert topic["evidenceResolvable"] is bool(topic["references"])
            assert topic["unsupported"] or topic["references"]
            assert all(resolve_reference(ref) for ref in topic["canonicalReferences"])
        for edge in study["relationships"]:
            assert edge["canonicalReferences"]
            assert all(resolve_reference(ref) for ref in edge["canonicalReferences"])


def test_study_keeps_same_name_identity_and_never_promotes_jesus_to_chat():
    assert study_material("mary")["characterId"] != study_material("mary_of_bethany")["characterId"]
    with pytest.raises(KeyError):
        study_material("jesus")


def test_study_http_requires_existing_session_and_rejects_unknown_character():
    app = FastAPI()
    app.include_router(digital_human.router)
    digital_human.init_digital_human_router(get_session_user=lambda _request: None)
    with TestClient(app) as client:
        assert client.get("/api/v1/digital-human/characters/david/study").status_code == 401
        digital_human.init_digital_human_router(get_session_user=lambda _request: {"email": "reader@example.test"})
        response = client.get("/api/v1/digital-human/characters/eve/study")
        assert response.status_code == 200
        assert response.json()["topics"][2]["canonicalReferences"] == ["Genesis 4:1-2", "Genesis 4:25"]
        assert client.get("/api/v1/digital-human/characters/jesus/study").status_code == 404
