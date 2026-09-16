"""Skill 07 - gospel-bridge-builder (llm-theology).

Christ-centred: affirmed good -> exposure -> law mirror -> Christ ->
union/identity -> practice -> hope. Never degrades into a behaviour checklist.
"""

from __future__ import annotations

from . import taxonomy
from .models import (
    DesireChain,
    FailureCode,
    FaithContext,
    GospelBridge,
    NormalizedCase,
    PrideHypothesis,
    SkillFailure,
    WorldviewMap,
)

SKILL_ID = "gospel-bridge-builder"
SKILL_VERSION = "0.1.0"

CHRIST_CORE = (
    "基督不是又一个更高的标准，而是那位替我们成全标准的：祂道成肉身、"
    "代替我们受死、担当我们的定罪、并且复活，重新定义了什么叫荣耀。"
)

JUSTIFICATION_NOTE = (
    "称义是一次成就、地位性的宣告，不因你今天的表现增减；"
    "成圣是一生渐进的更新，会有起伏。把两者混淆，会让软弱变成对被接纳的怀疑。"
)


def build(
    case: NormalizedCase,
    worldview: WorldviewMap,
    hypotheses: list[PrideHypothesis],
    desires: list[DesireChain],
) -> GospelBridge:
    """Build the gospel bridge. Requires consent and sufficient grounding."""

    if not case.consent_scope.allow_gospel_bridge:
        raise SkillFailure(
            FailureCode.USER_CONSENT_REQUIRED, "用户未同意进入福音桥接"
        )

    if not worldview.sufficient_material and not desires:
        raise SkillFailure(
            FailureCode.UNSUPPORTED_THEOLOGICAL_CLAIM,
            "神学依据不足，需知识库或人工复核",
        )

    chain = desires[0] if desires else None
    anchor_key = "default"
    if hypotheses:
        anchor_key = taxonomy.PRIDE_TO_ANCHOR.get(
            hypotheses[0].possible_pattern, "default"
        )
    if case.sensitivity.value == "mental_health":
        anchor_key = "scrupulosity"

    affirmed = (
        chain.good_desire if chain else (worldview.layers.creation_good or ["你的渴望中有真实的善"])[0]
    )
    absolutized = chain.absolutized_desire if chain else worldview.layers.fall_distortion[0]
    savior = chain.functional_savior if chain else "某个有限的好东西"

    return GospelBridge(
        affirmed_good=f"你所渴望的“{affirmed}”本身是好的，是受造之善，不需要被否定。",
        exposure=f"但它被要求承担终极的重量：{absolutized}。“{savior}”被放在了只有神能站的位置。",
        law_mirror=(
            "若诚实面对，没有人能靠这件事真正证明自己——标准要么被降低，要么把人压垮。"
            if case.sensitivity.value != "mental_health"
            else "律法的作用不是把你压得更低，而是指向那位已经替你成全的。"
        ),
        christ_person_and_work=CHRIST_CORE,
        union_identity=(
            "身份因此从成就、群体或表现，转向“在基督里”——这是被赐予的，不是被赢得的。"
        ),
        practice=_practice(case, chain),
        hope=(
            "盼望不是自我改良会成功，而是圣灵在你里面开始的新生命祂必完成；"
            "今生的痛苦不保证立刻消失，但不再是最终的话。"
        ),
        justification_sanctification_note=JUSTIFICATION_NOTE,
        scripture_anchors=list(taxonomy.SCRIPTURE_ANCHORS[anchor_key]),
        consent_granted=True,
        theologically_supported=True,
    )


def _practice(case: NormalizedCase, chain: DesireChain | None) -> str:
    if case.sensitivity.value == "mental_health":
        return (
            "本周做一件小事：把一次自我审查换成一次向神的道谢，"
            "并把反复认罪的内容一次性告诉一位可信任的牧者，然后停下。"
        )
    if chain:
        return (
            f"本周做一件具体的小事：在一个“{chain.functional_savior}”会受损的场合，"
            "刻意选择诚实而不是好看，并留意自己的反应。"
        )
    return "本周做一件具体、非表演性的小事：向一个你曾轻看的人主动求助一次。"


def requires_consent_first(case: NormalizedCase) -> bool:
    return case.faith_context is not FaithContext.CHRISTIAN
