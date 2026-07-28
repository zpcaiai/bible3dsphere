"""EMD-OS Batch 3: real-life events, recovery metrics and longitudinal verification.

Batch 2 只能证明「用户会怎么说」；Batch 3 处理「现实中实际发生了什么」：

    真实事件采集 EM-20
    → 触发-反应-恢复时间线 EM-21
    → 四种恢复指标 EM-22
    → 关系修复验证 EM-23
    → 训练迁移与提示依赖 EM-24
    → 复发与情境泛化 EM-25
    → 14/30/90 检查点调度 EM-26
    → 纵向成长评估 EM-27

不可动摇的原则（由代码强制）：

* 评估事件，不定义人格：输出「最近三次家庭冲突里你通常……」，而不是「你是回避型的人」。
* 四种恢复必须分开：行为、功能、情绪、关系。快速「不难过」不等于成熟，持续有情绪也不等于不成熟。
* 只评估用户可负责的部分；对方拒绝原谅、拒绝回应或关系结束，都不判定用户修复失败。
* 家暴、性暴力、跟踪威胁、强制控制、宗教权威滥用等情境不进入普通修复流程；安全退出就是成熟行为。
* 永远不要求用户为了完成评估去制造一次冲突。
* 变化只与用户自己的历史比较，且必须列出其他可能解释，不作因果断言。
"""
from __future__ import annotations

import hashlib
import json
import statistics
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .emotional_maturity import (
    DIMENSION_BY_CODE,
    EVIDENCE_CONTEXTS,
    STAGE_RANK,
    EvidenceItem,
    UnsafeContentError,
    validate_safe_text,
)
from .emotional_maturity_items import SCENARIO_CONTEXT_TO_EVIDENCE_CONTEXT


ENGINE_VERSION = "emd-event-engine-1.0"
RULE_VERSION = "emd-longitudinal-rules-1.0"

EVENT_STAGES: tuple[tuple[str, str], ...] = (
    ("T_MINUS_1", "事件前状态：睡眠、疲劳、压力、身体状况、已有关系张力"),
    ("T0", "触发事件：客观发生了什么"),
    ("T1", "即时解释：当时如何理解对方、自己和局势"),
    ("T2", "情绪与身体激活"),
    ("T3", "第一反应：最先说了什么、做了什么或没有做什么"),
    ("T4", "调节尝试：暂停、呼吸、祷告、离开现场、求助、写草稿"),
    ("T5", "第二选择：调节后实际采取了什么不同的行动"),
    ("T6", "关系处理：澄清、边界、道歉、补偿、修复或安全退出"),
    ("T7", "恢复：行为、功能、情绪、关系分别何时恢复"),
    ("T8", "学习与下次计划"),
)
EVENT_STAGE_CODES: tuple[str, ...] = tuple(code for code, _ in EVENT_STAGES)

EVENT_CONTEXTS: tuple[str, ...] = (
    "family", "partner", "friend", "workplace", "church_service", "solitude", "other",
)

# 真实行为证据等级
REAL_EVIDENCE_LEVELS: dict[str, str] = {
    "RL0": "无具体行为证据，只有抽象表达",
    "RL1": "回顾性事件，时间与细节有限",
    "RL2": "事件后 24 小时内记录了触发、反应和行动",
    "RL3": "48–72 小时后再次确认实际做了什么",
    "RL4": "确认完成了具体沟通、补偿、边界或行为改变",
    "RL5": "多次事件、多个场景中观察到相似成熟行为",
}
REAL_EVIDENCE_ORDER: tuple[str, ...] = ("RL0", "RL1", "RL2", "RL3", "RL4", "RL5")

UNSAFE_RELATIONSHIP_FLAGS: frozenset[str] = frozenset({
    "DOMESTIC_VIOLENCE", "SEXUAL_VIOLENCE", "STALKING_OR_THREAT", "COERCIVE_CONTROL",
    "SPIRITUAL_AUTHORITY_ABUSE", "SEVERE_RETALIATION_RISK", "CHILD_OR_VULNERABLE_HARM",
})

RECOVERY_KINDS: tuple[str, ...] = (
    "behavioral_control_recovery", "functional_recovery", "emotional_recovery", "relationship_recovery",
)
RECOVERY_BUCKETS: tuple[tuple[str, float], ...] = (
    ("IMMEDIATE", 5 * 60),
    ("MINUTES", 60 * 60),
    ("HOURS", 24 * 3600),
    ("DAYS", 7 * 24 * 3600),
    ("WEEKS", float("inf")),
)
RESOLUTION_STATUSES: tuple[str, ...] = (
    "not_needed", "unsafe_to_attempt", "attempted", "partially_resolved",
    "resolved", "boundary_exit", "unresolved",
)

REPAIR_STAGES: tuple[str, ...] = ("R0", "R1", "R2", "R3", "R4", "R5")
REPAIR_STAGE_RANK: dict[str, int] = {stage: index for index, stage in enumerate(REPAIR_STAGES)}
REPAIR_STAGE_LABELS: dict[str, str] = {
    "R0": "不适用或不安全接触",
    "R1": "意识到自己的行为对对方的影响",
    "R2": "启动修复：澄清、提出见面或承认需要谈",
    "R3": "承担自己的具体部分，没有夹带反击，也没有自我羞辱",
    "R4": "提出可执行补救、纠正与边界",
    "R5": "持续改变：后续相似事件中行为确实不同",
}
REPAIR_QUALITY_ELEMENTS: tuple[str, ...] = (
    "specificity", "ownership", "impact_acknowledgment", "no_counterattack",
    "concrete_repair", "boundary_integrity", "follow_through", "respect_for_other_choice",
)

