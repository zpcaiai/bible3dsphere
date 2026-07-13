"""Skill 46/47: local cross-cultural practicum and short-term exposure.

Encoded invariants:
  * a practicum cannot start without Host + Supervisor + required safeguarding;
  * every placement declares allowed and prohibited activities;
  * a participant refusing faith activities never affects the service they receive;
  * short exposure is never counted as long-term cross-cultural experience;
  * every exposure program declares explicit non-objectives;
  * sensitive locations never enter a public/normal DTO.
"""
from __future__ import annotations

PLACEMENT_STATUS = frozenset({
    "applied", "screening", "accepted", "preparation_required", "ready",
    "active", "paused", "completed", "withdrawn", "terminated", "failed_to_start",
})
# Activities never permitted to a practicum participant without special authority.
PROHIBITED_ACTIVITIES = frozenset({
    "unsupervised_minor_contact", "independent_crisis_handling",
    "promise_money_or_jobs", "replace_professional", "collect_religious_identity",
    "auto_enroll_in_faith_program", "unconsented_photography", "use_participant_for_promotion",
})

EXPOSURE_TYPES = frozenset({
    "virtual_field_orientation", "local_exposure_day", "short_observation_trip",
    "guided_exploration_trip", "cross_cultural_internship", "language_immersion",
    "professional_service_internship", "team_life_internship",
})
# Types that are short and must never be treated as long-term experience.
SHORT_TERM_TYPES = frozenset({
    "virtual_field_orientation", "local_exposure_day", "short_observation_trip", "guided_exploration_trip",
})
LONG_TERM_TYPES = frozenset({
    "cross_cultural_internship", "language_immersion",
    "professional_service_internship", "team_life_internship",
})


def assert_can_start_practicum(*, has_host: bool, has_supervisor: bool,
                               safeguarding_current: bool, required_training_done: bool) -> None:
    if not has_host:
        raise ValueError("practicum requires a host organization")
    if not has_supervisor:
        raise ValueError("practicum requires a supervisor")
    if not safeguarding_current:
        raise ValueError("practicum requires current safeguarding certification")
    if not required_training_done:
        raise ValueError("required pre-practicum training must be complete")


def validate_activities(*, allowed, prohibited) -> None:
    """Allowed and prohibited must be disjoint; core prohibitions are always enforced."""
    a = set(allowed)
    p = set(prohibited) | PROHIBITED_ACTIVITIES
    overlap = a & p
    if overlap:
        raise ValueError(f"allowed activities cannot include prohibited ones: {sorted(overlap)}")


def service_unaffected_by_faith_refusal(*, participant_refused_faith: bool, service_reduced: bool) -> None:
    """Refusing faith activities must never reduce the service a participant receives."""
    if participant_refused_faith and service_reduced:
        raise ValueError("service must not be reduced because a participant declined faith activities")


def evidence_weight_for_exposure(exposure_type: str) -> str:
    """Short exposure yields only 'exposure' evidence, never 'long_term_experience'."""
    if exposure_type in SHORT_TERM_TYPES:
        return "exposure"
    if exposure_type in LONG_TERM_TYPES:
        return "long_term_experience"
    raise ValueError(f"unknown exposure type: {exposure_type!r}")


def assert_not_overstated(*, exposure_type: str, claimed_weight: str) -> None:
    if exposure_type in SHORT_TERM_TYPES and claimed_weight == "long_term_experience":
        raise ValueError("short exposure cannot be recorded as long-term experience")


def require_non_objectives(non_objectives) -> None:
    if not non_objectives:
        raise ValueError("an exposure program must declare explicit non-objectives")


def assert_long_term_internship_ready(*, has_receiving_team: bool, has_language_goal: bool,
                                      has_supervisor: bool, has_local_feedback: bool) -> None:
    if not (has_receiving_team and has_language_goal and has_supervisor and has_local_feedback):
        raise ValueError("a long-term internship needs a receiving team, language goal, supervisor and local feedback")
