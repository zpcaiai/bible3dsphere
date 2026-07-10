#!/usr/bin/env python3
"""Seed deterministic Attention Stewardship demo data.

Safety rules:
- Refuses production environments.
- Uses only example.test demo emails.
- Upserts demo-owned rows and never deletes non-demo user data.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import psycopg2
from psycopg2.extras import Json

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

from attention_accountability import CHALLENGE_TEMPLATES, default_partner_permissions  # noqa: E402
from reset_attention_demo import clear_demo_data  # noqa: E402


DEMO_USERS = [
    ("demo.alice@example.test", "Alice"),
    ("demo.ben@example.test", "Ben"),
    ("demo.chloe@example.test", "Chloe"),
    ("demo.david@example.test", "David"),
    ("demo.eve@example.test", "Eve"),
]


def _require_safe_env() -> None:
    env = (os.getenv("NODE_ENV") or os.getenv("ENV") or "development").lower()
    if env == "production":
        raise SystemExit("Refusing to seed attention demo data in production.")
    if not os.getenv("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required.")


def _exec(cur, sql: str, params=()):
    cur.execute(sql, params)
    return cur


def seed() -> None:
    _require_safe_env()
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    prev_week_start = week_start - timedelta(days=7)
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor() as cur:
            # Rebuild only the reserved example.test scenario so repeated runs
            # produce the same counts without touching non-demo users.
            clear_demo_data(cur, delete_users=False)
            for email, name in DEMO_USERS:
                _exec(
                    cur,
                    """INSERT INTO users (email, nickname, avatar, openid, login_type, password_hash)
                    VALUES (%s,%s,'',%s, 'demo', 'demo-seed-login-disabled')
                    ON CONFLICT (email) DO UPDATE SET nickname=EXCLUDED.nickname""",
                    (email, name, f"attention-demo:{email}"),
                )
                _exec(
                    cur,
                    """INSERT INTO attention_privacy_settings
                    (user_id, default_partner_visibility, default_group_visibility,
                     default_challenge_visibility, share_scores_with_partners,
                     share_scores_with_groups, share_weekly_report_summary,
                     share_warfare_plan_progress, share_prayer_requests,
                     hide_sensitive_categories)
                    VALUES (%s,'status_only','status_only','status_only',false,false,true,true,true,
                            ARRAY['lust','financial_anxiety','family_conflict','mental_health','trauma','addiction','work_conflict','identity_shame'])
                    ON CONFLICT (user_id) DO NOTHING""",
                    (email,),
                )

            alice, ben, chloe, david, eve = [u[0] for u in DEMO_USERS]
            for offset in range(10):
                day = today - timedelta(days=offset)
                if offset in {1, 3, 8}:
                    continue
                pulls = ["fomo", "anxiety"] if offset % 2 == 0 else ["algorithm", "fatigue"]
                _exec(
                    cur,
                    """INSERT INTO attention_daily_covenants
                    (user_id, covenant_date, primary_offering, mission_focus, worship_focus,
                     relationship_focus, restoration_focus, main_risk, risk_pulls,
                     digital_boundary, time_boundary, spiritual_boundary, scripture_reference,
                     scripture_text, prayer)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'箴言 4:23',
                            '你要保守你心，胜过保守一切。','主啊，帮助我把注意力归给你。')
                    ON CONFLICT (user_id, covenant_date) DO UPDATE SET
                      primary_offering=EXCLUDED.primary_offering,
                      main_risk=EXCLUDED.main_risk,
                      risk_pulls=EXCLUDED.risk_pulls""",
                    (
                        alice, day, "完成今天的使命工作", "深度工作", "读经祷告",
                        "晚饭不看手机", "散步恢复",
                        "AI 资讯焦虑" if offset % 2 == 0 else "短视频与比较",
                        pulls, "上午 11 点前不看资讯", "30 分钟", "想刷新前先祷告 30 秒",
                    ),
                )
                if offset < 7:
                    _exec(
                        cur,
                        """INSERT INTO attention_entries
                        (user_id, entry_date, category, activity_name, duration_minutes, attention_state, pulls, note)
                        VALUES
                        (%s,%s,'mission','使命专注',60,'focused','{}','demo mission note'),
                        (%s,%s,'worship','读经祷告',20,'present','{}','demo worship note'),
                        (%s,%s,'captured','资讯流牵引',25,'scattered',%s,'demo captured note')""",
                        (alice, day, alice, day, alice, day, pulls),
                    )
                if offset in {0, 2, 4, 6}:
                    _exec(
                        cur,
                        """INSERT INTO attention_reviews
                        (user_id, review_date, biggest_capture, biggest_grace,
                         repentance_point, tomorrow_boundary, prayer)
                        VALUES (%s,%s,'被资讯牵引','看见后有归回','明天先设边界','上午固定信息窗口','主啊，带我安息。')
                        ON CONFLICT (user_id, review_date) DO UPDATE SET biggest_grace=EXCLUDED.biggest_grace""",
                        (alice, day),
                    )
                _exec(
                    cur,
                    """INSERT INTO attention_focus_sessions
                    (user_id, started_at, ended_at, planned_minutes, actual_minutes,
                     focus_type, intention, opening_prayer, closing_reflection,
                     interrupted, interruption_reason)
                    VALUES (%s,%s,%s,90,60,'mission','demo focus','short prayer','finished',%s,%s)""",
                    (
                        alice,
                        datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=1),
                        datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=2),
                        offset == 5,
                        "demo interruption" if offset == 5 else None,
                    ),
                )

            _exec(
                cur,
                """INSERT INTO attention_ai_diagnoses
                (user_id, diagnosis_date, diagnosis_type, input_summary, result,
                 provider, model_name, generated_by, safety_level, saved_by_user)
                VALUES (%s,%s,'daily',%s,%s,'fallback','rules','fallback','normal',true),
                       (%s,%s,'weekly_pattern',%s,%s,'fallback','rules','fallback','normal',true)""",
                (
                    alice, today, Json({"source": "demo", "entriesCount": 3}),
                    Json({"title": "资讯焦虑中的归回", "primaryPattern": {"key": "fomo_information_anxiety"}}),
                    alice, today - timedelta(days=3), Json({"source": "demo"}),
                    Json({"title": "疲惫时的真实恢复", "primaryPattern": {"key": "fatigue_escape"}}),
                ),
            )

            plan_ids = []
            for pattern, title in [("fomo_information_anxiety", "资讯焦虑守心计划"), ("fatigue_escape_algorithm", "疲惫逃避守心计划")]:
                row = _exec(
                    cur,
                    """INSERT INTO attention_warfare_plans
                    (user_id, pattern_key, title, description, primary_pulls,
                     digital_boundary, spiritual_boundary, replacement_practice, status)
                    VALUES (%s,%s,%s,'demo plan',ARRAY['fomo','anxiety'],'上午固定窗口','刷新前祷告','散步或读经','active')
                    RETURNING id""",
                    (alice, pattern, title),
                ).fetchone()
                plan_ids.append(row[0])
            for index, status in enumerate(["returned", "resisted", "captured", "not_seen"]):
                plan_id = plan_ids[index % len(plan_ids)]
                checkin_day = today - timedelta(days=index)
                _exec(
                    cur,
                    """INSERT INTO attention_warfare_checkins
                    (user_id, plan_id, checkin_date, status, noticed, resisted, returned_to_god,
                     boundary_used, replacement_used, grace_noticed)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,'demo boundary','demo replacement','demo grace')""",
                    (alice, plan_id, checkin_day, status, status != "not_seen", status == "resisted", status == "returned"),
                )

            for offset in range(7):
                score_day = today - timedelta(days=offset)
                score = 72 - offset
                _exec(
                    cur,
                    """INSERT INTO attention_daily_scores
                    (user_id, score_date, score, score_label, data_completeness, confidence,
                     component_scores, input_summary, insights, generated_by, version)
                    VALUES (%s,%s,%s,'steady',78,'medium',%s,%s,%s,'rules','v1')
                    ON CONFLICT (user_id, score_date) DO UPDATE SET score=EXCLUDED.score""",
                    (
                        alice, score_day, score,
                        Json({"covenant": 15, "focus": 20, "awareness": 18}),
                        Json({"source": "demo"}),
                        Json({"nextStep": "继续固定资讯窗口。"}),
                    ),
                )
            _exec(
                cur,
                """INSERT INTO attention_weekly_reports
                (user_id, week_start, week_end, worship_minutes, mission_minutes,
                 relationship_minutes, restoration_minutes, captured_minutes,
                 score_average, score_label, data_completeness, top_pulls,
                 report_sections, summary, next_week_practice, prayer, status, version)
                VALUES (%s,%s,%s,120,300,90,110,150,72,'steady',78,%s,%s,'demo weekly summary','下周固定资讯窗口','请为我的守心节奏祷告。','generated','v1'),
                       (%s,%s,%s,90,240,60,80,180,66,'growing',72,%s,%s,'demo previous weekly summary','晚上不刷短视频','请为我的恢复节奏祷告。','generated','v1')
                ON CONFLICT (user_id, week_start, week_end) DO UPDATE SET score_average=EXCLUDED.score_average""",
                (
                    alice, week_start, week_start + timedelta(days=6),
                    Json([{"pull": "fomo", "label": "错失恐惧", "count": 5}, {"pull": "anxiety", "label": "焦虑", "count": 4}]),
                    Json({"weeklySummary": "这一周更清楚看见资讯焦虑。"}),
                    alice, prev_week_start, prev_week_start + timedelta(days=6),
                    Json([{"pull": "fatigue", "label": "疲惫逃避", "count": 3}]),
                    Json({"weeklySummary": "上一周学习真实恢复。"}),
                ),
            )

            pair_key = "::".join(sorted([alice, ben]))
            _exec(
                cur,
                """INSERT INTO attention_accountability_relationships
                (requester_user_id, partner_user_id, pair_key, status,
                 requester_message, requester_permissions, partner_permissions, accepted_at)
                VALUES (%s,%s,%s,'active','demo partner invite',%s,%s,now())
                ON CONFLICT (pair_key) WHERE status IN ('pending','active','paused') DO UPDATE SET status='active'""",
                (
                    alice,
                    ben,
                    pair_key,
                    Json(default_partner_permissions({"canSeeWeeklyReportSummary": True})),
                    Json(default_partner_permissions()),
                ),
            )
            _exec(
                cur,
                """INSERT INTO attention_prayer_requests
                (owner_user_id, target_user_id, title, body, category, visibility_level, is_sensitive, status)
                VALUES (%s,%s,'请为今天的信息边界代祷','demo prayer body','attention','summary',false,'open')
                ON CONFLICT DO NOTHING RETURNING id""",
                (alice, ben),
            )
            prayer_row = cur.fetchone()
            if prayer_row:
                _exec(cur, "INSERT INTO attention_prayer_marks (prayer_request_id, user_id, message) VALUES (%s,%s,'prayed') ON CONFLICT DO NOTHING", (prayer_row[0], ben))
            _exec(
                cur,
                """INSERT INTO attention_share_snapshots
                (owner_user_id, scope, target_user_id, source_type, title, summary,
                 payload, visibility_level, sensitive_redactions, revoked_at)
                VALUES
                (%s,'partner',%s,'weekly_report','周报摘要','demo shared weekly summary',%s,'summary','{}',NULL),
                (%s,'partner',%s,'weekly_report','已撤回周报摘要','demo revoked share',%s,'summary','{}',now())""",
                (alice, ben, Json({"summary": "demo", "scoreIncluded": False}), alice, ben, Json({"summary": "revoked"})),
            )

            _exec(
                cur,
                """INSERT INTO attention_groups
                (owner_user_id, name, description, group_type, invite_code,
                 invite_enabled, default_member_visibility, guidelines, status)
                VALUES (%s,'周三守心小组','demo group','private','demo-wed-watch',true,'status_only','彼此提醒，不比较，不公开软弱。','active')
                ON CONFLICT (invite_code) DO UPDATE SET status='active'
                RETURNING id""",
                (chloe,),
            )
            group_id = cur.fetchone()[0]
            for email, role in [(chloe, "owner"), (alice, "member"), (ben, "member"), (david, "member")]:
                _exec(
                    cur,
                    """INSERT INTO attention_group_members (group_id, user_id, role, status, visibility_level)
                    VALUES (%s,%s,%s,'active','status_only')
                    ON CONFLICT (group_id, user_id) DO UPDATE SET role=EXCLUDED.role, status='active'""",
                    (group_id, email, role),
                )
            challenge_ids = []
            for template in CHALLENGE_TEMPLATES[:2]:
                _exec(
                    cur,
                    """INSERT INTO attention_group_challenges
                    (group_id, created_by_user_id, template_key, title, description,
                     challenge_type, start_date, end_date, target_days, target_minutes,
                     checkin_prompt, privacy_mode, allow_prayer_requests, status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true,'active')
                    RETURNING id""",
                    (
                        group_id, chloe, template["key"], template["title"], template["description"],
                        template["challengeType"], week_start, week_start + timedelta(days=6),
                        template["defaultTargetDays"], template["defaultTargetMinutes"],
                        template["checkinPrompt"], template["privacyMode"],
                    ),
                )
                challenge_id = cur.fetchone()[0]
                challenge_ids.append(challenge_id)
                for email in (alice, ben, david):
                    _exec(cur, "INSERT INTO attention_challenge_participations (challenge_id, user_id, status) VALUES (%s,%s,'active') ON CONFLICT DO NOTHING", (challenge_id, email))
                for email, days in [(alice, 3), (ben, 2), (david, 1)]:
                    for i in range(days):
                        _exec(
                            cur,
                            """INSERT INTO attention_challenge_checkins
                            (challenge_id, user_id, checkin_date, completed, visibility_level)
                            VALUES (%s,%s,%s,true,'status_only') ON CONFLICT DO NOTHING""",
                            (challenge_id, email, week_start + timedelta(days=i)),
                        )
            archived = CHALLENGE_TEMPLATES[2]
            _exec(
                cur,
                """INSERT INTO attention_group_challenges
                (group_id, created_by_user_id, template_key, title, description,
                 challenge_type, start_date, end_date, target_days, target_minutes,
                 checkin_prompt, privacy_mode, allow_prayer_requests, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true,'archived')""",
                (
                    group_id, chloe, archived["key"], archived["title"], archived["description"],
                    archived["challengeType"], prev_week_start, prev_week_start + timedelta(days=6),
                    archived["defaultTargetDays"], archived["defaultTargetMinutes"],
                    archived["checkinPrompt"], archived["privacyMode"],
                ),
            )
            _exec(
                cur,
                """INSERT INTO attention_share_snapshots
                (owner_user_id, scope, target_group_id, source_type, source_id, title, summary,
                 payload, visibility_level, sensitive_redactions)
                VALUES
                (%s,'group',%s,'challenge_progress',%s,'挑战进展','demo aggregate challenge progress',%s,'status_only','{}'),
                (%s,'group',%s,'daily_summary',NULL,'今日守心状态','demo daily status',%s,'status_only','{}')""",
                (
                    alice, group_id, str(challenge_ids[0]), Json({"completed": True, "ranking": False}),
                    ben, group_id, Json({"covenantDone": True, "reviewDone": False}),
                ),
            )
            _exec(
                cur,
                """INSERT INTO attention_prayer_requests
                (owner_user_id, target_group_id, title, body, category, visibility_level, is_sensitive, status)
                VALUES (%s,%s,'请为小组挑战代祷','demo group prayer','attention','summary',false,'open'),
                       (%s,%s,'需要温柔支持','demo sensitive group prayer','attention','summary',true,'open')""",
                (alice, group_id, david, group_id),
            )
        conn.commit()
    finally:
        conn.close()
    print(json.dumps({"ok": True, "users": DEMO_USERS, "groupInviteCode": "demo-wed-watch"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    seed()
