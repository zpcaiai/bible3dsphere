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
    existing_topic = {"samuel": "samuel-05-case", "saul": "saul-01-case"}.get(character)
    assert response.relatedEvents == ([existing_topic] if existing_topic else [])
    # A relationship can carry an existing topic only when its actual evidence
    # is contained in that topic; David has no such catalogue case.
    if existing_topic:
        profile = next(item for item in catalog_artifact()["characters"] if item["id"] == character)
        topic = next(item for item in profile["truthCases"] if item["id"] == existing_topic)
        assert topic["expected"]["mustReference"] == (
            ["1 Samuel 16:1-13"] if character == "samuel" else ["1 Samuel 9", "1 Samuel 10"]
        )


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


@pytest.mark.parametrize("character,question,expected", [
    ("moses", "过红海的记载是什么？", {"Exodus 14"}),
    ("moses", "请问你们是如何过红海的？", {"Exodus 14"}),
    ("peter", "五旬节那天发生了什么？", {"Acts 2:14-41"}),
    ("paul", "你的第一次宣教旅程去了哪里？", {"Acts 13", "Acts 14"}),
    ("ruth", "请问你为什么到波阿斯田里拾穗？", {"Ruth 2"}),
])
def test_question_boilerplate_does_not_hide_the_existing_topic(character, question, expected):
    response = DigitalHumanService().answer(character_id=character, question=question).response
    assert {ref.locator for ref in response.references} == expected
    assert response.contentReviewState == "THEOLOGY_REVIEW"
    assert response.speechApproved is False


def test_shared_question_wording_cannot_make_ten_plagues_a_burning_bush_question():
    result = DigitalHumanService().answer(character_id="moses", question="十灾与出埃及发生了什么？")
    # No ten-plagues truth case exists. Refusal must not become unrelated proof.
    assert result.state == "BLOCKED"
    assert result.response.references == []
    assert result.response.relatedEvents == []


@pytest.mark.parametrize("character,question,expected", [
    ("moses", "过红海的记载是什么？", {"Exodus 14"}),
    ("peter", "你为什么在海面上沉下去？", {"Matthew 14:28-31"}),
    ("paul", "你为什么与巴拿巴分开？", {"Acts 15:36-41"}),
    ("ruth", "你为什么到波阿斯田里拾穗？", {"Ruth 2"}),
    ("abraham", "神与你立约包括哪些内容？", {"Genesis 15", "Genesis 17"}),
    ("samuel", "你为什么膏立大卫？", {"1 Samuel 16:1-13"}),
    ("saul", "撒母耳为什么膏立你？", {"1 Samuel 9", "1 Samuel 10"}),
])
def test_natural_sequential_followups_keep_only_the_active_evidenced_topic(character, question, expected):
    service = DigitalHumanService()
    response = service.answer(character_id=character, question=question).response
    assert response.relatedEvents
    for followup in ["相关经文呢？", "这些经文的出处呢？", "请再详细解释一下吗？", "再解释一下"]:
        response = service.answer(character_id=character, question=followup, context_topic_ids=response.relatedEvents).response
        assert {ref.locator for ref in response.references} == expected
        assert "session-topic-context" in response.warnings
        assert response.speechApproved is False
        assert response.contentReviewState == "THEOLOGY_REVIEW"


def test_followups_without_context_never_select_an_arbitrary_new_topic():
    service = DigitalHumanService()
    for character in catalog_artifact()["characters"]:
        result = service.answer(character_id=character["id"], question="这些经文的出处呢？")
        assert result.state == "BLOCKED", character["id"]
        assert result.response.references == []
        assert result.response.relatedEvents == []


def test_all_catalogue_topics_execute_two_followups_without_changing_provenance():
    service = DigitalHumanService()
    executed = 0
    for character in catalog_artifact()["characters"]:
        for topic in character["truthCases"]:
            previous = service.answer(character_id=character["id"], question=topic["question"]).response
            for question in ["相关经文呢？", "这些经文的出处呢？"]:
                response = service.answer(character_id=character["id"], question=question, context_topic_ids=previous.relatedEvents).response
                expected = topic["expected"].get("mustReference") or []
                if not expected or topic["expected"].get("grounding") == "G0_UNSUPPORTED":
                    assert response.groundingLevel == "G0_UNSUPPORTED", (character["id"], topic["id"])
                    assert response.references == []
                else:
                    canonical = {ref for locator in expected for ref in expand_reference(locator)}
                    actual = {ref for reference in response.references for ref in expand_reference(reference.locator)}
                    assert actual == canonical, (character["id"], topic["id"], question)
                assert response.speechApproved is False
                previous = response
                executed += 1
    assert executed == 1064
