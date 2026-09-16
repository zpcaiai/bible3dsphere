"""Skill 08 - discernment-report-composer."""

import pytest

from backend.discernment_platform.batch01_core.claims import extract
from backend.discernment_platform.batch01_core.desire import map_desires
from backend.discernment_platform.batch01_core.gospel import build
from backend.discernment_platform.batch01_core.intake import normalize
from backend.discernment_platform.batch01_core.models import (
    FailureCode,
    ReviewStatus,
    RiskLevel,
    SafetyDecision,
    SkillFailure,
)
from backend.discernment_platform.batch01_core.pride import detect
from backend.discernment_platform.batch01_core.report import compose
from backend.discernment_platform.batch01_core.safety import precheck
from backend.discernment_platform.batch01_core.socratic import plan
from backend.discernment_platform.batch01_core.worldview import map_worldview


def _compose(case, safety=None):
    normalized = normalize(case)
    claims = extract(normalized)
    wv = map_worldview(normalized, claims)
    hypotheses = detect(normalized, claims, wv)
    desires = map_desires(normalized, wv, hypotheses)
    questions = plan(normalized, claims, wv, hypotheses, desires)
    bridge = build(normalized, wv, hypotheses, desires)
    return compose(
        normalized,
        claims,
        wv,
        hypotheses,
        desires,
        questions,
        bridge,
        safety or precheck(case),
    )


def test_report_always_has_limitations(influencer_case):
    assert _compose(influencer_case).limitations


def test_report_acknowledges_at_least_one_positive(influencer_case):
    assert _compose(influencer_case).affirmations


def test_report_delivers_only_one_leading_question(influencer_case):
    assert len(_compose(influencer_case).socratic_questions) == 1


def test_report_separates_observation_from_interpretation(influencer_case):
    report = _compose(influencer_case)
    assert "区分了观察、解释与假设" in report.summary
    for hypothesis in report.pride_hypotheses:
        assert hypothesis["observation"]
        assert hypothesis["interpretation_hypothesis"]


def test_high_risk_blocks_deep_report(influencer_case):
    high = SafetyDecision(stage="precheck", risk_level=RiskLevel.HIGH)
    with pytest.raises(SkillFailure) as exc:
        _compose(influencer_case, safety=high)
    assert exc.value.code is FailureCode.HIGH_RISK_REVIEW


def test_missing_intermediate_result_is_invalid(influencer_case):
    normalized = normalize(influencer_case)
    wv = map_worldview(normalized, [])
    with pytest.raises(SkillFailure) as exc:
        compose(normalized, [], wv, [], [], [], None, precheck(influencer_case))
    assert exc.value.code is FailureCode.MODEL_OUTPUT_INVALID


def test_limitations_state_no_mind_reading(influencer_case):
    assert any("不能读心" in item for item in _compose(influencer_case).limitations)


def test_limitations_disclaim_salvation_judgement(influencer_case):
    assert any("得救状态" in item for item in _compose(influencer_case).limitations)


def test_review_status_follows_safety(influencer_case):
    report = _compose(influencer_case)
    assert report.review_status in (
        ReviewStatus.READY,
        ReviewStatus.HUMAN_REVIEW_REQUIRED,
    )


def test_self_mirror_is_always_present(influencer_case):
    assert _compose(influencer_case).self_mirror
