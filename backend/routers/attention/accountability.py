"""Attention Stewardship / 守心 API — privacy / partners / shares / prayer request routes.

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


@router.get("/privacy")
def get_attention_privacy(request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            settings = _get_or_create_privacy(cur, user_id)
        conn.commit()
        return {"settings": settings}
    finally:
        _state["release_db"](conn)


@router.put("/privacy")
def update_attention_privacy(request: Request, body: PrivacySettingsIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    data = sanitize_privacy_update(body.model_dump(by_alias=True, exclude_unset=True))
    if not data:
        raise _json_error("VALIDATION_ERROR", "没有可更新的隐私设置。", 400)
    field_map = {
        "defaultPartnerVisibility": "default_partner_visibility",
        "defaultGroupVisibility": "default_group_visibility",
        "defaultChallengeVisibility": "default_challenge_visibility",
        "shareScoresWithPartners": "share_scores_with_partners",
        "shareScoresWithGroups": "share_scores_with_groups",
        "shareWeeklyReportSummary": "share_weekly_report_summary",
        "shareWarfarePlanProgress": "share_warfare_plan_progress",
        "sharePrayerRequests": "share_prayer_requests",
        "hideSensitiveCategories": "hide_sensitive_categories",
        "allowPartnerReminders": "allow_partner_reminders",
        "allowGroupChallengeReminders": "allow_group_challenge_reminders",
        "requirePreviewBeforeSharing": "require_preview_before_sharing",
    }
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _get_or_create_privacy(cur, user_id)
            assignments = ", ".join([f"{field_map[k]}=%s" for k in data])
            cur.execute(
                f"UPDATE attention_privacy_settings SET {assignments} WHERE user_id=%s RETURNING {_PRIVACY_COLUMNS}",
                list(data.values()) + [user_id],
            )
            settings = _privacy_row_to_dto(cur.fetchone())
        conn.commit()
        return {"settings": settings}
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/accountability/partners")
def list_attention_partners(request: Request, status: str = Query(default="active")) -> dict:
    user_id = _db_user_id(_require_user(request))
    if status not in PARTNER_STATUSES | {"all"}:
        raise _json_error("VALIDATION_ERROR", "status 不合法。", 400)
    clause = "(requester_user_id=%s OR partner_user_id=%s)" if status == "all" else "(requester_user_id=%s OR partner_user_id=%s) AND status=%s"
    params = (user_id, user_id) if status == "all" else (user_id, user_id, status)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_REL_COLUMNS} FROM attention_accountability_relationships WHERE {clause} ORDER BY created_at DESC", params)
            rows = cur.fetchall()
            return {"relationships": [_relationship_row_to_dto(cur, r, user_id) for r in rows]}
    finally:
        _state["release_db"](conn)


@router.post("/accountability/partners/invite")
def invite_attention_partner(request: Request, body: PartnerInviteIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            partner_id = _resolve_user_id(cur, body.partner_user_id)
            if partner_id == user_id:
                raise _json_error("VALIDATION_ERROR", "不能邀请自己成为守望伙伴。", 400)
            perms = default_partner_permissions(body.permissions)
            cur.execute(
                f"""INSERT INTO attention_accountability_relationships
                (requester_user_id, partner_user_id, pair_key, requester_message,
                 requester_permissions, partner_permissions)
                VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb)
                RETURNING {_REL_COLUMNS}""",
                (user_id, partner_id, _pair_key(user_id, partner_id), body.message, _Json(perms), _Json(default_partner_permissions())),
            )
            row = cur.fetchone()
            relationship = _relationship_row_to_dto(cur, row, user_id)
        conn.commit()
        return {"relationship": relationship}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        if "uniq_attention_accountability_pair_active" in str(exc):
            raise _json_error("RELATIONSHIP_EXISTS", "你们已经有进行中的守望关系或邀请。", 409)
        raise
    finally:
        _state["release_db"](conn)


@router.get("/accountability/partners/invitations")
def list_attention_partner_invitations(request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_REL_COLUMNS} FROM attention_accountability_relationships WHERE status='pending' AND partner_user_id=%s ORDER BY created_at DESC", (user_id,))
            received = [_relationship_row_to_dto(cur, r, user_id) for r in cur.fetchall()]
            cur.execute(f"SELECT {_REL_COLUMNS} FROM attention_accountability_relationships WHERE status='pending' AND requester_user_id=%s ORDER BY created_at DESC", (user_id,))
            sent = [_relationship_row_to_dto(cur, r, user_id) for r in cur.fetchall()]
        return {"received": received, "sent": sent}
    finally:
        _state["release_db"](conn)


@router.put("/accountability/partners/{relationship_id}")
def update_attention_partner_relationship(relationship_id: str, request: Request, body: PartnerActionIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    action = body.action
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _require_relationship(cur, user_id, relationship_id)
            requester, partner, status = row[1], row[2], row[3]
            if action in {"accept", "decline"} and user_id != partner:
                raise _json_error("FORBIDDEN", "只有被邀请方可以接受或拒绝。", 403)
            updates = {
                "accept": ("active", "accepted_at=now(), declined_at=NULL, paused_at=NULL, ended_at=NULL"),
                "decline": ("declined", "declined_at=now()"),
                "pause": ("paused", "paused_at=now()"),
                "resume": ("active", "paused_at=NULL"),
                "end": ("ended", "ended_at=now()"),
            }
            if action not in updates:
                raise _json_error("VALIDATION_ERROR", "action 不合法。", 400)
            if action == "accept" and status != "pending":
                raise _json_error("VALIDATION_ERROR", "只能接受待处理邀请。", 400)
            next_status, extra = updates[action]
            cur.execute(
                f"UPDATE attention_accountability_relationships SET status=%s, {extra} WHERE id=%s RETURNING {_REL_COLUMNS}",
                (next_status, relationship_id),
            )
            updated = cur.fetchone()
            relationship = _relationship_row_to_dto(cur, updated, user_id)
        conn.commit()
        return {"relationship": relationship}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/accountability/partners/{relationship_id}/permissions")
def get_attention_partner_permissions(relationship_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _require_relationship(cur, user_id, relationship_id)
            perms = _json_value(row[6] if row[1] == user_id else row[7]) or {}
        return {"permissions": _permission_dto(perms, relationship_id)}
    finally:
        _state["release_db"](conn)


@router.put("/accountability/partners/{relationship_id}/permissions")
def update_attention_partner_permissions(relationship_id: str, request: Request, body: PartnerPermissionsIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    data = body.model_dump(by_alias=True, exclude_unset=True)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _require_relationship(cur, user_id, relationship_id)
            column = "requester_permissions" if row[1] == user_id else "partner_permissions"
            current = _json_value(row[6] if row[1] == user_id else row[7]) or {}
            next_perms = default_partner_permissions({**current, **data})
            cur.execute(
                f"UPDATE attention_accountability_relationships SET {column}=%s::jsonb WHERE id=%s RETURNING {_REL_COLUMNS}",
                (_Json(next_perms), relationship_id),
            )
            updated = cur.fetchone()
            relationship = _relationship_row_to_dto(cur, updated, user_id)
        conn.commit()
        return {"permissions": _permission_dto(next_perms, relationship_id), "relationship": relationship}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


def _share_targets_for_user(cur, user_id: str) -> tuple[list[str], list[str]]:
    cur.execute(
        "SELECT group_id FROM attention_group_members WHERE user_id=%s AND status='active'",
        (user_id,),
    )
    groups = [str(r[0]) for r in cur.fetchall()]
    cur.execute(
        """SELECT requester_user_id, partner_user_id FROM attention_accountability_relationships
        WHERE (requester_user_id=%s OR partner_user_id=%s) AND status='active'""",
        (user_id, user_id),
    )
    partners = []
    for requester, partner in cur.fetchall():
        partners.append(partner if requester == user_id else requester)
    return partners, groups


def _require_share_access(cur, user_id: str, share_id: str):
    cur.execute(f"SELECT {_SHARE_COLUMNS} FROM attention_share_snapshots WHERE id=%s", (share_id,))
    row = cur.fetchone()
    if not row:
        raise _json_error("NOT_FOUND", "没有找到这份分享。", 404)
    if row[1] == user_id:
        return row
    if row[12]:
        raise _json_error("NOT_FOUND", "没有找到这份分享。", 404)
    if row[3] == user_id:
        if row[2] == "partner" and not _has_active_relationship(cur, row[1], user_id):
            raise _json_error("NOT_FOUND", "没有找到这份分享。", 404)
        return row
    if row[4] and _member_row(cur, str(row[4]), user_id):
        return row
    raise _json_error("FORBIDDEN", "你没有权限查看这份分享。", 403)


def _challenge_access_row(cur, challenge_id: str, group_id: Optional[str], user_id: str):
    if group_id:
        _require_group_member(cur, group_id, user_id)
        cur.execute(f"SELECT {_CHALLENGE_COLUMNS} FROM attention_group_challenges WHERE id=%s AND group_id=%s", (challenge_id, group_id))
    else:
        cur.execute(f"SELECT {_CHALLENGE_COLUMNS} FROM attention_group_challenges WHERE id=%s", (challenge_id,))
    row = cur.fetchone()
    if not row:
        raise _json_error("NOT_FOUND", "没有找到这个挑战。", 404)
    _require_group_member(cur, str(row[1]), user_id)
    return row


def _member_participant_summary(cur, challenge_id: str, user_id: str) -> dict:
    cur.execute(
        f"SELECT {_CHALLENGE_CHECKIN_COLUMNS} FROM attention_challenge_checkins WHERE challenge_id=%s AND user_id=%s ORDER BY checkin_date DESC",
        (challenge_id, user_id),
    )
    checkins = [_challenge_checkin_row_to_dto(r, include_reflection=False) for r in cur.fetchall()]
    completed = [c for c in checkins if c.get("completed")]
    return {
        "user": _display_user(cur, user_id),
        "checkinsCount": len(checkins),
        "completedDays": len(completed),
        "lastCheckinDate": checkins[0]["checkinDate"] if checkins else None,
        "encouragementText": "正在同行操练。" if checkins else "还没有记录，适合温柔提醒。",
    }


@router.get("/accountability/shares")
def list_attention_shares(request: Request, box: str = Query(default="received")) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if box == "sent":
                cur.execute(f"SELECT {_SHARE_COLUMNS} FROM attention_share_snapshots WHERE owner_user_id=%s ORDER BY created_at DESC LIMIT 100", (user_id,))
            else:
                partners, groups = _share_targets_for_user(cur, user_id)
                partner_ids = tuple(partners) or ("",)
                group_ids = tuple(groups) or ("",)
                cur.execute(
                    f"""SELECT {_SHARE_COLUMNS} FROM attention_share_snapshots
                    WHERE revoked_at IS NULL AND (
                      (target_user_id=%s AND (scope<>'partner' OR owner_user_id IN %s))
                      OR target_group_id::text IN %s
                    )
                    ORDER BY created_at DESC LIMIT 100""",
                    (user_id, partner_ids, group_ids),
                )
            shares = [_share_row_to_dto(cur, row) for row in cur.fetchall()]
        return {"shares": shares}
    finally:
        _state["release_db"](conn)


def _prepare_attention_share(cur, user_id: str, body: ShareCreateIn) -> dict:
    if body.scope not in SHARE_SCOPES:
        raise _json_error("VALIDATION_ERROR", "scope 不合法。", 400)
    if body.source_type not in SHARE_SOURCE_TYPES:
        raise _json_error("VALIDATION_ERROR", "sourceType 不合法。", 400)
    visibility = sanitize_visibility(body.visibility_level)
    settings = _get_or_create_privacy(cur, user_id)
    target_user_id = _resolve_user_id(cur, body.target_user_id) if body.target_user_id else None
    target_group_id = body.target_group_id
    if body.scope == "partner":
        if not target_user_id or not _has_active_relationship(cur, user_id, target_user_id):
            raise _json_error("FORBIDDEN", "只能分享给 active 守望伙伴。", 403)
    elif body.scope in {"group", "challenge"}:
        if not target_group_id:
            raise _json_error("VALIDATION_ERROR", "请选择守心小组。", 400)
        _require_group_member(cur, target_group_id, user_id)
    source = _load_share_source(cur, user_id, body)
    payload, redactions = build_share_payload(
        body.source_type,
        source,
        {
            "includeScore": body.include_score,
            "includeTopPulls": body.include_top_pulls,
            "includeNextPractice": body.include_next_practice,
            "customMessage": body.custom_message,
        },
        settings,
    )
    title = payload.get("title") or source.get("title") or source.get("summary") or "守心摘要分享"
    summary = payload.get("summary") or payload.get("encouragementText") or body.custom_message or "这份分享只包含用户选择公开的守心摘要。"
    return {
        "targetUserId": target_user_id,
        "targetGroupId": target_group_id,
        "visibilityLevel": visibility,
        "payload": payload,
        "redactions": redactions,
        "title": str(title)[:200],
        "summary": str(summary)[:1000],
    }


@router.post("/accountability/shares/preview")
def preview_attention_share(request: Request, body: ShareCreateIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            prepared = _prepare_attention_share(cur, user_id, body)
        conn.rollback()
        return {
            "preview": {
                "title": prepared["title"],
                "summary": prepared["summary"],
                "payload": prepared["payload"],
                "visibilityLevel": prepared["visibilityLevel"],
                "sensitiveRedactions": prepared["redactions"],
                "scoreIncluded": "scoreAverage" in prepared["payload"],
            }
        }
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/accountability/shares")
def create_attention_share(request: Request, body: ShareCreateIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            prepared = _prepare_attention_share(cur, user_id, body)
            cur.execute(
                f"""INSERT INTO attention_share_snapshots
                (owner_user_id, scope, target_user_id, target_group_id, source_type,
                 source_id, title, summary, payload, visibility_level, sensitive_redactions)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                RETURNING {_SHARE_COLUMNS}""",
                (user_id, body.scope, prepared["targetUserId"], prepared["targetGroupId"], body.source_type,
                 body.source_id, prepared["title"], prepared["summary"], _Json(prepared["payload"]),
                 prepared["visibilityLevel"], prepared["redactions"]),
            )
            share = _share_row_to_dto(cur, cur.fetchone())
        conn.commit()
        return {"share": share}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/accountability/shares/{share_id}")
def get_attention_share(share_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _require_share_access(cur, user_id, share_id)
            return {"share": _share_row_to_dto(cur, row)}
    finally:
        _state["release_db"](conn)


@router.delete("/accountability/shares/{share_id}")
def revoke_attention_share(share_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE attention_share_snapshots SET revoked_at=now() WHERE id=%s AND owner_user_id=%s RETURNING {_SHARE_COLUMNS}",
                (share_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到可撤回的分享。", 404)
            share = _share_row_to_dto(cur, row)
        conn.commit()
        return {"share": share}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/accountability/prayer-requests")
def list_attention_prayer_requests(request: Request, status: str = Query(default="open")) -> dict:
    user_id = _db_user_id(_require_user(request))
    if status not in PRAYER_STATUSES | {"all"}:
        raise _json_error("VALIDATION_ERROR", "status 不合法。", 400)
    status_clause = "" if status == "all" else "AND status=%s"
    params: list[Any] = [user_id, user_id, user_id]
    if status != "all":
        params.append(status)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT {_PRAYER_COLUMNS} FROM attention_prayer_requests
                WHERE (
                    owner_user_id=%s OR target_user_id=%s OR target_group_id IN (
                        SELECT group_id FROM attention_group_members WHERE user_id=%s AND status='active'
                    )
                ) {status_clause}
                ORDER BY created_at DESC LIMIT 100""",
                tuple(params),
            )
            prayers = [_prayer_row_to_dto(cur, row, user_id) for row in cur.fetchall()]
        return {"prayerRequests": prayers}
    finally:
        _state["release_db"](conn)


