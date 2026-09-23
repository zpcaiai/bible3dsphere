from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

REQUIRED_REVIEW_ROLES = (
    "theology_reviewer", "pastoral_reviewer", "rights_reviewer",
    "accessibility_reviewer", "release_reviewer",
)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unsigned(document: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in document.items() if key not in {"signature", "signatureAlgorithm", "signerKeyId"}}


def sign_document(document: Mapping[str, Any], *, private_key_pem: bytes, key_id: str) -> dict[str, Any]:
    key = serialization.load_pem_private_key(private_key_pem, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("release signing key must be Ed25519")
    unsigned = _unsigned(document)
    signature = key.sign(canonical_json(unsigned))
    return {
        **unsigned,
        "signatureAlgorithm": "Ed25519",
        "signerKeyId": key_id,
        "signature": base64.b64encode(signature).decode("ascii"),
    }


def verify_signed_document(document: Mapping[str, Any], *, public_key_pem: bytes) -> bool:
    if document.get("signatureAlgorithm") != "Ed25519" or not document.get("signature"):
        return False
    try:
        key = serialization.load_pem_public_key(public_key_pem)
        if not isinstance(key, Ed25519PublicKey):
            return False
        key.verify(base64.b64decode(str(document["signature"]), validate=True), canonical_json(_unsigned(document)))
        return True
    except Exception:
        return False


def create_review_attestation(
    *, subject: Mapping[str, str], reviewer_id: str, reviewer_role: str,
    decision: str, notes_sha256: str, private_key_pem: bytes, key_id: str,
    issued_at: str | None = None,
) -> dict[str, Any]:
    if reviewer_role not in REQUIRED_REVIEW_ROLES:
        raise ValueError("unknown review role")
    if decision not in {"APPROVED", "CHANGES_REQUIRED", "REJECTED"}:
        raise ValueError("invalid review decision")
    document = {
        "schemaVersion": "digital-human-review/v1",
        "reviewerId": reviewer_id,
        "reviewerRole": reviewer_role,
        "decision": decision,
        "notesSha256": notes_sha256,
        "subject": dict(subject),
        "issuedAt": issued_at or datetime.now(timezone.utc).isoformat(),
    }
    return sign_document(document, private_key_pem=private_key_pem, key_id=key_id)


def verify_review_bundle(
    reviews: Iterable[Mapping[str, Any]], *, subject: Mapping[str, str],
    trusted_keys: Mapping[str, bytes],
) -> dict[str, Mapping[str, Any]]:
    approved: dict[str, Mapping[str, Any]] = {}
    reviewer_ids: set[str] = set()
    for review in reviews:
        key_id = str(review.get("signerKeyId") or "")
        role = str(review.get("reviewerRole") or "")
        reviewer_id = str(review.get("reviewerId") or "")
        if role not in REQUIRED_REVIEW_ROLES or review.get("decision") != "APPROVED":
            continue
        if review.get("subject") != dict(subject):
            raise ValueError(f"review subject mismatch for {role}")
        public_key = trusted_keys.get(key_id)
        if not public_key or not verify_signed_document(review, public_key_pem=public_key):
            raise ValueError(f"invalid review signature for {role}")
        if reviewer_id in reviewer_ids:
            raise ValueError("one reviewer cannot satisfy multiple independent roles")
        reviewer_ids.add(reviewer_id)
        if role in approved:
            raise ValueError(f"duplicate review role: {role}")
        approved[role] = review
    missing = sorted(set(REQUIRED_REVIEW_ROLES) - set(approved))
    if missing:
        raise ValueError(f"missing approved review roles: {', '.join(missing)}")
    if approved["theology_reviewer"]["reviewerId"] == approved["release_reviewer"]["reviewerId"]:
        raise ValueError("theology and release reviewer must be independent")
    return approved


def build_release_certificate(
    *, subject: Mapping[str, str], reviews: Iterable[Mapping[str, Any]],
    trusted_review_keys: Mapping[str, bytes], build_revision: str,
    test_evidence_sha256: str, private_key_pem: bytes, key_id: str,
    issued_at: str | None = None,
) -> dict[str, Any]:
    approved = verify_review_bundle(reviews, subject=subject, trusted_keys=trusted_review_keys)
    review_digests = {
        role: sha256_json(review) for role, review in sorted(approved.items())
    }
    document = {
        "schemaVersion": "digital-human-release/v1",
        "contentDecision": "APPROVED",
        "productAssurance": "NOT_CERTIFIED",
        "subject": dict(subject),
        "buildRevision": build_revision,
        "testEvidenceSha256": test_evidence_sha256,
        "reviewDigests": review_digests,
        "reviewerIds": {role: review["reviewerId"] for role, review in sorted(approved.items())},
        "issuedAt": issued_at or datetime.now(timezone.utc).isoformat(),
    }
    return sign_document(document, private_key_pem=private_key_pem, key_id=key_id)


def verify_release_certificate(
    certificate: Mapping[str, Any], *, expected_subject: Mapping[str, str],
    trusted_release_keys: Mapping[str, bytes],
) -> bool:
    if certificate.get("schemaVersion") != "digital-human-release/v1":
        return False
    if certificate.get("contentDecision") != "APPROVED":
        return False
    if certificate.get("subject") != dict(expected_subject):
        return False
    reviewer_ids = certificate.get("reviewerIds") or {}
    if set(reviewer_ids) != set(REQUIRED_REVIEW_ROLES) or len(set(reviewer_ids.values())) != len(REQUIRED_REVIEW_ROLES):
        return False
    key_id = str(certificate.get("signerKeyId") or "")
    public_key = trusted_release_keys.get(key_id)
    return bool(public_key and verify_signed_document(certificate, public_key_pem=public_key))


def load_key_map(path: Path) -> dict[str, bytes]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("trusted key file must be an object")
    result: dict[str, bytes] = {}
    for key_id, value in payload.items():
        if not isinstance(key_id, str) or not isinstance(value, str):
            raise ValueError("trusted key entries must be PEM strings")
        result[key_id] = value.encode("utf-8")
    return result
