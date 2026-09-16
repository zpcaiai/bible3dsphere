"""Lazy accessors for the platform engines used by native handlers."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from ..skill_runtime import SkillInvocationError


def _fail(what: str, exc: Exception) -> SkillInvocationError:
    return SkillInvocationError("HANDLER_ERROR", f"{what} unavailable: {exc}")


@lru_cache(maxsize=1)
def registry() -> Any:
    from ..registry import get_registry

    return get_registry()


@lru_cache(maxsize=1)
def discernment_engine() -> Any:
    try:
        from ..engine import DiscernmentEngine

        return DiscernmentEngine()
    except Exception as exc:  # pragma: no cover - defensive
        raise _fail("DiscernmentEngine", exc) from exc


@lru_cache(maxsize=1)
def dialogue_engine() -> Any:
    try:
        from ..dialogue import DialogueEngine

        return DialogueEngine()
    except Exception as exc:  # pragma: no cover
        raise _fail("DialogueEngine", exc) from exc


@lru_cache(maxsize=1)
def gospel_engine() -> Any:
    try:
        from ..gospel import GospelPathEngine

        return GospelPathEngine()
    except Exception as exc:  # pragma: no cover
        raise _fail("GospelPathEngine", exc) from exc


def case_create(payload: dict[str, Any]) -> Any:
    """Build a validated ``DiscernmentCaseCreate`` from a loose payload."""

    from ..models import ConsentScope, DiscernmentCaseCreate

    raw = dict(payload.get("case") or payload)
    consent = raw.get("consent_scope") or {}
    if not isinstance(consent, ConsentScope):
        consent = ConsentScope(**consent)
    try:
        return DiscernmentCaseCreate(
            title=raw.get("title") or raw.get("topic") or "untitled case",
            subject_type=raw.get("subject_type", "idea"),
            raw_input=raw["raw_input"],
            user_goal=raw.get("user_goal") or "辨识",
            faith_context=raw.get("faith_context", "unknown"),
            consent_scope=consent,
            sensitivity=raw.get("sensitivity", "normal"),
            source_metadata=raw.get("source_metadata", {}),
            source_items=raw.get("source_items", []),
        )
    except KeyError as exc:
        raise SkillInvocationError(
            "MISSING_REQUIRED_INPUT", f"case payload missing {exc}"
        ) from exc
    except Exception as exc:
        raise SkillInvocationError("MODEL_OUTPUT_INVALID", str(exc)) from exc


def pack(kind: str, pack_id: str) -> dict[str, Any]:
    packs = getattr(registry(), f"{kind}_packs")
    if pack_id not in packs:
        raise SkillInvocationError(
            "INSUFFICIENT_EVIDENCE", f"unknown {kind} pack: {pack_id}"
        )
    return {k: v for k, v in packs[pack_id].items() if k != "_asset_dir"}
