from __future__ import annotations

from .models import Actor, ConsentGrant, DataLevel, PastoralCase


ROLE_LEVELS = {
    "self_user": {DataLevel.L0, DataLevel.L1, DataLevel.L2},
    "accountability_partner": {DataLevel.L0},
    "small_group_leader": {DataLevel.L0},
    "mentor_discipler": {DataLevel.L0, DataLevel.L1},
    "pastor_elder": {DataLevel.L0, DataLevel.L1, DataLevel.L2},
    "safeguarding_officer": {DataLevel.L2, DataLevel.L3},
    "licensed_professional": {DataLevel.L2},
    "governance_review_panel": {DataLevel.L3},
}


class AccessPolicyEvaluator:
    def evaluate(
        self,
        actor: Actor,
        case: PastoralCase,
        consent: ConsentGrant | None,
        purpose: str,
        requested_level: DataLevel,
        conflict_present: bool,
        safety_basis: bool = False,
    ) -> dict:
        if actor.status != "active":
            return {"decision": "denied", "reason": "actor_inactive"}

        if conflict_present:
            return {"decision": "denied", "reason": "conflict_of_interest"}

        if not purpose.strip():
            return {"decision": "denied", "reason": "purpose_required"}

        allowed_by_role = any(
            requested_level in ROLE_LEVELS.get(role, set())
            for role in actor.roles
        )
        if not allowed_by_role:
            return {"decision": "denied", "reason": "role_not_permitted"}

        if safety_basis:
            return {"decision": "allowed", "reason": "documented_safety_basis"}

        if consent is None or consent.status != "active":
            return {"decision": "denied", "reason": "active_consent_required"}

        if consent.recipient_actor_id != actor.actor_id:
            return {"decision": "denied", "reason": "consent_recipient_mismatch"}

        if consent.purpose != purpose:
            return {"decision": "denied", "reason": "purpose_mismatch"}

        if requested_level.value not in consent.allowed_categories:
            return {"decision": "denied", "reason": "category_not_consented"}

        return {"decision": "allowed", "reason": "role_attributes_and_consent_match"}
