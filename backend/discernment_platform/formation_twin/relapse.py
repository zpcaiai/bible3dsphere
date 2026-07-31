from __future__ import annotations

from .models import RelapseState


TRANSITIONS = {
    RelapseState.STABLE: {RelapseState.VULNERABLE, RelapseState.TRIGGERED},
    RelapseState.VULNERABLE: {RelapseState.TRIGGERED, RelapseState.STABLE},
    RelapseState.TRIGGERED: {RelapseState.OLD_PATTERN_ACTIVE, RelapseState.AWARENESS},
    RelapseState.OLD_PATTERN_ACTIVE: {
        RelapseState.CONSEQUENCE_VISIBLE,
        RelapseState.AWARENESS,
        RelapseState.UNACKNOWLEDGED,
        RelapseState.SHAME_SPIRAL,
    },
    RelapseState.CONSEQUENCE_VISIBLE: {
        RelapseState.AWARENESS,
        RelapseState.AVOIDANCE,
        RelapseState.HUMAN_SUPPORT_REQUIRED,
    },
    RelapseState.AWARENESS: {
        RelapseState.RETURN_TO_GOSPEL,
        RelapseState.AVOIDANCE,
        RelapseState.SHAME_SPIRAL,
    },
    RelapseState.RETURN_TO_GOSPEL: {RelapseState.REPAIR, RelapseState.REINTEGRATED},
    RelapseState.REPAIR: {RelapseState.REINTEGRATED, RelapseState.HUMAN_SUPPORT_REQUIRED},
    RelapseState.REINTEGRATED: {RelapseState.STABLE, RelapseState.VULNERABLE},
    RelapseState.UNACKNOWLEDGED: {RelapseState.AWARENESS, RelapseState.HUMAN_SUPPORT_REQUIRED},
    RelapseState.SHAME_SPIRAL: {RelapseState.RETURN_TO_GOSPEL, RelapseState.SAFETY_HOLD},
    RelapseState.AVOIDANCE: {RelapseState.AWARENESS, RelapseState.HUMAN_SUPPORT_REQUIRED},
    RelapseState.SAFETY_HOLD: {RelapseState.HUMAN_SUPPORT_REQUIRED},
    RelapseState.HUMAN_SUPPORT_REQUIRED: {
        RelapseState.AWARENESS,
        RelapseState.REPAIR,
        RelapseState.SAFETY_HOLD,
    },
}


class RelapseStateMachine:
    def can_transition(self, current: RelapseState, target: RelapseState) -> bool:
        return target in TRANSITIONS[current]

    def transition(self, current: RelapseState, target: RelapseState) -> RelapseState:
        if not self.can_transition(current, target):
            raise ValueError(f"Invalid relapse transition: {current} -> {target}")
        return target
