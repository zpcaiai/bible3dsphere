"""
AI Reasoning — LLM Fusion Layer

Responsibility:
  - Receive all 3 service outputs (semantic, structural, temporal)
  - Build structured prompt context
  - Run LLM reasoning call
  - Parse and return structured output

This is the ONLY place LLM calls are made for the main reasoning pipeline.
Prompt templates come from packages/prompts.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


async def run_fusion_reasoning(
    req: Any,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute LLM fusion reasoning over the full multi-layer context.

    Args:
        req:     DecisionRequest (user input)
        context: dict with keys: semantic, structural, temporal

    Returns:
        dict with: summary, guidance, reflective_questions, confidence, disclaimer
    """
    try:
        from packages.config.connections import get_openai_client
        from packages.config.settings import settings
        from packages.prompts.system_prompt import get_prompt

        client = get_openai_client()
        if not client:
            return _offline_fallback(context)

        system_prompt = get_prompt("discernment_system", "v3.1")
        user_content  = _build_user_content(req, context)

        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system",  "content": system_prompt},
                {"role": "user",    "content": user_content},
            ],
            temperature=0.4,
            max_tokens=600,
        )

        raw = response.choices[0].message.content or ""
        return {
            "summary":             raw[:500],
            "schema":              "v3.1",
            "confidence":          0.72,   # fixed mid-range — never claim precision
            "layers_used":         ["semantic", "structural", "temporal"],
            "disclaimer":          (
                "This synthesis describes possible patterns only. "
                "It is not a diagnosis, prediction, or authority statement."
            ),
        }

    except Exception as exc:
        logger.warning("[reasoning-fusion] LLM call failed: %s", exc)
        return _offline_fallback(context)


def _build_user_content(req: Any, context: Dict[str, Any]) -> str:
    semantic   = context.get("semantic", {})
    structural = context.get("structural", {})
    temporal   = context.get("temporal", {})

    principles = semantic.get("principles", [])
    loops      = structural.get("loops", [])
    trends     = temporal.get("trends", {})

    lines = [
        f"Decision context: {getattr(req, 'description', '')[:200]}",
        f"Category: {getattr(req, 'category', 'unknown')}",
        f"Dominant motive: {getattr(req, 'dominant_motive', 'unknown')}",
        "",
        f"Active emotional loops: {json.dumps(loops[:3])}",
        f"Temporal trends: {json.dumps(trends)}",
        f"Top principles: {json.dumps([p.get('principle_en', '') for p in principles[:3]])}",
    ]

    reflection = getattr(req, "reflection_notes", "")
    if reflection:
        lines.append(f"\nUser reflection: {reflection[:200]}")

    return "\n".join(lines)


def _offline_fallback(context: Dict[str, Any]) -> Dict[str, Any]:
    """Return a graceful offline response when LLM is unavailable."""
    return {
        "summary": (
            "Structural patterns and temporal trends have been analyzed. "
            "LLM reasoning is currently unavailable — "
            "please review the structural and temporal layers directly."
        ),
        "schema":     "v3.1",
        "confidence": 0.0,
        "offline":    True,
        "disclaimer": (
            "Offline mode: LLM fusion unavailable. "
            "Structural and temporal data are still available."
        ),
    }
