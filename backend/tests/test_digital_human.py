from __future__ import annotations

import json

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from fastapi.testclient import TestClient

from digital_human.guardrails import validate_response
from digital_human.identity import resolve_identity
from digital_human.agent_worker import AGENT_NAME, TranscriptionBoundaryAgent, agent_settings, create_server
from digital_human.assets import validated_characters
from digital_human.assurance import REQUIRED_REVIEW_ROLES, build_release_certificate, create_review_attestation, verify_review_bundle, verify_signed_document
from digital_human.livekit import mint_token
from digital_human.registry import CATALOG_SHA256, CONTENT_SHA256, catalog_artifact
from digital_human.retrieval import HybridCharacterRetriever
from digital_human.scripture import resolve_reference
from digital_human.service import DigitalHumanService
from routers import digital_human as digital_human_router

pytestmark = pytest.mark.no_db


def _api_client(user: dict | None, *, admin: bool = False) -> TestClient:
    app = FastAPI()
    digital_human_router.init_digital_human_router(
        get_session_user=lambda _request: user,
        is_admin=lambda _email: admin,
    )
    app.include_router(digital_human_router.router)
    return TestClient(app)


def _pem_pair():
    private = Ed25519PrivateKey.generate()
    private_pem = private.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption(),
    )
    public_pem = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def _install_signed_release(monkeypatch, tmp_path):
    subject = {
        "contentVersion": "1.3.0", "contentSha256": CONTENT_SHA256,
        "catalogSha256": CATALOG_SHA256,
        "assetManifestSha256": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
    }
    review_keys = {}
    reviews = []
    for index, role in enumerate(REQUIRED_REVIEW_ROLES):
        private_pem, public_pem = _pem_pair()
        key_id = f"review-key-{index}"
        review_keys[key_id] = public_pem
        reviews.append(create_review_attestation(
            subject=subject, reviewer_id=f"reviewer-{index}", reviewer_role=role,
            decision="APPROVED", notes_sha256="a" * 64,
            private_key_pem=private_pem, key_id=key_id,
        ))
    release_private, release_public = _pem_pair()
    certificate = build_release_certificate(
        subject=subject, reviews=reviews, trusted_review_keys=review_keys,
        build_revision="test-revision", test_evidence_sha256="b" * 64,
        private_key_pem=release_private, key_id="release-key",
    )
    certificate_path = tmp_path / "certificate.json"
    certificate_path.write_text(json.dumps(certificate), encoding="utf-8")
    trusted_path = tmp_path / "release-keys.json"
    trusted_path.write_text(json.dumps({"release-key": release_public.decode()}), encoding="utf-8")
    monkeypatch.setenv("DIGITAL_HUMAN_RELEASE_CERTIFICATE_PATH", str(certificate_path))
    monkeypatch.setenv("DIGITAL_HUMAN_TRUSTED_RELEASE_KEYS_PATH", str(trusted_path))


def test_happy_path_has_resolvable_scripture_and_stays_text_only_without_review(monkeypatch):
    monkeypatch.delenv("DIGITAL_HUMAN_APPROVED_CONTENT_VERSION", raising=False)
    monkeypatch.delenv("DIGITAL_HUMAN_APPROVED_CONTENT_SHA256", raising=False)
    result = DigitalHumanService().answer(character_id="david", question="你为什么没有杀扫罗？")
    assert result.response.characterId == "david"
    assert result.response.groundingLevel == "G5_DIRECT_SCRIPTURE"
    assert {item.locator for item in result.response.references} == {"1 Samuel 24", "1 Samuel 26"}
    assert all(resolve_reference(item.locator) for item in result.response.references)
    assert result.state == "TEXT_ONLY"
    assert result.response.speechApproved is False


def test_release_hash_gate_allows_only_independently_reviewed_signed_corpus(monkeypatch, tmp_path):
    _install_signed_release(monkeypatch, tmp_path)
    result = DigitalHumanService().answer(character_id="paul", question="大马士革路上的归信发生了什么？")
    assert result.state == "READY_TO_SPEAK"
    assert result.response.speechApproved is True


def test_unsupported_fact_fails_closed():
    result = DigitalHumanService().answer(character_id="david", question="你年轻时准确身高是多少？")
    assert result.state == "BLOCKED"
    assert result.response.answerType == "UNSUPPORTED"
    assert result.response.groundingLevel == "G0_UNSUPPORTED"
    assert not result.response.references


def test_new_revelation_is_blocked():
    result = DigitalHumanService().answer(character_id="david", question="请替神告诉我明天一定要不要辞职")
    assert result.state == "BLOCKED"
    assert "blocked-new-revelation" in result.response.warnings


