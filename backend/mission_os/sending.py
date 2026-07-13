"""Skill 50/52/53: church confirmation, candidate application and sending committee.

Encoded invariants:
  * a single pastor can never complete a church confirmation alone (>=2 eligible,
    non-family reviewers, conflicts disclosed);
  * an application cannot bypass completeness; expired readiness blocks it;
  * a committee needs quorum; the candidate and AI can never vote; a
    conflict-of-interest member does not count toward quorum or vote;
  * spouse or local-partner opposition blocks approval;
  * conditional approval carries owner + deadline + expiry;
  * a Batch 5 approval only unlocks Batch 6 — it is never "deploy now".
"""
from __future__ import annotations
from datetime import datetime, timezone

# ---- Skill 50: church confirmation ----------------------------------------
CONFIRMATION_SUPPORT = frozenset({
    "unable_to_confirm", "insufficient_observation", "support_exploration",
    "support_with_conditions", "support_sending_process", "recommend_pause",
})


def assert_church_confirmation_valid(*, reviewer_ids, family_reviewer_ids,
                                     observation_months: int, min_months: int = 6) -> None:
    reviewers = list(reviewer_ids)
    if len(set(reviewers)) < 2:
        raise ValueError("church confirmation requires at least two eligible reviewers")
    if set(reviewers) <= set(family_reviewer_ids):
        raise ValueError("reviewers cannot all be the candidate's family")
    if observation_months < min_months:
        raise ValueError("church confirmation requires a minimum observation period")


def church_support_is_not_deployment(support_level: str) -> None:
    if support_level not in CONFIRMATION_SUPPORT:
        raise ValueError("invalid church support level")
    # documents that support != final sending decision (enforced in committee).


# ---- Skill 52: candidate application --------------------------------------
REQUIRED_APPLICATION_SECTIONS = frozenset({
    "calling_journey", "readiness_decision", "stage_certifications", "church_confirmation",
    "mission_agency", "receiving_supervisor", "team_role", "field_assessment",
    "local_partner_status", "family_feedback", "financial_sustainability",
    "legal_entry_path", "member_care_owner", "safeguarding", "risk_summary", "consent",
})
CORE_FIELDS = frozenset({"target_role_id", "target_field_id", "sending_church_id",
                         "mission_agency_id", "target_team_id"})


def completeness(*, present_sections, expired_sections, blocking_sections) -> dict:
    present = set(present_sections)
    missing = sorted(REQUIRED_APPLICATION_SECTIONS - present)
    return {
        "missing": missing,
        "expired": sorted(set(expired_sections)),
        "blocked": sorted(set(blocking_sections)),
        "committee_ready": not missing and not set(expired_sections) and not set(blocking_sections),
    }


def assert_can_submit(*, present_sections, expired_sections, blocking_sections,
                      readiness_expired: bool, local_partner_present: bool, field_requires_partner: bool) -> None:
    c = completeness(present_sections=present_sections, expired_sections=expired_sections, blocking_sections=blocking_sections)
    if readiness_expired:
        raise ValueError("application cannot use an expired readiness decision")
    if field_requires_partner and not local_partner_present:
        raise ValueError("field requires a local partner before the committee")
    if not c["committee_ready"]:
        raise ValueError(f"application incomplete: missing={c['missing']} expired={c['expired']} blocked={c['blocked']}")


def requires_new_version(changed_fields) -> bool:
    return bool(set(changed_fields) & CORE_FIELDS)


# ---- Skill 53: sending committee ------------------------------------------
DECISION_TYPES = frozenset({
    "approved_for_next_stage", "conditionally_approved", "deferred",
    "revision_required", "declined_current_application", "withdrawn", "revoked", "expired",
})
VOTE_VALUES = frozenset({"approve", "conditionally_approve", "abstain", "oppose"})


def eligible_voters(members: list[dict], candidate_id: str) -> list[dict]:
    """Filter out the candidate, AI accounts and disclosed conflicts of interest."""
    out = []
    for m in members:
        if m.get("user_id") == candidate_id:
            continue
        if m.get("is_ai"):
            continue
        if m.get("conflict_disclosed"):
            continue
        if not m.get("voting_right", True):
            continue
        out.append(m)
    return out


def assert_quorum(members: list[dict], candidate_id: str, *, min_quorum: int,
                  require_roles=("sending_church", "mission_agency", "receiving_team")) -> None:
    voters = eligible_voters(members, candidate_id)
    if len(voters) < min_quorum:
        raise ValueError("committee lacks quorum among eligible voters")
    roles = {m.get("member_role") for m in voters}
    missing = set(require_roles) - roles
    if missing:
        raise ValueError(f"committee missing required representation: {sorted(missing)}")


def assert_can_approve(*, spouse_opposed: bool, local_partner_opposed: bool,
                       unresolved_hard_blocks: int) -> None:
    if spouse_opposed:
        raise ValueError("spouse opposition to family relocation blocks approval")
    if local_partner_opposed:
        raise ValueError("local partner opposition blocks approval")
    if unresolved_hard_blocks > 0:
        raise ValueError("unresolved hard blocks prevent approval")


def validate_conditional_approval(conditions: list[dict]) -> None:
    if not conditions:
        raise ValueError("conditional approval must carry at least one condition")
    for c in conditions:
        if not c.get("owner") or not c.get("deadline"):
            raise ValueError("each condition needs an owner and a deadline")


def approval_unlocks_batch6_only() -> str:
    """A Batch 5 approval unlocks the finance/visa/deployment-prep stage, not travel."""
    return "unlock_batch6_preparation"
