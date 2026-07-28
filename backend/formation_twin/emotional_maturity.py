"""EMD-OS Batch 1: emotional maturity diagnostic governance for Formation Twin.

情感成熟度诊断域（Emotional Maturity Diagnostic OS, EMD-OS）是 Formation Twin 的
一个诊断域，位于现有十个训练干预引擎（emotionally_healthy / anger / lament /
forgiveness / rule_of_life ...）的上游：

    知情授权 → 安全分流 → 多维评估 → 证据采集 → 可信度校准
    → 情感成熟度画像 → 训练 Skill 路由 → 14/30/90 天复测 → Twin 更新

本模块只实现 EM-01 ~ EM-10（Batch 1 底座），全部为确定性纯函数：不调用模型、
不产生副作用、不生成自由指令。

它明确不负责：
  * 判断用户是否得救、是否有圣灵同在、神是否喜悦；
  * 生成单一「情感成熟总分」或属灵排名；
  * 精神疾病临床诊断；
  * 替代牧者、教会、心理咨询师或危机支持；
  * 把童年经历、依恋类型或一次冲突写成用户永久人格。

安全与危机分流复用仓库既有能力：`crisis_engine.triage`、
`formation_twin.formation_safety.review_generated_text`、`theological_safety`。
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .formation_safety import review_generated_text


ENGINE_VERSION = "emd-os-engine-1.0"
RULE_VERSION = "emd-maturity-rules-1.0"
MODEL_VERSION = "emdm-0.1"
ROUTING_SCHEMA_VERSION = "emd-growth-route-1.0"


# ─────────────────────────────────────────────────────────────────────────────
# EMDM v0.1 十维模型（双轴中的情感轴；不与属灵成熟合并计分）
# ─────────────────────────────────────────────────────────────────────────────

DIMENSIONS: tuple[dict[str, Any], ...] = (
    {
        "code": "D1", "key": "emotion_awareness", "name": "情绪觉察与情绪颗粒度",
        "description": "能否在情绪发生时命名它，并区分相近情绪。",
        "training_modules": ["emotionally_healthy", "formation_twin_emotions"],
        "training_routes": ["/api/eh/assess", "/api/v1/formation-twin/emotions/checkin"],
    },
    {
        "code": "D2", "key": "regulation_recovery", "name": "情绪调节与恢复能力",
        "description": "被触发后是否能在不伤人、不伤己的前提下恢复功能。",
        "training_modules": ["anger", "comfort", "crisis"],
        "training_routes": ["/api/anger", "/api/comfort", "/api/crisis/grounding"],
    },
    {
        "code": "D3", "key": "stress_tolerance", "name": "压力退化与挫折承受力",
        "description": "在压力、疲惫与失败下，行为退化的幅度与恢复速度。",
        "training_modules": ["burnout", "suffering", "sabbath"],
        "training_routes": ["/api/burnout", "/api/suffering", "/api/sabbath"],
    },
    {
        "code": "D4", "key": "responsibility_reality", "name": "责任承担与现实感",
        "description": "能否区分自己的部分与他人的部分，并承担可承担的部分。",
        "training_modules": ["repentance", "conscience"],
        "training_routes": ["/api/repentance", "/api/conscience"],
    },
    {
        "code": "D5", "key": "integration_authenticity", "name": "人格整合与真我一致性",
        "description": "在不同场景中是否是同一个人，而不是靠角色分裂维持。",
        "training_modules": ["grace_identity", "narrative", "worldview"],
        "training_routes": ["/api/grace-identity", "/api/narrative"],
    },
    {
        "code": "D6", "key": "attachment_differentiation", "name": "依恋安全与自我分化",
        "description": "亲近时能否保持自我，独处时能否保持连接。",
        "training_modules": ["adoption", "loneliness", "parenting"],
        "training_routes": ["/api/adoption", "/api/loneliness"],
    },
    {
        "code": "D7", "key": "boundary_autonomy", "name": "边界、自主性与课题分离",
        "description": "能否在不敌意、不讨好的前提下说不并承担后果。",
        "training_modules": ["fear_of_man", "rule_of_life"],
        "training_routes": ["/api/fear-of-man", "/api/rule-of-life"],
    },
    {
        "code": "D8", "key": "empathy_mentalization", "name": "同理心与心智化能力",
        "description": "能否在不确定对方动机时保持好奇而非归罪。",
        "training_modules": ["neighbor_love", "ordo_amoris"],
        "training_routes": ["/api/neighbor-love", "/api/ordo-amoris"],
    },
    {
        "code": "D9", "key": "conflict_repair", "name": "冲突、脆弱表达与关系修复",
        "description": "冲突后是否能启动修复、承担自己的部分并改变行为。",
        "training_modules": ["forgiveness", "tender_heart"],
        "training_routes": ["/api/forgiveness", "/api/tender-heart"],
    },
    {
        "code": "D10", "key": "limits_grief_rest", "name": "有限性、哀伤与安息能力",
        "description": "能否承认限制、允许哀伤，并真正停下来安息。",
        "training_modules": ["lament", "waiting", "contentment", "sabbath"],
        "training_routes": ["/api/lament", "/api/waiting", "/api/sabbath"],
    },
)

DIMENSION_CODES: tuple[str, ...] = tuple(item["code"] for item in DIMENSIONS)
DIMENSION_BY_CODE: dict[str, dict[str, Any]] = {item["code"]: item for item in DIMENSIONS}

STAGES: tuple[str, ...] = ("E0", "E1", "E2", "E3", "E4", "E5")
STAGE_RANK: dict[str, int] = {stage: index for index, stage in enumerate(STAGES)}
STAGE_LABELS: dict[str, str] = {
    "E0": "当前证据不足以描述这个维度",
    "E1": "多在事后才意识到，当下几乎没有选择空间",
    "E2": "能够意识到，但需要外部提示才能采取不同做法",
    "E3": "在熟悉场景中能自己采取不同做法",
    "E4": "在多种场景中稳定，压力下仍能维持大部分",
    "E5": "在高压与关系受伤时仍稳定，并能帮助他人",
}

# 阶段不是分数，也不是人格；任何展示都必须带情境、时间与置信度。
STAGE_IS_NOT = (
    "阶段不是分数，不能相加，也不能与其他用户比较。",
    "阶段描述的是当前一段时间的表现，不是你这个人。",
    "情感成熟不等于属灵成熟，本系统不评估救恩、圣灵同在或神的评价。",
)


# ─────────────────────────────────────────────────────────────────────────────
# 同意、证据与置信度
# ─────────────────────────────────────────────────────────────────────────────

CONSENT_SCOPES: dict[str, str] = {
    "EMD_SELF_ASSESSMENT": "进行一次性的私人情感成熟度自评",
    "EMD_BEHAVIOR_EVIDENCE": "记录并使用最近真实行为作为证据",
    "EMD_LONGITUDINAL_TWIN": "把结果写入 Formation Twin 并长期复测",
    "EMD_PASTORAL_SHARE": "把逐字段确认后的脱敏摘要分享给牧养人员",
    "EMD_MODEL_ASSIST": "允许模型辅助整理开放文本（不参与最终评分）",
}
REQUIRED_CONSENT_SCOPES: tuple[str, ...] = ("EMD_SELF_ASSESSMENT",)
INDEPENDENTLY_WITHDRAWABLE: tuple[str, ...] = tuple(CONSENT_SCOPES)

EVIDENCE_KINDS: dict[str, float] = {
    "SELF_DESCRIPTION": 1.0,
    "SCENARIO_RESPONSE": 1.5,
    "RECENT_BEHAVIOR": 2.0,
    "TRAINING_TRANSFER": 2.5,
    "REAL_LIFE_EVENT": 3.0,
    "USER_CORRECTION": 0.0,
}
BEHAVIOR_EVIDENCE_KINDS: frozenset[str] = frozenset({"RECENT_BEHAVIOR", "REAL_LIFE_EVENT", "TRAINING_TRANSFER"})
REAL_EVIDENCE_KINDS: frozenset[str] = frozenset({"RECENT_BEHAVIOR", "REAL_LIFE_EVENT"})

EVIDENCE_CONTEXTS: frozenset[str] = frozenset({
    "FAMILY", "CLOSE_RELATIONSHIP", "WORK", "CHURCH", "FRIENDSHIP", "SELF", "OTHER",
})

CONFIDENCE_LEVELS: tuple[str, ...] = ("INSUFFICIENT", "PROVISIONAL", "MODERATE", "HIGHER")
CONFIDENCE_RANK: dict[str, int] = {level: index for index, level in enumerate(CONFIDENCE_LEVELS)}

EVIDENCE_FRESHNESS_DAYS = 180
STAGE_CAP_SELF_REPORT_ONLY = "E2"
STAGE_CAP_WITHOUT_REAL_EVENT = "E3"
STAGE_CAP_LOW_VALIDITY = "E3"

SAFETY_LEVELS: tuple[str, ...] = ("NONE", "CONCERN", "ELEVATED", "IMMINENT")
SAFETY_RANK: dict[str, int] = {level: index for index, level in enumerate(SAFETY_LEVELS)}
ASSESSMENT_BLOCKING_SAFETY: frozenset[str] = frozenset({"ELEVATED", "IMMINENT"})


# ─────────────────────────────────────────────────────────────────────────────
# 输出安全护栏
# ─────────────────────────────────────────────────────────────────────────────

PROHIBITED_KEYS: frozenset[str] = frozenset({
    "emotional_maturity_total_score", "maturity_total", "spiritual_maturity_score",
    "spiritual_rank", "maturity_percentile", "personality_type", "attachment_diagnosis",
    "clinical_diagnosis", "salvation_status", "holy_spirit_status", "sin_score",
    "obedience_score", "leader_eligibility", "ordination_readiness", "peer_ranking",
    "journal_text", "prayer_text", "confession_text", "crisis_text", "raw_narrative",
    "third_party_identity", "family_member_diagnosis",
})

PROHIBITED_PHRASES: tuple[str, ...] = (
    "情感成熟总分", "属灵成熟总分", "成熟度百分比", "情感成熟排名",
    "你就是回避型人格", "你是自恋型", "你患有", "你被诊断为",
    "神告诉你", "神正在告诉你", "这是神对你的评价", "圣灵已经离开",
    "你不够属灵", "比其他弟兄姊妹更成熟", "你必须立刻原谅", "你必须恢复这段关系",
    "你小时候一定", "你一定曾经被", "真正成熟的基督徒不会",
    "emotional maturity score", "maturity ranking", "you are a narcissist",
    "god is telling you", "you must forgive now",
)
_PROHIBITED_RE = tuple(re.compile(re.escape(phrase), re.IGNORECASE) for phrase in PROHIBITED_PHRASES)


class UnsafeContentError(ValueError):
    """Raised when generated user-visible text violates EMD-OS output rules."""


# 标记与脚本：EMD 的开放文本会出现在群体反馈、牧养摘要与报告里，
# 那些地方是要被渲染的。红队用例 REPORT_INJECTION 就是打这里。
_MARKUP_PATTERNS: tuple[tuple[str, str], ...] = (
    ("SCRIPT_TAG", r"(?i)<\s*/?\s*script\b"),
    ("IFRAME_OR_OBJECT", r"(?i)<\s*/?\s*(iframe|object|embed|applet)\b"),
    ("EVENT_HANDLER", r"(?i)\bon(error|load|click|mouseover|focus)\s*="),
    ("JS_URI", r"(?i)(javascript|vbscript|data)\s*:\s*[^\s]"),
    ("HTML_TAG", r"<\s*/?\s*[a-zA-Z][a-zA-Z0-9]*(\s[^<>]*)?>"),
    ("TEMPLATE_EXPRESSION", r"\{\{.*?\}\}|\$\{.*?\}"),
)
_MARKUP_RE: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (code, re.compile(pattern)) for code, pattern in _MARKUP_PATTERNS
)


def validate_safe_text(text: str) -> str:
    """Fail closed on markup, ranking, diagnosis, divine-verdict and coercion wording."""
    value = text or ""
    for code, pattern in _MARKUP_RE:
        if pattern.search(value):
            raise UnsafeContentError(f"markup is not allowed in emotional-maturity text: {code}")
    for pattern in _PROHIBITED_RE:
        if pattern.search(value):
            raise UnsafeContentError(f"prohibited emotional-maturity phrasing: {pattern.pattern}")
    result = review_generated_text(value)
    if not result.ok:
        raise UnsafeContentError("formation safety blocked: " + ",".join(item["code"] for item in result.flags))
    return value


def sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Drop forbidden keys anywhere in an outbound payload."""

    def scrub(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: scrub(item) for key, item in value.items() if key not in PROHIBITED_KEYS}
        if isinstance(value, list):
            return [scrub(item) for item in value]
        return value

    return scrub(payload)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware datetime required")
    return value


