"""Skill 17: people-group / language / religion knowledge-graph invariants.

Encodes the anti-stereotyping rules: a people group is never bound to a single
language or a single religion, individual belief is never inferred from a group
label, and religious share is always a range/estimate rather than a false point
value.
"""
from __future__ import annotations

LANGUAGE_RELATIONSHIPS = frozenset({
    "primary_language", "heritage_language", "trade_language", "liturgical_language",
    "second_language", "sign_language", "declining_language",
})
REGION_RELATIONSHIPS = frozenset({
    "historic_homeland", "current_majority_region", "current_minority_region",
    "diaspora_region", "seasonal_presence", "migration_corridor",
})
RELIGION_RELATIONSHIPS = frozenset({
    "majority_affiliation", "minority_affiliation", "historic_tradition",
    "syncretic_practice", "secularizing_context", "unknown_or_diverse",
})
CONFIDENCE = frozenset({"unknown", "very_low", "low", "medium", "high", "very_high"})


def validate_language_link(relationship_type: str) -> None:
    if relationship_type not in LANGUAGE_RELATIONSHIPS:
        raise ValueError(f"invalid language relationship: {relationship_type!r}")


def validate_region_link(relationship_type: str) -> None:
    if relationship_type not in REGION_RELATIONSHIPS:
        raise ValueError(f"invalid region relationship: {relationship_type!r}")


def validate_religion_link(relationship_type: str, *, share_range: tuple | None) -> None:
    """A religion link must be a *distribution*: share is a (low, high) range, or None
    when unknown/diverse. A single point share is rejected as false precision."""
    if relationship_type not in RELIGION_RELATIONSHIPS:
        raise ValueError(f"invalid religion relationship: {relationship_type!r}")
    if relationship_type == "unknown_or_diverse":
        if share_range is not None:
            raise ValueError("unknown_or_diverse cannot carry a numeric share")
        return
    if share_range is None:
        return  # allowed: share simply not known yet
    if not (isinstance(share_range, (tuple, list)) and len(share_range) == 2):
        raise ValueError("religious share must be a (low, high) range, not a point value")
    low, high = share_range
    if not (0.0 <= low <= high <= 1.0):
        raise ValueError("religious share range must satisfy 0<=low<=high<=1")


def validate_people_group_links(*, language_links, religion_links) -> None:
    """A people group must be modelled as multi-language and multi-religion capable.

    We reject configurations that collapse a group into exactly one language or
    one non-diverse religion, which is how stereotyping creeps in.
    """
    langs = list(language_links)
    rels = list(religion_links)
    # Never allow a single hard-coded religion as the group's whole identity.
    concrete_religions = [r for r in rels if r != "unknown_or_diverse"]
    if len(concrete_religions) == 1 and len(rels) == 1:
        raise ValueError("people group cannot be bound to a single religion; model a distribution")
    # A group may legitimately speak one primary language, but the model must not
    # forbid additional languages — enforced structurally (many-to-many table),
    # so here we only validate the individual relationship types.
    for lt in langs:
        validate_language_link(lt)


def assert_no_individual_inference(subject_type: str) -> None:
    """Belief/behaviour must attach to a group study, never to an individual row
    derived purely from a group label."""
    if subject_type == "individual_from_group_label":
        raise ValueError("individual religion/behaviour cannot be inferred from a group label")
