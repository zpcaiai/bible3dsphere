"""End-to-end pipeline tests."""

from backend.discernment_platform.batch01_core import DiscernmentCase, DiscernmentOrchestrator
from backend.discernment_platform.batch01_core.models import CaseState, ConsentScope, SubjectType


def test_e2e_influencer_reaches_ready(influencer_case):
    result = DiscernmentOrchestrator().run(influencer_case)
    assert result["state"] in (CaseState.READY.value, CaseState.REVIEW_REQUIRED.value)
    assert result["report"]
    assert result["production_ready"]


def test_e2e_self_control_produces_full_report(self_control_case):
    result = DiscernmentOrchestrator().run(self_control_case)
    assert result["report"]["limitations"]
    assert result["report"]["affirmations"]


def test_e2e_scrupulosity_halts_before_deep_analysis(scrupulosity_case):
    result = DiscernmentOrchestrator().run(scrupulosity_case)
    assert result["report"] is None
    assert result["failure"] == "HIGH_RISK_REVIEW"
    assert result["support_guidance"]
    assert not result["production_ready"]


def test_e2e_trace_is_complete_on_success(influencer_case):
    result = DiscernmentOrchestrator().run(influencer_case)
    assert not result["trace_bundle"]["missing_skills"]


def test_e2e_redacted_view_hides_internal_sections(influencer_case):
    result = DiscernmentOrchestrator().run(influencer_case)
    assert "pride_hypotheses" not in result["redacted_user_view"]


def test_e2e_without_spiritual_consent_stops_at_content_analysis(influencer_case):
    influencer_case.consent_scope = ConsentScope(
        allow_spiritual_analysis=False, allow_gospel_bridge=False
    )
    result = DiscernmentOrchestrator().run(influencer_case)
    assert result["failure"] == "USER_CONSENT_REQUIRED"
    assert result["content_analysis"]["claims"]
    assert "pride_hypotheses" not in result


def test_e2e_short_input_fails_with_insufficient_evidence():
    case = DiscernmentCase(
        case_id="e-1",
        subject_type=SubjectType.IDEA,
        raw_input="很短",
        user_goal="辨识",
        consent_scope=ConsentScope(
            allow_spiritual_analysis=True, allow_gospel_bridge=True
        ),
    )
    result = DiscernmentOrchestrator().run(case)
    assert result["failure"] == "INSUFFICIENT_EVIDENCE"


def test_e2e_review_packet_is_available(influencer_case):
    result = DiscernmentOrchestrator().run(influencer_case)
    assert result["review_packet"]["trace_records"]


def test_e2e_postcheck_runs_on_output(influencer_case):
    result = DiscernmentOrchestrator().run(influencer_case)
    assert result["safety"]["postcheck"]["stage"] == "postcheck"


def test_e2e_all_ten_skills_are_declared():
    from backend.discernment_platform.batch01_core import SKILL_IDS

    assert len(SKILL_IDS) == 10
