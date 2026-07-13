"""Skill 37/44/45: training plans, language learning and professional qualification.

Encoded invariants:
  * every readiness gap must map to a training/practice module;
  * a hard block can never be resolved by course completion alone;
  * language levels separate self / AI / native-speaker / authorized assessment;
    L4/L5 require a native or authorized assessor; official language != heart language;
  * cultural observation separates observation from interpretation;
  * professional identity is real — no fake identity; regulated professions require
    verification; expired certificates are invalid; qualification is per-country.
"""
from __future__ import annotations

# ---- Skill 37: training plan --------------------------------------------
MODULE_TYPES = frozenset({
    "formation_goal", "course", "reading", "language_goal", "cultural_observation",
    "local_service", "practicum", "professional_certificate", "team_exercise",
    "mentoring", "supervision", "safeguarding_training", "field_research",
    "reflection", "assessment", "restoration_action",
})
# A hard block requires human/remediation modules, never a course/quiz alone.
COURSE_ONLY_MODULE_TYPES = frozenset({"course", "reading", "assessment"})
PLAN_STATUS = frozenset({
    "draft", "awaiting_worker_review", "awaiting_mentor_review", "approved",
    "active", "paused", "revision_required", "completed", "cancelled", "superseded",
})


def validate_gap_has_module(gap_key: str, module_types) -> None:
    if not module_types:
        raise ValueError(f"readiness gap {gap_key!r} must map to at least one module")


def assert_hard_block_not_course_only(*, is_hard_block: bool, module_types) -> None:
    """A hard block cannot be cleared purely by course/reading/quiz modules."""
    if not is_hard_block:
        return
    types = set(module_types)
    if types and types <= COURSE_ONLY_MODULE_TYPES:
        raise ValueError("a hard block cannot be remediated by course completion alone")


def habits_require_user_confirmation(user_confirmed: bool) -> None:
    if not user_confirmed:
        raise ValueError("habits may only be created after explicit user confirmation")


# ---- Skill 44: language and culture --------------------------------------
LANGUAGE_LEVELS = ("L0", "L1", "L2", "L3", "L4", "L5")
LANGUAGE_SKILLS = frozenset({
    "listening", "speaking", "reading", "writing",
    "relational_communication", "ministry_communication",
    "professional_communication", "cultural_pragmatics",
})
ASSESSOR_TYPES = frozenset({"self", "ai", "native_speaker", "authorized_assessor"})
_HIGH_LEVELS = {"L4", "L5"}


def validate_language_level(level: str) -> None:
    if level not in LANGUAGE_LEVELS:
        raise ValueError(f"invalid language level: {level!r}")


def can_certify_language_level(*, level: str, assessor_type: str) -> None:
    """AI/self can record a level but cannot *certify* it; L4/L5 need a native or
    authorized assessor."""
    validate_language_level(level)
    if assessor_type not in ASSESSOR_TYPES:
        raise ValueError("invalid assessor type")
    if assessor_type in {"self", "ai"}:
        raise ValueError("self/AI assessment cannot certify a verified language level")
    if level in _HIGH_LEVELS and assessor_type != "native_speaker" and assessor_type != "authorized_assessor":
        raise ValueError("L4/L5 require a native or authorized assessor")


def official_is_not_heart_language(*, official_verified: bool, heart_language_verified: bool) -> None:
    """Official-language competence must never auto-satisfy heart-language need."""
    # This function documents the rule; heart language is tracked separately and is
    # never set from the official-language flag.
    return None


def cultural_observation_confidence(*, has_local_explanation: bool, requested_confidence: str) -> str:
    """An observation without a local explanation can never be high confidence."""
    if requested_confidence == "high" and not has_local_explanation:
        return "low"
    return requested_confidence


# ---- Skill 45: professional qualification --------------------------------
REGULATED_PROFESSIONS = frozenset({
    "medicine", "nursing", "counseling", "special_education", "education",
})
VERIFICATION_STATUS = frozenset({"unverified", "submitted", "verified", "expired", "rejected"})


def assert_no_fake_identity(intent: str) -> None:
    if intent in {"fake_employment", "fake_credential", "visa_cover_deception"}:
        raise ValueError("fabricated professional identity is not permitted")


def professional_qualification_ok(*, profession: str, verification_status: str, is_expired: bool) -> None:
    """Regulated professions require a current verified qualification."""
    if verification_status not in VERIFICATION_STATUS:
        raise ValueError("invalid verification status")
    if profession in REGULATED_PROFESSIONS:
        if verification_status != "verified" or is_expired:
            raise ValueError(f"{profession} requires a current verified qualification")


def qualification_is_country_specific(country_a: str, country_b: str, verified_country: str) -> bool:
    """A qualification verified for one country does not transfer to another."""
    return verified_country == country_b and country_a != country_b
