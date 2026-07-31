from __future__ import annotations

from .models import EscalationState


TRANSITIONS = {
    EscalationState.ROUTINE: {EscalationState.REVIEW_NEEDED, EscalationState.CLOSED},
    EscalationState.REVIEW_NEEDED: {
        EscalationState.PASTORAL_REVIEW,
        EscalationState.SAFEGUARDING_REVIEW,
        EscalationState.CONSENT_REVIEW,
        EscalationState.CONFLICT_OF_INTEREST_HOLD,
    },
    EscalationState.PASTORAL_REVIEW: {
        EscalationState.STABILIZED,
        EscalationState.PROFESSIONAL_REFERRAL,
        EscalationState.SAFEGUARDING_REVIEW,
        EscalationState.FOLLOW_UP,
    },
    EscalationState.SAFEGUARDING_REVIEW: {
        EscalationState.PROFESSIONAL_REFERRAL,
        EscalationState.LEGAL_DUTY_REVIEW,
        EscalationState.EXTERNAL_REPORT_REQUIRED,
        EscalationState.EMERGENCY_ACTION,
        EscalationState.STABILIZED,
    },
    EscalationState.PROFESSIONAL_REFERRAL: {
        EscalationState.STABILIZED,
        EscalationState.FOLLOW_UP,
    },
    EscalationState.EMERGENCY_ACTION: {
        EscalationState.STABILIZED,
        EscalationState.FOLLOW_UP,
    },
    EscalationState.STABILIZED: {
        EscalationState.FOLLOW_UP,
        EscalationState.CLOSED,
    },
    EscalationState.FOLLOW_UP: {
        EscalationState.CLOSED,
        EscalationState.REVIEW_NEEDED,
        EscalationState.APPEAL_OR_SECOND_REVIEW,
    },
    EscalationState.CONFLICT_OF_INTEREST_HOLD: {
        EscalationState.REVIEW_NEEDED,
        EscalationState.APPEAL_OR_SECOND_REVIEW,
    },
    EscalationState.CONSENT_REVIEW: {
        EscalationState.REVIEW_NEEDED,
        EscalationState.CLOSED,
    },
    EscalationState.LEGAL_DUTY_REVIEW: {
        EscalationState.EXTERNAL_REPORT_REQUIRED,
        EscalationState.SAFEGUARDING_REVIEW,
    },
    EscalationState.EXTERNAL_REPORT_REQUIRED: {
        EscalationState.STABILIZED,
        EscalationState.FOLLOW_UP,
    },
    EscalationState.APPEAL_OR_SECOND_REVIEW: {
        EscalationState.FOLLOW_UP,
        EscalationState.CLOSED,
    },
    EscalationState.CLOSED: set(),
}


class EscalationStateMachine:
    def can_transition(self, current: EscalationState, target: EscalationState) -> bool:
        return target in TRANSITIONS[current]

    def transition(self, current: EscalationState, target: EscalationState) -> EscalationState:
        if not self.can_transition(current, target):
            raise ValueError(f"Invalid escalation transition: {current} -> {target}")
        return target
