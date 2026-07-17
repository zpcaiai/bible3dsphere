"""Purpose-bound policy decision point. Unknown requests are denied."""
from __future__ import annotations

from .contracts import ContextAccessDecision, ContextRequest
from .registry import PROJECTIONS, PURPOSE_POLICIES


def decide_context_access(
    request: ContextRequest,
    *,
    consent_active: bool,
    consent_fields: set[str] | None = None,
    caller_authenticated: bool = True,
) -> ContextAccessDecision:
    reasons: list[str] = []
    projection = PROJECTIONS.get(request.requested_projection)
    policy = PURPOSE_POLICIES.get(request.purpose)
    if not caller_authenticated:
        reasons.append("CALLER_NOT_AUTHENTICATED")
    if not projection:
        reasons.append("PROJECTION_NOT_REGISTERED")
    if not policy:
        reasons.append("PURPOSE_NOT_REGISTERED")
    elif request.requester_module not in policy["modules"]:
        reasons.append("REQUESTER_NOT_ALLOWED_FOR_PURPOSE")
    elif request.requested_projection not in policy["projections"]:
        reasons.append("PROJECTION_NOT_ALLOWED_FOR_PURPOSE")
    # Service/system callers do not bypass the same user consent checked here.
    if not consent_active:
        reasons.append("USER_CONSENT_REQUIRED")

    registered_fields = list(projection["fields"]) if projection else []
    requested_fields = request.requested_fields or registered_fields
    consent_fields = set(registered_fields) if consent_fields is None else consent_fields
    allowed = [field for field in requested_fields if field in registered_fields and field in consent_fields]
    denied = [field for field in requested_fields if field not in allowed]
    if requested_fields and not allowed:
        reasons.append("NO_FIELDS_ALLOWED")
    if denied:
        reasons.append("FIELDS_REDACTED")

    hard_denial = any(reason != "FIELDS_REDACTED" for reason in reasons)
    return ContextAccessDecision(
        allowed=not hard_denial,
        decision_reason_codes=reasons or ["ALLOWED_MINIMUM_PROJECTION"],
        allowed_fields=allowed,
        denied_fields=denied,
        maximum_ttl_seconds=min(int(projection["ttl"]), 900) if projection else 60,
        user_confirmation_required=False,
        audit_required=True,
    )
