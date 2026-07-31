from __future__ import annotations

from .models import Actor, ConsentGrant, DataLevel, PastoralCase
from .policy import AccessPolicyEvaluator
from .safety import PastoralSafetyGuardian


class PastoralCollaborationOrchestrator:
    def __init__(self) -> None:
        self.policy = AccessPolicyEvaluator()
        self.guardian = PastoralSafetyGuardian()

    def request_access(
        self,
        actor: Actor,
        case: PastoralCase,
        consent: ConsentGrant | None,
        purpose: str,
        requested_level: DataLevel,
        conflict_present: bool = False,
        safety_basis: bool = False,
    ) -> dict:
        safety = self.guardian.review(case.purpose + " " + " ".join(case.safety_flags))
        if safety.status == "blocked":
            return {
                "decision": "denied",
                "reason": "safety_policy_block",
                "details": safety.reasons,
            }

        if safety.status == "safeguarding_review":
            return {
                "decision": "escalate",
                "reason": "safeguarding_review",
                "actions": safety.actions,
            }

        return self.policy.evaluate(
            actor=actor,
            case=case,
            consent=consent,
            purpose=purpose,
            requested_level=requested_level,
            conflict_present=conflict_present,
            safety_basis=safety_basis,
        )
