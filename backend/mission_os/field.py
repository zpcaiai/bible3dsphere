"""Skill 16/21/24: MissionField model and explainable field assessment.

Pure-python invariants. Two hard rules encoded here:
  * public field DTOs never carry P3/P4 sensitive geography/partner data;
  * a field assessment reports Need / Evidence / Readiness / Risk as *separate*
    scores, and a hard block can never be bought off by a high Need score.
"""
from __future__ import annotations
from dataclasses import dataclass, field as _dc_field

GEOGRAPHIC_TYPES = frozenset({
    "geographic_region", "country", "province_or_state", "city", "urban_district", "rural_area",
})
NON_GEOGRAPHIC_TYPES = frozenset({
    "people_group", "language_community", "diaspora_community", "migrant_worker_community",
    "international_student_community", "professional_community", "digital_community",
    "church_internal_group", "caregiver_community", "accessibility_community", "ministry_network",
})
FIELD_TYPES = GEOGRAPHIC_TYPES | NON_GEOGRAPHIC_TYPES

LIFECYCLE_STATUS = frozenset({"draft", "active", "inactive", "merged", "archived"})
RESEARCH_STATUS = frozenset({
    "unresearched", "initial_research", "evidence_gathering",
    "local_validation_pending", "locally_validated", "review_required", "disputed",
})
DATA_CONFIDENCE = frozenset({"unknown", "low", "medium", "high", "locally_verified"})

RELATIONSHIP_TYPES = frozenset({
    "contains", "overlaps", "migration_source_for", "migration_destination_for",
    "diaspora_of", "language_related_to", "ministry_connected_to",
    "historically_related_to", "do_not_merge_with",
})

# Fields that must never appear in a public field DTO (P3/P4 geography & partners).
SENSITIVE_FIELD_KEYS = frozenset({
    "sensitive_geometry_reference", "sensitive_location_reference",
    "local_partner_contacts", "non_public_church_info", "security_notes",
    "high_risk_entry_details", "encrypted_contact_reference",
})


@dataclass(frozen=True)
class MissionFieldProfile:
    field_id: str
    tenant_id: str
    field_type: str
    canonical_name: str
    country_code: str | None = None

    def validate(self) -> "MissionFieldProfile":
        if self.field_type not in FIELD_TYPES:
            raise ValueError(f"invalid field type: {self.field_type!r}")
        if not self.canonical_name.strip():
            raise ValueError("field requires a canonical name")
        if self.country_code is not None and (len(self.country_code) != 2 or not self.country_code.isalpha()):
            raise ValueError("country code must be ISO alpha-2")
        # Geographic fields anchor to a country; non-geographic fields must not be
        # silently treated as a country/region.
        if self.field_type in {"country", "province_or_state", "city", "urban_district", "rural_area"} and not self.country_code:
            raise ValueError("geographic sub-national field requires a country_code")
        return self


def public_field_dto(record: dict) -> dict:
    """Strip sensitive keys so a public DTO can never leak P3/P4 data."""
    return {k: v for k, v in record.items() if k not in SENSITIVE_FIELD_KEYS}


def assert_public_dto_clean(field_names) -> None:
    leaked = sorted(set(field_names) & SENSITIVE_FIELD_KEYS)
    if leaked:
        raise ValueError(f"public field DTO cannot expose sensitive keys: {leaked}")


# ---- Skill 24: explainable field assessment --------------------------------

RECOMMENDATIONS = frozenset({
    "pray_and_research", "improve_data_quality", "request_local_validation",
    "build_local_partnership", "begin_language_learning", "conduct_local_exposure",
    "begin_training", "form_team", "candidate_for_team_discernment",
    "professional_support_opportunity", "digital_support_opportunity",
    "not_ready", "pause_due_to_risk", "do_not_proceed", "review_required",
})

# Hard blocks: if any is present, the engine can never output an "enter now"
# recommendation, regardless of how high the Need score is.
HARD_BLOCK_KEYS = frozenset({
    "no_legal_entry_path", "no_sending_church", "no_receiving_team",
    "no_local_partner_when_required", "unmitigated_high_risk",
    "children_program_without_safeguarding", "data_quality_too_low",
    "primary_conclusion_from_ai_candidate", "local_partner_opposed",
    "worker_or_team_readiness_failed",
})

_ENTER_RECOMMENDATIONS = frozenset({
    "form_team", "candidate_for_team_discernment",
    "professional_support_opportunity", "digital_support_opportunity",
})


@dataclass(frozen=True)
class FieldAssessmentResult:
    need_score: float          # 0..1 — how great the need is
    evidence_score: float      # 0..1 — how trustworthy the evidence is
    readiness_score: float     # 0..1 — how ready the org/team currently is
    risk_level: str            # low|medium|high|critical
    hard_blocks: tuple = ()
    recommendation: str = "review_required"

    def is_blocked(self) -> bool:
        return bool(self.hard_blocks)


def _clamp(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else float(x)


def assess_field(*, need_score: float, evidence_score: float, readiness_score: float,
                 risk_level: str, hard_blocks=()) -> FieldAssessmentResult:
    """Return four independent signals plus an explainable recommendation.

    Never collapses to a single number; never lets Need override a hard block.
    """
    if risk_level not in {"low", "medium", "high", "critical"}:
        raise ValueError("invalid risk level")
    blocks = tuple(sorted(set(hard_blocks)))
    for b in blocks:
        if b not in HARD_BLOCK_KEYS:
            raise ValueError(f"unknown hard block: {b!r}")
    need = _clamp(need_score)
    evidence = _clamp(evidence_score)
    readiness = _clamp(readiness_score)

    if blocks:
        # A hard block forces a non-entry recommendation.
        if "unmitigated_high_risk" in blocks or risk_level == "critical":
            rec = "pause_due_to_risk"
        elif "data_quality_too_low" in blocks or "primary_conclusion_from_ai_candidate" in blocks:
            rec = "improve_data_quality"
        elif "no_local_partner_when_required" in blocks or "local_partner_opposed" in blocks:
            rec = "build_local_partnership"
        else:
            rec = "not_ready"
        return FieldAssessmentResult(need, evidence, readiness, risk_level, blocks, rec)

    # No hard blocks: choose the least-cost next step by weakest signal.
    if evidence < 0.4:
        rec = "improve_data_quality"
    elif need >= 0.5 and readiness < 0.4:
        rec = "begin_training"
    elif need >= 0.5 and 0.4 <= readiness < 0.7:
        rec = "conduct_local_exposure"
    elif need >= 0.5 and readiness >= 0.7 and risk_level in {"low", "medium"}:
        rec = "candidate_for_team_discernment"
    elif need < 0.5:
        rec = "pray_and_research"
    else:
        rec = "review_required"

    # Defence in depth: high risk can never yield an enter-type recommendation.
    if risk_level in {"high", "critical"} and rec in _ENTER_RECOMMENDATIONS:
        rec = "review_required"
    return FieldAssessmentResult(need, evidence, readiness, risk_level, (), rec)