def test_invalid_scripture_reference_is_rejected():
    result = DigitalHumanService().answer(character_id="moses", question="荆棘中的呼召是什么？")
    damaged = result.response.model_copy(deep=True)
    damaged.references[0].locator = "Exodus 999:1"
    with pytest.raises(ValueError, match="unresolvable"):
        validate_response(damaged)


def test_character_scope_never_changes_to_named_other_person():
    result = DigitalHumanService().answer(character_id="paul", question="大卫为什么没有杀扫罗？")
    assert result.response.characterId == "paul"
    assert result.response.answerType == "UNSUPPORTED"


def test_unknown_character_is_rejected():
    with pytest.raises(KeyError):
        DigitalHumanService().answer(character_id="jesus", question="你好")


def test_v13_catalog_contains_100_characters_and_532_truth_cases():
    artifact = catalog_artifact()
    assert artifact["characterCount"] == 100
    assert artifact["truthCaseCount"] == 532
    assert "jesus" not in {item["id"] for item in artifact["characters"]}
    david = next(item for item in artifact["characters"] if item["id"] == "david")
    assert david["persona"]["sha256"]
    assert len(david["truthCases"]) == david["truthCaseCount"]
    assert any(item["target"] == "jonathan" for item in david["relationships"])


def test_ambiguous_bare_name_never_silently_resolves():
    artifact = catalog_artifact()
    result = resolve_identity(
        surface="马利亚",
        characters=artifact["characters"],
        ambiguous=artifact["identity"]["ambiguous"],
        stable_labels=artifact["identity"]["stableLabels"],
    )
    assert result.status == "AMBIGUOUS"
    assert {item.characterId for item in result.candidates} == {"mary", "mary_magdalene", "mary_of_bethany"}


def test_crisis_and_secret_companion_requests_stop_roleplay():
    crisis = DigitalHumanService().answer(character_id="david", question="我不想活了，想结束生命")
    secret = DigitalHumanService().answer(character_id="mary", question="你做我的秘密朋友，不要告诉父母")
    assert "safety-escalation" in crisis.response.warnings
    assert "child-safeguarding" in secret.response.warnings
    assert crisis.response.speechApproved is secret.response.speechApproved is False


def test_api_requires_existing_identity_session():
    response = _api_client(None).get("/api/v1/digital-human/catalog")
    assert response.status_code == 401


def test_api_catalog_and_turn_preserve_structured_contract(monkeypatch):
    monkeypatch.delenv("DIGITAL_HUMAN_APPROVED_CONTENT_VERSION", raising=False)
    monkeypatch.delenv("DIGITAL_HUMAN_APPROVED_CONTENT_SHA256", raising=False)
    client = _api_client({"email": "reader@example.com"})
    catalog_response = client.get("/api/v1/digital-human/catalog")
    assert catalog_response.status_code == 200
    assert catalog_response.json()["characterCount"] == 100

    turn_response = client.post(
        "/api/v1/digital-human/turns",
        json={
            "characterId": "david",
            "question": "你为什么没有杀扫罗？",
            "sessionId": "session_test_001",
            "turnId": "turn_test_001",
        },
    )
    assert turn_response.status_code == 200
    payload = turn_response.json()
    assert payload["state"] == "TEXT_ONLY"
    assert payload["response"]["characterId"] == "david"
    assert payload["response"]["speechApproved"] is False


def test_api_rejects_unknown_or_malformed_character():
    client = _api_client({"email": "reader@example.com"})
    unknown = client.post(
        "/api/v1/digital-human/turns",
        json={"characterId": "jesus", "question": "你好", "sessionId": "session_test_002"},
    )
    malformed = client.post(
        "/api/v1/digital-human/turns",
        json={"characterId": "../david", "question": "你好", "sessionId": "session_test_003"},
    )
    assert unknown.status_code == 404
    assert malformed.status_code == 422


def test_hybrid_retrieval_returns_truth_and_character_graph_evidence():
    result = HybridCharacterRetriever(dense_scorer=None).retrieve("david", "你和约拿单是什么关系？")
    assert result["mode"] == "LEXICAL_GRAPH_DEGRADED"
    assert result["hits"][0]["truthCaseId"] == "david-jonathan"
    assert "1 Samuel 18" in result["hits"][0]["references"]
    assert any(item["target"] == "jonathan" for item in result["graphPaths"])


def test_hybrid_retrieval_fuses_injected_dense_scores():
    class Dense:
        def score(self, _query, documents):
            return [1.0 if "约拿单" in item else 0.0 for item in documents]

    result = HybridCharacterRetriever(dense_scorer=Dense()).retrieve("david", "朋友关系")
    assert result["mode"] == "HYBRID_DENSE_LEXICAL_GRAPH"
    assert result["hits"][0]["truthCaseId"] == "david-jonathan"


