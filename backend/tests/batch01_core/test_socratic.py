"""Skill 06 - socratic-question-planner."""

from backend.discernment_platform.batch01_core.claims import extract
from backend.discernment_platform.batch01_core.desire import map_desires
from backend.discernment_platform.batch01_core.intake import normalize
from backend.discernment_platform.batch01_core.models import FaithContext, QuestionStage, Sensitivity
from backend.discernment_platform.batch01_core.pride import detect
from backend.discernment_platform.batch01_core.socratic import (
    MAX_QUESTIONS_PER_TURN,
    next_question,
    plan,
    presumes_guilt,
)
from backend.discernment_platform.batch01_core.worldview import map_worldview


def _plan(normalized, defensiveness=False):
    claims = extract(normalized)
    wv = map_worldview(normalized, claims)
    hypotheses = detect(normalized, claims, wv)
    desires = map_desires(normalized, wv, hypotheses)
    return plan(normalized, claims, wv, hypotheses, desires, defensiveness)


def test_only_one_question_is_delivered_per_turn(influencer_normalized):
    assert len(next_question(_plan(influencer_normalized))) == MAX_QUESTIONS_PER_TURN


def test_questions_are_staged_and_ordered(influencer_normalized):
    questions = _plan(influencer_normalized)
    assert [q.order for q in questions] == sorted(q.order for q in questions)
    assert all(isinstance(q.stage, QuestionStage) for q in questions)


def test_every_question_declares_purpose_and_branches(influencer_normalized):
    for question in _plan(influencer_normalized):
        assert question.purpose
        assert question.branch_conditions


def test_no_question_presumes_guilt(influencer_normalized):
    assert not any(presumes_guilt(q) for q in _plan(influencer_normalized))


def test_defensiveness_returns_to_clarification(influencer_normalized):
    questions = _plan(influencer_normalized, defensiveness=True)
    assert len(questions) == 1
    assert questions[0].stage is QuestionStage.CLARIFY


def test_mental_health_reduces_law_pressure(scrupulosity_case):
    normalized = normalize(scrupulosity_case)
    assert normalized.sensitivity is Sensitivity.MENTAL_HEALTH
    stages = {q.stage for q in _plan(normalized)}
    assert QuestionStage.LAW not in stages
    assert QuestionStage.WORSHIP not in stages


def test_non_christian_gospel_stage_requires_consent(influencer_case):
    influencer_case.faith_context = FaithContext.SEEKER
    questions = _plan(normalize(influencer_case))
    gospel = [q for q in questions if q.stage is QuestionStage.GOSPEL]
    assert gospel and gospel[0].requires_consent


def test_gospel_stage_dropped_without_consent(influencer_case):
    influencer_case.consent_scope.allow_gospel_bridge = False
    stages = {q.stage for q in _plan(normalize(influencer_case))}
    assert QuestionStage.GOSPEL not in stages


def test_does_not_stack_ten_questions_at_the_user(influencer_normalized):
    assert len(next_question(_plan(influencer_normalized))) < 10
