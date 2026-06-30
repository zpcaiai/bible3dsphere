import pytest
from pathlib import Path

from batch1_4_engine import MODULES, build_summary, orchestrate_intent, safety_route, validate_record_type

pytestmark = pytest.mark.no_db


def test_batch1_4_registry_covers_required_domains():
    assert MODULES["scripture"]["batch"] == 1
    assert "memory_items" in MODULES["scripture"]["record_types"]
    assert MODULES["virtue_vice"]["batch"] == 3
    assert "fruit_assessments" in MODULES["virtue_vice"]["record_types"]
    assert MODULES["holy_habit"]["batch"] == 4
    assert "fasting_plans" in MODULES["holy_habit"]["record_types"]


def test_validate_record_type_rejects_unknown_type():
    validate_record_type("scripture", "lectio_sessions")
    with pytest.raises(ValueError):
        validate_record_type("scripture", "rule_profiles")


def test_orchestrate_routes_intent_to_batch_domain():
    scripture = orchestrate_intent("I need examen and confession after reading Scripture")
    virtue = orchestrate_intent("I am facing temptation and anger again")
    habit = orchestrate_intent("Build a rule of life with sabbath rest")
    assert scripture["recommendedDomain"] == "scripture"
    assert virtue["recommendedDomain"] == "virtue_vice"
    assert habit["recommendedDomain"] == "holy_habit"


def test_safety_route_blocks_crisis_and_fasting_risk():
    crisis = safety_route("I might hurt myself", "scripture")
    fasting = safety_route("I want to starve and punish myself", "holy_habit")
    assert crisis["route"] == "crisis_care"
    assert crisis["blockNormalFormation"] is True
    assert fasting["route"] == "pastoral_medical_support"


def test_build_summary_counts_records():
    rows = [
        {"domain": "scripture", "record_type": "memory_items", "status": "learning", "updated_at": "2026-06-01"},
        {"domain": "virtue_vice", "record_type": "focuses", "status": "active", "updated_at": "2026-06-02"},
        {"domain": "holy_habit", "record_type": "rule_profiles", "status": "archived", "updated_at": "2026-06-03"},
    ]
    summary = build_summary(rows)
    assert summary["totalRecords"] == 3
    assert summary["activeRecords"] == 2
    assert summary["byDomain"]["holy_habit"] == 1


def test_batch1_4_records_are_user_scoped_in_migration():
    sql = Path(__file__).resolve().parents[1].joinpath("migrations", "0112_batch1_4_formation_records.sql").read_text()
    assert "PRIMARY KEY (email, id)" in sql
    assert "idx_formation_batch1_4_email_domain" in sql
