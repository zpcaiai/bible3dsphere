"""Technical-only integration health and small circuit breaker."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    recovery_seconds: int = 60
    failures: int = 0
    opened_at: datetime | None = None

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self, *, now: datetime | None = None) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = now or datetime.now(timezone.utc)

    def state(self, *, now: datetime | None = None) -> str:
        if self.opened_at is None:
            return "CLOSED"
        now = now or datetime.now(timezone.utc)
        if now >= self.opened_at + timedelta(seconds=self.recovery_seconds):
            return "HALF_OPEN"
        return "OPEN"


def integration_status(*, registered: bool, feature_enabled: bool, adapter_available: bool, recent_failures: int = 0) -> tuple[str, list[str]]:
    if not registered:
        return "NOT_REGISTERED", ["CAPABILITY_NOT_REGISTERED"]
    if not feature_enabled:
        return "DISABLED", ["FEATURE_FLAG_DISABLED"]
    if not adapter_available:
        return "DEGRADED", ["SOURCE_ADAPTER_UNAVAILABLE"]
    if recent_failures:
        return "DEGRADED", ["RECENT_TECHNICAL_FAILURES"]
    return "HEALTHY", []
