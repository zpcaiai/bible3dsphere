"""Read/integration ports at the Mission OS bounded-context boundary.

Domain and application code depend on these protocols, never concrete database
repositories owned by another context.
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence

from .ids import OrganizationId, TenantId, UserId

Record = Mapping[str, Any]


class IdentityProfilePort(Protocol):
    def public_profile(self, tenant_id: TenantId, user_id: UserId) -> Record: ...


class GiftProfilePort(Protocol):
    def current_gifts(self, tenant_id: TenantId, user_id: UserId) -> Record | None: ...


class FormationPlanPort(Protocol):
    def current_plan(self, tenant_id: TenantId, user_id: UserId) -> Record | None: ...


class HabitTrackerPort(Protocol):
    def milestone_summary(self, tenant_id: TenantId, user_id: UserId) -> Record: ...


class DiscipleshipPort(Protocol):
    def journey_summary(self, tenant_id: TenantId, user_id: UserId) -> Record | None: ...


class CrisisRiskPort(Protocol):
    def create_human_review(self, tenant_id: TenantId, subject_id: UserId, reference_id: str) -> str: ...


class ContentPort(Protocol):
    def approved_items(self, tenant_id: TenantId, keys: Sequence[str], locale: str) -> Sequence[Record]: ...


class NotificationPort(Protocol):
    def enqueue(self, tenant_id: TenantId, recipient_id: UserId, template: str, variables: Record) -> str: ...


class FileStoragePort(Protocol):
    def signed_read_url(self, tenant_id: TenantId, object_key: str, expires_seconds: int) -> str: ...


class AuditPort(Protocol):
    def record(self, *, tenant_id: TenantId, actor_id: UserId, action: str,
               resource_type: str, resource_id: str, result: str,
               changed_fields: Sequence[str] = ()) -> None: ...


class FeatureFlagPort(Protocol):
    def enabled(self, key: str, *, tenant_id: TenantId,
                organization_id: OrganizationId | None = None,
                user_id: UserId | None = None) -> bool: ...
