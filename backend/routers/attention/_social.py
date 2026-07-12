"""Attention Stewardship / 守心 API — shared helpers for accountability & groups (privacy/partners/shares/prayers/challenges DTOs).

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


# ---------------------------------------------------------------------------
# Batch 6: Accountability Partners / Groups / Privacy
# ---------------------------------------------------------------------------

_PRIVACY_COLUMNS = """
    id, user_id, default_partner_visibility, default_group_visibility,
    default_challenge_visibility, share_scores_with_partners,
    share_scores_with_groups, share_weekly_report_summary,
    share_warfare_plan_progress, share_prayer_requests,
    hide_sensitive_categories, allow_partner_reminders,
    allow_group_challenge_reminders, require_preview_before_sharing,
    created_at, updated_at
"""

_REL_COLUMNS = """
    id, requester_user_id, partner_user_id, status, direction_label,
    requester_message, requester_permissions, partner_permissions,
    accepted_at, declined_at, paused_at, ended_at, created_at, updated_at
"""

_GROUP_COLUMNS = """
    id, owner_user_id, name, description, group_type, invite_code,
    invite_enabled, default_member_visibility, guidelines, status,
    created_at, updated_at
"""

_GROUP_COLUMNS_G = """
    g.id, g.owner_user_id, g.name, g.description, g.group_type, g.invite_code,
    g.invite_enabled, g.default_member_visibility, g.guidelines, g.status,
    g.created_at, g.updated_at
"""

_MEMBER_COLUMNS = """
    id, group_id, user_id, role, status, visibility_level, permissions,
    joined_at, left_at, removed_at, created_at, updated_at
"""

_CHALLENGE_COLUMNS = """
    id, group_id, created_by_user_id, template_key, title, description,
    challenge_type, start_date, end_date, target_days, target_minutes,
    checkin_prompt, privacy_mode, allow_comments, allow_prayer_requests,
    status, created_at, updated_at
"""

_CHALLENGE_COLUMNS_C = """
    c.id, c.group_id, c.created_by_user_id, c.template_key, c.title, c.description,
    c.challenge_type, c.start_date, c.end_date, c.target_days, c.target_minutes,
    c.checkin_prompt, c.privacy_mode, c.allow_comments, c.allow_prayer_requests,
    c.status, c.created_at, c.updated_at
"""

_CHALLENGE_CHECKIN_COLUMNS = """
    id, challenge_id, user_id, checkin_date, completed, value_minutes,
    value_count, reflection, prayer_request_id, visibility_level,
    created_at, updated_at
"""

_SHARE_COLUMNS = """
    id, owner_user_id, scope, target_user_id, target_group_id, source_type,
    source_id, title, summary, payload, visibility_level, sensitive_redactions,
    revoked_at, created_at, updated_at
"""

_PRAYER_COLUMNS = """
    id, owner_user_id, target_user_id, target_group_id, title, body, category,
    visibility_level, is_sensitive, status, answered_note, created_at,
    updated_at, closed_at
