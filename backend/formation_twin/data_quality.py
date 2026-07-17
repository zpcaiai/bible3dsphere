"""Fail-closed data-quality checks for canonical Formation Twin events."""
from __future__ import annotations

from typing import Any


def owner_quality_report(cur, *, email: str) -> dict[str, Any]:
    """Return aggregate quality signals without returning any sensitive body."""
    cur.execute(
        """
        SELECT
            COUNT(*) AS total_events,
            COUNT(*) FILTER (WHERE occurred_at IS NULL OR recorded_at IS NULL OR original_timezone='') AS invalid_time_events,
            COUNT(*) FILTER (WHERE consent_json='{}'::jsonb OR provenance_json='{}'::jsonb) AS missing_governance_events,
            COUNT(*) FILTER (
                WHERE self_report_json::text ~* '\"(content|raw_content|journal_text|prayer_text|transcript|crisis_text)\"[[:space:]]*:'
                   OR behavioral_facts_json::text ~* '\"(content|raw_content|journal_text|prayer_text|transcript|crisis_text)\"[[:space:]]*:'
            ) AS sensitive_leak_candidates,
            COUNT(*) FILTER (WHERE status IN ('REJECTED','QUARANTINED')) AS rejected_or_quarantined,
            COUNT(*) FILTER (WHERE exclude_from_twin_processing) AS excluded_events
        FROM formation_twin_life_events
        WHERE email=%s AND deleted_at IS NULL
        """,
        (email,),
    )
    row = cur.fetchone()
    cur.execute(
        """
        SELECT COUNT(*) FROM formation_twin_sensitive_contents sensitive
        WHERE sensitive.email=%s AND sensitive.deleted_at IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM formation_twin_life_events event
              WHERE event.content_reference_id=sensitive.id AND event.email=sensitive.email AND event.deleted_at IS NULL
          )
          AND NOT EXISTS (
              SELECT 1 FROM formation_twin_voice_journals voice
              WHERE voice.transcript_sensitive_content_id=sensitive.id AND voice.email=sensitive.email AND voice.deleted_at IS NULL
          )
        """,
        (email,),
    )
    orphaned_sensitive_records = cur.fetchone()[0]
    total = row[0]
    issues = row[1] + row[2] + row[3] + orphaned_sensitive_records
    return {
        "total_events": total,
        "invalid_time_events": row[1],
        "missing_governance_events": row[2],
        "sensitive_leak_candidates": row[3],
        "rejected_or_quarantined": row[4],
        "excluded_events": row[5],
        "orphaned_sensitive_records": orphaned_sensitive_records,
        "quality_passed": issues == 0,
        "valid_event_ratio": 1.0 if total == 0 else round((total - min(total, issues)) / total, 4),
    }
