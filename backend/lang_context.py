"""Per-request UI language propagation for AI content generation."""
from __future__ import annotations

import contextvars
import re as _re
from urllib.parse import parse_qs

current_lang = contextvars.ContextVar("current_lang", default="zh")

ENGLISH_DIRECTIVE = (
    "CRITICAL OUTPUT-LANGUAGE REQUIREMENT: Respond ENTIRELY in natural, fluent "
    "English. Every part of the output - including all JSON string values, "
    "titles, lists, prayers and Scripture quotations - must be written in "
    "English. Use standard English Bible book names and references (e.g. "
    "'John 3:16'). Do not include any Chinese characters."
)

_ZH_LANG_PATTERNS = [
    "回应使用中文", "回复使用中文", "语言使用中文", "请使用中文", "请用中文作答",
    "请用中文回答", "请用中文", "用简体中文回答", "用简体中文", "用繁体中文",
    "使用简体中文", "使用中文", "以中文", "用中文回答", "用中文回应", "用中文",
    "中文回答", "全部用中文", "务必用中文",
]


def _is_en(value) -> bool:
    return bool(value) and str(value).strip().lower().startswith("en")


def _force_english_text(prompt: str) -> str:
    text = prompt or ""
    for pattern in _ZH_LANG_PATTERNS:
        text = text.replace(pattern, "Respond entirely in English")
    text = _re.sub(r"(?:请)?(?:务必|一律|全部)?(?:使用|用|以)\s*中文", "Respond in English", text)
    return text.rstrip() + "\n\n" + ENGLISH_DIRECTIVE


def get_lang() -> str:
    return current_lang.get()


def set_lang(lang: str):
    return current_lang.set("en" if _is_en(lang) else "zh")


def is_english() -> bool:
    try:
        return current_lang.get() == "en"
    except Exception:
        return False


def english_suffix() -> str:
    return (
        "\n\n(Please respond entirely in natural English, using standard "
        "English Bible references.)"
        if is_english()
        else ""
    )


def localize_system_prompt(system_prompt: str) -> str:
    if is_english():
        return _force_english_text(system_prompt)
    return system_prompt


def apply_lang_messages(messages):
    if not is_english():
        return messages
    out = [dict(m) for m in messages]
    for message in out:
        if message.get("role") == "system":
            message["content"] = _force_english_text(message.get("content") or "")
            return out
    out.insert(0, {"role": "system", "content": ENGLISH_DIRECTIVE})
    return out


def lang_from_scope(scope) -> str:
    try:
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
    except Exception:
        headers = {}
    x_lang = headers.get("x-lang")
    lang_q = None
    try:
        query = parse_qs(scope.get("query_string", b"").decode("latin-1"))
        lang_q = (query.get("lang") or [None])[0]
    except Exception:
        pass
    if _is_en(x_lang) or _is_en(lang_q):
        return "en"
    return "zh"


class LanguageMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            token = current_lang.set(lang_from_scope(scope))
            try:
                await self.app(scope, receive, send)
            finally:
                current_lang.reset(token)
            return
        await self.app(scope, receive, send)
