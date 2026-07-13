"""Skill 54/55/56/57: mission teams, capability, covenant and health/complaints.

Encoded invariants:
  * a team leader cannot approve their own membership; a spouse is never an
    automatic member; exit closes access;
  * a single member cannot cover conflicting safety-critical roles (single point
    of failure); capacity accounts for language/family/rest (not 168h);
  * a covenant may not contain absolute-obedience or no-exit clauses and must
    include local-partner rights, appeal and exit;
  * a team leader cannot investigate a complaint against themselves; a critical
    health issue blocks sending.
"""
from __future__ import annotations

MEMBERSHIP_STAGE = frozenset({
    "invited", "discernment", "provisional", "probation", "active",
    "on_leave", "transitioning_out", "ended",
})


def assert_membership_approval(*, approver_id: str, candidate_id: str, is_leader_self: bool) -> None:
    if approver_id == candidate_id or is_leader_self:
        raise ValueError("a team leader cannot approve their own membership")


def assert_spouse_not_auto_member(*, is_spouse: bool, has_own_membership_decision: bool) -> None:
    if is_spouse and not has_own_membership_decision:
        raise ValueError("a spouse is never an automatic team member")


def access_after_exit(stage: str) -> bool:
    """Return whether the member retains access. Ended/transitioning closes it."""
    return stage not in {"ended", "transitioning_out"}


# ---- Skill 55: capability & single point of failure ------------------------
SAFETY_CRITICAL_CAPABILITIES = frozenset({
    "safeguarding", "member_care", "security", "legal_and_compliance",
})


def detect_single_point_of_failure(coverage: dict) -> list[str]:
    """coverage: capability -> list of member ids. Safety-critical capabilities
    with only one qualified member are single points of failure."""
    spof = []
    for cap in SAFETY_CRITICAL_CAPABILITIES:
        members = coverage.get(cap, [])
        if len(set(members)) < 2:
            spof.append(cap)
    return sorted(spof)


def assert_no_role_conflict(*, safeguarding_officer_id: str, complaint_investigator_id: str,
                            sole_appeal_handler: bool) -> None:
    """The safeguarding officer cannot also be the sole appeal handler."""
    if safeguarding_officer_id and safeguarding_officer_id == complaint_investigator_id and sole_appeal_handler:
        raise ValueError("safety and appeal roles must not concentrate in one person")


def team_capacity_hours(*, work_hours: float, language_hours: float, family_hours: float,
                        rest_hours: float, admin_hours: float) -> float:
    """Available ministry capacity after non-negotiable commitments. Never assume
    a 168-hour week is all deployable."""
    committed = language_hours + family_hours + rest_hours + admin_hours
    available = work_hours - committed
    return max(0.0, available)


def high_need_cannot_bypass_gap(*, has_critical_gap: bool, field_need_high: bool) -> None:
    if has_critical_gap and field_need_high:
        # need never removes a real capability gap
        raise ValueError("a high field need cannot bypass a critical team capability gap")


# ---- Skill 56: covenant clauses -------------------------------------------
FORBIDDEN_COVENANT_CLAUSES = frozenset({
    "absolute_obedience", "no_exit", "waive_legal_report", "waive_medical_help",
    "auto_bind_spouse", "waive_appeal", "surrender_personal_property",
})
REQUIRED_COVENANT_SECTIONS = frozenset({
    "local_partner_rights", "complaints_and_appeals", "exit_and_transition", "safeguarding",
})


def validate_covenant(*, clauses, sections) -> None:
    bad = set(clauses) & FORBIDDEN_COVENANT_CLAUSES
    if bad:
        raise ValueError(f"covenant contains forbidden clauses: {sorted(bad)}")
    missing = REQUIRED_COVENANT_SECTIONS - set(sections)
    if missing:
        raise ValueError(f"covenant missing required sections: {sorted(missing)}")


# ---- Skill 57: team health & complaints -----------------------------------
HEALTH_LEVELS = ("green", "attention", "significant_concern", "critical")


def assert_complaint_investigator(*, accused_id: str, investigator_id: str) -> None:
    if accused_id and accused_id == investigator_id:
        raise ValueError("the accused (e.g. team leader) cannot investigate the complaint against themselves")


def critical_health_blocks_sending(level: str) -> bool:
    return level == "critical"


def anonymity_threshold_met(response_count: int, *, min_responses: int = 4) -> bool:
    """Small teams cannot be aggregated anonymously below the threshold."""
    return response_count >= min_responses
