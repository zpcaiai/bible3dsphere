"""Skill 32/33/34: worker roles, match separation, and 15-dimension readiness.

Encoded invariants:
  * readiness is NOT a spiritual-value score — no single total is produced;
  * hard blocks can never be bought off by strong dimensions;
  * a deployment candidate decision requires a human panel (never AI, never self);
  * protected attributes (single, female, disabled, introvert, older, non-seminary,
    lower income) never auto-downgrade a dimension;
  * role / field / deployment are three separate layers.
"""
from __future__ import annotations

# ---- Skill 34: fifteen readiness dimensions --------------------------------
READINESS_DIMENSIONS = (
    "spiritual_maturity", "biblical_and_theological_foundation", "church_commitment",
    "character_and_integrity", "emotional_health", "marriage_and_family_health",
    "financial_stability", "teamwork", "conflict_resolution", "cross_cultural_humility",
    "language_learning_capacity", "professional_competence", "safeguarding_awareness",
    "legal_security_awareness", "resilience_and_long_term_commitment",
)
DIMENSION_LEVELS = (
    "unknown", "significant_concern", "developing", "adequate_for_next_stage", "strong", "trainer_level",
)
READINESS_LEVELS = frozenset({
    "exploration", "foundational_development", "local_practice_ready",
    "cross_cultural_internship_ready", "team_discernment_ready", "deployment_candidate",
    "pause_and_restore", "not_enough_evidence",
})
DEFAULT_HARD_BLOCKS = frozenset({
    "no_active_sending_church", "active_severe_addiction", "untreated_abuse_risk",
    "severe_marriage_crisis_with_relocation", "deceptive_or_illegal_entry_intent",
    "refuses_supervision", "major_safeguarding_concern", "missing_required_professional_qualification",
    "no_team_when_field_requires", "no_legal_status_path", "local_partner_opposed",
    "unmitigated_high_risk", "acute_mental_health_crisis", "financial_fraud_or_debt_evasion",
})
# Attributes that must never, by themselves, lower a readiness dimension.
PROTECTED_NON_DISQUALIFIERS = frozenset({
    "single", "older_age", "physical_disability", "introvert", "non_seminary",
    "lower_income", "recovered_past_failure", "no_public_preaching_gift", "female", "needs_accommodation",
})


def validate_dimension(key: str, level: str) -> None:
    if key not in READINESS_DIMENSIONS:
        raise ValueError(f"unknown readiness dimension: {key!r}")
    if level not in DIMENSION_LEVELS:
        raise ValueError(f"invalid dimension level: {level!r}")


def assert_not_protected_downgrade(reason_codes) -> None:
    """Raise if a downgrade is justified solely by a protected attribute."""
    codes = set(reason_codes)
    if codes and codes <= PROTECTED_NON_DISQUALIFIERS:
        raise ValueError("a readiness dimension cannot be downgraded solely on a protected attribute")


def resolve_readiness_level(*, dimensions: dict, hard_blocks, evidence_complete: bool) -> str:
    """Return a readiness *level* (not a numeric spiritual score)."""
    blocks = set(hard_blocks)
    for b in blocks:
        if b not in DEFAULT_HARD_BLOCKS:
            raise ValueError(f"unknown hard block: {b!r}")
    if blocks:
        return "pause_and_restore"
    if not evidence_complete or any(v == "unknown" for v in dimensions.values()):
        return "not_enough_evidence"
    concerns = [k for k, v in dimensions.items() if v == "significant_concern"]
    if concerns:
        return "foundational_development"
    developing = [k for k, v in dimensions.items() if v == "developing"]
    if developing:
        return "local_practice_ready"
    # All adequate or better across every dimension.
    if all(v in {"adequate_for_next_stage", "strong", "trainer_level"} for v in dimensions.values()):
        return "team_discernment_ready"
    return "cross_cultural_internship_ready"


def can_decide_deployment_candidate(*, decider_type: str, is_panel: bool,
                                    candidate_id: str, decider_id: str,
                                    hard_blocks) -> None:
    """Only an independent human panel may name a deployment candidate."""
    if decider_type == "ai":
        raise ValueError("AI cannot decide a deployment candidate")
    if candidate_id == decider_id:
        raise ValueError("a candidate cannot approve themselves")
    if not is_panel:
        raise ValueError("deployment candidate requires a human panel decision")
    if set(hard_blocks):
        raise ValueError("hard blocks must be cleared before a deployment candidate decision")


# ---- Skill 32: worker roles ------------------------------------------------
ROLE_FAMILIES = frozenset({
    "frontline_ministry", "church_equipping", "translation_and_language",
    "professional_service", "care_and_safeguarding", "technology_and_media",
    "research_and_strategy", "operations_and_support", "sending_and_mobilization",
})
# Roles that require a hard qualification/safeguarding gate before contact.
HARD_QUALIFICATION_ROLES = frozenset({
    "medical_worker", "nursing_and_care_worker", "children_and_family_worker",
    "trauma_and_member_care_worker", "education_worker", "special_education",
})


def role_requires_hard_qualification(role_key: str) -> bool:
    return role_key in HARD_QUALIFICATION_ROLES


# ---- Skill 33: match separation --------------------------------------------
MATCH_RECOMMENDATIONS = frozenset({
    "explore_role", "observe_role", "begin_training", "seek_mentor", "local_practicum",
    "team_discernment", "field_research_only", "support_role_match",
    "insufficient_evidence", "not_currently_suitable", "blocked_by_requirement",
})


def role_match(*, worker_levels: dict, required_levels: dict, missing_dimensions,
               hard_blocks) -> str:
    """Explainable role match. Missing data is NOT treated as deficiency; a high
    field need is not an input here (kept strictly separate from field match)."""
    if set(hard_blocks):
        return "blocked_by_requirement"
    if missing_dimensions:
        return "insufficient_evidence"
    order = {lvl: i for i, lvl in enumerate(DIMENSION_LEVELS)}
    gaps = [k for k, req in required_levels.items()
            if order.get(worker_levels.get(k, "unknown"), 0) < order.get(req, 0)]
    if not gaps:
        return "team_discernment"
    return "begin_training"


def assert_layers_separate(kind: str, upstream_kind: str | None) -> None:
    """Role match never auto-creates a field match; field match never auto-creates
    a deployment. Enforce the layering explicitly."""
    layers = {"role_match": None, "field_match": "role_match", "deployment": "field_match"}
    if kind not in layers:
        raise ValueError("invalid match layer")
    if layers[kind] != upstream_kind:
        raise ValueError(f"{kind} cannot be derived directly from {upstream_kind!r}")
