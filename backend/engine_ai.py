"""
engine_ai.py — shared AI entrypoint for the per-topic engine family.

Historically every ``*_engine.py`` carried a near-identical ``_call_ai`` helper
that tried, in order:

    waiting_engine.call_ai_provider(prompt)      # expects a *messages list*, not a str
    llm_provider.call_llm(prompt)                # a function that never existed

Passing a raw prompt string to ``call_ai_provider`` (which builds
``{"messages": <str>}``) produced an HTTP 400, and ``llm_provider.call_llm``
resolved to ``None`` via ``getattr`` — so ``use_ai=True`` never actually reached
a model.  This module gives the engines a single, correct entrypoint.

``call_ai(prompt, settings=None)`` returns the model's **raw text** (a JSON
string for the engines to parse) or ``None`` on any failure, so callers keep
their deterministic fallback.  It prefers the real Gemini/SiliconFlow/DeepSeek
path (``waiting_engine.call_ai_provider`` with a properly-shaped messages list)
and falls back to the unified provider (``llm_provider.complete_text``) when a
real provider is configured there instead.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def _import(name: str):
    """Import a sibling module tolerating both ``backend.x`` and top-level ``x``."""
    try:
        return __import__(f"backend.{name}", fromlist=[name])
    except Exception:
        try:
            return __import__(name)
        except Exception:
            return None


def call_ai(prompt: str, settings: Any = None, *,
            temperature: float = 0.3,
            max_tokens: Optional[int] = None) -> Optional[str]:
    """Single-shot completion from a raw prompt string.

    Returns the model text (typically a JSON blob for the engine to parse) or
    ``None`` on any failure / when no real provider is configured.
    """
    if prompt is None:
        return None
    text = prompt if isinstance(prompt, str) else str(prompt)
    if not text.strip():
        return None
    messages: List[Dict[str, str]] = [{"role": "user", "content": text}]

    # 1) Real Gemini / SiliconFlow / DeepSeek via the existing provider helper.
    #    call_ai_provider returns parsed JSON (dict) or None; it returns None
    #    immediately when no such keys are configured, so this is cheap.
    cap = _import("waiting_engine")
    if cap is not None:
        fn = getattr(cap, "call_ai_provider", None)
        if fn is not None:
            try:
                out = fn(messages, settings=settings)
            except Exception:
                out = None
            if isinstance(out, dict) and out:
                try:
                    return json.dumps(out, ensure_ascii=False)
                except Exception:
                    return str(out)
            if isinstance(out, str) and out.strip():
                return out

    # 2) Unified provider (real OpenAI / Anthropic / local).  Only used when a
    #    real provider is configured — we never surface Mock text into engines,
    #    preserving the original "no mock enhancement" behaviour.
    lp = _import("llm_provider")
    if lp is not None:
        real = getattr(lp, "_real_configured", None)
        complete_text = getattr(lp, "complete_text", None)
        if complete_text is not None and (real is None or real()):
            try:
                out = complete_text(text, temperature=temperature, max_tokens=max_tokens)
            except Exception:
                out = None
            if isinstance(out, str) and out.strip():
                return out

    return None
