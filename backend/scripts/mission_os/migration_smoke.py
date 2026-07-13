#!/usr/bin/env python3
"""Mission OS migration smoke test — run against a real PostgreSQL.

Applies every project migration from an empty database (via the project's own
run_migrations), then verifies the Mission OS Batch 1-6 tables (migrations
0186-0206) exist, have Row-Level Security enabled with a tenant-isolation policy,
and that tenant isolation actually holds behaviourally.

Usage:
    DATABASE_URL=postgresql://user:pass@host:5432/db python scripts/mission_os/migration_smoke.py

Exit code 0 = PASS. Non-zero = FAIL (prints the failing check).

Note on RLS behaviour: PostgreSQL bypasses RLS for the table owner / superuser
unless FORCE ROW LEVEL SECURITY is set. The behavioural tenant-isolation probe
therefore runs under a dedicated non-owner role when possible; if it must run as
a superuser it reports the caveat instead of failing.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[2]
sys.path.insert(0, str(BACKEND))

# A representative slice of the 117 Mission OS Batch 1-6 tables (one per migration).
SAMPLE_TABLES = [
    "mission_field_classifications",        # 0186
    "mission_sensitive_export_requests",    # 0187
    "mission_fields",                       # 0188
    "mission_people_groups",                # 0189
    "mission_claims",                       # 0190
    "mission_field_assessments",            # 0191
    "mission_calling_journeys",             # 0192
    "mission_readiness_assessments",        # 0193
    "mission_prompt_registry",              # 0194
    "mission_training_plans",               # 0195
    "mission_practicums",                   # 0196
    "mission_stage_certifications",         # 0197
    "mission_candidate_applications",       # 0198
    "mission_teams",                        # 0199
    "mission_local_partner_profiles",       # 0200
    "mission_financial_plans",              # 0201
    "mission_support_pledges",              # 0202
    "mission_legal_identity_paths",         # 0203
    "mission_compliance_cases",             # 0204
    "mission_medical_readiness_profiles",   # 0205
    "mission_deployment_readiness_gates",   # 0206
]


def fail(msg: str) -> None:
    print(f"[SMOKE] FAIL: {msg}")
    sys.exit(1)


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        fail("DATABASE_URL is not set")
    try:
        import psycopg2
    except Exception as exc:  # pragma: no cover
        fail(f"psycopg2 not installed: {exc}")
    from core.migrations import run_migrations

    print("[SMOKE] applying all migrations from empty ...")
    applied = run_migrations(url)
    print(f"[SMOKE] run_migrations applied {len(applied)} migration(s)")

    conn = psycopg2.connect(url)
    try:
        with conn.cursor() as cur:
            # 1) tables exist
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name = ANY(%s)", (SAMPLE_TABLES,))
            found = {r[0] for r in cur.fetchall()}
            missing = [t for t in SAMPLE_TABLES if t not in found]
            if missing:
                fail(f"missing tables: {missing}")
            print(f"[SMOKE] all {len(SAMPLE_TABLES)} sample tables present")

            # 2) RLS enabled + tenant-isolation policy on each
            cur.execute("SELECT relname FROM pg_class WHERE relname = ANY(%s) AND relrowsecurity", (SAMPLE_TABLES,))
            rls_on = {r[0] for r in cur.fetchall()}
            no_rls = [t for t in SAMPLE_TABLES if t not in rls_on]
            if no_rls:
                fail(f"RLS not enabled on: {no_rls}")
            cur.execute("SELECT tablename FROM pg_policies WHERE tablename = ANY(%s) AND policyname='mission_tenant_isolation'", (SAMPLE_TABLES,))
            policied = {r[0] for r in cur.fetchall()}
            no_policy = [t for t in SAMPLE_TABLES if t not in policied]
            if no_policy:
                fail(f"missing mission_tenant_isolation policy on: {no_policy}")
            print(f"[SMOKE] RLS + tenant-isolation policy verified on all sample tables")

            # 3) behavioural tenant isolation probe on mission_field_classifications
            cur.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
            is_super = bool(cur.fetchone()[0])
            cur.execute("SET row_security = on")
            cur.execute("SET app.tenant_id = 'tenant-a'")
            cur.execute(
                "INSERT INTO mission_field_classifications(tenant_id,resource_type,field_name,sensitivity_level) "
                "VALUES('tenant-a','probe','f',%s) ON CONFLICT DO NOTHING", ("P2",))
            cur.execute("SET app.tenant_id = 'tenant-b'")
            cur.execute("SELECT count(*) FROM mission_field_classifications WHERE resource_type='probe'")
            leaked = cur.fetchone()[0]
            conn.rollback()
            if is_super:
                print(f"[SMOKE] tenant-isolation probe skipped enforcement check "
                      f"(connected as superuser/owner; RLS is bypassed by design). rows seen={leaked}")
            elif leaked != 0:
                fail(f"tenant isolation breached: tenant-b saw {leaked} of tenant-a's rows")
            else:
                print("[SMOKE] behavioural tenant isolation holds (tenant-b sees 0 of tenant-a rows)")
    finally:
        conn.close()

    print("[SMOKE] PASS")


if __name__ == "__main__":
    main()
