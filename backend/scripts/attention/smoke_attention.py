#!/usr/bin/env python3
"""Smoke-check Attention Stewardship schema and static libraries."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

from attention_accountability import CHALLENGE_TEMPLATES, DEFAULT_PRIVACY  # noqa: E402
from attention_domain import SCRIPTURE_LIBRARY, pattern_definitions  # noqa: E402
from attention_integration import ATTENTION_TABLES, attention_environment_check  # noqa: E402


def main() -> None:
    if not os.getenv("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor() as cur:
            missing = []
            for table in ATTENTION_TABLES:
                cur.execute("SELECT to_regclass(%s)", (f"public.{table}",))
                if not cur.fetchone()[0]:
                    missing.append(table)
            if missing:
                raise SystemExit(f"missing attention tables: {', '.join(missing)}")
    finally:
        conn.close()
    assert len(CHALLENGE_TEMPLATES) >= 9
    assert len(pattern_definitions()) >= 9
    assert len(SCRIPTURE_LIBRARY) > 0
    assert DEFAULT_PRIVACY["defaultPartnerVisibility"] == "status_only"
    env = attention_environment_check(os.environ)
    if not env["ok"]:
        raise SystemExit("; ".join(env["errors"]))
    print("attention smoke check passed")


if __name__ == "__main__":
    main()
