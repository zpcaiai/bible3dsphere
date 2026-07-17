from pathlib import Path

import pytest

pytestmark = pytest.mark.no_db


def test_batch_03_migration_has_source_separation_rls_and_no_plaintext_columns():
    sql = (Path(__file__).parents[1] / "migrations" / "0213_formation_twin_emotional_state.sql").read_text()
    for table in (
        "formation_twin_emotion_observations", "formation_twin_emotion_evidence",
        "formation_twin_body_observations", "formation_twin_energy_stress_observations",
        "formation_twin_emotional_episodes", "formation_twin_episode_events",
        "formation_twin_emotional_snapshots", "formation_twin_inference_reviews",
        "formation_twin_emotion_rule_results", "formation_twin_emotion_model_runs",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "source_kind VARCHAR(30) NOT NULL" in sql
    assert "statement_type VARCHAR(40) NOT NULL" in sql
    assert "journal_text" not in sql
    assert "transcript TEXT" not in sql


def test_emotional_router_never_uses_postgres_any_placeholder():
    router = (Path(__file__).parents[1] / "routers" / "formation_twin_emotions.py").read_text()
    assert "ANY(%s)" not in router
