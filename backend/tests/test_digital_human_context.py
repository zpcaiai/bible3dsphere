import pytest

from digital_human.registry import catalog_artifact
from digital_human.scripture import resolve_reference
from digital_human.service import DigitalHumanService

pytestmark = pytest.mark.no_db


def test_all_532_real_questions_execute_and_unsupported_cases_never_become_facts():
    service = DigitalHumanService()
    executed = 0
    for character in catalog_artifact()["characters"]:
        for case in character["truthCases"]:
            result = service.answer(character_id=character["id"], question=case["question"])
            executed += 1
            assert result.response.characterId == character["id"]
            assert all(resolve_reference(ref.locator) for ref in result.response.references)
            if case["expected"].get("grounding") == "G0_UNSUPPORTED" or not case["expected"].get("mustReference"):
                assert result.state == "BLOCKED", (character["id"], case["id"])
                assert result.response.speechApproved is False
            else:
                assert result.state == "TEXT_ONLY", (character["id"], case["id"], result.response.warnings)
                assert result.response.references
                assert "safety-escalation" not in result.response.warnings
    assert executed == 532


def test_pharaoh_keyword_does_not_override_unsupported_catalog_question():
    result = DigitalHumanService().answer(character_id="moses", question="出埃及时的法老到底是谁？")
    assert result.state == "BLOCKED"
    assert result.response.groundingLevel == "G0_UNSUPPORTED"


@pytest.mark.parametrize("character_id,question", [
    ("moses", "请问出埃及时的法老到底是谁？"),
    ("moses", "我想了解：出埃及时的法老到底是谁？"),
    ("david", "你真实的外貌是什么样，和歌利亚战斗时有多高？"),
    ("david", "和歌利亚战斗的时候你身高多高？"),
])
def test_non_exact_unsupported_intent_cannot_become_prepared_speech(character_id, question):
    result = DigitalHumanService().answer(character_id=character_id, question=question)
    assert result.state == "BLOCKED"
    assert result.response.speechApproved is False


def test_historical_violence_is_not_user_crisis_but_personal_crisis_still_is():
    service = DigitalHumanService()
    history = service.answer(character_id="john_baptist", question="你为什么被希律囚禁并最终被杀？")
    assert {ref.locator for ref in history.response.references} == {"Mark 6:17-29"}
    assert history.state == "TEXT_ONLY"
    personal = service.answer(character_id="john_baptist", question="我想伤害自己，结束生命。你为什么被希律囚禁并最终被杀？")
    assert "safety-escalation" in personal.response.warnings
    assert personal.state == "BLOCKED"


def test_explicit_followup_uses_only_real_character_topic_evidence():
    service = DigitalHumanService()
    first = service.answer(character_id="moses", question="荆棘中的呼召是什么？")
    assert first.response.relatedEvents == ["moses-burning-bush"]
    followup = service.answer(character_id="moses", question="相关经文呢？", context_topic_ids=first.response.relatedEvents)
    assert "session-topic-context" in followup.response.warnings
    assert {ref.locator for ref in followup.response.references} == {"Exodus 3", "Exodus 4:1-17"}
    assert followup.response.speechApproved is False


def test_context_is_not_a_license_to_rewrite_or_bypass_current_question():
    service = DigitalHumanService()
    crisis = service.answer(character_id="david", question="我想伤害自己", context_topic_ids=["david-goliath"])
    assert crisis.state == "BLOCKED"
    unrelated = service.answer(character_id="david", question="你年轻时准确身高是多少？", context_topic_ids=["david-goliath"])
    assert unrelated.state == "BLOCKED"
    unsupported = service.answer(character_id="david", question="相关经文呢？", context_topic_ids=["david-height"])
    assert unsupported.state == "BLOCKED"


@pytest.mark.parametrize("topics", [["paul-conversion"], ["made-up-proof"], ["david-goliath"] * 5])
def test_cross_character_fabricated_or_oversized_context_is_rejected(topics):
    with pytest.raises(ValueError, match="context topics"):
        DigitalHumanService().answer(character_id="david", question="相关经文呢？", context_topic_ids=topics)


def test_regular_new_topic_does_not_inherit_previous_topic():
    result = DigitalHumanService().answer(character_id="david", question="你和约拿单是什么关系？", context_topic_ids=["david-goliath"])
    assert "session-topic-context" not in result.response.warnings
    assert "1 Samuel 20" in {ref.locator for ref in result.response.references}
