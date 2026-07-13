"""Batch 6 invariants: finance, identity/credentials, health/family, security/gate."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import pytest
from fastapi.routing import APIRoute
from mission_os import finance as fin
from mission_os import identity as idn
from mission_os import health_family as hf
from mission_os import deployment as dep
from routers.mission_finance import router as fin_router, campaign_router, expense_router
from routers.mission_deployment import identity_router, credential_router, family_router, gate_router

pytestmark = pytest.mark.no_db
MIG = Path(__file__).parents[1] / "migrations"


# ---- Skill 61: budget ----
def test_required_scenarios_and_evacuation_and_education():
    with pytest.raises(ValueError):
        fin.assert_scenarios_complete(["baseline", "conservative"], high_risk_field=False, has_children=False)
    with pytest.raises(ValueError):
        fin.assert_scenarios_complete(["baseline", "conservative", "support_loss"], high_risk_field=True, has_children=False)
    with pytest.raises(ValueError):
        fin.assert_scenarios_complete(["baseline", "conservative", "support_loss"], high_risk_field=False, has_children=True)
    fin.assert_scenarios_complete(["baseline", "conservative", "support_loss", "evacuation", "education_cost_increase"],
                                  high_risk_field=True, has_children=True)


def test_one_time_gift_not_annualized_and_pledge_not_receipt():
    assert fin.annualize_income(amount=1000, recurrence_type="one_time") == 0.0
    assert fin.annualize_income(amount=100, recurrence_type="monthly") == 1200
    assert fin.committed_income([{"kind": "committed", "received": True, "amount": 50},
                                 {"kind": "probable", "received": False, "amount": 999}]) == 50


def test_reserve_and_readiness_signals():
    assert fin.reserve_ok(reserve_type="evacuation", current_amount=100, minimum_required=100)
    assert not fin.reserve_ok(reserve_type="evacuation", current_amount=50, minimum_required=100)
    r = fin.financial_readiness(startup_pct=1.0, monthly_coverage_pct=1.2, reserve_months=1,
                                insurance_gap=True, blocking=["reserve_insufficient"])
    assert r["monthly_coverage_pct"] == 1.0 and r["blocked"] and "startup_pct" in r


# ---- Skill 62/63/64: support, funds, fraud ----
def test_campaign_ethics_and_pledge_no_governance():
    assert "guilt_pressure" in fin.scan_campaign(tactics=["guilt_pressure"], content_keys=[])
    assert "minor_story" in fin.scan_campaign(tactics=[], content_keys=["minor_story"])
    assert fin.scan_campaign(tactics=["testimony"], content_keys=["thanksgiving"]) == []
    with pytest.raises(ValueError):
        fin.pledge_grants_no_governance("governance")
    fin.pledge_grants_no_governance("prayer")


def test_expense_self_approval_dual_threshold_and_sod():
    with pytest.raises(ValueError):
        fin.assert_expense_approval(requester_id="a", approver_id="a", amount=10, approvals=1, dual_threshold=1000)
    with pytest.raises(ValueError):
        fin.assert_expense_approval(requester_id="a", approver_id="b", amount=5000, approvals=1, dual_threshold=1000)
    fin.assert_expense_approval(requester_id="a", approver_id="b", amount=5000, approvals=2, dual_threshold=1000)
    with pytest.raises(ValueError):
        fin.assert_separation_of_duties(["request_expense", "approve_expense", "release_funds", "reconcile"])
    with pytest.raises(ValueError):
        fin.assert_restricted_transfer(source_restriction="restricted", dest_restriction="general")


def test_anomaly_not_verdict_and_investigator_independent():
    assert fin.finding_is_not_verdict("duplicate_expense") == "requires_human_investigation"
    with pytest.raises(ValueError):
        fin.assert_investigator_independent(subject_id="x", investigator_id="x")


# ---- Skill 65/66/67: identity, credentials, compliance ----
def test_identity_consistency_and_no_fake_and_licence():
    with pytest.raises(ValueError):
        idn.assert_identity_consistent(declared_activity="teacher", actual_activity="pastor")
    with pytest.raises(ValueError):
        idn.assert_no_fake_identity("fake_employment")
    with pytest.raises(ValueError):
        idn.assert_regulated_licensed(activity="medicine", has_license=False)
    idn.assert_regulated_licensed(activity="medicine", has_license=True)


def test_credential_masking_and_expiry_block_and_ai_no_file():
    assert idn.mask_identifier("A1234567").startswith("****")
    with pytest.raises(ValueError):
        idn.assert_no_full_identifier_in_dto({"passport_number": "A1234567"})
    idn.assert_no_full_identifier_in_dto({"passport_number": "****567"})
    today = date(2026, 1, 1)
    assert idn.credential_blocks_deployment(credential_type="passport", expires_at=date(2026, 3, 1),
                                            min_validity_days=180, now=today)
    assert not idn.credential_blocks_deployment(credential_type="driver_license", expires_at=None,
                                               min_validity_days=180, now=today)
    assert idn.ai_may_access_credential_file() is False


def test_compliance_opinion_expiry_jurisdiction_and_ai_cannot_clear():
    today = date(2026, 1, 1)
    assert idn.opinion_valid(issued_at=date(2025, 6, 1), expires_at=date(2026, 6, 1), now=today)
    assert not idn.opinion_valid(issued_at=date(2024, 1, 1), expires_at=None, now=today)
    assert not idn.opinion_transfers(opinion_jurisdiction="US", target_jurisdiction="TH")
    with pytest.raises(ValueError):
        idn.assert_ai_cannot_clear_legal("ai", "cleared")
    assert idn.domain_needs_professional(domain="immigration", risk_level="low")


# ---- Skill 68/69: health & family ----
def test_committee_only_sees_summary_and_ai_no_diagnosis():
    assert hf.committee_view("cleared") == "cleared"
    assert hf.committee_view("assessment_pending") == "additional_review_required"
    assert hf.ai_may_diagnose_or_prescribe() is False
    with pytest.raises(ValueError):
        hf.assert_ai_medical_action("prescribe")
    assert hf.disability_auto_rejects() is False


def test_medication_and_insurance_block():
    assert not hf.medication_continuity_ok(ongoing_required=True, local_availability="unavailable", has_backup_plan=False)
    assert hf.medication_continuity_ok(ongoing_required=True, local_availability="available", has_backup_plan=True)
    assert hf.insurance_blocks_high_risk(gaps=["evacuation_missing"], high_risk_field=True)
    assert not hf.insurance_blocks_high_risk(gaps=["dental_excluded"], high_risk_field=True)


def test_spouse_review_authentic_and_consent_blocks_and_education_legal():
    with pytest.raises(ValueError):
        hf.assert_spouse_review_authentic(submitter_id="candidate", spouse_user_id="spouse")
    hf.assert_spouse_review_authentic(submitter_id="spouse", spouse_user_id="spouse")
    assert hf.spouse_consent_blocks_family_move("does_not_consent")
    assert not hf.spouse_consent_blocks_family_move("supportive")
    with pytest.raises(ValueError):
        hf.assert_education_legal(education_model="homeschool_where_legal", legal_in_region=False)
    g = hf.family_gate(spouse_willingness="does_not_consent", child_education_ready=True,
                       child_safeguarding_ready=True, dependent_care_ready=True, family_budget_ready=True)
    assert not g["ready"] and "spouse_not_consenting" in g["blocking"]


# ---- Skill 70/71: security, emergency, gate ----
def test_p4_unmanaged_device_and_lost_and_exit_revocation():
    with pytest.raises(ValueError):
        dep.assert_p4_storage(data_class="P4", device_managed=False)
    dep.assert_p4_storage(data_class="P4", device_managed=True)
    assert dep.access_revoked_on_lost_device(True)
    assert dep.access_revoked_on_team_exit("ended")
    with pytest.raises(ValueError):
        dep.assert_exception_has_expiry(None)
    with pytest.raises(ValueError):
        dep.assert_shared_account_blocked(is_shared=True, has_approved_exception=False)


def test_command_not_concentrated_and_evac_triggers_and_ai_no_evac():
    with pytest.raises(ValueError):
        dep.assert_command_not_concentrated(role_holders={"incident_commander": "x", "security_lead": "x"}, high_risk=True)
    dep.assert_command_not_concentrated(role_holders={"incident_commander": "x", "security_lead": "y"}, high_risk=True)
    with pytest.raises(ValueError):
        dep.validate_evacuation_trigger("bad_feeling")
    dep.validate_evacuation_trigger("official_evacuation_advisory")
    assert dep.ai_may_decide_evacuation() is False


def test_deployment_gate_hard_block_panel_and_ready_does_not_activate():
    blocked = dep.run_gate(hard_blocks=["medical_not_cleared"], decider_type="human", is_panel=True,
                           candidate_id="c", decider_id="p")
    assert blocked["status"] == "blocked"
    with pytest.raises(ValueError):
        dep.run_gate(hard_blocks=[], decider_type="ai", is_panel=True, candidate_id="c", decider_id="p")
    with pytest.raises(ValueError):
        dep.run_gate(hard_blocks=[], decider_type="human", is_panel=True, candidate_id="c", decider_id="c")
    with pytest.raises(ValueError):
        dep.run_gate(hard_blocks=[], decider_type="human", is_panel=False, candidate_id="c", decider_id="p")
    ready = dep.run_gate(hard_blocks=[], decider_type="human", is_panel=True, candidate_id="c", decider_id="p")
    assert ready["status"] == "ready_for_deployment_planning" and ready["unlocks"] == "deployment_planning"
    assert dep.gate_ready_activates_deployment() is False


# ---- migrations ----
@pytest.mark.parametrize("fname,rls_count", [
    ("0201_mission_os_financial_plans.sql", 5),
    ("0202_mission_os_support_funds.sql", 8),
    ("0203_mission_os_identity_credentials.sql", 5),
    ("0204_mission_os_compliance.sql", 6),
    ("0205_mission_os_health_family.sql", 8),
    ("0206_mission_os_security_deployment.sql", 7),
])
def test_migrations_rls_and_rollback(fname, rls_count):
    sql = (MIG / fname).read_text()
    assert sql.count("ENABLE ROW LEVEL SECURITY") == rls_count
    assert "current_setting(''app.tenant_id'',true)" in sql
    assert "-- Rollback:" in sql


def test_key_batch6_migration_checks():
    pledge = (MIG / "0202_mission_os_support_funds.sql").read_text()
    assert "CHECK(governance_rights_none)" in pledge
    cred = (MIG / "0203_mission_os_identity_credentials.sql").read_text()
    assert "masked_identifier LIKE '****%'" in cred
    fam = (MIG / "0205_mission_os_health_family.sql").read_text()
    assert "submitted_by=spouse_user_id" in fam
    assert "education_model<>'homeschool_where_legal' OR legal_in_region" in fam
    comp = (MIG / "0204_mission_os_compliance.sql").read_text()
    assert "expires_at>=issued_at" in comp


# ---- API contract ----
def test_batch6_api_contract_exists():
    routes = {(r.path, m) for r in (list(fin_router.routes) + list(campaign_router.routes) + list(expense_router.routes)
              + list(identity_router.routes) + list(credential_router.routes) + list(family_router.routes) + list(gate_router.routes))
              if isinstance(r, APIRoute) for m in r.methods}
    expected = {
        ("/api/v1/mission/financial-plans", "POST"),
        ("/api/v1/mission/support-campaigns/publish", "POST"),
        ("/api/v1/mission/expense-requests/approve", "POST"),
        ("/api/v1/mission/legal-identity-paths", "POST"),
        ("/api/v1/mission/credentials", "POST"),
        ("/api/v1/mission/family-readiness-plans/{family_plan_id}/spouse-review", "POST"),
        ("/api/v1/mission/deployment-readiness-gates/run", "POST"),
    }
    assert expected <= routes
