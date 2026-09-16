"""Skill 04 - pride-signal-detector (llm + taxonomy).

Emits *signals*, never verdicts on a heart. Every hypothesis carries an
evidence level, alternative explanations and a disconfirmation request.
"""

from __future__ import annotations

from . import taxonomy
from .models import (
    Claim,
    EvidenceLevel,
    NormalizedCase,
    PrideHypothesis,
    PrideSignal,
    WorldviewMap,
)

SKILL_ID = "pride-signal-detector"
SKILL_VERSION = "0.1.0"

HEDGE_PREFIX = "值得察验的是，这里可能"


def _evidence_level(hits: int, distinct_segments: int) -> EvidenceLevel:
    """Evidence ladder: repetition across segments is what lifts a signal."""

    if hits <= 0:
        return EvidenceLevel.E0
    if hits == 1 and distinct_segments <= 1:
        return EvidenceLevel.E1
    if distinct_segments <= 1:
        return EvidenceLevel.E2
    if distinct_segments == 2:
        return EvidenceLevel.E3
    return EvidenceLevel.E4


def detect(
    case: NormalizedCase,
    claims: list[Claim],
    worldview: WorldviewMap,
    user_reaction: str = "",
) -> list[PrideHypothesis]:
    """Detect possible pride patterns in the analysed material."""

    self_scope = case.subject_type.value == "self_reflection"
    corpus: list[tuple[str, str]] = [(c.claim_id, c.statement) for c in claims]
    if user_reaction:
        corpus.append(("user-reaction", user_reaction))

    hypotheses: list[PrideHypothesis] = []
    index = 0
    for signal, markers in taxonomy.PRIDE_MARKERS.items():
        matched_segments = [
            (cid, text) for cid, text in corpus if any(m in text for m in markers)
        ]
        if not matched_segments:
            continue
        hits = sum(
            sum(1 for m in markers if m in text) for _, text in matched_segments
        )
        level = _evidence_level(hits, len(matched_segments))
        index += 1
        observation = matched_segments[0][1][:120]
        hypotheses.append(
            PrideHypothesis(
                hypothesis_id=f"pride-{index:03d}",
                observation=observation,
                possible_pattern=signal,
                interpretation_hypothesis=(
                    f"{HEDGE_PREFIX}存在 {signal.value} 的模式；这是假设，不是对内心的判定。"
                ),
                evidence_level=level,
                alternative_explanations=list(taxonomy.PRIDE_ALTERNATIVES[signal]),
                disconfirming_evidence_needed=[
                    "在压力或失败情境下的实际反应",
                    "跨场景、跨时间是否出现同一模式",
                ],
                pastoral_risk="high" if signal is PrideSignal.SPIRITUAL_PRIDE else "moderate",
                pastoral_question=taxonomy.PRIDE_QUESTIONS[signal],
                scope="self" if self_scope else "other",
                public_material_only=not self_scope,
            )
        )

    hypotheses.sort(key=lambda h: h.evidence_level.rank, reverse=True)
    if self_scope:
        return hypotheses
    return _prefer_self_examinable(hypotheses, worldview)


def _prefer_self_examinable(
    hypotheses: list[PrideHypothesis], worldview: WorldviewMap
) -> list[PrideHypothesis]:
    """Skill 04 guardrail: start where the user can self-examine."""

    for hypothesis in hypotheses:
        hypothesis.pastoral_question = (
            f"{hypothesis.pastoral_question}（先用在自己身上，再用来看别人。）"
        )
    return hypotheses


def conclusive(hypotheses: list[PrideHypothesis]) -> list[PrideHypothesis]:
    """E0-E2 may never be surfaced as conclusions."""

    return [h for h in hypotheses if h.evidence_level.is_conclusive]


def redirect_to_self_examination(hypotheses: list[PrideHypothesis]) -> list[str]:
    """Failure handling: user only wants to condemn someone else."""

    prompts = [
        "这件事在你里面激起了什么反应？",
        "你最不能接受对方的哪一点？那一点在你身上以什么形式出现过？",
    ]
    if hypotheses:
        prompts.append(hypotheses[0].pastoral_question)
    return prompts
