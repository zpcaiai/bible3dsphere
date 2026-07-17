"""Deterministic, source-separated spiritual-formation snapshot engine."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from .formation_ontology import CONTEXT_FIELD_ALLOWLISTS, GRACE_AND_RECOVERY_TYPES

ENGINE_VERSION = "spiritual-formation-engine-1.0"
RULE_VERSION = "formation-chain-rules-1.0"


def build_minimal_chain(event_node: dict[str, Any], related_nodes: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Build chronology only; never add a cause or fill a missing inner state."""
    nodes = [event_node, *related_nodes]
    if len(nodes) < 2:
        return None
    ordered = sorted(nodes, key=lambda item: (item.get("sequence_order", 100), item.get("created_at", "")))
    edges = []
    for left, right in zip(ordered, ordered[1:]):
        edges.append({
            "source_node_id": left["id"],
            "target_node_id": right["id"],
            "relation_type": "OBSERVED_IN_SAME_EVENT",
            "source_kind": "RULE",
            "statement_type": "RULE_DERIVED_RELATION",
            "rule_version": RULE_VERSION,
            "confidence": None,
        })
    return {"nodes": ordered, "edges": edges, "completeness": len({item["node_type"] for item in ordered}) / 16}


def build_formation_snapshot(*, nodes: list[dict[str, Any]], chains: list[dict[str, Any]],
                             window_start: datetime, window_end: datetime) -> dict[str, Any]:
    def in_window(item: dict[str, Any]) -> bool:
        raw = item.get("occurred_at") or item.get("created_at")
        if not raw:
            return True
        value = raw if isinstance(raw, datetime) else datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return window_start <= value <= window_end

    active = [item for item in nodes if item.get("processing_status", "ACTIVE") == "ACTIVE" and in_window(item)]
    active_ids = {item["id"] for item in active}
    active_chains = [chain for chain in chains if any(item.get("id") in active_ids for item in chain.get("nodes", []))]
    user_reported = [item for item in active if item.get("source_kind") == "USER_REPORT"]
    observed = [item for item in active if item.get("source_kind") in {"OBSERVATION", "RULE"}]
    confirmed = [item for item in active if item.get("source_kind") == "USER_CONFIRMED"]
    pending = [item for item in active if item.get("source_kind") == "MODEL" and item.get("user_review_status") == "PENDING"]
    grace = [item for item in active if item.get("node_type") in GRACE_AND_RECOVERY_TYPES]
    directions = [item for item in confirmed if item.get("node_type") == "FORMATION_DIRECTION"]
    types = Counter(item["node_type"] for item in active)
    reflective_questions = []
    if not confirmed:
        reflective_questions.append("在这些记录中，哪一项最贴近你自己的理解？")
    if not grace:
        reflective_questions.append("这段经历中，有没有支持、恩典或帮助你恢复的因素？")
    payload = {
        "data_status": "AVAILABLE" if active else "INSUFFICIENT_DATA",
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "user_reported_items": user_reported,
        "observed_relations": observed,
        "confirmed_patterns": confirmed,
        "pending_hypotheses": pending,
        "grace_and_recovery": grace,
        "formation_directions": directions,
        "record_coverage": {"active_nodes": len(active), "active_chains": len(active_chains), "node_types_present": dict(types)},
        "reflective_questions": reflective_questions,
        "tensions": [],
        "limitations": [
            "该快照只复述已有记录及用户确认的关联。",
            "未确认候选不会被当作你的信念、动机或属灵结论。",
            "系统不判断救恩、悔改、神的旨意、人格、成熟度或圣洁程度。",
        ],
        "engine_version": ENGINE_VERSION,
    }
    payload["input_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    return payload


def context_envelope(snapshot: dict[str, Any], target: str, *, consent: bool) -> dict[str, Any]:
    if target not in CONTEXT_FIELD_ALLOWLISTS:
        raise ValueError("unknown context target")
    if not consent:
        return {"available": False, "reason": "CONSENT_REQUIRED", "target": target}
    base = {key: snapshot.get(key) for key in CONTEXT_FIELD_ALLOWLISTS[target] if key in snapshot}
    if target == "prayer":
        base["user_confirmed_prayer_context"] = [
            item for item in snapshot.get("confirmed_patterns", [])
            if item.get("node_type") in {"SPIRITUAL_PRACTICE", "GRACE_EVIDENCE", "RECOVERY_RESPONSE"}
        ]
    elif target == "habit":
        base["user_confirmed_practice_context"] = [
            item for item in snapshot.get("confirmed_patterns", [])
            if item.get("node_type") in {"BEHAVIOR", "SPIRITUAL_PRACTICE", "RECOVERY_RESPONSE"}
        ]
        base["protective_factors"] = [item for item in snapshot.get("grace_and_recovery", []) if item.get("node_type") == "PROTECTIVE_FACTOR"]
    elif target == "attention":
        base["user_confirmed_attention_context"] = [
            item for item in snapshot.get("confirmed_patterns", [])
            if item.get("scope") in {"THIS_EVENT_ONLY", "THIS_SEASON"}
        ]
        base["protective_factors"] = [item for item in snapshot.get("grace_and_recovery", []) if item.get("node_type") == "PROTECTIVE_FACTOR"]
    # Pending hypotheses are never sent to prayer/habit/attention.
    base.pop("pending_hypotheses", None)
    return {"available": True, "target": target, "generated_at": datetime.now(timezone.utc).isoformat(), "context": base}
