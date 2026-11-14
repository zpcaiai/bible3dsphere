"""Complete a reviewed primary-database erasure using operator DB credentials.

The operator confirms the reviewed request UUID. Backups, log stores and
external service data follow their respective retention and deletion workflows.
"""

import argparse
from contextlib import closing
import json
import os
from uuid import UUID

import psycopg2


class ErasureRejected(RuntimeError):
    """A request or database invariant prohibits completing this erasure."""


def execute_erasure(dsn: str, request_id: UUID) -> dict[str, str]:
    key = str(request_id)
    with closing(psycopg2.connect(dsn)) as conn, conn, conn.cursor() as cur:
        cur.execute("SET LOCAL search_path TO public, pg_catalog")
        cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (key,))
        cur.execute("SELECT completed_at FROM account_erasure_receipts WHERE request_id = %s", (key,))
        prior = cur.fetchone()
        if prior:
            return {"request_id": key, "completed_at": prior[0].isoformat()}

        # Intake locks the account before updating the request. Use the same
        # lock order and recheck the mutable request row after locking.
        cur.execute(
            "SELECT u.id, u.email FROM users u JOIN account_deletion_requests r "
            "ON r.user_id = u.id WHERE r.id = %s FOR UPDATE OF u",
            (key,),
        )
        account = cur.fetchone()
        if account is None:
            raise ErasureRejected("Request does not identify a current account")
        user_id, email = account
        cur.execute(
            "SELECT status FROM account_deletion_requests "
            "WHERE id = %s AND user_id = %s FOR UPDATE",
            (key, user_id),
        )
        if cur.fetchone() != ("pending_review",):
            raise ErasureRejected("Request is not pending review")
        cur.execute("SELECT EXISTS (SELECT 1 FROM erasure_coverage_gaps())")
        if cur.fetchone()[0]:
            raise ErasureRejected("Primary database erasure coverage check failed")

        cur.execute("SELECT * FROM erase_user_data(%s)", (email,))
        if dict(cur.fetchall()).get("users") != 1:
            raise ErasureRejected("Erasure did not remove the requested account")
        cur.execute(
            "SELECT EXISTS (SELECT 1 FROM user_tokens WHERE lower(email) = lower(%s)) "
            "OR EXISTS (SELECT 1 FROM ordo_amoris_records WHERE email = %s) "
            "OR EXISTS (SELECT 1 FROM account_deletion_requests WHERE id = %s)",
            (email, email, key),
        )
        if cur.fetchone()[0]:
            raise ErasureRejected("Erasure left a session, Ordo record or pending request")
        cur.execute(
            "INSERT INTO account_erasure_receipts(request_id) VALUES (%s) RETURNING completed_at",
            (key,),
        )
        completed_at, = cur.fetchone()
        return {"request_id": key, "completed_at": completed_at.isoformat()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-id", type=UUID, required=True)
    parser.add_argument("--confirm-reviewed-request", type=UUID, required=True)
    args = parser.parse_args()
    if args.request_id != args.confirm_reviewed_request:
        parser.error("Reviewed request confirmation does not match")
    dsn = os.getenv("ACCOUNT_ERASURE_DATABASE_URL")
    if not dsn:
        parser.error("ACCOUNT_ERASURE_DATABASE_URL is required")
    try:
        receipt = execute_erasure(dsn, args.request_id)
    except ErasureRejected as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
