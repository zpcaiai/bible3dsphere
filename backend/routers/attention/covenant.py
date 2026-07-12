"""Attention Stewardship / 守心 API — daily covenant routes.

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



@router.get("/covenant/today")
def get_today_covenant(request: Request) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    today = _local_date(request, user)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_SELECT_COLUMNS} FROM attention_daily_covenants "
                "WHERE user_id=%s AND covenant_date=%s LIMIT 1",
                (user_id, today),
            )
            row = cur.fetchone()
        return {"exists": bool(row), "covenant": _row_to_dto(row) if row else None}
    except HTTPException:
        raise
    except Exception:
        raise _json_error("INTERNAL_SERVER_ERROR", "获取今日立约失败。", 500)
    finally:
        _state["release_db"](conn)


@router.post("/covenant")
def create_covenant(request: Request, body: CovenantIn) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    today = _local_date(request, user)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM attention_daily_covenants WHERE user_id=%s AND covenant_date=%s LIMIT 1",
                (user_id, today),
            )
            if cur.fetchone():
                raise _json_error("COVENANT_ALREADY_EXISTS", "今天已经完成注意力立约，可以编辑已有立约。", 409)
            cur.execute(
                f"""
                INSERT INTO attention_daily_covenants (
                    user_id, covenant_date, primary_offering, mission_focus,
                    worship_focus, relationship_focus, restoration_focus,
                    main_risk, risk_pulls, digital_boundary, time_boundary,
                    spiritual_boundary, scripture_reference, scripture_text, prayer
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING {_SELECT_COLUMNS}
                """,
                (
                    user_id, today, body.primary_offering, body.mission_focus,
                    body.worship_focus, body.relationship_focus, body.restoration_focus,
                    body.main_risk, body.risk_pulls, body.digital_boundary,
                    body.time_boundary, body.spiritual_boundary,
                    body.scripture_reference, body.scripture_text, body.prayer,
                ),
            )
            row = cur.fetchone()
        conn.commit()
        return {"covenant": _row_to_dto(row)}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise _json_error("INTERNAL_SERVER_ERROR", "保存今日立约时遇到问题，请稍后再试。", 500)
    finally:
        _state["release_db"](conn)


@router.put("/covenant/{covenant_id}")
def update_covenant_by_id(covenant_id: str, request: Request, body: CovenantUpdate) -> dict:
    return _update_covenant(request, covenant_id, body)


@router.put("/covenant")
def update_covenant(request: Request, body: CovenantUpdate) -> dict:
    if not body.id:
        raise _json_error("VALIDATION_ERROR", "缺少立约 ID。", 400)
    return _update_covenant(request, body.id, body)


def _update_covenant(request: Request, covenant_id: str, body: CovenantUpdate) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    data = body.model_dump(by_alias=False, exclude_unset=True)
    data.pop("id", None)
    fields = {
        "primary_offering": "primary_offering",
        "mission_focus": "mission_focus",
        "worship_focus": "worship_focus",
        "relationship_focus": "relationship_focus",
        "restoration_focus": "restoration_focus",
        "main_risk": "main_risk",
        "risk_pulls": "risk_pulls",
        "digital_boundary": "digital_boundary",
        "time_boundary": "time_boundary",
        "spiritual_boundary": "spiritual_boundary",
        "scripture_reference": "scripture_reference",
        "scripture_text": "scripture_text",
        "prayer": "prayer",
        "status": "status",
    }
    updates = [(column, data[key]) for key, column in fields.items() if key in data]
    if not updates:
        raise _json_error("VALIDATION_ERROR", "没有可更新的字段。", 400)
    assignments = ", ".join([f"{column}=%s" for column, _ in updates])
    params = [value for _, value in updates] + [covenant_id, user_id]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE attention_daily_covenants SET {assignments} "
                "WHERE id=%s AND user_id=%s RETURNING " + _SELECT_COLUMNS,
                params,
            )
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这条立约。", 404)
        conn.commit()
        return {"covenant": _row_to_dto(row)}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise _json_error("INTERNAL_SERVER_ERROR", "保存今日立约时遇到问题，请稍后再试。", 500)
    finally:
        _state["release_db"](conn)


@router.get("/covenants")
def list_covenants(
    request: Request,
    from_date: Optional[str] = Query(default=None, alias="from"),
    to_date: Optional[str] = Query(default=None, alias="to"),
) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    today = _local_date(request, user)
    end = _parse_date(to_date, "to") if to_date else today
    start = _parse_date(from_date, "from") if from_date else end - timedelta(days=13)
    if start > end:
        raise _json_error("VALIDATION_ERROR", "from 不能晚于 to。", 400)
    if (end - start).days > 90:
        raise _json_error("VALIDATION_ERROR", "日期范围最多 90 天。", 400)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_SELECT_COLUMNS} FROM attention_daily_covenants "
                "WHERE user_id=%s AND covenant_date BETWEEN %s AND %s "
                "ORDER BY covenant_date DESC",
                (user_id, start, end),
            )
            rows = cur.fetchall()
        return {"covenants": [_row_to_dto(row) for row in rows]}
    except HTTPException:
        raise
    except Exception:
        raise _json_error("INTERNAL_SERVER_ERROR", "获取历史立约失败。", 500)
    finally:
        _state["release_db"](conn)


@router.post("/covenant/suggest")
def suggest_covenant(body: SuggestIn) -> dict:
    return build_attention_suggestion(
        primary_offering=body.primary_offering,
        main_risk=body.main_risk,
        risk_pulls=body.risk_pulls,
    )


