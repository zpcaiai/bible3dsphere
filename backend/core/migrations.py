"""SQL migration runner used by application startup and the deploy gate.

Application startup keeps the historical best-effort behaviour.  CI/CD calls
``run_migrations(..., strict=True)`` so checksum drift or a failed migration
stops deployment before new application code reaches production.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import psycopg2


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
# Shared transaction-scoped advisory lock for every project migration runner.
# Transaction scope is safe with Neon's pooled and direct connection strings.
MIGRATION_LOCK_KEY = int.from_bytes(b"bible3d", byteorder="big", signed=False)


@dataclass(frozen=True)
class MigrationRecord:
    version: str
    name: str
    checksum: str


class MigrationError(RuntimeError):
    """Base class for deploy-blocking migration validation errors."""


class MigrationChecksumError(MigrationError):
    """Raised when an applied migration file was edited in place."""


class DuplicateMigrationVersionError(MigrationError):
    """Raised when two SQL files claim the same migration version."""


def _migration_files(migrations_dir: Path = MIGRATIONS_DIR) -> list[Path]:
    if not migrations_dir.exists():
        return []
    return sorted(path for path in migrations_dir.glob("*.sql") if path.is_file())


def _record_for(path: Path) -> MigrationRecord:
    sql = path.read_text(encoding="utf-8")
    checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
    stem = path.stem
    version, _, name = stem.partition("_")
    return MigrationRecord(version=version, name=name or stem, checksum=checksum)


def _records_for(paths: Sequence[Path]) -> list[MigrationRecord]:
    records = [_record_for(path) for path in paths]
    seen: set[str] = set()
    duplicates: set[str] = set()
    for record in records:
        if record.version in seen:
            duplicates.add(record.version)
        seen.add(record.version)
    if duplicates:
        versions = ", ".join(sorted(duplicates))
        raise DuplicateMigrationVersionError(
            f"duplicate migration version(s): {versions}"
        )
    return records


def _checksum_drift(
    records: Sequence[MigrationRecord], existing: Mapping[str, str]
) -> list[str]:
    return sorted(
        record.version
        for record in records
        if record.version in existing
        and existing[record.version] != record.checksum
    )


def ensure_migration_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version text PRIMARY KEY,
                name text NOT NULL,
                checksum text NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )


def applied_versions(conn) -> dict[str, str]:
    ensure_migration_table(conn)
    with conn.cursor() as cur:
        cur.execute("SELECT version, checksum FROM schema_migrations")
        return {row[0]: row[1] for row in cur.fetchall()}


def run_migrations(
    database_url: str,
    migrations_dir: Path = MIGRATIONS_DIR,
    *,
    strict: bool = False,
) -> list[MigrationRecord]:
    """Apply pending migrations and return the records that were applied.

    Resilient by design: a single problematic migration (e.g. an already-applied
    file whose checksum changed because it was edited) must NOT abort the whole
    run and leave later migrations unapplied. All project migrations are written
    idempotently (CREATE TABLE/INDEX IF NOT EXISTS, ADD COLUMN IF NOT EXISTS),
    so re-applying them is safe. Each migration is committed independently.
    """
    migration_files = _migration_files(migrations_dir)
    records = _records_for(migration_files)
    paths_by_version = {
        record.version: path for record, path in zip(records, migration_files)
    }
    applied: list[MigrationRecord] = []
    conn = psycopg2.connect(database_url)
    try:
        ensure_migration_table(conn)
        conn.commit()
        existing = applied_versions(conn)
        if strict:
            drift = _checksum_drift(records, existing)
            if drift:
                versions = ", ".join(drift)
                raise MigrationChecksumError(
                    "applied migration checksum changed; create a new migration "
                    f"instead of editing version(s): {versions}"
                )

        for record in records:
            path = paths_by_version[record.version]
            previous_checksum = existing.get(record.version)
            if previous_checksum == record.checksum:
                continue

            sql = path.read_text(encoding="utf-8")
            edited = previous_checksum is not None and previous_checksum != record.checksum
            try:
                with conn.cursor() as cur:
                    # Re-check after acquiring the lock. Another workflow may
                    # have completed this version while this runner was waiting.
                    cur.execute("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK_KEY,))
                    cur.execute(
                        "SELECT checksum FROM schema_migrations WHERE version=%s",
                        (record.version,),
                    )
                    current = cur.fetchone()
                    current_checksum = current[0] if current else None
                    if current_checksum == record.checksum:
                        conn.commit()
                        existing[record.version] = record.checksum
                        continue
                    if strict and current_checksum is not None:
                        raise MigrationChecksumError(
                            "applied migration checksum changed while waiting for lock: "
                            f"{record.version}"
                        )

                    cur.execute(sql)
                    if current_checksum is None:
                        cur.execute(
                            "INSERT INTO schema_migrations (version, name, checksum) "
                            "VALUES (%s, %s, %s)",
                            (record.version, record.name, record.checksum),
                        )
                    else:
                        # Checksum changed after application — file was edited.
                        # Re-applied idempotently above; refresh the stored checksum.
                        cur.execute(
                            "UPDATE schema_migrations SET checksum=%s, name=%s WHERE version=%s",
                            (record.checksum, record.name, record.version),
                        )
                conn.commit()
                existing[record.version] = record.checksum
                applied.append(record)
                if edited:
                    print(f"[migrations] WARNING: {record.version} checksum changed "
                          f"after application; re-applied idempotently and refreshed checksum",
                          flush=True)
            except Exception as exc:
                conn.rollback()
                if strict:
                    raise
                print(f"[migrations] WARNING: {record.version} ({record.name}) "
                      f"could not be applied, skipping: {exc}", flush=True)
                # For an edited-but-already-applied migration whose re-apply failed,
                # still refresh the checksum so we don't retry forever every boot.
                if edited:
                    try:
                        with conn.cursor() as cur:
                            cur.execute(
                                "UPDATE schema_migrations SET checksum=%s WHERE version=%s",
                                (record.checksum, record.version),
                            )
                        conn.commit()
                    except Exception:
                        conn.rollback()
        return applied
    finally:
        conn.close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply versioned PostgreSQL migrations")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="fail on checksum drift or the first migration error",
    )
    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=MIGRATIONS_DIR,
        help="directory containing numbered SQL migration files",
    )
    args = parser.parse_args(argv)

    database_url = os.getenv("NEON_DATABASE_URL") or os.getenv("DATABASE_URL", "")
    if not database_url:
        parser.error("NEON_DATABASE_URL or DATABASE_URL is required")
    records = run_migrations(
        database_url,
        migrations_dir=args.migrations_dir,
        strict=args.strict,
    )
    for record in records:
        print(f"applied {record.version} {record.name}")
    if not records:
        print("no pending migrations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
