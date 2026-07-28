"""EMD-OS Batch 9: measurement, longitudinal analytics and growth reporting (EM-71 ~ EM-77).

Batch 9 不是另一个训练系统，而是整个 EMD-OS 的三个平面：

    Measurement Plane  证据与测量：EM-71 指标语义、EM-72 自适应复测、EM-73 基线可比性
    Analytics Plane    趋势与解释：EM-74 转折点、EM-75 跨场景泛化、EM-76 归因与恶化风险
    Reporting Plane    用户可理解的报告：EM-77 用户控制的成长报告

不可突破的原则（由代码强制）：

* 不生成任何单一总分、生命指数或用户间排名。
* 同一个指标名在全系统只有一个定义；分子、分母与可用证据类型都要注册并冻结版本。
* Rubric、题库或模型版本变化会使旧基线不可比，必须显式标注，而不是静默比较。
* 变化小于测量误差时只能显示「无法确认变化」。
* 任何趋势结论都必须附带替代解释，不作因果断言。
* 报告由用户审核后才存在；牧养视图与群体视图必须逐字段同意且可撤回。
"""
from __future__ import annotations

import re
import statistics
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .emotional_maturity import UnsafeContentError, validate_safe_text


ENGINE_VERSION = "emd-analytics-engine-1.0"
RULE_VERSION = "emd-analytics-rules-1.0"

METRIC_DOMAINS: tuple[str, ...] = (
    "BEHAVIOR", "RECOVERY", "REPAIR", "TRANSFER", "PRACTICE", "SAFETY", "EXPERIENCE",
)
METRIC_UNITS: tuple[str, ...] = ("RATE", "COUNT", "DURATION_SECONDS", "STAGE", "LEVEL")
EVIDENCE_TYPES_FOR_METRICS: tuple[str, ...] = (
    "REAL_LIFE_EVENT", "TIMELINE_CONFIRMED", "RECENT_BEHAVIOR", "SCENARIO_RESPONSE",
    "SELF_DESCRIPTION", "PRACTICE_LOG",
)
METRIC_STATUSES: tuple[str, ...] = ("DRAFT", "ACTIVE", "FROZEN", "RETIRED")

FORBIDDEN_REPORT_PHRASES: tuple[str, ...] = (
    "情感成熟度：", "属灵成熟度：", "综合生命指数", "排名前", "在全部用户中",
    "成熟度得分", "生命指数",
)

REPORT_VIEWS: dict[str, str] = {
    "PRIVATE": "只有你自己能看到的完整视图",
    "PASTORAL": "逐字段同意后分享给牧养人员的脱敏视图",
    "GROUP": "小组视图：只包含你主动选择公开的操练内容",
}


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _now(now: datetime | None = None) -> datetime:
    return now or datetime.now(timezone.utc)


def validate_report_text(text: str) -> str:
    """No total score, no life index, no ranking — ever."""
    for phrase in FORBIDDEN_REPORT_PHRASES:
        if phrase in (text or ""):
            raise UnsafeContentError(f"report may not contain: {phrase}")
    return validate_safe_text(text)


# ─────────────────────────────────────────────────────────────────────────────
# EM-71 formation_metric_catalog_and_semantic_guard
# ─────────────────────────────────────────────────────────────────────────────

