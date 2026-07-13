"""Batch 2 invariants: MissionField, knowledge graph, claims, field assessment."""
from datetime import datetime, timezone
from pathlib import Path
import pytest
from fastapi.routing import APIRoute
from mission_os.field import (
    MissionFieldProfile, public_field_dto, assert_public_dto_clean, assess_field,
)
from mission_os import knowledge_graph as kg
from mission_os import claims as cl
from routers.mission_fields import router as fields_router
from routers.mission_claims import router as claims_router, sources_router

pytestmark = pytest.mark.no_db

MIG = Path(__file__).parents[1] / "migrations"


# ---- Skill 16: MissionField ----
def test_field_supports_geographic_and_non_geographic():
    MissionFieldProfile("f1", "t1", "people_group", "Some Group").validate()          # non-geo, no country ok
    MissionFieldProfile("f2", "t1", "city", "Some City", "CN").validate()             # geo needs country
    with pytest.raises(ValueError):
        MissionFieldProfile("f3", "t1", "city", "No Country").validate()
    with pytest.raises(ValueError):
        MissionFieldProfile("f4", "t1", "not_a_type", "X").validate()


def test_public_dto_strips_sensitive_geography_and_partners():
    rec = {"canonicalName": "X", "sensitive_geometry_reference": "secret",
           "local_partner_contacts": ["a"], "publicVisibility": True}
    pub = public_field_dto(rec)
    assert "sensitive_geometry_reference" not in pub and "local_partner_contacts" not in pub
    assert_public_dto_clean(pub.keys())
    with pytest.raises(ValueError):
        assert_public_dto_clean(["sensitive_geometry_reference"])


# ---- Skill 24: assessment keeps Need/Evidence/Readiness/Risk separate ----
def test_assessment_reports_four_independent_scores():
    r = assess_field(need_score=0.9, evidence_score=0.8, readiness_score=0.8, risk_level="low")
    assert (r.need_score, r.evidence_score, r.readiness_score, r.risk_level) == (0.9, 0.8, 0.8, "low")
    assert r.recommendation == "candidate_for_team_discernment"


def test_high_need_cannot_override_hard_block():
    r = assess_field(need_score=1.0, evidence_score=1.0, readiness_score=1.0, risk_level="low",
                     hard_blocks=["no_legal_entry_path"])
    assert r.is_blocked() and r.recommendation in {"not_ready", "build_local_partnership", "pause_due_to_risk", "improve_data_quality"}
    assert r.recommendation != "candidate_for_team_discernment"


def test_high_need_high_risk_never_enters():
    r = assess_field(need_score=1.0, evidence_score=0.9, readiness_score=0.9, risk_level="critical",
                     hard_blocks=["unmitigated_high_risk"])
    assert r.recommendation == "pause_due_to_risk"


def test_low_evidence_routes_to_improve_data_quality():
    r = assess_field(need_score=0.9, evidence_score=0.2, readiness_score=0.9, risk_level="low")
    assert r.recommendation == "improve_data_quality"


# ---- Skill 17: knowledge graph anti-stereotyping ----
def test_people_group_cannot_be_bound_to_single_religion():
    with pytest.raises(ValueError):
        kg.validate_people_group_links(language_links=["primary_language"], religion_links=["majority_affiliation"])
    kg.validate_people_group_links(language_links=["primary_language", "trade_language"],
                                   religion_links=["majority_affiliation", "minority_affiliation"])


def test_religion_share_must_be_range_not_point():
    kg.validate_religion_link("majority_affiliation", share_range=(0.3, 0.6))
    kg.validate_religion_link("unknown_or_diverse", share_range=None)
    with pytest.raises(ValueError):
        kg.validate_religion_link("majority_affiliation", share_range=(0.42,))  # point-ish / wrong shape
    with pytest.raises(ValueError):
        kg.validate_religion_link("unknown_or_diverse", share_range=(0.1, 0.2))


def test_no_individual_inference_from_group_label():
    with pytest.raises(ValueError):
        kg.assert_no_individual_inference("individual_from_group_label")


