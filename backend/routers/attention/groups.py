"""Attention Stewardship / 守心 API — groups / members / invitations / challenges routes.

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
from ._social import *  # noqa: F401,F403
from ._social import (  # noqa: F401
    _CHALLENGE_CHECKIN_COLUMNS,
    _CHALLENGE_COLUMNS,
    _CHALLENGE_COLUMNS_C,
    _GROUP_COLUMNS,
    _GROUP_COLUMNS_G,
    _MEMBER_COLUMNS,
    _PRAYER_COLUMNS,
    _PRIVACY_COLUMNS,
    _REL_COLUMNS,
    _SHARE_COLUMNS,
    _can_access_prayer,
    _challenge_checkin_row_to_dto,
    _challenge_checkins,
    _challenge_participants,
    _challenge_row_to_dict,
    _challenge_row_to_dto,
    _display_user,
    _get_or_create_privacy,
    _group_row_to_dto,
    _has_active_relationship,
    _load_share_source,
    _local_date_from_source,
    _member_row,
    _member_row_to_dto,
    _pair_key,
    _permission_dto,
    _prayer_row_to_dto,
    _privacy_row_to_dto,
    _relationship_row_to_dto,
    _require_group_manager,
    _require_group_member,
    _require_group_owner,
    _require_relationship,
    _resolve_user_id,
    _share_row_to_dto,
)
from .accountability import _challenge_access_row, _member_participant_summary  # noqa: F401


@router.get("/groups")
def list_attention_groups(request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT {_GROUP_COLUMNS_G} FROM attention_groups g
                JOIN attention_group_members m ON m.group_id=g.id
                WHERE m.user_id=%s AND m.status='active' AND g.status='active'
                ORDER BY g.created_at DESC""",
                (user_id,),
            )
            groups = [_group_row_to_dto(cur, row, user_id) for row in cur.fetchall()]
        return {"groups": groups}
    finally:
        _state["release_db"](conn)


