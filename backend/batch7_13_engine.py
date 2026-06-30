"""Deterministic backend services for Spiritual Planet Batches 7-13.

This module follows the current backend style in this repo: small pure-Python
service functions plus raw-SQL persistence from routers. It intentionally does
not introduce SQLAlchemy/Alembic into a psycopg2/raw-migration codebase.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
import re
import uuid


_SHANGHAI = timezone(timedelta(hours=8))


def _now_iso() -> str:
    return datetime.now(_SHANGHAI).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _lower(text: str | None) -> str:
    return (text or "").lower()


RISK_PATTERNS = [
    re.compile(r"kill myself|suicide|self[- ]?harm|hurt myself", re.I),
    re.compile(r"violence|abuse|spiritual abuse|coerc|unsafe leader|unsafe group", re.I),
    re.compile(r"burn(?:ed)?\s*out|overcommit|leader .*pressures?", re.I),
    re.compile(r"自杀|自残|暴力|虐待|属灵操控|强迫|不安全|耗尽|逼我服事"),
]


def safety_scan(text: str, source: str = "formation_os") -> dict[str, Any]:
    matched = [pattern.pattern for pattern in RISK_PATTERNS if pattern.search(text or "")]
    high = any("kill" in item or "自杀" in item for item in matched)
    pressure = any("abuse" in item or "coerc" in item or "属灵操控" in item for item in matched)
    burnout = bool(re.search(r"burn(?:ed)?\s*out|overcommit|耗尽|过载", text or "", re.I))
    risk_level = "high" if high else "moderate" if matched else "none"
    route = "crisis_triage" if high else "suffering_care" if pressure else "holy_habit" if burnout else None
    return {
        "source": source,
        "risk_level": risk_level,
        "blocked_normal_formation": risk_level == "high",
        "route": route,
        "flags": matched,
        "message": "Safety and human care come before ordinary formation." if matched else "No safety blocker detected.",
    }


@dataclass(frozen=True)
class BatchDefinition:
    batch: int
    module_key: str
    module_name: str
    skills: tuple[str, str, str, str]


BATCHES: dict[int, BatchDefinition] = {
    7: BatchDefinition(7, "discipleship_community", "Community, Accountability & Discipleship OS", ("discipleship_pathway", "accountability_group", "mentor_coaching", "church_integration")),
    8: BatchDefinition(8, "gift_calling", "Gift, Calling & Mission OS", ("spiritual_gifts", "calling_discernment", "ministry_match", "mission_life")),
    9: BatchDefinition(9, "bible_doctrine", "Bible Knowledge Graph & Doctrine Learning OS", ("bible_character_graph", "biblical_theology_timeline", "doctrine_learning_path", "apologetics_dialogue")),
    10: BatchDefinition(10, "ai_formation_agent", "AI Spiritual Tutor & Personal Formation Agent OS", ("personal_formation_agent", "spiritual_memory_profile", "formation_recommendation", "ai_tutor_conversation")),
    11: BatchDefinition(11, "formation_analytics", "Analytics, Progress & Formation Metrics OS", ("formation_metrics", "progress_visualization", "formation_review_report", "safety_integrity_audit")),
    12: BatchDefinition(12, "productization", "Deployment, Multi-Tenant, Admin & Productization OS", ("multi_tenant_church", "admin_moderation", "subscription_packaging", "deployment_ops")),
    13: BatchDefinition(13, "master_build", "Full-Scale Integration, Enterprise Roadmap & Master Build OS", ("global_domain_integration", "product_roadmap_dependency_graph", "e2e_acceptance_matrix", "master_build_prompt")),
}


BIBLE_CHARACTERS = [
    "Adam", "Eve", "Noah", "Abraham", "Sarah", "Isaac", "Jacob", "Joseph", "Moses", "Aaron", "Miriam",
    "Joshua", "Deborah", "Gideon", "Ruth", "Boaz", "Samuel", "Saul", "David", "Solomon", "Elijah",
    "Elisha", "Isaiah", "Jeremiah", "Daniel", "Esther", "Mary", "Joseph of Nazareth", "John the Baptist",
    "Jesus", "Peter", "John", "Mary Magdalene", "Paul", "Barnabas", "Timothy", "Priscilla", "Aquila",
]


TIMELINE = [
    "Creation", "Fall", "Promise", "Abrahamic Covenant", "Exodus", "Sinai and Law", "Tabernacle",
    "Land and Judges", "Kingdom", "Davidic Covenant", "Prophets", "Exile", "Return", "Incarnation",
    "Cross", "Resurrection", "Ascension", "Pentecost", "Church and Mission", "New Creation",
]


PLANS = [
    {"key": "personal", "features": ["core formation", "ai tutor", "private analytics"]},
    {"key": "group", "features": ["accountability", "mentor-safe summaries"]},
    {"key": "church", "features": ["multi-tenant org", "admin console", "pastoral workflows"]},
    {"key": "institution", "features": ["audit", "custom config", "usage governance"]},
    {"key": "api", "features": ["api access", "webhooks", "usage meters"]},
]


def module_registry() -> dict[str, Any]:
    modules = [
        {
            "batch": item.batch,
            "module_key": item.module_key,
            "module_name": item.module_name,
            "skills": list(item.skills),
            "safety_first": True,
            "emits_events": True,
        }
        for item in BATCHES.values()
    ]
    skills = [
        {
            "skill_number": number,
            "skill_key": f"skill_{number:02d}",
            "module_key": BATCHES[((number - 1) // 4) + 1].module_key if number <= 52 and ((number - 1) // 4) + 1 in BATCHES else "legacy_or_frontend",
            "safety_first": True,
        }
        for number in range(1, 53)
    ]
    return {"modules": modules, "skills": skills, "total_modules": 13, "total_skills": 52}


def orchestrate(batch: int, intent_text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    if batch not in BATCHES:
        raise ValueError("unsupported batch")
    definition = BATCHES[batch]
    safe = safety_scan(intent_text, definition.module_key)
    if safe["route"]:
        return {
            "route": safe["route"],
            "risk_level": safe["risk_level"],
            "message": safe["message"],
            "next_endpoint": f"/api/{safe['route'].replace('_', '-')}",
            "blocked_normal_formation": safe["blocked_normal_formation"],
        }
    text = _lower(intent_text)
    skill = definition.skills[0]
    if batch == 7:
        skill = "accountability_group" if re.search(r"accountability|group|partner|小组|同伴", text) else "mentor_coaching" if "mentor" in text else "church_integration" if re.search(r"church|worship|教会|敬拜", text) else "discipleship_pathway"
    elif batch == 8:
        skill = "spiritual_gifts" if re.search(r"gift|恩赐", text) else "ministry_match" if re.search(r"serve|ministry|服事", text) else "mission_life" if re.search(r"mission|work|使命|职业", text) else "calling_discernment"
    elif batch == 9:
        skill = "bible_character_graph" if re.search(r"character|david|jesus|人物", text) else "doctrine_learning_path" if re.search(r"doctrine|教义", text) else "apologetics_dialogue" if re.search(r"apologetics|worldview|护教", text) else "biblical_theology_timeline"
    elif batch == 10:
        skill = "ai_tutor_conversation" if re.search(r"chat|question|问", text) else "spiritual_memory_profile" if re.search(r"memory|profile|记忆|画像", text) else "formation_recommendation" if re.search(r"recommend|next|推荐", text) else "personal_formation_agent"
    elif batch == 11:
        skill = "formation_review_report" if re.search(r"report|summary|报告", text) else "safety_integrity_audit" if re.search(r"audit|privacy|安全|审计", text) else "progress_visualization" if re.search(r"chart|timeline|可视化", text) else "formation_metrics"
    elif batch == 12:
        skill = "multi_tenant_church" if re.search(r"org|tenant|church|教会|租户", text) else "admin_moderation" if re.search(r"admin|moderation|管理", text) else "subscription_packaging" if re.search(r"billing|plan|subscription|订阅", text) else "deployment_ops"
    elif batch == 13:
        skill = "master_build_prompt" if re.search(r"prompt|build|codex", text) else "e2e_acceptance_matrix" if re.search(r"accept|journey|验收", text) else "product_roadmap_dependency_graph" if re.search(r"roadmap|dependency|路线", text) else "global_domain_integration"
    return {
        "route": definition.module_key,
        "skill": skill,
        "risk_level": safe["risk_level"],
        "message": f"Routed to {definition.module_name} / {skill}.",
        "next_endpoint": f"/api/formation-os/batches/{batch}/artifacts",
        "blocked_normal_formation": False,
    }


def dashboard(batch: int, existing_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if batch not in BATCHES:
        raise ValueError("unsupported batch")
    existing_records = existing_records or []
    definition = BATCHES[batch]
    counts: dict[str, int] = {}
    for record in existing_records:
        rtype = record.get("record_type", "unknown")
        counts[rtype] = counts.get(rtype, 0) + 1
    return {
        "batch": batch,
        "module_key": definition.module_key,
        "module_name": definition.module_name,
        "skills": list(definition.skills),
        "record_counts": counts,
        "recommended_next_step": recommended_next_step(batch, counts),
        "safety_contract": "Safety before formation; consent before sharing; grace before metrics.",
    }


def recommended_next_step(batch: int, counts: dict[str, int]) -> dict[str, str]:
    first_skill = BATCHES[batch].skills[0]
    if not counts:
        return {"skill": first_skill, "title": f"Create first {first_skill.replace('_', ' ')} artifact"}
    return {"skill": BATCHES[batch].skills[min(len(counts), 3)], "title": "Review current artifacts and create one safe next step"}


def create_artifacts(batch: int, user_id: str, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if batch not in BATCHES:
        raise ValueError("unsupported batch")
    context = context or {}
    if batch == 7:
        return [
            _record(user_id, batch, "discipleship_path", {"stage": "practicing_disciple", "steps": ["Rule of Life", "accountability group", "service experiment"]}),
            _record(user_id, batch, "accountability_group", {"type": "weekly_triads", "confidentiality": "consent-based, no public shaming"}),
            _record(user_id, batch, "mentor_relationship", {"permission_scope": "growth_summary", "status": "active"}),
            _record(user_id, batch, "church_integration", {"rhythm": "lord_day_worship", "safe_reentry": True}),
        ]
    if batch == 8:
        return [
            _record(user_id, batch, "gift_profile", {"primary_gifts": ["teaching", "encouragement"], "community_confirmation_needed": True}),
            _record(user_id, batch, "calling_pattern", {"domain": "teaching_discipleship", "confidence": "moderate", "not_certain": True}),
            _record(user_id, batch, "ministry_match", {"opportunity": "welcome_team_once_month", "match_score": 0.84, "observe_first": True}),
            _record(user_id, batch, "mission_life_profile", {"life_season": context.get("life_season", "single_worker"), "guardrails": ["rest", "family", "church"]}),
        ]
    if batch == 9:
        return [
            _record(user_id, batch, "bible_character_graph", {"characters_seeded": len(BIBLE_CHARACTERS), "path": ["David", "ancestor_of", "Jesus"]}),
            _record(user_id, batch, "biblical_timeline", {"movements": TIMELINE}),
            _record(user_id, batch, "doctrine_path", {"topic": "christology", "distinguish_tradition": True}),
            _record(user_id, batch, "apologetics_dialogue", {"topic": "problem_of_evil", "charitable": True, "non_coercive": True}),
        ]
    if batch == 10:
        return [
            _record(user_id, batch, "spiritual_profile", {"season": "stable_growth", "consent": {"ai_tutor": True, "mentor": False}}),
            _record(user_id, batch, "daily_plan", {"items": ["short prayer", "one Scripture", "one love action"], "max_items": 3}),
            _record(user_id, batch, "weekly_review", {"summary": "grace evidence before performance", "ranking": False}),
            _record(user_id, batch, "tutor_conversation", {"disclaimer": "AI is not God, pastor, therapist, or emergency service"}),
        ]
    if batch == 11:
        return [
            _record(user_id, batch, "metric_snapshot", {"metrics": ["prayer_sessions_completed", "grace_evidence_count"], "not_holiness_score": True}),
            _record(user_id, batch, "grace_evidence", {"title": "returned to one small practice"}),
            _record(user_id, batch, "formation_report", {"mentor_safe": True, "redacted": True}),
            _record(user_id, batch, "integrity_audit", {"privacy": "passed", "theology_boundary": "passed"}),
        ]
    if batch == 12:
        return [
            _record(user_id, batch, "organization", {"type": "church", "tenant_isolation": True}),
            _record(user_id, batch, "moderation_case", {"severity": "moderate", "audit_required": True}),
            _record(user_id, batch, "subscription", {"plans": PLANS, "crisis_soft_fail": True}),
            _record(user_id, batch, "deployment_health", {"status": "ready", "runbook": ["health", "backup", "monitoring", "incident"]}),
        ]
    return [
        _record(user_id, batch, "module_registry", module_registry()),
        _record(user_id, batch, "event_bus_contract", {"categories": ["scripture", "prayer", "community", "calling", "bible", "ai_tutor", "analytics", "admin", "ops"]}),
        _record(user_id, batch, "acceptance_matrix", {"roles": ["individual", "mentor", "pastor", "admin"], "definition_of_done": ["tests", "build", "safety", "consent"]}),
        _record(user_id, batch, "master_build_prompt", {"target": "FastAPI + PostgreSQL + Vercel frontend", "complete": True}),
    ]


def _record(user_id: str, batch: int, record_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    definition = BATCHES[batch]
    return {
        "id": _id(record_type),
        "email": user_id,
        "batch": batch,
        "module_key": definition.module_key,
        "record_type": record_type,
        "payload": payload,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }


def bible_graph_search(query: str = "") -> dict[str, Any]:
    q = _lower(query)
    matches = [name for name in BIBLE_CHARACTERS if not q or q in _lower(name)][:20]
    if not matches and query:
        matches = ["David", "Jesus", "Paul"]
    return {
        "characters": [{"name": name, "formation_lessons": ["grace and warning", "read in canonical context"]} for name in matches],
        "relationship_path": [{"from": "David", "relationship": "ancestor_of", "to": "Jesus", "confidence": "explicit", "scripture_references": ["Matthew 1:1"]}],
        "themes": ["covenant", "kingdom", "messiah", "new_creation"],
    }


def roadmap() -> dict[str, Any]:
    return {
        "phases": [
            {"key": "foundation", "batches": [1, 2, 3, 4], "deliverables": ["core practices", "habit engine"]},
            {"key": "formation_depth", "batches": [5, 6, 7, 8], "deliverables": ["worldview", "care", "community", "calling"]},
            {"key": "knowledge_agent_analytics", "batches": [9, 10, 11], "deliverables": ["Bible doctrine", "AI tutor", "analytics"]},
            {"key": "enterprise", "batches": [12, 13], "deliverables": ["multi-tenant", "admin", "master build"]},
        ],
        "definition_of_done": ["safety-first routing", "consent checks", "tenant isolation", "tests", "build", "runbooks"],
    }
