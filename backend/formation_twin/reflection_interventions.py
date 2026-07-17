"""Formation Twin Batch 6 reflection and micro-intervention domain engine.

The engine intentionally works on bounded, structured context.  It never needs
raw journal, prayer, confession, transcript, temptation, third-party, or crisis
bodies.  Every proposed action is optional and remains inert until the user
explicitly confirms it.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, time, timedelta, timezone
from enum import Enum
from typing import Any, Iterable, Literal, TypedDict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator


ENGINE_VERSION = "formation-reflection-intervention-engine-1.0"
TEMPLATE_VERSION = "formation-reflection-templates-1.0"
ROUTING_SCHEMA_VERSION = "formation-intervention-route-1.0"

CRISIS_LEVELS = {"ELEVATED", "IMMINENT"}
CONFIRMED_PATTERN_STATUSES = {"CONFIRMED_ACTIVE", "CONFIRMED_CONTEXTUAL", "WEAKENING"}
CONFIRMED_REVIEW_STATUSES = {"CONFIRMED", "PARTIALLY_CONFIRMED", "SCOPE_NARROWED", "SCOPE_EXPANDED"}
CAPACITY_MODES = {"MICRO_ONLY", "NORMAL", "REFLECTION_ONLY", "STORE_ONLY"}
CAPACITY_LEVELS = {"VERY_LOW_CAPACITY", "LOW_CAPACITY", "NORMAL_CAPACITY", "HIGH_CAPACITY", "USER_UNSPECIFIED"}
TARGET_MODULES = {
    "FORMATION_ENGINE", "PRAYER_OS", "HOLY_HABIT_ENGINE", "ATTENTION_OS", "REST",
    "RELATIONAL_SUPPORT", "PROFESSIONAL_SUPPORT", "CRISIS_CARE", "NO_ACTION",
}
DECISION_STATUSES = {
    "ACCEPTED", "ACCEPTED_WITH_MODIFICATION", "REQUESTED_ALTERNATIVE", "DEFERRED",
    "SKIPPED", "REJECTED", "NO_ACTION_SELECTED",
}

PROHIBITED_KEYS = {
    "journal_text", "journal_body", "prayer_text", "confession_text", "temptation_text",
    "voice_transcript", "transcript", "crisis_text", "crisis_body", "third_party_identity",
    "full_formation_chain", "raw_content", "full_text", "compliance_score",
    "intervention_success_score", "spiritual_discipline_score", "spiritual_growth_score",
    "holiness_score", "obedience_score", "salvation_probability", "spiritual_rank",
}
PROHIBITED_PHRASES = {
    "神告诉你", "圣灵要你", "神正在惩罚你", "必须这样做才算顺服", "没有真正悔改",
    "正在失去救恩", "真正的基督徒不会", "你患有抑郁症", "焦虑型人格", "依恋障碍",
    "只要祷告就不需要", "现在不做就说明", "连续完成才能", "成长正在下降",
    "提高属灵等级", "你的偶像是", "治死偶像计划", "属灵执行力", "顺服程度", "不愿顺服",
    "治疗你的抑郁症",
    "god told you", "the holy spirit requires", "you are losing salvation", "real christians do not",
    "this will treat your depression", "compliance score", "spiritual rank", "obedience score",
}
SENSITIVE_NOTIFICATION_PHRASES = {
    "认罪", "试探", "婚姻冲突", "危机", "自杀", "抑郁", "成瘾", "confession", "temptation", "crisis",
}


class CapacityMode(str, Enum):
    MICRO_ONLY = "MICRO_ONLY"
    NORMAL = "NORMAL"
    REFLECTION_ONLY = "REFLECTION_ONLY"
    STORE_ONLY = "STORE_ONLY"


class UserCapacitySnapshot(BaseModel):
    energy_level: int | None = Field(default=None, ge=0, le=10)
    stress_level: int | None = Field(default=None, ge=0, le=10)
    sleep_quality: int | None = Field(default=None, ge=0, le=10)
    available_minutes: int | None = Field(default=None, ge=0, le=1440)
    cognitive_load: Literal["LOW", "MODERATE", "HIGH", "UNKNOWN"] = "UNKNOWN"
    emotional_load: Literal["LOW", "MODERATE", "HIGH", "UNKNOWN"] = "UNKNOWN"
    practical_load: Literal["LOW", "MODERATE", "HIGH", "UNKNOWN"] = "UNKNOWN"
    capacity_level: str
    user_selected_mode: CapacityMode = CapacityMode.NORMAL
    source_event_ids: list[str] = Field(default_factory=list, max_length=10)
    generated_at: datetime

    @field_validator("generated_at")
    @classmethod
    def aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timezone-aware datetime required")
        return value

    @field_validator("capacity_level")
    @classmethod
    def known_capacity(cls, value: str) -> str:
        if value not in CAPACITY_LEVELS:
            raise ValueError("unknown capacity level")
        return value


class ReflectionContext(BaseModel):
    context_id: str
    context_type: Literal["DAILY", "WEEKLY", "EFFECT_REVIEW"]
    window_start: datetime
    window_end: datetime
    current_emotional_state: dict[str, Any] | None = None
    current_formation_state: dict[str, Any] | None = None
    active_life_seasons: list[dict[str, Any]] = Field(default_factory=list, max_length=2)
    confirmed_patterns: list[dict[str, Any]] = Field(default_factory=list, max_length=3)
    weakening_patterns: list[dict[str, Any]] = Field(default_factory=list, max_length=3)
    emerging_alternative_responses: list[dict[str, Any]] = Field(default_factory=list, max_length=3)
    pending_clarification_items: list[dict[str, Any]] = Field(default_factory=list, max_length=1)
    current_risk_factors: list[dict[str, Any]] = Field(default_factory=list, max_length=3)
    current_protective_factors: list[dict[str, Any]] = Field(default_factory=list, max_length=3)
    grace_and_recovery_factors: list[dict[str, Any]] = Field(default_factory=list, max_length=3)
    recent_effects: list[dict[str, Any]] = Field(default_factory=list, max_length=3)
    user_capacity: UserCapacitySnapshot
    user_preferences: dict[str, Any] = Field(default_factory=dict)
    safety_status: dict[str, Any]
    data_coverage: dict[str, Any]
    limitations: list[str] = Field(default_factory=list, max_length=10)
    allowed_output: Literal["FULL", "LIGHTWEIGHT_CHECKIN_ONLY", "REFLECTION_ONLY", "STORE_ONLY", "CRISIS_ONLY"]
    generated_at: datetime

    @model_validator(mode="after")
    def validate_context(self):
        for value in (self.window_start, self.window_end, self.generated_at):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("timezone-aware datetime required")
        if self.window_end < self.window_start:
            raise ValueError("invalid context window")
        if contains_prohibited_key(self.model_dump()):
            raise ValueError("sensitive body or scoring field is not permitted")
        return self


class ReflectionQuestion(BaseModel):
    question_id: str
    question_type: str
    question_text: str = Field(min_length=1, max_length=300)
    selection_rationale: list[str] = Field(min_length=1, max_length=4)
    source_references: list[dict[str, str]] = Field(default_factory=list, max_length=5)
    burden_level: Literal["VERY_LOW", "LOW", "NORMAL"]
    template_version: str = TEMPLATE_VERSION
    created_at: datetime

    @field_validator("question_text")
    @classmethod
    def safe_question(cls, value: str) -> str:
        validate_safe_text(value)
        return value


class ReflectionMirror(BaseModel):
    mirror_id: str
    mirror_type: Literal["DAILY", "WEEKLY"]
    context_id: str
    headline: str = Field(min_length=1, max_length=160)
    mirror_text: str = Field(min_length=1, max_length=600)
    confirmed_observations: list[dict[str, Any]] = Field(default_factory=list, max_length=3)
    pending_items: list[dict[str, Any]] = Field(default_factory=list, max_length=1)
    grace_and_protection: list[dict[str, Any]] = Field(default_factory=list, max_length=3)
    high_value_question: ReflectionQuestion | None = None
    proposed_intervention_id: str | None = None
    source_references: list[dict[str, str]] = Field(default_factory=list, max_length=10)
    limitations: list[str] = Field(default_factory=list, max_length=6)
    generation_method: Literal["RULE", "MODEL_VALIDATED", "LIGHTWEIGHT_TEMPLATE"]
    template_version: str = TEMPLATE_VERSION
    user_review_status: Literal["PENDING", "CONFIRMED", "CORRECTED", "DISMISSED"] = "PENDING"
    created_at: datetime

    @field_validator("headline", "mirror_text")
    @classmethod
    def safe_text(cls, value: str) -> str:
        validate_safe_text(value)
        return value


class MicroIntervention(BaseModel):
    intervention_id: str
    intervention_type: str
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=600)
    rationale: str = Field(min_length=1, max_length=400)
    intended_support: list[str] = Field(default_factory=list, max_length=5)
    estimated_duration_minutes: int = Field(ge=0, le=30)
    effort_level: Literal["VERY_LOW", "LOW", "NORMAL"]
    target_module: str
    routing_payload: dict[str, Any]
    source_pattern_ids: list[str] = Field(default_factory=list, max_length=3)
    source_factor_ids: list[str] = Field(default_factory=list, max_length=5)
    safety_classification: Literal["STANDARD", "SENSITIVE_USER_CONFIRMED", "PROFESSIONAL_SUPPORT", "CRISIS_ONLY"]
    contraindications: list[str] = Field(default_factory=list, max_length=8)
    generation_method: Literal["LIBRARY", "USER_MODIFIED", "MODEL_VALIDATED"] = "LIBRARY"
    statement_type: Literal["OPTIONAL_SUPPORT_PROPOSAL"] = "OPTIONAL_SUPPORT_PROPOSAL"
    required_user_confirmation: Literal[True] = True
    one_time: bool = True
    reminder_enabled: bool = False
    requires_second_confirmation: bool = False
    lifecycle_status: Literal["PROPOSED", "BLOCKED", "EXPIRED"] = "PROPOSED"
    created_at: datetime
    expires_at: datetime | None = None

    @field_validator("target_module")
    @classmethod
    def known_target(cls, value: str) -> str:
        if value not in TARGET_MODULES:
            raise ValueError("unknown intervention target")
        return value

    @field_validator("title", "description", "rationale")
    @classmethod
    def safe_intervention_text(cls, value: str) -> str:
        validate_safe_text(value)
        return value

    @model_validator(mode="after")
    def validate_payload(self):
        if contains_prohibited_key(self.routing_payload):
            raise ValueError("routing payload contains sensitive body or score")
        if self.target_module == "HOLY_HABIT_ENGINE" and self.one_time:
            raise ValueError("habit proposals must be separately confirmed as repeating")
        if self.reminder_enabled:
            raise ValueError("proposal defaults cannot enable reminders")
        return self


class EffectReview(BaseModel):
    review_id: str
    intervention_id: str
    execution_status: Literal[
        "COMPLETED", "PARTIALLY_COMPLETED", "NOT_STARTED", "STOPPED", "FORGOTTEN",
        "NO_LONGER_RELEVANT", "DECLINED_AFTER_ACCEPTANCE", "UNKNOWN",
    ]
    user_reported_helpfulness: Literal["NOT_HELPFUL", "SLIGHTLY_HELPFUL", "HELPFUL", "VERY_HELPFUL", "UNCERTAIN"] | None = None
    user_reported_burden: Literal["VERY_LOW", "LOW", "ACCEPTABLE", "HIGH", "TOO_HIGH"] | None = None
    emotional_effect: dict[str, Any] | None = None
    formation_effect: dict[str, Any] | None = None
    practical_effect: dict[str, Any] | None = None
    what_helped: str | None = Field(default=None, max_length=1000)
    what_did_not_help: str | None = Field(default=None, max_length=1000)
    preferred_adjustment: str | None = Field(default=None, max_length=1000)
    statement_type: Literal["USER_REPORTED_FACT"] = "USER_REPORTED_FACT"
    reviewed_at: datetime


class ReflectionInterventionState(TypedDict):
    profile: dict[str, Any] | None
    consent: dict[str, Any] | None
    safety_status: dict[str, Any] | None
    capacity: dict[str, Any] | None
    context: dict[str, Any] | None
    priority_theme: dict[str, Any] | None
    mirror: dict[str, Any] | None
    question_candidates: list[dict[str, Any]]
    intervention_candidates: list[dict[str, Any]]
    selected_question: dict[str, Any] | None
    selected_intervention: dict[str, Any] | None
    validation_result: dict[str, Any] | None
    user_decision: dict[str, Any] | None
    routing_result: dict[str, Any] | None
    effect_review: dict[str, Any] | None
    errors: list[dict[str, Any]]


def contains_prohibited_key(value: Any) -> bool:
    if isinstance(value, dict):
        keys = {str(key).lower() for key in value}
        return bool(keys.intersection(PROHIBITED_KEYS)) or any(contains_prohibited_key(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(contains_prohibited_key(item) for item in value)
    return False


def validate_safe_text(text: str) -> None:
    lowered = text.lower()
    if any(phrase.lower() in lowered for phrase in PROHIBITED_PHRASES):
        raise ValueError("theological verdict, diagnosis, shame, or performance language is not allowed")


def _safe_reference(item: dict[str, Any], fallback_type: str) -> dict[str, str] | None:
    reference_id = item.get("id") or item.get("pattern_id") or item.get("source_record_id")
    if not reference_id:
        return None
    return {"reference_type": str(item.get("reference_type") or fallback_type), "reference_id": str(reference_id)}


def build_user_capacity(
    *,
    energy_level: int | None,
    stress_level: int | None,
    sleep_quality: int | None,
    available_minutes: int | None,
    user_selected_mode: str = "NORMAL",
    source_event_ids: Iterable[str] = (),
    now: datetime | None = None,
) -> UserCapacitySnapshot:
    if user_selected_mode not in CAPACITY_MODES:
        raise ValueError("unknown user-selected capacity mode")
    values = (energy_level, stress_level, sleep_quality)
    if any(value is not None and not 0 <= value <= 10 for value in values):
        raise ValueError("capacity values must be between zero and ten")
    if available_minutes is not None and not 0 <= available_minutes <= 1440:
        raise ValueError("available minutes out of range")

    if energy_level is None and stress_level is None and sleep_quality is None and available_minutes is None:
        level = "USER_UNSPECIFIED"
    elif (
        user_selected_mode == "MICRO_ONLY" or (energy_level is not None and energy_level <= 2)
        or (stress_level is not None and stress_level >= 9) or (sleep_quality is not None and sleep_quality <= 2)
        or (available_minutes is not None and available_minutes <= 1)
    ):
        level = "VERY_LOW_CAPACITY"
    elif (
        (energy_level is not None and energy_level <= 4) or (stress_level is not None and stress_level >= 7)
        or (sleep_quality is not None and sleep_quality <= 4) or (available_minutes is not None and available_minutes <= 3)
    ):
        level = "LOW_CAPACITY"
    elif (
        energy_level is not None and energy_level >= 8 and (stress_level is None or stress_level <= 3)
        and (sleep_quality is None or sleep_quality >= 7) and (available_minutes is None or available_minutes >= 15)
    ):
        level = "HIGH_CAPACITY"
    else:
        level = "NORMAL_CAPACITY"

    cognitive = "HIGH" if (stress_level or 0) >= 8 else ("MODERATE" if stress_level is not None else "UNKNOWN")
    emotional = "HIGH" if (stress_level or 0) >= 8 else ("LOW" if stress_level is not None and stress_level <= 3 else ("MODERATE" if stress_level is not None else "UNKNOWN"))
    practical = "HIGH" if available_minutes is not None and available_minutes <= 3 else ("LOW" if available_minutes is not None and available_minutes >= 15 else ("MODERATE" if available_minutes is not None else "UNKNOWN"))
    return UserCapacitySnapshot(
        energy_level=energy_level, stress_level=stress_level, sleep_quality=sleep_quality,
        available_minutes=available_minutes, cognitive_load=cognitive, emotional_load=emotional,
        practical_load=practical, capacity_level=level, user_selected_mode=CapacityMode(user_selected_mode),
        source_event_ids=list(source_event_ids)[:10], generated_at=now or datetime.now(timezone.utc),
    )


def assemble_reflection_context(
    *,
    context_type: str,
    window_start: datetime,
    window_end: datetime,
    emotional_state: dict[str, Any] | None,
    formation_state: dict[str, Any] | None,
    patterns: Iterable[dict[str, Any]],
    life_seasons: Iterable[dict[str, Any]],
    capacity: UserCapacitySnapshot,
    preferences: dict[str, Any] | None,
    safety_status: dict[str, Any] | None,
    protective_factors: Iterable[dict[str, Any]] = (),
    grace_recovery_factors: Iterable[dict[str, Any]] = (),
    risk_factors: Iterable[dict[str, Any]] = (),
    alternative_responses: Iterable[dict[str, Any]] = (),
    recent_effects: Iterable[dict[str, Any]] = (),
    now: datetime | None = None,
) -> ReflectionContext:
    now = now or datetime.now(timezone.utc)
    pattern_items = [dict(item) for item in patterns if not item.get("deleted_at")]
    confirmed = [
        item for item in pattern_items
        if item.get("lifecycle_status") in CONFIRMED_PATTERN_STATUSES
        and item.get("user_review_status") in CONFIRMED_REVIEW_STATUSES
    ]
    weakening = [item for item in confirmed if item.get("lifecycle_status") == "WEAKENING"]
    pending = [
        item for item in pattern_items
        if item.get("lifecycle_status") in {"CANDIDATE", "PENDING_USER_REVIEW"}
        and item.get("user_review_status") == "PENDING"
    ]
    seasons = [
        dict(item) for item in life_seasons
        if item.get("active", True) and not item.get("deleted_at")
        and item.get("user_review_status") in {"CONFIRMED", "PARTIALLY_CONFIRMED"}
    ]
    safety = dict(safety_status or {"safety_level": "NONE"})
    safety_level = str(safety.get("safety_level", "NONE")).upper()
    mode = capacity.user_selected_mode.value
    limitations: list[str] = []
    if safety_level in CRISIS_LEVELS:
        allowed_output = "CRISIS_ONLY"
        limitations.append("当前安全状态优先，普通镜像和行动已暂停。")
    elif mode == "STORE_ONLY":
        allowed_output = "STORE_ONLY"
        limitations.append("用户选择只记录，不分析。")
    elif mode == "REFLECTION_ONLY" or bool((preferences or {}).get("reflection_only")):
        allowed_output = "REFLECTION_ONLY"
        limitations.append("用户选择只接收镜像，不接收行动。")
    elif not emotional_state and not confirmed:
        allowed_output = "LIGHTWEIGHT_CHECKIN_ONLY"
        limitations.append("当前数据不足，只提供轻量核对或休息选项。")
    else:
        allowed_output = "FULL"
    if pending:
        limitations.append("未确认候选只可用于澄清问题，不会驱动行动。")

    context = ReflectionContext(
        context_id=str(uuid.uuid4()), context_type=context_type, window_start=window_start, window_end=window_end,
        current_emotional_state=emotional_state, current_formation_state=formation_state,
        active_life_seasons=seasons[:2], confirmed_patterns=confirmed[:3], weakening_patterns=weakening[:3],
        emerging_alternative_responses=[dict(item) for item in alternative_responses][:3],
        pending_clarification_items=pending[:1], current_risk_factors=[dict(item) for item in risk_factors][:3],
        current_protective_factors=[dict(item) for item in protective_factors][:3],
        grace_and_recovery_factors=[dict(item) for item in grace_recovery_factors][:3],
        recent_effects=[dict(item) for item in recent_effects][:3], user_capacity=capacity,
        user_preferences=dict(preferences or {}), safety_status=safety,
        data_coverage={
            "status": "INSUFFICIENT_DATA" if allowed_output == "LIGHTWEIGHT_CHECKIN_ONLY" else "AVAILABLE",
            "confirmed_pattern_count": len(confirmed), "active_life_season_count": len(seasons),
            "has_current_emotional_state": bool(emotional_state), "pending_context_used_for_action": False,
        }, limitations=limitations, allowed_output=allowed_output, generated_at=now,
    )
    return context


QUESTION_TEMPLATES = {
    "REST_AND_LIMITS": "今天什么事情可以暂时不完成？",
    "PROTECTIVE_FACTOR": "这段时间，什么帮助你没有继续沿着旧路径走下去？",
    "CHOICE_POINT": "下次类似情况出现时，你最想先暂停哪一步？",
    "EMOTION_NAMING": "此刻最需要被承认的感受是什么？",
    "RELATIONAL_CONNECTION": "现在有谁可以听你真实地说五分钟？",
    "ALTERNATIVE_RESPONSE": "是什么帮助你这次选择了不同的回应？",
    "CLARIFICATION": "这个尚未确认的观察，与你当前的实际经历相符吗？",
}


def select_high_value_question(
    context: ReflectionContext,
    *,
    recent_questions: Iterable[dict[str, Any]] = (),
    now: datetime | None = None,
) -> ReflectionQuestion | None:
    if context.allowed_output in {"STORE_ONLY", "CRISIS_ONLY"}:
        return None
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    blocked_types: set[str] = set()
    for item in recent_questions:
        asked_at = item.get("created_at")
        if isinstance(asked_at, str):
            try: asked_at = datetime.fromisoformat(asked_at.replace("Z", "+00:00"))
            except ValueError: asked_at = None
        if item.get("do_not_ask_again") or item.get("status") == "DO_NOT_ASK_AGAIN" or (asked_at and asked_at >= cutoff):
            blocked_types.add(str(item.get("question_type")))

    capacity = context.user_capacity.capacity_level
    if context.pending_clarification_items and not context.confirmed_patterns and not context.current_emotional_state:
        candidates = ["CLARIFICATION", "EMOTION_NAMING"]
    elif capacity in {"VERY_LOW_CAPACITY", "LOW_CAPACITY"}:
        candidates = ["REST_AND_LIMITS", "EMOTION_NAMING", "RELATIONAL_CONNECTION"]
    elif context.user_preferences.get("self_reported_spiritual_distance"):
        candidates = ["EMOTION_NAMING", "RELATIONAL_CONNECTION", "REST_AND_LIMITS"]
    elif context.emerging_alternative_responses:
        candidates = ["ALTERNATIVE_RESPONSE", "PROTECTIVE_FACTOR", "CHOICE_POINT"]
    elif context.current_protective_factors or context.grace_and_recovery_factors:
        candidates = ["PROTECTIVE_FACTOR", "CHOICE_POINT", "EMOTION_NAMING"]
    elif context.confirmed_patterns:
        candidates = ["CHOICE_POINT", "EMOTION_NAMING", "RELATIONAL_CONNECTION"]
    elif context.pending_clarification_items:
        candidates = ["CLARIFICATION", "EMOTION_NAMING"]
    else:
        candidates = ["EMOTION_NAMING", "REST_AND_LIMITS"]
    selected = next((item for item in candidates if item not in blocked_types), None)
    if not selected:
        return None
    refs = []
    source_pool = (
        context.emerging_alternative_responses or context.current_protective_factors
        or context.confirmed_patterns or context.pending_clarification_items
    )
    if source_pool:
        ref = _safe_reference(source_pool[0], "STRUCTURED_CONTEXT")
        if ref: refs.append(ref)
    return ReflectionQuestion(
        question_id=str(uuid.uuid4()), question_type=selected, question_text=QUESTION_TEMPLATES[selected],
        selection_rationale=["与当前已授权上下文相关", "符合当前容量", "七天重复控制已应用"],
        source_references=refs, burden_level="VERY_LOW" if capacity == "VERY_LOW_CAPACITY" else "LOW",
        created_at=now,
    )


INTERVENTION_LIBRARY: dict[str, dict[str, Any]] = {
    "PAUSE": {"title": "暂停一分钟", "description": "暂停60秒，只说出现在最明显的一个感受。", "minutes": 1, "effort": "VERY_LOW", "target": "FORMATION_ENGINE"},
    "REST": {"title": "允许今天少做一点", "description": "取消一个非必要任务，并在准备好时再继续。", "minutes": 1, "effort": "VERY_LOW", "target": "REST"},
    "BODY_REGULATION": {"title": "让身体先稳定下来", "description": "喝一点水，做三次缓慢呼吸，然后决定是否继续。", "minutes": 1, "effort": "VERY_LOW", "target": "REST"},
    "PRAYER": {"title": "两分钟诚实祷告", "description": "向神诚实说出：我现在害怕……，我希望……。不要求自己立刻平静。", "minutes": 2, "effort": "LOW", "target": "PRAYER_OS"},
    "SCRIPTURE_REFLECTION": {"title": "读一小段诗篇", "description": "只标出一句贴近当前处境的话，不要求用经文压下感受。", "minutes": 3, "effort": "LOW", "target": "FORMATION_ENGINE"},
    "RELATIONAL_SUPPORT": {"title": "联系一个可信任的人", "description": "准备一句消息：我今天有点累，可以听我说五分钟吗？消息不会自动发送。", "minutes": 1, "effort": "LOW", "target": "RELATIONAL_SUPPORT"},
    "ATTENTION_BOUNDARY": {"title": "设一个温和的注意力边界", "description": "选择一个30分钟的无通知时段；默认只是提醒，不会强制封锁。", "minutes": 1, "effort": "LOW", "target": "ATTENTION_OS"},
    "RECONCILIATION_PREPARATION": {"title": "先准备一句不攻击的话", "description": "写下一句想诚实表达、但不攻击对方的话；今天不要求进行对话。", "minutes": 3, "effort": "LOW", "target": "FORMATION_ENGINE"},
    "PROFESSIONAL_SUPPORT": {"title": "准备寻求专业支持", "description": "简要记录持续影响睡眠或工作的状态，准备与医生或专业咨询人员讨论。", "minutes": 3, "effort": "LOW", "target": "PROFESSIONAL_SUPPORT"},
    "HABIT_MICRO_STEP": {"title": "把这一步设为短期习惯", "description": "仅在你再次确认频率、持续天数和提醒后，创建3至7天的小习惯。", "minutes": 1, "effort": "LOW", "target": "HOLY_HABIT_ENGINE"},
    "NO_ACTION": {"title": "今天不增加行动", "description": "今天不增加任何操练，只保留这次看见。", "minutes": 0, "effort": "VERY_LOW", "target": "NO_ACTION"},
    "CRISIS_HANDOFF": {"title": "先使用安全支持", "description": "普通形成建议已暂停，请打开危机安全入口并联系可信任的真人。", "minutes": 0, "effort": "VERY_LOW", "target": "CRISIS_CARE"},
}


def _intervention(kind: str, context: ReflectionContext, *, now: datetime, source: dict[str, Any] | None = None) -> MicroIntervention:
    template = INTERVENTION_LIBRARY[kind]
    fallback_type = "PATTERN" if source and (source.get("pattern_id") or source.get("pattern_type")) else "STRUCTURED_CONTEXT"
    source_ref = _safe_reference(source or {}, fallback_type)
    is_habit = template["target"] == "HOLY_HABIT_ENGINE"
    return MicroIntervention(
        intervention_id=str(uuid.uuid4()), intervention_type=kind, title=template["title"],
        description=template["description"], rationale="根据当前容量和已确认信息提供的可选最小支持。",
        intended_support=["降低当前负担", "保留用户选择"],
        estimated_duration_minutes=template["minutes"], effort_level=template["effort"],
        target_module=template["target"], routing_payload={
            "action_type": kind, "title": template["title"], "description": template["description"],
            "estimated_minutes": template["minutes"], "one_time": not is_habit,
        }, source_pattern_ids=[source_ref["reference_id"]] if source_ref and source_ref["reference_type"] == "PATTERN" else [],
        source_factor_ids=[source_ref["reference_id"]] if source_ref and source_ref["reference_type"] != "PATTERN" else [],
        safety_classification="CRISIS_ONLY" if kind == "CRISIS_HANDOFF" else ("PROFESSIONAL_SUPPORT" if kind == "PROFESSIONAL_SUPPORT" else "STANDARD"),
        contraindications=["Crisis 高风险时仅允许 Crisis Care"] if kind != "CRISIS_HANDOFF" else [],
        one_time=not is_habit, requires_second_confirmation=is_habit, created_at=now,
        expires_at=now + timedelta(days=1),
    )


def generate_intervention_candidates(context: ReflectionContext, *, now: datetime | None = None) -> list[MicroIntervention]:
    now = now or datetime.now(timezone.utc)
    safety = str(context.safety_status.get("safety_level", "NONE")).upper()
    if safety in CRISIS_LEVELS:
        return [_intervention("CRISIS_HANDOFF", context, now=now)]
    if context.allowed_output in {"STORE_ONLY", "REFLECTION_ONLY"}:
        return [_intervention("NO_ACTION", context, now=now)]
    capacity = context.user_capacity.capacity_level
    blocked = set(context.user_preferences.get("blocked_intervention_types", []))
    choices: list[tuple[str, dict[str, Any] | None]] = []
    if capacity == "VERY_LOW_CAPACITY":
        choices = [("REST", None), ("BODY_REGULATION", None), ("RELATIONAL_SUPPORT", None)]
    elif capacity == "LOW_CAPACITY" or (context.user_capacity.stress_level or 0) >= 7:
        choices = [("REST", None), ("PAUSE", None), ("RELATIONAL_SUPPORT", None)]
    elif context.user_preferences.get("self_reported_spiritual_distance"):
        choices = [("PRAYER", None), ("RELATIONAL_SUPPORT", None), ("REST", None)]
    elif context.emerging_alternative_responses:
        choices = [("PAUSE", context.emerging_alternative_responses[0]), ("RELATIONAL_SUPPORT", None), ("REST", None)]
    elif any(item.get("pattern_type") == "AVOIDANCE_PATTERN" for item in context.confirmed_patterns):
        source = next(item for item in context.confirmed_patterns if item.get("pattern_type") == "AVOIDANCE_PATTERN")
        choices = [("ATTENTION_BOUNDARY", source), ("PAUSE", source), ("REST", None)]
    else:
        choices = [("PAUSE", context.confirmed_patterns[0] if context.confirmed_patterns else None), ("REST", None), ("RELATIONAL_SUPPORT", None)]
    result = [_intervention(kind, context, now=now, source=source) for kind, source in choices if kind not in blocked][:3]
    if not result:
        result = [_intervention("NO_ACTION", context, now=now)]
    return result


def select_minimum_action(context: ReflectionContext, candidates: Iterable[MicroIntervention]) -> dict[str, Any]:
    blocked = set(context.user_preferences.get("blocked_intervention_types", []))
    capacity = context.user_capacity.capacity_level
    allowed_minutes = 1 if capacity == "VERY_LOW_CAPACITY" else (3 if capacity == "LOW_CAPACITY" else 10)
    eligible: list[MicroIntervention] = []
    exclusions: list[dict[str, str]] = []
    for candidate in candidates:
        reason = None
        if candidate.intervention_type in blocked:
            reason = "USER_BLOCKED_CATEGORY"
        elif candidate.target_module != "CRISIS_CARE" and str(context.safety_status.get("safety_level", "NONE")).upper() in CRISIS_LEVELS:
            reason = "CRISIS_CONFLICT"
        elif candidate.estimated_duration_minutes > allowed_minutes:
            reason = "CAPACITY_MISMATCH"
        elif candidate.source_pattern_ids and not context.confirmed_patterns:
            reason = "UNCONFIRMED_SOURCE"
        elif contains_prohibited_key(candidate.routing_payload):
            reason = "SENSITIVE_ROUTING_PAYLOAD"
        if reason:
            exclusions.append({"intervention_id": candidate.intervention_id, "reason": reason})
        else:
            eligible.append(candidate)
    selected = eligible[0] if eligible else _intervention("NO_ACTION", context, now=datetime.now(timezone.utc))
    return {
        "selected": selected, "alternatives_available": max(0, len(eligible) - 1), "excluded": exclusions,
        "selection_explanation": ["当前相关性", "用户容量匹配", "低负担优先", "安全与拒绝硬约束"],
        "score_is_internal_only": True, "cross_user_comparison": False,
    }


def make_action_smaller(intervention: MicroIntervention, context: ReflectionContext) -> MicroIntervention:
    if intervention.intervention_type in {"NO_ACTION", "CRISIS_HANDOFF"}:
        return intervention
    if intervention.estimated_duration_minutes > 3:
        duration, description = 3, "只做三分钟；到时可以停止，不需要解决全部问题。"
    elif intervention.estimated_duration_minutes > 1:
        duration, description = 1, "只做一分钟；说出一个感受或保留一个看见，然后停止。"
    elif intervention.estimated_duration_minutes == 1:
        return _intervention("NO_ACTION", context, now=datetime.now(timezone.utc))
    else:
        return _intervention("NO_ACTION", context, now=datetime.now(timezone.utc))
    payload = {**intervention.routing_payload, "description": description, "estimated_minutes": duration}
    return intervention.model_copy(update={
        "intervention_id": str(uuid.uuid4()), "description": description,
        "estimated_duration_minutes": duration, "routing_payload": payload, "generation_method": "USER_MODIFIED",
    })


def validate_reflection_intervention(
    context: ReflectionContext,
    mirror: ReflectionMirror | None,
    question: ReflectionQuestion | None,
    intervention: MicroIntervention | None,
) -> dict[str, Any]:
    violations: list[dict[str, str]] = []
    items: list[tuple[str, Any]] = [("context", context.model_dump()), ("mirror", mirror.model_dump() if mirror else {}), ("question", question.model_dump() if question else {}), ("intervention", intervention.model_dump() if intervention else {})]
    for area, item in items:
        if contains_prohibited_key(item):
            violations.append({"area": area, "code": "PROHIBITED_FIELD", "severity": "HIGH"})
        try:
            validate_safe_text(json.dumps(item, ensure_ascii=False, default=str))
        except ValueError:
            violations.append({"area": area, "code": "UNSAFE_LANGUAGE", "severity": "HIGH"})
    safety = str(context.safety_status.get("safety_level", "NONE")).upper()
    if safety in CRISIS_LEVELS and intervention and intervention.target_module != "CRISIS_CARE":
        violations.append({"area": "intervention", "code": "CRISIS_ORDINARY_ACTION", "severity": "HIGH"})
    if context.user_capacity.capacity_level == "VERY_LOW_CAPACITY" and intervention and intervention.estimated_duration_minutes > 1:
        violations.append({"area": "intervention", "code": "CAPACITY_OVERLOAD", "severity": "HIGH"})
    if intervention and intervention.reminder_enabled:
        violations.append({"area": "intervention", "code": "HIDDEN_REMINDER", "severity": "HIGH"})
    if intervention and not intervention.required_user_confirmation:
        violations.append({"area": "intervention", "code": "MISSING_CONFIRMATION", "severity": "HIGH"})
    if mirror and not mirror.source_references and context.allowed_output == "FULL":
        violations.append({"area": "mirror", "code": "MISSING_SOURCE_REFERENCE", "severity": "HIGH"})
    high = [item for item in violations if item["severity"] == "HIGH"]
    fallback = "CRISIS_ROUTE" if safety in CRISIS_LEVELS else ("MIRROR_ONLY" if intervention else "STORE_ONLY")
    return {"valid": not high, "violations": violations, "fallback": None if not high else fallback, "blocked_content_logged": False}


def generate_daily_mirror(context: ReflectionContext, *, recent_questions: Iterable[dict[str, Any]] = (), now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if context.allowed_output == "CRISIS_ONLY":
        return {"status": "CRISIS_ROUTED", "mirror": None, "question": None, "intervention": _intervention("CRISIS_HANDOFF", context, now=now), "ordinary_intervention_suppressed": True}
    if context.allowed_output == "STORE_ONLY":
        return {"status": "STORED_WITHOUT_ANALYSIS", "mirror": None, "question": None, "intervention": None}

    confirmed_observations: list[dict[str, Any]] = []
    sources: list[dict[str, str]] = [{"reference_type": "REFLECTION_CONTEXT", "reference_id": context.context_id}]
    emotional = context.current_emotional_state or {}
    energy = emotional.get("energy_level", context.user_capacity.energy_level)
    stress = emotional.get("stress_level", context.user_capacity.stress_level)
    if stress is not None or energy is not None:
        parts = []
        if stress is not None: parts.append(f"压力 {stress}/10")
        if energy is not None: parts.append(f"精力 {energy}/10")
        confirmed_observations.append({"statement_type": "USER_REPORTED_FACT", "text": "你今天主动记录了" + "、".join(parts) + "。"})
        sources.extend({"reference_type": "CAPACITY_SOURCE_EVENT", "reference_id": item} for item in context.user_capacity.source_event_ids[:2])
    if context.confirmed_patterns:
        pattern = context.confirmed_patterns[0]
        confirmed_observations.append({"statement_type": "USER_CONFIRMED_PATTERN", "text": f"你曾确认：{pattern.get('title', '一个当前相关的回应模式')}。"})
        ref = _safe_reference(pattern, "PATTERN")
        if ref: sources.append(ref)
    season_text = ""
    if context.active_life_seasons:
        season = context.active_life_seasons[0]
        season_text = f"这只反映你当前的“{season.get('title', '生命阶段')}”阶段。"
        ref = _safe_reference(season, "LIFE_SEASON")
        if ref: sources.append(ref)
    grace = context.emerging_alternative_responses or context.grace_and_recovery_factors or context.current_protective_factors
    grace_observations: list[dict[str, Any]] = []
    if grace:
        item = grace[0]
        label = item.get("title") or item.get("description") or item.get("label") or "你已经注意到一种保护或恢复因素"
        grace_observations.append({"statement_type": "STRUCTURED_OBSERVATION", "text": str(label)[:180]})
        ref = _safe_reference(item, "PROTECTIVE_FACTOR")
        if ref: sources.append(ref)

    if context.allowed_output == "LIGHTWEIGHT_CHECKIN_ONLY":
        text = "目前只有少量主动记录，还不能判断更深的形成模式。今天可以只承认当前状态，或选择休息。"
        generation = "LIGHTWEIGHT_TEMPLATE"
    else:
        pieces = [item["text"] for item in confirmed_observations]
        if season_text: pieces.append(season_text)
        if grace_observations: pieces.append("同时也出现了一个值得保留的保护或新回应。")
        text = "".join(pieces) or "你愿意停下来记录当前状态，这本身提供了一个可以核对的起点。"
        generation = "RULE"
    limit = 80 if context.user_capacity.capacity_level == "VERY_LOW_CAPACITY" else 150
    text = text[:limit].rstrip("，；") + ("。" if not text[:limit].endswith("。") else "")
    question = select_high_value_question(context, recent_questions=recent_questions, now=now)
    intervention = None
    if context.allowed_output == "FULL":
        candidates = generate_intervention_candidates(context, now=now)
        intervention = select_minimum_action(context, candidates)["selected"]
    mirror = ReflectionMirror(
        mirror_id=str(uuid.uuid4()), mirror_type="DAILY", context_id=context.context_id,
        headline="今天最重要的一面镜子", mirror_text=text,
        confirmed_observations=confirmed_observations[:3], pending_items=[], grace_and_protection=grace_observations[:3],
        high_value_question=question, proposed_intervention_id=intervention.intervention_id if intervention else None,
        source_references=sources[:10], limitations=context.limitations[:6], generation_method=generation, created_at=now,
    )
    validation = validate_reflection_intervention(context, mirror, question, intervention)
    if not validation["valid"]:
        intervention = None
        if validation["fallback"] == "STORE_ONLY": mirror = None
    return {"status": "AVAILABLE", "mirror": mirror, "question": question, "intervention": intervention, "validation": validation}


def generate_weekly_review(context: ReflectionContext, *, active_days: int, previous_week: dict[str, Any] | None = None, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if context.allowed_output == "CRISIS_ONLY":
        return {"status": "CRISIS_ROUTED", "ordinary_review_suppressed": True}
    observations: list[dict[str, Any]] = []
    if context.current_emotional_state:
        observations.append({"statement_type": "CURRENT_STRUCTURED_STATE", "text": "本周记录中出现了一个值得核对的当前状态。"})
    if context.confirmed_patterns:
        observations.append({"statement_type": "USER_CONFIRMED_PATTERN", "text": context.confirmed_patterns[0].get("title", "一个已确认模式在本周相关。")})
    if context.emerging_alternative_responses:
        observations.append({"statement_type": "STRUCTURED_ALTERNATIVE", "text": context.emerging_alternative_responses[0].get("title", "本周出现了一个不同回应。")})
    grace = (context.current_protective_factors + context.grace_and_recovery_factors)[:3]
    question = select_high_value_question(context, now=now)
    intervention = None if context.allowed_output in {"REFLECTION_ONLY", "STORE_ONLY"} else select_minimum_action(context, generate_intervention_candidates(context, now=now))["selected"]
    comparisons = []
    if previous_week and context.current_emotional_state and "stress_level" in context.current_emotional_state and "stress_level" in previous_week:
        comparisons.append({"text": "本周已有记录中的压力值与上周记录不同。", "scope": "RECORDED_DATA_ONLY"})
    return {
        "status": "PENDING", "important_observations": observations[:3],
        "burden_factors": context.current_risk_factors[:3], "grace_and_protection": grace,
        "emerging_alternatives": context.emerging_alternative_responses[:3],
        "focus_theme": observations[0]["text"] if observations else None,
        "high_value_question": question, "proposed_intervention": intervention,
        "data_coverage": {"active_days": max(0, min(active_days, 7)), "statement": f"本周共有{max(0, min(active_days, 7))}天主动记录。以下回顾只反映已有记录，可能没有覆盖全部经历。"},
        "comparisons": comparisons, "limitations": context.limitations,
    }


def decide_intervention(
    intervention: MicroIntervention,
    decision: str,
    *,
    modifications: dict[str, Any] | None = None,
    habit_confirmation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if decision not in DECISION_STATUSES:
        raise ValueError("unknown intervention decision")
    modifications = dict(modifications or {})
    if contains_prohibited_key(modifications):
        raise ValueError("sensitive or scoring modification is not permitted")
    if decision in {"ACCEPTED", "ACCEPTED_WITH_MODIFICATION"} and intervention.target_module == "HOLY_HABIT_ENGINE":
        required = {"frequency", "duration_days", "reminder_enabled", "weekly_review_usage"}
        if not habit_confirmation or not required.issubset(habit_confirmation):
            raise ValueError("habit routing requires a second explicit configuration confirmation")
        if not 3 <= int(habit_confirmation["duration_days"]) <= 7:
            raise ValueError("habit duration must remain between three and seven days")
    return {
        "decision_status": decision, "user_modifications": modifications,
        "route_allowed": decision in {"ACCEPTED", "ACCEPTED_WITH_MODIFICATION"},
        "repeat_allowed": bool(habit_confirmation), "rejection_is_negative_label": False,
        "created_at": datetime.now(timezone.utc),
    }


def build_routing_command(
    intervention: MicroIntervention,
    *,
    user_confirmed: bool,
    request_id: str | None = None,
    habit_confirmation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not user_confirmed:
        raise ValueError("explicit user confirmation is required before routing")
    if intervention.target_module == "HOLY_HABIT_ENGINE" and not habit_confirmation:
        raise ValueError("habit routing requires second confirmation")
    if intervention.target_module == "NO_ACTION":
        return {"routed": False, "status": "NO_ACTION_SELECTED", "target_module": "NO_ACTION"}
    request_id = request_id or str(uuid.uuid4())
    payload = {
        "request_id": request_id, "proposal_id": intervention.intervention_id,
        "target_module": intervention.target_module, "action_type": intervention.intervention_type,
        "title": intervention.title, "description": intervention.description,
        "duration_minutes": intervention.estimated_duration_minutes,
        "one_time": intervention.one_time, "reminder_enabled": False,
        "user_confirmed": True, "source": "formation_twin", "routing_schema_version": ROUTING_SCHEMA_VERSION,
        "sensitive_context_included": False,
    }
    if habit_confirmation:
        payload["habit_configuration"] = {
            "frequency": habit_confirmation["frequency"], "duration_days": int(habit_confirmation["duration_days"]),
            "reminder_enabled": bool(habit_confirmation["reminder_enabled"]),
            "weekly_review_usage": bool(habit_confirmation["weekly_review_usage"]),
            "streak_enabled": False, "failure_language": "NEUTRAL",
        }
    if contains_prohibited_key(payload):
        raise ValueError("routing payload is not minimal or contains sensitive content")
    return {
        "routed": True, "status": "ROUTING_REQUESTED", "request_id": request_id,
        "target_module": intervention.target_module, "payload": payload,
        "idempotency_key": hashlib.sha256(f"{request_id}:{intervention.target_module}".encode()).hexdigest(),
    }


def learn_intervention_preferences(
    review: EffectReview,
    *,
    intervention_type: str,
    learning_enabled: bool,
) -> list[dict[str, Any]]:
    if not learning_enabled:
        return []
    updates: list[dict[str, Any]] = []
    if review.user_reported_burden in {"HIGH", "TOO_HIGH"}:
        updates.append({"preference_type": "MAXIMUM_ACTION_DURATION", "preference_value": {"adjustment": "REDUCE"}, "source": "USER_REPORTED_EFFECT", "confidence": None})
    if review.user_reported_helpfulness == "NOT_HELPFUL":
        updates.append({"preference_type": "DEPRIORITIZE_INTERVENTION_TYPE", "preference_value": {"intervention_type": intervention_type}, "source": "USER_REPORTED_EFFECT", "confidence": None})
    elif review.user_reported_helpfulness in {"HELPFUL", "VERY_HELPFUL"}:
        updates.append({"preference_type": "USER_REPORTED_HELPFUL_TYPE", "preference_value": {"intervention_type": intervention_type}, "source": "USER_REPORTED_EFFECT", "confidence": None})
    return updates


def validate_engagement_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    lowered = json.dumps(proposal, ensure_ascii=False, default=str).lower()
    blocked = any(term in lowered for term in (
        "streak", "leaderboard", "spiritual_score", "completion_rate", "属灵积分", "成长等级",
        "连续完成", "教会排名", "顺服程度", "用户比较", "提高属灵等级",
    ))
    return {"valid": not blocked, "blocked_reason": "ANTI_GAMIFICATION" if blocked else None, "dependency_optimization": False}


def sanitize_notification_content(_: str | None = None) -> str:
    return "你的属灵星球中有一项可选回顾。"


def reminder_allowed(
    *,
    now: datetime,
    timezone_name: str,
    quiet_hours_start: str | None,
    quiet_hours_end: str | None,
    reminder_enabled: bool,
    consecutive_skips: int = 0,
    burden_reported_high: bool = False,
    paused: bool = False,
) -> dict[str, Any]:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timezone-aware datetime required")
    try:
        local = now.astimezone(ZoneInfo(timezone_name))
    except ZoneInfoNotFoundError as exc:
        raise ValueError("valid IANA timezone required") from exc
    if not reminder_enabled or paused:
        return {"allowed": False, "reason": "DISABLED_OR_PAUSED"}
    if consecutive_skips >= 2 or burden_reported_high:
        return {"allowed": False, "reason": "FREQUENCY_THROTTLED"}
    if quiet_hours_start and quiet_hours_end:
        start = time.fromisoformat(quiet_hours_start)
        end = time.fromisoformat(quiet_hours_end)
        current = local.timetz().replace(tzinfo=None)
        inside = start <= current < end if start < end else (current >= start or current < end)
        if inside:
            return {"allowed": False, "reason": "QUIET_HOURS"}
    return {"allowed": True, "reason": None}


def reflection_data_quality(
    mirrors: Iterable[dict[str, Any]],
    proposals: Iterable[dict[str, Any]],
    *,
    safety_level: str = "NONE",
    effect_tracking_enabled: bool = True,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for item in mirrors:
        mirror_id = str(item.get("id") or item.get("mirror_id") or "unknown")
        if not item.get("source_references") and not item.get("source_references_json"):
            findings.append({"severity": "HIGH", "code": "MIRROR_MISSING_SOURCE", "record_id": mirror_id})
        if item.get("uses_rejected_pattern") or item.get("uses_outdated_pattern"):
            findings.append({"severity": "HIGH", "code": "INVALID_PATTERN_REFERENCE", "record_id": mirror_id})
    for item in proposals:
        proposal_id = str(item.get("id") or item.get("intervention_id") or "unknown")
        if not item.get("estimated_duration_minutes") and item.get("intervention_type") != "NO_ACTION":
            findings.append({"severity": "HIGH", "code": "MISSING_DURATION", "record_id": proposal_id})
        if not item.get("target_module"):
            findings.append({"severity": "HIGH", "code": "MISSING_TARGET", "record_id": proposal_id})
        if item.get("routed") and not item.get("user_confirmed"):
            findings.append({"severity": "HIGH", "code": "UNCONFIRMED_ROUTE", "record_id": proposal_id})
        if contains_prohibited_key(item.get("routing_payload") or item.get("routing_payload_json") or {}):
            findings.append({"severity": "HIGH", "code": "SENSITIVE_ROUTING_PAYLOAD", "record_id": proposal_id})
    if safety_level.upper() in CRISIS_LEVELS and any(item.get("target_module") != "CRISIS_CARE" for item in proposals):
        findings.append({"severity": "HIGH", "code": "CRISIS_ORDINARY_PROPOSAL", "record_id": "current-user"})
    if not effect_tracking_enabled and any(item.get("effect_review_created") for item in proposals):
        findings.append({"severity": "HIGH", "code": "EFFECT_REVIEW_WITHOUT_CONSENT", "record_id": "current-user"})
    high = sum(item["severity"] == "HIGH" for item in findings)
    return {"status": "BLOCKED" if high else "PASS", "high_severity_count": high, "findings": findings, "scope": "CURRENT_USER"}


def daily_reflection_workflow(context: ReflectionContext, *, recent_questions: Iterable[dict[str, Any]] = ()) -> ReflectionInterventionState:
    output = generate_daily_mirror(context, recent_questions=recent_questions)
    return {
        "profile": None, "consent": None, "safety_status": context.safety_status,
        "capacity": context.user_capacity.model_dump(), "context": context.model_dump(), "priority_theme": None,
        "mirror": output["mirror"].model_dump() if output.get("mirror") else None,
        "question_candidates": [output["question"].model_dump()] if output.get("question") else [],
        "intervention_candidates": [output["intervention"].model_dump()] if output.get("intervention") else [],
        "selected_question": output["question"].model_dump() if output.get("question") else None,
        "selected_intervention": output["intervention"].model_dump() if output.get("intervention") else None,
        "validation_result": output.get("validation"), "user_decision": None, "routing_result": None,
        "effect_review": None, "errors": [],
    }


CONSUMED_EVENTS = {
    "formation_twin.emotional_snapshot_created", "formation_twin.formation_snapshot_created",
    "formation_twin.long_term_snapshot_created", "formation_twin.pattern_confirmed",
    "formation_twin.pattern_weakened", "formation_twin.pattern_resolved", "formation_twin.pattern_outdated",
    "formation_twin.life_season_created", "formation_twin.life_season_closed", "formation_twin.checkin_created",
    "formation_twin.checkin_updated", "formation_twin.processing_paused", "formation_twin.consent_updated",
    "formation.practice_completed", "formation.practice_skipped", "formation.practice_cancelled",
    "prayer.session_completed", "holy_habit.task_completed", "holy_habit.task_missed",
    "attention.boundary_completed", "crisis.case_routed", "crisis.case_stabilized",
}
PUBLISHED_EVENTS = {
    "formation_twin.reflection_context_created", "formation_twin.daily_mirror_created",
    "formation_twin.daily_mirror_corrected", "formation_twin.daily_mirror_dismissed",
    "formation_twin.weekly_review_created", "formation_twin.weekly_review_completed",
    "formation_twin.weekly_review_skipped", "formation_twin.reflection_question_created",
    "formation_twin.reflection_question_answered", "formation_twin.reflection_question_skipped",
    "formation_twin.intervention_proposed", "formation_twin.intervention_modified",
    "formation_twin.intervention_accepted", "formation_twin.intervention_deferred",
    "formation_twin.intervention_skipped", "formation_twin.intervention_rejected",
    "formation_twin.no_action_selected", "formation_twin.intervention_routed",
    "formation_twin.intervention_started", "formation_twin.intervention_completed",
    "formation_twin.intervention_stopped", "formation_twin.intervention_cancelled",
    "formation_twin.intervention_effect_reviewed", "formation_twin.intervention_preference_updated",
    "formation_twin.reflection_processing_skipped", "formation_twin.intervention_blocked",
    "formation_twin.intervention_routing_failed",
}
SCHEDULED_JOBS = (
    "weekly_reflection_review_due", "effect_review_due", "reflection_data_quality_scan",
    "reflection_source_invalidation_scan", "gentle_reminder_dispatch",
)
