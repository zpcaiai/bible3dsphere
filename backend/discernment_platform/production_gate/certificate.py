from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from .models import ReleaseCertificate, ReleaseStatus


def _signature_payload(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def issue_certificate(
    *,
    certificate_id: str,
    release_id: str,
    status: ReleaseStatus,
    expires_at: str,
    scope: dict,
    domain_results: list[dict],
    open_findings: list[str],
    accepted_risks: list[dict],
    feature_restrictions: list[str],
    rollback_target: str,
    recertification_triggers: list[str],
    signatories: list[dict],
) -> ReleaseCertificate:
    issued_at = datetime.now(timezone.utc).isoformat()
    unsigned = {
        "certificate_id": certificate_id,
        "release_id": release_id,
        "status": status.value,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "scope": scope,
        "domain_results": domain_results,
        "open_findings": open_findings,
        "accepted_risks": accepted_risks,
        "feature_restrictions": feature_restrictions,
        "rollback_target": rollback_target,
        "recertification_triggers": recertification_triggers,
        "signatories": signatories,
    }
    signature_hash = _signature_payload(unsigned)
    return ReleaseCertificate(**unsigned, signature_hash=signature_hash)


def revoke_certificate(
    certificate_id: str,
    reason_codes: list[str],
    actions: list[str],
) -> dict:
    return {
        "revocation_id": f"revoke-{certificate_id}",
        "certificate_id": certificate_id,
        "reason_codes": reason_codes,
        "effective_at": datetime.now(timezone.utc).isoformat(),
        "actions": actions,
    }
