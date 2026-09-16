"""Skill 08 - discernment-report-composer (composer)."""

from __future__ import annotations

from .models import (
    Claim,
    DesireChain,
    DiscernmentReport,
    FailureCode,
    GospelBridge,
    NormalizedCase,
    PrideHypothesis,
    ReviewStatus,
    RiskLevel,
    SafetyDecision,
    SkillFailure,
    SocraticQuestion,
    WorldviewMap,
)
from .pride import conclusive

SKILL_ID = "discernment-report-composer"
SKILL_VERSION = "0.1.0"

BASE_LIMITATIONS = (
    "本报告基于所提供材料，系统不能读心，也不领受新启示。",
    "所有关于动机与偶像的表述均为假设，附证据等级与替代解释。",
    "本系统不作心理疾病诊断，也不判定任何人的得救状态。",
)


def compose(
    case: NormalizedCase,
    claims: list[Claim],
    worldview: WorldviewMap,
    hypotheses: list[PrideHypothesis],
    desires: list[DesireChain],
    questions: list[SocraticQuestion],
    bridge: GospelBridge | None,
    safety: SafetyDecision,
) -> DiscernmentReport:
    """Compose the user-facing report in the nine-part order of skill 08."""

    if safety.risk_level.rank >= RiskLevel.HIGH.rank:
        raise SkillFailure(
            FailureCode.HIGH_RISK_REVIEW,
            "高风险案例不生成深度报告，转安全支持与人工复核",
        )
    if not worldview.case_id or not claims:
        raise SkillFailure(
            FailureCode.MODEL_OUTPUT_INVALID, "关键中间结果缺失，不予合成"
        )

    affirmations = worldview.possible_correct_points or worldview.layers.creation_good[:1]
    solid = conclusive(hypotheses)
    limitations = list(BASE_LIMITATIONS)
    if not solid:
        limitations.append(
            "当前自高相关线索均在 E0-E2，仅作为待察验的方向，不构成结论。"
        )
    if any(chain.candidate for chain in desires):
        limitations.append("欲望链为候选模型，需要更多自我报告才能确认。")
    if worldview.open_questions:
        limitations.append("材料不足以完整定性，已改为提出待答问题。")
    if case.missing_context:
        limitations.extend(case.missing_context)

    first_question = questions[:1]

    return DiscernmentReport(
        case_id=case.case_id,
        summary=_summary(case, worldview),
        observed_claims=[c.model_dump(mode="json") for c in claims],
        worldview_map=worldview.model_dump(mode="json"),
        pride_hypotheses=[h.model_dump(mode="json") for h in hypotheses],
        desire_map=[d.model_dump(mode="json") for d in desires],
        socratic_questions=[q.model_dump(mode="json") for q in first_question],
        gospel_bridge=bridge.model_dump(mode="json") if bridge else {},
        limitations=limitations,
        review_status=(
            ReviewStatus.HUMAN_REVIEW_REQUIRED
            if safety.human_review_required
            else ReviewStatus.READY
        ),
        affirmations=affirmations,
        self_mirror=_self_mirror(hypotheses),
        actionable_response=bridge.practice if bridge else "本周先只做一件事：把这段材料读给一位你信任的人听，并问他看到了什么。",
    )


def _summary(case: NormalizedCase, worldview: WorldviewMap) -> str:
    return (
        f"针对「{case.topic}」的辨识摘要。"
        f"{worldview.steelman} "
        "以下内容区分了观察、解释与假设：观察来自材料本身，解释与假设均可被推翻。"
    )


def _self_mirror(hypotheses: list[PrideHypothesis]) -> list[str]:
    if not hypotheses:
        return ["在这件事上，你自己最容易滑向哪一边？"]
    return [
        f"你如何看待自己身上是否也有“{h.possible_pattern.value}”的影子？"
        for h in hypotheses[:2]
    ]
