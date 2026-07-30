"""Anonymous dating-priority survey submission and aggregate statistics."""
from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field, model_validator

router = APIRouter()

# Dependencies injected from main at startup.
_get_db = None
_release_db = None

_PERSPECTIVE_ALIASES = {
    "dx": "male_to_female",
    "zm": "female_to_male",
    "male_to_female": "male_to_female",
    "female_to_male": "female_to_male",
}


def init_dating_priority_router(**deps):
    globals().update(deps)


class DatingPriorityItem(BaseModel):
    # 前端不再限制可选项数；100 只是防御性上限（最大题库 64 项），不是产品规则。
    rank: int = Field(ge=1, le=100)
    category: str = Field(default="", max_length=100)
    label: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=500)
    score: int = Field(ge=0, le=100)


class DatingVetoItem(BaseModel):
    suppliedRank: int = Field(ge=1, le=12)
    label: str = Field(min_length=1, max_length=500)
    strength: Literal["极高", "很高", "高", "中高", "因人而异"]


class DatingPrioritySubmitRequest(BaseModel):
    visitor_id: str = Field(min_length=16, max_length=255)
    perspective: str = Field(
        pattern="^(dx|zm|female_to_male|male_to_female)$"
    )

    # Legacy request fields remain accepted for older clients.
    focus_order: list = Field(default_factory=list, max_length=30)
    block_order: list = Field(default_factory=list, max_length=30)

    # Version 3 survey fields.
    version: int = Field(default=3, ge=1, le=3)
    selected: list[DatingPriorityItem] | None = Field(default=None, max_length=100)
    vetoes: list[DatingVetoItem] | None = Field(default=None, max_length=12)
    totalScore: int = Field(default=0, ge=0, le=100)

    @model_validator(mode="after")
    def validate_current_response(self):
        if self.selected is None:
            return self

        expected_ranks = list(range(1, len(self.selected) + 1))
        actual_ranks = [item.rank for item in self.selected]
        if actual_ranks != expected_ranks:
            raise ValueError("selected ranks must be sequential and start at 1")
        if len({item.label for item in self.selected}) != len(self.selected):
            raise ValueError("selected labels must be unique")

        score_total = sum(item.score for item in self.selected)
        expected_total = 100 if self.selected else 0
        if score_total != expected_total or self.totalScore != expected_total:
            raise ValueError("selected scores and totalScore must total 100, or 0 when empty")

        vetoes = self.vetoes or []
        if len({item.label for item in vetoes}) != len(vetoes):
            raise ValueError("veto labels must be unique")
        if len({item.suppliedRank for item in vetoes}) != len(vetoes):
            raise ValueError("veto supplied ranks must be unique")
        return self


def _decode_json(value, fallback):
    if isinstance(value, (list, dict)):
        return value
    if not value:
        return fallback
    try:
        decoded = json.loads(value)
        return decoded if isinstance(decoded, type(fallback)) else fallback
    except (TypeError, ValueError):
        return fallback


def _perspective_pair(value: str) -> tuple[str, str]:
    normalized = _PERSPECTIVE_ALIASES[value]
    legacy = "dx" if normalized == "male_to_female" else "zm"
    return normalized, legacy


def _rank_stats(rank_map: dict, denominator: int) -> list[dict]:
    stats = []
    for item, ranks in rank_map.items():
        stats.append({
            "item": item,
            "avg_rank": round(sum(ranks) / len(ranks), 2),
            "times_selected": len(ranks),
            "selection_rate": round(len(ranks) / denominator * 100, 1),
        })
    stats.sort(key=lambda entry: (entry["avg_rank"], -entry["times_selected"], entry["item"]))
    return stats


