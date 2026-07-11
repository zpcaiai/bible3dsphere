"""Stable Mission OS error codes shared by application and API adapters."""

from dataclasses import dataclass
from typing import Any, Mapping

MISSION_NOT_FOUND = "MISSION_NOT_FOUND"
MISSION_FORBIDDEN = "MISSION_FORBIDDEN"
MISSION_CONFLICT = "MISSION_CONFLICT"
MISSION_VALIDATION_ERROR = "MISSION_VALIDATION_ERROR"
MISSION_POLICY_BLOCKED = "MISSION_POLICY_BLOCKED"
MISSION_REVIEW_REQUIRED = "MISSION_REVIEW_REQUIRED"
MISSION_RISK_ESCALATED = "MISSION_RISK_ESCALATED"

ERROR_CODES = frozenset({
    MISSION_NOT_FOUND, MISSION_FORBIDDEN, MISSION_CONFLICT,
    MISSION_VALIDATION_ERROR, MISSION_POLICY_BLOCKED,
    MISSION_REVIEW_REQUIRED, MISSION_RISK_ESCALATED,
})


@dataclass(frozen=True)
class MissionError(Exception):
    code: str
    message: str
    details: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.code not in ERROR_CODES:
            raise ValueError(f"unknown Mission OS error code: {self.code}")
