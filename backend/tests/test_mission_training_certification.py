"""Batch 4 invariants: training, language, practicum, exposure, certification."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from fastapi.routing import APIRoute
from mission_os import training as tr
from mission_os import practicum as pr
from mission_os import certification as ce
from routers.mission_training import router as training_router, lang_router
from routers.mission_certification import router as cert_router, practicum_router

pytestmark = pytest.mark.no_db
MIG = Path(__file__).parents[1] / "migrations"


# ---- Skill 37: training plan ----
def test_gap_must_have_module_and_hard_block_not_course_only():
    with pytest.raises(ValueError):
        tr.validate_gap_has_module("teamwork", [])
    tr.validate_gap_has_module("teamwork", ["team_exercise"])
    with pytest.raises(ValueError):
        tr.assert_hard_block_not_course_only(is_hard_block=True, module_types=["course", "reading"])
    tr.assert_hard_block_not_course_only(is_hard_block=True, module_types=["course", "restoration_action"])
    tr.assert_hard_block_not_course_only(is_hard_block=False, module_types=["course"])  # non-block ok


def test_habits_require_confirmation():
    with pytest.raises(ValueError):
        tr.habits_require_user_confirmation(False)
    tr.habits_require_user_confirmation(True)


# ---- Skill 44: language ----
def test_self_and_ai_cannot_certify_and_high_level_needs_native():
    with pytest.raises(ValueError):
        tr.can_certify_language_level(level="L2", assessor_type="self")
    with pytest.raises(ValueError):
        tr.can_certify_language_level(level="L2", assessor_type="ai")
    with pytest.raises(ValueError):
        tr.can_certify_language_level(level="L4", assessor_type="self")
    tr.can_certify_language_level(level="L2", assessor_type="native_speaker")
    tr.can_certify_language_level(level="L5", assessor_type="authorized_assessor")


def test_cultural_observation_needs_local_explanation_for_high_confidence():
    assert tr.cultural_observation_confidence(has_local_explanation=False, requested_confidence="high") == "low"
    assert tr.cultural_observation_confidence(has_local_explanation=True, requested_confidence="high") == "high"


# ---- Skill 45: professional ----
def test_no_fake_identity_and_regulated_needs_verification():
    with pytest.raises(ValueError):
        tr.assert_no_fake_identity("fake_employment")
    with pytest.raises(ValueError):
        tr.professional_qualification_ok(profession="medicine", verification_status="unverified", is_expired=False)
    with pytest.raises(ValueError):
        tr.professional_qualification_ok(profession="nursing", verification_status="verified", is_expired=True)
    tr.professional_qualification_ok(profession="medicine", verification_status="verified", is_expired=False)
    tr.professional_qualification_ok(profession="software", verification_status="unverified", is_expired=False)  # unregulated ok


# ---- Skill 46: practicum ----
def test_practicum_cannot_start_without_host_supervisor_safeguarding():
    with pytest.raises(ValueError):
        pr.assert_can_start_practicum(has_host=False, has_supervisor=True, safeguarding_current=True, required_training_done=True)
    with pytest.raises(ValueError):
        pr.assert_can_start_practicum(has_host=True, has_supervisor=False, safeguarding_current=True, required_training_done=True)
    with pytest.raises(ValueError):
        pr.assert_can_start_practicum(has_host=True, has_supervisor=True, safeguarding_current=False, required_training_done=True)
    pr.assert_can_start_practicum(has_host=True, has_supervisor=True, safeguarding_current=True, required_training_done=True)


def test_prohibited_activities_always_enforced_and_service_unaffected():
    with pytest.raises(ValueError):
        pr.validate_activities(allowed=["unsupervised_minor_contact"], prohibited=[])
    pr.validate_activities(allowed=["observation", "language_exchange"], prohibited=[])
    with pytest.raises(ValueError):
        pr.service_unaffected_by_faith_refusal(participant_refused_faith=True, service_reduced=True)
    pr.service_unaffected_by_faith_refusal(participant_refused_faith=True, service_reduced=False)


# ---- Skill 47: exposure ----
def test_short_exposure_never_long_term_and_non_objectives_required():
    assert pr.evidence_weight_for_exposure("short_observation_trip") == "exposure"
    assert pr.evidence_weight_for_exposure("cross_cultural_internship") == "long_term_experience"
    with pytest.raises(ValueError):
        pr.assert_not_overstated(exposure_type="local_exposure_day", claimed_weight="long_term_experience")
    with pytest.raises(ValueError):
        pr.require_non_objectives([])
    pr.require_non_objectives(["not a deployment qualification"])
    with pytest.raises(ValueError):
        pr.assert_long_term_internship_ready(has_receiving_team=True, has_language_goal=True, has_supervisor=True, has_local_feedback=False)


# ---- Skill 43/49: certification ----
def test_batch4_cannot_issue_deployment_approval():
    with pytest.raises(ValueError):
        ce.certification_type_allowed("deployment_approved")
    ce.certification_type_allowed("local_practicum_completed")


def test_quiz_only_and_simulation_only_cannot_certify():
    with pytest.raises(ValueError):
        ce.assert_not_knowledge_only(["quiz", "written_assignment"])
    with pytest.raises(ValueError):
        ce.assert_not_simulation_only(["simulation"])
    ce.assert_not_knowledge_only(["quiz", "supervised_practice"])


def test_high_risk_needs_two_evidence_classes_and_second_reviewer():
    with pytest.raises(ValueError):  # observer == observed
        ce.can_certify(evidence_classes=["supervised_practice", "mentor_observation"], high_risk=True,
                       reviewer_ids=["a", "b"], observer_id="x", observed_id="x")
    with pytest.raises(ValueError):  # single evidence class
        ce.can_certify(evidence_classes=["supervised_practice"], high_risk=True,
                       reviewer_ids=["a", "b"], observer_id="o", observed_id="w")
    with pytest.raises(ValueError):  # single reviewer
        ce.can_certify(evidence_classes=["supervised_practice", "mentor_observation"], high_risk=True,
                       reviewer_ids=["a"], observer_id="o", observed_id="w")
    ce.can_certify(evidence_classes=["supervised_practice", "mentor_observation"], high_risk=True,
                   reviewer_ids=["a", "b"], observer_id="o", observed_id="w")


def test_rubric_rejects_vague_spiritual_adjectives():
    with pytest.raises(ValueError):
        ce.validate_rubric_criterion("很属灵")
    with pytest.raises(ValueError):
        ce.validate_rubric_criterion("anointed")
    ce.validate_rubric_criterion("accurately restates the other person's view")


def test_safeguarding_contact_requires_level_and_unexpired():
    now = datetime.now(timezone.utc)
    assert ce.safeguarding_contact_allowed(level="contact_ready", expires_at=now + timedelta(days=30), now=now)
    assert not ce.safeguarding_contact_allowed(level="awareness_completed", expires_at=now + timedelta(days=30), now=now)
    assert not ce.safeguarding_contact_allowed(level="contact_ready", expires_at=now - timedelta(days=1), now=now)  # expiry suspends
    assert not ce.safeguarding_contact_allowed(level=None, expires_at=None, now=now)


def test_safeguarding_requires_human_scenario():
    with pytest.raises(ValueError):
        ce.assert_safeguarding_requires_human_scenario(has_human_scenario_assessment=False)
    ce.assert_safeguarding_requires_human_scenario(has_human_scenario_assessment=True)


# ---- migrations ----
@pytest.mark.parametrize("fname,rls_count", [
    ("0195_mission_os_training.sql", 7),
    ("0196_mission_os_practicum.sql", 5),
    ("0197_mission_os_certification.sql", 5),
])
def test_migrations_rls_and_rollback(fname, rls_count):
    sql = (MIG / fname).read_text()
    assert sql.count("ENABLE ROW LEVEL SECURITY") == rls_count
    assert "current_setting(''app.tenant_id'',true)" in sql
    assert "-- Rollback:" in sql


def test_key_migration_checks_present():
    train = (MIG / "0195_mission_os_training.sql").read_text()
    assert "NOT verified OR assessor_type IN('native_speaker','authorized_assessor')" in train
    assert "confidence<>'high' OR local_explanation IS NOT NULL" in train
    prac = (MIG / "0196_mission_os_practicum.sql").read_text()
    assert "jsonb_array_length(non_objectives)>0" in prac
    cert = (MIG / "0197_mission_os_certification.sql").read_text()
    assert "second_reviewer_id<>decided_by" in cert
    assert "certification_level='awareness_completed' OR human_scenario_assessment_passed" in cert
    # deployment_approved is NOT an allowed certification type
    assert "deployment_approved" not in cert


# ---- API contract ----
def test_batch4_api_contract_exists():
    routes = {(r.path, m) for r in list(training_router.routes) + list(lang_router.routes) + list(cert_router.routes) + list(practicum_router.routes)
              if isinstance(r, APIRoute) for m in r.methods}
    expected = {
        ("/api/v1/mission/training-plans", "POST"),
        ("/api/v1/mission/language-plans/{plan_id}/assessments", "POST"),
        ("/api/v1/mission/practicum-placements/{placement_id}/start", "POST"),
        ("/api/v1/mission/certifications/stage", "POST"),
        ("/api/v1/mission/certifications/safeguarding/contact-allowed", "GET"),
    }
    assert expected <= routes
