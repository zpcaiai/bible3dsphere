"""Skill 58/59/60: local partners, agreements and support/prayer networks.

Encoded invariants:
  * partnership requires a two-way (mutual) assessment; a local partner may veto;
    funding never buys control or decision rights;
  * safeguarding decisions cannot be vetoed by the funder; data sharing needs
    consent; an expired agreement stops data access; an exit plan is mandatory;
  * prayer/support updates never carry P3/P4 (locations, contacts); a crisis
    pauses scheduled communications; funders gain no governance.
"""
from __future__ import annotations
from datetime import datetime, timezone

# ---- Skill 58: local partner ----------------------------------------------
PARTNER_STATUS = frozenset({
    "candidate", "researching", "mutual_assessment", "due_diligence",
    "approved_for_limited_collaboration", "approved", "conditional",
    "paused", "suspended", "ended", "do_not_engage",
})


def assert_can_approve_partner(*, has_mutual_assessment: bool, status_target: str) -> None:
    if status_target in {"approved"} and not has_mutual_assessment:
        raise ValueError("long-term partner approval requires a two-way mutual assessment")


def partner_opposition_blocks(*, partner_opposed: bool) -> None:
    if partner_opposed:
        raise ValueError("a local partner's objection blocks the sending flow")


def funding_grants_no_control(decision_rights: dict, providing_party_role: str) -> None:
    """A funding party cannot hold decide/veto over program strategy or safeguarding."""
    if providing_party_role == "funding_partner":
        for domain in ("safeguarding", "program_strategy", "participant_eligibility"):
            right = decision_rights.get(domain)
            if right in {"decide", "veto"}:
                raise ValueError("a funder cannot hold decide/veto over safeguarding or program strategy")


# ---- Skill 59: agreements --------------------------------------------------
DECISION_VERBS = frozenset({"decide", "approve", "consult", "inform", "veto", "escalate"})
REQUIRED_AGREEMENT_SECTIONS = frozenset({
    "decision_rights", "data_protection", "intellectual_property",
    "complaints", "termination", "transition",
})


def assert_safeguarding_not_funder_vetoable(decision_rights: dict) -> None:
    sg = decision_rights.get("safeguarding", {})
    if isinstance(sg, dict) and "funding_partner" in (sg.get("veto_parties") or []):
        raise ValueError("safeguarding decisions cannot be vetoed by the funder")


def assert_agreement_complete(sections, *, has_exit_plan: bool, has_local_decision_rights: bool) -> None:
    missing = REQUIRED_AGREEMENT_SECTIONS - set(sections)
    if missing:
        raise ValueError(f"agreement missing sections: {sorted(missing)}")
    if not has_exit_plan:
        raise ValueError("agreement must include an exit/transition plan")
    if not has_local_decision_rights:
        raise ValueError("agreement must grant the local partner explicit decision rights")


def data_access_allowed(*, agreement_active: bool, expires_at: datetime | None,
                        individual_consent: bool, now: datetime | None = None) -> bool:
    """Data sharing needs an active, unexpired agreement AND individual consent."""
    now = now or datetime.now(timezone.utc)
    if not agreement_active or not individual_consent:
        return False
    if expires_at is not None and (expires_at.tzinfo is None or expires_at <= now):
        return False  # expired agreement stops access
    return True


def forbids_legal_report_waiver(clauses) -> None:
    if "waive_legal_report" in set(clauses):
        raise ValueError("an agreement cannot forbid a lawful report")


# ---- Skill 60: support & prayer networks ----------------------------------
UPDATE_VISIBILITY = frozenset({
    "public", "registered_supporters", "sending_church_only",
    "care_team_only", "restricted_named_audience", "emergency_team_only",
})
# Field keys that must never appear in a normal prayer/support update.
FORBIDDEN_UPDATE_KEYS = frozenset({
    "sensitive_location", "exact_location", "local_believer_names",
    "partner_contacts", "financial_detail", "mental_health_detail",
})


def assert_update_clean(field_keys) -> None:
    leaked = sorted(set(field_keys) & FORBIDDEN_UPDATE_KEYS)
    if leaked:
        raise ValueError(f"prayer/support update cannot include sensitive keys: {leaked}")


def scheduled_send_allowed(*, crisis_active: bool) -> bool:
    """A crisis pauses scheduled communications automatically."""
    return not crisis_active


def funder_gets_no_governance(support_role: str, requested_permission: str) -> None:
    if support_role == "financial_supporter" and requested_permission in {"governance", "approval", "decide"}:
        raise ValueError("financial support does not grant governance or approval rights")


def unsubscribe_takes_effect_immediately(is_unsubscribed: bool) -> bool:
    return not is_unsubscribed  # returns whether the supporter still receives updates
