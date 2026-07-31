from __future__ import annotations

from .models import Disclosure


def build_disclosure(
    *,
    disclosure_id: str,
    case_id: str,
    recipient_actor_id: str,
    purpose: str,
    requested_fields: list[str],
    allowed_fields: set[str],
    prohibited_fields: set[str],
    expires_at: str,
    basis: str,
    audit_id: str,
) -> Disclosure:
    selected = [
        field for field in requested_fields
        if field in allowed_fields and field not in prohibited_fields
    ]
    redacted = [field for field in requested_fields if field not in selected]

    return Disclosure(
        disclosure_id=disclosure_id,
        case_id=case_id,
        recipient_actor_id=recipient_actor_id,
        purpose=purpose,
        selected_fields=selected,
        redacted_fields=redacted,
        expires_at=expires_at,
        basis=basis,
        reshare_policy="forbidden",
        audit_id=audit_id,
        limitations=[
            "Disclosure is purpose-bound and does not grant access to the full case."
        ],
    )
