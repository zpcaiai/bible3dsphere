"""Batch 5 invariants: church confirmation, committee, teams, partners, support."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from fastapi.routing import APIRoute
from mission_os import sending as sd
from mission_os import team as tm
from mission_os import partnership as pn
from routers.mission_sending import router as sending_router
from routers.mission_partnership import teams_router, partners_router, support_router

pytestmark = pytest.mark.no_db
MIG = Path(__file__).parents[1] / "migrations"


# ---- Skill 50: church confirmation ----
def test_single_pastor_cannot_confirm_alone():
    with pytest.raises(ValueError):
        sd.assert_church_confirmation_valid(reviewer_ids=["p1"], family_reviewer_ids=[], observation_months=12)
    with pytest.raises(ValueError):  # all family
        sd.assert_church_confirmation_valid(reviewer_ids=["f1", "f2"], family_reviewer_ids=["f1", "f2"], observation_months=12)
    with pytest.raises(ValueError):  # too short
        sd.assert_church_confirmation_valid(reviewer_ids=["p1", "p2"], family_reviewer_ids=[], observation_months=1)
    sd.assert_church_confirmation_valid(reviewer_ids=["p1", "p2"], family_reviewer_ids=["f1"], observation_months=12)


# ---- Skill 52: application ----
def test_application_completeness_and_expiry_and_partner():
    full = list(sd.REQUIRED_APPLICATION_SECTIONS)
    with pytest.raises(ValueError):  # expired readiness
        sd.assert_can_submit(present_sections=full, expired_sections=[], blocking_sections=[],
                             readiness_expired=True, local_partner_present=True, field_requires_partner=True)
    with pytest.raises(ValueError):  # missing partner
        sd.assert_can_submit(present_sections=full, expired_sections=[], blocking_sections=[],
                             readiness_expired=False, local_partner_present=False, field_requires_partner=True)
    with pytest.raises(ValueError):  # missing sections
        sd.assert_can_submit(present_sections=["calling_journey"], expired_sections=[], blocking_sections=[],
                             readiness_expired=False, local_partner_present=True, field_requires_partner=True)
    sd.assert_can_submit(present_sections=full, expired_sections=[], blocking_sections=[],
                         readiness_expired=False, local_partner_present=True, field_requires_partner=True)


def test_core_field_change_requires_new_version():
    assert sd.requires_new_version(["target_field_id"])
    assert not sd.requires_new_version(["intended_start_window"])


# ---- Skill 53: committee ----
def _members():
    return [
        {"user_id": "u_church", "member_role": "sending_church", "voting_right": True},
        {"user_id": "u_agency", "member_role": "mission_agency", "voting_right": True},
        {"user_id": "u_team", "member_role": "receiving_team", "voting_right": True},
        {"user_id": "u_ind", "member_role": "independent", "voting_right": True},
    ]


def test_candidate_and_ai_and_coi_excluded_from_quorum():
    members = _members() + [
        {"user_id": "cand", "member_role": "independent", "voting_right": True},
        {"user_id": "bot", "member_role": "independent", "is_ai": True, "voting_right": True},
        {"user_id": "coi", "member_role": "independent", "conflict_disclosed": True, "voting_right": True},
    ]
    voters = sd.eligible_voters(members, "cand")
    ids = {m["user_id"] for m in voters}
    assert "cand" not in ids and "bot" not in ids and "coi" not in ids
    sd.assert_quorum(members, "cand", min_quorum=4)
    with pytest.raises(ValueError):  # too few after exclusions
        sd.assert_quorum(_members()[:2], "cand", min_quorum=4)


def test_spouse_or_partner_opposition_blocks_and_conditions_need_owner_deadline():
    with pytest.raises(ValueError):
        sd.assert_can_approve(spouse_opposed=True, local_partner_opposed=False, unresolved_hard_blocks=0)
    with pytest.raises(ValueError):
        sd.assert_can_approve(spouse_opposed=False, local_partner_opposed=True, unresolved_hard_blocks=0)
    with pytest.raises(ValueError):
        sd.assert_can_approve(spouse_opposed=False, local_partner_opposed=False, unresolved_hard_blocks=1)
    sd.assert_can_approve(spouse_opposed=False, local_partner_opposed=False, unresolved_hard_blocks=0)
    with pytest.raises(ValueError):
        sd.validate_conditional_approval([{"text": "x"}])  # no owner/deadline
    sd.validate_conditional_approval([{"text": "x", "owner": "o", "deadline": "2026-01-01"}])


def test_approval_only_unlocks_batch6():
    assert sd.approval_unlocks_batch6_only() == "unlock_batch6_preparation"


# ---- Skill 54/55/56/57: teams ----
def test_leader_cannot_self_approve_and_spouse_not_auto_member():
    with pytest.raises(ValueError):
        tm.assert_membership_approval(approver_id="leader", candidate_id="leader", is_leader_self=True)
    with pytest.raises(ValueError):
        tm.assert_spouse_not_auto_member(is_spouse=True, has_own_membership_decision=False)
    tm.assert_spouse_not_auto_member(is_spouse=True, has_own_membership_decision=True)
    assert tm.access_after_exit("active") and not tm.access_after_exit("ended")


def test_single_point_of_failure_and_capacity_and_need_cannot_bypass():
    spof = tm.detect_single_point_of_failure({"safeguarding": ["a"], "member_care": ["a", "b"], "security": [], "legal_and_compliance": ["c", "d"]})
    assert "safeguarding" in spof and "security" in spof and "member_care" not in spof
    assert tm.team_capacity_hours(work_hours=50, language_hours=10, family_hours=15, rest_hours=10, admin_hours=5) == 10
    with pytest.raises(ValueError):
        tm.high_need_cannot_bypass_gap(has_critical_gap=True, field_need_high=True)


def test_covenant_forbids_absolute_obedience_and_requires_sections():
    with pytest.raises(ValueError):
        tm.validate_covenant(clauses=["absolute_obedience"], sections=list(tm.REQUIRED_COVENANT_SECTIONS))
    with pytest.raises(ValueError):
        tm.validate_covenant(clauses=[], sections=["safeguarding"])  # missing required sections
    tm.validate_covenant(clauses=["mutual_support"], sections=list(tm.REQUIRED_COVENANT_SECTIONS))


def test_leader_cannot_investigate_self_and_critical_blocks_sending():
    with pytest.raises(ValueError):
        tm.assert_complaint_investigator(accused_id="leader", investigator_id="leader")
    tm.assert_complaint_investigator(accused_id="leader", investigator_id="independent")
    assert tm.critical_health_blocks_sending("critical")
    assert not tm.anonymity_threshold_met(3)


# ---- Skill 58/59/60: partnership & support ----
def test_partner_needs_mutual_assessment_and_funding_no_control():
    with pytest.raises(ValueError):
        pn.assert_can_approve_partner(has_mutual_assessment=False, status_target="approved")
    pn.assert_can_approve_partner(has_mutual_assessment=True, status_target="approved")
    with pytest.raises(ValueError):
        pn.partner_opposition_blocks(partner_opposed=True)
    with pytest.raises(ValueError):
        pn.funding_grants_no_control({"safeguarding": "veto"}, "funding_partner")
    pn.funding_grants_no_control({"safeguarding": "consult"}, "funding_partner")


def test_agreement_completeness_and_safeguarding_not_funder_vetoable_and_data_access():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        pn.assert_agreement_complete(["decision_rights"], has_exit_plan=True, has_local_decision_rights=True)
    with pytest.raises(ValueError):
        pn.assert_agreement_complete(list(pn.REQUIRED_AGREEMENT_SECTIONS), has_exit_plan=False, has_local_decision_rights=True)
    pn.assert_agreement_complete(list(pn.REQUIRED_AGREEMENT_SECTIONS), has_exit_plan=True, has_local_decision_rights=True)
    with pytest.raises(ValueError):
        pn.assert_safeguarding_not_funder_vetoable({"safeguarding": {"veto_parties": ["funding_partner"]}})
    assert pn.data_access_allowed(agreement_active=True, expires_at=now + timedelta(days=1), individual_consent=True, now=now)
    assert not pn.data_access_allowed(agreement_active=True, expires_at=now - timedelta(days=1), individual_consent=True, now=now)
    assert not pn.data_access_allowed(agreement_active=True, expires_at=None, individual_consent=False, now=now)


def test_prayer_update_no_sensitive_and_crisis_pauses_and_funder_no_governance():
    with pytest.raises(ValueError):
        pn.assert_update_clean(["title", "sensitive_location"])
    pn.assert_update_clean(["title", "thanksgiving"])
    assert not pn.scheduled_send_allowed(crisis_active=True)
    assert pn.scheduled_send_allowed(crisis_active=False)
    with pytest.raises(ValueError):
        pn.funder_gets_no_governance("financial_supporter", "governance")
    assert pn.unsubscribe_takes_effect_immediately(True) is False


# ---- migrations ----
@pytest.mark.parametrize("fname,rls_count", [
    ("0198_mission_os_sending.sql", 9),
    ("0199_mission_os_teams.sql", 6),
    ("0200_mission_os_partnership.sql", 6),
])
def test_migrations_rls_and_rollback(fname, rls_count):
    sql = (MIG / fname).read_text()
    assert sql.count("ENABLE ROW LEVEL SECURITY") == rls_count
    assert "current_setting(''app.tenant_id'',true)" in sql
    assert "-- Rollback:" in sql


def test_key_batch5_migration_checks():
    teams = (MIG / "0199_mission_os_teams.sql").read_text()
    assert "assigned_independent_reviewer_id<>accused_user_id" in teams
    send = (MIG / "0198_mission_os_sending.sql").read_text()
    assert "unlock_batch6_preparation" in send
    part = (MIG / "0200_mission_os_partnership.sql").read_text()
    assert "sensitivity_level IN('P0','P1','P2')" in part  # prayer updates cannot be P3/P4


# ---- API contract ----
def test_batch5_api_contract_exists():
    routes = {(r.path, m) for r in list(sending_router.routes) + list(teams_router.routes) + list(partners_router.routes) + list(support_router.routes)
              if isinstance(r, APIRoute) for m in r.methods}
    expected = {
        ("/api/v1/mission/sending/church-confirmations", "POST"),
        ("/api/v1/mission/sending/applications/submit", "POST"),
        ("/api/v1/mission/sending/committee-decisions", "POST"),
        ("/api/v1/mission/teams/memberships/approve", "POST"),
        ("/api/v1/mission/teams/covenants", "POST"),
        ("/api/v1/mission/local-partners/approve", "POST"),
        ("/api/v1/mission/prayer-updates", "POST"),
    }
    assert expected <= routes
