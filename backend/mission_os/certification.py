"""Skill 43/49: safeguarding certification and multi-evidence stage certification.

Encoded invariants:
  * knowledge / simulation / real-practice evidence are separate — a quiz alone
    never proves real competence, a simulation alone never certifies competence;
  * rubric criteria are observable behaviours, never vague spiritual adjectives;
  * high-risk competencies require multiple evidence classes and a second reviewer;
  * an observer may never be the observed; conflicts of interest block certification;
  * safeguarding certification requires a human scenario assessment and expires,
    and expiry auto-suspends contact permission;
  * Batch 4 never issues a deployment approval.
"""
from __future__ import annotations
from datetime import datetime, timezone

EVIDENCE_CLASSES = frozenset({
    "quiz", "written_assignment", "oral_explanation", "simulation", "supervised_practice",
    "mentor_observation", "host_feedback", "community_feedback", "professional_certificate",
    "language_assessment", "safeguarding_assessment", "portfolio", "team_observation",
    "incident_free_practice_period", "reflection",
})
KNOWLEDGE_ONLY = frozenset({"quiz", "written_assignment"})
SIMULATION_ONLY = frozenset({"simulation"})

CERTIFICATION_TYPES = frozenset({
    "foundational_training_completed", "local_practicum_ready", "local_practicum_completed",
    "cross_cultural_internship_ready", "team_discernment_ready",
    "role_training_requirement_satisfied", "safeguarding_contact_ready",
    "language_stage_verified", "professional_requirement_verified",
})
# Batch 4 must never issue this.
FORBIDDEN_CERTIFICATION_TYPES = frozenset({"deployment_approved"})

# Vague spiritual adjectives a rubric criterion must never use.
FORBIDDEN_RUBRIC_TERMS = frozenset({
    "very_spiritual", "anointed", "mature_feeling", "likeable", "godly_vibe",
    "很属灵", "有恩膏", "感觉成熟", "让人喜欢",
})


def certification_type_allowed(cert_type: str) -> None:
    if cert_type in FORBIDDEN_CERTIFICATION_TYPES:
        raise ValueError("Batch 4 cannot issue a deployment approval")
    if cert_type not in CERTIFICATION_TYPES:
        raise ValueError(f"unknown certification type: {cert_type!r}")


def assert_not_knowledge_only(evidence_classes) -> None:
    """A competency cannot be 'observed' on knowledge evidence alone."""
    classes = set(evidence_classes)
    if classes and classes <= KNOWLEDGE_ONLY:
        raise ValueError("a quiz/written assignment alone cannot prove real competence")


def assert_not_simulation_only(evidence_classes) -> None:
    classes = set(evidence_classes)
    if classes and classes <= SIMULATION_ONLY:
        raise ValueError("a simulation alone cannot certify real-world competence")


def validate_rubric_criterion(text: str) -> None:
    low = text.strip().lower().replace(" ", "_")
    for term in FORBIDDEN_RUBRIC_TERMS:
        if term in low or term in text:
            raise ValueError("rubric criteria must be observable behaviours, not vague adjectives")


def can_certify(*, evidence_classes, high_risk: bool, reviewer_ids,
                observer_id: str, observed_id: str) -> None:
    """Raise unless a stage certification may be issued."""
    if observer_id == observed_id:
        raise ValueError("an observer cannot certify themselves")
    assert_not_knowledge_only(evidence_classes)
    if high_risk:
        classes = set(evidence_classes)
        if len(classes) < 2:
            raise ValueError("high-risk competency requires at least two evidence classes")
        if len(set(reviewer_ids)) < 2:
            raise ValueError("high-risk competency requires a second reviewer")


# ---- Skill 43: safeguarding certification ---------------------------------
SAFEGUARDING_LEVELS = ("awareness_completed", "contact_ready", "supervised_response_ready", "incident_role_ready")


def safeguarding_contact_allowed(*, level: str | None, expires_at: datetime | None,
                                 now: datetime | None = None) -> bool:
    """Contact permission requires at least contact_ready and an unexpired certificate."""
    now = now or datetime.now(timezone.utc)
    if level not in SAFEGUARDING_LEVELS:
        return False
    order = {lvl: i for i, lvl in enumerate(SAFEGUARDING_LEVELS)}
    if order[level] < order["contact_ready"]:
        return False
    if expires_at is None or expires_at.tzinfo is None or expires_at <= now:
        return False  # expiry auto-suspends contact
    return True


def assert_safeguarding_requires_human_scenario(*, has_human_scenario_assessment: bool) -> None:
    if not has_human_scenario_assessment:
        raise ValueError("safeguarding certification requires a human scenario assessment, not a quiz alone")
