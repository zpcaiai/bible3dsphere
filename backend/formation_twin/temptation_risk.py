"""Formation Twin Batch 7 temptation-cycle and early-protection policy.

This module treats risk as a temporary, explainable context assembled only from
user-confirmed cycles and consented signals.  It does not predict relapse,
diagnose addiction, or turn temptation into a fact that behavior occurred.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, time, timedelta, timezone
from typing import Any, Iterable, Literal, TypedDict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator


ENGINE_VERSION = "formation-twin-risk-engine-1.0"
RULE_VERSION = "temptation-risk-rules-1.0"
ROUTING_SCHEMA_VERSION = "formation-protection-route-1.0"

SENSITIVE_CYCLE_TYPES = {
    "PORNOGRAPHY_SELF_REPORTED", "SUBSTANCE_USE_SELF_REPORTED",
    "ALCOHOL_MISUSE_SELF_REPORTED", "GAMBLING_SELF_REPORTED",
    "SEXUAL_TEMPTATION", "FOOD_COMPULSION_SELF_REPORTED",
}
CRISIS_LEVELS = {"ELEVATED", "IMMINENT"}
ACTIVE_CYCLE_STATUSES = {"ACTIVE", "CONFIRMED_ACTIVE"}
CONFIRMED_REVIEW_STATUSES = {"CONFIRMED", "USER_CONFIRMED"}
WARNING_LEVELS = {
    "NO_WARNING", "AWARENESS", "PROTECTION_SUGGESTED",
    "IMMEDIATE_SUPPORT_SUGGESTED", "CRISIS_HANDOFF",
}
INTERNAL_RISK_BANDS = {
    "NONE", "CONTEXT_PRESENT", "MULTIPLE_CONDITIONS", "STRONG_URGE_SELF_REPORTED",
    "BEHAVIOR_STARTED", "CONTINUATION_RISK", "CRISIS_RELATED",
}
PROTECTION_ACTION_TYPES = {
    "PAUSE_AND_NAME", "LEAVE_ENVIRONMENT", "CHANGE_ROOM", "MOVE_DEVICE",
    "DISABLE_ACCESS", "START_ATTENTION_BOUNDARY", "CALL_SUPPORT_PERSON",
    "MESSAGE_SUPPORT_PERSON", "JOIN_SHARED_SPACE", "DELAY_DECISION",
    "REMOVE_PAYMENT_ACCESS", "REMOVE_SUBSTANCE_ACCESS", "BODY_REGULATION",
    "SHORT_HONEST_PRAYER", "READ_PROTECTION_CARD", "START_SAFETY_PLAN",
    "CONTACT_PROFESSIONAL", "CRISIS_HANDOFF", "NO_ACTION", "USER_DEFINED",
}
FORBIDDEN_PASSIVE_SIGNALS = {
    "RAW_BROWSER_HISTORY", "MESSAGE_CONTENT", "SEARCH_QUERY_CONTENT", "KEYSTROKES",
    "MICROPHONE_STREAM", "CAMERA_STREAM", "PHOTO_ANALYSIS", "PRECISE_LOCATION_STREAM",
    "CONTACT_INTERACTIONS", "PAYMENT_TRANSACTION_CONTENT", "PRIVATE_APP_CONTENT",
}
ALLOWED_PASSIVE_SIGNALS = {
    "USER_DEFINED_HIGH_RISK_WINDOW", "SELF_REPORTED_SLEEP", "ATTENTION_SCREEN_TIME_SUMMARY",
    "BOUNDARY_STATUS", "SELF_REPORTED_ALONE_STATUS", "USER_SELECTED_ENVIRONMENT_TAG",
    "SELF_REPORTED_SUPPORT_AVAILABILITY",
}

PROHIBITED_KEYS = {
    "relapse_probability", "sin_risk_score", "purity_score", "sobriety_rank",
    "obedience_score", "spiritual_risk_score", "salvation_probability", "journal_text",
    "journal_body", "confession_text", "temptation_text", "behavior_text",
    "browser_history", "message_content", "search_query", "keystrokes", "camera_stream",
    "microphone_stream", "precise_location", "crisis_body", "internal_risk_band",
    "third_party_identity", "full_twin", "contact_message_body",
}
PROHIBITED_PHRASES = {
    "你今晚很可能犯罪", "你即将复发", "你又失败了", "缺乏真正的悔改",
    "真正信靠神的人不会", "真正悔改的人不会复发", "你的属灵生命正在堕落",
    "神正在警告你", "否则会惩罚你", "必须立刻联系牧者认罪",
    "就是拒绝顺服", "你是一个成瘾者", "系统发现你正在隐藏罪",
    "提高属灵等级", "开启更多监控才能证明", "进入色情犯罪模式",
    "probability of relapse", "you will relapse", "you are an addict",
    "real repentance means", "spiritual risk score", "obedience score",
}
SENSITIVE_NOTIFICATION_TERMS = {
    "色情", "赌博", "酒精", "复发", "罪", "冲动", "试探", "成瘾",
    "porn", "gambling", "alcohol", "relapse", "temptation", "urge", "sin",
}


class EvidenceReference(BaseModel):
    reference_type: str = Field(min_length=1, max_length=80)
    reference_id: str = Field(min_length=1, max_length=160)
    independence_group: str | None = Field(default=None, max_length=160)


class CycleCondition(BaseModel):
    condition_type: str = Field(min_length=1, max_length=80)
    condition_code: str = Field(min_length=1, max_length=100)
    user_visible_description: str = Field(min_length=1, max_length=240)
    source_kind: str = "USER_REPORTED"
    statement_type: Literal["USER_REPORTED_FACT", "USER_CONFIRMED_INTERPRETATION"] = "USER_REPORTED_FACT"
    occurred_at: datetime
    expires_at: datetime | None = None
    evidence_references: list[EvidenceReference] = Field(default_factory=list, max_length=8)
    user_confirmed: bool = True

    @model_validator(mode="after")
    def validate_condition(self):
        _aware(self.occurred_at)
        if self.expires_at:
            _aware(self.expires_at)
            if self.expires_at <= self.occurred_at:
                raise ValueError("risk condition must expire after occurrence")
        validate_safe_text(self.user_visible_description)
        return self


class TemptationCycle(BaseModel):
    cycle_id: str
    title: str = Field(min_length=1, max_length=160)
    cycle_type: str
    trigger_conditions: list[str] = Field(default_factory=list, max_length=20)
    vulnerability_conditions: list[str] = Field(default_factory=list, max_length=20)
    emotional_conditions: list[str] = Field(default_factory=list, max_length=20)
    environmental_conditions: list[str] = Field(default_factory=list, max_length=20)
    temptation_nodes: list[dict[str, Any]] = Field(default_factory=list, max_length=30)
    choice_points: list[dict[str, Any]] = Field(default_factory=list, max_length=12)
    behavior_path: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    protective_factors: list[str] = Field(default_factory=list, max_length=20)
    interruption_points: list[str] = Field(default_factory=list, max_length=12)
    recovery_paths: list[str] = Field(default_factory=list, max_length=12)
    required_conditions: list[str] = Field(default_factory=list, max_length=20)
    optional_conditions: list[str] = Field(default_factory=list, max_length=20)
    minimum_independent_conditions: int = Field(default=2, ge=1, le=12)
    scope: dict[str, Any] = Field(default_factory=dict)
    lifecycle_status: str = "DRAFT"
    source_kind: str = "USER_BUILT"
    statement_type: str = "USER_CONFIRMED_INTERPRETATION"
    user_review_status: str = "PENDING"
    evidence_references: list[EvidenceReference] = Field(default_factory=list, max_length=20)
    counterevidence_references: list[EvidenceReference] = Field(default_factory=list, max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=12)
    version: int = Field(default=1, ge=1)
    supersedes_cycle_id: str | None = None
    user_confirmed: bool = False

    @model_validator(mode="after")
    def validate_cycle(self):
        validate_safe_text(self.title)
        if self.cycle_type in SENSITIVE_CYCLE_TYPES and not self.user_confirmed:
            raise ValueError("sensitive cycle types require explicit user confirmation")
        if self.lifecycle_status in ACTIVE_CYCLE_STATUSES and not self.user_confirmed:
            raise ValueError("an active cycle must be user confirmed")
        if _contains_prohibited_key(self.model_dump()):
            raise ValueError("cycle contains prohibited scoring or sensitive-body fields")
        for node in self.temptation_nodes + self.behavior_path:
            node_type = str(node.get("node_type", ""))
            if node_type == "TEMPTATION" and node.get("behavior_occurred") is True:
                raise ValueError("temptation cannot be stored as behavior")
        return self


class ActiveProtection(BaseModel):
    protection_type: str
    description: str = Field(min_length=1, max_length=240)
    active: bool = True
    evidence_references: list[EvidenceReference] = Field(default_factory=list, max_length=8)

    @field_validator("description")
    @classmethod
    def safe_description(cls, value: str) -> str:
        validate_safe_text(value)
        return value


class RiskConditionSnapshot(BaseModel):
    snapshot_id: str
    matched_cycle_ids: list[str]
    active_conditions: list[dict[str, Any]]
    active_protective_factors: list[dict[str, Any]]
    missing_protective_factors: list[str]
    unknown_conditions: list[str]
    counterevidence: list[str]
    internal_risk_band: str
    user_visible_warning_level: str
    evidence_quality: str
    explanation: list[str]
    limitations: list[str]
    warning_eligible: bool
    warning_suppression_reasons: list[str]
    engine_version: str = ENGINE_VERSION
    generated_at: datetime

    @model_validator(mode="after")
    def validate_snapshot(self):
        if self.internal_risk_band not in INTERNAL_RISK_BANDS:
            raise ValueError("unknown internal risk band")
        if self.user_visible_warning_level not in WARNING_LEVELS:
            raise ValueError("unknown warning level")
        _aware(self.generated_at)
        return self


class EarlyWarning(BaseModel):
    warning_id: str
    warning_level: str
    title: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=240)
    active_conditions: list[str] = Field(default_factory=list, max_length=6)
    active_protections: list[str] = Field(default_factory=list, max_length=6)
    unknown_conditions: list[str] = Field(default_factory=list, max_length=6)
    counterevidence: list[str] = Field(default_factory=list, max_length=6)
    matched_confirmed_cycles: list[str] = Field(default_factory=list, max_length=6)
    uncertainty_notes: list[str] = Field(default_factory=list, min_length=1, max_length=6)
    proposed_action: dict[str, Any] | None = None
    expires_at: datetime
    sharing_status: Literal["PRIVATE", "USER_INITIATED"] = "PRIVATE"

    @model_validator(mode="after")
    def validate_warning(self):
        if self.warning_level not in WARNING_LEVELS - {"NO_WARNING"}:
            raise ValueError("a warning must use a visible warning level")
        validate_safe_text(self.title)
        validate_safe_text(self.message)
        if re.search(r"\d{1,3}\s*%", self.message):
            raise ValueError("relapse probability is prohibited")
        _aware(self.expires_at)
        return self


class ProtectionAction(BaseModel):
    action_id: str
    action_type: str
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=320)
    target_module: str
    routing_payload: dict[str, Any] = Field(default_factory=dict)
    required_user_confirmation: Literal[True] = True
    high_impact: bool = False
    default_execution_mode: str = "REMINDER_ONLY"
    sensitive_context_included: Literal[False] = False

    @model_validator(mode="after")
    def validate_action(self):
        if self.action_type not in PROTECTION_ACTION_TYPES:
            raise ValueError("unknown protection action")
        validate_safe_text(self.title)
        validate_safe_text(self.description)
        if _contains_prohibited_key(self.routing_payload):
            raise ValueError("routing payload contains prohibited data")
        if self.high_impact and self.default_execution_mode not in {"SOFT_BLOCK", "HARD_BLOCK", "ACCOUNTABILITY_UNLOCK"}:
            raise ValueError("high impact action requires an explicit execution mode")
        return self


class TemptationRiskWorkflowState(TypedDict):
    source_event: dict[str, Any] | None
    profile: dict[str, Any] | None
    consent: dict[str, Any] | None
    safety_status: dict[str, Any] | None
    confirmed_cycles: list[dict[str, Any]]
    current_context: dict[str, Any] | None
    rule_conditions: list[dict[str, Any]]
    model_condition_candidates: list[dict[str, Any]]
    active_protections: list[dict[str, Any]]
    supporting_evidence: list[dict[str, Any]]
    counterevidence: list[dict[str, Any]]
    cycle_matches: list[dict[str, Any]]
    risk_snapshot: dict[str, Any] | None
    warning_decision: dict[str, Any] | None
    warning: dict[str, Any] | None
    protection_action: dict[str, Any] | None
    user_decision: dict[str, Any] | None
    routing_result: dict[str, Any] | None
    recovery_state: dict[str, Any] | None
    errors: list[dict[str, Any]]


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware datetime required")
    return value


def _contains_prohibited_key(value: Any) -> bool:
    if isinstance(value, dict):
        if {str(key).lower() for key in value}.intersection(PROHIBITED_KEYS):
            return True
        return any(_contains_prohibited_key(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_prohibited_key(item) for item in value)
    return False


def validate_safe_text(value: str) -> None:
    lowered = value.lower()
    if any(phrase.lower() in lowered for phrase in PROHIBITED_PHRASES):
        raise ValueError("prediction, shame, diagnosis, surveillance, or theological verdict is prohibited")
    if re.search(r"\d{1,3}\s*%\s*(复发|犯罪|跌倒|relapse|sin)", lowered):
        raise ValueError("numeric relapse probability is prohibited")


def condition_is_current(condition: CycleCondition, now: datetime | None = None) -> bool:
    now = _aware(now or datetime.now(timezone.utc))
    return condition.user_confirmed and condition.occurred_at <= now and (
        condition.expires_at is None or condition.expires_at > now
    )


def _dedupe_conditions(conditions: Iterable[CycleCondition], now: datetime) -> list[CycleCondition]:
    output: list[CycleCondition] = []
    seen: set[str] = set()
    for item in conditions:
        if not condition_is_current(item, now):
            continue
        groups = [ref.independence_group for ref in item.evidence_references if ref.independence_group]
        key = groups[0] if groups else item.condition_code
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def match_risk_context(
    *,
    cycles: Iterable[TemptationCycle],
    conditions: Iterable[CycleCondition],
    active_protections: Iterable[ActiveProtection] = (),
    explicit_urge: bool = False,
    behavior_started: bool = False,
    continuation_risk: bool = False,
    crisis_level: str = "NONE",
    warnings_enabled: bool = True,
    paused: bool = False,
    now: datetime | None = None,
) -> RiskConditionSnapshot:
    now = _aware(now or datetime.now(timezone.utc))
    current = _dedupe_conditions(conditions, now)
    condition_codes = {item.condition_code for item in current}
    protections = [item for item in active_protections if item.active]
    matched_cycles: list[str] = []
    matched_codes: set[str] = set()
    unknown: set[str] = set()
    limitations: list[str] = []

    for cycle in cycles:
        if not cycle.user_confirmed or cycle.lifecycle_status not in ACTIVE_CYCLE_STATUSES:
            continue
        required = cycle.required_conditions or list(dict.fromkeys(
            cycle.trigger_conditions + cycle.vulnerability_conditions
            + cycle.emotional_conditions + cycle.environmental_conditions
        ))
        present = set(required).intersection(condition_codes)
        minimum = max(2, cycle.minimum_independent_conditions)
        if len(present) >= minimum or ((explicit_urge or behavior_started) and bool(present)):
            matched_cycles.append(cycle.cycle_id)
            matched_codes.update(present)
            unknown.update(set(required) - condition_codes)

    protection_descriptions = [item.description for item in protections]
    suppression: list[str] = []
    if crisis_level in CRISIS_LEVELS:
        internal, visible = "CRISIS_RELATED", "CRISIS_HANDOFF"
    elif continuation_risk:
        internal, visible = "CONTINUATION_RISK", "IMMEDIATE_SUPPORT_SUGGESTED"
    elif behavior_started:
        internal, visible = "BEHAVIOR_STARTED", "IMMEDIATE_SUPPORT_SUGGESTED"
    elif explicit_urge:
        internal, visible = "STRONG_URGE_SELF_REPORTED", "IMMEDIATE_SUPPORT_SUGGESTED"
    elif len(matched_codes) >= 2:
        internal, visible = "MULTIPLE_CONDITIONS", "PROTECTION_SUGGESTED"
    elif current:
        internal, visible = "CONTEXT_PRESENT", "AWARENESS"
        limitations.append("目前只有一个普通条件，不能据此判断旧循环正在启动。")
    else:
        internal, visible = "NONE", "NO_WARNING"

    if protections and visible == "PROTECTION_SUGGESTED" and len(protections) >= len(matched_codes):
        visible = "AWARENESS"
        suppression.append("ACTIVE_PROTECTION_REDUCED_WARNING")
    if protections and visible == "AWARENESS":
        visible = "NO_WARNING"
        suppression.append("ACTIVE_PROTECTION_SUPPRESSED_AWARENESS")
    if not warnings_enabled:
        suppression.append("WARNINGS_DISABLED")
    if paused:
        suppression.append("WARNINGS_PAUSED")
    if visible == "NO_WARNING":
        suppression.append("NO_WARNING_THRESHOLD")

    warning_eligible = visible != "NO_WARNING" and not ({"WARNINGS_DISABLED", "WARNINGS_PAUSED"} & set(suppression))
    active = [
        {
            "condition_type": item.condition_type,
            "condition_code": item.condition_code,
            "user_visible_description": item.user_visible_description,
            "statement_type": item.statement_type,
        }
        for item in current if item.condition_code in matched_codes or not matched_cycles
    ]
    counterevidence = protection_descriptions[:6]
    explanation = [item["user_visible_description"] for item in active[:6]]
    if matched_cycles:
        explanation.append("这些条件与一个由你确认的旧循环有限相似。")
    evidence_quality = "USER_EXPLICIT" if explicit_urge or behavior_started else (
        "CONFIRMED_MULTI_SOURCE" if len(active) >= 2 else "LIMITED"
    )
    return RiskConditionSnapshot(
        snapshot_id=str(uuid.uuid4()), matched_cycle_ids=matched_cycles,
        active_conditions=active, active_protective_factors=[item.model_dump(mode="json") for item in protections[:6]],
        missing_protective_factors=[], unknown_conditions=sorted(unknown)[:8],
        counterevidence=counterevidence, internal_risk_band=internal,
        user_visible_warning_level=visible, evidence_quality=evidence_quality,
        explanation=explanation, limitations=limitations + ["风险条件不是命运，也不是行为已经发生的证据。"],
        warning_eligible=warning_eligible, warning_suppression_reasons=suppression,
        generated_at=now,
    )


def _in_quiet_hours(now: datetime, timezone_name: str, start: str, end: str) -> bool:
    try:
        zone = ZoneInfo(timezone_name)
        start_t = time.fromisoformat(start)
        end_t = time.fromisoformat(end)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("invalid quiet hours") from exc
    local = now.astimezone(zone).time().replace(tzinfo=None)
    return start_t <= local < end_t if start_t < end_t else local >= start_t or local < end_t


def apply_warning_policy(
    snapshot: RiskConditionSnapshot,
    *,
    last_warning_at: datetime | None = None,
    cooldown_hours: int | None = None,
    quiet_hours: dict[str, str] | None = None,
    user_requested_help: bool = False,
    false_positive_count: int = 0,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = _aware(now or datetime.now(timezone.utc))
    reasons = list(snapshot.warning_suppression_reasons)
    default_cooldown = 12 if snapshot.user_visible_warning_level == "AWARENESS" else 4
    cooldown = max(0, cooldown_hours if cooldown_hours is not None else default_cooldown)
    if false_positive_count >= 3:
        cooldown = max(cooldown, 24)
        reasons.append("USER_FEEDBACK_RECALIBRATION")
    if last_warning_at:
        _aware(last_warning_at)
        if now < last_warning_at + timedelta(hours=cooldown) and not user_requested_help:
            reasons.append("COOLDOWN_ACTIVE")
    safety_override = snapshot.user_visible_warning_level == "CRISIS_HANDOFF"
    immediate_request = user_requested_help and snapshot.user_visible_warning_level == "IMMEDIATE_SUPPORT_SUGGESTED"
    if quiet_hours and _in_quiet_hours(
        now, quiet_hours.get("timezone", "Asia/Shanghai"),
        quiet_hours.get("start", "22:00"), quiet_hours.get("end", "07:00"),
    ) and not (safety_override or immediate_request):
        reasons.append("QUIET_HOURS")
    allowed = snapshot.warning_eligible and not {
        "WARNINGS_DISABLED", "WARNINGS_PAUSED", "COOLDOWN_ACTIVE", "QUIET_HOURS",
    }.intersection(reasons)
    return {
        "deliver": allowed,
        "warning_level": snapshot.user_visible_warning_level,
        "suppression_reasons": sorted(set(reasons)),
        "cooldown_hours": cooldown,
        "safety_override": safety_override,
        "optimize_click_rate": False,
    }


def generate_warning(snapshot: RiskConditionSnapshot, *, now: datetime | None = None) -> EarlyWarning | None:
    if not snapshot.warning_eligible or snapshot.user_visible_warning_level == "NO_WARNING":
        return None
    now = _aware(now or datetime.now(timezone.utc))
    level = snapshot.user_visible_warning_level
    conditions = [item["user_visible_description"] for item in snapshot.active_conditions[:4]]
    if level == "AWARENESS":
        title = "一个可留意的条件"
        message = "你记录的一个条件曾出现在已确认的旧循环里；目前信息有限，不代表循环正在启动。"
    elif level == "PROTECTION_SUGGESTED":
        title = "可以提前增加一个保护条件"
        message = "几个与过去相似的条件正在同时出现。这不代表旧行为一定会发生；一个小保护动作可能有帮助。"
    elif level == "IMMEDIATE_SUPPORT_SUGGESTED":
        title = "先停止继续，并连接帮助"
        message = "你主动报告现在不容易独自停下来。先离开当前环境或联系一个你已选择的支持对象，不需要先分析原因。"
    else:
        title = "现在先处理安全"
        message = "当前信息涉及安全风险；普通循环分析已暂停，请使用现有危机安全支持。"
    return EarlyWarning(
        warning_id=str(uuid.uuid4()), warning_level=level, title=title, message=message,
        active_conditions=conditions, active_protections=[item.get("description", "") for item in snapshot.active_protective_factors],
        unknown_conditions=snapshot.unknown_conditions, counterevidence=snapshot.counterevidence,
        matched_confirmed_cycles=snapshot.matched_cycle_ids,
        uncertainty_notes=snapshot.limitations[:4] or ["当前信息可能不完整。"],
        expires_at=now + timedelta(hours=4 if level != "AWARENESS" else 12),
    )


ACTION_LIBRARY: dict[str, dict[str, Any]] = {
    "LEAVE_ENVIRONMENT": {"title": "先离开当前环境", "description": "到一个安全、有人或更开放的空间停留十分钟。", "target_module": "ATTENTION_OS"},
    "MOVE_DEVICE": {"title": "把设备移远", "description": "把当前设备放到另一个房间，先保留十分钟距离。", "target_module": "ATTENTION_OS"},
    "DELAY_DECISION": {"title": "延迟十分钟", "description": "先不作最终决定；十分钟后再重新选择。", "target_module": "FORMATION_ENGINE"},
    "MESSAGE_SUPPORT_PERSON": {"title": "准备一条求助消息", "description": "生成一句五分钟陪伴请求草稿；不会自动发送。", "target_module": "ACCOUNTABILITY"},
    "SHORT_HONEST_PRAYER": {"title": "一句诚实祷告", "description": "用一句话诚实表达现在的冲动与求助，同时保留环境和真人支持。", "target_module": "PRAYER_OS"},
    "START_ATTENTION_BOUNDARY": {"title": "开启提醒型边界", "description": "为当前设备建立三十分钟提醒型边界，可随时解除。", "target_module": "ATTENTION_OS"},
    "CONTACT_PROFESSIONAL": {"title": "准备联系专业支持", "description": "记录一个简短求助要点，由你决定是否联系专业人员。", "target_module": "PROFESSIONAL_SUPPORT"},
    "CRISIS_HANDOFF": {"title": "打开安全帮助", "description": "暂停普通分析，连接现有 Crisis Care 安全入口。", "target_module": "CRISIS_CARE"},
    "NO_ACTION": {"title": "现在不增加行动", "description": "只保留这次看见；如果安全状态变化，可以随时请求帮助。", "target_module": "NO_ACTION"},
}


def select_protection_action(
    snapshot: RiskConditionSnapshot,
    *,
    blocked_action_types: Iterable[str] = (),
    human_support_available: bool = False,
) -> ProtectionAction:
    blocked = set(blocked_action_types)
    band = snapshot.internal_risk_band
    if band == "CRISIS_RELATED":
        preferred = ["CRISIS_HANDOFF"]
    elif band in {"BEHAVIOR_STARTED", "CONTINUATION_RISK"}:
        preferred = ["LEAVE_ENVIRONMENT", "MESSAGE_SUPPORT_PERSON", "START_ATTENTION_BOUNDARY"]
    elif band == "STRONG_URGE_SELF_REPORTED":
        preferred = (["MESSAGE_SUPPORT_PERSON"] if human_support_available else []) + ["LEAVE_ENVIRONMENT", "DELAY_DECISION"]
    elif band == "MULTIPLE_CONDITIONS":
        preferred = ["MOVE_DEVICE", "DELAY_DECISION", "START_ATTENTION_BOUNDARY"]
    elif band == "CONTEXT_PRESENT":
        preferred = ["DELAY_DECISION", "NO_ACTION"]
    else:
        preferred = ["NO_ACTION"]
    action_type = next((item for item in preferred if item not in blocked), "NO_ACTION")
    template = ACTION_LIBRARY[action_type]
    return ProtectionAction(
        action_id=str(uuid.uuid4()), action_type=action_type, title=template["title"],
        description=template["description"], target_module=template["target_module"],
        routing_payload={
            "request_id": str(uuid.uuid4()), "action_type": action_type,
            "execution_mode": "REMINDER_ONLY", "start_now": True,
            "sensitive_reason_included": False, "user_confirmed": False,
        },
    )


def make_protection_action_smaller(action: ProtectionAction) -> ProtectionAction:
    mapping = {
        "LEAVE_ENVIRONMENT": ("CHANGE_ROOM", "先换一个空间", "先走到门口或换到更开放的房间。"),
        "MOVE_DEVICE": ("MOVE_DEVICE", "先把设备放远一点", "把设备放到伸手拿不到的位置五分钟。"),
        "MESSAGE_SUPPORT_PERSON": ("MESSAGE_SUPPORT_PERSON", "先准备一句话", "只写下：‘现在可以陪我说五分钟吗？’；不自动发送。"),
        "START_ATTENTION_BOUNDARY": ("DELAY_DECISION", "先延迟五分钟", "五分钟内先不继续，之后再选择。"),
        "DELAY_DECISION": ("PAUSE_AND_NAME", "先暂停一分钟", "暂停一分钟，只说出当前最强的一个感受。"),
    }
    action_type, title, description = mapping.get(action.action_type, ("NO_ACTION", "现在不增加行动", ACTION_LIBRARY["NO_ACTION"]["description"]))
    return ProtectionAction(
        action_id=str(uuid.uuid4()), action_type=action_type, title=title, description=description,
        target_module="FORMATION_ENGINE" if action_type == "PAUSE_AND_NAME" else action.target_module,
        routing_payload={
            "request_id": str(uuid.uuid4()), "action_type": action_type,
            "execution_mode": "REMINDER_ONLY", "start_now": True,
            "sensitive_reason_included": False, "user_confirmed": False,
        },
    )


def build_protection_route(action: ProtectionAction, *, user_confirmed: bool, request_id: str | None = None) -> dict[str, Any]:
    if not user_confirmed:
        raise ValueError("protection actions require current user confirmation")
    if action.high_impact and not action.routing_payload.get("recovery_method_visible"):
        raise ValueError("high-impact boundary requires a visible recovery method")
    request_id = request_id or str(uuid.uuid4())
    payload = {
        "request_id": request_id,
        "action_id": action.action_id,
        "action_type": action.action_type,
        "target_module": action.target_module,
        "execution_mode": action.default_execution_mode,
        "sensitive_reason_included": False,
        "user_confirmed": True,
        "routing_schema_version": ROUTING_SCHEMA_VERSION,
    }
    if _contains_prohibited_key(payload):
        raise ValueError("unsafe protection routing payload")
    payload["idempotency_key"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return payload


def validate_model_candidates(result: dict[str, Any], *, consent: bool, allowed_cycle_ids: Iterable[str]) -> dict[str, Any]:
    if not consent:
        return {"accepted": [], "rejected": ["MODEL_ASSISTANCE_NOT_CONSENTED"], "can_trigger_warning": False}
    if result.get("relapse_prediction_attempted") or result.get("moral_judgment_attempted") or result.get("diagnosis_attempted"):
        return {"accepted": [], "rejected": ["PROHIBITED_MODEL_OUTPUT"], "can_trigger_warning": False}
    if _contains_prohibited_key(result):
        return {"accepted": [], "rejected": ["PROHIBITED_MODEL_FIELD"], "can_trigger_warning": False}
    allowed = set(allowed_cycle_ids)
    accepted = []
    for item in result.get("possible_cycle_matches", []):
        if item.get("cycle_id") in allowed and item.get("user_confirmation_required") is True:
            accepted.append(item)
    return {"accepted": accepted, "rejected": [], "can_trigger_warning": False, "user_confirmation_required": True}


def validate_passive_signal(signal_type: str, *, consent: bool, raw_content_uploaded: bool = False) -> dict[str, Any]:
    if signal_type in FORBIDDEN_PASSIVE_SIGNALS or raw_content_uploaded:
        return {"accepted": False, "reason": "CONTENT_LEVEL_MONITORING_PROHIBITED"}
    if not consent:
        return {"accepted": False, "reason": "PASSIVE_METADATA_CONSENT_REQUIRED"}
    if signal_type not in ALLOWED_PASSIVE_SIGNALS:
        return {"accepted": False, "reason": "SIGNAL_NOT_ALLOWLISTED"}
    return {"accepted": True, "local_processing_preferred": True, "raw_content_uploaded": False}


def sanitize_notification_content(content: str | None = None) -> str:
    generic = "你有一项可选的保护提醒。"
    if not content:
        return generic
    lowered = content.lower()
    return generic if any(term.lower() in lowered for term in SENSITIVE_NOTIFICATION_TERMS) else content


def start_recovery(*, crisis_level: str = "NONE", behavior_stopped: bool | None = None) -> dict[str, Any]:
    if crisis_level in CRISIS_LEVELS:
        return {
            "status": "CRISIS_HANDOFF", "first_step": "IMMEDIATE_SAFETY",
            "questions": ["你现在安全吗？"], "deep_analysis_allowed": False,
            "target_module": "CRISIS_CARE",
        }
    questions = ["你现在安全吗？"]
    if behavior_stopped is None:
        questions.append("旧行为现在已经停止了吗？")
    questions.append("你现在是否需要一个真人陪伴？")
    return {
        "status": "SAFETY_CHECK_REQUIRED", "first_step": "IMMEDIATE_SAFETY",
        "questions": questions, "deep_analysis_allowed": False,
        "available_actions": ["STOP_CONTINUATION", "LEAVE_ENVIRONMENT", "CONTACT_SUPPORT", "NO_FURTHER_ANALYSIS_TODAY"],
        "user_failure_label": False,
    }


def learn_warning_feedback(feedback: Iterable[str], current_cooldown_hours: int = 4) -> dict[str, Any]:
    values = list(feedback)
    false_positives = sum(item in {"INACCURATE", "TOO_FREQUENT", "TOO_INTRUSIVE"} for item in values)
    return {
        "false_positive_count": false_positives,
        "cooldown_hours": max(current_cooldown_hours, 24) if false_positives >= 3 else current_cooldown_hours,
        "request_recalibration": false_positives >= 3,
        "passive_metadata_should_pause": false_positives >= 3,
        "stronger_language": False,
        "crisis_threshold_changed": False,
    }


def risk_data_quality(
    cycles: Iterable[dict[str, Any]], warnings: Iterable[dict[str, Any]],
    support_requests: Iterable[dict[str, Any]], recoveries: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for item in cycles:
        if item.get("cycle_type") in SENSITIVE_CYCLE_TYPES and not item.get("user_confirmed"):
            findings.append({"severity": "HIGH", "code": "UNCONFIRMED_SENSITIVE_CYCLE", "record_id": str(item.get("id", ""))})
        if item.get("lifecycle_status") in ACTIVE_CYCLE_STATUSES and item.get("user_review_status") not in CONFIRMED_REVIEW_STATUSES:
            findings.append({"severity": "HIGH", "code": "ACTIVE_UNCONFIRMED_CYCLE", "record_id": str(item.get("id", ""))})
    for item in warnings:
        active = item.get("active_condition_summaries_json") or item.get("active_conditions") or []
        if item.get("warning_level") in {"PROTECTION_SUGGESTED", "IMMEDIATE_SUPPORT_SUGGESTED"} and len(active) < 2 and not item.get("explicit_user_help"):
            findings.append({"severity": "HIGH", "code": "HIGH_WARNING_WITH_SINGLE_CONDITION", "record_id": str(item.get("id", ""))})
        if not (item.get("uncertainty_notes_json") or item.get("uncertainty_notes")):
            findings.append({"severity": "HIGH", "code": "WARNING_MISSING_UNCERTAINTY", "record_id": str(item.get("id", ""))})
    for item in support_requests:
        if item.get("delivery_status") == "SENT" and not item.get("user_confirmed"):
            findings.append({"severity": "HIGH", "code": "UNCONFIRMED_SUPPORT_SHARE", "record_id": str(item.get("id", ""))})
    for item in recoveries:
        if item.get("first_step") not in {None, "IMMEDIATE_SAFETY"}:
            findings.append({"severity": "HIGH", "code": "RECOVERY_DID_NOT_START_WITH_SAFETY", "record_id": str(item.get("id", ""))})
    high = sum(item["severity"] == "HIGH" for item in findings)
    return {"status": "FAIL_CLOSED" if high else "PASS", "high_severity_count": high, "findings": findings}


CONSUMED_EVENTS = (
    "formation_twin.life_event_accepted", "formation_twin.life_event_deleted",
    "formation_twin.life_event_excluded", "formation_twin.emotional_snapshot_created",
    "formation_twin.emotion_observation_created", "formation_twin.formation_chain_confirmed",
    "formation_twin.temptation_observation_created", "formation_twin.pattern_confirmed",
    "formation_twin.pattern_weakened", "formation_twin.pattern_outdated",
    "formation_twin.life_season_created", "formation_twin.life_season_closed",
    "formation_twin.intervention_completed", "formation_twin.intervention_effect_reviewed",
    "attention.daily_summary_created", "attention.boundary_started", "attention.boundary_completed",
    "attention.boundary_disabled", "holy_habit.task_completed", "prayer.session_completed",
    "crisis.case_routed", "crisis.case_stabilized",
)
PUBLISHED_EVENTS = (
    "formation_twin.temptation_cycle_created", "formation_twin.temptation_cycle_confirmed",
    "formation_twin.temptation_cycle_updated", "formation_twin.temptation_cycle_paused",
    "formation_twin.temptation_cycle_outdated", "formation_twin.risk_condition_activated",
    "formation_twin.risk_condition_expired", "formation_twin.risk_snapshot_created",
    "formation_twin.early_warning_created", "formation_twin.early_warning_suppressed",
    "formation_twin.early_warning_delivered", "formation_twin.early_warning_acknowledged",
    "formation_twin.early_warning_marked_inaccurate", "formation_twin.early_warning_snoozed",
    "formation_twin.protection_action_proposed", "formation_twin.protection_action_accepted",
    "formation_twin.protection_action_routed", "formation_twin.protection_action_completed",
    "formation_twin.protection_action_stopped", "formation_twin.protection_plan_created",
    "formation_twin.protection_plan_updated", "formation_twin.protection_plan_activated",
    "formation_twin.protection_plan_paused", "formation_twin.protection_plan_rehearsed",
    "formation_twin.support_request_drafted", "formation_twin.support_request_confirmed",
    "formation_twin.support_request_sent", "formation_twin.support_request_cancelled",
    "formation_twin.recovery_started", "formation_twin.recovery_safety_checked",
    "formation_twin.recovery_action_selected", "formation_twin.recovery_stabilized",
    "formation_twin.recovery_review_completed", "formation_twin.recovery_review_skipped",
    "formation_twin.risk_processing_skipped", "formation_twin.warning_blocked",
    "formation_twin.warning_delivery_failed", "formation_twin.crisis_handoff_requested",
    "formation_twin.protection_data_erased",
)
WORKFLOW_NODES = {
    "risk_monitoring": (
        "risk_relevant_event_received", "load_profile_and_consent", "validate_cycle_eligibility",
        "load_crisis_status", "run_crisis_gateway", "load_confirmed_cycles",
        "assemble_current_risk_context", "extract_rule_conditions", "decide_model_condition_extraction",
        "validate_model_candidates", "load_active_protective_factors", "build_support_and_counterevidence",
        "match_cycle_conditions", "calculate_internal_risk_band", "apply_warning_policy",
        "check_cooldown_and_quiet_hours", "generate_explainable_warning",
        "generate_one_protection_action", "validate_warning_and_action", "persist_risk_snapshot",
        "deliver_or_suppress_warning",
    ),
    "user_decision": (
        "warning_opened", "present_conditions_and_uncertainty", "present_one_action",
        "wait_for_user_choice", "execute_environment_or_support_route",
        "update_active_protection", "invite_minimal_status_update",
    ),
    "recovery": (
        "user_reports_relapse_or_behavior_started", "immediate_safety_check",
        "crisis_or_ordinary_recovery", "check_behavior_stopped", "reduce_continuation_access",
        "offer_human_connection", "offer_one_recovery_action", "suppress_deep_analysis",
        "schedule_optional_later_review", "update_cycle_after_user_stabilizes",
    ),
}
