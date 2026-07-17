"""Formation Twin Batch 5 temporal-pattern domain engine.

Patterns in this module are reviewable, time-bounded hypotheses.  The engine
operates on metadata and already-structured Formation Chains; it never needs
raw journal, prayer, confession, transcript, temptation, or crisis bodies.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Iterable, Literal, TypedDict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator


ENGINE_VERSION = "formation-temporal-pattern-engine-1.0"
RULE_VERSION = "formation-pattern-rules-1.0"
CONFIDENCE_ALGORITHM_VERSION = "pattern-confidence-1.0"

TIME_LEVELS = {
    "MOMENT", "DAY", "WEEK", "MONTH", "QUARTER", "YEAR", "LIFE_SEASON", "USER_DEFINED_PERIOD",
}
PATTERN_TYPES = {
    "TRIGGER_RESPONSE_PATTERN", "EMOTION_RESPONSE_PATTERN", "BELIEF_ACTIVATION_PATTERN",
    "DESIRE_FEAR_PATTERN", "TEMPTATION_CONTEXT_PATTERN", "COPING_PATTERN", "RELATIONAL_PATTERN",
    "SPIRITUAL_PRACTICE_PATTERN", "AVOIDANCE_PATTERN", "RECOVERY_PATTERN", "GRACE_SUPPORT_PATTERN",
    "FORMATION_DIRECTION_PATTERN", "LIFE_SEASON_PATTERN", "USER_DEFINED_PATTERN",
}
LIFECYCLE_STATUSES = {
    "CANDIDATE", "PENDING_USER_REVIEW", "CONFIRMED_ACTIVE", "CONFIRMED_CONTEXTUAL", "WEAKENING",
    "DORMANT", "RESOLVED", "OUTDATED", "REJECTED", "INVALIDATED", "ARCHIVED",
}
EVIDENCE_ROLES = {
    "SUPPORTING", "COUNTEREVIDENCE", "CONTEXT_LIMIT", "UNRESOLVED", "SUPERSEDED", "INVALIDATED",
}
REVIEW_STATUSES = {
    "PENDING", "CONFIRMED", "PARTIALLY_CONFIRMED", "REJECTED", "RELABELLED", "SCOPE_NARROWED",
    "SCOPE_EXPANDED", "MARKED_OUTDATED", "MARKED_RESOLVED", "MARKED_STILL_RELEVANT",
    "DO_NOT_SUGGEST_AGAIN", "NOT_REQUIRED",
}
CURRENT_PATTERN_STATUSES = {"CONFIRMED_ACTIVE", "CONFIRMED_CONTEXTUAL", "WEAKENING", "DORMANT"}
CONTEXT_PATTERN_STATUSES = {"CONFIRMED_ACTIVE", "CONFIRMED_CONTEXTUAL", "WEAKENING"}
SENSITIVE_DECAY_TYPES = {
    "GRIEF", "HEALTH_CHALLENGE", "TRAUMA", "MARRIAGE_BREAKDOWN", "CHURCH_BREAKDOWN",
    "FAMILY_BREAKDOWN", "CARE_GIVING", "CRISIS_RECOVERY", "RELOCATION", "CALLING_TRANSITION",
}
PROHIBITED_KEYS = {
    "personality_score", "spiritual_growth_score", "holiness_score", "idol_strength", "sin_severity",
    "salvation_probability", "spiritual_rank", "journal_text", "prayer_text", "confession_text",
    "temptation_text", "transcript", "crisis_text", "raw_content", "full_text", "third_party_identity",
}
PROHIBITED_TEXT = {
    "你从小就是", "你的根本偶像", "你一生都在", "你永远无法", "神正在通过失败惩罚你",
    "属灵成长速度", "人格障碍", "救恩概率", "圣洁程度", "罪性强度", "spiritual rank",
    "salvation probability", "your core idol", "you will never change", "fixed personality",
}

DEFAULT_HALF_LIFE_DAYS = {
    "EMOTION_OBSERVATION": 7.0,
    "COPING_BEHAVIOR": 30.0,
    "FORMATION_CHAIN": 60.0,
    "CONFIRMED_SEASON_PATTERN": 120.0,
    "CONFIRMED_LONG_TERM_PATTERN": 365.0,
    "USER_REJECTION": math.inf,
}
SOURCE_QUALITY_WEIGHT = {
    "USER_DIRECT_STATEMENT": 1.0,
    "USER_CONFIRMED_CHAIN": 0.95,
    "USER_CONFIRMED_PATTERN": 0.9,
    "OBSERVED_BEHAVIOR": 0.8,
    "RULE_DERIVED_RELATION": 0.6,
    "MODEL_HYPOTHESIS": 0.35,
    "THIRD_PARTY_FEEDBACK": 0.4,
    "PASTORAL_FEEDBACK": 0.4,
}


class TimePrecision(str, Enum):
    EXACT = "EXACT"
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
    SEASON = "SEASON"
    YEAR = "YEAR"
    UNKNOWN = "UNKNOWN"


def _require_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware datetime required")
    return value


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(PROHIBITED_KEYS.intersection(key.lower() for key in value)) or any(
            _contains_forbidden_key(item) for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def validate_pattern_text(text: str) -> str:
    lowered = text.lower()
    if any(phrase.lower() in lowered for phrase in PROHIBITED_TEXT):
        raise ValueError("fixed-personality, spiritual-verdict, or scoring language is not allowed")
    return text


class ApproximateTimeRange(BaseModel):
    start_at: datetime | None = None
    end_at: datetime | None = None
    precision: TimePrecision
    original_expression: str | None = Field(default=None, max_length=160)

    @field_validator("start_at", "end_at")
    @classmethod
    def aware_if_present(cls, value: datetime | None) -> datetime | None:
        return _require_aware(value) if value is not None else None

    @model_validator(mode="after")
    def preserve_uncertainty(self):
        if self.start_at and self.end_at and self.end_at < self.start_at:
            raise ValueError("end_at must be after start_at")
        if self.precision == TimePrecision.UNKNOWN and not self.original_expression:
            raise ValueError("unknown precision requires the original expression")
        return self


class PatternScope(BaseModel):
    scope_kind: Literal[
        "GLOBAL_UNKNOWN", "LIFE_SEASON_SPECIFIC", "DOMAIN_SPECIFIC", "RELATIONSHIP_SPECIFIC",
        "CURRENT_CONTEXT_ONLY", "USER_DEFINED",
    ] = "CURRENT_CONTEXT_ONLY"
    life_domains: list[str] = Field(default_factory=list, max_length=12)
    life_season_ids: list[str] = Field(default_factory=list, max_length=20)
    relationship_reference_ids: list[str] = Field(default_factory=list, max_length=10)
    user_description: str | None = Field(default=None, max_length=300)


class PatternEvidence(BaseModel):
    evidence_id: str
    evidence_role: str
    evidence_type: str
    source_record_type: str
    source_record_id: str
    occurred_at: datetime
    temporal_weight: float = Field(ge=0, le=1)
    source_quality: str
    independence_group: str | None = None
    relevance: float = Field(default=1.0, ge=0, le=1)
    user_review_status: str = "PENDING"
    explanation: str = Field(max_length=400)
    decay_strategy: Literal["STANDARD", "NON_STANDARD_DECAY", "USER_OVERRIDE"] = "STANDARD"

    @field_validator("evidence_role")
    @classmethod
    def known_role(cls, value: str) -> str:
        if value not in EVIDENCE_ROLES:
            raise ValueError("unknown evidence role")
        return value

    @field_validator("occurred_at")
    @classmethod
    def occurred_is_aware(cls, value: datetime) -> datetime:
        return _require_aware(value)


class PatternConfidence(BaseModel):
    level: Literal["VERY_LOW", "LOW", "MODERATE", "HIGH"]
    numeric_value: float = Field(ge=0, le=1)
    support_score: float = Field(ge=0)
    counterevidence_score: float = Field(ge=0)
    recency_factor: float = Field(ge=0, le=1)
    diversity_factor: float = Field(ge=0, le=1)
    user_confirmation_factor: float = Field(ge=-1, le=1)
    scope_consistency_factor: float = Field(ge=0, le=1)
    rationale: list[str]
    calculated_at: datetime
    algorithm_version: str = CONFIDENCE_ALGORITHM_VERSION


class FormationPatternHypothesis(BaseModel):
    pattern_id: str
    title: str = Field(min_length=1, max_length=160)
    pattern_type: str
    description: str = Field(min_length=1, max_length=1200)
    statement_type: Literal["RULE_PATTERN_HYPOTHESIS", "MODEL_PATTERN_HYPOTHESIS", "USER_CONFIRMED_PATTERN"]
    source_kind: Literal["RULE", "MODEL", "USER_DEFINED", "USER_CONFIRMED"]
    scope: PatternScope
    lifecycle_status: str
    supporting_evidence: list[PatternEvidence] = Field(min_length=1)
    counterevidence: list[PatternEvidence] = Field(default_factory=list)
    unresolved_evidence: list[PatternEvidence] = Field(default_factory=list)
    confidence: PatternConfidence
    alternative_explanations: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(min_length=1)
    first_observed_at: datetime
    last_observed_at: datetime
    review_due_at: datetime
    user_review_status: str = "PENDING"
    rule_version: str | None = None
    model_version: str | None = None
    version: int = Field(default=1, ge=1)

    @field_validator("pattern_type")
    @classmethod
    def known_pattern_type(cls, value: str) -> str:
        if value not in PATTERN_TYPES:
            raise ValueError("unknown pattern type")
        return value

    @field_validator("lifecycle_status")
    @classmethod
    def known_lifecycle(cls, value: str) -> str:
        if value not in LIFECYCLE_STATUSES:
            raise ValueError("unknown lifecycle status")
        return value

    @field_validator("title", "description")
    @classmethod
    def safe_language(cls, value: str) -> str:
        return validate_pattern_text(value)

    @model_validator(mode="after")
    def enforce_reviewable_hypothesis(self):
        for value in (self.first_observed_at, self.last_observed_at, self.review_due_at):
            _require_aware(value)
        if self.last_observed_at < self.first_observed_at:
            raise ValueError("invalid observed time range")
        if self.review_due_at <= self.last_observed_at:
            raise ValueError("review_due_at must follow last observation")
        if self.source_kind == "MODEL" and not self.alternative_explanations:
            raise ValueError("model hypotheses require alternative explanations")
        if self.lifecycle_status.startswith("CONFIRMED") and self.user_review_status not in {
            "CONFIRMED", "PARTIALLY_CONFIRMED", "SCOPE_NARROWED", "SCOPE_EXPANDED",
        }:
            raise ValueError("confirmed patterns require a user review")
        if _contains_forbidden_key(self.model_dump()):
            raise ValueError("prohibited score or sensitive content field")
        return self


class TemporalPatternProcessingState(TypedDict):
    source_change: dict[str, Any]
    consent_result: dict[str, Any] | None
    safety_result: dict[str, Any] | None
    temporal_windows: list[dict[str, Any]]
    event_clusters: list[dict[str, Any]]
    rule_candidates: list[dict[str, Any]]
    semantic_candidates: list[dict[str, Any]]
    model_candidates: list[dict[str, Any]]
    supporting_evidence: list[dict[str, Any]]
    counterevidence: list[dict[str, Any]]
    validated_patterns: list[dict[str, Any]]
    confidence_updates: list[dict[str, Any]]
    lifecycle_updates: list[dict[str, Any]]
    life_season_updates: list[dict[str, Any]]
    trajectory_updates: list[dict[str, Any]]
    graph_updates: list[dict[str, Any]]
    snapshot: dict[str, Any] | None
    errors: list[dict[str, Any]]


def resolve_temporal_windows(
    occurred_at: datetime,
    timezone_name: str,
    *,
    custom_windows: Iterable[dict[str, Any]] = (),
) -> list[dict[str, Any]]:
    """Return UTC boundaries calculated from the user's local calendar."""
    _require_aware(occurred_at)
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("valid IANA timezone required") from exc
    local = occurred_at.astimezone(zone)
    day = local.replace(hour=0, minute=0, second=0, microsecond=0)
    week = day - timedelta(days=day.weekday())
    month = day.replace(day=1)
    quarter_month = ((local.month - 1) // 3) * 3 + 1
    quarter = month.replace(month=quarter_month)
    year = month.replace(month=1)

    def next_month(value: datetime, months: int = 1) -> datetime:
        index = value.year * 12 + value.month - 1 + months
        return value.replace(year=index // 12, month=index % 12 + 1, day=1)

    boundaries = [
        ("DAY", day, day + timedelta(days=1), day.date().isoformat()),
        ("WEEK", week, week + timedelta(days=7), f"{week.isocalendar().year}-W{week.isocalendar().week:02d}"),
        ("MONTH", month, next_month(month), f"{local.year}-{local.month:02d}"),
        ("QUARTER", quarter, next_month(quarter, 3), f"{local.year}-Q{(local.month - 1) // 3 + 1}"),
        ("YEAR", year, year.replace(year=year.year + 1), str(local.year)),
    ]
    result = [{
        "window_type": kind,
        "start_at": start.astimezone(timezone.utc),
        "end_at": end.astimezone(timezone.utc),
        "timezone": timezone_name,
        "label": label,
        "source": "SYSTEM_CALENDAR",
    } for kind, start, end, label in boundaries]
    for item in custom_windows:
        start = item.get("start_at")
        end = item.get("end_at")
        if isinstance(start, str):
            start = datetime.fromisoformat(start.replace("Z", "+00:00"))
        if isinstance(end, str):
            end = datetime.fromisoformat(end.replace("Z", "+00:00"))
        if start and end and _require_aware(start) <= occurred_at < _require_aware(end):
            result.append({
                "window_type": item.get("window_type", "USER_DEFINED_PERIOD"),
                "start_at": start.astimezone(timezone.utc),
                "end_at": end.astimezone(timezone.utc),
                "timezone": item.get("timezone", timezone_name),
                "label": item.get("label"),
                "source": item.get("source", "USER_DEFINED"),
            })
    return result


def temporal_weight(
    occurred_at: datetime,
    evidence_type: str,
    *,
    now: datetime | None = None,
    user_marked_still_relevant: bool = False,
    non_standard_decay: bool = False,
    half_lives: dict[str, float] | None = None,
) -> tuple[float, str]:
    _require_aware(occurred_at)
    now = now or datetime.now(timezone.utc)
    _require_aware(now)
    if non_standard_decay:
        return 1.0, "NON_STANDARD_DECAY"
    if user_marked_still_relevant:
        return 1.0, "USER_OVERRIDE"
    configured = {**DEFAULT_HALF_LIFE_DAYS, **(half_lives or {})}
    half_life = configured.get(evidence_type, 60.0)
    if math.isinf(half_life):
        return 1.0, "STANDARD"
    age_days = max(0.0, (now - occurred_at.astimezone(timezone.utc)).total_seconds() / 86400)
    # Historical evidence remains queryable and distinguishable from invalidated
    # evidence even when its current relevance is extremely small.
    return max(0.000001, round(math.exp(-math.log(2) * age_days / max(half_life, 0.001)), 6)), "STANDARD"


def independent_evidence(evidence: Iterable[dict[str, Any] | PatternEvidence]) -> list[dict[str, Any]]:
    """Count one strongest item per source-derived independence group."""
    strongest: dict[str, dict[str, Any]] = {}
    for raw in evidence:
        item = raw.model_dump() if isinstance(raw, PatternEvidence) else dict(raw)
        group = item.get("independence_group") or f"{item.get('source_record_type')}:{item.get('source_record_id')}"
        strength = float(item.get("temporal_weight", 1)) * float(item.get("relevance", 1))
        existing = strongest.get(group)
        if existing is None or strength > float(existing.get("temporal_weight", 1)) * float(existing.get("relevance", 1)):
            strongest[group] = item
    return list(strongest.values())


def discover_rule_pattern_candidates(chains: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Discover repeated structures, never hidden motives or mere emotion labels."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for chain in chains:
        if chain.get("excluded") or chain.get("processing_preference") in {"STORE_ONLY", "EXCLUDE_FROM_TWIN"}:
            continue
        signature = chain.get("signature") or {}
        structured = signature.get("node_types") or [signature.get("trigger_type"), signature.get("response_type")]
        structured = [item for item in structured if item]
        if len(structured) < 2:
            continue
        safe_signature = {
            "node_types": structured,
            "relation_types": signature.get("relation_types", []),
        }
        key = hashlib.sha256(json.dumps(safe_signature, sort_keys=True).encode()).hexdigest()
        grouped[key].append({**chain, "safe_signature": safe_signature})

    candidates = []
    for key, items in grouped.items():
        unique: dict[str, dict[str, Any]] = {}
        for item in items:
            group = item.get("independence_group") or str(item.get("life_event_id") or item.get("source_record_id"))
            if group and group != "None":
                unique[group] = item
        confirmed_count = sum(bool(item.get("confirmed")) for item in unique.values())
        if len(unique) < 3 and confirmed_count < 2:
            continue
        ordered = sorted(unique.values(), key=lambda item: item["occurred_at"])
        season_ids = {item.get("life_season_id") for item in ordered if item.get("life_season_id")}
        domains = sorted({item.get("life_domain") for item in ordered if item.get("life_domain")})
        scope_kind = "LIFE_SEASON_SPECIFIC" if len(season_ids) == 1 else ("DOMAIN_SPECIFIC" if domains else "CURRENT_CONTEXT_ONLY")
        node_types = set(ordered[0]["safe_signature"]["node_types"])
        pattern_type = "GRACE_SUPPORT_PATTERN" if node_types.intersection({"GRACE_EVIDENCE", "PROTECTIVE_FACTOR"}) else (
            "RECOVERY_PATTERN" if "RECOVERY_RESPONSE" in node_types else "FORMATION_DIRECTION_PATTERN"
        )
        candidates.append({
            "pattern_key": key,
            "pattern_type": pattern_type,
            "signature": ordered[0]["safe_signature"],
            "supporting_record_ids": [str(item["source_record_id"]) for item in ordered],
            "independent_evidence_count": len(unique),
            "first_observed_at": ordered[0]["occurred_at"],
            "last_observed_at": ordered[-1]["occurred_at"],
            "scope": {"scope_kind": scope_kind, "life_domains": domains, "life_season_ids": sorted(season_ids)},
            "candidate_strength": "STRONG" if len(unique) >= 5 else "MODERATE",
            "is_alternative_response": any(bool(item.get("is_alternative_response")) for item in ordered),
            "limitations": [
                "这是重复结构候选，不代表固定人格或隐藏动机。",
                "相关记录可能集中在困难时期，记录频率不等于真实发生频率。",
            ],
            "rule_version": RULE_VERSION,
        })
    return candidates


def calculate_pattern_confidence(
    evidence: Iterable[dict[str, Any] | PatternEvidence],
    *,
    user_review_status: str = "PENDING",
    scope_consistency_factor: float = 1.0,
    now: datetime | None = None,
) -> PatternConfidence:
    now = now or datetime.now(timezone.utc)
    items = independent_evidence(evidence)
    if user_review_status in {"REJECTED", "DO_NOT_SUGGEST_AGAIN"}:
        return PatternConfidence(
            level="VERY_LOW", numeric_value=0, support_score=0, counterevidence_score=0,
            recency_factor=0, diversity_factor=0, user_confirmation_factor=-1,
            scope_consistency_factor=max(0, min(1, scope_consistency_factor)),
            rationale=["用户已明确否定；系统证据不能覆盖该决定。"], calculated_at=now,
        )
    support = counter = weighted_recency = 0.0
    groups = set()
    for item in items:
        if item.get("evidence_role") in {"INVALIDATED", "SUPERSEDED"}:
            continue
        weight = (
            float(item.get("temporal_weight", 1))
            * float(item.get("relevance", 1))
            * SOURCE_QUALITY_WEIGHT.get(item.get("source_quality"), 0.5)
        )
        weighted_recency += float(item.get("temporal_weight", 1))
        groups.add(item.get("independence_group") or item.get("source_record_id"))
        if item.get("evidence_role") == "SUPPORTING":
            support += weight
        elif item.get("evidence_role") in {"COUNTEREVIDENCE", "CONTEXT_LIMIT"}:
            counter += weight
    diversity = min(1.0, 0.45 + 0.12 * len(groups)) if groups else 0.0
    recency = min(1.0, weighted_recency / max(len(items), 1))
    scope = max(0.0, min(1.0, scope_consistency_factor))
    confirmation = 0.2 if user_review_status in {"CONFIRMED", "SCOPE_NARROWED", "SCOPE_EXPANDED"} else (
        0.1 if user_review_status == "PARTIALLY_CONFIRMED" else 0.0
    )
    adjusted_support = support * diversity * scope * recency
    numeric = max(0.0, min(1.0, adjusted_support / (adjusted_support + counter + 1.0) + confirmation))
    level = "VERY_LOW" if numeric < 0.2 else "LOW" if numeric < 0.4 else "MODERATE" if numeric < 0.7 else "HIGH"
    rationale = [
        f"按独立来源去重后使用 {len(groups)} 组证据。",
        f"支持证据权重 {support:.3f}；反证据与范围限制权重 {counter:.3f}。",
        "该值只描述当前证据对具体假设的支持程度，不评价人格、成熟度或改变能力。",
    ]
    return PatternConfidence(
        level=level, numeric_value=round(numeric, 6), support_score=round(support, 6),
        counterevidence_score=round(counter, 6), recency_factor=round(recency, 6),
        diversity_factor=round(diversity, 6), user_confirmation_factor=confirmation,
        scope_consistency_factor=scope, rationale=rationale, calculated_at=now,
    )


ALLOWED_TRANSITIONS = {
    "CANDIDATE": {"PENDING_USER_REVIEW", "REJECTED", "INVALIDATED"},
    "PENDING_USER_REVIEW": {"CONFIRMED_ACTIVE", "CONFIRMED_CONTEXTUAL", "REJECTED", "OUTDATED", "INVALIDATED"},
    "CONFIRMED_ACTIVE": {"CONFIRMED_CONTEXTUAL", "WEAKENING", "DORMANT", "RESOLVED", "OUTDATED", "INVALIDATED"},
    "CONFIRMED_CONTEXTUAL": {"WEAKENING", "DORMANT", "RESOLVED", "OUTDATED", "INVALIDATED"},
    "WEAKENING": {"CONFIRMED_ACTIVE", "DORMANT", "RESOLVED", "OUTDATED", "INVALIDATED"},
    "DORMANT": {"CONFIRMED_ACTIVE", "WEAKENING", "RESOLVED", "OUTDATED", "ARCHIVED", "INVALIDATED"},
    "RESOLVED": {"CONFIRMED_ACTIVE", "ARCHIVED"},
    "OUTDATED": {"PENDING_USER_REVIEW", "ARCHIVED"},
    "REJECTED": {"ARCHIVED"},
    "INVALIDATED": {"ARCHIVED"},
    "ARCHIVED": set(),
}


def transition_pattern(current: str, target: str, *, initiated_by: str) -> str:
    if current not in LIFECYCLE_STATUSES or target not in LIFECYCLE_STATUSES:
        raise ValueError("unknown lifecycle status")
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"invalid lifecycle transition: {current} -> {target}")
    if target == "RESOLVED" and initiated_by != "USER":
        raise ValueError("only the user can mark a pattern resolved")
    if target.startswith("CONFIRMED") and initiated_by != "USER":
        raise ValueError("only the user can confirm a pattern")
    return target


def build_long_term_snapshot(
    *, patterns: Iterable[dict[str, Any]], life_seasons: Iterable[dict[str, Any]],
    trajectories: Iterable[dict[str, Any]], window_start: datetime, window_end: datetime,
) -> dict[str, Any]:
    required = {"scope", "lifecycle_status", "counterevidence", "review_due_at", "user_review_status", "limitations"}
    valid = []
    blocked = []
    for pattern in patterns:
        missing = sorted(required - pattern.keys())
        if missing or not pattern.get("supporting_evidence"):
            blocked.append({"pattern_id": pattern.get("id"), "reason": "MISSING_REQUIRED_FIELDS", "missing": missing})
            continue
        if pattern.get("lifecycle_status") in {"REJECTED", "OUTDATED", "INVALIDATED", "ARCHIVED", "RESOLVED"}:
            continue
        valid.append(pattern)
    active = [item for item in valid if item["lifecycle_status"] == "CONFIRMED_ACTIVE"]
    contextual = [item for item in valid if item["lifecycle_status"] == "CONFIRMED_CONTEXTUAL"]
    weakening = [item for item in valid if item["lifecycle_status"] == "WEAKENING"]
    dormant = [item for item in valid if item["lifecycle_status"] == "DORMANT"]
    pending = [item for item in valid if item["lifecycle_status"] in {"CANDIDATE", "PENDING_USER_REVIEW"}]
    alternatives = [item for item in valid if item.get("pattern_type") == "FORMATION_DIRECTION_PATTERN" and item.get("is_alternative_response")]
    grace = [item for item in valid if item.get("pattern_type") == "GRACE_SUPPORT_PATTERN"]
    recovery = [item for item in valid if item.get("pattern_type") == "RECOVERY_PATTERN"]
    payload = {
        "window_start": window_start.isoformat(), "window_end": window_end.isoformat(),
        "active_life_seasons": [item for item in life_seasons if item.get("active")],
        "confirmed_active_patterns": active, "confirmed_contextual_patterns": contextual,
        "weakening_patterns": weakening, "dormant_patterns": dormant,
        "pending_pattern_candidates": pending, "emerging_alternative_responses": alternatives,
        "grace_and_protection_patterns": grace, "recovery_patterns": recovery,
        "trajectories": list(trajectories),
        "counterevidence_highlights": [evidence for item in valid for evidence in item.get("counterevidence", [])][:20],
        "unresolved_questions": ["这些模式是否仍符合你当前的阶段？"] if pending else [],
        "data_coverage": {"eligible_patterns": len(valid), "blocked_patterns": len(blocked)},
        "uncertainty_notes": ["记录偏差可能存在：你可能更常在困难时期记录。"],
        "limitations": [
            "长期模式只是基于已授权记录形成的可修正假设。",
            "它不定义你的本质，也不代表神对你的最终评价。",
            "属灵实践次数不等于属灵成长。",
        ],
        "blocked_items": blocked, "engine_version": ENGINE_VERSION,
    }
    payload["input_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()
    return payload


def build_formation_engine_context(snapshot: dict[str, Any], *, consent: bool, safety_level: str = "NONE") -> dict[str, Any]:
    if not consent:
        return {"available": False, "reason": "CONSENT_REQUIRED"}
    if safety_level in {"ELEVATED", "IMMINENT"}:
        return {
            "available": False, "reason": "CRISIS_SAFETY_GATE", "route": "CRISIS_CARE",
            "limitations": ["危机期间暂停普通深层模式分析。"],
        }
    confirmed = [
        *snapshot.get("confirmed_active_patterns", []),
        *snapshot.get("confirmed_contextual_patterns", []),
        *snapshot.get("weakening_patterns", []),
    ]
    return {
        "available": True,
        "current_life_seasons": snapshot.get("active_life_seasons", []),
        "confirmed_patterns": confirmed,
        "emerging_alternatives": snapshot.get("emerging_alternative_responses", []),
        "grace_and_protection": snapshot.get("grace_and_protection_patterns", []),
        "recovery_patterns": snapshot.get("recovery_patterns", []),
        "pending_hypotheses": [],
        "safety": {"formation_allowed": True},
        "limitations": snapshot.get("limitations", []),
        "engine_version": ENGINE_VERSION,
    }


def generate_pattern_review(
    review_type: str,
    *, patterns: Iterable[dict[str, Any]], window_start: datetime, window_end: datetime,
) -> dict[str, Any]:
    patterns = list(patterns)
    due = sorted(patterns, key=lambda item: item.get("review_due_at") or "9999")
    pending = [item for item in due if item.get("lifecycle_status") in {"CANDIDATE", "PENDING_USER_REVIEW"}][:1]
    return {
        "review_type": review_type, "window_start": window_start.isoformat(), "window_end": window_end.isoformat(),
        "new_candidates": [item.get("id") for item in pending],
        "active_patterns": [item.get("id") for item in patterns if item.get("lifecycle_status") in CURRENT_PATTERN_STATUSES],
        "weakening_patterns": [item.get("id") for item in patterns if item.get("lifecycle_status") == "WEAKENING"],
        "counterevidence_items": [e.get("id") for item in patterns for e in item.get("counterevidence", [])][:10],
        "grace_patterns": [item.get("id") for item in patterns if item.get("pattern_type") == "GRACE_SUPPORT_PATTERN"],
        "recovery_patterns": [item.get("id") for item in patterns if item.get("pattern_type") == "RECOVERY_PATTERN"],
        "user_questions": ["这个模式现在仍符合你吗？"] if pending else [],
        "limitations": ["跳过回顾不会使候选模式自动成立。", "每次默认只询问一个待确认问题。"],
    }


def temporal_data_quality(patterns: Iterable[dict[str, Any]]) -> dict[str, Any]:
    patterns = list(patterns)
    issues = []
    for item in patterns:
        pattern_id = item.get("id")
        for field in ("scope", "supporting_evidence", "counterevidence", "review_due_at", "user_review_status", "lifecycle_status", "limitations"):
            if field not in item or item[field] is None:
                issues.append({"severity": "HIGH", "pattern_id": pattern_id, "code": f"MISSING_{field.upper()}"})
        if item.get("source_kind") == "MODEL" and not item.get("alternative_explanations"):
            issues.append({"severity": "HIGH", "pattern_id": pattern_id, "code": "MODEL_ALTERNATIVES_MISSING"})
        if item.get("lifecycle_status") in {"REJECTED", "OUTDATED", "INVALIDATED"} and item.get("in_current_snapshot"):
            issues.append({"severity": "HIGH", "pattern_id": pattern_id, "code": "INELIGIBLE_PATTERN_IN_SNAPSHOT"})
        if _contains_forbidden_key(item):
            issues.append({"severity": "HIGH", "pattern_id": pattern_id, "code": "PROHIBITED_FIELD"})
    return {
        "total_patterns": len(patterns),
        "issues": issues, "high_severity_count": sum(item["severity"] == "HIGH" for item in issues),
        "snapshot_publish_allowed": not any(item["severity"] == "HIGH" for item in issues),
        "context_publish_allowed": not any(item["severity"] == "HIGH" for item in issues),
    }


def process_temporal_change(
    source_change: dict[str, Any],
    *, chains: Iterable[dict[str, Any]], consent: bool, safety_level: str,
    model_allowed: bool = False,
) -> TemporalPatternProcessingState:
    state: TemporalPatternProcessingState = {
        "source_change": source_change, "consent_result": {"allowed": consent},
        "safety_result": {"safety_level": safety_level}, "temporal_windows": [], "event_clusters": [],
        "rule_candidates": [], "semantic_candidates": [], "model_candidates": [], "supporting_evidence": [],
        "counterevidence": [], "validated_patterns": [], "confidence_updates": [], "lifecycle_updates": [],
        "life_season_updates": [], "trajectory_updates": [], "graph_updates": [], "snapshot": None, "errors": [],
    }
    preference = source_change.get("processing_preference", "STORE_ONLY")
    if not consent or preference in {"STORE_ONLY", "EXCLUDE_FROM_TWIN"} or source_change.get("excluded"):
        state["errors"].append({"code": "PROCESSING_SKIPPED", "reason": "CONSENT_OR_PROCESSING_PREFERENCE"})
        return state
    if safety_level in {"ELEVATED", "IMMINENT"}:
        state["errors"].append({"code": "PATTERN_INFERENCE_BLOCKED", "reason": "CRISIS_SAFETY_GATE"})
        return state
    state["rule_candidates"] = discover_rule_pattern_candidates(chains)
    if model_allowed:
        state["errors"].append({"code": "MODEL_ADAPTER_NOT_CONFIGURED", "recoverable": True})
    return state


CONSUMED_EVENTS = {
    "formation_twin.life_event_accepted", "formation_twin.life_event_superseded", "formation_twin.life_event_deleted",
    "formation_twin.life_event_excluded", "formation_twin.life_event_included",
    "formation_twin.emotion_observation_created", "formation_twin.emotion_candidate_confirmed",
    "formation_twin.emotional_snapshot_created", "formation_twin.formation_hypothesis_confirmed",
    "formation_twin.formation_hypothesis_rejected", "formation_twin.formation_chain_confirmed",
    "formation_twin.formation_chain_updated", "formation_twin.formation_chain_superseded",
    "formation_twin.consent_updated", "formation_twin.processing_paused", "formation_twin.processing_resumed",
    "crisis.case_routed", "crisis.case_stabilized",
}
PUBLISHED_EVENTS = {
    "formation_twin.event_cluster_created", "formation_twin.event_cluster_updated", "formation_twin.event_cluster_rejected",
    "formation_twin.pattern_candidate_created", "formation_twin.pattern_candidate_updated", "formation_twin.pattern_confirmed",
    "formation_twin.pattern_partially_confirmed", "formation_twin.pattern_rejected", "formation_twin.pattern_scope_changed",
    "formation_twin.pattern_confidence_updated", "formation_twin.pattern_weakened", "formation_twin.pattern_dormant",
    "formation_twin.pattern_resolved", "formation_twin.pattern_outdated", "formation_twin.pattern_invalidated",
    "formation_twin.pattern_reopened", "formation_twin.life_season_created", "formation_twin.life_season_updated",
    "formation_twin.life_season_closed", "formation_twin.life_season_reopened", "formation_twin.trajectory_created",
    "formation_twin.trajectory_updated", "formation_twin.alternative_response_emerging",
    "formation_twin.pattern_review_created", "formation_twin.pattern_review_completed",
    "formation_twin.pattern_review_skipped", "formation_twin.long_term_snapshot_created",
    "formation_twin.long_term_snapshot_superseded", "formation_twin.long_term_context_updated",
    "formation_twin.pattern_processing_skipped", "formation_twin.pattern_inference_blocked",
    "formation_twin.pattern_inference_failed",
}
