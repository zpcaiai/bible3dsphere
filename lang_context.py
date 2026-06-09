"""Per-request UI language propagation for AI content generation.

The mobile app / web client signal the desired output language with the
``?lang=`` query parameter and/or an ``X-Lang`` header (values like ``en`` or
``zh-CN``). An ASGI middleware records the requested language in a ContextVar
so every LLM helper (sync, async, threadpool or background task) can localize
output without threading a ``request`` object through the whole codebase.

Only explicit signals (``X-Lang`` and ``?lang=``) are honoured; the browser's
automatic ``Accept-Language`` header is intentionally ignored.
"""
from __future__ import annotations

import contextvars
from urllib.parse import parse_qs

current_lang = contextvars.ContextVar("current_lang", default="zh")

ENGLISH_DIRECTIVE = (
    "CRITICAL OUTPUT-LANGUAGE REQUIREMENT: Respond ENTIRELY in natural, fluent "
    "English. Every part of the output - including all JSON string values, "
    "titles, lists, prayers and Scripture quotations - must be written in "
    "English. Use standard English Bible book names and references (e.g. "
    "'John 3:16'). Do not include any Chinese characters."
)


import re as _re

# Chinese "answer in Chinese" directives that appear hard-coded in prompts;
# when English is requested we rewrite them so they do not fight the English
# directive (recency alone is not reliable when the body insists on Chinese).
_ZH_LANG_PATTERNS = [
    "回应使用中文", "回复使用中文", "语言使用中文", "请使用中文", "请用中文作答",
    "请用中文回答", "请用中文", "用简体中文回答", "用简体中文", "用繁体中文",
    "使用简体中文", "使用中文", "以中文", "用中文回答", "用中文回应", "用中文",
    "中文回答", "全部用中文", "务必用中文",
]

def _force_english_text(prompt: str) -> str:
    """Rewrite hard-coded Chinese-language directives to English, then append
    the strong English directive. Used only when EN is requested."""
    text = prompt or ""
    for pat in _ZH_LANG_PATTERNS:
        text = text.replace(pat, "Respond entirely in English")
    # Catch leftover generic forms like "...，中文，..." length limits etc.
    text = _re.sub(r"(?:请)?(?:务必|一律|全部)?(?:使用|用|以)\s*中文", "Respond in English", text)
    return text.rstrip() + "\n\n" + ENGLISH_DIRECTIVE


def _is_en(value) -> bool:
    return bool(value) and str(value).strip().lower().startswith("en")


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
    for m in out:
        if m.get("role") == "system":
            m["content"] = _force_english_text(m.get("content") or "")
            return out
    out.insert(0, {"role": "system", "content": ENGLISH_DIRECTIVE})
    return out


def lang_from_scope(scope) -> str:
    try:
        headers = {
            k.decode("latin-1").lower(): v.decode("latin-1")
            for k, v in scope.get("headers", [])
        }
    except Exception:
        headers = {}
    x_lang = headers.get("x-lang")
    lang_q = None
    try:
        q = parse_qs(scope.get("query_string", b"").decode("latin-1"))
        lang_q = (q.get("lang") or [None])[0]
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
