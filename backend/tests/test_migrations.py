from __future__ import annotations

from pathlib import Path

import pytest

from core import migrations


class FakeCursor:
    def __init__(self, conn: "FakeConnection") -> None:
        self.conn = conn
        self._one = None

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    def execute(self, sql: str, params=None) -> None:
        normalized = " ".join(sql.split())
        if normalized.startswith("CREATE TABLE IF NOT EXISTS schema_migrations"):
            return
        if normalized == "SELECT version, checksum FROM schema_migrations":
            return
        if normalized.startswith("SELECT pg_advisory_xact_lock"):
            self.conn.lock_count += 1
            return
        if normalized.startswith(
            "SELECT checksum FROM schema_migrations WHERE version="
        ):
            checksum = self.conn.existing.get(params[0])
            self._one = (checksum,) if checksum is not None else None
            return
        if normalized.startswith("INSERT INTO schema_migrations"):
            version, _name, checksum = params
            self.conn.existing[version] = checksum
            return
        if normalized.startswith("UPDATE schema_migrations SET checksum="):
            checksum = params[0]
            version = params[-1]
            self.conn.existing[version] = checksum
            return
        if self.conn.fail_sql and self.conn.fail_sql in sql:
            raise RuntimeError("migration SQL failed")
        self.conn.executed_sql.append(sql)

    def fetchall(self):
        return sorted(self.conn.existing.items())

    def fetchone(self):
        return self._one


class FakeConnection:
    def __init__(self, existing=None, fail_sql: str | None = None) -> None:
        self.existing = dict(existing or {})
        self.fail_sql = fail_sql
        self.executed_sql: list[str] = []
        self.commits = 0
        self.rollbacks = 0
        self.lock_count = 0
        self.closed = False

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


def write_migration(directory: Path, filename: str, sql: str) -> Path:
    path = directory / filename
    path.write_text(sql, encoding="utf-8")
    return path


def test_strict_runner_applies_pending_migration_under_lock(tmp_path, monkeypatch):
    write_migration(tmp_path, "0001_create_widget.sql", "CREATE TABLE widget(id int);")
    conn = FakeConnection()
    monkeypatch.setattr(migrations.psycopg2, "connect", lambda _url: conn)

    applied = migrations.run_migrations("postgresql://redacted", tmp_path, strict=True)

    assert [record.version for record in applied] == ["0001"]
    assert conn.lock_count == 1
    assert conn.executed_sql == ["CREATE TABLE widget(id int);"]
    assert "0001" in conn.existing
    assert conn.closed is True


def test_strict_runner_rejects_checksum_drift_before_sql(tmp_path, monkeypatch):
    write_migration(tmp_path, "0001_create_widget.sql", "CREATE TABLE widget(id int);")
    conn = FakeConnection(existing={"0001": "old-checksum"})
    monkeypatch.setattr(migrations.psycopg2, "connect", lambda _url: conn)

    with pytest.raises(migrations.MigrationChecksumError, match="0001"):
        migrations.run_migrations("postgresql://redacted", tmp_path, strict=True)

    assert conn.executed_sql == []
    assert conn.closed is True


def test_strict_runner_propagates_sql_failure(tmp_path, monkeypatch):
    write_migration(tmp_path, "0001_bad.sql", "BROKEN MIGRATION;")
    conn = FakeConnection(fail_sql="BROKEN MIGRATION")
    monkeypatch.setattr(migrations.psycopg2, "connect", lambda _url: conn)

    with pytest.raises(RuntimeError, match="migration SQL failed"):
        migrations.run_migrations("postgresql://redacted", tmp_path, strict=True)

    assert conn.rollbacks == 1
    assert conn.closed is True


def test_duplicate_versions_are_rejected_before_connecting(tmp_path, monkeypatch):
    write_migration(tmp_path, "0001_alpha.sql", "SELECT 1;")
    write_migration(tmp_path, "0001_beta.sql", "SELECT 2;")
    connected = False

    def connect(_url):
        nonlocal connected
        connected = True
        return FakeConnection()

    monkeypatch.setattr(migrations.psycopg2, "connect", connect)

    with pytest.raises(migrations.DuplicateMigrationVersionError, match="0001"):
        migrations.run_migrations("postgresql://redacted", tmp_path, strict=True)

    assert connected is False
