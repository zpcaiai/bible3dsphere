from pathlib import Path

import pytest


pytestmark = pytest.mark.no_db


def test_batch_02_migration_contains_required_storage_boundaries():
    migration = Path(__file__).parents[1] / "migrations" / "0212_formation_twin_life_events.sql"
    sql = migration.read_text(encoding="utf-8")

    for table in (
        "formation_twin_sensitive_contents",
        "formation_twin_life_events",
        "formation_twin_daily_checkins",
        "formation_twin_journals",
        "formation_twin_voice_journals",
        "formation_twin_event_revisions",
        "formation_twin_ingestion_receipts",
        "formation_twin_ingestion_failures",
        "formation_twin_source_connections",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql

    assert "encrypted_content BYTEA NOT NULL" in sql
    assert "nonce BYTEA NOT NULL" in sql
    assert "idempotency_key VARCHAR(64) NOT NULL UNIQUE" in sql
    assert "never stores full journal, prayer, transcript, confession, or crisis text" in sql
