"""Prove reviewed account erasure, rollback and replay across real HTTP workers."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import json
import os
import subprocess
import sys
from uuid import UUID

import psycopg2
import pytest

from scripts.execute_account_erasure import ErasureRejected, execute_erasure
from test_ordo_account_custody_http import (
    OTHER, OWNER, ROUTE, accounts, isolated_dsn, rows, worker,
)

ROOT = Path(__file__).resolve().parents[1]


def requests(dsn):
    with closing(psycopg2.connect(dsn)) as conn, conn, conn.cursor() as cur:
        cur.execute((ROOT / "migrations/0248_account_erasure_receipts.sql").read_text())
        cur.execute(
            "INSERT INTO account_deletion_requests(user_id) "
            "SELECT id FROM users WHERE email = %s RETURNING id",
            (OWNER,),
        )
        return UUID(cur.fetchone()[0])


@pytest.mark.no_db
def test_reviewed_erasure_is_atomic_and_replayable(isolated_dsn, tmp_path):
    dsn, pg_pid = isolated_dsn
    tokens = accounts(dsn)
    request_id = requests(dsn)
    with worker(dsn, tmp_path, "owner") as (owner_pid, a), worker(
        dsn, tmp_path, "other"
    ) as (other_pid, b):
        auth = {"Authorization": "Bearer " + tokens[OWNER]}
        other_auth = {"Authorization": "Bearer " + tokens[OTHER]}
        for client, headers, payload in [(a, auth, "owner"), (b, other_auth, "other")]:
            client.post(ROUTE + "/record", headers=headers,
                        json={"input_text": payload}).raise_for_status()
        b.get(ROUTE + "/history", headers=auth).raise_for_status()

        command = [
            sys.executable, str(ROOT / "scripts/execute_account_erasure.py"),
            "--request-id", str(request_id), "--confirm-reviewed-request", str(request_id),
        ]
        env = {**os.environ, "ACCOUNT_ERASURE_DATABASE_URL": dsn}
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(subprocess.run, command, env=env, check=True,
                                capture_output=True, text=True) for _ in range(2)]
            receipts = [json.loads(job.result(timeout=10).stdout) for job in jobs]
        first, second = receipts
        assert first == second and set(first) == {"request_id", "completed_at"}
        assert first["request_id"] == str(request_id)
        assert pg_pid > 0 and owner_pid != other_pid
        for client in (a, b):
            assert client.get(ROUTE + "/history", headers=auth).status_code == 401
            assert client.post(ROUTE + "/record", headers=auth,
                               json={"input_text": "stale"}).status_code == 401
        assert rows(dsn) == [(OTHER, "other")]
        with closing(psycopg2.connect(dsn)) as conn, conn.cursor() as cur:
            cur.execute("SELECT request_id::text FROM account_erasure_receipts")
            assert cur.fetchall() == [(str(request_id),)]
        print(json.dumps({"postgres_pid": pg_pid, "http_pids": [owner_pid, other_pid]}))


@pytest.mark.no_db
def test_executor_failure_keeps_account_and_request(isolated_dsn):
    dsn, pg_pid = isolated_dsn
    accounts(dsn)
    request_id = requests(dsn)
    with closing(psycopg2.connect(dsn)) as conn, conn, conn.cursor() as cur:
        cur.execute("UPDATE account_deletion_requests SET status = 'cancelled'")
    with pytest.raises(ErasureRejected, match="not pending"):
        execute_erasure(dsn, request_id)
    with closing(psycopg2.connect(dsn)) as conn, conn, conn.cursor() as cur:
        cur.execute("UPDATE account_deletion_requests SET status = 'pending_review'")
        cur.execute("ALTER TABLE account_erasure_receipts ADD CHECK (completed_at < '2000-01-01')")
    with pytest.raises(psycopg2.errors.CheckViolation):
        execute_erasure(dsn, request_id)
    with closing(psycopg2.connect(dsn)) as conn, conn.cursor() as cur:
        cur.execute("SELECT status FROM account_deletion_requests")
        assert cur.fetchall() == [("pending_review",)]
        cur.execute("SELECT COUNT(*) FROM users")
        assert cur.fetchone() == (2,)
        cur.execute("SELECT COUNT(*) FROM account_erasure_receipts")
        assert cur.fetchone() == (0,)
        cur.execute("SELECT COUNT(*) FROM user_tokens")
        assert cur.fetchone() == (5,)
    assert pg_pid > 0


@pytest.mark.no_db
def test_reviewed_erasure_with_0249_purges_mixed_case_tokens_and_social_tables(isolated_dsn):
    dsn, pg_pid = isolated_dsn
    accounts(dsn)
    request_id = requests(dsn)
    with closing(psycopg2.connect(dsn)) as conn, conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS friendships (
                id SERIAL PRIMARY KEY,
                requester VARCHAR(255) NOT NULL,
                addressee VARCHAR(255) NOT NULL,
                user_low VARCHAR(255) NOT NULL,
                user_high VARCHAR(255) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'accepted'
            );
            CREATE TABLE IF NOT EXISTS chat_messages (
                id BIGSERIAL PRIMARY KEY,
                sender VARCHAR(255) NOT NULL,
                recipient VARCHAR(255) NOT NULL,
                body TEXT NOT NULL
            );
            """
        )
        cur.execute((ROOT / "migrations/0245_social_safety.sql").read_text(encoding="utf-8"))
        cur.execute((ROOT / "migrations/0249_industrial_erasure_and_safety_indexes.sql").read_text(encoding="utf-8"))
        cur.execute(
            "INSERT INTO user_tokens(token, email, data, expires_at) "
            "VALUES ('mixed-case-tok', %s, '{}'::jsonb, NOW() + INTERVAL '10 minutes')",
            (OWNER.upper(),),
        )
        low, high = sorted((OWNER, OTHER))
        cur.execute(
            "INSERT INTO friendships(requester, addressee, user_low, user_high) VALUES (%s, %s, %s, %s)",
            (OWNER, OTHER, low, high),
        )
        cur.execute(
            "INSERT INTO chat_messages(sender, recipient, body) VALUES (%s, %s, 'secret dm')",
            (OWNER.upper(), OTHER),
        )
        cur.execute(
            "INSERT INTO social_reports(reporter_email, target_email, resource_type, resource_key, category, status) "
            "VALUES (%s, %s, 'chat', 'dm-1', 'harassment', 'review_pending') RETURNING id::text",
            (OTHER, OWNER),
        )
        open_report_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO social_reports(reporter_email, target_email, resource_type, resource_key, category, status) "
            "VALUES (%s, %s, 'chat', 'dm-2', 'spam', 'closed')",
            (OTHER, OWNER),
        )

    receipt = execute_erasure(dsn, request_id)
    assert receipt["request_id"] == str(request_id)
    with closing(psycopg2.connect(dsn)) as conn, conn.cursor() as cur:
        cur.execute("SELECT table_name, reason FROM erasure_coverage_gaps()")
        assert cur.fetchall() == []
        cur.execute("SELECT COUNT(*) FROM user_tokens WHERE lower(email) = lower(%s)", (OWNER,))
        assert cur.fetchone() == (0,)
        cur.execute("SELECT COUNT(*) FROM friendships")
        assert cur.fetchone() == (0,)
        cur.execute("SELECT COUNT(*) FROM chat_messages")
        assert cur.fetchone() == (0,)
        cur.execute("SELECT target_email, status FROM social_reports WHERE id = %s::uuid", (open_report_id,))
        assert cur.fetchone() == ("[erased]", "review_pending")
        cur.execute("SELECT COUNT(*) FROM social_reports")
        assert cur.fetchone() == (1,)
    assert pg_pid > 0
