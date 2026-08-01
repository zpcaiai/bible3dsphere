from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scripts.generate_ai_formation_local_evidence import build_report, run_gate_command
from scripts.verify_ai_formation_migrations import _database_url


pytestmark = pytest.mark.no_db


def test_default_evidence_is_fail_closed_and_unsigned():
    report, failed = build_report(run_local_gates=False, database_url=None)
    assert failed is False
    assert report["certificationStatus"] == "NOT_CERTIFIED"
    assert report["automatedApproval"] is False
    assert report["localGateExecutionRequested"] is False
    assert {item["result"] for item in report["evidence"]} == {"not_run"}
    assert all(item["humanReviewer"] is None for item in report["evidence"])
    assert all(item["evidenceSha256"] is None for item in report["evidence"])


def test_gate_result_comes_from_the_real_process_exit_code(tmp_path: Path):
    passed = run_gate_command(
        gate="skill_evals",
        args=[sys.executable, "-c", "print('gate-ok')"],
        cwd=tmp_path,
        artifact_hash="a" * 64,
    )
    failed = run_gate_command(
        gate="skill_evals",
        args=[sys.executable, "-c", "raise SystemExit(7)"],
        cwd=tmp_path,
        artifact_hash="a" * 64,
    )
    assert (passed["result"], passed["exitCode"]) == ("passed", 0)
    assert (failed["result"], failed["exitCode"]) == ("failed", 7)
    assert passed["evidenceSha256"] != failed["evidenceSha256"]


def test_migration_rehearsal_refuses_non_local_database_hosts(monkeypatch):
    monkeypatch.delenv("AI_FORMATION_MIGRATION_DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="isolated local PostgreSQL"):
        _database_url(None)
    with pytest.raises(ValueError, match="refuses non-local"):
        _database_url("postgresql://user:pass@example.com/database")
    assert _database_url("postgresql://postgres:postgres@127.0.0.1:5431/postgres").startswith(
        "postgresql://"
    )
