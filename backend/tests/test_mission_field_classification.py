"""Skill 11 invariants: field-level sensitivity classification and authorization."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from fastapi.routing import APIRoute
from mission_os.classification import (
    LEVELS, at_most, classify_field, scope_ceiling, redact_record,
    assert_dto_safe, ai_input_allowed, FieldAccessGrant, REDACTED,
)
from routers.mission_field_classification import router, grants_router

pytestmark = pytest.mark.no_db


def test_levels_are_ordered_p0_to_p4():
    assert LEVELS == ("P0", "P1", "P2", "P3", "P4")
    assert at_most("P1", "P3") and not at_most("P4", "P2")


def test_unknown_field_defaults_to_research_not_public():
    assert classify_field("mission_field", "some_new_field") == "P2"
    assert classify_field("local_partner", "encrypted_contact_reference") == "P4"
    assert classify_field("worker_profile", "family_stage_summary") == "P3"


def test_redact_record_withholds_fields_above_ceiling():
    record = {"public_geometry": "poly", "sensitive_geometry_reference": "secret-ref"}
    out, redacted = redact_record(record, "mission_field", ceiling="P1")
    assert out["public_geometry"] == "poly"
    assert out["sensitive_geometry_reference"] == REDACTED
    assert redacted == ["sensitive_geometry_reference"]


def test_public_dto_cannot_expose_p3_or_p4():
    assert_dto_safe("public", "mission_field", ["public_geometry"])  # ok
    with pytest.raises(ValueError):
        assert_dto_safe("public", "mission_field", ["sensitive_geometry_reference"])
    with pytest.raises(ValueError):
        assert_dto_safe("research", "worker_profile", ["family_stage_summary"])  # P3 > research P2


def test_ai_model_never_receives_p3_or_p4():
    ai_input_allowed("mission_field", ["public_geometry"])  # ok (P1)
    with pytest.raises(ValueError):
        ai_input_allowed("calling_journey", ["spouse_feedback"])  # P4


def test_field_grant_is_time_boxed_and_fails_closed():
    now = datetime.now(timezone.utc)
    active = FieldAccessGrant("user", "u1", "mission_field", "sensitive_geometry_reference", "P4",
                              expires_at=now + timedelta(hours=1))
    assert active.is_active(now) and active.effective_level(now) == "P4"
    expired = FieldAccessGrant("user", "u1", "mission_field", "x", "P4", expires_at=now - timedelta(seconds=1))
    assert not expired.is_active(now) and expired.effective_level(now) is None
    revoked = FieldAccessGrant("user", "u1", "mission_field", "x", "P4", revoked_at=now)
    assert not revoked.is_active(now)


def test_scope_ceiling_respects_grants():
    assert scope_ceiling("public") == "P1"
    assert scope_ceiling("researcher") == "P2"
    assert scope_ceiling("researcher", grant_level="P4") == "P4"
    assert scope_ceiling("ai_model") == "P2"


def test_migration_enables_rls_on_both_tables():
    sql = (Path(__file__).parents[1] / "migrations" / "0186_mission_os_field_classification.sql").read_text()
    assert sql.count("ENABLE ROW LEVEL SECURITY") == 2
    assert "tenant_id=current_setting(''app.tenant_id'',true)" in sql
    assert "sensitivity_level IN('P0','P1','P2','P3','P4')" in sql
    assert "-- Rollback:" in sql


def test_service_subject_cannot_be_granted_p3_p4_in_router_source():
    src = (Path(__file__).parents[1] / "routers" / "mission_field_classification.py").read_text()
    assert "服务账号不得被授予 P3/P4" in src


def test_skill_11_api_contract_exists():
    routes = {(r.path, m) for r in list(router.routes) + list(grants_router.routes)
              if isinstance(r, APIRoute) for m in r.methods}
    expected = {
        ("/api/v1/mission/field-classifications", "GET"),
        ("/api/v1/mission/field-classifications", "PUT"),
        ("/api/v1/mission/field-access-grants", "POST"),
    }
    assert expected <= routes
