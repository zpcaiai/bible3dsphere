"""Attention Stewardship / 守心 API — health / dashboard / route registry / admin observability routes.

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
from .focus import get_today_summary  # noqa: F401


def _attention_table_status(cur) -> dict[str, bool]:
    status = {}
    for table in ATTENTION_TABLES:
        rows = _safe_rows(cur, "SELECT to_regclass(%s)", (f"public.{table}",))
        status[table] = bool(rows and rows[0][0])
    return status


def _attention_health_payload(cur) -> dict:
    tables = _attention_table_status(cur)
    env = attention_environment_check(os.environ)
    content = content_library_summary(
        scripture_count=len(SCRIPTURE_LIBRARY),
        warfare_count=len(pattern_definitions()),
        challenge_count=len(CHALLENGE_TEMPLATES),
    )
    checks = {
        "database": "ok",
        "migrations": "ok" if all(tables.values()) else "missing_tables",
        "featureFlags": "ok" if env.get("ok") else "error",
        "scriptureLibrary": "ok" if content["scriptureCount"] > 0 else "missing",
        "warfarePatternLibrary": "ok" if content["warfarePatternCount"] >= 9 else "incomplete",
        "challengeTemplates": "ok" if content["challengeTemplateCount"] >= 9 else "incomplete",
        "aiFallback": "ok",
        "privacyDefaults": "ok" if DEFAULT_PRIVACY.get("defaultPartnerVisibility") == "status_only" else "warn",
    }
    return {
        "ok": all(value == "ok" for value in checks.values()),
        "version": ATTENTION_VERSION,
        "checks": checks,
        "featureFlags": env.get("featureFlags", {}),
        "environment": {"ok": env.get("ok"), "warnings": env.get("warnings", []), "errors": env.get("errors", [])},
        "tables": tables,
    }


@router.get("/health")
def get_attention_health() -> dict:
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            return _attention_health_payload(cur)
    finally:
        _state["release_db"](conn)


@router.get("/dashboard/summary")
def get_attention_dashboard_summary(request: Request) -> dict:
    return get_today_summary(request)


@router.get("/integration/routes")
def get_attention_route_registry(request: Request) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    routes = [
        route for route in ATTENTION_ROUTES
        if not route.get("requiresAdmin") or (_state.get("is_admin") and _state["is_admin"](user_id))
    ]
    return {"routes": routes}


def _aggregate_top_pulls(rows: list) -> list[dict]:
    counts: dict[str, int] = {}
    labels: dict[str, str] = {}
    for row in rows:
        items = _json_value(row[0]) or []
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            pull = str(item.get("pull") or "")
            if not pull:
                continue
            key = "sensitive" if pull in {"lust", "trauma", "addiction", "mental_health", "family_conflict"} else pull
            labels[key] = "敏感牵引" if key == "sensitive" else (item.get("label") or PULL_LABELS.get(key) or key)
            counts[key] = counts.get(key, 0) + int(item.get("count") or 1)
    return [
        {"pull": key, "label": labels.get(key, key), "count": count}
        for key, count in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:8]
    ]


def _attention_admin_overview(cur, start: date, end: date) -> dict:
    active_users = _safe_scalar(
        cur,
        """SELECT COUNT(DISTINCT user_id) FROM (
            SELECT user_id FROM attention_daily_covenants WHERE covenant_date BETWEEN %s AND %s
            UNION SELECT user_id FROM attention_entries WHERE entry_date BETWEEN %s AND %s
            UNION SELECT user_id FROM attention_focus_sessions WHERE started_at::date BETWEEN %s AND %s
            UNION SELECT user_id FROM attention_reviews WHERE review_date BETWEEN %s AND %s
        ) s""",
        (start, end, start, end, start, end, start, end),
    )
    category_rows = _safe_rows(
        cur,
        """SELECT category, COALESCE(SUM(duration_minutes),0)
        FROM attention_entries WHERE entry_date BETWEEN %s AND %s
        GROUP BY category""",
        (start, end),
    )
    top_pull_rows = _safe_rows(
        cur,
        "SELECT top_pulls FROM attention_weekly_reports WHERE week_start >= %s AND week_end <= %s AND status <> 'hidden'",
        (start, end),
    )
    metrics = {
        "activeAttentionUsers7d": active_users,
        "dailyCovenants7d": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_daily_covenants WHERE covenant_date BETWEEN %s AND %s", (start, end)),
        "focusSessions7d": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_focus_sessions WHERE started_at::date BETWEEN %s AND %s", (start, end)),
        "ledgerEntries7d": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_entries WHERE entry_date BETWEEN %s AND %s", (start, end)),
        "reviews7d": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_reviews WHERE review_date BETWEEN %s AND %s", (start, end)),
        "diagnoses7d": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_ai_diagnoses WHERE diagnosis_date BETWEEN %s AND %s", (start, end)),
        "warfarePlansActive": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_warfare_plans WHERE status='active'"),
        "weeklyReportsGenerated7d": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_weekly_reports WHERE week_start >= %s AND week_end <= %s AND status <> 'hidden'", (start, end)),
        "groupsActive": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_groups WHERE status='active'"),
        "challengesActive": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_group_challenges WHERE status='active'"),
        "prayerRequestsOpen": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_prayer_requests WHERE status='open'"),
        "crisisSafetyTriggers7d": _safe_scalar(cur, "SELECT COUNT(*) FROM attention_ai_diagnoses WHERE safety_level='crisis' AND diagnosis_date BETWEEN %s AND %s", (start, end)),
    }
    category_distribution = {str(row[0]): int(row[1] or 0) for row in category_rows}
    return {
        "metrics": metrics,
        "categoryDistribution": category_distribution,
        "topPullsAggregate": _aggregate_top_pulls(top_pull_rows),
        "featureFlags": attention_feature_flags(os.environ),
    }


@router.get("/admin/overview")
def get_attention_admin_overview(request: Request) -> dict:
    _require_attention_admin(request)
    end = date.today()
    start = end - timedelta(days=6)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            overview = _attention_admin_overview(cur, start, end)
            overview["health"] = _attention_health_payload(cur)
        return overview
    finally:
        _state["release_db"](conn)


@router.get("/admin/audit")
def get_attention_admin_audit(request: Request) -> dict:
    _require_attention_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            tables = _attention_table_status(cur)
            return attention_audit_checks(
                route_count=len(router.routes),
                table_status=tables,
                admin_enabled=attention_feature_flags(os.environ).get("ATTENTION_ADMIN_ENABLED", True),
            )
    finally:
        _state["release_db"](conn)


@router.get("/admin/content-library")
def get_attention_admin_content_library(request: Request) -> dict:
    _require_attention_admin(request)
    return {
        "contentLibrary": content_library_summary(
            scripture_count=len(SCRIPTURE_LIBRARY),
            warfare_count=len(pattern_definitions()),
            challenge_count=len(CHALLENGE_TEMPLATES),
        ),
        "routeRegistry": ATTENTION_ROUTES,
        "releaseChecklist": release_checklist(),
    }


@router.get("/admin/reports")
def get_attention_admin_reports(
    request: Request,
    from_value: Optional[str] = Query(default=None, alias="from"),
    to_value: Optional[str] = Query(default=None, alias="to"),
) -> dict:
    _require_attention_admin(request)
    end = _parse_optional_date(to_value, "to", date.today())
    start = _parse_optional_date(from_value, "from", end - timedelta(days=29))
    if (end - start).days > 90:
        raise _json_error("VALIDATION_ERROR", "运营报表时间范围最多 90 天。", 400)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            overview = _attention_admin_overview(cur, start, end)
        return {"range": {"from": start.isoformat(), "to": end.isoformat()}, **overview}
    finally:
        _state["release_db"](conn)