class MetricDefinition(BaseModel):
    metric_code: str = Field(min_length=2, max_length=60, pattern=r"^[a-z0-9_]+$")
    version: str = Field(default="v1", max_length=12)
    display_name: str = Field(min_length=1, max_length=60)
    domain: str
    description: str = Field(min_length=1, max_length=240)
    unit: str
    numerator_definition: str = Field(default="", max_length=240)
    denominator_definition: str = Field(default="", max_length=240)
    eligible_evidence_types: list[str] = Field(default_factory=list, max_length=6)
    forbidden_interpretations: list[str] = Field(default_factory=list, max_length=8)
    status: str = "DRAFT"

    @field_validator("domain")
    @classmethod
    def known_domain(cls, value: str) -> str:
        if value not in METRIC_DOMAINS:
            raise ValueError(f"unknown metric domain: {value}")
        return value

    @field_validator("unit")
    @classmethod
    def known_unit(cls, value: str) -> str:
        if value not in METRIC_UNITS:
            raise ValueError(f"unknown metric unit: {value}")
        return value

    @field_validator("status")
    @classmethod
    def known_status(cls, value: str) -> str:
        if value not in METRIC_STATUSES:
            raise ValueError(f"unknown metric status: {value}")
        return value

    @field_validator("eligible_evidence_types")
    @classmethod
    def known_evidence(cls, value: list[str]) -> list[str]:
        unknown = [item for item in value if item not in EVIDENCE_TYPES_FOR_METRICS]
        if unknown:
            raise ValueError(f"unknown evidence type: {','.join(unknown)}")
        return value

    @model_validator(mode="after")
    def validate_definition(self):
        validate_report_text(self.display_name)
        validate_report_text(self.description)
        if self.unit == "RATE" and not (self.numerator_definition and self.denominator_definition):
            raise ValueError("rate metrics require both numerator and denominator definitions")
        if not self.eligible_evidence_types:
            raise ValueError("a metric must declare which evidence types may feed it")
        return self


