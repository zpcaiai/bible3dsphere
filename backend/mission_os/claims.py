"""Skill 22/23: Source / Snapshot / Claim-Evidence and conflict handling.

Every important field-intelligence conclusion is a Claim backed by Evidence.
Encoded invariants:
  * an AI-produced claim can only ever be an `ai_candidate`;
  * a claim cannot become `supported` without at least one supporting evidence;
  * a numeric/statistic claim must carry an as-of date (no undated "current");
  * `locally_confirmed` requires a local reviewer;
  * conflicting claims are never silently overwritten — both may be retained.
"""
from __future__ import annotations
from datetime import datetime

CLAIM_TYPES = frozenset({
    "observed_fact", "reported_statistic", "reported_assessment", "local_testimony",
    "researcher_interpretation", "strategic_hypothesis", "ai_candidate", "theological_reflection",
})
NUMERIC_CLAIM_TYPES = frozenset({"reported_statistic"})

EVIDENCE_STANCE = frozenset({
    "supports", "partially_supports", "contradicts", "contextualizes", "supersedes", "uncertain",
})
CLAIM_STATUS = frozenset({
    "candidate", "under_review", "supported", "locally_confirmed",
    "disputed", "outdated", "rejected", "superseded",
})
CONFLICT_RESOLUTIONS = frozenset({
    "detected", "triaged", "research_required", "local_review_required",
    "resolved_keep_both", "resolved_prefer_a", "resolved_prefer_b",
    "resolved_new_claim", "unresolved",
})

CREATOR_TYPES = frozenset({"human", "ai", "system"})


def validate_new_claim(*, claim_type: str, created_by_type: str,
                       normalized_value: dict | None, as_of_date: datetime | None) -> str:
    """Validate a claim at creation and return its initial status."""
    if claim_type not in CLAIM_TYPES:
        raise ValueError(f"invalid claim type: {claim_type!r}")
    if created_by_type not in CREATOR_TYPES:
        raise ValueError(f"invalid creator type: {created_by_type!r}")
    # AI can only ever create a candidate claim.
    if created_by_type == "ai" and claim_type != "ai_candidate":
        raise ValueError("AI may only create ai_candidate claims")
    if claim_type == "ai_candidate" and created_by_type != "ai":
        # allow system too, but never a human masquerading a candidate as fact
        if created_by_type != "system":
            raise ValueError("ai_candidate claims must be created by the AI/system")
    # Numeric claims must be dated.
    if claim_type in NUMERIC_CLAIM_TYPES:
        if as_of_date is None:
            raise ValueError("statistic claims require an as_of_date")
        if normalized_value is not None and "unit" not in normalized_value:
            raise ValueError("statistic claims must record a unit")
    return "candidate"


def can_promote(*, current_status: str, target_status: str, evidence_count: int,
                supporting_evidence_count: int, has_local_reviewer: bool,
                created_by_type: str) -> None:
    """Raise unless a claim may move to *target_status*."""
    if current_status not in CLAIM_STATUS or target_status not in CLAIM_STATUS:
        raise ValueError("invalid claim status")
    if target_status == "under_review" and evidence_count < 1:
        raise ValueError("a claim needs at least one evidence to enter review")
    if target_status == "supported":
        if supporting_evidence_count < 1:
            raise ValueError("cannot mark supported without supporting evidence")
        if created_by_type == "ai":
            raise ValueError("an ai_candidate cannot be promoted to supported without human evidence")
    if target_status == "locally_confirmed" and not has_local_reviewer:
        raise ValueError("locally_confirmed requires a local reviewer")


def resolve_conflict(resolution: str) -> str:
    if resolution not in CONFLICT_RESOLUTIONS:
        raise ValueError(f"invalid conflict resolution: {resolution!r}")
    return resolution


def snapshot_is_immutable(existing_hash: str | None, new_hash: str | None) -> None:
    """A captured source snapshot cannot be silently overwritten with new content."""
    if existing_hash is not None and new_hash is not None and existing_hash != new_hash:
        raise ValueError("source snapshot is immutable; capture a new snapshot instead")
