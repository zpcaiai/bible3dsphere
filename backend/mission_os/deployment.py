"""Skill 70/71: digital security, emergency/evacuation, and the Deployment Readiness Gate.

Encoded invariants:
  * P4 data may not live on an unmanaged device; a lost device and a team exit
    both revoke access immediately; a security exception must carry an expiry;
  * an incident-command role set may not concentrate in one person on a high-risk
    team; evacuation triggers are concrete (never a vague feeling); AI never
    decides evacuation;
  * the Deployment Readiness Gate aggregates every Batch 6 signal, a hard block is
    never bypassable, the candidate/AI cannot decide it, and a Ready gate only
    unlocks the operational deployment-planning stage — it never marks the worker
    as deployed.
"""
from __future__ import annotations

# ---- Skill 70: digital security -------------------------------------------
SECURITY_TIERS = ("standard", "elevated", "high", "restricted")
SECURITY_CONTROLS = frozenset({
    "device_encryption", "screen_lock", "automatic_updates", "approved_apps", "mfa",
    "password_manager", "recovery_codes", "account_separation", "least_privilege",
    "secure_backup", "remote_wipe", "sensitive_file_encryption", "location_metadata_control",
    "secure_disposal", "incident_reporting", "travel_mode", "shared_device_mode",
    "offline_data_limit", "secure_printing", "access_review", "team_exit_revocation",
})


def assert_p4_storage(*, data_class: str, device_managed: bool) -> None:
    if data_class == "P4" and not device_managed:
        raise ValueError("P4 data may not be stored on an unmanaged device")


def access_revoked_on_lost_device(reported_lost: bool) -> bool:
    return reported_lost  # losing a device revokes tokens/sessions


def access_revoked_on_team_exit(membership_stage: str) -> bool:
    return membership_stage in {"ended", "transitioning_out"}


def assert_exception_has_expiry(expires_at) -> None:
    if expires_at is None:
        raise ValueError("a security exception must have an expiry")


def assert_shared_account_blocked(*, is_shared: bool, has_approved_exception: bool) -> None:
    if is_shared and not has_approved_exception:
        raise ValueError("shared accounts are blocked without an approved exception")


# ---- Skill 71: emergency & evacuation -------------------------------------
INCIDENT_COMMAND_ROLES = frozenset({
    "incident_commander", "deputy", "security_lead", "medical_lead", "family_liaison",
    "communications_lead", "finance_lead", "data_security_lead",
    "local_partner_liaison", "sending_church_liaison",
})
EVACUATION_TYPES = frozenset({
    "shelter_in_place", "relocation", "temporary_evacuation",
    "permanent_exit", "medical_evacuation",
})
CONCRETE_EVAC_TRIGGERS = frozenset({
    "official_evacuation_advisory", "medical_capacity_failure", "insurance_evac_condition",
    "child_safety", "imminent_violence", "identity_invalidated", "communication_outage",
    "supply_chain_failure", "critical_medication_unavailable", "team_capability_collapse",
    "receiving_org_cannot_support", "major_family_crisis",
})


def assert_command_not_concentrated(*, role_holders: dict, high_risk: bool) -> None:
    """On a high-risk team one person cannot hold every incident-command role."""
    if not high_risk:
        return
    people = set(role_holders.values())
    if role_holders and len(people) < 2:
        raise ValueError("incident-command roles must not concentrate in one person on a high-risk team")


def validate_evacuation_trigger(trigger: str) -> None:
    if trigger not in CONCRETE_EVAC_TRIGGERS:
        raise ValueError("evacuation triggers must be concrete conditions, not vague feelings")


def ai_may_decide_evacuation() -> bool:
    return False


# ---- Deployment Readiness Gate --------------------------------------------
GATE_INPUTS = (
    "sending_decision", "financial", "support_coverage", "reserve", "legal_identity",
    "credential", "compliance", "medical", "insurance", "family",
    "digital_security", "emergency", "drills",
)
GATE_HARD_BLOCKS = frozenset({
    "sending_decision_expired", "financial_underfunded", "reserve_insufficient",
    "credential_invalid", "identity_illegal_or_inconsistent", "compliance_hard_block",
    "medical_not_cleared", "insurance_critical_gap", "spouse_not_consenting",
    "child_education_or_safety_gap", "digital_security_p4_noncompliant",
    "no_emergency_plan", "required_drill_incomplete", "critical_finding_open",
    "team_or_partner_invalid", "unresolved_l2_l3_incident",
})
GATE_STATUS = frozenset({
    "not_started", "data_collection", "review_required", "blocked",
    "conditionally_ready", "ready_for_deployment_planning", "expired", "revoked",
})


def run_gate(*, hard_blocks, decider_type: str, is_panel: bool,
             candidate_id: str, decider_id: str) -> dict:
    """Aggregate all signals into a gate result. Hard blocks are never bypassable."""
    blocks = sorted(set(hard_blocks))
    for b in blocks:
        if b not in GATE_HARD_BLOCKS:
            raise ValueError(f"unknown gate hard block: {b!r}")
    if blocks:
        return {"status": "blocked", "blocking": blocks, "unlocks": "none"}
    # Deciding a clear gate requires an independent human panel.
    if decider_type == "ai":
        raise ValueError("AI cannot decide the deployment readiness gate")
    if candidate_id == decider_id:
        raise ValueError("a candidate cannot approve their own deployment gate")
    if not is_panel:
        raise ValueError("deployment readiness gate requires a human panel decision")
    return {"status": "ready_for_deployment_planning", "blocking": [], "unlocks": "deployment_planning"}


def gate_ready_activates_deployment() -> bool:
    """A Ready gate only unlocks the operational deployment-planning stage; it never
    activates a deployment or marks the worker as deployed."""
    return False
