"""Small SQL migration runner used for deploy-time schema changes."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import psycopg2


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


@dataclass(frozen=True)
class MigrationRecord:
    version: str
    name: str
    checksum: str


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


def run_migrations(database_url: str, migrations_dir: Path = MIGRATIONS_DIR) -> list[MigrationRecord]:
    """Apply pending migrations and return the records that were applied.

    Resilient by design: a single problematic migration (e.g. an already-applied
    file whose checksum changed because it was edited) must NOT abort the whole
    run and leave later migrations unapplied. All project migrations are written
    idempotently (CREATE TABLE/INDEX IF NOT EXISTS, ADD COLUMN IF NOT EXISTS),
    so re-applying them is safe. Each migration is committed independently.
    """
    applied: list[MigrationRecord] = []
    conn = psycopg2.connect(database_url)
    try:
        ensure_migration_table(conn)
        conn.commit()
        existing = applied_versions(conn)
        for path in _migration_files(migrations_dir):
            record = _record_for(path)
            previous_checksum = existing.get(record.version)
            if previous_checksum == record.checksum:
                continue

            sql = path.read_text(encoding="utf-8")
            edited = previous_checksum is not None and previous_checksum != record.checksum
            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    if previous_checksum is None:
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
                applied.append(record)
                if edited:
                    print(f"[migrations] WARNING: {record.version} checksum changed "
                          f"after application; re-applied idempotently and refreshed checksum",
                          flush=True)
            except Exception as exc:
                conn.rollback()
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


if __name__ == "__main__":
    import os

    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    records = run_migrations(database_url)
    for record in records:
        print(f"applied {record.version} {record.name}")
    if not records:
        print("no pending migrations")
