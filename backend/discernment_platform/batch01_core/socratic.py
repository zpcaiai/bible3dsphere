"""Skill 06 - socratic-question-planner (planner).

One core question per turn; ten ordered stages; consent gate before the
gospel layer; reduced law pressure for scrupulosity and religious trauma.
"""

from __future__ import annotations

from . import taxonomy
from .models import (
    Claim,
    DesireChain,
    FaithContext,
    NormalizedCase,
    PrideHypothesis,
    QuestionStage,
    Sensitivity,
    SocraticQuestion,
    WorldviewMap,
)

SKILL_ID = "socratic-question-planner"
SKILL_VERSION = "0.1.0"

MAX_QUESTIONS_PER_TURN = 1

_PRESUMPTIVE = ("你为什么这么骄傲", "你是不是在自义", "承认吧", "难道你不觉得")


def plan(
    case: NormalizedCase,
    claims: list[Claim],
    worldview: WorldviewMap,
    hypotheses: list[PrideHypothesis],
    desires: list[DesireChain],
    defensiveness: bool = False,
) -> list[SocraticQuestion]:
    """Plan a staged question path. Never stacks ten questions on the user."""

    reduce_law = case.sensitivity in (
        Sensitivity.MENTAL_HEALTH,
        Sensitivity.ABUSE,
        Sensitivity.CRISIS,
    )
    needs_consent = case.faith_context is not FaithContext.CHRISTIAN
    gospel_allowed = case.consent_scope.allow_gospel_bridge

    if defensiveness:
        return _de_escalated(case)

    questions: list[SocraticQuestion] = []
    order = 0
    for stage in QuestionStage:
        if stage in taxonomy.LAW_PRESSURE_STAGES and reduce_law:
            continue
        if stage is QuestionStage.GOSPEL and not gospel_allowed:
            continue
        template, purpose = taxonomy.STAGE_TEMPLATES[stage]
        order += 1
        questions.append(
            SocraticQuestion(
                question_id=f"q-{order:03d}",
                stage=stage,
                order=order,
                question=template.format(topic=case.topic[:20]),
                purpose=purpose,
                difficulty=min(5, 1 + stage.order // 3),
                expected_risk=_risk_for(stage, reduce_law),
                branch_conditions=_branches(stage),
                requires_consent=(
                    stage in taxonomy.CONSENT_REQUIRED_STAGES and needs_consent
                ),
                presumes_guilt=False,
            )
        )

    if hypotheses:
        questions = _personalise(questions, hypotheses[0])
    if desires and not desires[0].candidate:
        questions = _anchor_worship(questions, desires[0])
    return questions


def _risk_for(stage: QuestionStage, reduce_law: bool) -> str:
    if stage in taxonomy.LAW_PRESSURE_STAGES:
        return "high" if reduce_law else "moderate"
    if stage in (QuestionStage.HEART, QuestionStage.GOSPEL):
        return "moderate"
    return "low"


def _branches(stage: QuestionStage) -> dict:
    return {
        "if_defensive": "回到澄清与共情，不继续加压",
        "if_engaged": f"进入第 {stage.order + 1} 阶段",
        "if_unsure": "停留在本阶段，换一个更具体的问法",
    }


def _personalise(
    questions: list[SocraticQuestion], hypothesis: PrideHypothesis
) -> list[SocraticQuestion]:
    for question in questions:
        if question.stage is QuestionStage.HEART:
            question.question = hypothesis.pastoral_question
            question.purpose = "以该假设中最可自察之处进入心的层面"
    return questions


def _anchor_worship(
    questions: list[SocraticQuestion], chain: DesireChain
) -> list[SocraticQuestion]:
    for question in questions:
        if question.stage is QuestionStage.WORSHIP:
            question.question = (
                f"“{chain.functional_savior}”在你生活里承担了多大的重量？"
                "如果它塌了，你会变成谁？"
            )
    return questions


def _de_escalated(case: NormalizedCase) -> list[SocraticQuestion]:
    """Failure handling: defensiveness rises -> clarify and empathise only."""

    clarify_template, clarify_purpose = taxonomy.STAGE_TEMPLATES[QuestionStage.CLARIFY]
    return [
        SocraticQuestion(
            question_id="q-001",
            stage=QuestionStage.CLARIFY,
            order=1,
            question=clarify_template.format(topic=case.topic[:20]),
            purpose=clarify_purpose,
            difficulty=1,
            expected_risk="low",
            branch_conditions={"if_defensive": "停止追问，转为倾听"},
            requires_consent=False,
        )
    ]


def next_question(questions: list[SocraticQuestion]) -> list[SocraticQuestion]:
    """Only one core question is ever delivered per turn."""

    return questions[:MAX_QUESTIONS_PER_TURN]


def presumes_guilt(question: SocraticQuestion) -> bool:
    return any(marker in question.question for marker in _PRESUMPTIVE)
