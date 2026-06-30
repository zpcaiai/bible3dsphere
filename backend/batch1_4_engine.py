"""Deterministic helpers for Spiritual Formation Batches 1, 3, and 4.

These functions keep the API explainable and usable without an LLM. The router
persists records; this module describes the supported record types and produces
small orchestration summaries from user intent.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import date
from typing import Any


MODULES: dict[str, dict[str, Any]] = {
    "scripture": {
        "batch": 1,
        "title": "Scripture Meditation & Inner Formation OS",
        "skills": ["lectio", "scripture_memory", "spiritual_examen", "confession_repentance"],
        "record_types": ["lectio_sessions", "memory_items", "examen_sessions", "confession_sessions"],
    },
    "virtue_vice": {
        "batch": 3,
        "title": "Virtue & Vice Formation OS",
        "skills": ["virtue_focus", "vice_pattern", "temptation_resistance", "fruit_tracker"],
        "record_types": [
            "focuses",
            "virtue_logs",
            "observations",
            "patterns",
            "temptation_plans",
            "temptation_checkins",
            "failure_reviews",
            "fruit_assessments",
            "feedback_requests",
        ],
    },
    "holy_habit": {
        "batch": 4,
        "title": "Rule of Life & Holy Habit Engine",
        "skills": ["rule_of_life", "holy_habit_planner", "sabbath_rest", "fasting_simplicity"],
        "record_types": [
            "rule_profiles",
            "commitments",
            "rule_checkins",
            "rule_reviews",
            "habit_plans",
            "habit_checkins",
            "habit_reviews",
            "sabbath_plans",
            "sabbath_sessions",
            "rest_audits",
            "sabbath_reviews",
            "boundary_rules",
            "fasting_plans",
            "fasting_checkins",
            "fasting_reviews",
            "simplicity_audits",
            "simplicity_actions",
        ],
    },
}

CRISIS_RE = re.compile(
    r"suicide|self[- ]?harm|hurt myself|kill myself|end my life|abuse|violence|unsafe|emergency|"
    r"自杀|轻生|伤害自己|虐待|暴力|家暴|危险|绝望",
    re.I,
)
FASTING_RISK_RE = re.compile(
    r"eating disorder|anorexia|bulimia|starve|punish myself|pregnant|diabetes|"
    r"厌食|暴食|催吐|惩罚自己|怀孕|糖尿病|不配吃",
    re.I,
)
SHAME_RE = re.compile(r"worthless|never forgiven|never change|punish myself|没救|无法被赦免|惩罚自己", re.I)


def validate_record_type(domain: str, record_type: str) -> None:
    if domain not in MODULES:
        raise ValueError(f"Unsupported domain: {domain}")
    if record_type not in MODULES[domain]["record_types"]:
        raise ValueError(f"Unsupported {domain} record type: {record_type}")


def normalize_payload(payload: dict[str, Any], *, fallback_id: str, email: str) -> dict[str, Any]:
    out = dict(payload or {})
    out.setdefault("id", fallback_id)
    out.setdefault("userId", email)
    return out


def safety_route(text: str, domain: str = "") -> dict[str, Any] | None:
    source = text or ""
    if CRISIS_RE.search(source):
        return {
            "route": "crisis_care",
            "blockNormalFormation": True,
            "message": "Safety and immediate human support come before ordinary formation.",
        }
    if domain == "holy_habit" and FASTING_RISK_RE.search(source):
        return {
            "route": "pastoral_medical_support",
            "blockNormalFormation": True,
            "message": "Do not intensify fasting or bodily discipline when health, coercion, or self-punishment risk is present.",
        }
    if SHAME_RE.search(source):
        return {
            "route": "pastoral_care",
            "blockNormalFormation": False,
            "message": "This sounds like condemnation or obsessive guilt. Reduce intensity and seek gentle pastoral support.",
        }
    return None


def orchestrate_intent(text: str, *, domain: str | None = None) -> dict[str, Any]:
    route = safety_route(text, domain or "")
    if route:
        return {"safety": route, "recommendedDomain": "suffering_care", "recommendedRecordType": None}

    input_text = (text or "").lower()
    if domain in MODULES:
        chosen = domain
    elif re.search(r"scripture|bible|verse|lectio|examen|confess|repent|经文|读经|省察|认罪|悔改", input_text):
        chosen = "scripture"
    elif re.search(r"virtue|vice|tempt|fruit|anger|lust|pride|德性|罪性|试探|果子|怒气|骄傲", input_text):
        chosen = "virtue_vice"
    elif re.search(r"rule|habit|sabbath|fast|simplicity|rest|生活规则|习惯|安息|禁食|简朴", input_text):
        chosen = "holy_habit"
    else:
        chosen = "scripture"

    record_type = {
        "scripture": "examen_sessions" if re.search(r"review|examen|省察", input_text) else "lectio_sessions",
        "virtue_vice": "temptation_checkins" if re.search(r"tempt|试探", input_text) else "focuses",
        "holy_habit": "fasting_plans" if re.search(r"fast|禁食", input_text) else "rule_profiles",
    }[chosen]
    return {
        "safety": None,
        "recommendedDomain": chosen,
        "recommendedRecordType": record_type,
        "nextStep": _next_step(chosen, record_type),
        "module": MODULES[chosen],
    }


def _next_step(domain: str, record_type: str) -> str:
    if domain == "scripture":
        return "Begin with one passage, one honest prayer, and one concrete obedience step."
    if domain == "virtue_vice":
        return "Name the possible pattern without shame, then choose one opposite virtue practice."
    if record_type == "fasting_plans":
        return "Keep fasting voluntary, medically wise, and paired with prayer, generosity, and simplicity."
    return "Build a small rule with a grace minimum, then review burden before adding practices."


def build_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_domain = Counter(r.get("domain") for r in records)
    by_type = Counter(r.get("record_type") for r in records)
    active = [r for r in records if (r.get("status") or "").lower() in ("active", "started", "reviewing", "learning")]
    latest = sorted(records, key=lambda r: str(r.get("updated_at") or r.get("created_at") or ""), reverse=True)[:8]
    return {
        "totalRecords": len(records),
        "activeRecords": len(active),
        "byDomain": dict(by_domain),
        "byRecordType": dict(by_type),
        "latest": latest,
        "asOf": date.today().isoformat(),
    }
