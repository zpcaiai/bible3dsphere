"""Shared safety gate. Crisis Care remains the authoritative target."""
from __future__ import annotations

from dataclasses import dataclass


ORDINARY_OPERATIONS = {
    "DAILY_MIRROR", "CREATE_HABIT", "FORMATION_CHAIN", "CALLING_PLAN",
    "MISSION_PLAN", "LONG_TERM_PATTERN", "PASTORAL_BRIEF", "MULTI_ACTION_PLAN",
}


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    route: str
    reason_codes: tuple[str, ...]
    allowed_operations: tuple[str, ...]


def safety_gate(safety_state: str, operation: str) -> SafetyDecision:
    state = (safety_state or "NONE").upper()
    if state in {"ELEVATED", "IMMINENT"}:
        allowed = (
            "CRISIS_CARE", "SAFETY_PLAN", "HUMAN_CONNECTION", "PROFESSIONAL_SUPPORT",
            "BRIEF_USER_REQUESTED_PRAYER", "SIMPLE_INFORMATION",
        )
        return SafetyDecision(
            allowed=operation in allowed,
            route="crisis",
            reason_codes=("CRISIS_AUTHORITY_OVERRIDE", "ORDINARY_WORKFLOW_STOPPED"),
            allowed_operations=allowed,
        )
    return SafetyDecision(True, "requested_workflow", ("SAFETY_GATE_PASSED",), tuple(ORDINARY_OPERATIONS))
