"""Topic provenance regression: execute the real registry, retriever and service."""
import pytest

from digital_human.registry import catalog_artifact
from digital_human.scripture import expand_reference, resolve_reference
from digital_human.retrieval import get_retriever
from digital_human.service import DigitalHumanService

pytestmark = pytest.mark.no_db


@pytest.mark.parametrize("character,question,expected", [
    ("david", "撒母耳为什么膏立你？", {"1 Samuel 16:13"}),
    ("david", "撒母耳膏抹大卫的经文在哪里？", {"1 Samuel 16:13"}),
    ("david", "Why did Samuel anoint you?", {"1 Samuel 16:13"}),
    ("saul", "撒母耳为什么膏立你？", {"1 Samuel 10:1"}),
    ("samuel", "你膏立大卫的经文在哪里？", {"1 Samuel 16:13"}),
])
def test_anointing_uses_existing_direct_relationship_evidence(character, question, expected):
    response = DigitalHumanService().answer(character_id=character, question=question).response
    assert {ref.locator for ref in response.references} == expected
    assert all(resolve_reference(ref.locator) for ref in response.references)
    assert response.contentReviewState == "THEOLOGY_REVIEW"
    assert response.speechApproved is False
    assert "david-spare-saul" not in response.relatedEvents
    assert "retrieval-only" in response.warnings
    assert response.relatedEvents == []  # Relationship evidence is not a fabricated topic ID.


@pytest.mark.parametrize("character,question", [
    ("adam", "撒母耳为什么膏立你？"),
    ("david", "亚当为什么膏立你？"),
    ("david", "撒母耳为什么膏立扫罗？"),
    ("david", "你为什么膏立撒母耳？"),
    ("david", "Why did you anoint Samuel?"),
    ("samuel", "大卫为什么膏立你？"),
    ("samuel", "你为什么被大卫膏立？"),
])
def test_unmatched_relation_does_not_fall_back_to_unrelated_lexical_hit(character, question):
    result = DigitalHumanService().answer(character_id=character, question=question)
    assert result.state == "BLOCKED"
    assert not result.response.references


@pytest.mark.parametrize("question", ["你为什么不杀耶和华的受膏者扫罗？", "你为什么不杀受膏的扫罗？", "你为何放过被膏立的扫罗？"])
def test_anointed_title_does_not_replace_the_spare_saul_event(question):
    result = DigitalHumanService().answer(character_id="david", question=question)
    assert {ref.locator for ref in result.response.references} == {"1 Samuel 24", "1 Samuel 26"}


def test_every_exact_catalog_question_keeps_its_own_reference_provenance():
    service = DigitalHumanService()
    executed = 0
    for character in catalog_artifact()["characters"]:
        for topic in character["truthCases"]:
            expected = topic["expected"].get("mustReference") or []
            if not expected or topic["expected"].get("grounding") == "G0_UNSUPPORTED":
                continue
            response = service.answer(character_id=character["id"], question=topic["question"]).response
            canonical = {value for locator in expected for value in expand_reference(locator)}
            hit = get_retriever().retrieve(character["id"], topic["question"])["hits"][0]
            assert hit["truthCaseId"] == topic["id"]
            assert {value for locator in hit["references"] for value in expand_reference(locator)} == canonical
            if "retrieval-only" in response.warnings:
                assert {value for ref in response.references for value in expand_reference(ref.locator)} <= canonical, (character["id"], topic["id"])
            assert response.references
            executed += 1
    assert executed > 300
