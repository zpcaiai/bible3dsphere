#!/usr/bin/env python3
"""Remove Attention Stewardship demo data scoped to example.test users."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

DEMO_USERS = [
    "demo.alice@example.test",
    "demo.ben@example.test",
    "demo.chloe@example.test",
    "demo.david@example.test",
    "demo.eve@example.test",
]


def main() -> None:
    env = (os.getenv("NODE_ENV") or os.getenv("ENV") or "development").lower()
    if env == "production":
        raise SystemExit("Refusing to reset attention demo data in production.")
    if not os.getenv("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required.")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM attention_groups WHERE owner_user_id = ANY(%s) OR invite_code='demo-wed-watch'", (DEMO_USERS,))
            group_ids = [r[0] for r in cur.fetchall()]
            cur.execute("SELECT id FROM attention_group_challenges WHERE group_id = ANY(%s)", (group_ids,))
            challenge_ids = [r[0] for r in cur.fetchall()]
            cur.execute("DELETE FROM attention_challenge_checkins WHERE challenge_id = ANY(%s) OR user_id = ANY(%s)", (challenge_ids, DEMO_USERS))
            cur.execute("DELETE FROM attention_challenge_participations WHERE challenge_id = ANY(%s) OR user_id = ANY(%s)", (challenge_ids, DEMO_USERS))
            cur.execute("DELETE FROM attention_group_challenges WHERE id = ANY(%s) OR group_id = ANY(%s)", (challenge_ids, group_ids))
            cur.execute("DELETE FROM attention_group_members WHERE group_id = ANY(%s) OR user_id = ANY(%s)", (group_ids, DEMO_USERS))
            cur.execute("DELETE FROM attention_group_invitations WHERE group_id = ANY(%s) OR invited_user_id = ANY(%s)", (group_ids, DEMO_USERS))
            cur.execute("DELETE FROM attention_groups WHERE id = ANY(%s) OR invite_code='demo-wed-watch'", (group_ids,))
            cur.execute("DELETE FROM attention_prayer_marks WHERE user_id = ANY(%s) OR prayer_request_id IN (SELECT id FROM attention_prayer_requests WHERE owner_user_id = ANY(%s) OR target_user_id = ANY(%s))", (DEMO_USERS, DEMO_USERS, DEMO_USERS))
            for table, column in [
                ("attention_share_snapshots", "owner_user_id"),
                ("attention_prayer_requests", "owner_user_id"),
                ("attention_accountability_relationships", "requester_user_id"),
                ("attention_privacy_settings", "user_id"),
                ("attention_weekly_reports", "user_id"),
                ("attention_daily_scores", "user_id"),
                ("attention_warfare_checkins", "user_id"),
                ("attention_warfare_plans", "user_id"),
                ("attention_ai_diagnoses", "user_id"),
                ("attention_focus_sessions", "user_id"),
                ("attention_reviews", "user_id"),
                ("attention_entries", "user_id"),
                ("attention_daily_covenants", "user_id"),
            ]:
                cur.execute(f"DELETE FROM {table} WHERE {column} = ANY(%s)", (DEMO_USERS,))
            cur.execute("DELETE FROM attention_accountability_relationships WHERE partner_user_id = ANY(%s)", (DEMO_USERS,))
            cur.execute("DELETE FROM attention_share_snapshots WHERE target_user_id = ANY(%s)", (DEMO_USERS,))
            cur.execute("DELETE FROM attention_prayer_requests WHERE target_user_id = ANY(%s)", (DEMO_USERS,))
            cur.execute("DELETE FROM users WHERE email = ANY(%s)", (DEMO_USERS,))
        conn.commit()
    finally:
        conn.close()
    print("attention demo data reset")


if __name__ == "__main__":
    main()
