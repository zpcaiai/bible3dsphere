"""State machine (BATCH_01_IMPLEMENTATION section 2)."""

import pytest

from backend.discernment_platform.batch01_core.models import CaseState, FailureCode
from backend.discernment_platform.batch01_core.state import MAX_RETRIES, StateMachine


def test_happy_path_transitions():
    machine = StateMachine()
    for state in (
        CaseState.SAFETY_CHECKED,
        CaseState.NORMALIZED,
        CaseState.CLAIMS_EXTRACTED,
        CaseState.WORLDVIEW_MAPPED,
        CaseState.PRIDE_HYPOTHESES_BUILT,
        CaseState.DESIRES_MAPPED,
        CaseState.QUESTIONS_PLANNED,
        CaseState.GOSPEL_BRIDGE_BUILT,
        CaseState.REPORT_COMPOSED,
        CaseState.READY,
        CaseState.DELIVERED,
    ):
        machine.to(state)
    assert machine.state is CaseState.DELIVERED


def test_illegal_transition_is_rejected():
    with pytest.raises(ValueError):
        StateMachine().to(CaseState.REPORT_COMPOSED)


def test_every_failure_code_routes_to_review():
    for code in FailureCode:
        machine = StateMachine()
        assert machine.fail(code) is CaseState.REVIEW_REQUIRED


def test_retry_budget_is_bounded():
    machine = StateMachine()
    assert all(machine.should_retry("skill") for _ in range(MAX_RETRIES))
    assert not machine.should_retry("skill")


def test_history_is_recorded():
    machine = StateMachine()
    machine.to(CaseState.SAFETY_CHECKED)
    machine.to(CaseState.NORMALIZED)
    assert machine.history == [
        CaseState.RECEIVED,
        CaseState.SAFETY_CHECKED,
        CaseState.NORMALIZED,
    ]


def test_gospel_stage_is_skippable():
    machine = StateMachine()
    for state in (
        CaseState.SAFETY_CHECKED,
        CaseState.NORMALIZED,
        CaseState.CLAIMS_EXTRACTED,
        CaseState.WORLDVIEW_MAPPED,
        CaseState.PRIDE_HYPOTHESES_BUILT,
        CaseState.DESIRES_MAPPED,
        CaseState.QUESTIONS_PLANNED,
        CaseState.REPORT_COMPOSED,
    ):
        machine.to(state)
    assert machine.state is CaseState.REPORT_COMPOSED
