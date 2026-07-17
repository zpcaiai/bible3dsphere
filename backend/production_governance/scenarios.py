"""Finite, user-owned scenario simulation for Formation Twin Batch 10.

The engine compares a few near-term branches.  It is deliberately not a
forecasting system: it accepts only user-confirmed inputs, never produces
probabilities, never declares divine intent, and cannot execute an action.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


ENGINE_VERSION = "formation-scenario-rules-1.0.0"
POLICY_VERSION = "scenario-non-prediction-1.0.0"
NON_PREDICTION_NOTICE = (
    "这是基于你确认资料和可见假设的有限情景比较，不是预测、概率、神的旨意或人生结论。"
)
PROHIBITED_INTERPRETATIONS = [
    "不得解释为神的隐藏旨意", "不得解释为救恩或属灵结果预测",
    "不得解释为复发、关系、医疗或重大人生结果的保证",
]

PROHIBITED_KEYS = {
    "scenario_success_probability", "spiritual_outcome_score", "salvation_probability",
    "relapse_probability", "holiness_forecast", "obedience_forecast",
    "divine_will_recommendation", "future_spiritual_rank", "spiritual_growth_probability",
    "marriage_success_probability", "calling_success_probability",
}
RAW_SENSITIVE_KEYS = {
    "journal_body", "journal_text", "prayer_body", "confession_text", "crisis_body",
    "crisis_narrative", "temptation_text", "relapse_text", "voice_transcript",
    "collaborator_feedback", "report_body", "model_prompt", "internal_risk_band",
}
PROHIBITED_LANGUAGE = (
    r"\b(?:will|must|guarantee[sd]?|proves?|certainly)\b",
    r"\b\d+(?:\.\d+)?\s*%",
    r"神(?:告诉|命令|要求|证明|保证)(?:你|我)",
    r"神(?:一定|必然|希望你|要你)",
    r"一定会|必然会|保证会|系统证明|模型证明|命中率|成功率|复发概率|救恩概率|属灵收益率",
)
MAJOR_DECISION_TERMS = {
    "辞职", "离职", "结婚", "离婚", "换教会", "离开教会", "宣教", "停药",
    "手术", "quit my job", "resign", "marry", "divorce", "change church",
}


class ScenarioType(str, Enum):
    CONTINUE_CURRENT_PATTERN = "CONTINUE_CURRENT_PATTERN"
    ADD_PROTECTIVE_FACTOR = "ADD_PROTECTIVE_FACTOR"
    REMOVE_BURDEN_FACTOR = "REMOVE_BURDEN_FACTOR"
    TRY_ALTERNATIVE_RESPONSE = "TRY_ALTERNATIVE_RESPONSE"
    CHANGE_ENVIRONMENT_BOUNDARY = "CHANGE_ENVIRONMENT_BOUNDARY"
    INCREASE_REST = "INCREASE_REST"
    ADD_HUMAN_SUPPORT = "ADD_HUMAN_SUPPORT"
    PAUSE_EXISTING_PRACTICE = "PAUSE_EXISTING_PRACTICE"
    LIFE_SEASON_TRANSITION = "LIFE_SEASON_TRANSITION"
    USER_DEFINED = "USER_DEFINED"


class ScenarioHorizon(str, Enum):
    NEXT_EVENT = "NEXT_EVENT"
    NEXT_24_HOURS = "NEXT_24_HOURS"
    NEXT_7_DAYS = "NEXT_7_DAYS"
    NEXT_30_DAYS = "NEXT_30_DAYS"
    CURRENT_LIFE_SEASON = "CURRENT_LIFE_SEASON"
    USER_DEFINED = "USER_DEFINED"


class ScenarioSourceKind(str, Enum):
    USER_CURRENT_STATE = "USER_CURRENT_STATE"
    USER_CONFIRMED_PATTERN = "USER_CONFIRMED_PATTERN"
    USER_CONFIRMED_LIFE_SEASON = "USER_CONFIRMED_LIFE_SEASON"
    USER_CONFIRMED_EFFECT = "USER_CONFIRMED_EFFECT"
    USER_DEFINED = "USER_DEFINED"


class EvidenceLevel(str, Enum):
    USER_CONFIRMED_EFFECT = "USER_CONFIRMED_EFFECT"
    USER_CONFIRMED_PATTERN = "USER_CONFIRMED_PATTERN"
    OBSERVED_SEQUENCE = "OBSERVED_SEQUENCE"
    RULE_DERIVED_ASSOCIATION = "RULE_DERIVED_ASSOCIATION"
    MODEL_SCENARIO_HYPOTHESIS = "MODEL_SCENARIO_HYPOTHESIS"


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware datetime required")
    return value


def _walk_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            found.add(str(key).lower())
            found.update(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_walk_keys(child))
    return found


def assert_scenario_payload_safe(value: Any) -> Any:
    keys = _walk_keys(value)
    blocked = sorted(keys & (PROHIBITED_KEYS | RAW_SENSITIVE_KEYS))
    if blocked:
        raise ValueError("scenario contains prohibited or raw-sensitive fields: " + ",".join(blocked[:5]))
    return value


def validate_non_prediction_text(value: str) -> str:
    normalized = value.strip()
    for pattern in PROHIBITED_LANGUAGE:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            raise ValueError("deterministic, probabilistic, or divine-oracle scenario language is prohibited")
    return normalized


class ScenarioAssumption(BaseModel):
    assumption_type: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=320)
    source_kind: ScenarioSourceKind
    source_reference_ids: list[str] = Field(default_factory=list, max_length=20)
    user_confirmed: bool
    uncertainty: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def confirmed_and_safe(self):
        if not self.user_confirmed:
            raise ValueError("scenario assumptions must be user confirmed")
        validate_non_prediction_text(self.description)
        if self.uncertainty:
            validate_non_prediction_text(self.uncertainty)
        return self


class ScenarioEvidence(BaseModel):
    evidence_level: EvidenceLevel
    source_reference_id: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=280)
    supports_branch: bool = True
    user_confirmed: bool = True

    @field_validator("summary")
    @classmethod
    def humble_summary(cls, value: str) -> str:
        return validate_non_prediction_text(value)


class ScenarioEvidenceMatrix(BaseModel):
    supporting_evidence: list[ScenarioEvidence] = Field(default_factory=list, max_length=20)
    counterevidence: list[ScenarioEvidence] = Field(default_factory=list, max_length=20)
    missing_evidence: list[str] = Field(default_factory=list, min_length=1, max_length=12)
    contextual_similarity: Literal["LIMITED", "PARTIAL", "CURRENT_USER_HISTORY"] = "LIMITED"
    evidence_diversity: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"
    causal_claim_allowed: Literal[False] = False
    limitations: list[str] = Field(default_factory=list, min_length=1, max_length=12)


class ScenarioEffect(BaseModel):
    effect_type: Literal[
        "POSSIBLE_REDUCTION_IN_BURDEN", "POSSIBLE_INCREASE_IN_RECOVERY_CAPACITY",
        "POSSIBLE_INTERRUPTION_OF_OLD_PATH", "POSSIBLE_IMPROVEMENT_IN_HUMAN_CONNECTION",
        "POSSIBLE_INCREASE_IN_TASK_LOAD", "POSSIBLE_CONFLICT_RISK", "POSSIBLE_SLEEP_IMPACT",
        "POSSIBLE_ATTENTION_IMPACT", "UNCLEAR",
    ]
    description: str = Field(min_length=1, max_length=280)
    evidence_level: EvidenceLevel = EvidenceLevel.RULE_DERIVED_ASSOCIATION

    @field_validator("description")
    @classmethod
    def non_predictive(cls, value: str) -> str:
        return validate_non_prediction_text(value)


class ScenarioBranch(BaseModel):
    branch_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    label: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=320)
    changed_assumptions: list[ScenarioAssumption] = Field(default_factory=list, max_length=4)
    unchanged_constraints: list[str] = Field(default_factory=list, max_length=12)
    plausible_near_term_effects: list[ScenarioEffect] = Field(default_factory=list, max_length=6)
    possible_tradeoffs: list[str] = Field(default_factory=list, min_length=1, max_length=6)
    uncertainty_factors: list[str] = Field(default_factory=list, min_length=1, max_length=6)
    observation_plan: list[str] = Field(default_factory=list, min_length=1, max_length=6)
    action_required: Literal[False] = False
    user_selected: bool = False

    @model_validator(mode="after")
    def safe_branch(self):
        validate_non_prediction_text(self.description)
        for item in self.possible_tradeoffs + self.uncertainty_factors + self.observation_plan:
            validate_non_prediction_text(item)
        assert_scenario_payload_safe(self.model_dump(mode="json"))
        return self


class ScenarioCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    question: str = Field(min_length=1, max_length=320)
    scenario_type: ScenarioType
    baseline_snapshot_ids: list[str] = Field(default_factory=list, max_length=20)
    baseline_generated_at: datetime
    assumptions: list[ScenarioAssumption] = Field(min_length=1, max_length=8)
    fixed_constraints: list[str] = Field(default_factory=list, max_length=12)
    excluded_factors: list[str] = Field(default_factory=list, max_length=12)
    horizon: ScenarioHorizon
    evidence: list[ScenarioEvidence] = Field(default_factory=list, max_length=30)
    safety_level: Literal["NONE", "CONCERN", "ELEVATED", "IMMINENT"] = "NONE"
    user_review_status: Literal["DRAFT", "USER_CONFIRMED"] = "DRAFT"

    @model_validator(mode="after")
    def bounded(self):
        _aware(self.baseline_generated_at)
        validate_non_prediction_text(self.title)
        # Questions may contain a major-decision term; oracle/probability language is still blocked.
        for pattern in PROHIBITED_LANGUAGE[1:]:
            if re.search(pattern, self.question, flags=re.IGNORECASE):
                raise ValueError("scenario question contains probability or divine-oracle language")
        for item in self.fixed_constraints + self.excluded_factors:
            validate_non_prediction_text(item)
        if self.safety_level in {"ELEVATED", "IMMINENT"}:
            raise ValueError("acute safety context must route to Crisis Care, not scenario simulation")
        assert_scenario_payload_safe(self.model_dump(mode="json"))
        return self


class FormationScenarioSimulation(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    title: str
    scenario_type: ScenarioType
    baseline_snapshot_ids: list[str]
    baseline_generated_at: datetime
    assumptions: list[ScenarioAssumption]
    fixed_constraints: list[str]
    excluded_factors: list[str]
    horizon: ScenarioHorizon
    branches: list[ScenarioBranch] = Field(min_length=1, max_length=3)
    evidence_matrix: ScenarioEvidenceMatrix
    uncertainty_notes: list[str] = Field(min_length=1, max_length=12)
    non_prediction_notice: Literal[
        "这是基于你确认资料和可见假设的有限情景比较，不是预测、概率、神的旨意或人生结论。"
    ] = NON_PREDICTION_NOTICE
    prohibited_interpretations: list[str] = Field(default_factory=lambda: list(PROHIBITED_INTERPRETATIONS))
    generation_method: Literal["RULE_ONLY"] = "RULE_ONLY"
    engine_version: Literal["formation-scenario-rules-1.0.0"] = ENGINE_VERSION
    model_version: None = None
    rule_version: Literal["scenario-non-prediction-1.0.0"] = POLICY_VERSION
    user_review_status: Literal["DRAFT", "USER_CONFIRMED", "INACCURATE"] = "DRAFT"
    created_at: datetime
    expires_at: datetime
    major_decision_limited: bool = False

    @model_validator(mode="after")
    def validate_output(self):
        _aware(self.created_at); _aware(self.expires_at)
        if self.expires_at <= self.created_at:
            raise ValueError("scenario must expire")
        assert_scenario_payload_safe(self.model_dump(mode="json"))
        return self


def _major_decision(question: str) -> bool:
    lowered = question.lower()
    return any(term.lower() in lowered for term in MAJOR_DECISION_TERMS)


def _change_assumption(request: ScenarioCreate, kind: ScenarioType, description: str) -> ScenarioAssumption:
    matching = next((item for item in request.assumptions if item.assumption_type == kind.value), None)
    return matching or ScenarioAssumption(
        assumption_type=kind.value, description=description,
        source_kind=ScenarioSourceKind.USER_DEFINED, source_reference_ids=[], user_confirmed=True,
        uncertainty="这是用户主动设置的可变条件，效果目前无法确定。",
    )


def build_scenario(request: ScenarioCreate, *, now: datetime | None = None) -> FormationScenarioSimulation:
    """Generate at most three deterministic, non-executing comparison branches."""
    now = _aware(now or datetime.now(timezone.utc))
    if not request.evidence and not request.baseline_snapshot_ids:
        raise ValueError("没有可追溯的已确认基线，当前无法生成有意义的情景比较")
    major = _major_decision(request.question)
    uncertainty = [
        "相似历史不等于相同未来。",
        "目前没有数值概率，也不能确认单一因素造成了过去结果。",
    ]
    if major:
        uncertainty.append("重大人生问题只比较近期负担、支持与现实条件；需结合可信真人和相关专业意见。")

    current = ScenarioBranch(
        label="A · 维持当前方式",
        description="在所选短期范围内保持当前已确认条件，观察旧路径是否再次出现。",
        unchanged_constraints=request.fixed_constraints,
        plausible_near_term_effects=[ScenarioEffect(
            effect_type="UNCLEAR", description="旧路径可能继续，也可能因未记录因素而不同。",
        )],
        possible_tradeoffs=["不增加新任务，但现有负担可能保持。"],
        uncertainty_factors=["未来处境和支持可用性目前无法确定。"],
        observation_plan=["观察负担、睡眠、连接和恢复速度是否变化。"],
    )

    protective_assumption = _change_assumption(
        request, ScenarioType.ADD_PROTECTIVE_FACTOR, "增加一个由你选择的最小保护因素。",
    )
    protective = ScenarioBranch(
        label="B · 增加一个最小保护因素",
        description="只增加一个低风险保护条件，并在所选期限内观察是否更容易暂停旧路径。",
        changed_assumptions=[protective_assumption], unchanged_constraints=request.fixed_constraints,
        plausible_near_term_effects=[
            ScenarioEffect(effect_type="POSSIBLE_INTERRUPTION_OF_OLD_PATH", description="可能更早看见并暂停旧路径，值得观察。"),
            ScenarioEffect(effect_type="POSSIBLE_INCREASE_IN_TASK_LOAD", description="增加保护步骤也可能带来一点执行负担。"),
        ],
        possible_tradeoffs=["需要额外记住并执行一个步骤。", "若当前容量很低，这个步骤也可能显得有负担。"],
        uncertainty_factors=["过去相关不等于这次有效。"],
        observation_plan=["记录是否更早暂停，以及这个保护步骤是否实际可行。"],
    )

    alternative_assumption = _change_assumption(
        request, ScenarioType.TRY_ALTERNATIVE_RESPONSE, "尝试一个已经由你确认的替代回应。",
    )
    alternative = ScenarioBranch(
        label="C · 尝试已确认的替代回应",
        description="在相同短期范围内尝试一个由你确认的替代回应，不把它视为保证或属灵要求。",
        changed_assumptions=[alternative_assumption], unchanged_constraints=request.fixed_constraints,
        plausible_near_term_effects=[
            ScenarioEffect(effect_type="POSSIBLE_REDUCTION_IN_BURDEN", description="替代回应可能减轻当前负担，也可能没有明显变化。"),
            ScenarioEffect(effect_type="POSSIBLE_IMPROVEMENT_IN_HUMAN_CONNECTION", description="若替代回应包含真人支持，连接感可能增加。"),
        ],
        possible_tradeoffs=["替代回应可能需要时间、沟通或他人配合。"],
        uncertainty_factors=["他人的回应和外部环境不在系统控制中。"],
        observation_plan=["观察负担、连接和恢复能力，而不是追求成功分数。"],
    )

    supporting = [item for item in request.evidence if item.supports_branch and item.user_confirmed]
    counter = [item for item in request.evidence if not item.supports_branch and item.user_confirmed]
    matrix = ScenarioEvidenceMatrix(
        supporting_evidence=supporting, counterevidence=counter,
        missing_evidence=["未来环境变化", "未记录的保护或负担因素"],
        contextual_similarity="CURRENT_USER_HISTORY" if supporting else "LIMITED",
        evidence_diversity="MEDIUM" if supporting and counter else "LOW",
        limitations=["只使用用户已确认资料。", "关联和先后顺序不能证明因果。"],
    )
    days = 30 if request.horizon in {ScenarioHorizon.NEXT_30_DAYS, ScenarioHorizon.CURRENT_LIFE_SEASON} else 14
    return FormationScenarioSimulation(
        title=request.title, scenario_type=request.scenario_type,
        baseline_snapshot_ids=request.baseline_snapshot_ids,
        baseline_generated_at=request.baseline_generated_at,
        assumptions=request.assumptions, fixed_constraints=request.fixed_constraints,
        excluded_factors=request.excluded_factors, horizon=request.horizon,
        branches=[current, protective, alternative], evidence_matrix=matrix,
        uncertainty_notes=uncertainty, user_review_status=request.user_review_status,
        created_at=now, expires_at=now + timedelta(days=days), major_decision_limited=major,
    )


def add_user_branch(simulation: FormationScenarioSimulation, branch: ScenarioBranch) -> FormationScenarioSimulation:
    if len(simulation.branches) >= 3:
        raise ValueError("scenario branch limit is three; remove a branch before adding another")
    return simulation.model_copy(update={"branches": [*simulation.branches, branch]})


def scenario_to_proposal(simulation: FormationScenarioSimulation, branch_id: str) -> dict[str, Any]:
    branch = next((item for item in simulation.branches if str(item.branch_id) == branch_id), None)
    if not branch:
        raise ValueError("scenario branch not found")
    return {
        "proposal_type": "SCENARIO_DERIVED_MICRO_INTERVENTION",
        "scenario_id": str(simulation.id), "branch_id": str(branch.branch_id),
        "title": branch.label, "description": branch.description,
        "requires_user_confirmation": True, "requires_safety_gate": True,
        "execution_status": "NOT_EXECUTED", "source_is_prediction": False,
    }


def scenario_data_quality(simulation: FormationScenarioSimulation) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    if simulation.non_prediction_notice != NON_PREDICTION_NOTICE:
        issues.append({"severity": "HIGH", "code": "NON_PREDICTION_NOTICE_MISSING"})
    if len(simulation.branches) > 3:
        issues.append({"severity": "HIGH", "code": "BRANCH_LIMIT_EXCEEDED"})
    if any(not item.user_confirmed for item in simulation.assumptions):
        issues.append({"severity": "HIGH", "code": "UNCONFIRMED_ASSUMPTION_USED"})
    try:
        assert_scenario_payload_safe(simulation.model_dump(mode="json"))
    except ValueError:
        issues.append({"severity": "HIGH", "code": "PROHIBITED_SCENARIO_FIELD"})
    high = [item for item in issues if item["severity"] == "HIGH"]
    return {"ok": not high, "issue_count": len(issues), "high_severity_count": len(high), "issues": issues}