"""


def _pair_key(a: str, b: str) -> str:
    left, right = sorted([a.strip().lower(), b.strip().lower()])
    return f"{left}::{right}"


def _display_user(cur, user_id: Optional[str]) -> dict:
    if not user_id:
        return {"id": None, "displayName": None, "avatarUrl": None}
    cur.execute("SELECT email, nickname, avatar FROM users WHERE LOWER(email)=LOWER(%s) LIMIT 1", (user_id,))
    row = cur.fetchone()
    if not row:
        return {"id": user_id, "displayName": user_id.split("@")[0], "avatarUrl": None}
    return {"id": row[0], "displayName": row[1] or row[0].split("@")[0], "avatarUrl": row[2]}


def _resolve_user_id(cur, value: str) -> str:
    ident = (value or "").strip().lower()
    if not ident:
        raise _json_error("VALIDATION_ERROR", "请选择守望对象。", 400)
    cur.execute("SELECT email FROM users WHERE LOWER(email)=LOWER(%s) OR id::text=%s LIMIT 1", (ident, ident))
    row = cur.fetchone()
    if not row:
        raise _json_error("NOT_FOUND", "没有找到这位用户。", 404)
    return row[0]


def _privacy_row_to_dto(row) -> dict:
    return {
        "userId": row[1],
        "defaultPartnerVisibility": row[2],
        "defaultGroupVisibility": row[3],
        "defaultChallengeVisibility": row[4],
        "shareScoresWithPartners": bool(row[5]),
        "shareScoresWithGroups": bool(row[6]),
        "shareWeeklyReportSummary": bool(row[7]),
        "shareWarfarePlanProgress": bool(row[8]),
        "sharePrayerRequests": bool(row[9]),
        "hideSensitiveCategories": list(row[10] or []),
        "allowPartnerReminders": bool(row[11]),
        "allowGroupChallengeReminders": bool(row[12]),
        "requirePreviewBeforeSharing": bool(row[13]),
        "createdAt": _iso(row[14]),
        "updatedAt": _iso(row[15]),
    }


def _get_or_create_privacy(cur, user_id: str) -> dict:
    cur.execute(f"SELECT {_PRIVACY_COLUMNS} FROM attention_privacy_settings WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    if not row:
        cur.execute(
            f"""INSERT INTO attention_privacy_settings
            (user_id, default_partner_visibility, default_group_visibility,
             default_challenge_visibility, share_scores_with_partners,
             share_scores_with_groups, share_weekly_report_summary,
             share_warfare_plan_progress, share_prayer_requests,
             hide_sensitive_categories, allow_partner_reminders,
             allow_group_challenge_reminders, require_preview_before_sharing)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING {_PRIVACY_COLUMNS}""",
            (
                user_id,
                DEFAULT_PRIVACY["defaultPartnerVisibility"],
                DEFAULT_PRIVACY["defaultGroupVisibility"],
                DEFAULT_PRIVACY["defaultChallengeVisibility"],
                DEFAULT_PRIVACY["shareScoresWithPartners"],
                DEFAULT_PRIVACY["shareScoresWithGroups"],
                DEFAULT_PRIVACY["shareWeeklyReportSummary"],
                DEFAULT_PRIVACY["shareWarfarePlanProgress"],
                DEFAULT_PRIVACY["sharePrayerRequests"],
                DEFAULT_PRIVACY["hideSensitiveCategories"],
                DEFAULT_PRIVACY["allowPartnerReminders"],
                DEFAULT_PRIVACY["allowGroupChallengeReminders"],
                DEFAULT_PRIVACY["requirePreviewBeforeSharing"],
            ),
        )
        row = cur.fetchone()
    return _privacy_row_to_dto(row)


def _permission_dto(perms: dict, relationship_id: str) -> dict:
    merged = default_partner_permissions(perms or {})
    return {"relationshipId": relationship_id, **merged, "updatedAt": _iso(_utc_now())}


def _relationship_row_to_dto(cur, row, current_user_id: str) -> dict:
    rid = str(row[0])
    requester = row[1]
    partner = row[2]
    current_role = "requester" if requester == current_user_id else "partner"
    return {
        "id": rid,
        "requesterUser": _display_user(cur, requester),
        "partnerUser": _display_user(cur, partner),
        "status": row[3],
        "currentUserRole": current_role,
        "directionLabel": row[4],
        "requesterMessage": row[5],
        "permissionsForCurrentUserSharing": _permission_dto(_json_value(row[6] if current_role == "requester" else row[7]) or {}, rid),
        "permissionsForPartnerSharing": _permission_dto(_json_value(row[7] if current_role == "requester" else row[6]) or {}, rid),
        "acceptedAt": _iso(row[8]),
        "declinedAt": _iso(row[9]),
        "pausedAt": _iso(row[10]),
        "endedAt": _iso(row[11]),
        "createdAt": _iso(row[12]),
        "updatedAt": _iso(row[13]),
    }


def _require_relationship(cur, user_id: str, relationship_id: str):
    cur.execute(
        f"SELECT {_REL_COLUMNS} FROM attention_accountability_relationships WHERE id=%s AND (requester_user_id=%s OR partner_user_id=%s)",
        (relationship_id, user_id, user_id),
    )
    row = cur.fetchone()
    if not row:
        raise _json_error("NOT_FOUND", "没有找到这段守望关系。", 404)
    return row


def _has_active_relationship(cur, user_a: str, user_b: str) -> bool:
    cur.execute(
        """SELECT id FROM attention_accountability_relationships
        WHERE pair_key=%s AND status='active' LIMIT 1""",
        (_pair_key(user_a, user_b),),
    )
    return bool(cur.fetchone())


def _member_row(cur, group_id: str, user_id: str):
    cur.execute(f"SELECT {_MEMBER_COLUMNS} FROM attention_group_members WHERE group_id=%s AND user_id=%s AND status='active'", (group_id, user_id))
    return cur.fetchone()


def _require_group_member(cur, group_id: str, user_id: str):
    row = _member_row(cur, group_id, user_id)
    if not row:
        raise _json_error("NOT_FOUND", "没有找到这个守心小组，或你尚未加入。", 404)
    return row


def _require_group_manager(cur, group_id: str, user_id: str):
    member = _require_group_member(cur, group_id, user_id)
    if member[3] not in {"owner", "leader"}:
        raise _json_error("FORBIDDEN", "只有小组 owner/leader 可以操作。", 403)
    return member


def _require_group_owner(cur, group_id: str, user_id: str):
    member = _require_group_member(cur, group_id, user_id)
    if member[3] != "owner":
        raise _json_error("FORBIDDEN", "只有小组 owner 可以操作。", 403)
    return member


def _group_row_to_dto(cur, row, current_user_id: str) -> dict:
    gid = str(row[0])
    cur.execute("SELECT role, status FROM attention_group_members WHERE group_id=%s AND user_id=%s LIMIT 1", (gid, current_user_id))
    mine = cur.fetchone()
    cur.execute("SELECT COUNT(*) FROM attention_group_members WHERE group_id=%s AND status='active'", (gid,))
    members_count = int(cur.fetchone()[0] or 0)
    cur.execute("SELECT COUNT(*) FROM attention_group_challenges WHERE group_id=%s AND status='active'", (gid,))
    active_challenges = int(cur.fetchone()[0] or 0)
    return {
        "id": gid,
        "ownerUserId": row[1],
        "name": row[2],
        "description": row[3],
        "groupType": row[4],
        "inviteCode": row[5],
        "inviteEnabled": bool(row[6]),
        "defaultMemberVisibility": row[7],
        "guidelines": row[8],
        "status": row[9],
        "currentUserRole": mine[0] if mine else None,
        "currentUserMembershipStatus": mine[1] if mine else None,
        "membersCount": members_count,
        "activeChallengesCount": active_challenges,
        "createdAt": _iso(row[10]),
        "updatedAt": _iso(row[11]),
    }


def _member_row_to_dto(cur, row) -> dict:
    return {
        "id": str(row[0]),
        "groupId": str(row[1]),
        "user": _display_user(cur, row[2]),
        "role": row[3],
        "status": row[4],
        "visibilityLevel": row[5],
        "joinedAt": _iso(row[7]),
        "createdAt": _iso(row[10]),
        "updatedAt": _iso(row[11]),
    }


def _challenge_row_to_dict(row) -> dict:
    return {
        "id": str(row[0]),
        "groupId": str(row[1]),
        "createdByUserId": row[2],
        "templateKey": row[3],
        "title": row[4],
        "description": row[5],
        "challengeType": row[6],
        "startDate": _iso(row[7]),
        "endDate": _iso(row[8]),
        "targetDays": row[9],
        "targetMinutes": row[10],
        "checkinPrompt": row[11],
        "privacyMode": row[12],
        "allowComments": bool(row[13]),
        "allowPrayerRequests": bool(row[14]),
        "status": row[15],
        "createdAt": _iso(row[16]),
        "updatedAt": _iso(row[17]),
    }


def _challenge_participants(cur, challenge_id: str) -> list[dict]:
    cur.execute("SELECT user_id, status, joined_at FROM attention_challenge_participations WHERE challenge_id=%s ORDER BY joined_at ASC", (challenge_id,))
    return [{"userId": r[0], "status": r[1], "joinedAt": _iso(r[2])} for r in cur.fetchall()]


def _challenge_checkins(cur, challenge_id: str) -> list[dict]:
    cur.execute(f"SELECT {_CHALLENGE_CHECKIN_COLUMNS} FROM attention_challenge_checkins WHERE challenge_id=%s ORDER BY checkin_date DESC", (challenge_id,))
    return [_challenge_checkin_row_to_dto(r, include_reflection=True) for r in cur.fetchall()]


def _challenge_row_to_dto(cur, row, current_user_id: str) -> dict:
    data = _challenge_row_to_dict(row)
    participants = _challenge_participants(cur, data["id"])
    checkins = _challenge_checkins(cur, data["id"])
    cur.execute("SELECT status, joined_at FROM attention_challenge_participations WHERE challenge_id=%s AND user_id=%s", (data["id"], current_user_id))
    mine = cur.fetchone()
    data["currentUserParticipation"] = {"status": mine[0], "joinedAt": _iso(mine[1])} if mine else None
    data["progress"] = challenge_progress(challenge=data, participants=participants, checkins=checkins, current_user_id=current_user_id, today=date.today())
    return data


def _challenge_checkin_row_to_dto(row, include_reflection: bool = False) -> dict:
    return {
        "id": str(row[0]),
        "challengeId": str(row[1]),
        "userId": row[2],
        "checkinDate": _iso(row[3]),
        "completed": bool(row[4]),
        "valueMinutes": row[5],
        "valueCount": row[6],
        "reflection": row[7] if include_reflection else None,
        "prayerRequestId": str(row[8]) if row[8] else None,
        "visibilityLevel": row[9],
        "createdAt": _iso(row[10]),
        "updatedAt": _iso(row[11]),
    }


def _share_row_to_dto(cur, row) -> dict:
    return {
        "id": str(row[0]),
        "ownerUser": _display_user(cur, row[1]),
        "scope": row[2],
        "targetUserId": row[3],
        "targetGroupId": str(row[4]) if row[4] else None,
        "sourceType": row[5],
        "sourceId": row[6],
        "title": row[7],
        "summary": row[8],
        "payload": _json_value(row[9]) or {},
        "visibilityLevel": row[10],
        "sensitiveRedactions": list(row[11] or []),
        "revokedAt": _iso(row[12]),
        "createdAt": _iso(row[13]),
        "updatedAt": _iso(row[14]),
    }


def _prayer_row_to_dto(cur, row, current_user_id: str) -> dict:
    prayer_id = str(row[0])
    cur.execute("SELECT COUNT(*) FROM attention_prayer_marks WHERE prayer_request_id=%s", (prayer_id,))
    count = int(cur.fetchone()[0] or 0)
    cur.execute("SELECT id FROM attention_prayer_marks WHERE prayer_request_id=%s AND user_id=%s", (prayer_id, current_user_id))
    prayed = bool(cur.fetchone())
    is_owner = row[1] == current_user_id
    is_sensitive = bool(row[8])
    may_see_body = is_owner or (row[7] == "selected_details" and not is_sensitive)
    return {
        "id": prayer_id,
        "ownerUser": _display_user(cur, row[1]),
        "targetUserId": row[2],
        "targetGroupId": str(row[3]) if row[3] else None,
        "title": row[4] if is_owner or not is_sensitive else "一项敏感代祷需要",
        "body": row[5] if may_see_body else None,
        "category": row[6],
        "visibilityLevel": row[7],
        "isSensitive": bool(row[8]),
        "status": row[9],
        "answeredNote": row[10] if is_owner else None,
        "prayedCount": count,
        "hasCurrentUserPrayed": prayed,
        "createdAt": _iso(row[11]),
        "updatedAt": _iso(row[12]),
        "closedAt": _iso(row[13]),
    }


def _can_access_prayer(cur, user_id: str, row) -> bool:
    if row[1] == user_id or row[2] == user_id:
        return True
    if row[3]:
        return bool(_member_row(cur, str(row[3]), user_id))
    return False


def _load_share_source(cur, user_id: str, body: ShareCreateIn) -> dict:
    if body.source_type == "weekly_report" and body.source_id:
        cur.execute(f"SELECT {_REPORT_COLUMNS} FROM attention_weekly_reports WHERE id=%s AND user_id=%s AND status <> 'hidden'", (body.source_id, user_id))
        row = cur.fetchone()
        if not row:
            raise _json_error("NOT_FOUND", "没有找到这份周报。", 404)
        return _report_row_to_dto(row)
    if body.source_type == "warfare_plan" and body.source_id:
        cur.execute(f"SELECT {_PLAN_COLUMNS} FROM attention_warfare_plans WHERE id=%s AND user_id=%s", (body.source_id, user_id))
        row = cur.fetchone()
        if not row:
            raise _json_error("NOT_FOUND", "没有找到这条守心计划。", 404)
        return _plan_row_to_dto(row)
    if body.source_type == "daily_summary":
        target = _local_date_from_source(body.source_id)
        score_input = _load_daily_score_input(cur, user_id, target)
        return {
            "date": target.isoformat(),
            "covenant": score_input.get("covenant"),
            "focus": {"totalActualMinutes": score_input.get("focusMinutes", 0)},
            "review": {"exists": bool(score_input.get("review"))},
        }
    if body.source_type == "challenge_progress" and body.source_id:
        cur.execute(f"SELECT {_CHALLENGE_COLUMNS} FROM attention_group_challenges WHERE id=%s", (body.source_id,))
        row = cur.fetchone()
        if not row:
            raise _json_error("NOT_FOUND", "没有找到这个挑战。", 404)
        return _challenge_row_to_dto(cur, row, user_id)
    if body.source_type == "prayer_request" and body.source_id:
        cur.execute(f"SELECT {_PRAYER_COLUMNS} FROM attention_prayer_requests WHERE id=%s AND owner_user_id=%s", (body.source_id, user_id))
        row = cur.fetchone()
        if not row:
            raise _json_error("NOT_FOUND", "没有找到这个代祷请求。", 404)
        return _prayer_row_to_dto(cur, row, user_id)
    return {"customMessage": body.custom_message}


def _local_date_from_source(value: Optional[str]) -> date:
    if not value:
        return date.today()
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except Exception:
        return date.today()

