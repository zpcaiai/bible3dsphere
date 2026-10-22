import pytest
from pydantic import ValidationError

from digital_human.drafts import DraftCandidate, draft_context, generate_review_draft, validate_draft
from digital_human.registry import catalog_artifact

pytestmark = pytest.mark.no_db


def test_real_context_assembly_for_every_supported_catalog_topic_without_user_history():
    count = 0
    for character in catalog_artifact()["characters"]:
        for topic in character["truthCases"]:
            if topic["expected"].get("grounding") == "G0_UNSUPPORTED" or not topic["expected"].get("mustReference"):
                continue
            context = draft_context(character["id"], topic["id"])
            count += 1
            assert context["allowedReferences"] == topic["expected"]["mustReference"]
            assert context["personaSha256"] == character["persona"]["sha256"]
            assert context["speechApproved"] is False
            assert "history" not in context
    assert count == 356


def test_validating_a_candidate_never_claims_model_execution_or_content_approval():
    context = draft_context("david", "david-goliath")
    candidate = DraftCandidate(characterId="david", topicId="david-goliath", claims=[{"statement": "请核对这项陈述是否被经文支持。", "references": ["1 Samuel 17"]}])
    result = validate_draft(candidate, context)
    assert result["response"]["speechApproved"] is False
    assert result["reviewState"] == "THEOLOGY_REVIEW"
    assert result["claimVerification"] == "HUMAN_REVIEW_REQUIRED"
    assert "providerExecution" not in result
    assert len(result["draftSha256"]) == 64


@pytest.mark.parametrize("patch", [
    {"characterId": "paul"}, {"topicId": "david-height"},
    {"claims": [{"statement": "伪造引用", "references": ["Genesis 1:1"]}]},
    {"claims": [{"statement": "错误章节", "references": ["1 Samuel 999:1"]}]},
    {"claims": [{"statement": "神现在告诉你秘密启示", "references": ["1 Samuel 17"]}]},
])
def test_candidate_identity_evidence_and_revelation_fail_closed(patch):
    data = {"characterId": "david", "topicId": "david-goliath", "claims": [{"statement": "待审核陈述", "references": ["1 Samuel 17"]}], **patch}
    with pytest.raises(ValueError):
        validate_draft(DraftCandidate.model_validate(data), draft_context("david", "david-goliath"))


def test_mock_inference_is_never_used_when_the_real_generation_gate_is_closed(monkeypatch):
    monkeypatch.delenv("DIGITAL_HUMAN_DRAFT_GENERATION_ENABLED", raising=False)
    with pytest.raises(RuntimeError, match="disabled"):
        generate_review_draft("david", "david-goliath")
    with pytest.raises(ValueError, match="unsupported"):
        draft_context("david", "david-height")
    with pytest.raises(ValidationError):
        DraftCandidate.model_validate({"characterId": "david", "topicId": "david-goliath", "claims": [], "speechApproved": True})


def test_explicit_enable_still_rejects_the_existing_mock_factory_without_inference(monkeypatch):
    from dataclasses import replace
    import llm_provider
    if llm_provider._settings is not None:
        monkeypatch.setattr(llm_provider, "_settings", replace(llm_provider._settings, agent_mode="mock"))
    monkeypatch.setenv("DIGITAL_HUMAN_DRAFT_GENERATION_ENABLED", "true")
    with pytest.raises(RuntimeError, match="real explicitly configured model"):
        generate_review_draft("david", "david-goliath")
