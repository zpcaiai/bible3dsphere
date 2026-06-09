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
