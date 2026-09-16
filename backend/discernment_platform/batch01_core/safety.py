"""Skill 09 - pastoral-safety-guardian (always-on rule + classifier).

Runs before intake, after every high-risk node, and before final output.
"""

from __future__ import annotations

from . import taxonomy
from .models import (
    DiscernmentCase,
    RiskLevel,
    SafetyDecision,
    Sensitivity,
)

SKILL_ID = "pastoral-safety-guardian"
SKILL_VERSION = "0.1.0"


def _hits(text: str, markers: tuple[str, ...]) -> list[str]:
    return [m for m in markers if m in text]


def _escalate(current: RiskLevel, candidate: RiskLevel) -> RiskLevel:
    return candidate if candidate.rank > current.rank else current


def precheck(case: DiscernmentCase) -> SafetyDecision:
    """Input-side safety pass. Never pathologises ordinary faith language."""

    text = f"{case.raw_input}\n{case.user_goal}"
    risk = RiskLevel.NONE
    blocked: list[str] = []
    guidance: list[str] = []
    notes: list[str] = []
    halt = False
    review = False

    if _hits(text, taxonomy.CRISIS_MARKERS):
        risk = _escalate(risk, RiskLevel.CRITICAL)
        blocked.append("self_harm_risk")
        guidance.extend(taxonomy.SUPPORT_GUIDANCE["crisis"])
        halt = True
        review = True

    if _hits(text, taxonomy.HARM_TO_OTHERS_MARKERS):
        risk = _escalate(risk, RiskLevel.CRITICAL)
        blocked.append("harm_to_others_risk")
        guidance.extend(taxonomy.SUPPORT_GUIDANCE["crisis"])
        halt = True
        review = True

    if _hits(text, taxonomy.ABUSE_MARKERS) or case.sensitivity is Sensitivity.ABUSE:
        risk = _escalate(risk, RiskLevel.HIGH)
        blocked.append("abuse_context")
        guidance.extend(taxonomy.SUPPORT_GUIDANCE["abuse"])
        halt = True
        review = True

    if _hits(text, taxonomy.DELUSION_MARKERS):
        risk = _escalate(risk, RiskLevel.HIGH)
        blocked.append("revelation_certainty")
        guidance.extend(taxonomy.SUPPORT_GUIDANCE["delusion"])
        review = True
        notes.append("不得确认或强化“神已直接启示”类的确定性断言。")

    scrupulosity = _hits(text, taxonomy.SCRUPULOSITY_MARKERS)
    if scrupulosity or case.sensitivity is Sensitivity.MENTAL_HEALTH:
        risk = _escalate(risk, RiskLevel.HIGH)
        blocked.append("religious_scrupulosity")
        guidance.extend(taxonomy.SUPPORT_GUIDANCE["mental_health"])
        review = True
        notes.append("降低律法压力，优先安慰与确据，不得继续加深自我控告。")

    if _hits(text, taxonomy.DEEPER_SIN_REQUEST_MARKERS) and scrupulosity:
        blocked.append("deeper_sin_excavation_request")
        notes.append("用户请求继续深挖罪，但存在强迫性认罪风险，不予执行。")

    if _hits(text, taxonomy.MINOR_MARKERS):
        risk = _escalate(risk, RiskLevel.HIGH)
        blocked.append("possible_minor")
        review = True

    if _hits(text, taxonomy.MEDICALIZATION_MARKERS):
        risk = _escalate(risk, RiskLevel.MODERATE)
        notes.append("涉及医疗议题，不得把医疗问题简化为属灵问题，也不得作临床诊断。")

    if case.sensitivity is Sensitivity.CRISIS:
        risk = RiskLevel.CRITICAL
        halt = True
        review = True
        if "self_harm_risk" not in blocked:
            blocked.append("declared_crisis")
        guidance.extend(taxonomy.SUPPORT_GUIDANCE["crisis"])

    if not case.consent_scope.allow_spiritual_analysis:
        notes.append("未获属灵分析同意，仅执行内容与观点层面的分析。")

    return SafetyDecision(
        stage="precheck",
        risk_level=risk,
        blocked_patterns=blocked,
        human_review_required=review,
        halt_normal_flow=halt,
        support_guidance=list(dict.fromkeys(guidance)),
        notes=notes,
    )


def postcheck(case: DiscernmentCase, rendered_text: str) -> SafetyDecision:
    """Output-side safety pass over everything the user would see."""

    risk = RiskLevel.NONE
    blocked: list[str] = []
    rewrite: list[str] = []
    review = False

    condemnation = _hits(rendered_text, taxonomy.CONDEMNATION_MARKERS)
    if condemnation:
        risk = _escalate(risk, RiskLevel.HIGH)
        blocked.append("soul_condemnation")
        rewrite.append("移除对他人灵魂状态的断言，改为可察验的行为观察。")
        review = True

    if "你还没认够罪" in rendered_text or "认罪不够" in rendered_text:
        risk = _escalate(risk, RiskLevel.HIGH)
        blocked.append("religious_coercion")
        rewrite.append("移除加深认罪压力的措辞，改为基督已成全的确据。")
        review = True

    if case.subject_type.value == "person" and _hits(
        rendered_text, taxonomy.MEDICALIZATION_MARKERS
    ):
        risk = _escalate(risk, RiskLevel.MODERATE)
        blocked.append("clinical_diagnosis_of_public_person")
        rewrite.append("移除对公众人物的临床性判断。")
        review = True

    return SafetyDecision(
        stage="postcheck",
        risk_level=risk,
        blocked_patterns=blocked,
        required_rewrite=rewrite,
        human_review_required=review,
        halt_normal_flow=False,
    )