def _now(now: datetime | None = None) -> datetime:
    return _aware(now) if now else datetime.now(timezone.utc)


def _hash(payload: dict[str, Any]) -> str:
    serializable = json.loads(json.dumps(payload, default=str))
    return hashlib.sha256(json.dumps(serializable, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _cap_stage(stage: str, ceiling: str) -> str:
    return stage if STAGE_RANK[stage] <= STAGE_RANK[ceiling] else ceiling


# ─────────────────────────────────────────────────────────────────────────────
# 契约
# ─────────────────────────────────────────────────────────────────────────────

class EvidenceReference(BaseModel):
    reference_type: str = Field(min_length=1, max_length=80)
    reference_id: str = Field(min_length=1, max_length=160)
    independence_group: str | None = Field(default=None, max_length=160)


class ConsentRequest(BaseModel):
    """EM-01 input."""

    requested_scopes: list[str] = Field(min_length=1, max_length=8)
    granted_scopes: list[str] = Field(default_factory=list, max_length=8)
    policy_version: str = Field(default="emd-consent-1.0", max_length=32)
    user_acknowledged_limits: bool = False
    is_minor: bool = False
    locale: str = Field(default="zh-CN", max_length=16)

    @field_validator("requested_scopes", "granted_scopes")
    @classmethod
    def known_scopes(cls, value: list[str]) -> list[str]:
        unknown = [scope for scope in value if scope not in CONSENT_SCOPES]
        if unknown:
            raise ValueError(f"unknown consent scope: {','.join(unknown)}")
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def granted_subset(self):
        extra = set(self.granted_scopes) - set(self.requested_scopes)
        if extra:
            raise ValueError("granted scope was never requested")
        return self


class EvidenceItem(BaseModel):
    """EM-04 normalized evidence unit. Raw narrative never enters this object."""

    evidence_id: str = Field(min_length=1, max_length=160)
    dimension_code: str
    evidence_kind: str
    context: str = "OTHER"
    stage_signal: str
    occurred_at: datetime
    recorded_at: datetime
    statement_type: Literal[
        "USER_REPORTED_FACT", "USER_CONFIRMED_INTERPRETATION", "OBSERVED_EVENT", "SCENARIO_RESPONSE",
    ] = "USER_REPORTED_FACT"
    user_confirmed: bool = True
    self_rated: bool = False
    independence_group: str | None = Field(default=None, max_length=160)
    behavior_summary: str = Field(default="", max_length=240)
    references: list[EvidenceReference] = Field(default_factory=list, max_length=8)
    excluded: bool = False
    exclusion_reason: str | None = Field(default=None, max_length=120)

    @field_validator("dimension_code")
    @classmethod
    def known_dimension(cls, value: str) -> str:
        if value not in DIMENSION_BY_CODE:
            raise ValueError(f"unknown dimension: {value}")
        return value

    @field_validator("evidence_kind")
    @classmethod
    def known_kind(cls, value: str) -> str:
        if value not in EVIDENCE_KINDS:
            raise ValueError(f"unknown evidence kind: {value}")
        return value

    @field_validator("stage_signal")
    @classmethod
    def known_stage(cls, value: str) -> str:
        if value not in STAGE_RANK:
            raise ValueError(f"unknown stage signal: {value}")
        return value

    @field_validator("context")
    @classmethod
    def known_context(cls, value: str) -> str:
        if value not in EVIDENCE_CONTEXTS:
            raise ValueError(f"unknown context: {value}")
        return value

    @model_validator(mode="after")
    def validate_evidence(self):
        _aware(self.occurred_at)
        _aware(self.recorded_at)
        if self.recorded_at < self.occurred_at:
            raise ValueError("evidence cannot be recorded before it occurred")
        if self.behavior_summary:
            validate_safe_text(self.behavior_summary)
        if self.evidence_kind in REAL_EVIDENCE_KINDS and not self.behavior_summary:
            raise ValueError("real behavior evidence requires an observable behavior summary")
        return self

    @property
    def weight(self) -> float:
        return EVIDENCE_KINDS[self.evidence_kind]

    def is_fresh(self, now: datetime, *, days: int = EVIDENCE_FRESHNESS_DAYS) -> bool:
        return (now - self.occurred_at) <= timedelta(days=days)


class DimensionSnapshot(BaseModel):
    dimension_code: str
    dimension_name: str
    stage: str
    stage_label: str
    confidence: str
    evidence_count: int
    evidence_weight: float
    evidence_kinds: list[str]
    contexts: list[str]
    context_differences: list[dict[str, Any]] = Field(default_factory=list)
    caps_applied: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    user_review_status: Literal["PENDING", "USER_CONFIRMED", "USER_DISPUTED", "USER_CORRECTED"] = "PENDING"
    computed_at: datetime
    rule_version: str = RULE_VERSION
    model_version: str = MODEL_VERSION


# ─────────────────────────────────────────────────────────────────────────────
# EM-01 emotional_maturity_consent_gate
# ─────────────────────────────────────────────────────────────────────────────

def run_consent_gate(request: ConsentRequest, *, now: datetime | None = None) -> dict[str, Any]:
    """Decide whether an assessment may start at all, and with what scope."""
    moment = _now(now)
    missing = [scope for scope in REQUIRED_CONSENT_SCOPES if scope not in request.granted_scopes]
    blocks: list[str] = []
    if missing:
        blocks.append("REQUIRED_CONSENT_MISSING")
    if not request.user_acknowledged_limits:
        blocks.append("LIMITS_NOT_ACKNOWLEDGED")
    if request.is_minor:
        blocks.append("MINOR_REQUIRES_SEPARATE_CERTIFICATION")

    decision = "BLOCKED" if blocks else "GRANTED"
    allowed = list(request.granted_scopes) if decision == "GRANTED" else []
    payload = {
        "consent_gate_id": str(uuid.uuid4()),
        "decision": decision,
        "granted_scopes": allowed,
        "declined_scopes": [scope for scope in request.requested_scopes if scope not in allowed],
        "missing_required_scopes": missing,
        "blocks": blocks,
        "withdrawable_scopes": list(INDEPENDENTLY_WITHDRAWABLE),
        "policy_version": request.policy_version,
        "disclosures": [
            "这是私人自我反思工具，不是临床评估，也不是属灵评判。",
            "情感成熟不等于属灵成熟；本系统不评估救恩、圣灵同在或神对你的评价。",
            "你随时可以跳过任何题目、修正结论、撤回任一项授权或删除数据。",
            "拒绝分享类授权不会影响私人核心功能。",
        ],
        "next_action": "SAFETY_TRIAGE" if decision == "GRANTED" else "SHOW_CONSENT_EXPLANATION",
        "decided_at": moment,
        "engine_version": ENGINE_VERSION,
    }
    payload["input_hash"] = _hash(payload)
    return payload


def withdraw_consent(granted_scopes: list[str], scope: str) -> dict[str, Any]:
    """Every scope is independently withdrawable; core private use survives."""
    if scope not in CONSENT_SCOPES:
        raise ValueError(f"unknown consent scope: {scope}")
    remaining = [item for item in granted_scopes if item != scope]
    consequences: list[str] = []
    if scope == "EMD_LONGITUDINAL_TWIN":
        consequences.append("停止写入 Formation Twin 并暂停复测排程。")
    if scope == "EMD_PASTORAL_SHARE":
        consequences.append("已生成的牧养摘要立即失效，分享链接停用。")
    if scope == "EMD_BEHAVIOR_EVIDENCE":
        consequences.append("真实行为证据不再参与评分，相关维度置信度会下降。")
    if scope == "EMD_SELF_ASSESSMENT":
        consequences.append("评估流程停止；已有结论标记为不再更新。")
    return {
        "withdrawn_scope": scope,
        "remaining_scopes": remaining,
        "private_core_still_available": "EMD_SELF_ASSESSMENT" in remaining,
        "consequences": consequences,
        "recompute_required": scope in {"EMD_BEHAVIOR_EVIDENCE", "EMD_LONGITUDINAL_TWIN"},
        "next_action": "RECOMPUTE_PROFILE" if scope in {"EMD_BEHAVIOR_EVIDENCE"} else "UPDATE_CONSENT_STATE",
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-02 emotional_safety_triage_router
# ─────────────────────────────────────────────────────────────────────────────

_ABUSE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("INTIMATE_PARTNER_VIOLENCE", r"打我|动手|掐我|推我|家暴|威胁要杀|不让我出门|抢走我的(手机|证件)"),
    ("COERCIVE_CONTROL", r"监控我|查我手机|不准我(见|联系)|控制我的钱|不让我工作"),
    ("CHURCH_POWER_HARM", r"(牧师|长老|小组长).{0,8}(威胁|羞辱|封口|不准我说|要我顺服他)"),
    ("MEDICAL_RED_FLAG", r"胸痛|呼吸困难|喘不上气|昏倒|吐血|胸口压着"),
)
_ABUSE_RE = tuple((code, re.compile(pattern)) for code, pattern in _ABUSE_PATTERNS)

# 生命风险的直接表达。crisis_engine 是第一道判断，这里只做「只能抬高、不能降低」的兜底，
# 避免措辞变化时整条链路静默退化为普通评估。
_LIFE_RISK_PATTERNS: tuple[tuple[str, str, str], ...] = (
    ("SELF_HARM_URGE", r"(想|要)(伤害|弄伤|伤)(一下)?(我)?自己|自残|不想活|活不下去|结束这一切|想死(?![你我])", "IMMINENT"),
    ("HARM_TO_OTHERS_URGE", r"想(杀|弄死|捅)(了)?(他|她|他们|你)|想(把.{0,6})?(杀|弄死)", "IMMINENT"),
    ("LIFE_THREAT_FROM_OTHER", r"(威胁|说)(过)?.{0,10}(杀了我|要我的命|弄死我)|掐(我的)?脖子|拿刀", "ELEVATED"),
)
_LIFE_RISK_RE = tuple(
    (code, re.compile(pattern), level) for code, pattern, level in _LIFE_RISK_PATTERNS
)

_CRISIS_LEVEL_MAP = {"green": "NONE", "yellow": "CONCERN", "orange": "ELEVATED", "red": "IMMINENT"}


def _external_triage(text: str) -> dict[str, Any] | None:
    try:  # reuse the shipped crisis engine; never re-implement crisis detection
        import crisis_engine  # type: ignore
    except Exception:  # pragma: no cover - engine always present in app runtime
        try:
            from backend import crisis_engine  # type: ignore
        except Exception:
            return None
    try:
        return crisis_engine.triage(text)
    except Exception:  # pragma: no cover - defensive
        return None


def run_safety_triage(
    *,
    free_text: str = "",
    self_reported_flags: list[str] | None = None,
    prior_safety_level: str = "NONE",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Route to care before assessment. Risk may only be escalated, never lowered."""
    moment = _now(now)
    text = free_text or ""
    level = prior_safety_level if prior_safety_level in SAFETY_RANK else "NONE"
    signals: list[dict[str, str]] = []

    external = _external_triage(text)
    if external:
        mapped = _CRISIS_LEVEL_MAP.get(str(external.get("riskLevel") or "green"), "NONE")
        if SAFETY_RANK[mapped] > SAFETY_RANK[level]:
            level = mapped
        for risk_type in external.get("riskTypes") or []:
            signals.append({"code": str(risk_type).upper(), "source": "crisis_engine"})

    for code, pattern in _ABUSE_RE:
        if pattern.search(text):
            signals.append({"code": code, "source": "emd_rules"})
            if code == "MEDICAL_RED_FLAG" and SAFETY_RANK["ELEVATED"] > SAFETY_RANK[level]:
                level = "ELEVATED"
            elif SAFETY_RANK["CONCERN"] > SAFETY_RANK[level]:
                level = "CONCERN"

    for code, pattern, minimum in _LIFE_RISK_RE:
        if pattern.search(text):
            signals.append({"code": code, "source": "emd_life_risk_backstop"})
            if SAFETY_RANK[minimum] > SAFETY_RANK[level]:
                level = minimum

    for flag in self_reported_flags or []:
        code = str(flag).upper()
        signals.append({"code": code, "source": "user_reported"})
        if code in {"SUICIDAL_IDEATION", "SELF_HARM", "HARM_TO_OTHERS"}:
            level = "IMMINENT"
        elif code in {"PARTNER_VIOLENCE", "ABUSE", "MEDICAL_EMERGENCY"} and SAFETY_RANK["ELEVATED"] > SAFETY_RANK[level]:
            level = "ELEVATED"

    codes = {item["code"] for item in signals}
    blocked = level in ASSESSMENT_BLOCKING_SAFETY
    relationship_safety = "CAUTION" if codes & {
        "INTIMATE_PARTNER_VIOLENCE", "COERCIVE_CONTROL", "CHURCH_POWER_HARM", "PARTNER_VIOLENCE",
        "ABUSE", "LIFE_THREAT_FROM_OTHER", "DOMESTIC_VIOLENCE",
    } else "STANDARD"

    restrictions: list[str] = []
    if relationship_safety == "CAUTION":
        restrictions += [
            "不得建议直接对质、深度脆弱披露或恢复联系。",
            "关系修复类维度只做安全优先的观察，不给出修复行动。",
        ]
    if "MEDICAL_RED_FLAG" in codes:
        restrictions.append("不得把身体症状解释为情绪问题，先提示身体安全评估。")

    payload = {
        "triage_id": str(uuid.uuid4()),
        "safety_level": level,
        "signals": sorted(signals, key=lambda item: item["code"]),
        "assessment_allowed": not blocked,
        "relationship_safety": relationship_safety,
        "route": "CRISIS_CARE" if blocked else ("CARE_FIRST" if level == "CONCERN" else "ASSESSMENT"),
        "route_target": "/api/crisis/triage" if blocked else None,
        "restrictions": restrictions,
        "limitations": [
            "本分流不是临床评估，也不能替代紧急服务。",
            "系统只根据你主动提供的信息判断，可能遗漏其他风险。",
        ],
        "next_action": "ROUTE_TO_CRISIS_CARE" if blocked else "BUILD_INTAKE",
        "triaged_at": moment,
        "engine_version": ENGINE_VERSION,
        "rule_version": RULE_VERSION,
    }
    payload["input_hash"] = _hash(payload)
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# EM-03 emotional_assessment_intake_builder
# ─────────────────────────────────────────────────────────────────────────────

INTAKE_FIELDS: tuple[dict[str, Any], ...] = (
    {"key": "life_season", "label": "现在处在什么阶段", "optional": True, "kind": "CHOICE",
     "choices": ["相对平稳", "压力较大", "重大变动", "刚经历失去", "说不清"]},
    {"key": "main_contexts", "label": "最近情绪最常被触动的场景", "optional": True, "kind": "MULTI",
     "choices": sorted(EVIDENCE_CONTEXTS)},
    {"key": "sleep_recent", "label": "最近的睡眠大致如何", "optional": True, "kind": "CHOICE",
     "choices": ["还可以", "偏少", "很差", "不想回答"]},
    {"key": "support_available", "label": "现在身边有可以说话的人吗", "optional": True, "kind": "CHOICE",
     "choices": ["有", "有但不方便说", "几乎没有", "不想回答"]},
    {"key": "spiritual_framework", "label": "希望内容使用什么语言框架", "optional": True, "kind": "CHOICE",
     "choices": ["基督信仰语言", "中性语言", "让我自己选"]},
    {"key": "goal", "label": "你希望这次评估帮到你什么", "optional": True, "kind": "TEXT"},
)

INTAKE_FORBIDDEN_FIELDS: frozenset[str] = frozenset({
    "diagnosis_history", "medication", "childhood_trauma_detail", "third_party_name",
    "church_name", "partner_name", "abuse_detail", "confession_detail",
})


def build_intake(
    *,
    triage: dict[str, Any],
    submitted: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Collect only the context needed to interpret answers; everything is skippable."""
    moment = _now(now)
    if not triage.get("assessment_allowed", False):
        return {
            "intake_id": str(uuid.uuid4()),
            "status": "BLOCKED_BY_SAFETY",
            "fields": [],
            "accepted": {},
            "next_action": "ROUTE_TO_CRISIS_CARE",
            "built_at": moment,
        }
    provided = submitted or {}
    rejected = sorted(set(provided) & INTAKE_FORBIDDEN_FIELDS)
    accepted = {
        field["key"]: provided[field["key"]]
        for field in INTAKE_FIELDS
        if field["key"] in provided and provided[field["key"]] not in (None, "")
    }
    if isinstance(accepted.get("goal"), str):
        validate_safe_text(accepted["goal"])
    skipped = [field["key"] for field in INTAKE_FIELDS if field["key"] not in accepted]
    framework = accepted.get("spiritual_framework") or "让我自己选"
    payload = {
        "intake_id": str(uuid.uuid4()),
        "status": "READY",
        "fields": list(INTAKE_FIELDS),
        "accepted": accepted,
        "skipped_fields": skipped,
        "rejected_fields": rejected,
        "spiritual_framework": framework,
        "restrictions": list(triage.get("restrictions") or []),
        "notes": [
            "所有问题都可以跳过，跳过不会被解读为回避或不成熟。",
            "系统不收集诊断史、用药、第三方姓名或创伤细节。",
        ],
        "next_action": "SELECT_ASSESSMENT_ITEMS",
        "built_at": moment,
        "engine_version": ENGINE_VERSION,
    }
    payload["input_hash"] = _hash(payload)
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# EM-04 emotional_evidence_normalizer
# ─────────────────────────────────────────────────────────────────────────────

def normalize_evidence(
    raw_items: list[dict[str, Any]],
    *,
    consented_scopes: list[str],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Turn raw submissions into evidence units; drop bodies, dedupe, mark provenance."""
    moment = _now(now)
    accepted: list[EvidenceItem] = []
    rejected: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    behavior_allowed = "EMD_BEHAVIOR_EVIDENCE" in consented_scopes

    for raw in raw_items:
        payload = {key: value for key, value in (raw or {}).items() if key not in PROHIBITED_KEYS}
        kind = str(payload.get("evidence_kind") or "")
        if kind in REAL_EVIDENCE_KINDS and not behavior_allowed:
            rejected.append({"evidence_id": payload.get("evidence_id"), "reason": "BEHAVIOR_CONSENT_MISSING"})
            continue
        try:
            item = EvidenceItem(**payload)
        except (ValueError, TypeError) as exc:
            rejected.append({"evidence_id": payload.get("evidence_id"), "reason": "INVALID", "detail": str(exc)[:160]})
            continue
        identity = (item.dimension_code, item.evidence_kind, item.independence_group or item.evidence_id)
        if identity in seen:
            rejected.append({"evidence_id": item.evidence_id, "reason": "DUPLICATE"})
            continue
        seen.add(identity)
        accepted.append(item)

    stale = [item.evidence_id for item in accepted if not item.is_fresh(moment)]
    coverage = {code: 0 for code in DIMENSION_CODES}
    for item in accepted:
        if not item.excluded:
            coverage[item.dimension_code] += 1
    payload = {
        "normalization_id": str(uuid.uuid4()),
        "accepted": [item.model_dump(mode="json") for item in accepted],
        "rejected": rejected,
        "stale_evidence_ids": stale,
        "dimension_coverage": coverage,
        "dropped_body_fields": True,
        "provenance": {
            "normalization_version": "emd-evidence-normalizer-1.0",
            "statement_types": sorted({item.statement_type for item in accepted}),
        },
        "next_action": "ASSESS_DIMENSIONS",
        "normalized_at": moment,
        "engine_version": ENGINE_VERSION,
    }
    payload["input_hash"] = _hash(payload)
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# EM-05 adaptive_dimension_assessor
# ─────────────────────────────────────────────────────────────────────────────

REQUIRED_KINDS_PER_DIMENSION: tuple[str, ...] = ("SELF_DESCRIPTION", "RECENT_BEHAVIOR", "SCENARIO_RESPONSE")
MAX_ITEMS_PER_SESSION = 24
MAX_ITEMS_PER_DIMENSION = 6


def select_next_items(
    *,
    evidence: list[EvidenceItem],
    focus_dimensions: list[str] | None = None,
    answered_count: int = 0,
    fatigue_reported: bool = False,
    restrictions: list[str] | None = None,
) -> dict[str, Any]:
    """Choose the next few questions: widest gap first, three evidence kinds per dimension."""
    active = [item for item in evidence if not item.excluded]
    per_dimension: dict[str, set[str]] = {code: set() for code in DIMENSION_CODES}
    counts: dict[str, int] = {code: 0 for code in DIMENSION_CODES}
    for item in active:
        per_dimension[item.dimension_code].add(item.evidence_kind)
        counts[item.dimension_code] += 1

    candidates = focus_dimensions or list(DIMENSION_CODES)
    unsafe_relationship = any("对质" in text or "恢复联系" in text for text in (restrictions or []))

    gaps: list[dict[str, Any]] = []
    for code in candidates:
        if code not in DIMENSION_BY_CODE:
            continue
        missing = [kind for kind in REQUIRED_KINDS_PER_DIMENSION if kind not in per_dimension[code]]
        if not missing or counts[code] >= MAX_ITEMS_PER_DIMENSION:
            continue
        gaps.append({
            "dimension_code": code,
            "dimension_name": DIMENSION_BY_CODE[code]["name"],
            "missing_evidence_kinds": missing,
            "asked": counts[code],
        })
    gaps.sort(key=lambda item: (-len(item["missing_evidence_kinds"]), item["dimension_code"]))

    stop_reasons: list[str] = []
    if answered_count >= MAX_ITEMS_PER_SESSION:
        stop_reasons.append("SESSION_ITEM_LIMIT")
    if fatigue_reported:
        stop_reasons.append("USER_FATIGUE")
    if not gaps:
        stop_reasons.append("COVERAGE_SUFFICIENT")

    selected = [] if stop_reasons else gaps[:3]
    for item in selected:
        if unsafe_relationship and item["dimension_code"] in {"D9"}:
            item["scenario_restriction"] = "只做安全优先的观察题，不生成对质或修复行动。"
    return {
        "selection_id": str(uuid.uuid4()),
        "selected": selected,
        "remaining_gaps": gaps,
        "stop": bool(stop_reasons),
        "stop_reasons": stop_reasons,
        "skippable": True,
        "next_action": "SCORE_DIMENSIONS" if stop_reasons else "RENDER_ITEMS",
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-06 maturity_dimension_scorer
# ─────────────────────────────────────────────────────────────────────────────

def _confidence_for(items: list[EvidenceItem], now: datetime) -> tuple[str, float, list[str], list[str]]:
    fresh = [item for item in items if item.is_fresh(now)]
    weight = round(sum(item.weight for item in fresh), 2)
    kinds = sorted({item.evidence_kind for item in fresh})
    contexts = sorted({item.context for item in fresh})
    real_events = [item for item in fresh if item.evidence_kind == "REAL_LIFE_EVENT"]
    behavior = [item for item in fresh if item.evidence_kind in BEHAVIOR_EVIDENCE_KINDS]

    level = "INSUFFICIENT"
    if weight >= 3.0 and len(kinds) >= 2:
        level = "PROVISIONAL"
    if weight >= 6.0 and len(kinds) >= 3 and behavior:
        level = "MODERATE"
    if weight >= 10.0 and len(kinds) >= 3 and len(real_events) >= 2 and len(contexts) >= 2:
        level = "HIGHER"
    return level, weight, kinds, contexts


def score_dimension(
    dimension_code: str,
    evidence: list[EvidenceItem],
    *,
    validity_flags: list[str] | None = None,
    now: datetime | None = None,
) -> DimensionSnapshot:
    """Pick the highest stage supported by at least two independent evidence items."""
    if dimension_code not in DIMENSION_BY_CODE:
        raise ValueError(f"unknown dimension: {dimension_code}")
    moment = _now(now)
    items = [
        item for item in evidence
        if item.dimension_code == dimension_code and not item.excluded and item.evidence_kind != "USER_CORRECTION"
    ]
    fresh = [item for item in items if item.is_fresh(moment)]
    confidence, weight, kinds, contexts = _confidence_for(items, moment)
    caps: list[str] = []
    uncertainty: list[str] = []

    if confidence == "INSUFFICIENT" or not fresh:
        stage = "E0"
        uncertainty.append("现有证据不足以描述这个维度，这不代表你的能力低。")
    else:
        support: dict[str, list[EvidenceItem]] = {}
        for item in fresh:
            support.setdefault(item.stage_signal, []).append(item)
        stage = "E1"
        for candidate in reversed(STAGES[1:]):
            group = support.get(candidate, [])
            independent = {item.independence_group or item.evidence_id for item in group}
            if len(independent) >= 2:
                stage = candidate
                break
        else:
            highest = max((item.stage_signal for item in fresh), key=lambda value: STAGE_RANK[value])
            stage = "E1" if STAGE_RANK[highest] > STAGE_RANK["E2"] else highest
            uncertainty.append("只有单一证据支持较高阶段，已按更保守的阶段呈现。")

        if not any(item.evidence_kind in BEHAVIOR_EVIDENCE_KINDS for item in fresh):
            capped = _cap_stage(stage, STAGE_CAP_SELF_REPORT_ONLY)
            if capped != stage:
                caps.append("SELF_REPORT_ONLY")
                stage = capped
        elif not any(item.evidence_kind == "REAL_LIFE_EVENT" for item in fresh):
            capped = _cap_stage(stage, STAGE_CAP_WITHOUT_REAL_EVENT)
            if capped != stage:
                caps.append("NO_REAL_LIFE_EVENT")
                stage = capped
        if validity_flags:
            capped = _cap_stage(stage, STAGE_CAP_LOW_VALIDITY)
            if capped != stage:
                caps.append("RESPONSE_VALIDITY_CONCERN")
                stage = capped

    context_stage: dict[str, list[int]] = {}
    for item in fresh:
        context_stage.setdefault(item.context, []).append(STAGE_RANK[item.stage_signal])
    differences = [
        {"context": context, "observed_stage": STAGES[round(sum(values) / len(values))], "evidence_count": len(values)}
        for context, values in sorted(context_stage.items())
    ]
    if len({entry["observed_stage"] for entry in differences}) > 1:
        uncertainty.append("不同场景之间存在差异，这通常说明情境不同，而不是你在某处不真诚。")

    return DimensionSnapshot(
        dimension_code=dimension_code,
        dimension_name=DIMENSION_BY_CODE[dimension_code]["name"],
        stage=stage,
        stage_label=STAGE_LABELS[stage],
        confidence=confidence,
        evidence_count=len(fresh),
        evidence_weight=weight,
        evidence_kinds=kinds,
        contexts=contexts,
        context_differences=differences,
        caps_applied=caps,
        uncertainty=uncertainty,
        computed_at=moment,
    )


# ─────────────────────────────────────────────────────────────────────────────
# EM-07 response_validity_and_bias_auditor
# ─────────────────────────────────────────────────────────────────────────────

RUBRIC_PHRASES: tuple[str, ...] = (
    "我会先暂停，命名情绪，再选择回应",
    "我承担我的部分并做出具体补偿",
    "我保持好奇而不是归罪",
)


def audit_response_validity(
    responses: list[dict[str, Any]],
    evidence: list[EvidenceItem],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Detect social desirability, acquiescence, rubric copying, speeding and fatigue."""
    moment = _now(now)
    flags: list[dict[str, str]] = []
    self_rated = [item for item in responses if item.get("self_rating") is not None]
    ratings = [float(item["self_rating"]) for item in self_rated]
    behavior = [item for item in evidence if item.evidence_kind in BEHAVIOR_EVIDENCE_KINDS and not item.excluded]

    if ratings and min(ratings) >= 0.8 and not behavior:
        flags.append({"code": "SOCIAL_DESIRABILITY", "severity": "MEDIUM"})
    if len(ratings) >= 5 and len(set(ratings)) == 1:
        flags.append({"code": "ACQUIESCENCE", "severity": "MEDIUM"})

    durations = [float(item["duration_ms"]) for item in responses if item.get("duration_ms") is not None]
    if durations and sum(1 for value in durations if value < 1500) >= max(3, len(durations) // 2):
        flags.append({"code": "SPEEDING", "severity": "LOW"})
    if len(durations) >= 8:
        first_half = durations[: len(durations) // 2]
        second_half = durations[len(durations) // 2 :]
        if sum(second_half) / len(second_half) < 0.4 * (sum(first_half) / len(first_half)):
            flags.append({"code": "ASSESSMENT_FATIGUE", "severity": "LOW"})

    for item in responses:
        text = str(item.get("text") or "")
        if any(phrase in text for phrase in RUBRIC_PHRASES):
            flags.append({"code": "RUBRIC_LANGUAGE_COPIED", "severity": "MEDIUM"})
            break

    self_stage = [STAGE_RANK[item.stage_signal] for item in evidence if item.self_rated and not item.excluded]
    behavior_stage = [STAGE_RANK[item.stage_signal] for item in behavior]
    if self_stage and behavior_stage:
        gap = (sum(self_stage) / len(self_stage)) - (sum(behavior_stage) / len(behavior_stage))
        if gap >= 1.5:
            flags.append({"code": "SELF_REPORT_BEHAVIOR_GAP", "severity": "HIGH"})

    codes = [item["code"] for item in flags]
    return {
        "validity_audit_id": str(uuid.uuid4()),
        "flags": flags,
        "flag_codes": codes,
        "cap_stage_required": any(item["severity"] in {"MEDIUM", "HIGH"} for item in flags),
        "user_visible_notes": [
            "这些只是作答模式的提醒，不是说你不诚实。",
            "短的回答不会因为字少而被评低。",
        ],
        "not_allowed_interpretation": [
            "不得把作答模式解释为人格特质。",
            "不得把语言能力当作成熟度。",
        ],
        "audited_at": moment,
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-08 emotional_maturity_profile_synthesizer
# ─────────────────────────────────────────────────────────────────────────────

def synthesize_profile(
    snapshots: list[DimensionSnapshot],
    *,
    triage: dict[str, Any] | None = None,
    validity: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Compose a per-dimension picture. There is no single maturity score, ever."""
    moment = _now(now)
    rated = [item for item in snapshots if item.confidence != "INSUFFICIENT" and item.stage != "E0"]
    ordered = sorted(rated, key=lambda item: (STAGE_RANK[item.stage], -CONFIDENCE_RANK[item.confidence]))
    strengths = [item for item in reversed(ordered)][:2]
    invitations = ordered[:2]
    unrated = [item for item in snapshots if item not in rated]

    payload = {
        "profile_id": str(uuid.uuid4()),
        "model_version": MODEL_VERSION,
        "dimensions": [item.model_dump(mode="json") for item in snapshots],
        "current_strengths": [
            {"dimension_code": item.dimension_code, "dimension_name": item.dimension_name,
             "stage": item.stage, "confidence": item.confidence}
            for item in strengths
        ],
        "growth_invitations": [
            {"dimension_code": item.dimension_code, "dimension_name": item.dimension_name,
             "stage": item.stage, "confidence": item.confidence,
             "why": "这个维度目前证据支持的阶段最低，也最可能带来实际改变。"}
            for item in invitations
        ],
        "insufficient_evidence_dimensions": [item.dimension_code for item in unrated],
        "total_score": None,
        "spiritual_maturity_claim": None,
        "context_note": "同一个人在家庭、职场与教会中的表现可以不同，这是情境差异而不是虚伪。",
        "validity_flags": list((validity or {}).get("flag_codes") or []),
        "safety_level": str((triage or {}).get("safety_level") or "NONE"),
        "relationship_safety": str((triage or {}).get("relationship_safety") or "STANDARD"),
        "limitations": [
            *STAGE_IS_NOT,
            "本结果只描述现有证据支持的表现，不构成临床或属灵诊断。",
            "你可以对任何一条结论提出异议，异议会保留并触发重新评估。",
        ],
        "user_review_status": "PENDING",
        "next_action": "PLAN_GROWTH_ROUTE",
        "synthesized_at": moment,
        "engine_version": ENGINE_VERSION,
    }
    payload = sanitize_payload(payload)
    payload["input_hash"] = _hash(payload)
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# EM-09 emotional_growth_route_planner
# ─────────────────────────────────────────────────────────────────────────────

CHECKPOINT_DAYS: tuple[int, ...] = (14, 30, 90)

SAFETY_FIRST_ROUTE: dict[str, Any] = {
    "route_type": "CARE_FIRST",
    "modules": ["crisis", "care", "pastoral"],
    "routes": ["/api/crisis/triage", "/api/care", "/api/pastoral"],
    "note": "安全与照顾优先于任何训练；训练路由暂不生成。",
}


def plan_growth_route(
    profile: dict[str, Any],
    *,
    max_dimensions: int = 2,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Route into the existing training engines; never invent a new intervention."""
    moment = _now(now)
    safety_level = str(profile.get("safety_level") or "NONE")
    relationship_safety = str(profile.get("relationship_safety") or "STANDARD")
    if safety_level in ASSESSMENT_BLOCKING_SAFETY:
        return {
            "route_id": str(uuid.uuid4()),
            "schema_version": ROUTING_SCHEMA_VERSION,
            "assignments": [],
            **SAFETY_FIRST_ROUTE,
            "checkpoints": [],
            "next_action": "ROUTE_TO_CRISIS_CARE",
            "planned_at": moment,
        }

    invitations = list(profile.get("growth_invitations") or [])[:max_dimensions]
    assignments: list[dict[str, Any]] = []
    for invitation in invitations:
        code = str(invitation.get("dimension_code"))
        dimension = DIMENSION_BY_CODE.get(code)
        if not dimension:
            continue
        restrictions: list[str] = []
        if relationship_safety == "CAUTION" and code in {"D6", "D9"}:
            restrictions = [
                "在关系安全存疑时，本维度只做自我保护与观察，不建议对质、披露或恢复联系。",
            ]
        assignments.append({
            "dimension_code": code,
            "dimension_name": dimension["name"],
            "current_stage": invitation.get("stage"),
            "confidence": invitation.get("confidence"),
            "training_modules": dimension["training_modules"],
            "training_routes": dimension["training_routes"],
            "practice_size": "one_small_step",
            "restrictions": restrictions,
        })

    checkpoints = [
        {
            "day": day,
            "due_at": moment + timedelta(days=day),
            "goal": {
                14: "技能获得与第一次应用",
                30: "初步稳定与模式打断",
                90: "维持、跨场景泛化与整合",
            }[day],
            "evidence_requested": ["RECENT_BEHAVIOR", "REAL_LIFE_EVENT"] if day > 14 else ["RECENT_BEHAVIOR"],
        }
        for day in CHECKPOINT_DAYS
    ]

    payload = {
        "route_id": str(uuid.uuid4()),
        "schema_version": ROUTING_SCHEMA_VERSION,
        "route_type": "TRAINING",
        "assignments": assignments,
        "max_dimensions": max_dimensions,
        "checkpoints": checkpoints,
        "declined_allowed": True,
        "limitations": [
            "路由只推荐已有模块，不生成新的心理干预。",
            "你可以拒绝任何一条建议，拒绝不会降低你的阶段。",
        ],
        "next_action": "SCHEDULE_REASSESSMENT",
        "planned_at": moment,
        "engine_version": ENGINE_VERSION,
    }
    payload["input_hash"] = _hash(payload)
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# EM-10 profile_correction_and_reassessment
# ─────────────────────────────────────────────────────────────────────────────

CORRECTION_TYPES: frozenset[str] = frozenset({
    "DISPUTE_STAGE", "EXCLUDE_EVIDENCE", "CORRECT_CONTEXT", "ADD_EVIDENCE", "DECLINE_DIMENSION",
})


def apply_correction(
    snapshot: DimensionSnapshot,
    evidence: list[EvidenceItem],
    correction: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """User correction always wins over the engine; the old snapshot is superseded, not deleted."""
    moment = _now(now)
    correction_type = str(correction.get("correction_type") or "")
    if correction_type not in CORRECTION_TYPES:
        raise ValueError(f"unknown correction type: {correction_type}")
    note = str(correction.get("user_note") or "")
    if note:
        validate_safe_text(note)

    working = list(evidence)
    if correction_type == "EXCLUDE_EVIDENCE":
        target = str(correction.get("evidence_id") or "")
        working = [
            item.model_copy(update={"excluded": True, "exclusion_reason": "USER_EXCLUDED"})
            if item.evidence_id == target else item
            for item in working
        ]
    elif correction_type == "CORRECT_CONTEXT":
        target = str(correction.get("evidence_id") or "")
        context = str(correction.get("context") or "OTHER")
        if context not in EVIDENCE_CONTEXTS:
            raise ValueError(f"unknown context: {context}")
        working = [
            item.model_copy(update={"context": context}) if item.evidence_id == target else item
            for item in working
        ]

    if correction_type == "DECLINE_DIMENSION":
        recomputed = snapshot.model_copy(update={
            "stage": "E0", "stage_label": STAGE_LABELS["E0"], "confidence": "INSUFFICIENT",
            "user_review_status": "USER_CORRECTED", "computed_at": moment,
            "uncertainty": ["用户选择不评估这个维度。"],
        })
    else:
        recomputed = score_dimension(snapshot.dimension_code, working, now=moment)
        status = "USER_DISPUTED" if correction_type == "DISPUTE_STAGE" else "USER_CORRECTED"
        recomputed = recomputed.model_copy(update={"user_review_status": status})

    return {
        "correction_id": str(uuid.uuid4()),
        "correction_type": correction_type,
        "superseded_snapshot": snapshot.model_dump(mode="json"),
        "snapshot": recomputed.model_dump(mode="json"),
        "evidence": [item.model_dump(mode="json") for item in working],
        "user_note_retained": bool(note),
        "twin_update_allowed": correction_type != "DISPUTE_STAGE",
        "notes": [
            "你的修正会被保留；系统不会覆盖你自己的说法。",
            "有异议的结论不会被写入 Formation Twin。",
        ],
        "next_action": "SCHEDULE_REASSESSMENT",
        "corrected_at": moment,
    }


def schedule_reassessment(
    profile: dict[str, Any],
    *,
    consented_scopes: list[str],
    now: datetime | None = None,
) -> dict[str, Any]:
    """14/30/90-day re-measurement. Without longitudinal consent nothing is scheduled."""
    moment = _now(now)
    if "EMD_LONGITUDINAL_TWIN" not in consented_scopes:
        return {
            "plan_id": str(uuid.uuid4()),
            "status": "NOT_SCHEDULED",
            "reason": "LONGITUDINAL_CONSENT_MISSING",
            "checkpoints": [],
            "next_action": "OFFER_LONGITUDINAL_CONSENT",
            "planned_at": moment,
        }
    dimensions = [item.get("dimension_code") for item in (profile.get("growth_invitations") or [])]
    return {
        "plan_id": str(uuid.uuid4()),
        "status": "SCHEDULED",
        "dimensions": dimensions,
        "checkpoints": [
            {"day": day, "due_at": moment + timedelta(days=day), "window_days": 3, "skippable": True}
            for day in CHECKPOINT_DAYS
        ],
        "comparability_requirements": [
            "复测必须使用同一 Rubric 版本，否则结果标记为不可比。",
            "变化小于测量误差时只显示『无法确认变化』。",
        ],
        "next_action": "UPDATE_FORMATION_TWIN",
        "planned_at": moment,
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 状态机、事件与数据质量
# ─────────────────────────────────────────────────────────────────────────────

STATE_MACHINE: tuple[tuple[str, str], ...] = (
    ("CONSENT_REQUESTED", "CONSENT_GRANTED"),
    ("CONSENT_REQUESTED", "CONSENT_BLOCKED"),
    ("CONSENT_GRANTED", "SAFETY_TRIAGED"),
    ("SAFETY_TRIAGED", "ROUTED_TO_CRISIS"),
    ("SAFETY_TRIAGED", "INTAKE_BUILT"),
    ("INTAKE_BUILT", "ASSESSING"),
    ("ASSESSING", "EVIDENCE_NORMALIZED"),
    ("EVIDENCE_NORMALIZED", "SCORED"),
    ("SCORED", "PROFILE_SYNTHESIZED"),
    ("PROFILE_SYNTHESIZED", "ROUTE_PLANNED"),
    ("ROUTE_PLANNED", "REASSESSMENT_SCHEDULED"),
    ("PROFILE_SYNTHESIZED", "USER_CORRECTED"),
    ("USER_CORRECTED", "PROFILE_SYNTHESIZED"),
    ("REASSESSMENT_SCHEDULED", "TWIN_UPDATED"),
)

WORKFLOW_NODES: tuple[str, ...] = (
    "EM-01_consent_gate", "EM-02_safety_triage", "EM-03_intake_builder",
    "EM-04_evidence_normalizer", "EM-05_dimension_assessor", "EM-06_dimension_scorer",
    "EM-07_validity_auditor", "EM-08_profile_synthesizer", "EM-09_growth_route_planner",
    "EM-10_correction_and_reassessment",
)

PUBLISHED_EVENTS: frozenset[str] = frozenset({
    "emd.consent_updated", "emd.safety_routed", "emd.assessment_started",
    "emd.profile_synthesized", "emd.route_planned", "emd.profile_corrected",
    "emd.reassessment_scheduled", "emd.data_erased",
})
CONSUMED_EVENTS: frozenset[str] = frozenset({
    "formation_twin.checkin_updated", "formation_twin.consent_updated",
    "crisis.status_changed", "formation_twin.protection_recovery_started",
})

EVENT_ALLOWED_FIELDS: frozenset[str] = frozenset({
    "profile_id", "route_id", "plan_id", "correction_id", "triage_id", "dimension_code",
    "stage", "confidence", "safety_level", "status", "engine_version", "rule_version",
})


def sanitize_event(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    if event_type not in PUBLISHED_EVENTS:
        raise ValueError("unregistered EMD-OS event")
    return {key: value for key, value in payload.items() if key in EVENT_ALLOWED_FIELDS}


def emd_data_quality(
    *,
    consent_records: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
) -> dict[str, Any]:
    """Deterministic Batch 1 data-quality checks. Critical findings block release."""
    findings: list[dict[str, Any]] = []
    if not consent_records:
        findings.append({"severity": "CRITICAL", "code": "NO_CONSENT_RECORD"})
    scoped = {scope for record in consent_records for scope in (record.get("granted_scopes") or [])}
    behavior_items = [item for item in evidence if item.get("evidence_kind") in REAL_EVIDENCE_KINDS]
    if behavior_items and "EMD_BEHAVIOR_EVIDENCE" not in scoped:
        findings.append({"severity": "CRITICAL", "code": "BEHAVIOR_EVIDENCE_WITHOUT_CONSENT", "count": len(behavior_items)})

    seen: set[tuple[Any, Any, Any]] = set()
    duplicates = 0
    for item in evidence:
        identity = (item.get("dimension_code"), item.get("evidence_kind"), item.get("independence_group") or item.get("evidence_id"))
        if identity in seen:
            duplicates += 1
        seen.add(identity)
    if duplicates:
        findings.append({"severity": "CRITICAL", "code": "DUPLICATE_EVIDENCE", "count": duplicates})

    untraceable = [item for item in evidence if item.get("evidence_kind") in REAL_EVIDENCE_KINDS and not item.get("references")]
    if untraceable:
        findings.append({"severity": "HIGH", "code": "UNTRACEABLE_REAL_EVIDENCE", "count": len(untraceable)})

    overconfident = [
        item for item in snapshots
        if item.get("confidence") == "INSUFFICIENT" and item.get("stage") not in (None, "E0")
    ]
    if overconfident:
        findings.append({"severity": "CRITICAL", "code": "STAGE_WITHOUT_EVIDENCE", "count": len(overconfident)})

    forbidden = [item for item in snapshots if set(item) & PROHIBITED_KEYS]
    if forbidden:
        findings.append({"severity": "CRITICAL", "code": "PROHIBITED_FIELD_PRESENT", "count": len(forbidden)})

    critical = [item for item in findings if item["severity"] == "CRITICAL"]
    return {
        "status": "BLOCKED" if critical else ("PASS_WITH_WARNINGS" if findings else "PASS"),
        "findings": findings,
        "critical_count": len(critical),
        "release_allowed": not critical,
        "rule_version": RULE_VERSION,
    }


def describe_module() -> dict[str, Any]:
    """Self-description used by the API and the platform registry."""
    return {
        "module": "emotional_maturity_diagnostic_os",
        "short_name": "EMD-OS",
        "batch": 1,
        "skills": list(WORKFLOW_NODES),
        "dimensions": [
            {"code": item["code"], "name": item["name"], "training_modules": item["training_modules"]}
            for item in DIMENSIONS
        ],
        "stages": {stage: STAGE_LABELS[stage] for stage in STAGES},
        "consent_scopes": CONSENT_SCOPES,
        "does_not": [
            "判断得救、圣灵同在或神对用户的评价",
            "生成情感或属灵成熟总分与排名",
            "进行精神疾病临床诊断",
            "替代牧者、教会、心理咨询师或危机支持",
            "把一次评估写成用户的永久人格",
        ],
        "engine_version": ENGINE_VERSION,
        "rule_version": RULE_VERSION,
        "model_version": MODEL_VERSION,
        "state_machine": [{"from": source, "to": target} for source, target in STATE_MACHINE],
        "published_events": sorted(PUBLISHED_EVENTS),
        "consumed_events": sorted(CONSUMED_EVENTS),
    }