def register_metric(
    definition: MetricDefinition,
    *,
    catalog: dict[tuple[str, str], MetricDefinition] | None = None,
) -> dict[str, Any]:
    """One name, one definition. A frozen version can never be redefined in place."""
    registry = dict(catalog or {})
    key = (definition.metric_code, definition.version)
    existing = registry.get(key)
    errors: list[str] = []

    if existing and existing.status in {"FROZEN", "ACTIVE"}:
        changed = (
            existing.numerator_definition != definition.numerator_definition
            or existing.denominator_definition != definition.denominator_definition
            or existing.unit != definition.unit
        )
        if changed:
            errors.append("FROZEN_METRIC_REDEFINED")

    conflicting = [
        item for (code, version), item in registry.items()
        if code == definition.metric_code and version != definition.version
        and item.unit != definition.unit
    ]
    if conflicting:
        errors.append("UNIT_CONFLICT_ACROSS_VERSIONS")

    if errors:
        return {
            "registration_id": _new_id("mtc"),
            "status": "REJECTED",
            "errors": errors,
            "fix": "改变语义必须发新版本号，并把旧版本标记为 RETIRED。",
            "next_action": "CREATE_NEW_METRIC_VERSION",
        }

    registry[key] = definition
    return {
        "registration_id": _new_id("mtc"),
        "status": "REGISTERED",
        "metric_code": definition.metric_code,
        "version": definition.version,
        "definition": definition.model_dump(mode="json"),
        "catalog_size": len(registry),
        "semantic_rule": "同一个指标名在全系统只有一个定义；分子、分母与可用证据类型必须一致。",
        "next_action": "COMPOSE_REASSESSMENT",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-72 adaptive_longitudinal_reassessment_composer
# ─────────────────────────────────────────────────────────────────────────────

MAX_REASSESSMENT_ITEMS = 12


def compose_reassessment(
    *,
    day: int,
    baseline_item_ids: list[str],
    priority_dimensions: list[str],
    new_events_since_baseline: int = 0,
    fatigue: float = 0.0,
    skipped_last_time: list[str] | None = None,
) -> dict[str, Any]:
    """Re-ask what is comparable, skip what was declined, and stop long before fatigue."""
    if day not in {14, 30, 90}:
        raise ValueError(f"unknown checkpoint day: {day}")
    skipped = set(skipped_last_time or [])

    reask = [item for item in baseline_item_ids if item not in skipped]
    budget = MAX_REASSESSMENT_ITEMS if fatigue < 0.5 else max(3, MAX_REASSESSMENT_ITEMS // 2)
    selected = reask[:budget]

    return {
        "composition_id": _new_id("rea"),
        "day": day,
        "selected_items": selected,
        "reused_baseline_items": selected,
        "excluded_previously_skipped": sorted(skipped),
        "item_budget": budget,
        "event_items_requested": min(2, new_events_since_baseline),
        "priority_dimensions": priority_dimensions[:2],
        "comparability_rule": "只有与基线同版本的题目才用于比较；新题只作为补充证据。",
        "skipping_is_free": "跳过任何一题都不会影响你的阶段或置信度。",
        "next_action": "RECONCILE_COMPARABILITY",
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-73 baseline_snapshot_comparability_reconciler
# ─────────────────────────────────────────────────────────────────────────────

VERSIONED_COMPONENTS: tuple[str, ...] = (
    "rubric_bundle_version", "item_bank_version", "model_version", "engine_version", "metric_version",
)
DEFAULT_MEASUREMENT_ERROR = 1  # 阶段单位


def reconcile_comparability(
    *,
    baseline: dict[str, Any],
    current: dict[str, Any],
    stage_change: int = 0,
    measurement_error: int = DEFAULT_MEASUREMENT_ERROR,
) -> dict[str, Any]:
    """Version drift makes a comparison invalid; small changes stay 'cannot confirm'."""
    changed = [
        component for component in VERSIONED_COMPONENTS
        if baseline.get(component) != current.get(component)
    ]
    comparable = not changed

    if not comparable:
        verdict = "NOT_COMPARABLE"
        statement = "评分规则或题库版本发生了变化，这两次结果不能直接比较。"
    elif abs(stage_change) < measurement_error:
        verdict = "CHANGE_NOT_CONFIRMED"
        statement = "变化小于测量误差，目前无法确认是否发生了真实变化。"
    else:
        verdict = "COMPARABLE_CHANGE"
        statement = "两次结果版本一致，变化超过测量误差。"

    return {
        "reconciliation_id": _new_id("cmp"),
        "comparable": comparable,
        "verdict": verdict,
        "changed_components": changed,
        "stage_change": stage_change,
        "measurement_error": measurement_error,
        "user_statement": statement,
        "recompute_required": bool(changed),
        "next_action": "ANALYSE_TRAJECTORY" if verdict == "COMPARABLE_CHANGE" else "REPORT_UNCERTAINTY",
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-74 multi_domain_trajectory_change_point_analyzer
# ─────────────────────────────────────────────────────────────────────────────

MIN_POINTS_FOR_TREND = 3


def analyze_trajectory(
    *,
    domain: str,
    points: list[dict[str, Any]],
    lower_is_better: bool = True,
) -> dict[str, Any]:
    """Trend plus change point, per domain, with no causal claim attached."""
    if domain not in METRIC_DOMAINS:
        raise ValueError(f"unknown metric domain: {domain}")
    values = [(item["at"], float(item["value"])) for item in points if item.get("value") is not None]
    if len(values) < MIN_POINTS_FOR_TREND:
        return {
            "trajectory_id": _new_id("trj"),
            "domain": domain,
            "status": "INSUFFICIENT_POINTS",
            "minimum_required": MIN_POINTS_FOR_TREND,
            "note": "数据点不足以描述趋势；这不代表没有变化。",
            "next_action": "COLLECT_MORE_DATA",
        }

    ordered = sorted(values, key=lambda item: item[0])
    midpoint = max(1, len(ordered) // 2)
    early = statistics.median(value for _, value in ordered[:midpoint])
    late = statistics.median(value for _, value in ordered[midpoint:])
    delta = late - early
    improving = delta < 0 if lower_is_better else delta > 0

    if abs(delta) < max(0.1, abs(early) * 0.1):
        direction = "STABLE"
    else:
        direction = "IMPROVING" if improving else "WORSENING"

    change_point = None
    if len(ordered) >= 4:
        gaps = [
            (abs(ordered[index + 1][1] - ordered[index][1]), index)
            for index in range(len(ordered) - 1)
        ]
        largest, index = max(gaps)
        if largest >= max(0.2, abs(early) * 0.2):
            change_point = {
                "between": [ordered[index][0], ordered[index + 1][0]],
                "magnitude": round(largest, 3),
                "causal_claim": False,
            }

    return {
        "trajectory_id": _new_id("trj"),
        "domain": domain,
        "status": "ANALYSED",
        "direction": direction,
        "early_median": round(early, 3),
        "late_median": round(late, 3),
        "delta": round(delta, 3),
        "point_count": len(ordered),
        "change_point": change_point,
        "no_causal_claim": "转折点只是数据上的变化位置，不说明原因。",
        "next_action": "ANALYSE_GENERALIZATION",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-75 context_transfer_generalization_analytics_engine
# ─────────────────────────────────────────────────────────────────────────────

GENERALIZATION_LEVELS: dict[str, str] = {
    "G0": "证据不足",
    "G1": "只在一个场景中观察到",
    "G2": "在两个场景中观察到，但压力水平相近",
    "G3": "跨场景且包含一次较高压力情境",
    "G4": "跨场景、跨压力，并且在 30/90 天中重复出现",
}
GEN_ORDER: tuple[str, ...] = ("G0", "G1", "G2", "G3", "G4")


def analyze_generalization(
    *,
    observations: list[dict[str, Any]],
    longitudinal_days: int = 0,
) -> dict[str, Any]:
    """Breadth of transfer across contexts and pressure — never averaged into one number."""
    contexts = {str(item.get("context")) for item in observations if item.get("context")}
    high_pressure = [item for item in observations if item.get("high_pressure")]
    repeats = len(observations)

    level = "G0"
    if repeats >= 1 and contexts:
        level = "G1"
    if len(contexts) >= 2:
        level = "G2"
    if len(contexts) >= 2 and high_pressure:
        level = "G3"
    if level == "G3" and longitudinal_days >= 30 and repeats >= 3:
        level = "G4"

    per_context = {}
    for item in observations:
        context = str(item.get("context") or "OTHER")
        per_context.setdefault(context, {"count": 0, "high_pressure": 0})
        per_context[context]["count"] += 1
        if item.get("high_pressure"):
            per_context[context]["high_pressure"] += 1

    return {
        "generalization_id": _new_id("gen"),
        "level": level,
        "level_label": GENERALIZATION_LEVELS[level],
        "contexts_observed": sorted(contexts),
        "per_context": per_context,
        "high_pressure_events": len(high_pressure),
        "not_averaged": "不同场景分别呈现，不合并为一个平均值。",
        "next_action": "CALIBRATE_ATTRIBUTION",
        "rule_version": RULE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-76 change_attribution_and_regression_risk_calibrator
# ─────────────────────────────────────────────────────────────────────────────

ALTERNATIVE_EXPLANATIONS: tuple[str, ...] = (
    "这段时间的触发机会本身变多或变少",
    "睡眠、身体状况或工作强度发生变化",
    "环境、住处或关系对象发生变化",
    "记录方式或记录意愿发生变化",
    "对方的行为发生变化",
    "同期开始了其他支持（医疗、咨询、牧养或药物）",
)
REGRESSION_SIGNALS: dict[str, str] = {
    "HARMFUL_ACTION_RETURNED": "伤害性行为重新出现",
    "RECOVERY_SLOWING": "恢复时间连续变长",
    "REPAIR_STOPPED": "修复行为停止",
    "WITHDRAWAL_INCREASING": "回避与断联增加",
    "SAFETY_SIGNAL": "出现安全相关信号",
    "PRACTICE_ABANDONED": "操练完全停止且伴随功能下降",
}


def calibrate_attribution(
    *,
    observed_change: str,
    concurrent_factors: list[str] | None = None,
    regression_signals: list[str] | None = None,
    comparable_event_count: int = 0,
) -> dict[str, Any]:
    """Correlation with training is reported as correlation; deterioration is escalated early."""
    signals = [str(item).upper() for item in (regression_signals or [])]
    unknown = [item for item in signals if item not in REGRESSION_SIGNALS]
    if unknown:
        raise ValueError(f"unknown regression signal: {','.join(unknown)}")

    severity = "NONE"
    if signals:
        severity = "WATCH"
    if "SAFETY_SIGNAL" in signals:
        severity = "SAFETY_FIRST"
    elif len(signals) >= 2:
        severity = "ELEVATED"

    return {
        "attribution_id": _new_id("att"),
        "observed_change": observed_change,
        "attribution_claim": "CORRELATION_ONLY",
        "causal_claim": False,
        "alternative_explanations": [
            *(concurrent_factors or []),
            *ALTERNATIVE_EXPLANATIONS,
        ],
        "evidence_sufficiency": "SUFFICIENT" if comparable_event_count >= 2 else "LIMITED",
        "regression_signals": [
            {"code": code, "description": REGRESSION_SIGNALS[code]} for code in signals
        ],
        "regression_severity": severity,
        "next_action": (
            "ROUTE_TO_SAFETY_SUPPORT" if severity == "SAFETY_FIRST"
            else "PUBLISH_GROWTH_REPORT"
        ),
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EM-77 user_controlled_growth_report_dashboard_publisher
# ─────────────────────────────────────────────────────────────────────────────

REPORT_SECTIONS: tuple[tuple[str, str], ...] = (
    ("WHAT_YOU_PRACTISED", "这段时间你实际练习了什么"),
    ("WHAT_CHANGED", "有证据支持的变化"),
    ("WHAT_DID_NOT_CHANGE", "暂时没有变化的部分"),
    ("STILL_UNKNOWN", "仍然不知道的部分"),
    ("CONTEXT_DIFFERENCES", "不同场景的差别"),
    ("NEXT_SMALL_STEP", "下一步的一件小事"),
)
RECOMMENDED_CHARTS: tuple[tuple[str, str], ...] = (
    ("STAGE_BY_CONTEXT", "按场景显示阶段，不做平均"),
    ("RECOVERY_TIME_BUCKETS", "恢复时间分桶，而不是精确秒数"),
    ("EVENT_COUNT_TIMELINE", "事件数量时间线，标注证据是否充分"),
    ("CONFIDENCE_BANDS", "置信度带，而不是单点数值"),
)


def publish_growth_report(
    *,
    view: str,
    sections: dict[str, str],
    consented_scopes: list[str] | None = None,
    approved_by_user: bool = False,
    selected_fields: list[str] | None = None,
    expires_in_days: int = 30,
) -> dict[str, Any]:
    """A report exists only after the user approves it; sharing is field-level and expiring."""
    if view not in REPORT_VIEWS:
        raise ValueError(f"unknown report view: {view}")
    scopes = list(consented_scopes or [])
    if view in {"PASTORAL", "GROUP"} and "EMD_PASTORAL_SHARE" not in scopes:
        return {
            "report_id": _new_id("rpt"),
            "status": "BLOCKED_NO_CONSENT",
            "view": view,
            "next_action": "OFFER_SHARE_CONSENT",
        }

    unknown = [key for key in sections if key not in dict(REPORT_SECTIONS)]
    if unknown:
        raise ValueError(f"unknown report section: {','.join(unknown)}")
    content = {key: validate_report_text(value) for key, value in sections.items()}

    if view != "PRIVATE" and selected_fields is not None:
        content = {key: value for key, value in content.items() if key in selected_fields}

    return {
        "report_id": _new_id("rpt"),
        "status": "PUBLISHED" if approved_by_user else "DRAFT_AWAITING_USER_APPROVAL",
        "view": view,
        "view_label": REPORT_VIEWS[view],
        "sections": [
            {"code": code, "label": label, "content": content.get(code)}
            for code, label in REPORT_SECTIONS
        ],
        "total_score": None,
        "ranking": None,
        "recommended_charts": [{"code": code, "note": note} for code, note in RECOMMENDED_CHARTS],
        "language_rules": [
            "只描述有证据支持的变化，并标注置信度。",
            "没有变化和仍然未知都要写出来。",
            "不使用分数、指数或排名。",
        ],
        "user_approved": approved_by_user,
        "auto_shared": False,
        "expires_in_days": expires_in_days if view != "PRIVATE" else None,
        "revocable": view != "PRIVATE",
        "next_action": "USER_REVIEW" if not approved_by_user else "UPDATE_FORMATION_TWIN",
        "engine_version": ENGINE_VERSION,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 状态机与自描述
# ─────────────────────────────────────────────────────────────────────────────

WORKFLOW_NODES: tuple[str, ...] = (
    "EM-71_metric_catalog", "EM-72_reassessment_composer", "EM-73_comparability_reconciler",
    "EM-74_trajectory_analyzer", "EM-75_generalization_analytics", "EM-76_attribution_calibrator",
    "EM-77_report_publisher",
)

STATE_MACHINE: tuple[tuple[str, str], ...] = (
    ("METRICS_REGISTERED", "REASSESSMENT_COMPOSED"),
    ("REASSESSMENT_COMPOSED", "COMPARABILITY_RECONCILED"),
    ("COMPARABILITY_RECONCILED", "TRAJECTORY_ANALYSED"),
    ("COMPARABILITY_RECONCILED", "UNCERTAINTY_REPORTED"),
    ("TRAJECTORY_ANALYSED", "GENERALIZATION_ANALYSED"),
    ("GENERALIZATION_ANALYSED", "ATTRIBUTION_CALIBRATED"),
    ("ATTRIBUTION_CALIBRATED", "REPORT_DRAFTED"),
    ("ATTRIBUTION_CALIBRATED", "ROUTED_TO_SAFETY"),
    ("REPORT_DRAFTED", "REPORT_PUBLISHED"),
    ("REPORT_DRAFTED", "REPORT_DISCARDED"),
    ("REPORT_PUBLISHED", "TWIN_UPDATED"),
)


def describe_analytics_engine() -> dict[str, Any]:
    return {
        "module": "emotional_maturity_analytics",
        "short_name": "EMD-OS Batch 9",
        "batch": 9,
        "skills": list(WORKFLOW_NODES),
        "planes": {
            "measurement": ["EM-71", "EM-72", "EM-73"],
            "analytics": ["EM-74", "EM-75", "EM-76"],
            "reporting": ["EM-77"],
        },
        "metric_domains": list(METRIC_DOMAINS),
        "metric_units": list(METRIC_UNITS),
        "versioned_components": list(VERSIONED_COMPONENTS),
        "generalization_levels": GENERALIZATION_LEVELS,
        "regression_signals": REGRESSION_SIGNALS,
        "report_views": REPORT_VIEWS,
        "report_sections": [{"code": code, "label": label} for code, label in REPORT_SECTIONS],
        "recommended_charts": [{"code": code, "note": note} for code, note in RECOMMENDED_CHARTS],
        "forbidden_report_phrases": list(FORBIDDEN_REPORT_PHRASES),
        "does_not": [
            "不生成单一总分、生命指数或用户间排名",
            "不允许同一指标在不同模块有不同定义",
            "不在版本变化后静默比较两次结果",
            "不把小于测量误差的差异说成变化",
            "不对趋势作因果断言",
            "不在用户批准前发布或分享任何报告",
        ],
        "engine_version": ENGINE_VERSION,
        "rule_version": RULE_VERSION,
        "state_machine": [{"from": source, "to": target} for source, target in STATE_MACHINE],
    }
