"""Batch 3 invariants: calling journey, motives, confirmation, readiness, AI boundaries."""
from pathlib import Path
import pytest
from fastapi.routing import APIRoute
from mission_os import calling as ca
from mission_os import readiness as rd
from mission_os import ai_boundaries as ai
from routers.mission_calling import router as calling_router
from routers.mission_readiness import router as readiness_router

pytestmark = pytest.mark.no_db
MIG = Path(__file__).parents[1] / "migrations"


# ---- Skill 28: calling gate ----
def test_subjective_impression_alone_cannot_pass_gate():
    with pytest.raises(ValueError):
        ca.readiness_gate(has_church_or_mentor_feedback=True, has_local_practice=True,
                          motive_assessment_complete=True, unresolved_hard_blocks=0,
                          evidence_types=["subjective_impression"])


def test_gate_requires_church_feedback_and_local_practice():
    with pytest.raises(ValueError):
        ca.readiness_gate(has_church_or_mentor_feedback=False, has_local_practice=True,
                          motive_assessment_complete=True, unresolved_hard_blocks=0,
                          evidence_types=["church_feedback"])
    with pytest.raises(ValueError):
        ca.readiness_gate(has_church_or_mentor_feedback=True, has_local_practice=False,
                          motive_assessment_complete=True, unresolved_hard_blocks=0,
                          evidence_types=["church_feedback"])
    ca.readiness_gate(has_church_or_mentor_feedback=True, has_local_practice=True,
                      motive_assessment_complete=True, unresolved_hard_blocks=0,
                      evidence_types=["church_feedback", "local_practice"])


def test_unresolved_hard_block_prevents_gate():
    with pytest.raises(ValueError):
        ca.readiness_gate(has_church_or_mentor_feedback=True, has_local_practice=True,
                          motive_assessment_complete=True, unresolved_hard_blocks=1,
                          evidence_types=["church_feedback", "local_practice"])


# ---- Skill 29: blockers ----
def test_hard_block_blocks_deployment_and_only_human_clears():
    assert ca.blocks_deployment_candidate(["development_needed", "hard_block"])
    assert not ca.blocks_deployment_candidate(["observation"])
    with pytest.raises(ValueError):
        ca.can_clear_blocker(actor_type="ai")
    ca.can_clear_blocker(actor_type="human")


# ---- Skill 30: confirmation ----
def test_candidate_cannot_confirm_self_and_feedback_not_averaged():
    with pytest.raises(ValueError):
        ca.validate_feedback_request(requester_id="u1", respondent_id="u1", respondent_type="pastor")
    agg = ca.aggregate_is_not_average(["support_continue", "significant_concern"])
    assert agg["has_conflict"] and agg["total"] == 2


# ---- Skill 35: pause / appeal ----
def test_pause_is_non_shaming_and_appeal_independent():
    with pytest.raises(ValueError):
        ca.assert_pause_label_is_not_shaming("failure")
    ca.assert_pause_label_is_not_shaming("resting and receiving support")
    with pytest.raises(ValueError):
        ca.can_review_appeal(appellant_id="a", reviewer_id="d", original_decider_id="d")
    ca.can_review_appeal(appellant_id="a", reviewer_id="c", original_decider_id="d")


# ---- Skill 34: readiness ----
def test_readiness_has_fifteen_dimensions_no_total_score():
    assert len(rd.READINESS_DIMENSIONS) == 15


def test_hard_block_forces_pause_and_restore():
    dims = {k: "strong" for k in rd.READINESS_DIMENSIONS}
    lvl = rd.resolve_readiness_level(dimensions=dims, hard_blocks=["no_active_sending_church"], evidence_complete=True)
    assert lvl == "pause_and_restore"


def test_protected_attribute_cannot_downgrade():
    with pytest.raises(ValueError):
        rd.assert_not_protected_downgrade(["single"])
    with pytest.raises(ValueError):
        rd.assert_not_protected_downgrade(["female", "introvert"])
    rd.assert_not_protected_downgrade(["professional_incompetence"])  # legitimate reason ok


def test_deployment_candidate_requires_panel_not_ai_not_self():
    with pytest.raises(ValueError):
        rd.can_decide_deployment_candidate(decider_type="ai", is_panel=True, candidate_id="c", decider_id="p", hard_blocks=[])
    with pytest.raises(ValueError):
        rd.can_decide_deployment_candidate(decider_type="human", is_panel=True, candidate_id="c", decider_id="c", hard_blocks=[])
    with pytest.raises(ValueError):
        rd.can_decide_deployment_candidate(decider_type="human", is_panel=False, candidate_id="c", decider_id="p", hard_blocks=[])
    with pytest.raises(ValueError):
        rd.can_decide_deployment_candidate(decider_type="human", is_panel=True, candidate_id="c", decider_id="p", hard_blocks=["no_team_when_field_requires"])
    rd.can_decide_deployment_candidate(decider_type="human", is_panel=True, candidate_id="c", decider_id="p", hard_blocks=[])