@router.post("/groups")
def create_attention_group(request: Request, body: GroupCreateIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    if body.group_type not in GROUP_TYPES:
        raise _json_error("VALIDATION_ERROR", "groupType 不合法。", 400)
    visibility = sanitize_visibility(body.default_member_visibility, allow_selected=False)
    invite_code = uuid.uuid4().hex[:10]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""INSERT INTO attention_groups
                (owner_user_id, name, description, group_type, invite_code,
                 default_member_visibility, guidelines)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                RETURNING {_GROUP_COLUMNS}""",
                (user_id, body.name.strip(), body.description, body.group_type, invite_code, visibility, body.guidelines),
            )
            row = cur.fetchone()
            cur.execute(
                """INSERT INTO attention_group_members (group_id, user_id, role, status, visibility_level)
                VALUES (%s,%s,'owner','active',%s)
                ON CONFLICT (group_id, user_id) DO UPDATE SET role='owner', status='active'""",
                (row[0], user_id, visibility),
            )
            group = _group_row_to_dto(cur, row, user_id)
        conn.commit()
        return {"group": group}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/groups/join")
def join_attention_group(request: Request, body: GroupJoinIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_GROUP_COLUMNS} FROM attention_groups WHERE invite_code=%s AND invite_enabled=true AND status='active'", (body.invite_code.strip(),))
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "邀请链接无效或已关闭。", 404)
            cur.execute(
                """INSERT INTO attention_group_members (group_id, user_id, role, status, visibility_level)
                VALUES (%s,%s,'member','active',%s)
                ON CONFLICT (group_id, user_id) DO UPDATE SET status='active', left_at=NULL, removed_at=NULL""",
                (row[0], user_id, row[7]),
            )
            group = _group_row_to_dto(cur, row, user_id)
        conn.commit()
        return {"group": group}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/groups/{group_id}")
def get_attention_group(group_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_member(cur, group_id, user_id)
            cur.execute(f"SELECT {_GROUP_COLUMNS} FROM attention_groups WHERE id=%s", (group_id,))
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这个守心小组。", 404)
            return {"group": _group_row_to_dto(cur, row, user_id)}
    finally:
        _state["release_db"](conn)


@router.put("/groups/{group_id}")
def update_attention_group(group_id: str, request: Request, body: GroupUpdateIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    data = body.model_dump(by_alias=True, exclude_unset=True)
    if not data:
        raise _json_error("VALIDATION_ERROR", "没有可更新的小组设置。", 400)
    allowed = {
        "name": "name", "description": "description", "groupType": "group_type",
        "inviteEnabled": "invite_enabled", "defaultMemberVisibility": "default_member_visibility",
        "guidelines": "guidelines", "status": "status",
    }
    if "groupType" in data and data["groupType"] not in GROUP_TYPES:
        raise _json_error("VALIDATION_ERROR", "groupType 不合法。", 400)
    if "status" in data and data["status"] not in GROUP_STATUSES:
        raise _json_error("VALIDATION_ERROR", "status 不合法。", 400)
    if "defaultMemberVisibility" in data:
        data["defaultMemberVisibility"] = sanitize_visibility(data["defaultMemberVisibility"], allow_selected=False)
    fields = [(allowed[k], v) for k, v in data.items() if k in allowed]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_manager(cur, group_id, user_id)
            assignments = ", ".join([f"{col}=%s" for col, _ in fields])
            cur.execute(
                f"UPDATE attention_groups SET {assignments} WHERE id=%s RETURNING {_GROUP_COLUMNS}",
                [v for _, v in fields] + [group_id],
            )
            group = _group_row_to_dto(cur, cur.fetchone(), user_id)
        conn.commit()
        return {"group": group}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.delete("/groups/{group_id}")
def archive_attention_group(group_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_owner(cur, group_id, user_id)
            cur.execute(f"UPDATE attention_groups SET status='archived' WHERE id=%s RETURNING {_GROUP_COLUMNS}", (group_id,))
            group = _group_row_to_dto(cur, cur.fetchone(), user_id)
        conn.commit()
        return {"group": group}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/groups/{group_id}/members")
def list_attention_group_members(group_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_member(cur, group_id, user_id)
            cur.execute(f"SELECT {_MEMBER_COLUMNS} FROM attention_group_members WHERE group_id=%s ORDER BY joined_at ASC", (group_id,))
            members = [_member_row_to_dto(cur, r) for r in cur.fetchall()]
        return {"members": members}
    finally:
        _state["release_db"](conn)


@router.put("/groups/{group_id}/members/{member_id}")
def update_attention_group_member(group_id: str, member_id: str, request: Request, body: MemberUpdateIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    data = body.model_dump(exclude_unset=True)
    if "role" in data and data["role"] not in GROUP_ROLES:
        raise _json_error("VALIDATION_ERROR", "role 不合法。", 400)
    if "status" in data and data["status"] not in MEMBER_STATUSES:
        raise _json_error("VALIDATION_ERROR", "status 不合法。", 400)
    fields = [(k, v) for k, v in data.items() if k in {"role", "status"}]
    if not fields:
        raise _json_error("VALIDATION_ERROR", "没有可更新的成员设置。", 400)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_manager(cur, group_id, user_id)
            if any(k == "role" and v == "owner" for k, v in fields):
                _require_group_owner(cur, group_id, user_id)
            assignments = ", ".join([f"{k}=%s" for k, _ in fields])
            cur.execute(
                f"UPDATE attention_group_members SET {assignments} WHERE id=%s AND group_id=%s RETURNING {_MEMBER_COLUMNS}",
                [v for _, v in fields] + [member_id, group_id],
            )
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这个成员。", 404)
            member = _member_row_to_dto(cur, row)
        conn.commit()
        return {"member": member}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.delete("/groups/{group_id}/members/{member_id}")
def remove_attention_group_member(group_id: str, member_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_MEMBER_COLUMNS} FROM attention_group_members WHERE id=%s AND group_id=%s", (member_id, group_id))
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这个成员。", 404)
            if row[2] != user_id:
                _require_group_manager(cur, group_id, user_id)
            if row[3] == "owner":
                cur.execute("SELECT COUNT(*) FROM attention_group_members WHERE group_id=%s AND role='owner' AND status='active'", (group_id,))
                if int(cur.fetchone()[0] or 0) <= 1:
                    raise _json_error("VALIDATION_ERROR", "小组至少需要保留一位 owner。", 400)
            cur.execute(
                f"UPDATE attention_group_members SET status=%s, left_at=now(), removed_at=now() WHERE id=%s RETURNING {_MEMBER_COLUMNS}",
                ("left" if row[2] == user_id else "removed", member_id),
            )
            member = _member_row_to_dto(cur, cur.fetchone())
        conn.commit()
        return {"member": member}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/groups/{group_id}/invitations")
def create_attention_group_invitation(group_id: str, request: Request, body: GroupInviteIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    invite_code = uuid.uuid4().hex[:10] if body.create_invite_code else None
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_manager(cur, group_id, user_id)
            invited_user_id = _resolve_user_id(cur, body.invited_user_id) if body.invited_user_id else None
            if invite_code:
                cur.execute("UPDATE attention_groups SET invite_code=%s, invite_enabled=true WHERE id=%s", (invite_code, group_id))
            cur.execute(
                """INSERT INTO attention_group_invitations
                (group_id, invited_by_user_id, invited_user_id, invited_email, invite_code, message)
                VALUES (%s,%s,%s,%s,%s,%s)
                RETURNING id, group_id, invited_user_id, invited_email, invite_code, status, message, created_at""",
                (group_id, user_id, invited_user_id, body.invited_email, invite_code, body.message),
            )
            row = cur.fetchone()
        conn.commit()
        return {"invitation": {
            "id": str(row[0]), "groupId": str(row[1]), "invitedUserId": row[2],
            "invitedEmail": row[3], "inviteCode": row[4], "status": row[5],
            "message": row[6], "createdAt": _iso(row[7]),
        }}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/challenges/templates")
def list_attention_challenge_templates(request: Request) -> dict:
    _require_user(request)
    requested_lang = request.headers.get("x-lang") or request.query_params.get("lang") or "zh"
    return {"templates": challenge_templates_for_lang(requested_lang)}


@router.get("/challenges/mine")
def list_my_attention_challenges(request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT {_CHALLENGE_COLUMNS_C} FROM attention_group_challenges c
                JOIN attention_challenge_participations p ON p.challenge_id=c.id
                WHERE p.user_id=%s AND p.status='active' AND c.status='active'
                ORDER BY c.start_date DESC""",
                (user_id,),
            )
            challenges = [_challenge_row_to_dto(cur, r, user_id) for r in cur.fetchall()]
        return {"challenges": challenges}
    finally:
        _state["release_db"](conn)