def _aggregate_current_stats(rows: list, requested_perspective: str) -> dict:
    priority_aggregates: dict[tuple[str, str], dict] = {}
    veto_aggregates: dict[str, dict] = {}
    legacy_focus_ranks: dict[str, list[int]] = {}
    legacy_block_ranks: dict[str, list[int]] = {}
    current_total = 0
    legacy_total = 0

    for response_value, focus_value, block_value in rows:
        response = _decode_json(response_value, {})
        selected = response.get("selected") if isinstance(response, dict) else None
        vetoes = response.get("vetoes") if isinstance(response, dict) else None
        is_current = (
            isinstance(selected, list)
            and isinstance(vetoes, list)
            and int(response.get("version") or 0) >= 3
        )

        if is_current:
            current_total += 1
            for item in selected:
                if not isinstance(item, dict) or not item.get("label"):
                    continue
                key = (str(item.get("category") or ""), str(item["label"]))
                aggregate = priority_aggregates.setdefault(key, {
                    "category": key[0],
                    "label": key[1],
                    "ranks": [],
                    "scores": [],
                })
                aggregate["ranks"].append(int(item.get("rank") or 0))
                aggregate["scores"].append(int(item.get("score") or 0))

            for item in vetoes:
                if not isinstance(item, dict) or not item.get("label"):
                    continue
                label = str(item["label"])
                aggregate = veto_aggregates.setdefault(label, {
                    "label": label,
                    "strength": str(item.get("strength") or ""),
                    "supplied_rank": int(item.get("suppliedRank") or 0),
                    "count": 0,
                })
                aggregate["count"] += 1

        focus_list = _decode_json(focus_value, [])
        block_list = _decode_json(block_value, [])
        if not is_current:
            legacy_total += 1
        for rank, item in enumerate(focus_list, 1):
            legacy_focus_ranks.setdefault(str(item), []).append(rank)
        for rank, item in enumerate(block_list, 1):
            legacy_block_ranks.setdefault(str(item), []).append(rank)

    priority_stats = []
    if current_total:
        for aggregate in priority_aggregates.values():
            count = len(aggregate["ranks"])
            priority_stats.append({
                "category": aggregate["category"],
                "label": aggregate["label"],
                "avg_rank": round(sum(aggregate["ranks"]) / count, 2),
                "avg_score": round(sum(aggregate["scores"]) / count, 1),
                "selection_count": count,
                "selection_rate": round(count / current_total * 100, 1),
            })
        priority_stats.sort(
            key=lambda entry: (
                -entry["selection_rate"],
                entry["avg_rank"],
                -entry["avg_score"],
                entry["label"],
            )
        )

    veto_stats = []
    if current_total:
        for aggregate in veto_aggregates.values():
            veto_stats.append({
                "label": aggregate["label"],
                "strength": aggregate["strength"],
                "supplied_rank": aggregate["supplied_rank"],
                "selection_count": aggregate["count"],
                "selection_rate": round(aggregate["count"] / current_total * 100, 1),
            })
        veto_stats.sort(
            key=lambda entry: (
                -entry["selection_rate"],
                entry["supplied_rank"],
                entry["label"],
            )
        )

    use_legacy_total = requested_perspective in {"dx", "zm"}
    return {
        "ok": True,
        "anonymous": True,
        "total": legacy_total if use_legacy_total else current_total,
        "current_total": current_total,
        "priority_stats": priority_stats,
        "veto_stats": veto_stats,
        # Backward-compatible fields for the old page.
        "focus_stats": _rank_stats(legacy_focus_ranks, legacy_total) if legacy_total else [],
        "block_stats": _rank_stats(legacy_block_ranks, legacy_total) if legacy_total else [],
    }


def _load_stats(cur, perspective: str) -> dict:
    normalized, legacy = _perspective_pair(perspective)
    cur.execute(
        """
        SELECT response_json, focus_order, block_order
        FROM (
            SELECT DISTINCT ON (visitor_id)
                visitor_id, response_json, focus_order, block_order, created_at, id
            FROM dating_priority_submissions
            WHERE perspective IN (%s, %s)
            ORDER BY visitor_id, created_at DESC, id DESC
        ) latest
        """,
        (normalized, legacy),
    )
    return _aggregate_current_stats(cur.fetchall(), perspective)


@router.post("/api/dating-priority/submit")
def submit_dating_priority(payload: DatingPrioritySubmitRequest) -> dict:
    """Save one pseudonymous browser response and return current aggregates."""
    normalized, _legacy = _perspective_pair(payload.perspective)
    is_current = payload.selected is not None
    response = {
        "version": 3,
        "selected": [
            item.model_dump() for item in (payload.selected or [])
        ],
        "vetoes": [
            item.model_dump() for item in (payload.vetoes or [])
        ],
        "totalScore": payload.totalScore,
    } if is_current else {}

    print(
        "[dating] anonymous submit "
        f"perspective={normalized} priorities={len(payload.selected or [])} "
        f"vetoes={len(payload.vetoes or [])}",
        flush=True,
    )
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO dating_priority_submissions (
                    visitor_id, perspective, focus_order, block_order,
                    response_version, response_json
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    payload.visitor_id,
                    normalized,
                    json.dumps(payload.focus_order, ensure_ascii=False),
                    json.dumps(payload.block_order, ensure_ascii=False),
                    3 if is_current else 1,
                    json.dumps(response, ensure_ascii=False),
                ),
            )
            conn.commit()
            stats = _load_stats(cur, normalized)
        return {"ok": True, "anonymous": True, "stats": stats}
    finally:
        _release_db(conn)


@router.get("/api/dating-priority/stats")
def get_dating_priority_stats(
    perspective: str = Query(
        pattern="^(dx|zm|female_to_male|male_to_female)$"
    ),
) -> dict:
    """Return aggregates only; no visitor identifiers are selected or exposed."""
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            return _load_stats(cur, perspective)
    finally:
        _release_db(conn)
