"""Small scheduled worker entrypoint for MissionBridge lifecycle jobs."""
from __future__ import annotations

import os
import time

import psycopg2


def run_once(database_url: str) -> dict:
    """Expire temporary grants and retain immutable safeguarding records."""
    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE mission_bridge_data_access_grants SET status='expired' WHERE status='active' AND expires_at <= now()")
            expired = cur.rowcount
            cur.execute("UPDATE mission_bridge_data_requests SET status='processing' WHERE status='pending' AND request_type='delete' AND requested_at <= now() - interval '24 hours'")
            deletion_requests = cur.rowcount
            cur.execute("DELETE FROM mission_bridge_checkins c USING mission_bridge_enrollments e WHERE c.enrollment_id=e.id AND c.created_at < now() - interval '730 days'")
            deleted_checkins = cur.rowcount
            cur.execute("INSERT INTO mission_bridge_retention_runs(records_deleted,completed_at) VALUES(%s,now())",(deleted_checkins,))
    return {"expired_access_grants": expired,"deletion_requests_started":deletion_requests,"expired_checkins_deleted":deleted_checkins}


def main() -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    interval = max(30, int(os.environ.get("MISSION_BRIDGE_WORKER_INTERVAL", "300")))
    while True:
        try:
            print(f"[mission-bridge-worker] {run_once(database_url)}", flush=True)
        except Exception as exc:
            print(f"[mission-bridge-worker] failed: {type(exc).__name__}", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