@router.post("/accountability/prayer-requests")
def create_attention_prayer_request(request: Request, body: PrayerRequestIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    if body.category not in PRAYER_CATEGORIES:
        raise _json_error("VALIDATION_ERROR", "category 不合法。", 400)
    visibility = sanitize_visibility(body.visibility_level)
    safety = safety_check(body.title, body.body)
    is_sensitive = body.is_sensitive or safety["level"] in {"sensitive", "crisis"}
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            target_user_id = _resolve_user_id(cur, body.target_user_id) if body.target_user_id else None
            if target_user_id and not _has_active_relationship(cur, user_id, target_user_id):
                raise _json_error("FORBIDDEN", "只能向 active 守望伙伴发送代祷请求。", 403)
            if body.target_group_id:
                _require_group_member(cur, body.target_group_id, user_id)
            if not target_user_id and not body.target_group_id:
                raise _json_error("VALIDATION_ERROR", "请选择守望伙伴或小组。", 400)
            cur.execute(
                f"""INSERT INTO attention_prayer_requests
                (owner_user_id, target_user_id, target_group_id, title, body, category,
                 visibility_level, is_sensitive)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING {_PRAYER_COLUMNS}""",
                (user_id, target_user_id, body.target_group_id, body.title.strip(), body.body, body.category, visibility, is_sensitive),
            )
            prayer = _prayer_row_to_dto(cur, cur.fetchone(), user_id)
        conn.commit()
        response = {"prayerRequest": prayer, "safetyLevel": safety["level"]}
        if safety["level"] == "crisis":
            response["safetyNotice"] = {
                "urgent": True,
                "message": "如果你正处于即时危险或有伤害自己/他人的冲动，请立即联系身边可信任的人、当地紧急服务或专业危机援助。代祷可以同行，但不能替代现实中的紧急帮助。",
            }
        return response
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.put("/accountability/prayer-requests/{prayer_id}")
def update_attention_prayer_request(prayer_id: str, request: Request, body: PrayerRequestUpdateIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    data = body.model_dump(by_alias=True, exclude_unset=True)
    if not data:
        raise _json_error("VALIDATION_ERROR", "没有可更新的代祷请求。", 400)
    allowed = {
        "title": "title", "body": "body", "category": "category",
        "visibilityLevel": "visibility_level", "isSensitive": "is_sensitive",
        "status": "status", "answeredNote": "answered_note",
    }
    if "action" in data:
        if data["action"] == "close":
            data["status"] = "closed"
        elif data["action"] == "answer":
            data["status"] = "answered"
    if "category" in data and data["category"] not in PRAYER_CATEGORIES:
        raise _json_error("VALIDATION_ERROR", "category 不合法。", 400)
    if "status" in data and data["status"] not in PRAYER_STATUSES:
        raise _json_error("VALIDATION_ERROR", "status 不合法。", 400)
    if "visibilityLevel" in data:
        data["visibilityLevel"] = sanitize_visibility(data["visibilityLevel"])
    fields = [(allowed[k], v) for k, v in data.items() if k in allowed]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_PRAYER_COLUMNS} FROM attention_prayer_requests WHERE id=%s AND owner_user_id=%s", (prayer_id, user_id))
            if not cur.fetchone():
                raise _json_error("NOT_FOUND", "没有找到这条代祷请求。", 404)
            assignments = ", ".join([f"{col}=%s" for col, _ in fields])
            values = [v for _, v in fields]
            closed_sql = ", closed_at=now()" if data.get("status") in {"closed", "answered"} else ""
            cur.execute(
                f"UPDATE attention_prayer_requests SET {assignments}{closed_sql} WHERE id=%s RETURNING {_PRAYER_COLUMNS}",
                values + [prayer_id],
            )
            prayer = _prayer_row_to_dto(cur, cur.fetchone(), user_id)
        conn.commit()
        return {"prayerRequest": prayer}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.delete("/accountability/prayer-requests/{prayer_id}")
def delete_attention_prayer_request(prayer_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM attention_prayer_requests WHERE id=%s AND owner_user_id=%s RETURNING id", (prayer_id, user_id))
            if not cur.fetchone():
                raise _json_error("NOT_FOUND", "没有找到可删除的代祷请求。", 404)
        conn.commit()
        return {"ok": True}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.post("/accountability/prayer-requests/{prayer_id}/pray")
def mark_attention_prayer(prayer_id: str, request: Request, body: PrayerMarkIn) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_PRAYER_COLUMNS} FROM attention_prayer_requests WHERE id=%s", (prayer_id,))
            row = cur.fetchone()
            if not row or not _can_access_prayer(cur, user_id, row):
                raise _json_error("NOT_FOUND", "没有找到这条代祷请求。", 404)
            cur.execute(
                """INSERT INTO attention_prayer_marks (prayer_request_id, user_id, message)
                VALUES (%s,%s,%s)
                ON CONFLICT (prayer_request_id, user_id) DO UPDATE SET message=EXCLUDED.message
                RETURNING id, created_at""",
                (prayer_id, user_id, body.message),
            )
            mark = cur.fetchone()
        conn.commit()
        return {"mark": {"id": str(mark[0]), "createdAt": _iso(mark[1])}}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)