@router.get("/groups/{group_id}/challenges")
def list_attention_group_challenges(group_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_member(cur, group_id, user_id)
            cur.execute(f"SELECT {_CHALLENGE_COLUMNS} FROM attention_group_challenges WHERE group_id=%s AND status<>'archived' ORDER BY start_date DESC", (group_id,))
            challenges = [_challenge_row_to_dto(cur, r, user_id) for r in cur.fetchall()]
        return {"challenges": challenges}
    finally:
        _state["release_db"](conn)


@router.post("/groups/{group_id}/challenges")
def create_attention_group_challenge(group_id: str, request: Request, body: ChallengeCreateIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    if body.challenge_type not in CHALLENGE_TYPES:
        raise _json_error("VALIDATION_ERROR", "challengeType 不合法。", 400)
    if body.privacy_mode not in CHALLENGE_PRIVACY_MODES:
        raise _json_error("VALIDATION_ERROR", "privacyMode 不合法。", 400)
    start = _parse_date(body.start_date, "startDate")
    end = _parse_date(body.end_date, "endDate")
    if end < start:
        raise _json_error("VALIDATION_ERROR", "endDate 不能早于 startDate。", 400)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_manager(cur, group_id, user_id)
            cur.execute(
                f"""INSERT INTO attention_group_challenges
                (group_id, created_by_user_id, template_key, title, description,
                 challenge_type, start_date, end_date, target_days, target_minutes,
                 checkin_prompt, privacy_mode, allow_comments, allow_prayer_requests)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING {_CHALLENGE_COLUMNS}""",
                (group_id, user_id, body.template_key, body.title.strip(), body.description,
                 body.challenge_type, start, end, body.target_days, body.target_minutes,
                 body.checkin_prompt, body.privacy_mode, body.allow_comments, body.allow_prayer_requests),
            )
            row = cur.fetchone()
            cur.execute(
                """INSERT INTO attention_challenge_participations (challenge_id, user_id, status)
                VALUES (%s,%s,'active') ON CONFLICT (challenge_id, user_id) DO UPDATE SET status='active'""",
                (row[0], user_id),
            )
            challenge = _challenge_row_to_dto(cur, row, user_id)
        conn.commit()
        return {"challenge": challenge}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/groups/{group_id}/challenges/{challenge_id}")
def get_attention_group_challenge(group_id: str, challenge_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _challenge_access_row(cur, challenge_id, group_id, user_id)
            return {"challenge": _challenge_row_to_dto(cur, row, user_id)}
    finally:
        _state["release_db"](conn)


@router.put("/groups/{group_id}/challenges/{challenge_id}")
def update_attention_group_challenge(group_id: str, challenge_id: str, request: Request, body: ChallengeUpdateIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    data = body.model_dump(by_alias=True, exclude_unset=True)
    if not data:
        raise _json_error("VALIDATION_ERROR", "没有可更新的挑战设置。", 400)
    allowed = {
        "title": "title", "description": "description", "startDate": "start_date",
        "endDate": "end_date", "targetDays": "target_days", "targetMinutes": "target_minutes",
        "checkinPrompt": "checkin_prompt", "privacyMode": "privacy_mode",
        "allowComments": "allow_comments", "allowPrayerRequests": "allow_prayer_requests",
        "status": "status",
    }
    if "privacyMode" in data and data["privacyMode"] not in CHALLENGE_PRIVACY_MODES:
        raise _json_error("VALIDATION_ERROR", "privacyMode 不合法。", 400)
    if "status" in data and data["status"] not in CHALLENGE_STATUSES:
        raise _json_error("VALIDATION_ERROR", "status 不合法。", 400)
    if "startDate" in data:
        data["startDate"] = _parse_date(data["startDate"], "startDate")
    if "endDate" in data:
        data["endDate"] = _parse_date(data["endDate"], "endDate")
    fields = [(allowed[k], v) for k, v in data.items() if k in allowed]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_manager(cur, group_id, user_id)
            _challenge_access_row(cur, challenge_id, group_id, user_id)
            assignments = ", ".join([f"{col}=%s" for col, _ in fields])
            cur.execute(
                f"UPDATE attention_group_challenges SET {assignments} WHERE id=%s AND group_id=%s RETURNING {_CHALLENGE_COLUMNS}",
                [v for _, v in fields] + [challenge_id, group_id],
            )
            challenge = _challenge_row_to_dto(cur, cur.fetchone(), user_id)
        conn.commit()
        return {"challenge": challenge}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.delete("/groups/{group_id}/challenges/{challenge_id}")
def archive_attention_group_challenge(group_id: str, challenge_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _require_group_manager(cur, group_id, user_id)
            cur.execute(
                f"UPDATE attention_group_challenges SET status='archived' WHERE id=%s AND group_id=%s RETURNING {_CHALLENGE_COLUMNS}",
                (challenge_id, group_id),
            )
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这个挑战。", 404)
            challenge = _challenge_row_to_dto(cur, row, user_id)
        conn.commit()
        return {"challenge": challenge}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/groups/{group_id}/challenges/{challenge_id}/participants")
def list_attention_challenge_participants(group_id: str, challenge_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _challenge_access_row(cur, challenge_id, group_id, user_id)
            challenge = _challenge_row_to_dto(cur, row, user_id)
            if challenge["privacyMode"] == "anonymous_aggregate":
                return {"participants": [], "progress": challenge["progress"]}
            cur.execute("SELECT user_id FROM attention_challenge_participations WHERE challenge_id=%s AND status='active' ORDER BY joined_at ASC", (challenge_id,))
            participants = [_member_participant_summary(cur, challenge_id, r[0]) for r in cur.fetchall()]
        return {"participants": participants, "progress": challenge["progress"]}
    finally:
        _state["release_db"](conn)


@router.post("/groups/{group_id}/challenges/{challenge_id}/checkins")
def save_attention_challenge_checkin(group_id: str, challenge_id: str, request: Request, body: ChallengeCheckinIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    checkin_date = _parse_date(body.checkin_date, "checkinDate") if body.checkin_date else date.today()
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _challenge_access_row(cur, challenge_id, group_id, user_id)
            challenge = _challenge_row_to_dict(row)
            visibility = sanitize_visibility(body.visibility_level)
            if challenge["privacyMode"] in {"status_only", "anonymous_aggregate"}:
                visibility = "status_only"
            prayer_request_id = None
            if body.create_prayer_request:
                if not challenge["allowPrayerRequests"]:
                    raise _json_error("VALIDATION_ERROR", "这个挑战未开启代祷请求。", 400)
                cur.execute(
                    f"""INSERT INTO attention_prayer_requests
                    (owner_user_id, target_group_id, title, body, category, visibility_level, is_sensitive)
                    VALUES (%s,%s,%s,%s,'attention','summary',false)
                    RETURNING {_PRAYER_COLUMNS}""",
                    (
                        user_id,
                        group_id,
                        body.prayer_request_title or f"{challenge['title']} 的代祷请求",
                        body.prayer_request_body or "请为我在这个守心操练中继续归回祷告。",
                    ),
                )
                prayer_request_id = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO attention_challenge_participations (challenge_id, user_id, status)
                VALUES (%s,%s,'active')
                ON CONFLICT (challenge_id, user_id) DO UPDATE SET status='active', left_at=NULL""",
                (challenge_id, user_id),
            )
            cur.execute(
                f"""INSERT INTO attention_challenge_checkins
                (challenge_id, user_id, checkin_date, completed, value_minutes, value_count,
                 reflection, prayer_request_id, visibility_level)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (challenge_id, user_id, checkin_date) DO UPDATE SET
                    completed=EXCLUDED.completed,
                    value_minutes=EXCLUDED.value_minutes,
                    value_count=EXCLUDED.value_count,
                    reflection=EXCLUDED.reflection,
                    prayer_request_id=COALESCE(EXCLUDED.prayer_request_id, attention_challenge_checkins.prayer_request_id),
                    visibility_level=EXCLUDED.visibility_level
                RETURNING {_CHALLENGE_CHECKIN_COLUMNS}""",
                (challenge_id, user_id, checkin_date, body.completed, body.value_minutes, body.value_count,
                 body.reflection, prayer_request_id, visibility),
            )
            checkin = _challenge_checkin_row_to_dto(cur.fetchone(), include_reflection=True)
        conn.commit()
        return {"checkin": checkin}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)
