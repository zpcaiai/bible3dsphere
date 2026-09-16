"""Skill 02 - claim-evidence-extractor (llm-structured)."""

from __future__ import annotations

from . import taxonomy
from .models import Claim, ClaimType, NormalizedCase

SKILL_ID = "claim-evidence-extractor"
SKILL_VERSION = "0.1.0"

BASE_CONFIDENCE = 0.55
EVIDENCE_BONUS = 0.25
MULTI_MARKER_BONUS = 0.1
HIGH_CONFIDENCE_FLOOR = 0.6

# Ordered so that the most spiritually load-bearing type wins a tie.
_TYPE_PRIORITY: tuple[ClaimType, ...] = (
    ClaimType.SALVATION,
    ClaimType.IDENTITY,
    ClaimType.ANTHROPOLOGICAL,
    ClaimType.ENEMY,
    ClaimType.MORAL,
    ClaimType.CAUSAL,
    ClaimType.ACTION_CALL,
    ClaimType.EMOTIONAL,
    ClaimType.FACTUAL,
)


def _score_types(chunk: str) -> dict[ClaimType, int]:
    scores: dict[ClaimType, int] = {}
    for claim_type, markers in taxonomy.CLAIM_MARKERS.items():
        hits = sum(1 for marker in markers if marker in chunk)
        if hits:
            scores[claim_type] = hits
    return scores


def _pick_types(scores: dict[ClaimType, int]) -> list[ClaimType]:
    if not scores:
        return []
    best = max(scores.values())
    ranked = [t for t in _TYPE_PRIORITY if scores.get(t) == best]
    ranked += [t for t in _TYPE_PRIORITY if t in scores and t not in ranked]
    return ranked[:3]


def _rhetoric_discount(chunk: str) -> float:
    hits = sum(1 for marker in taxonomy.RHETORIC_MARKERS if marker in chunk)
    return min(0.3, 0.15 * hits)


def extract(case: NormalizedCase) -> list[Claim]:
    """Extract typed claims, each bound to an evidence span or flagged implicit."""

    claims: list[Claim] = []
    index = 0
    segments = case.analyzed_object_segments + case.user_reaction_segments
    for segment in segments:
        chunk = segment.text
        scores = _score_types(chunk)
        for claim_type in _pick_types(scores):
            index += 1
            marker_hits = scores.get(claim_type, 1)
            discount = _rhetoric_discount(chunk)
            confidence = BASE_CONFIDENCE + EVIDENCE_BONUS
            if marker_hits > 1:
                confidence += MULTI_MARKER_BONUS
            confidence = round(max(0.0, min(1.0, confidence - discount)), 3)
            verifiable = any(m in chunk for m in taxonomy.VERIFIABLE_MARKERS)
            claims.append(
                Claim(
                    claim_id=f"claim-{index:03d}",
                    claim_type=claim_type,
                    statement=chunk,
                    evidence_span=chunk,
                    implicit=False,
                    verifiable=verifiable,
                    confidence=confidence,
                    rhetoric_discount=discount,
                    counter_evidence_needed=_counter_evidence(claim_type),
                    externally_verified=False,
                )
            )

    claims.extend(_implicit_claims(case, start_index=index))
    return claims


def _counter_evidence(claim_type: ClaimType) -> list[str]:
    if claim_type is ClaimType.SALVATION:
        return ["是否存在照做却未得到所承诺结果的案例"]
    if claim_type is ClaimType.CAUSAL:
        return ["是否存在同因不同果的反例", "是否遗漏了结构性变量"]
    if claim_type is ClaimType.FACTUAL:
        return ["原始数据来源是否可核验"]
    if claim_type is ClaimType.IDENTITY:
        return ["该身份判断是否被跨场景行为支持"]
    return ["是否存在合理的替代解释"]


def _implicit_claims(case: NormalizedCase, start_index: int) -> list[Claim]:
    """Implicit claims never receive high confidence and carry no evidence span."""

    implicit: list[Claim] = []
    text = case.subject_description
    index = start_index
    if any(m in text for m in ("只要", "就能")) and any(
        m in text for m in ("自由", "成功", "幸福")
    ):
        index += 1
        implicit.append(
            Claim(
                claim_id=f"claim-{index:03d}",
                claim_type=ClaimType.SALVATION,
                statement="隐含主张：某一条件足以带来根本性的解决",
                evidence_span="",
                implicit=True,
                verifiable=False,
                confidence=0.4,
                counter_evidence_needed=["需要当事人明确表述才能提升置信度"],
            )
        )
    return implicit


def high_confidence(claims: list[Claim]) -> list[Claim]:
    """Only span-bound claims above the floor may be treated as high confidence."""

    return [
        c
        for c in claims
        if c.evidence_span and not c.implicit and c.confidence >= HIGH_CONFIDENCE_FLOOR
    ]
