"""Shared helpers for native skill handlers."""

from __future__ import annotations

import dataclasses
from typing import Any

from ..skill_runtime import SkillInvocationError

Payload = dict[str, Any]


def require(payload: Payload, *keys: str) -> tuple[Any, ...]:
    missing = [key for key in keys if payload.get(key) in (None, "", [], {})]
    if missing:
        raise SkillInvocationError(
            "MISSING_REQUIRED_INPUT", f"missing required input(s): {missing}"
        )
    return tuple(payload[key] for key in keys)


def dumped(value: Any) -> Any:
    """Serialise pydantic models / dataclasses / enums into plain JSON types."""

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "as_dict"):
        return value.as_dict()
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {key: dumped(item) for key, item in dataclasses.asdict(value).items()}
    if hasattr(value, "value") and hasattr(value, "name"):
        return value.value
    if isinstance(value, list):
        return [dumped(item) for item in value]
    if isinstance(value, tuple):
        return [dumped(item) for item in value]
    if isinstance(value, dict):
        return {key: dumped(item) for key, item in value.items()}
    return value


def steps_from(contract: Any) -> list[str]:
    return list(contract.processing_contract)
