"""Framework-free, versioned domain-event envelope."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

from .ids import TenantId, UserId


@dataclass(frozen=True)
class DomainEvent:
    event_id: str
    event_type: str
    event_version: int
    tenant_id: TenantId
    occurred_at: datetime
    actor_id: UserId
    aggregate_id: str
    correlation_id: str
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.event_version < 1:
            raise ValueError("event_version must be positive")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
