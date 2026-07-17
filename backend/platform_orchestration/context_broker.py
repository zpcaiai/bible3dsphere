"""Minimum, short-lived projections for cross-module reads."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .contracts import ContextAccessDecision, ContextRequest, ContextResponse, ContextSourceReference
from .registry import PROJECTIONS


def _pick(source: dict[str, Any], allowed_fields: list[str]) -> dict[str, Any]:
    return {field: source[field] for field in allowed_fields if field in source}


def resolve_projection(
    request: ContextRequest,
    decision: ContextAccessDecision,
    *,
    confirmed_source: dict[str, Any],
    pending_source: dict[str, Any] | None = None,
    source_references: list[dict[str, Any]] | None = None,
    consent_reference_ids: list[str] | None = None,
    now: datetime | None = None,
) -> ContextResponse:
    if not decision.allowed:
        raise PermissionError("context denied: " + ",".join(decision.decision_reason_codes))
    definition = PROJECTIONS.get(request.requested_projection)
    if not definition:
        raise LookupError("projection is not registered")
    now = now or datetime.now(timezone.utc)
    allowed = decision.allowed_fields
    confirmed = _pick(confirmed_source, allowed)
    pending = _pick(pending_source or {}, allowed)
    limitations = ["MINIMUM_FIELD_PROJECTION", "NO_RAW_SENSITIVE_TEXT", "PENDING_IS_NOT_FACT"]
    if decision.denied_fields:
        limitations.append("REQUESTED_FIELDS_REDACTED")
    # Crisis context is a routing signal only and never carries model hypotheses.
    if request.requested_projection == "crisis_routing_context_v1":
        pending = {}
        limitations.append("CRISIS_NARRATIVE_EXCLUDED")
    refs = [ContextSourceReference.model_validate(item) for item in (source_references or [])]
    return ContextResponse(
        projection_name=request.requested_projection,
        projection_version=definition["version"],
        confirmed_context=confirmed,
        pending_context=pending,
        limitations=limitations,
        consent_reference_ids=consent_reference_ids or [],
        source_references=refs,
        generated_at=now,
        expires_at=now + timedelta(seconds=decision.maximum_ttl_seconds),
    )


def context_is_fresh(response: ContextResponse, *, now: datetime | None = None) -> bool:
    return response.expires_at > (now or datetime.now(timezone.utc))
