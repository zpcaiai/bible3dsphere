"""Deterministic candidate arbitration with one visible action by default."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from .contracts import (
    RecommendationArbitrationResult,
    RecommendationCandidate,
    SuppressedRecommendation,
)


def _key(candidate: RecommendationCandidate) -> str:
    if candidate.dedupe_key:
        return candidate.dedupe_key.lower()
    compact = re.sub(r"\W+", "", candidate.title.lower())
    if any(token in compact for token in ("守望", "伙伴", "真人", "联系")):
        return "human-connection"
    return f"{candidate.recommendation_type.lower()}:{compact[:40]}"


def _smaller(candidate: RecommendationCandidate) -> RecommendationCandidate:
    if candidate.capacity_mode not in {"LOW", "VERY_LOW"} and candidate.burden_level not in {"MEDIUM", "HIGH"}:
        return candidate
    update = {
        "estimated_duration_minutes": min(candidate.estimated_duration_minutes, 2),
        "burden_level": "VERY_LOW",
        "description": "保留一个最小、可随时停止的步骤；若今天没有容量，也可以不增加行动。",
    }
    if candidate.recommendation_type == "PRAYER":
        update["title"] = "一句话诚实祷告，或今天不增加行动"
    return candidate.model_copy(update=update)


def arbitrate_recommendations(
    candidates: list[RecommendationCandidate],
    *,
    safety_state: str = "NONE",
    active_action_count: int = 0,
    now: datetime | None = None,
) -> RecommendationArbitrationResult:
    now = now or datetime.now(timezone.utc)
    suppressed: list[SuppressedRecommendation] = []
    eligible: list[RecommendationCandidate] = []
    for item in candidates:
        if item.expires_at and item.expires_at <= now:
            suppressed.append(SuppressedRecommendation(candidate_id=item.id, reason_code="EXPIRED"))
        elif item.uses_pending_context:
            suppressed.append(SuppressedRecommendation(candidate_id=item.id, reason_code="PENDING_CONTEXT_CANNOT_DRIVE_COMMAND"))
        elif safety_state in {"ELEVATED", "IMMINENT"} and item.safety_priority > 2:
            suppressed.append(SuppressedRecommendation(candidate_id=item.id, reason_code="CRISIS_OVERRIDE"))
        else:
            eligible.append(item)

    if active_action_count >= 3:
        for item in eligible:
            suppressed.append(SuppressedRecommendation(candidate_id=item.id, reason_code="ACTIVE_ACTION_LIMIT"))
        return RecommendationArbitrationResult(
            selected_recommendation=None, merged_candidates=[], suppressed_candidates=suppressed,
            selection_rationale=["ACTIVE_ACTION_LIMIT", "USER_MAY_CLOSE_OR_COMPLETE_AN_EXISTING_ACTION"],
            no_action_selected=True,
        )

    groups: dict[str, list[RecommendationCandidate]] = {}
    for item in eligible:
        groups.setdefault(_key(item), []).append(item)
    representatives: list[RecommendationCandidate] = []
    merged_ids: list = []
    for group in groups.values():
        group.sort(key=lambda item: (item.safety_priority, not item.explicit_user_intent, item.estimated_duration_minutes))
        representatives.append(group[0])
        for duplicate in group[1:]:
            merged_ids.append(duplicate.id)
            suppressed.append(SuppressedRecommendation(candidate_id=duplicate.id, reason_code="MERGED_DUPLICATE"))
    if not representatives:
        return RecommendationArbitrationResult(
            selected_recommendation=None, merged_candidates=merged_ids, suppressed_candidates=suppressed,
            selection_rationale=["NO_SAFE_ELIGIBLE_ACTION"], no_action_selected=True,
        )
    representatives.sort(
        key=lambda item: (
            0 if item.safety_priority <= 2 else 1,
            0 if item.explicit_user_intent else 1,
            item.safety_priority,
            item.estimated_duration_minutes,
        )
    )
    selected = _smaller(representatives[0])
    for item in representatives[1:]:
        suppressed.append(SuppressedRecommendation(candidate_id=item.id, reason_code="ONE_VISIBLE_ACTION_LIMIT"))
    rationale = ["SAFETY_FIRST", "EXPLICIT_USER_INTENT_PREFERRED" if selected.explicit_user_intent else "MINIMUM_BURDEN_SELECTED", "ONE_VISIBLE_ACTION"]
    if selected.capacity_mode in {"LOW", "VERY_LOW"}:
        rationale.append("CAPACITY_DOWNGRADED")
    return RecommendationArbitrationResult(
        selected_recommendation=selected,
        merged_candidates=merged_ids,
        suppressed_candidates=suppressed,
        selection_rationale=rationale,
        no_action_selected=False,
    )
