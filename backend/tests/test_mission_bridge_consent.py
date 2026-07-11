from pathlib import Path

from routers.mission_bridge import CONSENT_TYPES, CONSENT_DEFAULTS


def test_all_consent_types_are_independent_and_described():
    assert len(CONSENT_TYPES) == 10
    assert CONSENT_TYPES == set(CONSENT_DEFAULTS)
    assert "service_participation" in CONSENT_TYPES
    assert "faith_exploration" in CONSENT_TYPES
    assert "ai_assistance" in CONSENT_TYPES
    assert "audio_recording" in CONSENT_TYPES


def test_lifecycle_schema_keeps_safety_records_and_tracks_retention():
    sql=(Path(__file__).parents[1]/"migrations"/"0153_mission_bridge_consent_lifecycle.sql").read_text(encoding="utf-8")
    assert "retention_days" in sql
    assert "safety_records_retained" in sql
    assert "mission_bridge_retention_runs" in sql
