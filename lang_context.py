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
        return (system_prompt or "").rstrip() + "\n\n" + ENGLISH_DIRECTIVE
    return system_prompt


def apply_lang_messages(messages):
    if not is_english():
        return messages
    out = [dict(m) for m in messages]
    for m in out:
        if m.get("role") == "system":
            m["content"] = (((m.get("content") or "").rstrip()) + "\n\n" + ENGLISH_DIRECTIVE).strip()
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
