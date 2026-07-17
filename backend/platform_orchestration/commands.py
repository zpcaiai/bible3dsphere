"""Command validation and adapter registry; target modules retain ownership."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from .contracts import UnifiedCommand


COMMAND_PAYLOAD_FIELDS = {
    "platform_orchestrator": {"title", "duration_minutes", "action_type", "source_reference_id"},
    "prayer": {"title", "duration_minutes", "source_reference_id"},
    "holy_habit": {"title", "duration_minutes", "schedule_hint", "source_reference_id"},
    "attention": {"title", "boundary_type", "duration_minutes", "source_reference_id"},
    "formation_engine": {"title", "practice_type", "duration_minutes", "source_reference_id"},
    "gift_calling": {"title", "reflection_prompt", "source_reference_id"},
    "mission": {"title", "reflection_prompt", "source_reference_id"},
    "crisis": {"route", "source_reference_id"},
}


def validate_command(command: UnifiedCommand, *, confirmation_active: bool, consent_active: bool, now: datetime | None = None) -> list[str]:
    errors: list[str] = []
    now = now or datetime.now(timezone.utc)
    if not confirmation_active:
        errors.append("USER_CONFIRMATION_REQUIRED")
    if not consent_active:
        errors.append("CONSENT_REQUIRED")
    if command.expires_at and command.expires_at <= now:
        errors.append("COMMAND_EXPIRED")
    allowed = COMMAND_PAYLOAD_FIELDS.get(command.target_module)
    if allowed is None:
        errors.append("TARGET_ADAPTER_NOT_REGISTERED")
    else:
        extra = set(command.payload) - allowed
        if extra:
            errors.append("PAYLOAD_FIELDS_NOT_ALLOWED")
    return errors


def execute_registered_command(
    command: UnifiedCommand,
    *,
    confirmation_active: bool,
    consent_active: bool,
    adapters: dict[str, Callable[[UnifiedCommand], dict[str, Any]]],
) -> dict[str, Any]:
    errors = validate_command(command, confirmation_active=confirmation_active, consent_active=consent_active)
    if errors:
        return {"status": "REJECTED", "reason_codes": errors, "target_record_id": None}
    adapter = adapters.get(command.target_module)
    if adapter is None:
        return {"status": "DEGRADED", "reason_codes": ["TARGET_ADAPTER_UNAVAILABLE"], "target_record_id": None}
    result = adapter(command)
    return {"status": result.get("status", "EXECUTED"), "reason_codes": result.get("reason_codes", []), "target_record_id": result.get("target_record_id")}
