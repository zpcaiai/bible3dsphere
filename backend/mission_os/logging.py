"""Redacted structured logging context; narrative values are never accepted."""

from dataclasses import asdict, dataclass

from .ids import TenantId, UserId


@dataclass(frozen=True)
class LogContext:
    request_id: str
    trace_id: str
    tenant_id: TenantId
    actor_id: UserId
    action: str
    resource_type: str
    resource_id: str
    result: str

    def fields(self) -> dict[str, str]:
        return {key: str(value) for key, value in asdict(self).items()}