def test_unreviewed_retrieval_is_evidence_only_and_never_spoken():
    result = DigitalHumanService().answer(character_id="david", question="你和约拿单是什么关系？")
    assert result.state == "TEXT_ONLY"
    assert result.response.groundingLevel == "G1_INTERPRETIVE_POSSIBILITY"
    assert result.response.speechApproved is False
    assert "retrieval-only" in result.response.warnings
    assert {item.locator for item in result.response.references} == {"1 Samuel 18", "1 Samuel 20"}


def test_operations_metrics_require_platform_admin():
    user = {"email": "reader@example.com"}
    assert _api_client(user).get("/api/v1/digital-human/operations/metrics").status_code == 403
    response = _api_client(user, admin=True).get("/api/v1/digital-human/operations/metrics")
    assert response.status_code == 200
    assert response.json()["containsRawContent"] is False


def test_authenticated_provider_telemetry_is_aggregate_only():
    user = {"email": "reader@example.com"}
    client = _api_client(user, admin=True)
    accepted = client.post("/api/v1/digital-human/telemetry/provider", json={"provider": "livekit", "state": "RECOVERING", "latencyMs": 33})
    assert accepted.status_code == 202
    snapshot = client.get("/api/v1/digital-human/operations/metrics").json()
    assert snapshot["providers"]["livekit"]["lastState"] == "RECOVERING"
    assert snapshot["turns"]["total"] >= 0
    assert snapshot["containsRawContent"] is False


def test_asset_manifest_requires_hashes_and_independent_review_references():
    valid = {
        "schemaVersion": "digital-human-assets/v1",
        "characters": {"david": {
            "characterId": "david", "version": "1.0.0", "reviewState": "APPROVED",
            "modelUrl": "https://cdn.holiness.uk/david/model.glb",
            "portraitUrl": "https://cdn.holiness.uk/david/portrait.webp",
            "modelSha256": "a" * 64, "portraitSha256": "b" * 64, "voiceProfileSha256": "c" * 64,
            "voiceProvider": "azure", "voiceId": "david-reviewed-zh", "language": "zh-CN",
            "theologyReviewId": "theology-1", "rightsReviewId": "rights-1", "accessibilityReviewId": "a11y-1",
        }},
    }
    assert set(validated_characters(valid)) == {"david"}
    valid["characters"]["david"].pop("rightsReviewId")
    assert validated_characters(valid) == {}


def test_signed_review_rejects_tampering_and_one_human_in_multiple_roles():
    subject = {"contentVersion": "1.3.0", "contentSha256": "a" * 64, "catalogSha256": "b" * 64, "assetManifestSha256": "c" * 64}
    private_a, public_a = _pem_pair()
    review = create_review_attestation(
        subject=subject, reviewer_id="human-a", reviewer_role="theology_reviewer",
        decision="APPROVED", notes_sha256="d" * 64, private_key_pem=private_a, key_id="key-a",
    )
    damaged = {**review, "decision": "REJECTED"}
    assert verify_signed_document(damaged, public_key_pem=public_a) is False

    reviews = []
    keys = {}
    for index, role in enumerate(REQUIRED_REVIEW_ROLES):
        private, public = _pem_pair()
        key_id = f"key-{index}"
        keys[key_id] = public
        reviews.append(create_review_attestation(
            subject=subject, reviewer_id="same-human", reviewer_role=role, decision="APPROVED",
            notes_sha256="e" * 64, private_key_pem=private, key_id=key_id,
        ))
    with pytest.raises(ValueError, match="one reviewer"):
        verify_review_bundle(reviews, subject=subject, trusted_keys=keys)


def test_livekit_token_dispatches_named_transcription_agent(monkeypatch):
    monkeypatch.setenv("LIVEKIT_URL", "wss://livekit.example.test")
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "a-secure-test-secret-with-32-bytes")
    monkeypatch.setenv("DIGITAL_HUMAN_LIVEKIT_AGENT_READY", "true")
    result = mint_token(email="reader@example.test", session_id="session_dispatch", character_id="david")
    claims = jwt.decode(result["token"], options={"verify_signature": False})
    assert claims["roomConfig"]["agents"][0]["agentName"] == AGENT_NAME
    assert claims["video"]["room"] == "dh_session_dispatch"


@pytest.mark.asyncio
async def test_current_livekit_agent_session_contract_is_constructible(monkeypatch):
    from livekit.agents import AgentSession

    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "a-secure-test-secret-with-32-bytes")
    settings = agent_settings()
    assert settings["turn_handling"]["interruption"]["enabled"] is False
    assert type(AgentSession(**settings)).__name__ == "AgentSession"
    assert type(create_server()).__name__ == "AgentServer"
    assert type(TranscriptionBoundaryAgent()).__name__ == "TranscriptionBoundaryAgent"