# ---- Skill 22/23: claims ----
def test_ai_can_only_create_candidate_and_cannot_be_supported_without_human_evidence():
    assert cl.validate_new_claim(claim_type="ai_candidate", created_by_type="ai",
                                 normalized_value=None, as_of_date=None) == "candidate"
    with pytest.raises(ValueError):
        cl.validate_new_claim(claim_type="observed_fact", created_by_type="ai",
                              normalized_value=None, as_of_date=None)
    with pytest.raises(ValueError):
        cl.can_promote(current_status="under_review", target_status="supported",
                       evidence_count=1, supporting_evidence_count=1,
                       has_local_reviewer=False, created_by_type="ai")


def test_statistic_claim_requires_as_of_date():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        cl.validate_new_claim(claim_type="reported_statistic", created_by_type="human",
                              normalized_value={"unit": "people"}, as_of_date=None)
    cl.validate_new_claim(claim_type="reported_statistic", created_by_type="human",
                          normalized_value={"unit": "people"}, as_of_date=now)


def test_supported_needs_supporting_evidence_and_local_confirm_needs_reviewer():
    with pytest.raises(ValueError):
        cl.can_promote(current_status="under_review", target_status="supported",
                       evidence_count=1, supporting_evidence_count=0,
                       has_local_reviewer=True, created_by_type="human")
    with pytest.raises(ValueError):
        cl.can_promote(current_status="supported", target_status="locally_confirmed",
                       evidence_count=2, supporting_evidence_count=2,
                       has_local_reviewer=False, created_by_type="human")
    cl.can_promote(current_status="supported", target_status="locally_confirmed",
                   evidence_count=2, supporting_evidence_count=2,
                   has_local_reviewer=True, created_by_type="human")


def test_snapshot_is_immutable():
    with pytest.raises(ValueError):
        cl.snapshot_is_immutable("hash-a", "hash-b")
    cl.snapshot_is_immutable("hash-a", "hash-a")  # same content ok


# ---- migrations: tenant_id + RLS + rollback ----
@pytest.mark.parametrize("fname,rls_count", [
    ("0188_mission_os_field_intelligence.sql", 4),
    ("0189_mission_os_knowledge_graph.sql", 6),
    ("0190_mission_os_sources_claims.sql", 5),
    ("0191_mission_os_field_assessments.sql", 3),
])
def test_migrations_enable_rls_and_rollback(fname, rls_count):
    sql = (MIG / fname).read_text()
    assert sql.count("ENABLE ROW LEVEL SECURITY") == rls_count
    assert "current_setting(''app.tenant_id'',true)" in sql
    assert "-- Rollback:" in sql


def test_statistic_and_ai_candidate_checks_in_migration():
    sql = (MIG / "0190_mission_os_sources_claims.sql").read_text()
    assert "claim_type<>'reported_statistic' OR as_of_date IS NOT NULL" in sql
    assert "claim_type<>'ai_candidate' OR created_by_type IN('ai','system')" in sql


def test_religion_share_range_check_in_migration():
    sql = (MIG / "0189_mission_os_knowledge_graph.sql").read_text()
    assert "estimated_share_high>=estimated_share_low" in sql


# ---- API contract ----
def test_batch2_api_contract_exists():
    routes = {(r.path, m) for r in list(fields_router.routes) + list(claims_router.routes) + list(sources_router.routes)
              if isinstance(r, APIRoute) for m in r.methods}
    expected = {
        ("/api/v1/mission/fields", "POST"),
        ("/api/v1/mission/fields/{field_id}", "GET"),
        ("/api/v1/mission/fields/{field_id}/assess", "POST"),
        ("/api/v1/mission/sources", "POST"),
        ("/api/v1/mission/claims", "POST"),
        ("/api/v1/mission/claims/{claim_id}/evidence", "POST"),
        ("/api/v1/mission/claims/{claim_id}/promote", "POST"),
    }
    assert expected <= routes
