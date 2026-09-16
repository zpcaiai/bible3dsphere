"""Skill 05 - desire-idolatry-mapper (llm-structured).

good_desire -> absolutized_desire -> functional_savior -> demanded_sacrifice
-> enslaving_fruit
"""

from __future__ import annotations

from . import taxonomy
from .models import (
    DesireChain,
    EvidenceLevel,
    NormalizedCase,
    PrideHypothesis,
    WorldviewMap,
)

SKILL_ID = "desire-idolatry-mapper"
SKILL_VERSION = "0.1.0"


def _structural_factors(text: str) -> list[str]:
    found = [m for m in taxonomy.STRUCTURAL_MARKERS if m in text]
    if not found:
        return []
    return [
        f"材料中出现结构性因素“{m}”，不应仅归因于个人偶像" for m in found
    ]


def map_desires(
    case: NormalizedCase,
    worldview: WorldviewMap,
    hypotheses: list[PrideHypothesis],
    user_reaction: str = "",
) -> list[DesireChain]:
    """Build desire chains. Idolatry language stays a pastoral hypothesis."""

    text = f"{case.subject_description} {user_reaction}"
    structural = _structural_factors(text)

    chains: list[DesireChain] = []
    seen: set[str] = set()
    index = 0
    for hypothesis in hypotheses:
        template = taxonomy.DESIRE_TEMPLATES.get(hypothesis.possible_pattern)
        if not template:
            continue
        key = template["functional_savior"]
        if key in seen:
            continue
        seen.add(key)
        index += 1
        chains.append(
            DesireChain(
                chain_id=f"desire-{index:03d}",
                good_desire=template["good_desire"],
                absolutized_desire=template["absolutized_desire"],
                functional_savior=template["functional_savior"],
                demanded_sacrifice=template["demanded_sacrifice"],
                enslaving_fruit=template["enslaving_fruit"],
                loss_reaction=template["loss_reaction"],
                structural_factors=structural,
                reanchoring_in_christ=template["reanchoring_in_christ"],
                confidence=hypothesis.evidence_level,
                candidate=not hypothesis.evidence_level.is_conclusive,
            )
        )

    if not chains:
        chains = _candidate_models(structural)
    return chains


def _candidate_models(structural: list[str]) -> list[DesireChain]:
    """Failure handling: emit candidates and ask for more self-report."""

    template = taxonomy.DEFAULT_DESIRE_CHAIN
    return [
        DesireChain(
            chain_id="desire-candidate-001",
            good_desire=template["good_desire"],
            absolutized_desire=template["absolutized_desire"],
            functional_savior=template["functional_savior"],
            demanded_sacrifice=template["demanded_sacrifice"],
            enslaving_fruit=template["enslaving_fruit"],
            loss_reaction=template["loss_reaction"],
            structural_factors=structural,
            reanchoring_in_christ=template["reanchoring_in_christ"],
            confidence=EvidenceLevel.E1,
            candidate=True,
        )
    ]


def more_self_report_needed(chains: list[DesireChain]) -> bool:
    return all(chain.candidate for chain in chains)
