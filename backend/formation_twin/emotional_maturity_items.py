"""EMD-OS Batch 2: ten-dimension adaptive item bank and behavior-evidence engine.

Batch 1 的 `select_next_items` 只是一个编排外观；本模块把它拆成九个可独立测试的 Skill：

    题库注册 EM-11
    → 自适应选题 EM-12
    → 情境化呈现 EM-13
    → 压力情境模拟 EM-14
    → 行为证据提取 EM-15
    → 行为锚点评分 EM-16
    → 反事实追问 EM-17
    → 跨题一致性校准 EM-18
    → 证据充分性判断 EM-19
    → 回到 Batch 1 的 EM-06 / EM-07 / EM-08

工程原则（全部由代码强制）：

* 不存在 `mock_llm_response`；本模块完全确定性，LLM 只在上层负责改写措辞，不做最终评分。
* 语言能力不参与评分：回答长、术语多、引用经文、认同系统价值观都不加分。
* 情境题回答再好也只是「意向」，不能证明现实中的稳定能力。
* 每一条推断都必须带原文片段；没有证据就返回 `unknown`，而不是低分。
* 「我不知道」「跳过」记为证据不足，不记为低成熟。
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .emotional_maturity import (
    DIMENSION_BY_CODE,
    DIMENSION_CODES,
    EVIDENCE_CONTEXTS,
    STAGE_RANK,
    STAGES,
    EvidenceItem,
    UnsafeContentError,
    validate_safe_text,
)


ENGINE_VERSION = "emd-item-engine-1.0"
BANK_VERSION = "emd-bank-v1"
RUBRIC_BUNDLE_VERSION = "emd-rubric-v1"
EXTRACTOR_VERSION = "emd-feature-extractor-1.0"

ITEM_TYPES: tuple[str, ...] = ("SR", "BE", "SF", "CF", "RV")
ITEM_TYPE_LABELS: dict[str, str] = {
    "SR": "一般性自我描述",
    "BE": "最近真实行为事件",
    "SF": "压力情境中的预期反应",
    "CF": "改变条件后的反事实回答",
    "RV": "反向题或效度校准题",
}

DIMENSION_KEYS: dict[str, str] = {
    "D1": "emotion_awareness_granularity",
    "D2": "emotion_regulation_recovery",
    "D3": "stress_regression_tolerance",
    "D4": "responsibility_reality_orientation",
    "D5": "personality_integration_true_self",
    "D6": "attachment_security_differentiation",
    "D7": "boundaries_autonomy_separation",
    "D8": "empathy_mentalization",
    "D9": "conflict_vulnerability_repair",
    "D10": "limits_grief_rest",
}

# 证据等级：情境题回答再好也不能自动视为 L4 / L5。
EVIDENCE_LEVELS: dict[str, str] = {
    "L1": "一般性自我评价",
    "L2": "情境中声称会怎么做",
    "L3": "最近真实事件中实际怎么做",
    "L4": "对方反应后如何继续处理",
    "L5": "事后是否修复、复盘和改变",
}
SOURCE_TYPES: tuple[str, ...] = (
    "self_report", "scenario_intention", "recent_behavior", "escalated_behavior",
    "post_repair", "counterfactual", "clarification",
)
SOURCE_EVIDENCE_LEVEL: dict[str, str] = {
    "self_report": "L1", "scenario_intention": "L2", "counterfactual": "L2",
    "clarification": "L2", "recent_behavior": "L3", "escalated_behavior": "L4",
    "post_repair": "L5",
}
# 工程初始配置，不是已验证的心理测量结论；必须配置化、版本化。
SOURCE_WEIGHTS: dict[str, float] = {
    "self_report": 0.40, "scenario_intention": 0.55, "counterfactual": 0.55,
    "clarification": 0.55, "recent_behavior": 0.80, "escalated_behavior": 0.90,
    "post_repair": 1.00,
}
STABLE_CAPACITY_SOURCES: frozenset[str] = frozenset({"escalated_behavior", "post_repair"})

# Batch 1 的证据种类映射（EM-16 → EM-06 的桥）
BATCH1_EVIDENCE_KIND: dict[str, str] = {
    "self_report": "SELF_DESCRIPTION",
    "scenario_intention": "SCENARIO_RESPONSE",
    "counterfactual": "SCENARIO_RESPONSE",
    "clarification": "SCENARIO_RESPONSE",
    "recent_behavior": "RECENT_BEHAVIOR",
    "escalated_behavior": "REAL_LIFE_EVENT",
    "post_repair": "REAL_LIFE_EVENT",
}

SCENARIO_CONTEXTS: tuple[str, ...] = (
    "workplace", "family", "partner", "friend", "church_service", "solitude",
)
SCENARIO_AXES: dict[str, tuple[str, ...]] = {
    "life_context": SCENARIO_CONTEXTS,
    "stress_level": ("low", "medium", "high"),
    "power_relation": ("equal", "moderate_asymmetry", "strong_asymmetry"),
    "publicity": ("private", "small_group", "public"),
    "motive_clarity": ("clear", "ambiguous", "highly_ambiguous"),
    "event_frequency": ("first_time", "repeated", "chronic"),
    "body_state": ("rested", "tired", "sleep_deprived"),
    "spiritualized_pressure": ("none", "mild", "manipulative"),
}
SCENARIO_CONTEXT_TO_EVIDENCE_CONTEXT: dict[str, str] = {
    "workplace": "WORK", "family": "FAMILY", "partner": "CLOSE_RELATIONSHIP",
    "friend": "FRIENDSHIP", "church_service": "CHURCH", "solitude": "SELF",
}

MAX_COUNTERFACTUALS_PER_ITEM = 2
MAX_CONSECUTIVE_SAME_DIMENSION = 4
HIGH_BURDEN_TYPES: frozenset[str] = frozenset({"BE", "SF", "CF"})


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware datetime required")
    return value


def _now(now: datetime | None = None) -> datetime:
    return _aware(now) if now else datetime.now(timezone.utc)


def _hash(payload: dict[str, Any]) -> str:
    serializable = json.loads(json.dumps(payload, default=str))
    return hashlib.sha256(json.dumps(serializable, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# 统一数据契约
# ─────────────────────────────────────────────────────────────────────────────

class AssessmentItem(BaseModel):
    item_id: str = Field(min_length=3, max_length=40)
    bank_version: str = BANK_VERSION
    dimension_code: str
    item_type: str
    canonical_text: str = Field(min_length=1, max_length=400)
    locale: str = "zh-CN"
    contexts: list[str] = Field(default_factory=list, max_length=8)
    response_mode: Literal["likert", "frequency", "open_text", "forced_choice", "ordered_options"]
    estimated_difficulty: float = Field(default=0.5, ge=0, le=1)
    estimated_discrimination: float = Field(default=0.5, ge=0, le=1)
    calibration_status: Literal["estimated", "pilot_calibrated"] = "estimated"
    reverse_keyed: bool = False
    social_desirability_risk: Literal["low", "medium", "high"] = "medium"
    rubric_id: str = Field(min_length=1, max_length=60)
    safety_level: Literal["normal", "sensitive", "restricted"] = "normal"
    requires_safety_gate: bool = False
    burden: Literal["low", "medium", "high"] = "medium"
    status: Literal["draft", "reviewed", "pilot", "active", "retired"] = "draft"

    @field_validator("dimension_code")
    @classmethod
    def known_dimension(cls, value: str) -> str:
        if value not in DIMENSION_BY_CODE:
            raise ValueError(f"unknown dimension: {value}")
        return value

    @field_validator("item_type")
    @classmethod
    def known_type(cls, value: str) -> str:
        if value not in ITEM_TYPES:
            raise ValueError(f"unknown item type: {value}")
        return value

    @field_validator("contexts")
    @classmethod
    def known_contexts(cls, value: list[str]) -> list[str]:
        unknown = [item for item in value if item not in SCENARIO_CONTEXTS]
        if unknown:
            raise ValueError(f"unknown scenario context: {','.join(unknown)}")
        return value

    @model_validator(mode="after")
    def validate_item(self):
        validate_safe_text(self.canonical_text)
        if self.item_type in {"BE", "SF", "CF"} and self.response_mode != "open_text":
            raise ValueError("behavioral, scenario and counterfactual items require open text")
        if self.item_type == "RV" and not self.reverse_keyed:
            raise ValueError("validity items must be reverse keyed")
        return self


class AssessmentResponse(BaseModel):
    response_id: str = Field(min_length=1, max_length=80)
    assessment_id: str = Field(min_length=1, max_length=80)
    item_id: str = Field(min_length=1, max_length=40)
    raw_response: str | int | list[str] = ""
    response_time_ms: int | None = Field(default=None, ge=0)
    skipped: bool = False
    user_confidence: int | None = Field(default=None, ge=1, le=5)
    context_tags: list[str] = Field(default_factory=list, max_length=6)
    occurred_in_real_life: bool = False
    event_recency_days: int | None = Field(default=None, ge=0)
    submitted_at: datetime

    @model_validator(mode="after")
    def validate_response(self):
        _aware(self.submitted_at)
        return self

    @property
    def text(self) -> str:
        if isinstance(self.raw_response, str):
            return self.raw_response
        if isinstance(self.raw_response, list):
            return " ".join(str(item) for item in self.raw_response)
        return ""


class BehaviorEvidence(BaseModel):
    evidence_id: str
    response_id: str
    dimension_code: str
    source_type: str
    evidence_level: str
    extracted_features: dict[str, Any] = Field(default_factory=dict)
    unsupported_fields: list[str] = Field(default_factory=list)
    context: str = "OTHER"
    scenario_context: str | None = None
    behavior_specificity: float = Field(default=0.0, ge=0, le=1)
    evidence_reliability: float = Field(default=0.0, ge=0, le=1)
    fact_inference_separated: bool = True
    requires_user_confirmation: bool = False
    extractor_version: str = EXTRACTOR_VERSION

    @field_validator("source_type")
    @classmethod
    def known_source(cls, value: str) -> str:
        if value not in SOURCE_TYPES:
            raise ValueError(f"unknown source type: {value}")
        return value


# ─────────────────────────────────────────────────────────────────────────────
# EM-11 ten_dimension_item_bank_registry
# ─────────────────────────────────────────────────────────────────────────────

_SEED: tuple[tuple[str, str, str, str, str], ...] = (
    # (dimension, type, item number, response mode, text)
    ("D1", "SR", "001", "likert", "我通常能把「烦」进一步区分为失望、羞耻、害怕、孤单或无力。"),
    ("D1", "BE", "001", "open_text", "描述最近一次你情绪很强烈的事件：事实是什么、你的解释是什么、你的感受是什么？"),
    ("D1", "SF", "001", "open_text", "一位同工没有回复消息，你立刻觉得自己被轻视。你如何判断这是事实还是推测？"),
    ("D1", "RV", "001", "likert", "只要我的感受足够强烈，就足以证明我对别人动机的判断是正确的。"),
    ("D2", "SR", "001", "likert", "情绪上来时，我通常能在行动前停顿一下。"),
    ("D2", "BE", "001", "open_text", "最近一次你差点说出伤人的话时，后来实际做了什么？"),
    ("D2", "SF", "001", "open_text", "你被当众否定，身体发热、想立刻反击。接下来一分钟你会做什么？"),
    ("D2", "RV", "001", "likert", "情绪真实，就应该立刻表达出来，否则就是压抑。"),
    ("D3", "SR", "001", "likert", "计划突然失败时，我仍能逐步处理问题。"),
    ("D3", "BE", "001", "open_text", "最近一次计划被完全打乱时，你的前十分钟和之后一小时分别如何反应？"),
    ("D3", "SF", "001", "open_text", "重要项目上线失败，你已经连续工作十二小时，主管要求立刻解释。你会怎么做？"),
    ("D3", "RV", "001", "likert", "如果一件重要的事失败，说明后面的努力多半也没有意义。"),
    ("D4", "SR", "001", "likert", "我能区分自己的责任、他人的责任和不可控结果。"),
    ("D4", "BE", "001", "open_text", "最近一次冲突中，你认为自己具体应承担哪一部分责任？"),
    ("D4", "SF", "001", "open_text", "你尽力帮助一位朋友，但他仍然作出伤害自己的选择。你需要负责到什么程度？"),
    ("D4", "RV", "001", "likert", "只要结果不好，就说明我一定还不够努力。"),
    ("D5", "SR", "001", "likert", "我能承认「不知道」「做不到」或「需要帮助」。"),
    ("D5", "BE", "001", "open_text", "最近一次你为了显得完美而隐藏真实状态是什么时候？"),
    ("D5", "SF", "001", "open_text", "服事负责人临时要求你承担一项你不会的任务，众人都在看着。你会如何回应？"),
    ("D5", "RV", "001", "likert", "为了不给别人软弱的印象，隐藏自己的真实感受通常是更成熟的选择。"),
    ("D6", "SR", "001", "likert", "亲近的人沉默或拒绝我时，我不会立刻认定关系要破裂。"),
    ("D6", "BE", "001", "open_text", "最近一次对方没有及时回应你时，你实际做了什么？"),
    ("D6", "SF", "001", "open_text", "伴侣或好友说需要两天独处，你会如何理解和回应？"),
    ("D6", "RV", "001", "likert", "真正亲密的人不应该需要彼此以外的私人空间。"),
    ("D7", "SR", "001", "likert", "我可以拒绝不合理要求，同时允许对方失望。"),
    ("D7", "BE", "001", "open_text", "最近一次你本想拒绝却最终答应的事情是什么？"),
    ("D7", "SF", "001", "open_text", "教会同工说「真正爱主的人不会计较服事量」，但你已严重过载。你会怎么回应？"),
    ("D7", "RV", "001", "likert", "如果对方因我的边界而难过，通常意味着我的边界是错的。"),
    ("D8", "SR", "001", "likert", "我能理解对方的视角，而不必赞同对方。"),
    ("D8", "BE", "001", "open_text", "最近一次你误解了别人动机，后来如何修正？"),
    ("D8", "SF", "001", "open_text", "一个人持有与你完全相反的观点，并批评你的价值观。你会如何了解他的想法？"),
    ("D8", "RV", "001", "likert", "有些观点明显错误，因此没有必要进一步理解持有者的经历。"),
    ("D9", "SR", "001", "likert", "冲突后，我能主动澄清、道歉或提出修复。"),
    ("D9", "BE", "001", "open_text", "描述最近一次冲突之后，你做过的具体修复行为。"),
    ("D9", "SF", "001", "open_text", "对方说「你从来不听我说话」，你觉得很不公平。你第一句会说什么？"),
    ("D9", "RV", "001", "likert", "只要我是对的，就没有必要先表达歉意或修复关系。"),
    ("D10", "SR", "001", "likert", "我可以停止工作，而不把休息理解为失败。"),
    ("D10", "BE", "001", "open_text", "最近一次你承认自己无法控制结果，并作出调整是什么时候？"),
    ("D10", "SF", "001", "open_text", "一项长期努力最终没有结果，你既难过又自责。接下来一周你会如何面对？"),
    ("D10", "RV", "001", "likert", "成熟的人应该尽快摆脱悲伤，不应长时间停留在失落里。"),
)

_SEED_CONTEXTS: dict[str, tuple[str, ...]] = {
    "D1": ("workplace", "church_service"), "D2": ("workplace", "family"),
    "D3": ("workplace", "solitude"), "D4": ("friend", "family"),
    "D5": ("church_service", "workplace"), "D6": ("partner", "friend"),
    "D7": ("church_service", "family"), "D8": ("friend", "workplace"),
    "D9": ("partner", "family"), "D10": ("solitude", "workplace"),
}


def seed_item_bank(*, status: str = "pilot") -> list[AssessmentItem]:
    """First canonical bank: 10 dimensions × {SR, BE, SF, RV}. CF items come from EM-17."""
    items: list[AssessmentItem] = []
    for dimension, item_type, number, mode, text in _SEED:
        items.append(AssessmentItem(
            item_id=f"{dimension}-{item_type}-{number}",
            dimension_code=dimension,
            item_type=item_type,
            canonical_text=text,
            response_mode=mode,  # type: ignore[arg-type]
            contexts=list(_SEED_CONTEXTS[dimension]),
            reverse_keyed=item_type == "RV",
            social_desirability_risk="high" if item_type in {"SR", "RV"} else "medium",
            rubric_id=f"rubric-{dimension}-v1",
            burden="high" if item_type in HIGH_BURDEN_TYPES else "low",
            safety_level="sensitive" if dimension in {"D6", "D9"} and item_type == "BE" else "normal",
            status=status,  # type: ignore[arg-type]
        ))
    return items


def register_item_bank(
    items: list[AssessmentItem],
    *,
    bank_version: str = BANK_VERSION,
    existing: dict[str, AssessmentItem] | None = None,
) -> dict[str, Any]:
    """Validate coverage, immutability and locale isolation before a bank goes live."""
    errors: list[dict[str, str]] = []
    warnings: list[str] = []
    registry = dict(existing or {})

    seen: set[str] = set()
    for item in items:
        if item.bank_version != bank_version:
            errors.append({"item_id": item.item_id, "code": "BANK_VERSION_MISMATCH"})
        if item.item_id in seen:
            errors.append({"item_id": item.item_id, "code": "DUPLICATE_ITEM_ID"})
        seen.add(item.item_id)
        previous = registry.get(item.item_id)
        if previous and previous.canonical_text != item.canonical_text:
            # 题目版本不可变：改文案必须发新 item_id 或新 bank_version。
            errors.append({"item_id": item.item_id, "code": "IMMUTABLE_ITEM_MODIFIED"})
        if previous and previous.locale != item.locale:
            errors.append({"item_id": item.item_id, "code": "LOCALE_MIXED_IN_ONE_ITEM"})
        if item.calibration_status == "pilot_calibrated" and item.status == "draft":
            warnings.append(f"{item.item_id}: 声称已校准但仍是 draft")

    coverage: dict[str, dict[str, int]] = {
        code: {item_type: 0 for item_type in ITEM_TYPES} for code in DIMENSION_CODES
    }
    for item in items:
        coverage[item.dimension_code][item.item_type] += 1

    required = ("SR", "BE", "SF", "RV")
    for code in DIMENSION_CODES:
        missing = [item_type for item_type in required if coverage[code][item_type] == 0]
        if missing:
            errors.append({"item_id": code, "code": "DIMENSION_TYPE_COVERAGE_MISSING", "detail": ",".join(missing)})

    likert_only = all(item.response_mode in {"likert", "frequency"} for item in items) if items else False
    if likert_only:
        errors.append({"item_id": bank_version, "code": "LIKERT_ONLY_BANK_NOT_ALLOWED"})

    status = "REJECTED" if errors else "REGISTERED"
    if status == "REGISTERED":
        registry.update({item.item_id: item for item in items})

    payload = {
        "registry_id": str(uuid.uuid4()),
        "bank_version": bank_version,
        "status": status,
        "registered_item_count": len(items) if status == "REGISTERED" else 0,
        "coverage": coverage,
        "errors": errors,
        "warnings": warnings,
        "calibration_note": "难度与区分度在获得校准样本前只能标记为 estimated。",
        "next_action": "ADAPTIVE_ITEM_SELECTION" if status == "REGISTERED" else "FIX_ITEM_BANK",
        "engine_version": ENGINE_VERSION,
    }
    payload["input_hash"] = _hash(payload)
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# EM-12 adaptive_item_information_selector
# ─────────────────────────────────────────────────────────────────────────────

class SelectionState(BaseModel):
    assessment_id: str = "ema_local"
    asked_item_ids: list[str] = Field(default_factory=list, max_length=200)
    priority_dimensions: list[str] = Field(default_factory=list, max_length=10)
    blocked_topics: list[str] = Field(default_factory=list, max_length=20)
    evidence_by_dimension: dict[str, list[str]] = Field(default_factory=dict)
    contexts_by_dimension: dict[str, list[str]] = Field(default_factory=dict)
    contradictions: list[str] = Field(default_factory=list, max_length=20)
    fatigue: float = Field(default=0.0, ge=0, le=1)
    item_budget: int = Field(default=24, ge=1, le=120)
    consecutive_no_new_evidence: int = Field(default=0, ge=0)
    safety_level: str = "NONE"
    relationship_safety: str = "STANDARD"
    behavior_evidence_allowed: bool = False
    recent_dimensions: list[str] = Field(default_factory=list, max_length=20)


def _safety_allowed(item: AssessmentItem, state: SelectionState) -> bool:
    if state.safety_level in {"ELEVATED", "IMMINENT"}:
        return False
    if item.item_type == "BE" and not state.behavior_evidence_allowed:
        return False
    if item.safety_level == "restricted":
        return False
    if state.relationship_safety == "CAUTION" and item.dimension_code in {"D6", "D9"} and item.item_type in {"BE", "CF"}:
        return False
    return True


def _topic_allowed(item: AssessmentItem, state: SelectionState) -> bool:
    return item.dimension_code not in state.blocked_topics and item.item_id not in state.blocked_topics


def _burden_divisor(item: AssessmentItem, state: SelectionState) -> float:
    base = {"low": 1.0, "medium": 1.4, "high": 1.9}[item.burden]
    return base * (1.0 + state.fatigue)


def select_next_item(state: SelectionState, candidates: list[AssessmentItem]) -> dict[str, Any]:
    """Deterministic MVP selection — no IRT claim until real calibration data exists."""
    stop_reasons: list[str] = []
    if state.safety_level in {"ELEVATED", "IMMINENT"}:
        stop_reasons.append("SAFETY_STATE_CHANGED")
    if len(state.asked_item_ids) >= state.item_budget:
        stop_reasons.append("ITEM_BUDGET_REACHED")
    if state.fatigue >= 0.8:
        stop_reasons.append("FATIGUE_TOO_HIGH")
    if state.consecutive_no_new_evidence >= 3:
        stop_reasons.append("NO_NEW_EVIDENCE_FOR_THREE_ITEMS")

    eligible = [
        item for item in candidates
        if item.item_id not in state.asked_item_ids
        and item.status in {"pilot", "active"}
        and _safety_allowed(item, state)
        and _topic_allowed(item, state)
    ]
    recent_tail = state.recent_dimensions[-MAX_CONSECUTIVE_SAME_DIMENSION:]
    if len(recent_tail) == MAX_CONSECUTIVE_SAME_DIMENSION and len(set(recent_tail)) == 1:
        eligible = [item for item in eligible if item.dimension_code != recent_tail[0]] or eligible

    if stop_reasons or not eligible:
        return {
            "decision": "stop",
            "selected_item_id": None,
            "stop_reasons": stop_reasons or ["NO_ELIGIBLE_ITEMS"],
            "next_action": "EVIDENCE_SUFFICIENCY_CONTROLLER",
            "engine_version": ENGINE_VERSION,
        }

    scored: list[tuple[float, str, AssessmentItem, list[str]]] = []
    for item in eligible:
        reasons: list[str] = []
        sources = state.evidence_by_dimension.get(item.dimension_code, [])
        contexts = state.contexts_by_dimension.get(item.dimension_code, [])

        dimension_gap = 2.0 if item.dimension_code in state.priority_dimensions else 1.0
        if dimension_gap > 1.0:
            reasons.append(f"{item.dimension_code} 为用户优先维度")

        source_gap = 1.0
        if not sources:
            source_gap = 1.6
            reasons.append("该维度尚无任何证据")
        elif set(sources) <= {"self_report"} and item.item_type in {"BE", "SF"}:
            source_gap = 1.8
            reasons.append("当前只有自我描述证据")
        elif "recent_behavior" not in sources and item.item_type == "BE":
            source_gap = 1.5
            reasons.append("缺少近期真实行为证据")

        context_gap = 1.0
        new_contexts = [item_context for item_context in item.contexts if item_context not in contexts]
        if contexts and new_contexts:
            context_gap = 1.3
            reasons.append("该题覆盖尚未评估的生活场景")

        contradiction = 1.0
        if item.dimension_code in state.contradictions and item.item_type in {"BE", "CF"}:
            contradiction = 1.7
            reasons.append("存在待澄清的不一致，优先具体行为或反事实题")

        exposure = 0.85 if item.social_desirability_risk == "high" else 1.0
        priority = (
            dimension_gap * source_gap * context_gap * contradiction
            * item.estimated_discrimination * exposure
        ) / _burden_divisor(item, state)
        scored.append((round(priority, 6), item.item_id, item, reasons))

    # deterministic: highest priority, ties broken by item_id
    best = sorted(scored, key=lambda entry: (-entry[0], entry[1]))[0]
    priority, _, item, reasons = best
    return {
        "decision": "ask_item",
        "selected_item_id": item.item_id,
        "dimension_code": item.dimension_code,
        "item_type": item.item_type,
        "selection_reasons": reasons or ["覆盖该维度的基础证据"],
        "expected_information_gain": min(1.0, round(priority, 3)),
        "estimated_burden": item.burden,
        "next_action": "CONTEXTUAL_ITEM_RENDERER",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-13 contextual_item_renderer
# ─────────────────────────────────────────────────────────────────────────────

_RENDER_LEADING: dict[str, str] = {
    "leading_question": r"你(一定|肯定|难道不)",
    "moral_pressure": r"成熟的人(应该|都会)|真正(爱主|属灵)的人",
}
_RENDER_LEADING_RE = tuple((code, re.compile(pattern)) for code, pattern in _RENDER_LEADING.items())

ALLOWED_RENDER_CHANGES: tuple[str, ...] = (
    "场景名词（同工/同事/家人）", "阅读难度与句长", "语言框架（信仰语言或中性语言）", "示例长度",
)
FORBIDDEN_RENDER_CHANGES: tuple[str, ...] = (
    "题目所测的构念", "评分方向", "反向题的反向性", "行为锚点", "难度声称",
)


def render_item(
    item: AssessmentItem,
    *,
    life_context: str | None = None,
    reading_level: Literal["standard", "simplified"] = "standard",
    spiritual_framework: Literal["faith", "neutral", "user_choice"] = "user_choice",
) -> dict[str, Any]:
    """Only wording and context may change — never the construct or the scoring direction."""
    text = item.canonical_text
    substitutions: list[str] = []
    if life_context and life_context not in SCENARIO_CONTEXTS:
        raise ValueError(f"unknown scenario context: {life_context}")
    if life_context == "workplace" and "同工" in text:
        text = text.replace("同工", "同事")
        substitutions.append("同工→同事")
    if spiritual_framework == "neutral":
        neutral = {"爱主": "尽责", "服事": "志愿服务", "教会同工": "团队伙伴"}
        for source, target in neutral.items():
            if source in text:
                text = text.replace(source, target)
                substitutions.append(f"{source}→{target}")
    if reading_level == "simplified":
        text = text.replace("，同时", "。同时").replace("；", "。")
        substitutions.append("拆分长句")

    for code, pattern in _RENDER_LEADING_RE:
        if pattern.search(text):
            raise UnsafeContentError(f"leading item wording: {code}")
    validate_safe_text(text)

    return {
        "item_id": item.item_id,
        "dimension_code": item.dimension_code,
        "item_type": item.item_type,
        "item_type_label": ITEM_TYPE_LABELS[item.item_type],
        "rendered_text": text,
        "canonical_text": item.canonical_text,
        "response_mode": item.response_mode,
        "reverse_keyed": item.reverse_keyed,
        "substitutions": substitutions,
        "allowed_changes": list(ALLOWED_RENDER_CHANGES),
        "forbidden_changes": list(FORBIDDEN_RENDER_CHANGES),
        "skippable": True,
        "skip_note": "跳过不会被解读为回避，也不会降低任何阶段。",
        "next_action": "COLLECT_RESPONSE",
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-14 real_pressure_scenario_simulator
# ─────────────────────────────────────────────────────────────────────────────

SCENARIO_STAGES: tuple[str, ...] = ("A_INITIAL_TRIGGER", "B_PRESSURE_ESCALATION", "C_REPAIR_WINDOW")

_UNSAFE_SCENARIO_COMBINATION = (
    ("strong_asymmetry", "manipulative"),
)


def build_pressure_scenario(
    *,
    target_dimension: str,
    axes: dict[str, str],
    previous_axes: dict[str, str] | None = None,
    relationship_safety: str = "STANDARD",
    safety_level: str = "NONE",
) -> dict[str, Any]:
    """Branching scenario; escalation changes exactly one variable at a time."""
    if target_dimension not in DIMENSION_BY_CODE:
        raise ValueError(f"unknown dimension: {target_dimension}")
    for axis, value in axes.items():
        if axis not in SCENARIO_AXES:
            raise ValueError(f"unknown scenario axis: {axis}")
        if value not in SCENARIO_AXES[axis]:
            raise ValueError(f"unknown value for {axis}: {value}")
    resolved = {axis: axes.get(axis, values[0]) for axis, values in SCENARIO_AXES.items()}

    changed: list[str] = []
    if previous_axes:
        changed = [axis for axis, value in resolved.items() if previous_axes.get(axis, value) != value]
        if len(changed) > 1:
            raise ValueError("counterfactual and escalation may change only one variable at a time")

    if safety_level in {"ELEVATED", "IMMINENT"}:
        return {
            "scenario_id": str(uuid.uuid4()),
            "status": "BLOCKED_BY_SAFETY",
            "stages": [],
            "next_action": "ROUTE_TO_CRISIS_CARE",
        }

    restrictions: list[str] = []
    if relationship_safety == "CAUTION":
        restrictions.append("不生成对质、深度披露或恢复联系的分支。")
    if (resolved["power_relation"], resolved["spiritualized_pressure"]) in _UNSAFE_SCENARIO_COMBINATION:
        restrictions.append("高权力差 + 属灵操控组合下只观察自我保护选项，不要求用户设想顺服或对质。")

    include_repair = relationship_safety != "CAUTION"
    stages = [
        {
            "stage": "A_INITIAL_TRIGGER",
            "prompt": "事情刚发生的那一刻，你注意到什么？接下来的一分钟你会做什么？",
            "captures": ["emotion_identification", "impulse_delay", "fact_interpretation_separation"],
        },
        {
            "stage": "B_PRESSURE_ESCALATION",
            "prompt": "对方的反应比你预期更强烈，而你已经很累了。这时你会做什么？",
            "captures": ["behavioral_specificity", "attack_tendency", "withdrawal_tendency", "boundary_clarity"],
            "escalated_axis": changed[0] if changed else "stress_level",
        },
    ]
    if include_repair:
        stages.append({
            "stage": "C_REPAIR_WINDOW",
            "prompt": "两天以后，你和对方都冷静下来了。你会做什么，或者不做什么？",
            "captures": ["repair_orientation", "responsibility_ownership", "boundary_proportionality"],
        })

    return {
        "scenario_id": str(uuid.uuid4()),
        "status": "READY",
        "target_dimension": target_dimension,
        "axes": resolved,
        "changed_axes": changed,
        "stages": stages,
        "evidence_context": SCENARIO_CONTEXT_TO_EVIDENCE_CONTEXT.get(resolved["life_context"], "OTHER"),
        "restrictions": restrictions,
        "limitations": [
            "情境模拟只能产生意向证据（L2），不能证明现实中的稳定能力。",
            "任何阶段都可以退出，退出不影响结论。",
        ],
        "next_action": "EXTRACT_SCENARIO_EVIDENCE",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-15 scenario_response_evidence_extractor
# ─────────────────────────────────────────────────────────────────────────────

FEATURE_SPACE: tuple[str, ...] = (
    "emotion_identification", "fact_interpretation_separation", "impulse_delay",
    "behavioral_specificity", "responsibility_ownership", "other_perspective_consideration",
    "clarification_request", "boundary_clarity", "boundary_proportionality",
    "vulnerable_expression", "repair_orientation", "withdrawal_tendency", "attack_tendency",
    "mind_reading", "absolutist_language", "historical_overgeneralization",
    "spiritual_bypassing", "safety_awareness",
)

HARMFUL_FEATURES: frozenset[str] = frozenset({
    "withdrawal_tendency", "attack_tendency", "mind_reading",
    "absolutist_language", "historical_overgeneralization", "spiritual_bypassing",
})

_FEATURE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("emotion_identification", r"(难受|受伤|失望|羞耻|害怕|恐惧|孤单|无力|愤怒|生气|委屈|焦虑|难过|沮丧)"),
    ("fact_interpretation_separation", r"(事实是|我的解释是|这是我的推测|也许只是|不一定代表|我先确认)"),
    ("impulse_delay", r"(先离开|先停|停一下|深呼吸|等我冷静|过一会儿|十分钟|第二天再|先不回|暂停)"),
    ("responsibility_ownership", r"(我(也)?有(错|责任)|是我先|我没有(说清|做到)|我的部分)"),
    ("other_perspective_consideration", r"(他可能|她可能|站在(他|她)的角度|也许(他|她)|对方也许)"),
    ("clarification_request", r"(问(他|她|清楚|一下|问)|确认一下|想了解|请(他|她)说|听(他|她)说)"),
    ("boundary_clarity", r"(我(说|告诉)[^。]{0,8}不|我拒绝|我做不到|我不能接受|我需要先)"),
    ("vulnerable_expression", r"(我(很|有点)?(难受|受伤|害怕|孤单)|我告诉(他|她)我的感受)"),
    ("repair_orientation", r"(道歉|对不起|我去找(他|她)|把话说开|修复|重新沟通|承认)"),
    ("withdrawal_tendency", r"(冷战|不理(他|她)|断联|不想再说|再也不联系|自己消失)"),
    ("attack_tendency", r"(骂|吼|摔|讽刺|反击|羞辱|翻旧账|让(他|她)难堪)"),
    ("mind_reading", r"((他|她)(就是|肯定|一定)(故意|看不起|不在乎)|我知道(他|她)在想)"),
    ("absolutist_language", r"(从来(没有|不)|永远|根本就|一点都不)"),
    ("historical_overgeneralization", r"(每次都(这样|是)|一直都是这样|总是这样)"),
    ("spiritual_bypassing", r"(祷告(一下)?就(好|够)了|交给神就(不用|没事)|基督徒不该有(这种)?情绪|要喜乐就(不该|不能))"),
    ("safety_awareness", r"(先确保安全|离开现场|找人陪|告诉(可信的)?人|保护自己)"),
)
_FEATURE_RE = tuple((feature, re.compile(pattern)) for feature, pattern in _FEATURE_PATTERNS)

_SPECIFICITY_RE = re.compile(r"(昨天|前天|上周|上个月|那天|当时|十分钟|一小时|第二天|周末)")
_EXTREME_BOUNDARY_RE = re.compile(r"(以后就(再也)?不(再)?|永远不再|直接退出|再也不参加)")
_UNKNOWN_RE = re.compile(r"(不知道|说不清|想不起来|没印象)")


def extract_evidence(
    response: AssessmentResponse,
    *,
    dimension_code: str,
    source_type: str,
    context: str = "OTHER",
    scenario_context: str | None = None,
) -> BehaviorEvidence:
    """Deterministic feature extraction. Absent features are `unknown`, never `low`."""
    if dimension_code not in DIMENSION_BY_CODE:
        raise ValueError(f"unknown dimension: {dimension_code}")
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"unknown source type: {source_type}")
    if context not in EVIDENCE_CONTEXTS:
        raise ValueError(f"unknown context: {context}")

    text = response.text
    features: dict[str, Any] = {}
    for feature, pattern in _FEATURE_RE:
        match = pattern.search(text)
        if match:
            features[feature] = {
                "value": True if feature != "emotion_identification" else match.group(0),
                "supporting_span": match.group(0),
            }

    if _SPECIFICITY_RE.search(text) and re.search(r"(我)(先|就|然后|后来)?[^。]{2,}", text):
        features["behavioral_specificity"] = {
            "value": True, "supporting_span": _SPECIFICITY_RE.search(text).group(0),
        }
    if "boundary_clarity" in features:
        extreme = _EXTREME_BOUNDARY_RE.search(text)
        features["boundary_proportionality"] = {
            "value": "uncertain" if extreme else True,
            "supporting_span": extreme.group(0) if extreme else features["boundary_clarity"]["supporting_span"],
        }

    unsupported = [feature for feature in FEATURE_SPACE if feature not in features]
    skipped_or_unknown = response.skipped or bool(_UNKNOWN_RE.search(text)) or not text.strip()

    specificity = 0.0 if skipped_or_unknown else min(1.0, round(len(features) / 6.0, 2))
    reliability = 0.0 if skipped_or_unknown else SOURCE_WEIGHTS[source_type]
    if source_type in {"recent_behavior", "escalated_behavior", "post_repair"} and not response.occurred_in_real_life:
        # 声称是真实事件却没有标记，降级为意向证据的可靠度并要求用户确认。
        reliability = min(reliability, SOURCE_WEIGHTS["scenario_intention"])

    return BehaviorEvidence(
        evidence_id=f"eve_{uuid.uuid4().hex[:12]}",
        response_id=response.response_id,
        dimension_code=dimension_code,
        source_type=source_type,
        evidence_level=SOURCE_EVIDENCE_LEVEL[source_type],
        extracted_features=features,
        unsupported_fields=unsupported,
        context=context,
        scenario_context=scenario_context,
        behavior_specificity=specificity,
        evidence_reliability=round(reliability, 2),
        fact_inference_separated="fact_interpretation_separation" in features,
        requires_user_confirmation=skipped_or_unknown or (
            source_type in {"recent_behavior", "escalated_behavior", "post_repair"}
            and not response.occurred_in_real_life
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# EM-16 behavior_anchor_rubric_scorer
# ─────────────────────────────────────────────────────────────────────────────

# 行为锚点：正向锚点按阶段累积，伤害性锚点直接封顶，语言能力不参与评分。
DIMENSION_ANCHORS: dict[str, dict[str, tuple[str, ...]]] = {
    "D1": {
        "E3": ("emotion_identification", "fact_interpretation_separation"),
        "E4": ("emotion_identification", "fact_interpretation_separation", "behavioral_specificity"),
        "E5": ("emotion_identification", "fact_interpretation_separation", "behavioral_specificity", "other_perspective_consideration"),
    },
    "D2": {
        "E3": ("impulse_delay",),
        "E4": ("impulse_delay", "behavioral_specificity"),
        "E5": ("impulse_delay", "behavioral_specificity", "repair_orientation"),
    },
    "D3": {
        "E3": ("impulse_delay", "behavioral_specificity"),
        "E4": ("impulse_delay", "behavioral_specificity", "responsibility_ownership"),
        "E5": ("impulse_delay", "behavioral_specificity", "responsibility_ownership", "safety_awareness"),
    },
    "D4": {
        "E3": ("responsibility_ownership",),
        "E4": ("responsibility_ownership", "behavioral_specificity"),
        "E5": ("responsibility_ownership", "behavioral_specificity", "boundary_proportionality"),
    },
    "D5": {
        "E3": ("vulnerable_expression",),
        "E4": ("vulnerable_expression", "behavioral_specificity"),
        "E5": ("vulnerable_expression", "behavioral_specificity", "responsibility_ownership"),
    },
    "D6": {
        "E3": ("clarification_request",),
        "E4": ("clarification_request", "vulnerable_expression"),
        "E5": ("clarification_request", "vulnerable_expression", "repair_orientation"),
    },
    "D7": {
        "E3": ("boundary_clarity",),
        "E4": ("boundary_clarity", "boundary_proportionality"),
        "E5": ("boundary_clarity", "boundary_proportionality", "other_perspective_consideration"),
    },
    "D8": {
        "E3": ("other_perspective_consideration",),
        "E4": ("other_perspective_consideration", "clarification_request"),
        "E5": ("other_perspective_consideration", "clarification_request", "boundary_clarity"),
    },
    "D9": {
        "E3": ("clarification_request", "vulnerable_expression"),
        "E4": ("clarification_request", "vulnerable_expression", "repair_orientation"),
        "E5": ("clarification_request", "vulnerable_expression", "repair_orientation", "responsibility_ownership"),
    },
    "D10": {
        "E3": ("impulse_delay",),
        "E4": ("impulse_delay", "vulnerable_expression"),
        "E5": ("impulse_delay", "vulnerable_expression", "boundary_proportionality"),
    },
}

ANCHOR_LABELS: dict[str, str] = {
    "emotion_identification": "命名了具体情绪",
    "fact_interpretation_separation": "区分了事实与解释",
    "impulse_delay": "在行动前有停顿",
    "behavioral_specificity": "描述了具体可观察的行为",
    "responsibility_ownership": "承担了自己的那一部分",
    "other_perspective_consideration": "考虑了对方的视角",
    "clarification_request": "使用了澄清提问",
    "boundary_clarity": "提出了明确的边界",
    "boundary_proportionality": "边界与情境相称",
    "vulnerable_expression": "表达了脆弱感受",
    "repair_orientation": "有修复取向",
    "safety_awareness": "考虑了安全",
}

HARMFUL_STAGE_CAP: dict[str, str] = {
    "attack_tendency": "E1",
    "withdrawal_tendency": "E2",
    "mind_reading": "E2",
    "spiritual_bypassing": "E2",
    "historical_overgeneralization": "E2",
    "absolutist_language": "E3",
}


def score_rubric(evidence: BehaviorEvidence) -> dict[str, Any]:
    """Behaviorally anchored scoring: highest stage that the anchors actually support."""
    dimension = evidence.dimension_code
    anchors = DIMENSION_ANCHORS[dimension]
    # "uncertain" / "partial" 不算达成锚点，只算已观察到但尚未确认。
    present = {
        feature for feature, payload in evidence.extracted_features.items()
        if payload.get("value") not in (None, False, "unknown", "uncertain", "partial")
    }
    harmful = sorted(present & HARMFUL_FEATURES)

    if evidence.behavior_specificity == 0.0 and not present:
        stage = "E0"
        supported: list[str] = []
        missing = ["没有足够具体的行为描述"]
    else:
        stage = "E1"
        supported = []
        for candidate in ("E5", "E4", "E3"):
            required = anchors[candidate]
            if set(required) <= present:
                stage = candidate
                supported = [ANCHOR_LABELS.get(item, item) for item in required]
                break
        else:
            partial = [item for item in anchors["E3"] if item in present]
            if partial and "behavioral_specificity" in present:
                # 行为具体且部分达到 E3 锚点：能实践但证据尚不完整
                stage = "E3"
                supported = [ANCHOR_LABELS.get(item, item) for item in partial]
            elif present & {"emotion_identification", "fact_interpretation_separation", "other_perspective_consideration"}:
                # 有觉察类特征但没有行动锚点 → E2
                stage = "E2"
                supported = [ANCHOR_LABELS.get(item, item) for item in sorted(present) if item in ANCHOR_LABELS]
        missing = [
            f"缺少：{ANCHOR_LABELS.get(item, item)}"
            for item in anchors["E4"] if item not in present
        ]

    caps_applied: list[str] = []
    for feature in harmful:
        ceiling = HARMFUL_STAGE_CAP[feature]
        if STAGE_RANK[stage] > STAGE_RANK[ceiling]:
            stage = ceiling
            caps_applied.append(feature)

    # 情境意图不能证明长期稳定
    is_stable = evidence.source_type in STABLE_CAPACITY_SOURCES
    if not is_stable and STAGE_RANK[stage] > STAGE_RANK["E3"] and evidence.source_type in {
        "self_report", "scenario_intention", "counterfactual", "clarification",
    }:
        stage = "E3"
        caps_applied.append("INTENTION_ONLY")
    if evidence.source_type == "self_report" and STAGE_RANK[stage] > STAGE_RANK["E2"]:
        stage = "E2"
        caps_applied.append("SELF_REPORT_ONLY")

    weight = SOURCE_WEIGHTS[evidence.source_type]
    source_confidence = "high" if weight >= 0.90 else ("medium" if weight >= 0.80 else "low")
    if evidence.requires_user_confirmation:
        source_confidence = "low"

    return {
        "rubric_result_id": f"rr_{uuid.uuid4().hex[:12]}",
        "dimension_code": dimension,
        "rubric_version": f"rubric-{dimension}-v1",
        "rubric_bundle_version": RUBRIC_BUNDLE_VERSION,
        "provisional_stage": stage,
        "stage_support": {"supported_anchors": supported, "missing_anchors": missing},
        "harmful_markers": harmful,
        "caps_applied": caps_applied,
        "source_type": evidence.source_type,
        "evidence_level": evidence.evidence_level,
        "source_confidence": source_confidence,
        "source_weight": weight,
        "context": evidence.context,
        "scenario_context": evidence.scenario_context,
        "is_stable_capacity": is_stable and STAGE_RANK[stage] >= STAGE_RANK["E4"],
        "language_not_scored": [
            "回答长度", "术语数量", "引用经文", "熟悉心理学", "认同系统价值观",
        ],
        "next_action": "CROSS_ITEM_CONSISTENCY_CALIBRATOR",
        "engine_version": ENGINE_VERSION,
    }


def to_batch1_evidence(
    rubric_result: dict[str, Any],
    evidence: BehaviorEvidence,
    *,
    occurred_at: datetime,
    behavior_summary: str = "",
    independence_group: str | None = None,
) -> EvidenceItem:
    """Bridge EM-16 output into the Batch 1 scorer (EM-06)."""
    kind = BATCH1_EVIDENCE_KIND[evidence.source_type]
    summary = behavior_summary
    if kind in {"RECENT_BEHAVIOR", "REAL_LIFE_EVENT"} and not summary:
        anchors = rubric_result["stage_support"]["supported_anchors"]
        summary = "、".join(anchors) if anchors else "记录了一次具体行为"
    return EvidenceItem(
        evidence_id=evidence.evidence_id,
        dimension_code=evidence.dimension_code,
        evidence_kind=kind,
        context=evidence.context,
        stage_signal=rubric_result["provisional_stage"],
        occurred_at=_aware(occurred_at),
        recorded_at=_aware(occurred_at),
        statement_type="SCENARIO_RESPONSE" if kind == "SCENARIO_RESPONSE" else "USER_REPORTED_FACT",
        self_rated=evidence.source_type == "self_report",
        independence_group=independence_group or evidence.response_id,
        behavior_summary=summary,
        references=[{"reference_type": "ASSESSMENT_RESPONSE", "reference_id": evidence.response_id}],
    )


# ─────────────────────────────────────────────────────────────────────────────
# EM-17 counterfactual_probe_generator
# ─────────────────────────────────────────────────────────────────────────────

COUNTERFACTUAL_VARIABLES: dict[str, tuple[str, str, str]] = {
    "power_relation": ("power_asymmetry_sensitivity", "equal", "strong_asymmetry"),
    "publicity": ("public_exposure_sensitivity", "private", "public"),
    "closeness": ("intimacy_sensitivity", "friend", "family"),
    "event_frequency": ("repetition_sensitivity", "first_time", "chronic"),
    "other_reaction": ("other_reaction_sensitivity", "understanding", "spiritual_accusation"),
    "body_state": ("depletion_sensitivity", "rested", "sleep_deprived"),
    "real_cost": ("cost_sensitivity", "low_cost", "role_loss"),
    "motive_clarity": ("ambiguity_sensitivity", "clear", "highly_ambiguous"),
}

_PROBE_TEMPLATES: dict[str, str] = {
    "power_relation": "如果提出这个要求的不是同辈，而是决定你去留的负责人，你刚才说的做法还会一样吗？具体会怎么做？",
    "publicity": "如果这件事不是私下发生，而是当着一群人，你会怎么做？",
    "closeness": "如果对方不是朋友，而是你的父母或伴侣，你的做法会有什么不同？",
    "event_frequency": "如果这已经是第十次发生，而不是第一次，你会怎么做？",
    "other_reaction": "如果对方没有理解你，而是用属灵理由指责你，你接下来会做什么？",
    "body_state": "如果那天你已经连续几晚没睡好，你还能做到刚才说的吗？实际可能会怎样？",
    "real_cost": "如果坚持这个做法可能让你失去这个岗位或群体身份，你会怎么选择？",
    "motive_clarity": "如果你并不确定对方是不是真的越界，你会怎么处理？",
}


def generate_counterfactual_probe(
    *,
    base_item_id: str,
    target_dimension: str,
    base_response_summary: str,
    uncertainty_type: str,
    already_tested_variables: list[str] | None = None,
    probes_for_base_item: int = 0,
    relationship_safety: str = "STANDARD",
) -> dict[str, Any]:
    """Change exactly one condition to test whether a capacity is stable or context-bound."""
    tested = set(already_tested_variables or [])
    if probes_for_base_item >= MAX_COUNTERFACTUALS_PER_ITEM:
        return {
            "decision": "no_probe",
            "reason": "MAX_PROBES_PER_ITEM_REACHED",
            "note": "每个原题最多两个反事实追问，避免把评估变成审讯。",
            "next_action": "CROSS_ITEM_CONSISTENCY_CALIBRATOR",
        }

    ordered = [
        variable for variable, (label, _, _) in COUNTERFACTUAL_VARIABLES.items()
        if variable not in tested and (label == uncertainty_type or uncertainty_type == "unspecified")
    ] or [variable for variable in COUNTERFACTUAL_VARIABLES if variable not in tested]
    if not ordered:
        return {"decision": "no_probe", "reason": "ALL_VARIABLES_TESTED", "next_action": "CROSS_ITEM_CONSISTENCY_CALIBRATOR"}

    if relationship_safety == "CAUTION":
        ordered = [variable for variable in ordered if variable not in {"other_reaction", "closeness"}] or ordered

    variable = ordered[0]
    label, baseline, changed = COUNTERFACTUAL_VARIABLES[variable]
    text = _PROBE_TEMPLATES[variable]
    validate_safe_text(text)
    return {
        "decision": "ask_probe",
        "probe_id": f"cf_{uuid.uuid4().hex[:10]}",
        "base_item_id": base_item_id,
        "item_id": f"{target_dimension}-CF-{variable}",
        "target_dimension": target_dimension,
        "changed_variable": variable,
        "uncertainty_type": label,
        "from_condition": baseline,
        "to_condition": changed,
        "probe_text": text,
        "base_response_summary": base_response_summary[:160],
        "single_variable_change": True,
        "max_probes_per_item": MAX_COUNTERFACTUALS_PER_ITEM,
        "interpretation_rules": [
            "回答变化说明能力对情境敏感，不说明用户之前不诚实。",
            "反事实回答仍属意向证据（L2），不能升级为现实能力。",
        ],
        "next_action": "EXTRACT_SCENARIO_EVIDENCE",
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-18 cross_item_consistency_calibrator
# ─────────────────────────────────────────────────────────────────────────────

DIFFERENCE_TYPES: tuple[str, ...] = (
    "context_variance", "temporal_change", "self_report_behavior_gap",
    "direct_contradiction", "principle_action_gap", "requires_clarification",
)

_FORBIDDEN_CALIBRATION_WORDS: tuple[str, ...] = ("撒谎", "虚伪", "不诚实", "作假", "诚实度")


def classify_difference(evidence_a: dict[str, Any], evidence_b: dict[str, Any]) -> str:
    if evidence_a.get("context") != evidence_b.get("context"):
        return "context_variance"
    if evidence_a.get("time_period") != evidence_b.get("time_period"):
        return "temporal_change"
    sources = {evidence_a.get("source_type"), evidence_b.get("source_type")}
    if "self_report" in sources and sources & {"recent_behavior", "escalated_behavior", "post_repair"}:
        return "self_report_behavior_gap"
    if evidence_a.get("item_semantics_are_inverse") or evidence_b.get("item_semantics_are_inverse"):
        return "direct_contradiction"
    if "scenario_intention" in sources and sources & {"recent_behavior", "escalated_behavior"}:
        return "principle_action_gap"
    return "requires_clarification"


def calibrate_consistency(dimension_code: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    """Differences lower confidence and describe context — they never call the user dishonest."""
    if dimension_code not in DIMENSION_BY_CODE:
        raise ValueError(f"unknown dimension: {dimension_code}")
    patterns: list[dict[str, Any]] = []
    confidence_delta = 0.0

    by_context: dict[str, list[str]] = {}
    for result in results:
        by_context.setdefault(str(result.get("context") or "OTHER"), []).append(str(result.get("provisional_stage") or "E0"))
    context_stages = {
        context: max(stages, key=lambda stage: STAGE_RANK[stage])
        for context, stages in by_context.items()
    }
    if len(context_stages) > 1 and len(set(context_stages.values())) > 1:
        spread = max(STAGE_RANK[stage] for stage in context_stages.values()) - min(
            STAGE_RANK[stage] for stage in context_stages.values()
        )
        patterns.append({
            "type": "context_variance",
            "contexts": context_stages,
            "severity": "high" if spread >= 2 else "medium",
            "interpretation": "这个能力似乎依赖关系类型，在某些场景中明显更困难。",
        })
        confidence_delta -= 0.15 if spread >= 2 else 0.08

    for index, first in enumerate(results):
        for second in results[index + 1 :]:
            if first.get("context") != second.get("context"):
                continue
            kind = classify_difference(first, second)
            gap = abs(STAGE_RANK[str(first.get("provisional_stage") or "E0")] - STAGE_RANK[str(second.get("provisional_stage") or "E0")])
            if kind in {"self_report_behavior_gap", "principle_action_gap"} and gap >= 2:
                patterns.append({
                    "type": kind,
                    "severity": "medium",
                    "interpretation": "一般自我评价高于近期真实行为证据；这通常说明认知理解快于行为整合。",
                })
                confidence_delta -= 0.10
            elif kind == "direct_contradiction" and gap >= 2:
                patterns.append({
                    "type": "direct_contradiction",
                    "severity": "medium",
                    "interpretation": "两道题的方向不一致，需要一次澄清而不是判断谁对谁错。",
                })
                confidence_delta -= 0.12
            elif kind == "temporal_change" and gap >= 1:
                patterns.append({
                    "type": "temporal_change",
                    "severity": "low",
                    "interpretation": "较早与较近的证据不同，这可能代表成长，而不是回答无效。",
                })

    status = "consistent"
    if any(item["type"] == "context_variance" for item in patterns):
        status = "context_dependent"
    elif patterns:
        status = "needs_clarification"

    recommended_probe = None
    if status != "consistent":
        recommended_probe = {"type": "counterfactual", "target_dimension": dimension_code}

    payload = {
        "calibration_id": f"cal_{uuid.uuid4().hex[:10]}",
        "dimension_code": dimension_code,
        "consistency_status": status,
        "patterns": patterns,
        "confidence_adjustments": {"general_stage_confidence": round(confidence_delta, 3)},
        "score_adjustments": {},
        "clarification_needed": status != "consistent",
        "recommended_probe": recommended_probe,
        "internal_metrics_not_user_visible": [
            "semantic_consistency", "behavioral_consistency", "context_stability",
            "temporal_stability", "source_agreement",
        ],
        "next_action": "COUNTERFACTUAL_PROBE_GENERATOR" if status != "consistent" else "EVIDENCE_SUFFICIENCY_CONTROLLER",
        "engine_version": ENGINE_VERSION,
    }
    for item in patterns:
        for word in _FORBIDDEN_CALIBRATION_WORDS:
            if word in item["interpretation"]:
                raise UnsafeContentError(f"calibration wording implies dishonesty: {word}")
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# EM-19 assessment_evidence_sufficiency_controller
# ─────────────────────────────────────────────────────────────────────────────

SUFFICIENCY_LEVELS: tuple[str, ...] = ("insufficient", "provisional", "moderate_confidence", "higher_confidence")
SUFFICIENCY_RANK: dict[str, int] = {level: index for index, level in enumerate(SUFFICIENCY_LEVELS)}
REAL_SOURCES: frozenset[str] = frozenset({"recent_behavior", "escalated_behavior", "post_repair"})


def dimension_readiness(coverage: dict[str, Any]) -> dict[str, Any]:
    """Engineering thresholds only; they must be recalibrated on real assessment data."""
    counts: dict[str, int] = {source: int(coverage.get(source, 0) or 0) for source in SOURCE_TYPES}
    contexts = list(coverage.get("contexts") or [])
    contradictions = int(coverage.get("unresolved_contradictions", 0) or 0)
    confirmed = int(coverage.get("user_confirmed_evidence", 0) or 0)
    total = sum(counts.values())
    sources_used = [source for source, value in counts.items() if value]
    real_behavior = sum(counts[source] for source in REAL_SOURCES)
    has_pressure = bool(counts["scenario_intention"] or counts["escalated_behavior"])
    has_repair = bool(counts["post_repair"])
    has_escalation = bool(counts["escalated_behavior"])
    abstract_only = sources_used == ["self_report"]

    status = "insufficient"
    if total >= 3 and len(sources_used) >= 2 and (real_behavior or has_pressure) and not abstract_only:
        status = "provisional"
    if (
        total >= 4 and real_behavior >= 1 and has_pressure
        and len(contexts) >= 2 and contradictions == 0
    ):
        status = "moderate_confidence"
    if (
        total >= 5 and len(contexts) >= 2 and has_escalation and has_repair
        and confirmed >= 1 and contradictions == 0
    ):
        status = "higher_confidence"

    missing: list[str] = []
    if not real_behavior:
        missing.append("缺少近期真实行为证据")
    if not has_pressure:
        missing.append("缺少压力情境证据")
    if len(contexts) < 2:
        missing.append("只覆盖了一个生活场景")
    if contradictions:
        missing.append("存在尚未澄清的不一致")
    if not has_repair and status in {"moderate_confidence", "provisional"}:
        missing.append("缺少事后修复或恢复证据")

    return {"status": status, "evidence_count": total, "sources": sources_used,
            "contexts": contexts, "missing_evidence": missing}


def evaluate_sufficiency(
    *,
    coverage_by_dimension: dict[str, dict[str, Any]],
    priority_dimensions: list[str] | None = None,
    fatigue: float = 0.0,
    items_asked: int = 0,
    item_budget: int = 24,
    safety_changed: bool = False,
) -> dict[str, Any]:
    """Decide whether to keep asking, pause, or complete — never chase completeness forever."""
    readiness = {code: dimension_readiness(coverage) for code, coverage in coverage_by_dimension.items()}
    focus = [code for code in (priority_dimensions or list(readiness)) if code in readiness]
    budget_left = max(0, item_budget - items_asked)
    minimum_met = all(
        SUFFICIENCY_RANK[readiness[code]["status"]] >= SUFFICIENCY_RANK["provisional"] for code in focus
    ) if focus else False

    if safety_changed:
        decision, status = "stop_for_safety", "safety_routed"
    elif fatigue >= 0.8 and minimum_met:
        decision, status = "pause_and_save", "paused_with_minimum_evidence"
    elif fatigue >= 0.8:
        decision, status = "stop_assessment", "insufficient_evidence"
    elif not budget_left:
        decision, status = "complete_assessment", (
            "provisional_complete" if minimum_met else "insufficient_evidence"
        )
    elif all(
        SUFFICIENCY_RANK[readiness[code]["status"]] >= SUFFICIENCY_RANK["moderate_confidence"] for code in focus
    ) and focus:
        decision, status = "complete_assessment", "complete"
    else:
        decision, status = "continue_assessment", "in_progress"

    next_item_hint: list[str] = []
    for code in focus:
        entry = readiness[code]
        if "缺少近期真实行为证据" in entry["missing_evidence"]:
            next_item_hint.append(f"{code}: 优先真实事件题(BE)")
        elif "存在尚未澄清的不一致" in entry["missing_evidence"]:
            next_item_hint.append(f"{code}: 优先澄清或反事实题(CF)")
        elif "只覆盖了一个生活场景" in entry["missing_evidence"]:
            next_item_hint.append(f"{code}: 优先另一生活场景的情境题(SF)")

    remaining_unknowns = [
        f"{code}: {'; '.join(readiness[code]['missing_evidence'])}"
        for code in focus if readiness[code]["missing_evidence"]
    ]
    next_actions = (
        ["MATURITY_DIMENSION_SCORER", "RESPONSE_VALIDITY_AUDITOR", "PROFILE_SYNTHESIZER"]
        if decision in {"complete_assessment", "stop_assessment"}
        else ["ADAPTIVE_ITEM_SELECTION"]
    )
    payload = {
        "decision": decision,
        "assessment_status": status,
        "dimension_readiness": readiness,
        "next_item_hints": next_item_hint,
        "remaining_unknowns": remaining_unknowns,
        "evidence_bundle_id": f"evbundle_{uuid.uuid4().hex[:10]}",
        "budget_left": budget_left,
        "notes": [
            "跳过敏感题不会被惩罚，也不会计为低成熟。",
            "不要求十个维度都达到高置信度才允许结束。",
        ],
        "next_actions": next_actions,
        "engine_version": ENGINE_VERSION,
    }
    payload["input_hash"] = _hash(payload)
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# 状态机与自描述
# ─────────────────────────────────────────────────────────────────────────────

WORKFLOW_NODES: tuple[str, ...] = (
    "EM-11_item_bank_registry", "EM-12_adaptive_item_selector", "EM-13_contextual_renderer",
    "EM-14_pressure_scenario_simulator", "EM-15_evidence_extractor", "EM-16_rubric_scorer",
    "EM-17_counterfactual_probe", "EM-18_consistency_calibrator", "EM-19_sufficiency_controller",
)

STATE_MACHINE: tuple[tuple[str, str], ...] = (
    ("BANK_REGISTERED", "ITEM_SELECTED"),
    ("ITEM_SELECTED", "ITEM_RENDERED"),
    ("ITEM_RENDERED", "RESPONSE_COLLECTED"),
    ("ITEM_RENDERED", "ITEM_SKIPPED"),
    ("ITEM_SKIPPED", "ITEM_SELECTED"),
    ("RESPONSE_COLLECTED", "EVIDENCE_EXTRACTED"),
    ("EVIDENCE_EXTRACTED", "RUBRIC_SCORED"),
    ("RUBRIC_SCORED", "CONSISTENCY_CALIBRATED"),
    ("CONSISTENCY_CALIBRATED", "COUNTERFACTUAL_PROBED"),
    ("COUNTERFACTUAL_PROBED", "EVIDENCE_EXTRACTED"),
    ("CONSISTENCY_CALIBRATED", "SUFFICIENCY_EVALUATED"),
    ("SUFFICIENCY_EVALUATED", "ITEM_SELECTED"),
    ("SUFFICIENCY_EVALUATED", "ASSESSMENT_COMPLETE"),
    ("SUFFICIENCY_EVALUATED", "ASSESSMENT_PAUSED"),
    ("SUFFICIENCY_EVALUATED", "ROUTED_TO_CRISIS"),
)


def describe_item_engine() -> dict[str, Any]:
    return {
        "module": "emotional_maturity_item_bank",
        "short_name": "EMD-OS Batch 2",
        "batch": 2,
        "skills": list(WORKFLOW_NODES),
        "item_types": ITEM_TYPE_LABELS,
        "dimension_keys": DIMENSION_KEYS,
        "evidence_levels": EVIDENCE_LEVELS,
        "source_weights": SOURCE_WEIGHTS,
        "feature_space": list(FEATURE_SPACE),
        "sufficiency_levels": list(SUFFICIENCY_LEVELS),
        "scenario_axes": {axis: list(values) for axis, values in SCENARIO_AXES.items()},
        "bank_version": BANK_VERSION,
        "rubric_bundle_version": RUBRIC_BUNDLE_VERSION,
        "engine_version": ENGINE_VERSION,
        "llm_role": "只做措辞改写与结构化抽取的候选；最终评分、阶段与充分性判断全部由规则引擎决定。",
        "state_machine": [{"from": source, "to": target} for source, target in STATE_MACHINE],
    }
