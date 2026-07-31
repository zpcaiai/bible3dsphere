from __future__ import annotations

from datetime import datetime
from .models import CertificationControl, EvidenceItem


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_evidence(
    control: CertificationControl,
    evidence: list[EvidenceItem],
    now: datetime,
) -> dict:
    matching = [e for e in evidence if e.control_id == control.control_id]
    valid = []
    invalid_reasons = []

    for item in matching:
        if item.status != "valid":
            invalid_reasons.append(f"{item.evidence_id}:status={item.status}")
            continue
        expires = _parse_iso(item.expires_at)
        if expires is not None and expires < now:
            invalid_reasons.append(f"{item.evidence_id}:expired")
            continue
        if not item.locator:
            invalid_reasons.append(f"{item.evidence_id}:locator_missing")
            continue
        valid.append(item)

    present_types = {e.evidence_type for e in valid}
    missing_types = [
        t for t in control.required_evidence_types
        if t not in present_types
    ]

    return {
        "control_id": control.control_id,
        "valid": bool(valid) and not missing_types,
        "valid_evidence_ids": [e.evidence_id for e in valid],
        "missing_types": missing_types,
        "invalid_reasons": invalid_reasons,
    }
