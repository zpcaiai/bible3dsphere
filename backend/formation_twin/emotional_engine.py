"""Deterministic emotional observations, trends, and snapshot composition."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

from .emotion_ontology import normalize_emotion_label

RULE_VERSION = "emotional-rules-1.0"
ENGINE_VERSION = "emotional-state-engine-1.0"


def extract_user_reported(event: dict[str, Any]) -> tuple[list[dict], dict | None, list[dict]]:
    """Convert only explicit Batch 2 self-report fields; never infer missing values."""
    report = event.get("self_report") or {}
    observations = []
    seen: dict[tuple[str, str | None], dict] = {}
    for item in report.get("emotions") or []:
        label, custom = normalize_emotion_label(str(item.get("emotion") or ""))
        candidate = {
            "emotion_label": label, "custom_label": custom, "intensity": item.get("intensity"),
            "source_kind": "USER_REPORT", "statement_type": "USER_REPORTED_FACT", "confidence": None,
            "occurred_at": event["occurred_at"], "life_event_id": event["event_id"],
            "user_review_status": "NOT_REQUIRED", "processing_status": "ACTIVE",
        }
        identity = (label, custom)
        previous = seen.get(identity)
        if previous is None or (candidate["intensity"] or -1) > (previous["intensity"] or -1):
            seen[identity] = candidate
    observations.extend(seen.values())
    energy_keys = ("energy_level", "stress_level", "sleep_quality", "restfulness", "mental_load")
    energy = {key: report.get(key) for key in energy_keys if report.get(key) is not None}
    if energy:
        energy.update({
            "source_kind": "USER_REPORT", "statement_type": "USER_REPORTED_FACT",
            "occurred_at": event["occurred_at"], "life_event_id": event["event_id"],
        })
    body_states = []
    for item in report.get("body_states") or []:
        label = str(item.get("body_label") or "").strip()
        if not label:
            continue
        body_states.append({
            "body_label": label,
            "body_region": item.get("body_region"),
            "intensity": item.get("intensity"),
            "source_kind": "USER_REPORT",
            "statement_type": "USER_REPORTED_FACT",
            "occurred_at": event["occurred_at"],
            "life_event_id": event["event_id"],
            "user_review_status": "NOT_REQUIRED",
        })
    return observations, energy or None, body_states


def numeric_trend(points: list[tuple[datetime, int | float | None]], *, minimum_days: int = 3) -> dict:
    valid = sorted((time, float(value)) for time, value in points if value is not None)
    distinct_days = {time.date() for time, _ in valid}
    if len(distinct_days) < minimum_days:
        return {"direction": "INSUFFICIENT_DATA", "data_points": len(valid), "range": None, "median": None}
    midpoint = max(1, len(valid) // 2)
    early = median(value for _, value in valid[:midpoint])
    late = median(value for _, value in valid[midpoint:])
    delta = late - early
    overall_range = max(value for _, value in valid) - min(value for _, value in valid)
    if overall_range >= 6 and abs(delta) < 2:
        direction = "VOLATILE"
    elif delta >= 1:
        direction = "INCREASING"
    elif delta <= -1:
        direction = "DECREASING"
    else:
        direction = "STABLE"
    return {"direction": direction, "data_points": len(valid), "range": overall_range, "median": median(v for _, v in valid)}


def build_snapshot(*, observations: list[dict], energy_points: list[dict], start: datetime, end: datetime,
                   body_points: list[dict] | None = None,
                   model_candidates: list[dict] | None = None) -> dict:
    in_window = [item for item in observations if start <= item["occurred_at"] <= end and item.get("processing_status") == "ACTIVE"]
    user_items = [item for item in in_window if item["source_kind"] in {"USER_REPORT", "USER_CONFIRMED"}]
    pending_model = [item for item in (model_candidates or []) if item.get("user_review_status") == "PENDING"]
    latest_by_label = {}
    for item in sorted(user_items, key=lambda value: value["occurred_at"]):
        identity = (item["emotion_label"], item.get("custom_label"))
        previous = latest_by_label.get(identity)
        same_time = previous and previous["occurred_at"] == item["occurred_at"]
        explicit_wins = same_time and previous["source_kind"] == "USER_REPORT" and item["source_kind"] == "USER_CONFIRMED"
        if not explicit_wins:
            latest_by_label[identity] = item
    recent_energy = [item for item in energy_points if start <= item["occurred_at"] <= end]
    latest_energy = max(recent_energy, key=lambda value: value["occurred_at"], default=None)
    recent_body = [item for item in (body_points or []) if start <= item["occurred_at"] <= end]
    seven_start = end - timedelta(days=7)
    seven_energy = [item for item in energy_points if seven_start <= item["occurred_at"] <= end]
    rules = {}
    for key in ("energy_level", "stress_level", "sleep_quality"):
        rules[f"{key}_trend"] = numeric_trend([(item["occurred_at"], item.get(key)) for item in seven_energy])
    days = max(1, (end.date() - start.date()).days + 1)
    observed_dates = {item["occurred_at"].date() for item in user_items + recent_energy + recent_body}
    coverage = min(1.0, len(observed_dates) / days)
    payload = {
        "data_status": "AVAILABLE" if user_items or recent_energy or recent_body else "INSUFFICIENT_DATA",
        "window_start": start, "window_end": end,
        "data_coverage": {"observed_days": len(observed_dates), "expected_days": days, "coverage": round(coverage, 4)},
        "user_reported": {"emotions": list(latest_by_label.values()), "body_states": recent_body, "latest_energy_stress_sleep": latest_energy},
        "rule_derived": {"source_kind": "RULE", "statement_type": "RULE_DERIVED_METRIC", "rule_version": RULE_VERSION, **rules},
        "possible_model_candidates": pending_model,
        "uncertainty": (["当前没有足够的主动记录形成状态描述。"] if not user_items and not recent_energy and not recent_body else ["这些记录可能没有覆盖你全部的实际经历。"]),
        "limitations": ["该快照只描述现有记录支持的状态。", "系统不进行心理、医学或属灵诊断。"],
        "engine_version": ENGINE_VERSION,
    }
    serializable = json.loads(json.dumps(payload, default=lambda value: value.isoformat()))
    serializable["input_hash"] = hashlib.sha256(json.dumps(serializable, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return serializable


def emotion_frequencies(observations: list[dict], *, start: datetime, end: datetime) -> list[dict]:
    counts = Counter(item["emotion_label"] for item in observations if start <= item["occurred_at"] <= end and item["source_kind"] in {"USER_REPORT", "USER_CONFIRMED"})
    return [{"emotion_label": label, "recorded_count": count, "wording": "记录中出现"} for label, count in counts.most_common()]
