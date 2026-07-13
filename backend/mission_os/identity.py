"""Skill 65/66/67: legal identity paths, credentials, and compliance review.

Encoded invariants:
  * an identity path's declared activity must match its actual activity — no fake
    employment / school / business; regulated work requires a licence;
  * credential identifiers are masked (never a full number in a normal DTO); a
    critical credential expiring blocks deployment; AI never reads credential files;
  * a legal/compliance conclusion needs a professional; an opinion has an expiry
    and a jurisdiction and does not transfer to another country; AI never clears.
"""
from __future__ import annotations
from datetime import date, datetime, timezone

# ---- Skill 65: identity paths ---------------------------------------------
IDENTITY_TYPES = frozenset({
    "employment", "self_employment", "business_owner", "student", "researcher",
    "dependent", "family_reunification", "volunteer_where_legal",
    "religious_worker_where_legal", "retirement", "digital_nomad_where_legal",
    "professional_secondment", "humanitarian_worker", "local_citizen_or_permanent_resident",
})
REGULATED_ACTIVITIES = frozenset({"medicine", "nursing", "counseling", "teaching_licensed", "law"})
FAKE_INTENTS = frozenset({
    "fake_employment", "shell_company", "fake_course", "forged_proof",
    "fake_address", "fictitious_business", "hide_regulated_work",
    "bypass_license", "forged_invitation", "illegal_overstay",
})
IDENTITY_HARD_BLOCKS = frozenset({
    "fake_employment", "fake_school", "fictitious_business", "unlicensed_practice",
    "tourist_status_for_long_term_work", "overstay_plan", "using_others_documents",
    "forged_funds_proof", "activity_identity_mismatch", "requires_illegal_or_unethical_acts",
})


def assert_identity_consistent(*, declared_activity: str, actual_activity: str) -> None:
    if declared_activity.strip().lower() != actual_activity.strip().lower():
        raise ValueError("declared and actual activity must be consistent")


def assert_no_fake_identity(intent: str) -> None:
    if intent in FAKE_INTENTS:
        raise ValueError(f"identity path may not rely on: {intent}")


def assert_regulated_licensed(*, activity: str, has_license: bool) -> None:
    if activity in REGULATED_ACTIVITIES and not has_license:
        raise ValueError(f"{activity} requires a professional licence")


# ---- Skill 66: credentials -------------------------------------------------
CREDENTIAL_TYPES = frozenset({
    "passport", "visa", "residence_permit", "work_permit", "student_permit",
    "dependent_permit", "professional_license", "business_registration",
    "tax_registration", "driver_license", "marriage_certificate", "custody_document",
    "vaccination_certificate", "insurance_card", "background_check",
})
CRITICAL_CREDENTIALS = frozenset({"passport", "visa", "residence_permit", "work_permit"})
REMINDER_STAGES = (180, 120, 90, 60, 30, 14, 7, 0)


def mask_identifier(identifier: str) -> str:
    """Only the last few characters are ever exposed."""
    if not identifier:
        return ""
    tail = identifier[-3:]
    return f"****{tail}"


def assert_no_full_identifier_in_dto(dto: dict) -> None:
    for k, v in dto.items():
        if k in {"identifier", "passport_number", "credential_number"} and v and not str(v).startswith("****"):
            raise ValueError(f"credential DTO exposes an unmasked identifier: {k}")


def credential_blocks_deployment(*, credential_type: str, expires_at: date | None,
                                 min_validity_days: int, now: date | None = None) -> bool:
    """A critical credential expiring within the required validity window blocks deploy."""
    if credential_type not in CRITICAL_CREDENTIALS:
        return False
    if expires_at is None:
        return True
    now = now or datetime.now(timezone.utc).date()
    remaining = (expires_at - now).days
    return remaining < min_validity_days


def ai_may_access_credential_file() -> bool:
    return False


# ---- Skill 67: compliance --------------------------------------------------
COMPLIANCE_DOMAINS = frozenset({
    "immigration", "employment", "professional_licensing", "tax_residency",
    "personal_tax", "organization_tax", "foreign_exchange", "fundraising",
    "anti_money_laundering", "religious_activity", "education", "child_safeguarding",
    "healthcare", "insurance", "data_protection", "cybersecurity",
    "content_publication", "intellectual_property", "nonprofit_operations",
    "sanctions_and_export_controls",
})
COMPLIANCE_HARD_BLOCKS = frozenset({
    "identity_activity_mismatch", "unlicensed_regulated_work", "explicitly_prohibited_activity",
    "tax_registration_incomplete", "cross_border_data_no_basis", "funds_flow_violation",
    "minor_program_no_legal_basis", "mandatory_insurance_unmet",
    "sanctioned_transaction", "public_content_violation", "entity_not_qualified",
})


def assert_ai_cannot_clear_legal(actor_type: str, target_status: str) -> None:
    if actor_type == "ai" and target_status in {"cleared", "cleared_for_next_stage", "professional_review_complete"}:
        raise ValueError("AI cannot produce a legal/compliance clearance")


def opinion_valid(*, issued_at: date, expires_at: date | None, now: date | None = None) -> bool:
    now = now or datetime.now(timezone.utc).date()
    if expires_at is None:
        return False  # opinions must carry an expiry
    return issued_at <= now <= expires_at


def opinion_transfers(*, opinion_jurisdiction: str, target_jurisdiction: str) -> bool:
    """A legal opinion for one jurisdiction does not transfer to another."""
    return opinion_jurisdiction == target_jurisdiction


def domain_needs_professional(*, domain: str, risk_level: str) -> bool:
    if domain not in COMPLIANCE_DOMAINS:
        raise ValueError(f"unknown compliance domain: {domain!r}")
    return risk_level in {"high", "critical"} or domain in {
        "immigration", "tax_residency", "professional_licensing",
        "sanctions_and_export_controls", "child_safeguarding",
    }