TRANSFER_STAGES: tuple[str, ...] = ("T0", "T1", "T2", "T3", "T4", "T5", "T6")
TRANSFER_STAGE_RANK: dict[str, int] = {stage: index for index, stage in enumerate(TRANSFER_STAGES)}
TRANSFER_STAGE_LABELS: dict[str, str] = {
    "T0": "只理解原则，尚无现实应用",
    "T1": "在完整脚本引导下完成一次行动",
    "T2": "只需提示技能名称或步骤即可自行组织行动",
    "T3": "没有实时提示，在相似场景中自主使用",
    "T4": "跨到另一种生活场景",
    "T5": "在疲劳、公开批评或权力差下仍能使用",
    "T6": "30/90 天后仍稳定，且不再依赖系统提醒",
}
PROMPT_DEPENDENCE: tuple[str, ...] = ("P4", "P3", "P2", "P1", "P0")
PROMPT_DEPENDENCE_LABELS: dict[str, str] = {
    "P4": "需要逐字话术", "P3": "需要分步指导", "P2": "只需简短提醒",
    "P1": "自己想起并使用", "P0": "自动整合，事后才意识到用了训练",
}
TRANSFER_TYPES: tuple[str, ...] = (
    "near_transfer", "context_transfer", "pressure_transfer", "combined_transfer", "maintenance_transfer",
)

KNOWN_CYCLES: dict[str, str] = {
    "boundary_guilt_cycle": "越界 → 顺从 → 怨恨 → 爆发 → 内疚 → 再次顺从",
    "rejection_panic_cycle": "延迟回应 → 推测被抛弃 → 连续追问 → 对方退缩 → 更加恐慌",
    "perfectionism_collapse_cycle": "高标准 → 过度工作 → 小错误 → 自我攻击 → 放弃或耗竭",
    "conflict_avoidance_cycle": "受伤 → 沉默 → 假装没事 → 怨恨积累 → 突然断联",
    "spiritual_bypassing_cycle": "痛苦 → 用属灵口号压抑 → 不处理现实问题 → 痛苦重复",
    "control_failure_cycle": "试图控制所有结果 → 现实失控 → 灾难化 → 过度自责",
}

CHECKPOINT_DAYS: tuple[int, ...] = (14, 30, 90)
CHECKPOINT_WINDOWS: dict[int, int] = {14: 3, 30: 5, 90: 7}
CHECKPOINT_GOALS: dict[int, str] = {
    14: "技能获得与第一次现实应用",
    30: "初步稳定与旧循环被打断",
    90: "维持、跨场景泛化与整合",
}
CHECKPOINT_EVIDENCE: dict[int, tuple[str, ...]] = {
    14: ("1–2 个现实事件", "一次行为实验", "一次技能使用复盘", "提示依赖程度", "主观负担"),
    30: ("至少 3 个可比较现实事件", "至少一次后续修复验证", "至少一个与基线相似的事件", "至少一个不同情境的事件"),
    90: ("多个现实事件", "至少两种生活情境", "压力变化证据", "复发与恢复证据", "至少一次长期修复验证"),
}

ALTERNATIVE_EXPLANATIONS: tuple[str, ...] = (
    "这段时间的触发机会本身变多或变少",
    "睡眠、身体状况或工作强度发生变化",
    "环境或关系对象发生变化",
    "记录方式或记录意愿发生变化",
    "对方的反应不同",
)

MIN_EVENTS_FOR_COMPARISON = 2
MIN_EVENTS_FOR_PATTERN = 3


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware datetime required")
    return value


def _now(now: datetime | None = None) -> datetime:
    return _aware(now) if now else datetime.now(timezone.utc)


