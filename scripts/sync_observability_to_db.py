#!/usr/bin/env python3
"""Sync retrieval evaluation and artifact manifest JSON files into Postgres."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import Json


ROOT_DIR = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def iso_key(prefix: str) -> str:
    return f"{prefix}:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def sync_eval(conn, report_path: Path) -> bool:
    report = load_json(report_path)
    if not report:
        return False
    run_key = report.get("run_key") or iso_key("retrieval-eval")
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO retrieval_eval_runs (run_key, top_k, summary, cases, source_path)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (run_key) DO UPDATE
            SET top_k = EXCLUDED.top_k,
                summary = EXCLUDED.summary,
                cases = EXCLUDED.cases,
                source_path = EXCLUDED.source_path
            """,
            (
                run_key,
                int(report.get("top_k") or 0),
                Json(report.get("summary") or {}),
                Json(report.get("cases") or []),
                str(report_path.relative_to(ROOT_DIR) if report_path.is_relative_to(ROOT_DIR) else report_path),
            ),
        )
    return True


def sync_manifest(conn, manifest_path: Path) -> bool:
    manifest = load_json(manifest_path)
    if not manifest:
        return False
    manifest_key = manifest.get("manifest_key") or iso_key("artifact-manifest")
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO artifact_manifests (manifest_key, generated_at, payload, source_path)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (manifest_key) DO UPDATE
            SET generated_at = EXCLUDED.generated_at,
                payload = EXCLUDED.payload,
                source_path = EXCLUDED.source_path
            """,
            (
                manifest_key,
                manifest.get("generated_at"),
                Json(manifest),
                str(manifest_path.relative_to(ROOT_DIR) if manifest_path.is_relative_to(ROOT_DIR) else manifest_path),
            ),
        )
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""))
    parser.add_argument("--report", type=Path, default=ROOT_DIR / "evaluation" / "reports" / "retrieval_eval_latest.json")
    parser.add_argument("--manifest", type=Path, default=ROOT_DIR / "artifact_manifest.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required")
    with psycopg2.connect(args.database_url) as conn:
        synced_eval = sync_eval(conn, args.report)
        synced_manifest = sync_manifest(conn, args.manifest)
    print(json.dumps({"synced_eval": synced_eval, "synced_manifest": synced_manifest}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
