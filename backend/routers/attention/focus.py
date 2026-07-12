"""Attention Stewardship / 守心 API — focus sessions / ledger entries / evening reviews / today summary routes.

Mechanically split from the original single-file routers/attention.py.
Do not change route paths/parameters/logic here without checking the whole package.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import os
import uuid
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ._common import *  # noqa: F401,F403
from ._common import (  # noqa: F401
    _CHECKIN_COLUMNS,
    _DIAGNOSIS_COLUMNS,
    _ENTRY_COLUMNS,
    _FOCUS_COLUMNS,
    _Json,
    _PLAN_COLUMNS,
    _REPORT_COLUMNS,
    _REVIEW_COLUMNS,
    _SCORE_COLUMNS,
    _SELECT_COLUMNS,
    _checkin_row_to_dto,
    _clean_text_list,
    _clip_text,
    _db_user_id,
    _diagnosis_row_to_dto,
    _entry_row_to_dto,
    _fetch_entries_between,
    _focus_row_to_dto,
    _iso,
    _json_error,
    _json_value,
    _load_daily_score_input,
    _load_warfare_data,
    _local_date,
    _local_day_bounds,
    _local_timezone,
    _minutes_between,
    _parse_date,
    _parse_optional_date,
    _plan_row_to_dto,
    _report_row_to_dto,
    _require_attention_admin,
    _require_plan,
    _require_user,
    _review_row_to_dto,
    _row_to_dto,
    _safe_rows,
    _safe_scalar,
    _state,
    _utc_now,
)
from ._models import *  # noqa: F401,F403
from ._social import _get_or_create_privacy  # noqa: F401


@router.get("/focus-sessions/active")
def get_active_focus_session(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_FOCUS_COLUMNS} FROM attention_focus_sessions WHERE user_id=%s AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1", (_db_user_id(user),))
            row = cur.fetchone()
        return {"active": _focus_row_to_dto(row) if row else None}
    finally:
        _state["release_db"](conn)


@router.post("/focus-sessions")
def create_focus_session(request: Request, body: FocusSessionIn) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    now = _utc_now()
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM attention_focus_sessions WHERE user_id=%s AND ended_at IS NULL LIMIT 1", (user_id,))
            if cur.fetchone():
                raise _json_error("ACTIVE_FOCUS_SESSION_EXISTS", "当前已有进行中的专注。", 409)
            cur.execute(
                f"""INSERT INTO attention_focus_sessions
                (user_id, started_at, planned_minutes, focus_type, intention, opening_prayer)
                VALUES (%s,%s,%s,%s,%s,%s) RETURNING {_FOCUS_COLUMNS}""",
                (user_id, now, body.planned_minutes, body.focus_type, body.intention, body.opening_prayer),
            )
            row = cur.fetchone()
        conn.commit()
        return {"session": _focus_row_to_dto(row)}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise _json_error("INTERNAL_SERVER_ERROR", "开始专注时遇到问题。", 500)
    finally:
        _state["release_db"](conn)


@router.post("/focus-sessions/{session_id}/end")
@router.patch("/focus-sessions/{session_id}/end")
def end_focus_session(session_id: str, request: Request, body: FocusEndIn) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    ended_at = _utc_now()
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT started_at FROM attention_focus_sessions WHERE id=%s AND user_id=%s", (session_id, user_id))
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这段专注。", 404)
            actual = body.actual_minutes or _minutes_between(row[0], ended_at)
            cur.execute(
                f"""UPDATE attention_focus_sessions
                SET ended_at=%s, actual_minutes=%s, closing_reflection=COALESCE(%s, closing_reflection)
                WHERE id=%s AND user_id=%s RETURNING {_FOCUS_COLUMNS}""",
                (ended_at, actual, body.closing_reflection, session_id, user_id),
            )
            updated = cur.fetchone()
        conn.commit()
        return {"session": _focus_row_to_dto(updated)}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/focus-sessions/{session_id}/interrupt")
@router.patch("/focus-sessions/{session_id}/interrupt")
def interrupt_focus_session(session_id: str, request: Request, body: FocusInterruptIn) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""UPDATE attention_focus_sessions
                SET interrupted=true, interruption_reason=%s
                WHERE id=%s AND user_id=%s RETURNING {_FOCUS_COLUMNS}""",
                (body.interruption_reason, session_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这段专注。", 404)
        conn.commit()
        return {"session": _focus_row_to_dto(row)}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/focus-sessions")
def list_focus_sessions(
    request: Request,
    from_date: Optional[str] = Query(default=None, alias="from"),
    to_date: Optional[str] = Query(default=None, alias="to"),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    user = _require_user(request)
    today = _local_date(request, user)
    end = _parse_optional_date(to_date, "to", today + timedelta(days=1))
    start = _parse_optional_date(from_date, "from", end - timedelta(days=14))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT {_FOCUS_COLUMNS} FROM attention_focus_sessions
                WHERE user_id=%s AND started_at::date BETWEEN %s AND %s
                ORDER BY started_at DESC LIMIT %s""",
                (_db_user_id(user), start, end, limit),
            )
            rows = cur.fetchall()
        return {"sessions": [_focus_row_to_dto(row) for row in rows]}
    finally:
        _state["release_db"](conn)


@router.get("/entries/summary")
def get_entries_summary(request: Request, date_value: Optional[str] = Query(default=None, alias="date")) -> dict:
    user = _require_user(request)
    target = _parse_optional_date(date_value, "date", _local_date(request, user))
    entries = _load_entries_for_date(_db_user_id(user), target)
    return {"date": target.isoformat(), "summary": calculate_daily_summary(entries)}


@router.get("/entries")
def list_entries(request: Request, date_value: Optional[str] = Query(default=None, alias="date")) -> dict:
    user = _require_user(request)
    target = _parse_optional_date(date_value, "date", _local_date(request, user))
    entries = _load_entries_for_date(_db_user_id(user), target)
    return {"date": target.isoformat(), "entries": entries, "summary": calculate_daily_summary(entries)}


def _load_entries_for_date(user_id: str, target: date) -> list[dict]:
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_ENTRY_COLUMNS} FROM attention_entries WHERE user_id=%s AND entry_date=%s ORDER BY created_at DESC", (user_id, target))
            return [_entry_row_to_dto(row) for row in cur.fetchall()]
    finally:
        _state["release_db"](conn)


@router.post("/entries")
def create_entry(request: Request, body: EntryIn) -> dict:
    user = _require_user(request)
    target = _parse_optional_date(body.entry_date, "entryDate", _local_date(request, user))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""INSERT INTO attention_entries
                (user_id, entry_date, category, activity_name, duration_minutes, attention_state, pulls, note)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING {_ENTRY_COLUMNS}""",
                (_db_user_id(user), target, body.category, body.activity_name, body.duration_minutes, body.attention_state, body.pulls, body.note),
            )
            row = cur.fetchone()
        conn.commit()
        return {"entry": _entry_row_to_dto(row)}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.put("/entries/{entry_id}")
def update_entry(entry_id: str, request: Request, body: EntryUpdate) -> dict:
    user_id = _db_user_id(_require_user(request))
    data = body.model_dump(by_alias=False, exclude_unset=True)
    if "entry_date" in data and data["entry_date"]:
        data["entry_date"] = _parse_date(data["entry_date"], "entryDate")
    fields = {
        "entry_date": "entry_date", "category": "category", "activity_name": "activity_name",
        "duration_minutes": "duration_minutes", "attention_state": "attention_state",
        "pulls": "pulls", "note": "note",
    }
    updates = [(fields[k], v) for k, v in data.items() if k in fields]
    if not updates:
        raise _json_error("VALIDATION_ERROR", "没有可更新的字段。", 400)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            assignments = ", ".join([f"{col}=%s" for col, _ in updates])
            cur.execute(
                f"UPDATE attention_entries SET {assignments} WHERE id=%s AND user_id=%s RETURNING {_ENTRY_COLUMNS}",
                [v for _, v in updates] + [entry_id, user_id],
            )
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这条注意力记录。", 404)
        conn.commit()
        return {"entry": _entry_row_to_dto(row)}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.delete("/entries/{entry_id}")
def delete_entry(entry_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM attention_entries WHERE id=%s AND user_id=%s", (entry_id, user_id))
            if cur.rowcount == 0:
                raise _json_error("NOT_FOUND", "没有找到这条注意力记录。", 404)
        conn.commit()
        return {"ok": True}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/review/today")
def get_today_review(request: Request) -> dict:
    user = _require_user(request)
    target = _local_date(request, user)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_REVIEW_COLUMNS} FROM attention_reviews WHERE user_id=%s AND review_date=%s LIMIT 1", (_db_user_id(user), target))
            row = cur.fetchone()
        return {"exists": bool(row), "review": _review_row_to_dto(row) if row else None}
    finally:
        _state["release_db"](conn)


@router.post("/review")
def create_review(request: Request, body: ReviewIn) -> dict:
    user = _require_user(request)
    target = _parse_optional_date(body.review_date, "reviewDate", _local_date(request, user))
    if not any([body.biggest_capture, body.biggest_grace, body.repentance_point, body.tomorrow_boundary, body.prayer]):
        raise _json_error("VALIDATION_ERROR", "至少填写一项复盘内容。", 400)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""INSERT INTO attention_reviews
                (user_id, review_date, biggest_capture, biggest_grace, repentance_point, tomorrow_boundary, prayer)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (user_id, review_date) DO UPDATE SET
                biggest_capture=EXCLUDED.biggest_capture, biggest_grace=EXCLUDED.biggest_grace,
                repentance_point=EXCLUDED.repentance_point, tomorrow_boundary=EXCLUDED.tomorrow_boundary,
                prayer=EXCLUDED.prayer
                RETURNING {_REVIEW_COLUMNS}""",
                (_db_user_id(user), target, body.biggest_capture, body.biggest_grace, body.repentance_point, body.tomorrow_boundary, body.prayer),
            )
            row = cur.fetchone()
        conn.commit()
        return {"review": _review_row_to_dto(row)}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.put("/review/{review_id}")
def update_review(review_id: str, request: Request, body: ReviewIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""UPDATE attention_reviews SET
                biggest_capture=%s, biggest_grace=%s, repentance_point=%s,
                tomorrow_boundary=%s, prayer=%s
                WHERE id=%s AND user_id=%s RETURNING {_REVIEW_COLUMNS}""",
                (body.biggest_capture, body.biggest_grace, body.repentance_point, body.tomorrow_boundary, body.prayer, review_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这份复盘。", 404)
        conn.commit()
        return {"review": _review_row_to_dto(row)}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/review/suggest")
def suggest_review(request: Request) -> dict:
    user = _require_user(request)
    today = _local_date(request, user)
    entries = _load_entries_for_date(_db_user_id(user), today)
    summary = calculate_daily_summary(entries)
    top = summary["topPulls"][0]["label"] if summary["topPulls"] else "今天最明显的牵引"
    return {
        "suggestion": {
            "biggestGrace": "今天你愿意看见注意力的方向，这本身就是恩典。",
            "repentancePoint": f"可以把「{top}」带到神面前，不停在自责，而是选择归回。",
            "tomorrowBoundary": "明天先设一道小而具体的数字边界，并保留一段使命专注。",
            "prayer": "主啊，求你帮助我在诚实中看见，在恩典中归回。",
        }
    }


@router.get("/today/summary")
def get_today_summary(request: Request) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    today = _local_date(request, user)
    day_start, day_end = _local_day_bounds(request, user, today)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_ENTRY_COLUMNS} FROM attention_entries WHERE user_id=%s AND entry_date=%s ORDER BY created_at DESC",
                (user_id, today),
            )
            entries = [_entry_row_to_dto(row) for row in cur.fetchall()]
            cur.execute(
                f"SELECT {_SELECT_COLUMNS} FROM attention_daily_covenants WHERE user_id=%s AND covenant_date=%s LIMIT 1",
                (user_id, today),
            )
            covenant_row = cur.fetchone()
            covenant = _row_to_dto(covenant_row) if covenant_row else None
            cur.execute(
                f"SELECT {_FOCUS_COLUMNS} FROM attention_focus_sessions WHERE user_id=%s AND started_at >= %s AND started_at < %s",
                (user_id, day_start, day_end),
            )
            sessions = [_focus_row_to_dto(r) for r in cur.fetchall()]
            cur.execute(f"SELECT {_REVIEW_COLUMNS} FROM attention_reviews WHERE user_id=%s AND review_date=%s LIMIT 1", (user_id, today))
            review = cur.fetchone()
            cur.execute(f"SELECT {_DIAGNOSIS_COLUMNS} FROM attention_ai_diagnoses WHERE user_id=%s AND diagnosis_date=%s ORDER BY created_at DESC LIMIT 1", (user_id, today))
            diagnosis = cur.fetchone()
            cur.execute(f"SELECT {_PLAN_COLUMNS} FROM attention_warfare_plans WHERE user_id=%s AND status='active' ORDER BY created_at DESC", (user_id,))
            plans = [_plan_row_to_dto(r) for r in cur.fetchall()]
            cur.execute(
                "SELECT COUNT(DISTINCT plan_id) FROM attention_warfare_checkins WHERE user_id=%s AND checkin_date=%s",
                (user_id, today),
            )
            today_warfare_checkins = int(cur.fetchone()[0] or 0)
            week_start, week_end = week_range_from_start(today)
            cur.execute(
                """SELECT score_average, score_label, data_completeness, top_pulls,
                next_week_practice FROM attention_weekly_reports
                WHERE user_id=%s AND week_start=%s AND week_end=%s AND status <> 'hidden'
                LIMIT 1""",
                (user_id, week_start, week_end),
            )
            weekly_row = cur.fetchone()
            cur.execute(
                """SELECT COUNT(*) FROM attention_accountability_relationships
                WHERE (requester_user_id=%s OR partner_user_id=%s) AND status='active'""",
                (user_id, user_id),
            )
            active_partners_count = int(cur.fetchone()[0] or 0)
            cur.execute(
                "SELECT COUNT(*) FROM attention_accountability_relationships WHERE partner_user_id=%s AND status='pending'",
                (user_id,),
            )
            pending_invitations_count = int(cur.fetchone()[0] or 0)
            cur.execute(
                """SELECT COUNT(*) FROM attention_prayer_requests
                WHERE status='open' AND (
                    owner_user_id=%s OR target_user_id=%s OR target_group_id IN (
                        SELECT group_id FROM attention_group_members WHERE user_id=%s AND status='active'
                    )
                )""",
                (user_id, user_id, user_id),
            )
            open_prayer_requests_count = int(cur.fetchone()[0] or 0)
            cur.execute("SELECT COUNT(*) FROM attention_group_members WHERE user_id=%s AND status='active'", (user_id,))
            active_groups_count = int(cur.fetchone()[0] or 0)
            cur.execute(
                """SELECT COUNT(*) FROM attention_challenge_participations p
                JOIN attention_group_challenges c ON c.id=p.challenge_id
                WHERE p.user_id=%s AND p.status='active' AND c.status='active'""",
                (user_id,),
            )
            active_challenges_count = int(cur.fetchone()[0] or 0)
            cur.execute(
                """SELECT COUNT(*) FROM attention_challenge_participations p
                JOIN attention_group_challenges c ON c.id=p.challenge_id
                WHERE p.user_id=%s AND p.status='active' AND c.status='active'
                  AND %s BETWEEN c.start_date AND c.end_date
                  AND NOT EXISTS (
                    SELECT 1 FROM attention_challenge_checkins cc
                    WHERE cc.challenge_id=c.id AND cc.user_id=%s AND cc.checkin_date=%s
                  )""",
                (user_id, today, user_id, today),
            )
            today_challenge_checkins_due = int(cur.fetchone()[0] or 0)
            privacy_settings = _get_or_create_privacy(cur, user_id)
        summary = calculate_daily_summary(entries)
        completed = [s for s in sessions if s.get("endedAt")]
        diagnosis_dto = _diagnosis_row_to_dto(diagnosis) if diagnosis else None
        diagnosis_result = (diagnosis_dto or {}).get("result") or {}
        primary_pattern = diagnosis_result.get("primaryPattern")
        if not primary_pattern and plans:
            pattern = next((item for item in pattern_definitions() if item.get("key") == plans[0].get("patternKey")), None)
            primary_pattern = {
                "patternKey": plans[0].get("patternKey"),
                "label": (pattern or {}).get("label") or plans[0].get("title"),
                "intensity": "active_plan",
            }
        return {
            "date": today.isoformat(),
            "covenant": covenant,
            "ledger": summary,
            "focus": {
                "completedSessions": len(completed),
                "totalActualMinutes": sum(int(s.get("actualMinutes") or 0) for s in completed),
                "interruptedSessions": len([s for s in sessions if s.get("interrupted")]),
                "activeSessionExists": any(not s.get("endedAt") for s in sessions),
            },
            "review": {"exists": bool(review), "review": _review_row_to_dto(review) if review else None},
            "diagnosis": ({
                **diagnosis_dto,
                "todayExists": True,
                "latestTitle": diagnosis_result.get("title"),
                "latestShortSummary": diagnosis_result.get("shortSummary"),
            } if diagnosis_dto else None),
            "warfare": {
                "activePlansCount": len(plans),
                "todayCheckinsCount": today_warfare_checkins,
                "todayCheckinsDue": max(0, len(plans) - today_warfare_checkins),
                "primaryPattern": primary_pattern,
            },
            "weekly": {
                "weekStart": week_start.isoformat(),
                "weekEnd": week_end.isoformat(),
                "reportExists": bool(weekly_row),
                "scoreAverage": weekly_row[0] if weekly_row else None,
                "scoreLabel": weekly_row[1] if weekly_row else "insufficient_data",
                "dataCompleteness": int(weekly_row[2] or 0) if weekly_row else 0,
                "topPulls": (_json_value(weekly_row[3]) or [])[:3] if weekly_row else [],
                "nextWeekPractice": weekly_row[4] if weekly_row else None,
            },
            "accountability": {
                "activePartnersCount": active_partners_count,
                "pendingInvitationsCount": pending_invitations_count,
                "openPrayerRequestsCount": open_prayer_requests_count,
            },
            "groups": {
                "activeGroupsCount": active_groups_count,
                "activeChallengesCount": active_challenges_count,
                "todayChallengeCheckinsDue": today_challenge_checkins_due,
            },
            "privacy": {
                "defaultPartnerVisibility": privacy_settings.get("defaultPartnerVisibility"),
                "defaultGroupVisibility": privacy_settings.get("defaultGroupVisibility"),
                "sensitiveProtectionEnabled": bool(privacy_settings.get("hideSensitiveCategories")),
            },
        }
    finally:
        _state["release_db"](conn)

