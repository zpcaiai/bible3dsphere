"""Verify every historical migration on a disposable PostGIS + pgvector DB.

The command refuses databases whose name does not visibly identify a disposable
gate/test environment. It bootstraps the repository's legacy first-run tables,
then applies all numbered migrations in strict checksum mode.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
from psycopg2 import pool

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from core.migrations import MIGRATIONS_DIR, run_migrations  # noqa: E402
from db_schema import init_db_postgresql  # noqa: E402
from decision_support import SFDS_TABLES_SQL  # noqa: E402
from mvfe.db.postgres import init_mvfe_tables  # noqa: E402
from mvfe.db.graph_schema import MVFE_GRAPH_SCHEMA_SQL  # noqa: E402


AI_MIGRATION_VERSIONS = ("0238", "0239", "0240", "0241")


def _database_name(url: str) -> str:
    return urlparse(url).path.lstrip("/").split("?", 1)[0]


def _require_disposable(url: str, confirmed: bool) -> None:
    name = _database_name(url).casefold()
    if not confirmed or not any(marker in name for marker in ("gate", "test", "smoke", "staging")):
        raise SystemExit(
            "refusing migration rehearsal: use --confirm-disposable and a database "
            "name containing gate, test, smoke, or staging"
        )


def _extensions(url: str) -> dict[str, str]:
    conn = psycopg2.connect(url)
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
            cur.execute(
                "SELECT extname,extversion FROM pg_extension "
                "WHERE extname IN ('vector','postgis') ORDER BY extname"
            )
            result = dict(cur.fetchall())
        conn.commit()
        if set(result) != {"postgis", "vector"}:
            raise RuntimeError(f"required extensions missing: {result}")
        return result
    finally:
        conn.close()


def _bootstrap_legacy_tables(url: str) -> None:
    os.environ["SEED_DEMO_USER"] = "false"

    def get_db():
        return psycopg2.connect(url)

    def release_db(conn):
        conn.close()

    init_db_postgresql(get_db, release_db, lambda value: f"unused:{value}", lambda *_args: False)
    conn = psycopg2.connect(url)
    try:
        with conn.cursor() as cur:
            cur.execute(SFDS_TABLES_SQL)
            cur.execute(MVFE_GRAPH_SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()
    mvfe_pool = pool.ThreadedConnectionPool(1, 2, url)
    try:
        if not init_mvfe_tables(mvfe_pool):
            raise RuntimeError("MVFE prerequisite table bootstrap failed")
    finally:
        mvfe_pool.closeall()


def _query_metrics(url: str) -> dict[str, int]:
    conn = psycopg2.connect(url)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM schema_migrations")
            applied = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM sunday_school_ai_formation_content")
            content = cur.fetchone()[0]
            cur.execute(
                "SELECT count(*) FROM sunday_school_ai_formation_content "
                "WHERE published_at IS NOT NULL"
            )
            published = cur.fetchone()[0]
        return {"appliedMigrationCount": applied, "contentVersionCount": content, "publishedContentCount": published}
    finally:
        conn.close()


def _rollback_ai_migrations(url: str) -> dict[str, bool]:
    conn = psycopg2.connect(url)
    try:
        with conn.cursor() as cur:
            for version in reversed(AI_MIGRATION_VERSIONS):
                matches = sorted((MIGRATIONS_DIR / "rollback").glob(f"{version}_*.down.sql"))
                if len(matches) != 1:
                    raise RuntimeError(f"expected one rollback for {version}, found {len(matches)}")
                cur.execute(matches[0].read_text(encoding="utf-8"))
                cur.execute("DELETE FROM schema_migrations WHERE version=%s", (version,))
            cur.execute(
                "SELECT to_regclass('public.sunday_school_ai_formation_records'),"
                "to_regclass('public.sunday_school_ai_formation_content')"
            )
            records_table, content_table = cur.fetchone()
        conn.commit()
        return {"recordsTableRemoved": records_table is None, "contentTableRemoved": content_table is None}
    finally:
        conn.close()


def verify(url: str) -> dict:
    started = datetime.now(UTC)
    extensions = _extensions(url)
    _bootstrap_legacy_tables(url)
    expected = len(list(MIGRATIONS_DIR.glob("*.sql")))
    first = run_migrations(url, strict=True)
    metrics = _query_metrics(url)
    if metrics != {
        "appliedMigrationCount": expected,
        "contentVersionCount": 67,
        "publishedContentCount": 0,
    }:
        raise RuntimeError(f"unexpected forward metrics: {metrics}; expected migrations={expected}")
    second = run_migrations(url, strict=True)
    if second:
        raise RuntimeError(f"idempotency failed; reapplied: {[record.version for record in second]}")
    rollback = _rollback_ai_migrations(url)
    if not all(rollback.values()):
        raise RuntimeError(f"AI Formation rollback incomplete: {rollback}")
    reapplied = run_migrations(url, strict=True)
    if [record.version for record in reapplied] != list(AI_MIGRATION_VERSIONS):
        raise RuntimeError(f"unexpected AI Formation reapply set: {[record.version for record in reapplied]}")
    migration_manifest_hash = hashlib.sha256("".join(
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(MIGRATIONS_DIR.glob("*.sql"))
    ).encode("ascii")).hexdigest()
    return {
        "evidenceVersion": "1.0.0",
        "environment": "disposable_postgis_gate",
        "databaseName": _database_name(url),
        "extensions": extensions,
        "migrationManifestSha256": migration_manifest_hash,
        "historicalMigrationFileCount": expected,
        "strictForwardAppliedCount": len(first),
        "strictIdempotentReapplyCount": len(second),
        "aiFormationRollback": rollback,
        "aiFormationReappliedVersions": [record.version for record in reapplied],
        "metrics": _query_metrics(url),
        "startedAt": started.isoformat(),
        "completedAt": datetime.now(UTC).isoformat(),
        "result": "passed",
        "limitations": [
            "All historical migrations were applied forward; only migrations 0238-0241 have repository rollback SQL and were rolled back/reapplied.",
            "The database was disposable and contained no production data.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""))
    parser.add_argument("--confirm-disposable", action="store_true")
    parser.add_argument(
        "--output", type=Path,
        default=BACKEND.parent / "docs" / "ai-formation-certification" / "postgis-migration-evidence.json",
    )
    args = parser.parse_args()
    if not args.database_url:
        parser.error("--database-url or DATABASE_URL is required")
    _require_disposable(args.database_url, args.confirm_disposable)
    evidence = verify(args.database_url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
