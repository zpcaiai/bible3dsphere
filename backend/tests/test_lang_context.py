"""Tests for request-scoped language context helpers."""
import pytest

pytestmark = pytest.mark.no_db


def test_apply_lang_messages_adds_english_system_instruction():
    import lang_context

    token = lang_context.set_lang("en")
    try:
        messages = [{"role": "user", "content": "Help me"}]
        localized = lang_context.apply_lang_messages(messages)
    finally:
        lang_context.current_lang.reset(token)

    assert localized[0]["role"] == "system"
    assert "Respond ENTIRELY" in localized[0]["content"]
    assert "Do not include any Chinese characters" in localized[0]["content"]
    assert messages == [{"role": "user", "content": "Help me"}]


def test_localize_system_prompt_keeps_chinese_default():
    import lang_context

    assert lang_context.localize_system_prompt("系统提示") == "系统提示"
