"""Skill 03 - worldview-frame-mapper (llm + rules)."""

from __future__ import annotations

from .models import Claim, ClaimType, NormalizedCase, WorldviewLayer, WorldviewMap

SKILL_ID = "worldview-frame-mapper"
SKILL_VERSION = "0.1.0"

MIN_CLAIMS_FOR_MAP = 2

SEVEN_QUESTIONS = (
    "what_is_ultimately_real",
    "what_is_a_human",
    "what_is_the_core_problem",
    "who_or_what_saves",
    "what_is_a_good_life",
    "who_holds_final_authority",
    "what_community_does_it_form",
)

_GOOD_BEHIND = {
    ClaimType.ACTION_CALL: "对主动性与责任的肯定，是受造之善",
    ClaimType.MORAL: "对善恶有分辨的渴望，反映神所造的道德感",
    ClaimType.SALVATION: "对救赎与彻底改变的渴望本身是真实的",
    ClaimType.IDENTITY: "对稳固身份的渴望是受造之善",
    ClaimType.CAUSAL: "寻求因果理解是受造的理性之善",
    ClaimType.EMOTIONAL: "情感表达本身是受造之善，不应被病理化",
    ClaimType.ENEMY: "对不义的敏感中包含真实的公义渴望",
    ClaimType.ANTHROPOLOGICAL: "试图理解人是什么，是正当的追问",
    ClaimType.FACTUAL: "对事实的看重是共同恩典的一部分",
}

_DISTORTION_BEHIND = {
    ClaimType.SALVATION: "把有限的手段绝对化为终极拯救",
    ClaimType.CAUSAL: "把复杂成因压缩为单一变量",
    ClaimType.MORAL: "以道德判断确立自身无需恩典",
    ClaimType.IDENTITY: "把可变的表现固化为人的本质",
    ClaimType.ENEMY: "以敌我划分承载本应由公义之神承担的审判",
    ClaimType.ACTION_CALL: "把顺从某一方法当作得救之路",
    ClaimType.ANTHROPOLOGICAL: "以片面人论覆盖人的完整图景",
    ClaimType.EMOTIONAL: "把情绪当作真理的最终裁判",
    ClaimType.FACTUAL: "以未经核验的数据支撑价值结论",
}


def _steelman(case: NormalizedCase, claims: list[Claim]) -> str:
    """Fair restatement of the strongest version, required before evaluation."""

    salient = [c.statement for c in claims if c.claim_type in
               (ClaimType.CAUSAL, ClaimType.SALVATION, ClaimType.MORAL)][:2]
    body = "；".join(salient) if salient else case.subject_description[:120]
    return f"其最强版本可以表述为：{body}。这一表述若成立，确实回应了人对意义与改变的真实渴望。"


def map_worldview(case: NormalizedCase, claims: list[Claim]) -> WorldviewMap:
    """Map claims onto creation / fall / redemption-substitute / consummation."""

    sufficient = len(claims) >= MIN_CLAIMS_FOR_MAP
    types = {c.claim_type for c in claims}

    creation = [_GOOD_BEHIND[t] for t in types if t in _GOOD_BEHIND]
    distortion = [_DISTORTION_BEHIND[t] for t in types if t in _DISTORTION_BEHIND]

    if not creation:
        creation = ["材料中仍可见对意义与关系的真实渴望，这是受造之善"]
    if not distortion:
        distortion = ["尚未见明确扭曲，需要更多材料"]

    substitutes = [
        c.statement for c in claims if c.claim_type is ClaimType.SALVATION
    ][:3] or ["材料中未见明确的替代救恩叙事"]

    telos = _telos(case, types)

    seven = {
        "what_is_ultimately_real": "材料所预设的终极实在（需更多材料确认）",
        "what_is_a_human": "人被视为可通过方法改造的主体" if ClaimType.ANTHROPOLOGICAL in types
        else "人论在材料中未明确表述",
        "what_is_the_core_problem": "根本问题被定位为能力或环境不足"
        if ClaimType.CAUSAL in types else "根本问题未被明确界定",
        "who_or_what_saves": substitutes[0],
        "what_is_a_good_life": telos[0],
        "who_holds_final_authority": "自我判断被置于最高位"
        if ClaimType.IDENTITY in types else "权威来源未明确",
        "what_community_does_it_form": "以表现分层的共同体"
        if ClaimType.ENEMY in types or ClaimType.IDENTITY in types
        else "共同体形态未明确",
    }

    open_questions = []
    if not sufficient:
        open_questions = [
            "材料不足以给出完整定性，需要补充：当事人如何界定成功与失败？",
            "该叙事在长期实践中结出了什么果子？",
        ]

    return WorldviewMap(
        case_id=case.case_id,
        steelman=_steelman(case, claims),
        layers=WorldviewLayer(
            creation_good=creation,
            fall_distortion=distortion,
            redemption_substitute=substitutes,
            consummation_telos=telos,
        ),
        seven_questions=seven,
        common_grace_insights=creation[:2],
        possible_correct_points=creation[:1],
        potential_distortions=distortion[:1],
        supporting_claim_ids=[c.claim_id for c in claims],
        conflicts=case.conflicts,
        open_questions=open_questions,
        sufficient_material=sufficient,
    )


def _telos(case: NormalizedCase, types: set[ClaimType]) -> list[str]:
    if ClaimType.SALVATION in types:
        return ["把人塑造成必须持续证明自己的人，把共同体塑造成以业绩分层的群体"]
    if case.subject_type.value == "self_reflection":
        return ["把人塑造成持续自我审查、难以安息的人"]
    return ["终局图景在材料中尚不明确"]
