"""Attention Stewardship / 守心 API — daily stewardship scores / weekly reports / growth trends routes.

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
# Batch 5: Weekly Reports / Stewardship Scores / Growth Curves
# ---------------------------------------------------------------------------


def _score_row_to_dto(row) -> dict:
    components = _json_value(row[6]) or []
    input_summary = _json_value(row[7]) or {}
    insights = _json_value(row[8]) or {}
    return {
        "id": str(row[0]),
        "date": _iso(row[1]),
        "score": row[2],
        "scoreLabel": row[3] or "insufficient_data",
        "dataCompleteness": int(row[4] or 0),
        "confidence": row[5] or "low",
        "components": components if isinstance(components, list) else [],
        "inputSummary": input_summary if isinstance(input_summary, dict) else {},
        "insights": insights if isinstance(insights, dict) else {},
        "generatedBy": row[9],
        "version": row[10],
        "createdAt": _iso(row[11]),
        "updatedAt": _iso(row[12]),
    }



def _upsert_daily_score(cur, user_id: str, dto: dict) -> dict:
    cur.execute(
        f"""INSERT INTO attention_daily_scores
        (user_id, score_date, score, score_label, data_completeness, confidence,
         component_scores, input_summary, insights, generated_by, version)
        VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,'rules','v1')
        ON CONFLICT (user_id, score_date) DO UPDATE SET
        score=EXCLUDED.score, score_label=EXCLUDED.score_label,
        data_completeness=EXCLUDED.data_completeness, confidence=EXCLUDED.confidence,
        component_scores=EXCLUDED.component_scores, input_summary=EXCLUDED.input_summary,
        insights=EXCLUDED.insights, generated_by='rules', version='v1'
        RETURNING {_SCORE_COLUMNS}""",
        (
            user_id,
            dto["date"],
            dto.get("score"),
            dto.get("scoreLabel"),
            dto.get("dataCompleteness"),
            dto.get("confidence"),
            _Json(dto.get("components") or []),
            _Json(dto.get("inputSummary") or {}),
            _Json(dto.get("insights") or {}),
        ),
    )
    return _score_row_to_dto(cur.fetchone())


def _compute_daily_score(cur, user_id: str, target: date) -> dict:
    dto = compute_daily_score(_load_daily_score_input(cur, user_id, target))
    return _upsert_daily_score(cur, user_id, dto)


def _get_or_compute_daily_score(cur, user_id: str, target: date, force: bool = False) -> dict:
    if not force:
        cur.execute(f"SELECT {_SCORE_COLUMNS} FROM attention_daily_scores WHERE user_id=%s AND score_date=%s LIMIT 1", (user_id, target))
        row = cur.fetchone()
        if row:
            return _score_row_to_dto(row)
    return _compute_daily_score(cur, user_id, target)



def _weekly_raw_summary(cur, user_id: str, start: date, end: date) -> dict:
    cur.execute(f"SELECT {_ENTRY_COLUMNS} FROM attention_entries WHERE user_id=%s AND entry_date BETWEEN %s AND %s", (user_id, start, end))
    entries = [_entry_row_to_dto(r) for r in cur.fetchall()]
    totals = category_totals(entries)
    cur.execute(f"SELECT {_FOCUS_COLUMNS} FROM attention_focus_sessions WHERE user_id=%s AND started_at::date BETWEEN %s AND %s", (user_id, start, end))
    sessions = [_focus_row_to_dto(r) for r in cur.fetchall()]
    cur.execute(f"SELECT {_REVIEW_COLUMNS} FROM attention_reviews WHERE user_id=%s AND review_date BETWEEN %s AND %s", (user_id, start, end))
    reviews = [_review_row_to_dto(r) for r in cur.fetchall()]
    cur.execute(f"SELECT {_SCORE_COLUMNS} FROM attention_daily_scores WHERE user_id=%s AND score_date BETWEEN %s AND %s", (user_id, start, end))
    stored_scores = [_score_row_to_dto(r) for r in cur.fetchall()]
    avg_values = [s["score"] for s in stored_scores if s.get("score") is not None]
    return {
        "scoreAverage": round(sum(avg_values) / len(avg_values)) if len(avg_values) >= 2 else None,
        "capturedMinutes": totals.get("captured", 0),
        "investedMinutes": totals.get("worship", 0) + totals.get("mission", 0) + totals.get("relationship", 0) + totals.get("restoration", 0),
        "focusMinutes": sum(int(s.get("actualMinutes") or 0) for s in sessions if s.get("endedAt")),
        "reviewDays": len({r.get("reviewDate") for r in reviews}),
    }


def _build_weekly_report_input(cur, user_id: str, start: date, end: date) -> dict:
    daily_scores = [_get_or_compute_daily_score(cur, user_id, day, force=True) for day in list_dates(start, end)]
    warfare_data = _load_warfare_data(cur, user_id, start, end)
    warfare_map = build_warfare_map(warfare_data, start, end)
    return {
        "dailyScores": daily_scores,
        "entries": warfare_data["entries"],
        "focusSessions": warfare_data["focusSessions"],
        "covenants": warfare_data["covenants"],
        "reviews": warfare_data["reviews"],
        "checkins": warfare_data["checkins"],
        "activePlans": warfare_data["activePlans"],
        "primaryPattern": warfare_map.get("primaryPattern"),
    }


def _upsert_weekly_report(cur, user_id: str, report: dict) -> dict:
    cm = report["categoryMinutes"]
    sections = report["reportSections"]
    cur.execute(
        f"""INSERT INTO attention_weekly_reports
        (user_id, week_start, week_end, worship_minutes, mission_minutes,
         relationship_minutes, restoration_minutes, captured_minutes,
         score_average, score_label, score_trend, data_completeness,
         daily_scores, category_minutes, category_percentages, focus_summary,
         covenant_summary, review_summary, warfare_summary, top_pulls,
         growth_signals, report_sections, summary, main_pattern,
         recommended_practice, next_week_practice, prayer, status, version)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s,'generated','v1')
        ON CONFLICT (user_id, week_start, week_end) DO UPDATE SET
        worship_minutes=EXCLUDED.worship_minutes, mission_minutes=EXCLUDED.mission_minutes,
        relationship_minutes=EXCLUDED.relationship_minutes, restoration_minutes=EXCLUDED.restoration_minutes,
        captured_minutes=EXCLUDED.captured_minutes, score_average=EXCLUDED.score_average,
        score_label=EXCLUDED.score_label, score_trend=EXCLUDED.score_trend,
        data_completeness=EXCLUDED.data_completeness, daily_scores=EXCLUDED.daily_scores,
        category_minutes=EXCLUDED.category_minutes, category_percentages=EXCLUDED.category_percentages,
        focus_summary=EXCLUDED.focus_summary, covenant_summary=EXCLUDED.covenant_summary,
        review_summary=EXCLUDED.review_summary, warfare_summary=EXCLUDED.warfare_summary,
        top_pulls=EXCLUDED.top_pulls, growth_signals=EXCLUDED.growth_signals,
        report_sections=EXCLUDED.report_sections, summary=EXCLUDED.summary,
        main_pattern=EXCLUDED.main_pattern, recommended_practice=EXCLUDED.recommended_practice,
        next_week_practice=EXCLUDED.next_week_practice, prayer=EXCLUDED.prayer,
        status='generated', version='v1'
        RETURNING {_REPORT_COLUMNS}""",
        (
            user_id,
            report["weekStart"],
            report["weekEnd"],
            cm.get("worship", 0),
            cm.get("mission", 0),
            cm.get("relationship", 0),
            cm.get("restoration", 0),
            cm.get("captured", 0),
            report.get("scoreAverage"),
            report.get("scoreLabel"),
            report.get("scoreTrend"),
            report.get("dataCompleteness"),
            _Json(report.get("dailyScores") or []),
            _Json(report.get("categoryMinutes") or {}),
            _Json(report.get("categoryPercentages") or {}),
            _Json(report.get("focusSummary") or {}),
            _Json(report.get("covenantSummary") or {}),
            _Json(report.get("reviewSummary") or {}),
            _Json(report.get("warfareSummary") or {}),
            _Json(report.get("topPulls") or []),
            _Json(report.get("growthSignals") or {}),
            _Json(sections),
            sections.get("weeklySummary"),
            sections.get("mainPattern"),
            report.get("nextWeekPractice"),
            report.get("nextWeekPractice"),
            report.get("prayer"),
        ),
    )
    return _report_row_to_dto(cur.fetchone())


def _week_range_for_request(request: Request, user: dict, week_start: Optional[str]) -> tuple[date, date]:
    target = _parse_optional_date(week_start, "weekStart", _local_date(request, user))
    return week_range_from_start(target)


@router.get("/scores/daily")
def get_daily_score(request: Request, date_value: Optional[str] = Query(default=None, alias="date"), force: bool = Query(default=False)) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    target = _parse_optional_date(date_value, "date", _local_date(request, user))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            score = _get_or_compute_daily_score(cur, user_id, target, force)
        conn.commit()
        return {"score": score}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise _json_error("INTERNAL_SERVER_ERROR", "暂时无法计算守心节奏指标，请稍后再试。", 500)
    finally:
        _state["release_db"](conn)


@router.post("/scores/daily")
def recompute_daily_score(request: Request, body: DailyScoreIn) -> dict:
    user = _require_user(request)
    target = _parse_optional_date(body.date, "date", _local_date(request, user))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            score = _compute_daily_score(cur, _db_user_id(user), target)
        conn.commit()
        return {"score": score}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise _json_error("INTERNAL_SERVER_ERROR", "暂时无法计算守心节奏指标，请稍后再试。", 500)
    finally:
        _state["release_db"](conn)


@router.get("/scores/range")
def get_daily_scores_range(
    request: Request,
    from_date: Optional[str] = Query(default=None, alias="from"),
    to_date: Optional[str] = Query(default=None, alias="to"),
) -> dict:
    user = _require_user(request)
    end = _parse_optional_date(to_date, "to", _local_date(request, user))
    start = _parse_optional_date(from_date, "from", end - timedelta(days=13))
    if start > end or (end - start).days > 89:
        raise _json_error("VALIDATION_ERROR", "分数范围最多 90 天。", 400)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            scores = [_get_or_compute_daily_score(cur, _db_user_id(user), day, False) for day in list_dates(start, end)]
        conn.commit()
        return {"scores": scores}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise _json_error("INTERNAL_SERVER_ERROR", "暂时无法计算守心节奏指标，请稍后再试。", 500)
    finally:
        _state["release_db"](conn)


@router.get("/reports/weekly")
def get_weekly_report(request: Request, week_start: Optional[str] = Query(default=None, alias="weekStart")) -> dict:
    user = _require_user(request)
    start, end = _week_range_for_request(request, user, week_start)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_REPORT_COLUMNS} FROM attention_weekly_reports WHERE user_id=%s AND week_start=%s AND week_end=%s AND status <> 'hidden' LIMIT 1",
                (_db_user_id(user), start, end),
            )
            row = cur.fetchone()
        return {"exists": bool(row), "report": _report_row_to_dto(row) if row else None, "weekStart": start.isoformat(), "weekEnd": end.isoformat()}
    finally:
        _state["release_db"](conn)


@router.post("/reports/weekly/generate")
def generate_weekly_report(request: Request, body: WeeklyReportGenerateIn) -> dict:
    user = _require_user(request)
    user_id = _db_user_id(user)
    start, end = _week_range_for_request(request, user, body.week_start)
    prev_start, prev_end = previous_week_range(start)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if not body.force_regenerate:
                cur.execute(
                    f"SELECT {_REPORT_COLUMNS} FROM attention_weekly_reports WHERE user_id=%s AND week_start=%s AND week_end=%s AND status <> 'hidden' LIMIT 1",
                    (user_id, start, end),
                )
                row = cur.fetchone()
                if row:
                    return {"report": _report_row_to_dto(row)}
            previous = _weekly_raw_summary(cur, user_id, prev_start, prev_end)
            report_input = _build_weekly_report_input(cur, user_id, start, end)
            report = build_weekly_report(start, end, report_input, previous)
            saved = _upsert_weekly_report(cur, user_id, report)
        conn.commit()
        return {"report": saved}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise _json_error("INTERNAL_SERVER_ERROR", "生成守心周报时遇到问题，请稍后再试。", 500)
    finally:
        _state["release_db"](conn)


@router.get("/reports/weekly/history")
def list_weekly_reports(request: Request, limit: int = Query(default=12, ge=1, le=52)) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_REPORT_COLUMNS} FROM attention_weekly_reports WHERE user_id=%s AND status <> 'hidden' ORDER BY week_start DESC LIMIT %s",
                (user_id, limit),
            )
            rows = cur.fetchall()
        return {"reports": [_report_row_to_dto(r) for r in rows]}
    finally:
        _state["release_db"](conn)


@router.get("/reports/weekly/{report_id}")
def get_weekly_report_by_id(report_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_REPORT_COLUMNS} FROM attention_weekly_reports WHERE id=%s AND user_id=%s AND status <> 'hidden'", (report_id, user_id))
            row = cur.fetchone()
            if not row:
                raise _json_error("NOT_FOUND", "没有找到这份周报。", 404)
        return {"report": _report_row_to_dto(row)}
    finally:
        _state["release_db"](conn)


@router.delete("/reports/weekly/{report_id}")
def hide_weekly_report(report_id: str, request: Request) -> dict:
    user_id = _db_user_id(_require_user(request))
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE attention_weekly_reports SET status='hidden' WHERE id=%s AND user_id=%s", (report_id, user_id))
            if cur.rowcount == 0:
                raise _json_error("NOT_FOUND", "没有找到这份周报。", 404)
        conn.commit()
        return {"ok": True}
    except HTTPException:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)


@router.get("/growth")
def get_growth_trends(
    request: Request,
    days: int = Query(default=30),
    from_date: Optional[str] = Query(default=None, alias="from"),
    to_date: Optional[str] = Query(default=None, alias="to"),
) -> dict:
    user = _require_user(request)
    today = _local_date(request, user)
    if from_date or to_date:
        end = _parse_optional_date(to_date, "to", today)
        start = _parse_optional_date(from_date, "from", end - timedelta(days=29))
    else:
        if days not in {30, 60, 90}:
            raise _json_error("VALIDATION_ERROR", "days 只能是 30、60 或 90。", 400)
        end = today
        start = end - timedelta(days=days - 1)
    if start > end or (end - start).days > 89:
        raise _json_error("VALIDATION_ERROR", "成长曲线范围最多 90 天。", 400)
    user_id = _db_user_id(user)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            points = []
            for day in list_dates(start, end):
                score = _get_or_compute_daily_score(cur, user_id, day, False)
                input_summary = score.get("inputSummary") or {}
                cm = input_summary
                category_minutes = input_summary.get("categoryMinutes") or {}
                points.append({
                    "date": day.isoformat(),
                    "score": score.get("score"),
                    "dataCompleteness": score.get("dataCompleteness", 0),
                    "investedMinutes": cm.get("investedMinutes", 0),
                    "capturedMinutes": cm.get("capturedMinutes", 0),
                    "capturedRatio": cm.get("capturedRatio"),
                    "worshipMinutes": category_minutes.get("worship", 0),
                    "missionMinutes": category_minutes.get("mission", 0),
                    "relationshipMinutes": category_minutes.get("relationship", 0),
                    "restorationMinutes": category_minutes.get("restoration", 0),
                    "focusMinutes": cm.get("focusMinutes", 0),
                    "reviewCompleted": bool(cm.get("reviewExists")),
                    "planCheckins": cm.get("planCheckinsCount", 0),
                    "topPulls": cm.get("topPulls", []),
                })
        conn.commit()
        return {"trend": {"range": {"from": start.isoformat(), "to": end.isoformat(), "days": (end - start).days + 1}, "points": points, "summary": growth_summary(points)}}
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise _json_error("INTERNAL_SERVER_ERROR", "暂时无法加载成长曲线，请稍后再试。", 500)
    finally:
        _state["release_db"](conn)

