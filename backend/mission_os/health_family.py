"""Skill 68/69: medical readiness & insurance, and family/spouse/child readiness.

Encoded invariants:
  * the platform stores only a minimal medical *status* (a committee/leader never
    sees the full record); AI never diagnoses or advises stopping medication;
  * disability is never an automatic rejection — reasonable accommodation first;
  * each accompanying family member is assessed independently; insurance gaps are
    explicit; a medication-continuity failure can block deployment;
  * a spouse's consent is independent (the candidate cannot submit it) and spouse
    opposition to relocation is never overridden; child education legality is checked.
"""
from __future__ import annotations

# ---- Skill 68: medical & insurance ----------------------------------------
MEDICAL_STATUS = frozenset({
    "assessment_pending", "additional_review_required", "cleared",
    "cleared_with_conditions", "not_cleared_currently", "expired", "superseded",
})
# The only statuses a non-medical committee/leader may see.
COMMITTEE_VISIBLE_STATUS = frozenset({
    "cleared", "cleared_with_conditions", "not_cleared_currently", "additional_review_required",
})
INSURANCE_GAP_TYPES = frozenset({
    "region_not_covered", "preexisting_condition_excluded", "mental_health_excluded",
    "maternity_excluded", "evacuation_missing", "repatriation_missing",
    "deductible_too_high", "coverage_limit_low", "provider_network_inadequate",
    "professional_liability_missing", "dependent_missing", "policy_expiring",
})


def committee_view(status: str) -> str:
    """Reduce a medical status to what a non-medical reviewer may see."""
    if status not in MEDICAL_STATUS:
        raise ValueError(f"invalid medical status: {status!r}")
    return status if status in COMMITTEE_VISIBLE_STATUS else "additional_review_required"


def ai_may_diagnose_or_prescribe() -> bool:
    return False


def assert_ai_medical_action(action: str) -> None:
    if action in {"diagnose", "prescribe", "stop_medication", "confirm_insurance_payout"}:
        raise ValueError(f"AI may not: {action}")


def disability_auto_rejects() -> bool:
    """Disability is never an automatic disqualifier."""
    return False


def medication_continuity_ok(*, ongoing_required: bool, local_availability: str,
                             has_backup_plan: bool) -> bool:
    if not ongoing_required:
        return True
    if local_availability in {"available", "importable_with_plan"} and has_backup_plan:
        return True
    return False


def insurance_blocks_high_risk(*, gaps, high_risk_field: bool) -> bool:
    """Missing evacuation/region coverage blocks a high-risk deployment."""
    g = set(gaps)
    critical = {"evacuation_missing", "region_not_covered", "repatriation_missing"}
    return high_risk_field and bool(g & critical)


# ---- Skill 69: family readiness -------------------------------------------
WILLINGNESS_STATUS = frozenset({
    "not_asked", "considering", "supportive", "supportive_with_conditions",
    "not_ready", "does_not_consent", "withdrawn", "review_required",
})
EDUCATION_MODELS = frozenset({
    "local_public_school", "local_private_school", "international_school",
    "boarding_school", "homeschool_where_legal", "online_school", "hybrid",
    "return_home_for_schooling", "undetermined",
})


def assert_spouse_review_authentic(*, submitter_id: str, spouse_user_id: str) -> None:
    if submitter_id != spouse_user_id:
        raise ValueError("a spouse review must be submitted by the spouse, not the candidate")


def spouse_consent_blocks_family_move(willingness_status: str) -> bool:
    if willingness_status not in WILLINGNESS_STATUS:
        raise ValueError(f"invalid willingness status: {willingness_status!r}")
    return willingness_status in {"does_not_consent", "not_ready", "withdrawn"}


def assert_education_legal(*, education_model: str, legal_in_region: bool) -> None:
    if education_model not in EDUCATION_MODELS:
        raise ValueError(f"invalid education model: {education_model!r}")
    if education_model == "homeschool_where_legal" and not legal_in_region:
        raise ValueError("homeschool is not legal in this region; choose another model")


def child_media_requires_guardian_consent(*, has_guardian_consent: bool) -> None:
    if not has_guardian_consent:
        raise ValueError("a child's photo/story requires guardian consent")


def family_gate(*, spouse_willingness: str, child_education_ready: bool,
                child_safeguarding_ready: bool, dependent_care_ready: bool,
                family_budget_ready: bool) -> dict:
    """Return the family readiness gate result — spouse opposition always blocks."""
    blocks = []
    if spouse_consent_blocks_family_move(spouse_willingness):
        blocks.append("spouse_not_consenting")
    if not child_education_ready:
        blocks.append("child_education_gap")
    if not child_safeguarding_ready:
        blocks.append("child_safeguarding_gap")
    if not dependent_care_ready:
        blocks.append("dependent_care_gap")
    if not family_budget_ready:
        blocks.append("family_budget_gap")
    return {"ready": not blocks, "blocking": blocks}
