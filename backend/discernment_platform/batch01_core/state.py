"""Explicit state machine for the Batch 01 pipeline (BATCH_01_IMPLEMENTATION §2)."""

from __future__ import annotations

from .models import CaseState, FailureCode

TRANSITIONS: dict[CaseState, tuple[CaseState, ...]] = {
    CaseState.RECEIVED: (CaseState.SAFETY_CHECKED,),
    CaseState.SAFETY_CHECKED: (CaseState.NORMALIZED, CaseState.REVIEW_REQUIRED),
    CaseState.NORMALIZED: (CaseState.CLAIMS_EXTRACTED,),
    CaseState.CLAIMS_EXTRACTED: (CaseState.WORLDVIEW_MAPPED,),
    CaseState.WORLDVIEW_MAPPED: (CaseState.PRIDE_HYPOTHESES_BUILT,),
    CaseState.PRIDE_HYPOTHESES_BUILT: (CaseState.DESIRES_MAPPED,),
    CaseState.DESIRES_MAPPED: (CaseState.QUESTIONS_PLANNED,),
    CaseState.QUESTIONS_PLANNED: (
        CaseState.GOSPEL_BRIDGE_BUILT,
        CaseState.REPORT_COMPOSED,
    ),
    CaseState.GOSPEL_BRIDGE_BUILT: (CaseState.REPORT_COMPOSED,),
    CaseState.REPORT_COMPOSED: (CaseState.REVIEW_REQUIRED, CaseState.READY),
    CaseState.REVIEW_REQUIRED: (CaseState.READY, CaseState.DELIVERED),
    CaseState.READY: (CaseState.DELIVERED,),
    CaseState.DELIVERED: (),
}

FAILURE_TARGET: dict[FailureCode, CaseState] = {
    FailureCode.INSUFFICIENT_EVIDENCE: CaseState.REVIEW_REQUIRED,
    FailureCode.HIGH_RISK_REVIEW: CaseState.REVIEW_REQUIRED,
    FailureCode.UNSUPPORTED_THEOLOGICAL_CLAIM: CaseState.REVIEW_REQUIRED,
    FailureCode.MODEL_OUTPUT_INVALID: CaseState.REVIEW_REQUIRED,
    FailureCode.USER_CONSENT_REQUIRED: CaseState.REVIEW_REQUIRED,
}

MAX_RETRIES = 2


class StateMachine:
    def __init__(self, state: CaseState = CaseState.RECEIVED) -> None:
        self.state = state
        self.history: list[CaseState] = [state]
        self.failures: list[FailureCode] = []
        self.retries: dict[str, int] = {}

    def can(self, target: CaseState) -> bool:
        return target in TRANSITIONS[self.state]

    def to(self, target: CaseState) -> CaseState:
        if not self.can(target):
            raise ValueError(f"illegal transition {self.state.value} -> {target.value}")
        self.state = target
        self.history.append(target)
        return self.state

    def fail(self, code: FailureCode) -> CaseState:
        self.failures.append(code)
        target = FAILURE_TARGET[code]
        self.state = target
        self.history.append(target)
        return self.state

    def should_retry(self, skill_id: str) -> bool:
        count = self.retries.get(skill_id, 0)
        if count >= MAX_RETRIES:
            return False
        self.retries[skill_id] = count + 1
        return True
