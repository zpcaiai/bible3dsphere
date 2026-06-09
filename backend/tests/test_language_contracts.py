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