# ---- Skill 33: match separation ----
def test_role_field_deployment_layers_are_separate():
    rd.assert_layers_separate("field_match", "role_match")   # ok
    with pytest.raises(ValueError):
        rd.assert_layers_separate("deployment", "role_match")  # cannot skip field_match
    with pytest.raises(ValueError):
        rd.assert_layers_separate("field_match", None)


def test_role_match_missing_data_is_not_deficiency():
    r = rd.role_match(worker_levels={}, required_levels={"teamwork": "strong"},
                      missing_dimensions=["teamwork"], hard_blocks=[])
    assert r == "insufficient_evidence"
    r2 = rd.role_match(worker_levels={"teamwork": "strong"}, required_levels={"teamwork": "strong"},
                       missing_dimensions=[], hard_blocks=[])
    assert r2 == "team_discernment"


# ---- Skill 32: role qualification ----
def test_children_and_medical_roles_require_hard_qualification():
    assert rd.role_requires_hard_qualification("children_and_family_worker")
    assert rd.role_requires_hard_qualification("medical_worker")
    assert not rd.role_requires_hard_qualification("digital_infrastructure_engineer")


# ---- Skill 36: AI boundaries ----
def test_ai_cannot_perform_forbidden_actions():
    for act in ("declare_divine_calling", "approve_readiness", "clear_hard_block", "approve_deployment"):
        with pytest.raises(ValueError):
            ai.assert_ai_action_allowed(act)


def test_ai_output_scan_detects_divine_call_and_coercion():
    assert "divine_call_declaration" in ai.scan_output("上帝已经呼召你去那里")
    assert "divine_call_declaration" in ai.scan_output("God has called you to go")
    assert "obedience_coercion" in ai.scan_output("你不去就是悖逆")
    assert ai.scan_output("这是一些需要进一步确认的证据") == []


def test_ai_draft_decision_is_forced_null():
    safe = ai.sanitize_decision_field({"decision": "approved", "summary": "x"})
    assert safe["decision"] is None and safe["requires_human_review"] is True


def test_p4_never_enters_model():
    with pytest.raises(ValueError):
        ai.assert_model_input_allowed(["P2", "P4"])
    ai.assert_model_input_allowed(["P1", "P2"])


# ---- migrations ----
@pytest.mark.parametrize("fname,rls_count", [
    ("0192_mission_os_calling.sql", 8),
    ("0193_mission_os_worker_readiness.sql", 6),
    ("0194_mission_os_ai_governance.sql", 3),
])
def test_migrations_rls_and_rollback(fname, rls_count):
    sql = (MIG / fname).read_text()
    assert sql.count("ENABLE ROW LEVEL SECURITY") == rls_count
    assert "current_setting(''app.tenant_id'',true)" in sql
    assert "-- Rollback:" in sql


def test_feedback_request_self_check_and_appeal_check_in_migration():
    sql = (MIG / "0192_mission_os_calling.sql").read_text()
    assert "respondent_user_id<>requester_id" in sql
    assert "independent_reviewer_id<>appellant_id" in sql


def test_prompt_registry_and_redteam_seed_present():
    sql = (MIG / "0194_mission_os_ai_governance.sql").read_text()
    assert "mission.calling.reflection" in sql
    assert "redteam_divine_call" in sql
    assert "'[\"P4\"]'::jsonb" in sql  # prohibited data classes default to P4


# ---- API contract ----
def test_batch3_api_contract_exists():
    routes = {(r.path, m) for r in list(calling_router.routes) + list(readiness_router.routes)
              if isinstance(r, APIRoute) for m in r.methods}
    expected = {
        ("/api/v1/mission/calling-journeys", "POST"),
        ("/api/v1/mission/calling-journeys/{journey_id}/reflections", "POST"),
        ("/api/v1/mission/calling-journeys/{journey_id}/feedback-requests", "POST"),
        ("/api/v1/mission/calling-journeys/{journey_id}/submit-readiness-gate", "POST"),
        ("/api/v1/mission/readiness-assessments", "POST"),
        ("/api/v1/mission/readiness-assessments/{assessment_id}/dimensions", "POST"),
        ("/api/v1/mission/readiness-assessments/{assessment_id}/panel-decision", "POST"),
        ("/api/v1/mission/readiness-assessments/{assessment_id}/ai-draft", "POST"),
    }
    assert expected <= routes
