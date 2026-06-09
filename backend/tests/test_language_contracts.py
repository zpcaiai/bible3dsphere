"""Language contract tests for AI-oriented route helpers."""
import pytest

pytestmark = pytest.mark.no_db


class _Request:
    def __init__(self, lang):
        self.headers = {"X-Lang": lang}


def test_verse_router_adds_english_instruction_for_en_requests():
    from routers.verse import _with_language_instruction

    text = _with_language_instruction("I feel anxious", _Request("en"), bible_refs=True)

    assert "Please respond entirely in natural English." in text
    assert "standard English Bible references" in text


def test_verse_router_keeps_zh_requests_unchanged():
    from routers.verse import _with_language_instruction

    assert _with_language_instruction("我感到焦虑", _Request("zh")) == "我感到焦虑"


def test_verse_prayer_english_fallback_has_no_chinese(monkeypatch):
    import query_emotion_verses as qev

    def fail_llm(**_kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(qev, "_call_llm_with_fallback", fail_llm)

    result = qev.generate_verse_prayer("John 3:16", "For God so loved the world", language="en")

    assert "Lord" in result["prayer"]
    assert not any("\u4e00" <= ch <= "\u9fff" for ch in result["prayer"])


def test_meditation_questions_english_fallback_has_no_chinese(monkeypatch):
    import query_emotion_verses as qev

    def fail_llm(**_kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(qev, "_call_llm_with_fallback", fail_llm)

    result = qev.generate_meditation_questions("John 3:16", "For God so loved the world", language="en")

    assert len(result["questions"]) == 4
    assert "God's character" in result["questions"][0]
    assert not any("\u4e00" <= ch <= "\u9fff" for q in result["questions"] for ch in q)


def test_guidance_english_prompt_replaces_chinese_core_need_rule(monkeypatch):
    import json
    import query_emotion_verses as qev

    captured = {}

    def fake_llm(**kwargs):
        captured["system_prompt"] = kwargs["system_prompt"]
        return json.dumps({
            "core_emotions": ["restless longing"],
            "psychological_assessment": "God sees this ache with compassion.",
            "coping_suggestions": ["You can pray this honestly before God."],
            "spiritual_guidance": "Christ meets you in weakness and gives grace for today.",
            "core_need": "Your soul's deepest longing right now is to rest in God's faithful presence.",
        })

    monkeypatch.setattr(qev.llm_cache, "get", lambda _key: None)
    monkeypatch.setattr(qev.llm_cache, "set", lambda _key, _value: None)
    monkeypatch.setattr(qev, "_call_llm_with_fallback", fake_llm)

    result = qev.assess_psychological_state("I feel anxious", language="en")

    assert result["core_need"].startswith("Your soul's deepest longing right now is")
    assert "你的灵魂此刻最深的渴望是" not in captured["system_prompt"]
    assert not any("\u4e00" <= ch <= "\u9fff" for ch in result["core_need"])