def _hash(payload: dict[str, Any]) -> str:
    serializable = json.loads(json.dumps(payload, default=str))
    return hashlib.sha256(json.dumps(serializable, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def bucket_for(seconds: float | None) -> str:
    if seconds is None:
        return "UNKNOWN"
    for label, ceiling in RECOVERY_BUCKETS:
        if seconds < ceiling:
            return label
    return "WEEKS"


# ─────────────────────────────────────────────────────────────────────────────
# EM-20 real_life_emotional_event_capture
# ─────────────────────────────────────────────────────────────────────────────

class EmotionalEventInput(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    growth_plan_id: str | None = None
    occurred_at: datetime
    captured_at: datetime
    context: str = "other"
    objective_facts: list[str] = Field(default_factory=list, max_length=12)
    user_interpretations: list[str] = Field(default_factory=list, max_length=12)
    emotions: list[dict[str, Any]] = Field(default_factory=list, max_length=12)
    body_signals: list[str] = Field(default_factory=list, max_length=12)
    first_response: str | None = Field(default=None, max_length=240)
    regulation_attempts: list[str] = Field(default_factory=list, max_length=10)
    later_response: str | None = Field(default=None, max_length=240)
    relationship_outcome: str | None = None
    safety_flags: list[str] = Field(default_factory=list, max_length=8)
    urge_only_actions: list[str] = Field(default_factory=list, max_length=8)
    harmful_actions: list[str] = Field(default_factory=list, max_length=8)
    related_dimensions: list[str] = Field(default_factory=list, max_length=5)
    third_party_labels: list[str] = Field(default_factory=list, max_length=6)
    user_requested_private_mode: bool = True

    @field_validator("context")
    @classmethod
    def known_context(cls, value: str) -> str:
        if value not in EVENT_CONTEXTS:
            raise ValueError(f"unknown event context: {value}")
        return value

    @field_validator("related_dimensions")
    @classmethod
    def known_dimensions(cls, value: list[str]) -> list[str]:
        unknown = [code for code in value if code not in DIMENSION_BY_CODE]
        if unknown:
            raise ValueError(f"unknown dimension: {','.join(unknown)}")
        return value

    @field_validator("relationship_outcome")
    @classmethod
    def known_outcome(cls, value: str | None) -> str | None:
        if value is not None and value not in RESOLUTION_STATUSES:
            raise ValueError(f"unknown relationship outcome: {value}")
        return value

    @model_validator(mode="after")
    def validate_event(self):
        _aware(self.occurred_at)
        _aware(self.captured_at)
        if self.captured_at < self.occurred_at:
            raise ValueError("event cannot be captured before it occurred")
        for text in [*self.objective_facts, *self.user_interpretations, self.first_response or "", self.later_response or ""]:
            if text:
                validate_safe_text(text)
        return self

    @property
    def evidence_context(self) -> str:
        return SCENARIO_CONTEXT_TO_EVIDENCE_CONTEXT.get(self.context, "OTHER")


_THIRD_PARTY_MINIMIZED = "对方"


def capture_event(
    event: EmotionalEventInput,
    *,
    consented_scopes: list[str],
    safety_level: str = "NONE",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Capture a real event: consent + safety first, third parties minimised, facts kept apart."""
    moment = _now(now)
    if "EMD_BEHAVIOR_EVIDENCE" not in consented_scopes:
        return {
            "event_id": event.event_id,
            "status": "BLOCKED_NO_CONSENT",
            "next_action": "OFFER_BEHAVIOR_EVIDENCE_CONSENT",
            "captured_at": moment,
        }
    unsafe = sorted(set(event.safety_flags) & UNSAFE_RELATIONSHIP_FLAGS)
    if safety_level in {"ELEVATED", "IMMINENT"} or unsafe:
        return {
            "event_id": event.event_id,
            "status": "ROUTED_TO_SAFETY",
            "unsafe_flags": unsafe,
            "repair_workflow_allowed": False,
            "note": "安全退出、停止联系或寻求保护，在这种情境中就是成熟行为。",
            "next_action": "ROUTE_TO_CRISIS_CARE",
            "captured_at": moment,
        }

    hours_since = (moment - event.occurred_at).total_seconds() / 3600
    if hours_since <= 24:
        level = "RL2"
    elif hours_since <= 72:
        level = "RL3" if event.later_response else "RL1"
    else:
        level = "RL1"
    if not (event.first_response or event.later_response or event.regulation_attempts):
        level = "RL0"

    dimensions = list(event.related_dimensions)
    if not dimensions:
        inferred = []
        if event.regulation_attempts or event.harmful_actions:
            inferred.append("D2")
        if event.relationship_outcome in {"attempted", "partially_resolved", "resolved"}:
            inferred.append("D9")
        if event.context in {"family", "partner"} and not inferred:
            inferred.append("D6")
        dimensions = inferred or ["D2"]

    payload = {
        "event_id": event.event_id,
        "status": "CAPTURED",
        "evidence_level": level,
        "evidence_level_label": REAL_EVIDENCE_LEVELS[level],
        "context": event.context,
        "evidence_context": event.evidence_context,
        "related_dimensions": dimensions,
        "fact_interpretation_separated": bool(event.objective_facts) and bool(event.user_interpretations),
        "objective_fact_count": len(event.objective_facts),
        "interpretation_count": len(event.user_interpretations),
        "third_party_minimised": True,
        "third_party_labels": [_THIRD_PARTY_MINIMIZED for _ in event.third_party_labels],
        "urge_recorded_without_action": bool(event.urge_only_actions) and not event.harmful_actions,
        "private_mode": event.user_requested_private_mode,
        "limitations": [
            "这是一次事件记录，不是对你这个人的判断。",
            "系统不记录第三方姓名，也不评估对方。",
        ],
        "next_action": "BUILD_EVENT_TIMELINE",
        "captured_at": moment,
        "engine_version": ENGINE_VERSION,
    }
    payload["input_hash"] = _hash(payload)
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# EM-21 trigger_response_recovery_timeline_builder
# ─────────────────────────────────────────────────────────────────────────────

def build_timeline(
    event: EmotionalEventInput,
    *,
    stage_times: dict[str, datetime] | None = None,
    pre_event_factors: list[str] | None = None,
) -> dict[str, Any]:
    """Build T-1..T8. Missing nodes stay `unknown`; the engine never fills in a guess."""
    times = {code: _aware(value) for code, value in (stage_times or {}).items()}
    unknown_codes = [code for code in EVENT_STAGE_CODES if code not in times and code != "T_MINUS_1"]

    nodes: list[dict[str, Any]] = []
    for code, description in EVENT_STAGES:
        occurred = times.get(code)
        content: Any = None
        if code == "T_MINUS_1":
            content = list(pre_event_factors or [])
        elif code == "T0":
            content = event.objective_facts
        elif code == "T1":
            content = event.user_interpretations
        elif code == "T2":
            content = {"emotions": event.emotions, "body_signals": event.body_signals}
        elif code == "T3":
            content = event.first_response
        elif code == "T4":
            content = event.regulation_attempts
        elif code == "T5":
            content = event.later_response
        elif code == "T6":
            content = event.relationship_outcome
        nodes.append({
            "stage": code,
            "description": description,
            "occurred_at": occurred,
            "content": content if content not in ([], {}, "") else None,
            "status": "RECORDED" if (occurred or content) else "UNKNOWN",
        })

    turning_point = None
    if event.regulation_attempts and event.later_response:
        turning_point = {
            "between": ["T3", "T5"],
            "regulation_attempt": event.regulation_attempts[0],
            "observation": "调节尝试之后，行动发生了变化。",
            "causal_claim": False,
        }

    return {
        "timeline_id": f"tml_{uuid.uuid4().hex[:12]}",
        "event_id": event.event_id,
        "nodes": nodes,
        "unknown_nodes": unknown_codes,
        "pre_event_vulnerability": list(pre_event_factors or []),
        "turning_point": turning_point,
        "notes": [
            "空白节点保持为未知，系统不会替你补全记忆。",
            "转折点只是观察，不代表因果证明。",
        ],
        "next_action": "COMPUTE_RECOVERY_METRICS",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-22 recovery_and_regulation_metric_calculator
# ─────────────────────────────────────────────────────────────────────────────

class RecoveryInput(BaseModel):
    trigger_at: datetime
    first_regulation_at: datetime | None = None
    harmful_action_stopped_at: datetime | None = None
    functional_recovery_at: datetime | None = None
    emotional_recovery_at: datetime | None = None
    repair_initiated_at: datetime | None = None
    rumination_minutes: int | None = Field(default=None, ge=0)
    harmful_action_occurred: bool = False
    urge_without_action: bool = False
    relationship_resolution_status: str = "not_needed"

    @field_validator("relationship_resolution_status")
    @classmethod
    def known_status(cls, value: str) -> str:
        if value not in RESOLUTION_STATUSES:
            raise ValueError(f"unknown resolution status: {value}")
        return value

    @model_validator(mode="after")
    def validate_times(self):
        _aware(self.trigger_at)
        for field in (
            "first_regulation_at", "harmful_action_stopped_at", "functional_recovery_at",
            "emotional_recovery_at", "repair_initiated_at",
        ):
            value = getattr(self, field)
            if value is not None:
                _aware(value)
                if value < self.trigger_at:
                    raise ValueError(f"{field} cannot precede the trigger")
        return self


def _delta(start: datetime, end: datetime | None) -> float | None:
    return None if end is None else (end - start).total_seconds()


def compute_recovery_metrics(
    recovery: RecoveryInput,
    *,
    previous_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Four separate recoveries, compared only with the user's own history."""
    metrics = {
        "regulation_start_latency": _delta(recovery.trigger_at, recovery.first_regulation_at),
        "behavioral_control_recovery": _delta(recovery.trigger_at, recovery.harmful_action_stopped_at),
        "functional_recovery": _delta(recovery.trigger_at, recovery.functional_recovery_at),
        "emotional_recovery": _delta(recovery.trigger_at, recovery.emotional_recovery_at),
        "repair_initiation_latency": _delta(recovery.trigger_at, recovery.repair_initiated_at),
        "rumination_duration": None if recovery.rumination_minutes is None else recovery.rumination_minutes * 60,
    }
    if not recovery.harmful_action_occurred:
        metrics["behavioral_control_recovery"] = 0.0

    buckets = {name: bucket_for(value) for name, value in metrics.items()}

    comparison: dict[str, Any] = {"status": "INSUFFICIENT_HISTORY", "baseline_event_count": len(previous_events or [])}
    if previous_events and len(previous_events) >= MIN_EVENTS_FOR_COMPARISON:
        comparison = {"status": "COMPARED", "baseline_event_count": len(previous_events), "changes": {}}
        for name, value in metrics.items():
            history = [
                float(item[name]) for item in previous_events
                if item.get(name) is not None
            ]
            if value is None or len(history) < MIN_EVENTS_FOR_COMPARISON:
                comparison["changes"][name] = "INSUFFICIENT_HISTORY"
                continue
            baseline = statistics.median(history)
            if baseline == 0 and value == 0:
                comparison["changes"][name] = "STABLE"
                continue
            ratio = (value - baseline) / max(baseline, 1.0)
            if ratio <= -0.25:
                comparison["changes"][name] = "FASTER"
            elif ratio >= 0.25:
                comparison["changes"][name] = "SLOWER"
            else:
                comparison["changes"][name] = "STABLE"

    payload = {
        "metric_set_id": f"mset_{uuid.uuid4().hex[:10]}",
        "metrics_seconds": metrics,
        "buckets": buckets,
        "harmful_action_occurrence": recovery.harmful_action_occurred,
        "urge_without_action": recovery.urge_without_action and not recovery.harmful_action_occurred,
        "relationship_resolution_status": recovery.relationship_resolution_status,
        "within_user_comparison": comparison,
        "interpretation_rules": [
            "四种恢复分开看：情绪仍难过但已停止伤害行为，属于行为恢复良好。",
            "快速恢复工作不等于成熟，持续有情绪也不等于不成熟。",
            "冲动出现但没有执行，记为自我控制证据，而不是伤害行为。",
        ],
        "next_action": "VERIFY_RELATIONSHIP_REPAIR",
        "rule_version": RULE_VERSION,
    }
    payload["input_hash"] = _hash(payload)
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# EM-23 relationship_repair_evidence_verifier
# ─────────────────────────────────────────────────────────────────────────────

def verify_repair(
    *,
    repair_actions: list[str],
    quality_flags: dict[str, bool],
    completed: bool,
    follow_through_events: int = 0,
    other_party_response: str | None = None,
    safety_flags: list[str] | None = None,
    relationship_safety: str = "STANDARD",
) -> dict[str, Any]:
    """Verify what the user actually did. The other party's response never changes the stage."""
    unsafe = sorted(set(safety_flags or []) & UNSAFE_RELATIONSHIP_FLAGS)
    if unsafe or relationship_safety == "CAUTION":
        return {
            "repair_result_id": f"rep_{uuid.uuid4().hex[:10]}",
            "repair_stage": "R0",
            "repair_stage_label": REPAIR_STAGE_LABELS["R0"],
            "unsafe_flags": unsafe,
            "workflow": "SAFETY_FIRST",
            "notes": [
                "这段关系目前不适合进入普通修复流程。",
                "安全退出、停止联系或寻求保护，在这种情境中就是成熟行为。",
            ],
            "next_action": "ROUTE_TO_SAFETY_SUPPORT",
        }

    flags = {element: bool(quality_flags.get(element)) for element in REPAIR_QUALITY_ELEMENTS}
    actions = {action.lower() for action in repair_actions}
    stage = "R0"
    if flags["impact_acknowledgment"] or "acknowledged_impact" in actions:
        stage = "R1"
    if completed and ({"clarified", "apologised", "requested_conversation"} & actions):
        stage = "R2"
    if stage == "R2" and flags["ownership"] and flags["specificity"] and flags["no_counterattack"]:
        stage = "R3"
    if stage == "R3" and flags["concrete_repair"] and flags["boundary_integrity"]:
        stage = "R4"
    if stage == "R4" and flags["follow_through"] and follow_through_events >= 1:
        stage = "R5"

    missing = [element for element, value in flags.items() if not value]
    return {
        "repair_result_id": f"rep_{uuid.uuid4().hex[:10]}",
        "repair_stage": stage,
        "repair_stage_label": REPAIR_STAGE_LABELS[stage],
        "quality_flags": flags,
        "missing_quality_elements": missing,
        "completed_by_user": completed,
        "follow_through_events": follow_through_events,
        "other_party_response_recorded": other_party_response,
        "other_party_response_affects_stage": False,
        "notes": [
            "系统只评估你可以负责的部分。",
            "对方拒绝原谅、拒绝回应或关系最终结束，都不判定你修复失败。",
            "道歉里夹带反击或旧账，会停留在启动修复阶段。",
        ],
        "next_action": "DETECT_TRAINING_TRANSFER",
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-24 training_transfer_and_prompt_dependence_detector
# ─────────────────────────────────────────────────────────────────────────────

def detect_transfer(
    *,
    skill_id: str,
    events: list[dict[str, Any]],
    trained_context: str,
    days_since_training: int = 0,
) -> dict[str, Any]:
    """Transfer requires event evidence; a system prompt never erases observed progress."""
    used = [event for event in events if event.get("skill_used")]
    if not used:
        return {
            "transfer_id": f"trf_{uuid.uuid4().hex[:10]}",
            "skill_id": skill_id,
            "transfer_stage": "T0",
            "transfer_stage_label": TRANSFER_STAGE_LABELS["T0"],
            "prompt_dependence": "P4",
            "transfer_types": [],
            "evidence_event_ids": [],
            "note": "目前只有理解，没有现实事件证据。这不是失败，只是还没有机会。",
            "next_action": "ANALYSE_RECURRENCE",
        }

    dependence_order = {level: index for index, level in enumerate(PROMPT_DEPENDENCE)}
    best_dependence = min(
        (str(event.get("prompt_dependence") or "P4") for event in used),
        key=lambda level: dependence_order.get(level, 0),
    )
    contexts = {str(event.get("context") or trained_context) for event in used}
    pressure_events = [event for event in used if event.get("under_pressure")]

    stage = "T1"
    if best_dependence in {"P3"}:
        stage = "T1"
    if best_dependence in {"P2"}:
        stage = "T2"
    if best_dependence in {"P1", "P0"}:
        stage = "T3"
    if contexts - {trained_context}:
        stage = max(stage, "T4", key=lambda value: TRANSFER_STAGE_RANK[value])
    if pressure_events:
        stage = max(stage, "T5", key=lambda value: TRANSFER_STAGE_RANK[value])
    if days_since_training >= 30 and len(used) >= 2 and best_dependence in {"P1", "P0"}:
        stage = max(stage, "T6", key=lambda value: TRANSFER_STAGE_RANK[value])

    types: list[str] = []
    if any(str(event.get("context")) == trained_context for event in used):
        types.append("near_transfer")
    if contexts - {trained_context}:
        types.append("context_transfer")
    if pressure_events:
        types.append("pressure_transfer")
    if any(len(event.get("skills_combined") or []) > 1 for event in used):
        types.append("combined_transfer")
    if days_since_training >= 30:
        types.append("maintenance_transfer")

    return {
        "transfer_id": f"trf_{uuid.uuid4().hex[:10]}",
        "skill_id": skill_id,
        "transfer_stage": stage,
        "transfer_stage_label": TRANSFER_STAGE_LABELS[stage],
        "prompt_dependence": best_dependence,
        "prompt_dependence_label": PROMPT_DEPENDENCE_LABELS[best_dependence],
        "transfer_types": types,
        "contexts_observed": sorted(contexts),
        "evidence_event_ids": [str(event.get("event_id")) for event in used],
        "notes": [
            "使用系统提示完成的行动仍然算数，只是提示依赖等级更高。",
            "提示依赖通常按 P4 → P3 → P2 → P1 → P0 逐步下降。",
        ],
        "next_action": "ANALYSE_RECURRENCE",
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-25 recurrence_and_context_generalization_analyzer
# ─────────────────────────────────────────────────────────────────────────────

def analyze_recurrence(
    events: list[dict[str, Any]],
    *,
    pattern_name: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Describe cycles as event patterns — never as a permanent personality."""
    moment = _now(now)
    if len(events) < MIN_EVENTS_FOR_PATTERN:
        return {
            "pattern_id": f"pat_{uuid.uuid4().hex[:10]}",
            "status": "INSUFFICIENT_EVENTS",
            "recurrence_count": len(events),
            "minimum_required": MIN_EVENTS_FOR_PATTERN,
            "note": "事件数量不足以描述循环；这不代表模式不存在，也不代表用户有问题。",
            "next_action": "COLLECT_MORE_EVENTS",
        }

    ordered = sorted(events, key=lambda event: _aware(event["occurred_at"]))
    contexts = sorted({str(event.get("context") or "other") for event in ordered})
    intensities = [float(event["intensity"]) for event in ordered if event.get("intensity") is not None]
    recoveries = [float(event["behavioral_control_recovery"]) for event in ordered if event.get("behavioral_control_recovery") is not None]
    repairs = [str(event.get("repair_stage") or "R0") for event in ordered]

    def _trend(values: list[float]) -> str:
        if len(values) < MIN_EVENTS_FOR_COMPARISON + 1:
            return "INSUFFICIENT_DATA"
        midpoint = max(1, len(values) // 2)
        early = statistics.median(values[:midpoint])
        late = statistics.median(values[midpoint:])
        if late < early * 0.75:
            return "DECREASING"
        if late > early * 1.25:
            return "INCREASING"
        return "STABLE"

    repair_ranks = [REPAIR_STAGE_RANK[stage] for stage in repairs]
    repair_trend = _trend([float(rank) for rank in repair_ranks])
    if repair_trend == "INCREASING":
        repair_direction = "修复行为在增加"
    elif repair_trend == "DECREASING":
        repair_direction = "修复行为在减少"
    else:
        repair_direction = "修复行为大致稳定"

    turning_points = sum(1 for event in ordered if event.get("regulation_attempted"))

    return {
        "pattern_id": f"pat_{uuid.uuid4().hex[:10]}",
        "status": "ANALYSED",
        "pattern_name": pattern_name if pattern_name in KNOWN_CYCLES else None,
        "pattern_description": KNOWN_CYCLES.get(pattern_name or "", None),
        "recurrence_count": len(ordered),
        "first_seen_at": ordered[0]["occurred_at"],
        "last_seen_at": ordered[-1]["occurred_at"],
        "contexts": contexts,
        "context_generalization": len(contexts) > 1,
        "frequency_per_30_days": round(
            len(ordered) / max(1.0, (_aware(ordered[-1]["occurred_at"]) - _aware(ordered[0]["occurred_at"])).days / 30 or 1.0), 2
        ),
        "intensity_trend": _trend(intensities),
        "behavioral_recovery_trend": _trend(recoveries),
        "turning_point_events": turning_points,
        "repair_trend": repair_direction,
        "language_rules": [
            "这是对事件的描述，不是对人格的判断。",
            "循环名称不是医学诊断。",
        ],
        "analysed_at": moment,
        "next_action": "SCHEDULE_CHECKPOINTS",
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-26 longitudinal_checkpoint_orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def schedule_checkpoints(
    *,
    plan_started_at: datetime,
    consented_scopes: list[str],
    now: datetime | None = None,
) -> dict[str, Any]:
    moment = _now(now)
    start = _aware(plan_started_at)
    if "EMD_LONGITUDINAL_TWIN" not in consented_scopes:
        return {
            "schedule_id": f"sch_{uuid.uuid4().hex[:10]}",
            "status": "NOT_SCHEDULED",
            "reason": "LONGITUDINAL_CONSENT_MISSING",
            "checkpoints": [],
            "next_action": "OFFER_LONGITUDINAL_CONSENT",
        }
    checkpoints = [
        {
            "day": day,
            "goal": CHECKPOINT_GOALS[day],
            "due_at": start + timedelta(days=day),
            "window_days": CHECKPOINT_WINDOWS[day],
            "opens_at": start + timedelta(days=day - CHECKPOINT_WINDOWS[day]),
            "closes_at": start + timedelta(days=day + CHECKPOINT_WINDOWS[day]),
            "recommended_evidence": list(CHECKPOINT_EVIDENCE[day]),
            "skippable": True,
        }
        for day in CHECKPOINT_DAYS
    ]
    return {
        "schedule_id": f"sch_{uuid.uuid4().hex[:10]}",
        "status": "SCHEDULED",
        "checkpoints": checkpoints,
        "generated_at": moment,
        "next_action": "RUN_CHECKPOINT_WHEN_DUE",
        "rule_version": RULE_VERSION,
    }


def handle_checkpoint_without_events(day: int, *, opportunities_reported: bool = False) -> dict[str, Any]:
    """No conflict happened — that is data, not failure, and never a reason to create one."""
    if day not in CHECKPOINT_GOALS:
        raise ValueError(f"unknown checkpoint day: {day}")
    return {
        "day": day,
        "status": "NO_COMPARABLE_EVENT",
        "conclusion": "INSUFFICIENT_EVIDENCE_FOR_CHANGE",
        "allowed_alternatives": [
            "回顾一次较早的类似事件",
            "记录一次低强度的小摩擦",
            "延后到下一个窗口",
            "跳过这次检查点",
        ],
        "forbidden": ["不得要求或暗示用户制造一次冲突来完成评估。"],
        "note": (
            "这段时间没有出现可比较的事件；这本身可能是环境变化，也可能是机会变少，"
            "系统不会把它算成成长，也不会算成退步。"
            if not opportunities_reported else
            "有触发机会但没有形成事件记录，可在下次窗口补记。"
        ),
        "next_action": "EXTEND_OR_SKIP_CHECKPOINT",
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-27 fourteen_thirty_ninety_growth_evaluator
# ─────────────────────────────────────────────────────────────────────────────

CHANGE_RESULTS: tuple[str, ...] = (
    "INSUFFICIENT_EVIDENCE", "NO_CONFIRMED_CHANGE", "EARLY_APPLICATION",
    "IMPROVING", "STABILISING", "MAINTAINED_AND_GENERALISED", "REGRESSION_OBSERVED",
)


def evaluate_growth(
    *,
    day: int,
    baseline_metrics: dict[str, Any],
    checkpoint_metrics: dict[str, Any],
    transfer: dict[str, Any] | None = None,
    repair_stages: list[str] | None = None,
    comparable_event_count: int = 0,
    contexts_observed: list[str] | None = None,
    alternative_explanations: list[str] | None = None,
) -> dict[str, Any]:
    """Longitudinal evaluation with explicit attribution limits — correlation, not cause."""
    if day not in CHECKPOINT_GOALS:
        raise ValueError(f"unknown checkpoint day: {day}")
    contexts = sorted(set(contexts_observed or []))
    transfer_stage = str((transfer or {}).get("transfer_stage") or "T0")
    dependence = str((transfer or {}).get("prompt_dependence") or "P4")
    stages = [stage for stage in (repair_stages or []) if stage in REPAIR_STAGE_RANK]

    changes: dict[str, str] = {}
    for name in ("regulation_start_latency", "behavioral_control_recovery", "emotional_recovery", "repair_initiation_latency"):
        before = baseline_metrics.get(name)
        after = checkpoint_metrics.get(name)
        if before is None or after is None:
            changes[name] = "INSUFFICIENT_EVIDENCE"
            continue
        before_value, after_value = float(before), float(after)
        if before_value == 0 and after_value == 0:
            changes[name] = "UNCHANGED"
        elif after_value <= before_value * 0.75:
            changes[name] = "FASTER"
        elif after_value >= before_value * 1.25:
            changes[name] = "SLOWER"
        else:
            changes[name] = "UNCHANGED"

    improved = sum(1 for value in changes.values() if value == "FASTER")
    worsened = sum(1 for value in changes.values() if value == "SLOWER")

    if comparable_event_count < 1:
        result = "INSUFFICIENT_EVIDENCE"
    elif day == 14:
        result = "EARLY_APPLICATION" if TRANSFER_STAGE_RANK[transfer_stage] >= TRANSFER_STAGE_RANK["T1"] else "NO_CONFIRMED_CHANGE"
    elif day == 30:
        if comparable_event_count >= 3 and improved >= 1 and worsened == 0:
            result = "STABILISING"
        elif improved >= 1:
            result = "IMPROVING"
        elif worsened >= 2:
            result = "REGRESSION_OBSERVED"
        else:
            result = "NO_CONFIRMED_CHANGE"
    else:  # day 90
        if worsened >= 2:
            result = "REGRESSION_OBSERVED"
        elif len(contexts) >= 2 and TRANSFER_STAGE_RANK[transfer_stage] >= TRANSFER_STAGE_RANK["T5"] and improved >= 1:
            result = "MAINTAINED_AND_GENERALISED"
        elif improved >= 1:
            result = "IMPROVING"
        else:
            result = "NO_CONFIRMED_CHANGE"

    highlights: list[str] = []
    if stages:
        best = max(stages, key=lambda stage: REPAIR_STAGE_RANK[stage])
        highlights.append(f"最近的修复行为达到 {best}：{REPAIR_STAGE_LABELS[best]}")
    if dependence in {"P1", "P0"}:
        highlights.append("你已经不需要完整脚本就能使用这个做法。")
    if len(contexts) >= 2:
        highlights.append("这个做法出现在不止一种生活场景中。")

    payload = {
        "evaluation_id": f"gev_{uuid.uuid4().hex[:10]}",
        "day": day,
        "goal": CHECKPOINT_GOALS[day],
        "result": result,
        "metric_changes": changes,
        "comparable_event_count": comparable_event_count,
        "contexts_observed": contexts,
        "transfer_stage": transfer_stage,
        "prompt_dependence": dependence,
        "highlights": highlights,
        "attribution_limits": [
            "这些变化与训练同时发生，但不能证明是训练造成的。",
            *(alternative_explanations or list(ALTERNATIVE_EXPLANATIONS)),
        ],
        "not_allowed": [
            "不得把一次成功显示为 100% 稳定。",
            "不得把打卡数量当作能力提高。",
            "不得因为一次复发就取消已经观察到的改变。",
        ],
        "next_action": "UPDATE_FORMATION_TWIN",
        "rule_version": RULE_VERSION,
    }
    payload["input_hash"] = _hash(payload)
    return payload


def event_to_batch1_evidence(
    capture: dict[str, Any],
    *,
    dimension_code: str,
    stage_signal: str,
    occurred_at: datetime,
    behavior_summary: str,
) -> EvidenceItem:
    """Bridge a verified real event into the Batch 1 scorer (EM-06)."""
    if capture.get("status") != "CAPTURED":
        raise ValueError("only captured events may become Batch 1 evidence")
    if stage_signal not in STAGE_RANK:
        raise ValueError(f"unknown stage signal: {stage_signal}")
    context = capture.get("evidence_context", "OTHER")
    if context not in EVIDENCE_CONTEXTS:
        context = "OTHER"
    validate_safe_text(behavior_summary)
    return EvidenceItem(
        evidence_id=str(capture["event_id"]),
        dimension_code=dimension_code,
        evidence_kind="REAL_LIFE_EVENT",
        context=context,
        stage_signal=stage_signal,
        occurred_at=_aware(occurred_at),
        recorded_at=_aware(occurred_at),
        statement_type="USER_REPORTED_FACT",
        independence_group=str(capture["event_id"]),
        behavior_summary=behavior_summary,
        references=[{"reference_type": "REAL_LIFE_EVENT", "reference_id": str(capture["event_id"])}],
    )


WORKFLOW_NODES: tuple[str, ...] = (
    "EM-20_event_capture", "EM-21_timeline_builder", "EM-22_recovery_metrics",
    "EM-23_repair_verifier", "EM-24_transfer_detector", "EM-25_recurrence_analyzer",
    "EM-26_checkpoint_orchestrator", "EM-27_growth_evaluator",
)

STATE_MACHINE: tuple[tuple[str, str], ...] = (
    ("EVENT_SUBMITTED", "EVENT_CAPTURED"),
    ("EVENT_SUBMITTED", "ROUTED_TO_SAFETY"),
    ("EVENT_SUBMITTED", "BLOCKED_NO_CONSENT"),
    ("EVENT_CAPTURED", "TIMELINE_BUILT"),
    ("TIMELINE_BUILT", "METRICS_COMPUTED"),
    ("METRICS_COMPUTED", "REPAIR_VERIFIED"),
    ("REPAIR_VERIFIED", "TRANSFER_DETECTED"),
    ("TRANSFER_DETECTED", "PATTERN_ANALYSED"),
    ("PATTERN_ANALYSED", "CHECKPOINT_SCHEDULED"),
    ("CHECKPOINT_SCHEDULED", "CHECKPOINT_EVALUATED"),
    ("CHECKPOINT_SCHEDULED", "CHECKPOINT_SKIPPED"),
    ("CHECKPOINT_EVALUATED", "TWIN_UPDATED"),
)


def describe_event_engine() -> dict[str, Any]:
    return {
        "module": "emotional_maturity_real_life_events",
        "short_name": "EMD-OS Batch 3",
        "batch": 3,
        "skills": list(WORKFLOW_NODES),
        "event_stages": [{"stage": code, "description": text} for code, text in EVENT_STAGES],
        "real_evidence_levels": REAL_EVIDENCE_LEVELS,
        "recovery_kinds": list(RECOVERY_KINDS),
        "repair_stages": REPAIR_STAGE_LABELS,
        "transfer_stages": TRANSFER_STAGE_LABELS,
        "prompt_dependence": PROMPT_DEPENDENCE_LABELS,
        "known_cycles": KNOWN_CYCLES,
        "checkpoints": [{"day": day, "goal": CHECKPOINT_GOALS[day]} for day in CHECKPOINT_DAYS],
        "unsafe_relationship_flags": sorted(UNSAFE_RELATIONSHIP_FLAGS),
        "does_not": [
            "不把结果归因于用户一个人",
            "不强迫修复不安全关系",
            "不要求用户制造冲突来完成评估",
            "不把事件写成永久人格标签",
            "不宣称训练造成了变化",
        ],
        "engine_version": ENGINE_VERSION,
        "rule_version": RULE_VERSION,
        "state_machine": [{"from": source, "to": target} for source, target in STATE_MACHINE],
    }
