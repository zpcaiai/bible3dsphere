"""Skill 28/29/30/35: calling-discernment journey, motives, confirmation, pause/appeal.

Pure-python invariants. Core rules encoded here:
  * a subjective impression (dream/feeling) can never *by itself* unlock the
    readiness gate;
  * Field Interest is distinct from Calling Orientation;
  * a hard-block motive blocks becoming a deployment candidate and can only be
    cleared by a human (never AI);
  * multi-source feedback is never silently averaged;
  * pause is non-shaming and never means "no calling".
"""
from __future__ import annotations
from dataclasses import dataclass

# ---- Skill 28: calling journey --------------------------------------------
CALLING_ORIENTATIONS = frozenset({
    "general_christian_mission", "local_evangelism", "cross_cultural_mission",
    "diaspora_ministry", "church_equipping", "bible_translation_support",
    "professional_mission", "member_care", "prayer_and_mobilization",
    "sending_church_service", "mission_research", "digital_mission_infrastructure",
    "undetermined",
})
JOURNEY_STATUS = frozenset({
    "draft", "active_discernment", "waiting_for_feedback", "local_practice_required",
    "training_required", "paused", "ready_for_readiness_assessment", "completed",
    "withdrawn", "archived",
})
REFLECTION_TYPES = frozenset({
    "burden", "dream_or_impression", "scripture_reflection", "ministry_experience",
    "suffering_or_crisis", "role_interest", "field_interest", "mentor_feedback_response",
    "family_response", "local_practice_reflection", "cross_cultural_reflection", "decision_review",
})
# Evidence strength classes. A subjective impression is explicitly non-decisive.
EVIDENCE_TYPES = frozenset({
    "subjective_impression", "church_feedback", "mentor_feedback", "family_feedback",
    "ministry_supervision", "local_practice", "cross_cultural_practice", "formation_progress",
})
NON_DECISIVE_EVIDENCE = frozenset({"subjective_impression"})


def validate_reflection(reflection_type: str) -> None:
    if reflection_type not in REFLECTION_TYPES:
        raise ValueError(f"invalid reflection type: {reflection_type!r}")


def readiness_gate(*, has_church_or_mentor_feedback: bool, has_local_practice: bool,
                   motive_assessment_complete: bool, unresolved_hard_blocks: int,
                   evidence_types) -> None:
    """Raise unless the journey may enter the readiness assessment.

    Subjective impressions alone can never satisfy the gate.
    """
    ev = set(evidence_types)
    decisive = ev - NON_DECISIVE_EVIDENCE
    if not decisive:
        raise ValueError("a calling cannot advance on subjective impressions alone")
    if not has_church_or_mentor_feedback:
        raise ValueError("readiness gate requires church or mentor feedback")
    if not has_local_practice:
        raise ValueError("readiness gate requires real local practice")
    if not motive_assessment_complete:
        raise ValueError("readiness gate requires a completed motive assessment")
    if unresolved_hard_blocks > 0:
        raise ValueError("unresolved hard blocks prevent the readiness gate")


def field_interest_is_not_calling(orientation: str | None, field_interest: str | None) -> None:
    """Field interest must never be recorded as a settled calling orientation."""
    if orientation is not None and orientation not in CALLING_ORIENTATIONS:
        raise ValueError("invalid calling orientation")
    # A field interest string is stored separately; it does not set orientation.


# ---- Skill 29: motives and blockers ---------------------------------------
BLOCKER_TYPES = frozenset({
    "active_addiction", "untreated_mental_health_crisis", "marriage_crisis",
    "family_abandonment_risk", "unresolved_abuse_behavior", "financial_instability",
    "debt_avoidance", "church_conflict_escape", "authority_rejection", "savior_complex",
    "power_control_pattern", "false_or_deceptive_entry_intent", "lack_of_church_accountability",
    "unrealistic_field_expectation", "professional_incompetence", "safeguarding_concern",
})
BLOCKER_SEVERITY = ("observation", "development_needed", "significant_concern", "hard_block")


def blocks_deployment_candidate(severities) -> bool:
    return any(s == "hard_block" for s in severities)


def can_clear_blocker(*, actor_type: str) -> None:
    """Only a human may clear a blocker; AI never can."""
    if actor_type == "ai":
        raise ValueError("AI cannot clear a calling blocker")
    if actor_type not in {"human", "panel"}:
        raise ValueError("invalid actor type for blocker clearance")


# ---- Skill 30: multi-source confirmation ----------------------------------
FEEDBACK_RECOMMENDATIONS = frozenset({
    "support_continue", "support_with_development", "recommend_pause",
    "significant_concern", "insufficient_observation", "unable_to_assess",
})


def validate_feedback_request(*, requester_id: str, respondent_id: str, respondent_type: str) -> None:
    if requester_id == respondent_id:
        raise ValueError("a candidate cannot submit their own confirmation")
    if not respondent_type:
        raise ValueError("respondent type required")


def aggregate_is_not_average(recommendations) -> dict:
    """Return agreement/conflict structure — never a single averaged verdict."""
    recs = list(recommendations)
    concern = [r for r in recs if r in {"recommend_pause", "significant_concern"}]
    support = [r for r in recs if r in {"support_continue", "support_with_development"}]
    return {
        "total": len(recs),
        "support": len(support),
        "concern": len(concern),
        "has_conflict": bool(support and concern),
        "insufficient": all(r in {"insufficient_observation", "unable_to_assess"} for r in recs) if recs else True,
    }


# ---- Skill 35: pause / restore / appeal -----------------------------------
PAUSE_REASONS = frozenset({
    "personal_request", "health", "mental_health", "marriage_or_family", "financial",
    "church_relationship", "team_conflict", "safeguarding", "legal_or_security",
    "calling_uncertainty", "training_gap", "professional_qualification",
    "insufficient_evidence", "organization_request",
})
APPEAL_TYPES = frozenset({
    "factual_error", "process_violation", "conflict_of_interest", "missing_evidence",
    "discriminatory_assumption", "new_material_evidence", "privacy_violation", "other",
})
# Language that must never be used for a pause (non-shaming rule).
FORBIDDEN_PAUSE_LANGUAGE = frozenset({
    "failure", "not_called", "unspiritual", "eliminated", "unworthy",
})


def validate_pause_reason(reason: str) -> None:
    if reason not in PAUSE_REASONS:
        raise ValueError(f"invalid pause reason: {reason!r}")


def assert_pause_label_is_not_shaming(label: str) -> None:
    if label.strip().lower() in FORBIDDEN_PAUSE_LANGUAGE:
        raise ValueError("pause label must not be shaming")


def can_review_appeal(*, appellant_id: str, reviewer_id: str, original_decider_id: str) -> None:
    """The original decider may not solely adjudicate an appeal against their decision."""
    if reviewer_id == appellant_id:
        raise ValueError("appellant cannot review their own appeal")
    if reviewer_id == original_decider_id:
        raise ValueError("original decider cannot solely adjudicate the appeal")
