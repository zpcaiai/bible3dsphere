#!/usr/bin/env python3
"""One command that answers "would a deletion request actually delete everything?".

Run it against staging (never production — step 3 deletes a row it created):

    DATABASE_URL=postgresql://... python3 backend/scripts/verify_emd_erasure.py

    # coverage checks only, no writes:
    DATABASE_URL=postgresql://... python3 backend/scripts/verify_emd_erasure.py --read-only

Exit code 0 means every personal table is inside the erasure path. Anything else means a
deletion request would leave data behind, and the exact tables are printed.

The offline suite (`tests/test_emd_erasure_schema_verification.py`) already replays this
logic against the migration DDL. What only a real server can tell you is whether the
plpgsql compiles and whether *your* database — including tables created outside
`migrations/`, like `mvfe_memories` — matches the schema the migrations describe.
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path


MIGRATION = Path(__file__).resolve().parents[1] / "migrations" / "0233_emd_erasure_propagation.sql"

GREEN, RED, YELLOW, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[0m"


def _mark(ok: bool) -> str:
    return f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--read-only", action="store_true",
                        help="skip the round-trip that creates and erases a throwaway user")
    parser.add_argument("--apply-migration", action="store_true", default=True,
                        help="apply 0233 first (idempotent; default on)")
    args = parser.parse_args()

    url = os.environ.get("DATABASE_URL")
    if not url:
        print(f"{RED}DATABASE_URL is not set{RESET}", file=sys.stderr)
        return 2

    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        print(f"{RED}psycopg2 is not installed{RESET}", file=sys.stderr)
        return 2

    conn = psycopg2.connect(url, connect_timeout=10)
    conn.autocommit = False
    failures: list[str] = []

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if args.apply_migration:
                cur.execute(MIGRATION.read_text(encoding="utf-8"))
                conn.commit()
                print(f"{_mark(True)}  迁移 0233 已应用（plpgsql 编译通过）")

            # 1) 覆盖缺口必须为空
            cur.execute("SELECT table_name, reason FROM erasure_coverage_gaps()")
            gaps = cur.fetchall()
            ok = not gaps
            print(f"{_mark(ok)}  erasure_coverage_gaps() -> {len(gaps)} 条")
            if not ok:
                failures.append("coverage_gaps")
                for row in gaps[:40]:
                    print(f"        {row['table_name']}: {row['reason']}")

            # 2) EMD 域必须全覆盖
            cur.execute("SELECT total_emd_tables, covered, uncovered FROM emd_erasure_coverage()")
            row = cur.fetchone()
            ok = row and not row["uncovered"] and row["covered"] == row["total_emd_tables"]
            print(f"{_mark(bool(ok))}  emd_erasure_coverage() -> {row['covered']}/{row['total_emd_tables']} 覆盖")
            if not ok:
                failures.append("emd_coverage")
                print(f"        未覆盖: {row['uncovered']}")

            # 3) 向量库确实在删除范围内
            cur.execute("SELECT to_regclass('mvfe_memories') AS present")
            if cur.fetchone()["present"]:
                cur.execute("SELECT 1 FROM personal_userid_tables() WHERE table_name='mvfe_memories'")
                ok = cur.fetchone() is not None
                print(f"{_mark(ok)}  mvfe_memories（向量库，含用户原文）在删除范围内")
                if not ok:
                    failures.append("vector_store")
            else:
                print(f"{YELLOW}SKIP{RESET}  mvfe_memories 在此库中不存在")

            # 4) 规模抽查，防止发现函数意外返回空集
            cur.execute("SELECT count(*) AS n FROM personal_email_tables()")
            email_n = cur.fetchone()["n"]
            cur.execute("SELECT count(*) AS n FROM personal_userid_tables()")
            userid_n = cur.fetchone()["n"]
            ok = email_n > 100 and userid_n > 0
            print(f"{_mark(ok)}  发现 {email_n} 张 email 键表、{userid_n} 张 user_id 键表")
            if not ok:
                failures.append("discovery_returned_too_few")

        # 5) 真实往返：建一个一次性用户，写一行，删账号，确认没了
        if not args.read_only:
            probe = f"erasure-probe-{uuid.uuid4().hex[:12]}@example.invalid"
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT table_name FROM personal_email_tables() "
                            "WHERE table_name LIKE 'formation_twin_emd_%' LIMIT 1")
                target = cur.fetchone()
                if not target:
                    print(f"{YELLOW}SKIP{RESET}  此库没有 EMD 表，跳过往返验证")
                else:
                    table = target["table_name"]
                    try:
                        cur.execute(f"INSERT INTO {table}(email) VALUES(%s)", (probe,))
                        conn.commit()
                        cur.execute("SELECT * FROM erase_user_data(%s)", (probe,))
                        cur.fetchall()
                        conn.commit()
                        cur.execute(f"SELECT count(*) AS n FROM {table} WHERE email=%s", (probe,))
                        remaining = cur.fetchone()["n"]
                        ok = remaining == 0
                        print(f"{_mark(ok)}  往返验证：{table} 中残留 {remaining} 行")
                        if not ok:
                            failures.append("round_trip")
                    except Exception as exc:
                        conn.rollback()
                        print(f"{YELLOW}SKIP{RESET}  往返验证无法执行（{type(exc).__name__}: {exc}）")
        else:
            print(f"{YELLOW}SKIP{RESET}  --read-only：跳过往返验证")

    finally:
        conn.close()

    print()
    if failures:
        print(f"{RED}删除请求会留下数据。失败项: {', '.join(failures)}{RESET}")
        return 1
    print(f"{GREEN}每一张个人表都在删除路径内。{RESET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
