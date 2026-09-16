"""Skill 09 - pastoral-safety-guardian."""

from backend.discernment_platform.batch01_core.models import (
    ConsentScope,
    DiscernmentCase,
    RiskLevel,
    Sensitivity,
    SubjectType,
)
from backend.discernment_platform.batch01_core.safety import postcheck, precheck


def _case(raw, **kw):
    kw.setdefault("subject_type", SubjectType.SELF_REFLECTION)
    return DiscernmentCase(
        case_id="s-1",
        raw_input=raw,
        user_goal="求助",
        consent_scope=ConsentScope(
            allow_spiritual_analysis=True, allow_gospel_bridge=True
        ),
        **kw,
    )


def test_suicidal_content_halts_normal_flow():
    decision = precheck(_case("我最近常常觉得不想活了，也想过结束生命。"))
    assert decision.halt_normal_flow
    assert decision.risk_level is RiskLevel.CRITICAL
    assert "self_harm_risk" in decision.blocked_patterns


def test_crisis_offers_real_world_support():
    assert precheck(_case("我想死，撑不下去了。")).support_guidance


def test_abuse_context_triggers_review():
    decision = precheck(_case("我丈夫经常家暴我，还不让我出门见任何人。"))
    assert decision.human_review_required
    assert "abuse_context" in decision.blocked_patterns


def test_scrupulosity_reduces_law_pressure(scrupulosity_case):
    decision = precheck(scrupulosity_case)
    assert "religious_scrupulosity" in decision.blocked_patterns
    assert any("不得继续加深自我控告" in n for n in decision.notes)


def test_deeper_sin_request_is_refused_under_scrupulosity(scrupulosity_case):
    decision = precheck(scrupulosity_case)
    assert "deeper_sin_excavation_request" in decision.blocked_patterns


def test_revelation_certainty_is_flagged_not_confirmed():
    decision = precheck(_case("神直接告诉我，他们都在监视我，只有我被拣选。"))
    assert "revelation_certainty" in decision.blocked_patterns
    assert any("不得确认或强化" in n for n in decision.notes)


def test_ordinary_faith_language_is_not_pathologised():
    decision = precheck(_case("我最近在读罗马书，觉得对恩典有了新的理解，很感恩。"))
    assert decision.risk_level is RiskLevel.NONE
    assert not decision.halt_normal_flow


def test_minor_signals_trigger_review():
    assert precheck(_case("我今年13岁，最近很困惑，不知道该怎么办才好。")).human_review_required


def test_medical_topic_is_not_spiritualised():
    decision = precheck(_case("医生说我有抑郁症，需要吃药，但我不确定该怎么办。"))
    assert any("不得把医疗问题简化为属灵问题" in n for n in decision.notes)


def test_postcheck_blocks_soul_condemnation(influencer_case):
    decision = postcheck(influencer_case, "这个网红显然是被鬼附了，神已经定他的罪。")
    assert "soul_condemnation" in decision.blocked_patterns
    assert decision.required_rewrite


def test_postcheck_blocks_religious_coercion(scrupulosity_case):
    decision = postcheck(scrupulosity_case, "问题在于你还没认够罪。")
    assert "religious_coercion" in decision.blocked_patterns


def test_postcheck_passes_clean_text(influencer_case):
    assert postcheck(influencer_case, "这段材料值得进一步察验。").risk_level is RiskLevel.NONE


def test_declared_crisis_sensitivity_halts():
    decision = precheck(_case("我现在状态非常糟糕，需要有人帮我一下。", sensitivity=Sensitivity.CRISIS))
    assert decision.halt_normal_flow
