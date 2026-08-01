"""Create a command-backed, local-only Batch 01-12 evidence snapshot.

The default mode is fail-closed and records every gate as ``not_run``. Pass
``--run-local-gates`` to execute the local automated gates. Human gates
remain unsigned and the report always remains ``NOT_CERTIFIED``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


BACKEND = Path(__file__).resolve().parents[1]
API_ROOT = BACKEND.parent
WEB = BACKEND.parents[1] / "bible3dsphereWeb"
OUTPUT = WEB / "docs" / "AI_FORMATION_LOCAL_GATE_EVIDENCE.json"
ARTIFACT_ID = "sunday-school-ai-formation"
ARTIFACT_VERSION = "1.0.0-rc.20260801"
GATES = (
    "theology", "pastoral_safety", "child_safety", "privacy_security",
    "tenant_isolation", "accessibility_automated", "accessibility_manual",
    "content_quality", "skill_evals", "rollback_rehearsal",
)
HUMAN_GATE_REASON = "authorized staging/production review required"


def artifact_files() -> list[Path]:
    files = [
        BACKEND / "routers" / "ai_formation.py",
        BACKEND / "requirements.txt",
        BACKEND / "scripts" / "generate_ai_formation_local_evidence.py",
        BACKEND / "scripts" / "generate_ai_formation_content_review.py",
        BACKEND / "scripts" / "verify_full_postgis_migration_chain.py",
        BACKEND / "scripts" / "verify_ai_formation_migrations.py",
        WEB / "e2e" / "ai-formation.spec.js",
        WEB / "playwright.config.js",
        WEB / "src" / "features" / "ai-formation" / "AiFormationPage.jsx",
        WEB / "src" / "features" / "ai-formation" / "BatchWorkspace.jsx",
        WEB / "src" / "features" / "ai-formation" / "GovernanceWorkspace.jsx",
        WEB / "src" / "features" / "ai-formation" / "ScenarioRuntime.jsx",
        WEB / "src" / "features" / "ai-formation" / "api.js",
        WEB / "src" / "features" / "ai-formation" / "program.js",
        WEB / "src" / "features" / "ai-formation" / "aiFormation.css",
    ]
    files.extend(
        path for path in (BACKEND / "ai_formation").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )
    files.extend(BACKEND / "migrations" / name for name in (
        "0238_sunday_school_ai_formation_batches_01_12.sql",
        "0239_ai_formation_production_workflows.sql",
        "0240_ai_formation_reviewed_asset_catalog.sql",
    ))
    files.extend(BACKEND / "migrations" / "rollback" / name for name in (
        "0238_sunday_school_ai_formation_batches_01_12.down.sql",
        "0239_ai_formation_production_workflows.down.sql",
        "0240_ai_formation_reviewed_asset_catalog.down.sql",
    ))
    return sorted(set(files), key=lambda path: str(path))


def artifact_sha256(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        digest.update(_artifact_label(path).encode("utf-8"))
        digest.update(b"\0")
        if path.is_file():
            digest.update(b"present\0")
            digest.update(path.read_bytes())
        else:
            # Backend-only CI checkouts must still produce deterministic,
            # fail-closed evidence without pretending the sibling web
            # artifact was hashed.
            digest.update(b"missing\0")
        digest.update(b"\0")
    return digest.hexdigest()


def _artifact_label(path: Path) -> str:
    if path.is_relative_to(BACKEND):
        return f"backend/{path.relative_to(BACKEND)}"
    if path.is_relative_to(WEB):
        return f"web/{path.relative_to(WEB)}"
    return str(path)


def _output_digest(completed: subprocess.CompletedProcess[str]) -> str:
    payload = (completed.stdout + completed.stderr).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def run_gate_command(
    *,
    gate: str,
    args: list[str],
    cwd: Path,
    artifact_hash: str,
    environment: dict[str, str] | None = None,
    evidence_command: str | None = None,
) -> dict[str, Any]:
    executed_at = datetime.now(UTC).isoformat()
    command = evidence_command or shlex.join(args)
    print(f"[{gate}] {command}")
    completed = subprocess.run(
        args,
        cwd=cwd,
        env={**os.environ, **(environment or {})},
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    return {
        "artifactId": ARTIFACT_ID,
        "artifactVersion": ARTIFACT_VERSION,
        "environment": "local",
        "artifactSha256": artifact_hash,
        "executedAt": executed_at,
        "gate": gate,
        "result": "passed" if completed.returncode == 0 else "failed",
        "command": command,
        "exitCode": completed.returncode,
        "evidenceSha256": _output_digest(completed),
        "humanReviewer": None,
    }


def not_run_evidence(gate: str, artifact_hash: str, generated_at: str) -> dict[str, Any]:
    automated = gate in {
        "tenant_isolation", "accessibility_automated", "skill_evals", "rollback_rehearsal",
    }
    reason = "rerun with --run-local-gates" if automated else HUMAN_GATE_REASON
    return {
        "artifactId": ARTIFACT_ID,
        "artifactVersion": ARTIFACT_VERSION,
        "environment": "local",
        "artifactSha256": artifact_hash,
        "executedAt": generated_at,
        "gate": gate,
        "result": "not_run",
        "command": reason,
        "exitCode": None,
        "evidenceSha256": None,
        "humanReviewer": None,
    }


def collect_local_evidence(*, database_url: str, artifact_hash: str) -> list[dict[str, Any]]:
    generated_at = datetime.now(UTC).isoformat()
    evidence = {gate: not_run_evidence(gate, artifact_hash, generated_at) for gate in GATES}
    evidence["tenant_isolation"] = run_gate_command(
        gate="tenant_isolation",
        args=[sys.executable, "-m", "pytest", "-q", "backend/tests/test_ai_formation_integration.py"],
        cwd=API_ROOT,
        artifact_hash=artifact_hash,
        environment={"TEST_DATABASE_URL": database_url},
    )
    evidence["accessibility_automated"] = run_gate_command(
        gate="accessibility_automated",
        args=["npm", "run", "test:e2e:ai-formation"],
        cwd=WEB,
        artifact_hash=artifact_hash,
        environment={"NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost"},
    )
    evidence["skill_evals"] = run_gate_command(
        gate="skill_evals",
        args=[
            sys.executable,
            str(WEB / "skills" / "spiritual-planet-sunday-school-ai-formation-batches-01-12" / "scripts" / "validate-all.py"),
        ],
        cwd=WEB,
        artifact_hash=artifact_hash,
    )
    evidence["rollback_rehearsal"] = run_gate_command(
        gate="rollback_rehearsal",
        args=[
            sys.executable,
            str(BACKEND / "scripts" / "verify_ai_formation_migrations.py"),
            "--allow-local-test-database",
        ],
        cwd=API_ROOT,
        artifact_hash=artifact_hash,
        environment={"AI_FORMATION_MIGRATION_DATABASE_URL": database_url},
        evidence_command=(
            f"{shlex.quote(sys.executable)} backend/scripts/verify_ai_formation_migrations.py "
            "--allow-local-test-database (URL supplied via redacted environment variable)"
        ),
    )
    return [evidence[gate] for gate in GATES]


def build_report(*, run_local_gates: bool, database_url: str | None) -> tuple[dict[str, Any], bool]:
    files = artifact_files()
    missing_files = [_artifact_label(path) for path in files if not path.is_file()]
    if run_local_gates and missing_files:
        raise ValueError(
            "artifact scope is incomplete; missing files: " + ", ".join(missing_files)
        )
    artifact_hash = artifact_sha256(files)
    generated_at = datetime.now(UTC).isoformat()
    if run_local_gates:
        if not database_url:
            raise ValueError("--database-url or TEST_DATABASE_URL is required with --run-local-gates")
        evidence = collect_local_evidence(database_url=database_url, artifact_hash=artifact_hash)
    else:
        evidence = [not_run_evidence(gate, artifact_hash, generated_at) for gate in GATES]

    executed = [item for item in evidence if item["result"] != "not_run"]
    local_gate_failure = any(item["result"] != "passed" for item in executed)
    report = {
        "schemaVersion": "1.1.0",
        "certificationStatus": "NOT_CERTIFIED",
        "automatedApproval": False,
        "humanReleaseDecisionRequired": True,
        "artifactFileCount": len(files),
        "artifactFilesPresent": len(files) - len(missing_files),
        "missingArtifactFiles": missing_files,
        "generatedAt": generated_at,
        "localGateExecutionRequested": run_local_gates,
        "evidence": evidence,
        "limitations": [
            "Local evidence is not staging or production evidence.",
            "Human gates are intentionally unsigned.",
            "Automated browser evidence does not replace screen-reader or physical-device acceptance.",
            "Command output is represented by SHA-256 only and may be retained separately by the caller.",
        ],
    }
    return report, local_gate_failure


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-local-gates",
        action="store_true",
        help="execute tenant isolation, browser accessibility, skill eval and rollback rehearsal",
    )
    parser.add_argument(
        "--database-url",
        help="isolated local test database; defaults to TEST_DATABASE_URL",
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        report, failed = build_report(
            run_local_gates=args.run_local_gates,
            database_url=args.database_url or os.environ.get("TEST_DATABASE_URL"),
        )
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    artifact_hash = report["evidence"][0]["artifactSha256"]
    print(f"wrote {args.output} ({artifact_hash})")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
