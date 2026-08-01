"""Rehearse the AI-formation forward/rollback chain on a local test database.

All DDL and seed changes run inside one PostgreSQL transaction which is always
rolled back. The command refuses non-local database hosts so it cannot be used
as a production rollback mechanism.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlparse

import psycopg2


BACKEND = Path(__file__).resolve().parents[1]
MIGRATIONS = BACKEND / "migrations"
FORWARD = (
    MIGRATIONS / "0238_sunday_school_ai_formation_batches_01_12.sql",
    MIGRATIONS / "0239_ai_formation_production_workflows.sql",
    MIGRATIONS / "0240_ai_formation_reviewed_asset_catalog.sql",
)
ROLLBACK = (
    MIGRATIONS / "rollback" / "0240_ai_formation_reviewed_asset_catalog.down.sql",
    MIGRATIONS / "rollback" / "0239_ai_formation_production_workflows.down.sql",
    MIGRATIONS / "rollback" / "0238_sunday_school_ai_formation_batches_01_12.down.sql",
)
EXPECTED_TABLES = (
    "sunday_school_ai_formation_records",
    "sunday_school_ai_formation_content",
    "sunday_school_ai_formation_content_reviews",
    "sunday_school_ai_formation_audit",
    "sunday_school_ai_formation_release_evidence",
    "sunday_school_ai_formation_release_decisions",
)
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _database_url(value: str | None) -> str:
    url = value or os.environ.get("AI_FORMATION_MIGRATION_DATABASE_URL", "")
    if not url:
        raise ValueError(
            "set AI_FORMATION_MIGRATION_DATABASE_URL to an isolated local PostgreSQL database"
        )
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in LOCAL_HOSTS:
        raise ValueError("migration rehearsal refuses non-local PostgreSQL hosts")
    return url


def _execute_files(cursor, paths: tuple[Path, ...]) -> None:
    for path in paths:
        cursor.execute(path.read_text(encoding="utf-8"))


def _table_exists(cursor, name: str) -> bool:
    cursor.execute("SELECT to_regclass(%s)", (f"public.{name}",))
    return cursor.fetchone()[0] is not None


def _assert_forward_state(cursor) -> None:
    missing = [name for name in EXPECTED_TABLES if not _table_exists(cursor, name)]
    if missing:
        raise RuntimeError(f"forward migration missing tables: {', '.join(missing)}")
    cursor.execute(
        "SELECT COUNT(*), COUNT(*) FILTER "
        "(WHERE review_status IN ('draft','theology_review','pastoral_review')), "
        "COUNT(*) FILTER (WHERE published_at IS NOT NULL) "
        "FROM sunday_school_ai_formation_content WHERE created_by='skills-bag-01-12'"
    )
    total, review_gated, published = cursor.fetchone()
    if (total, review_gated, published) != (67, 67, 0):
        raise RuntimeError(
            "review-only seed invariant failed: "
            f"total={total}, review_gated={review_gated}, published={published}"
        )


def _assert_rollback_state(cursor) -> None:
    remaining = [name for name in EXPECTED_TABLES if _table_exists(cursor, name)]
    if remaining:
        raise RuntimeError(f"rollback left module tables: {', '.join(remaining)}")


def rehearse(database_url: str) -> dict[str, object]:
    connection = psycopg2.connect(database_url)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout = '10s'")
            cursor.execute("SET LOCAL statement_timeout = '120s'")

            # If the integration suite initialized the same disposable database,
            # first remove that state inside this transaction. The final rollback
            # restores the exact pre-rehearsal database state.
            if _table_exists(cursor, EXPECTED_TABLES[0]):
                _execute_files(cursor, ROLLBACK)
                _assert_rollback_state(cursor)

            _execute_files(cursor, FORWARD)
            _assert_forward_state(cursor)
            _execute_files(cursor, ROLLBACK)
            _assert_rollback_state(cursor)
            _execute_files(cursor, FORWARD)
            _assert_forward_state(cursor)
        connection.rollback()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return {
        "status": "passed",
        "forwardMigrations": [path.name for path in FORWARD],
        "rollbackMigrations": [path.name for path in ROLLBACK],
        "seedAssets": 67,
        "transactionPersisted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        help="isolated local PostgreSQL URL; prefer AI_FORMATION_MIGRATION_DATABASE_URL",
    )
    parser.add_argument(
        "--allow-local-test-database",
        action="store_true",
        help="required acknowledgement that the target is a disposable local test database",
    )
    args = parser.parse_args()
    if not args.allow_local_test_database:
        parser.error("--allow-local-test-database is required")
    try:
        result = rehearse(_database_url(args.database_url))
    except (ValueError, RuntimeError, psycopg2.Error) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
