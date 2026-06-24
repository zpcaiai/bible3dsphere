"""
Weekly Review router — 每周复盘 (/api/weekly-review)

  GET  /api/weekly-review/meta       趋势枚举
  POST /api/weekly-review/generate   聚合本周（或指定周）打卡/操练/省察 → 落库 weekly_reviews
  GET  /api/weekly-review/current    最近一份周复盘
  GET  /api/weekly-review/list       历史周复盘

聚合源：user_checkins / formation_task_logs / examen_entries（全部以 email 为用户键）。
原则：不打"属灵分数"，只给趋势 + 证据 + 1–3 个温柔的小行动。
生成的鼓励文本会best-effort经神学安全审查（Skill 9）。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:
    from backend import weekly_review_engine as engine
except Exception:  # pragma: no cover
    import weekly_review_engine as engine  # type: ignore

router = APIRouter(prefix="/api/weekly-review", tags=["weekly-review"])
_state: Dict[str, Any] = {}


def init_weekly_review_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _Json(obj):
    try:
        from psycopg2.extras import Json
        return Json(obj)
    except Exception:
        import json as _json
        return _json.dumps(obj)


def _week_bounds(week_start: Optional[str]) -> tuple:
    """返回 (start_date, end_date)；缺省取（上海时区）本周一至周日。"""
    if week_start:
        try:
            start = datetime.strptime(week_start, "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=400, detail="week_start 须为 YYYY-MM-DD")
    else:
        try:
            from zoneinfo import ZoneInfo
            today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
        except Exception:
            today = date.today()
        start = today - timedelta(days=today.weekday())  # 周一
    return start, start + timedelta(days=6)


def _fetch(cur, sql: str, params: tuple) -> List[tuple]:
    """容错查询：表缺失/查询异常时回滚并返回空，不阻断复盘生成。"""
    try:
        cur.execute(sql, params)
        return cur.fetchall()
    except Exception:
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return []


class GenerateBody(BaseModel):
    week_start: Optional[str] = Field(default=None, description="YYYY-MM-DD；缺省=本周一")
    week_end: Optional[str] = Field(default=None, description="YYYY-MM-DD；缺省=week_start+6")


@router.get("/meta")
def get_meta() -> dict:
    return {"ok": True, **engine.meta()}


@router.post("/generate")
def generate(request: Request, body: GenerateBody) -> dict:
    user = _require_user(request)
    email = user["email"]
    start, end = _week_bounds(body.week_start)
    if body.week_end:
        try:
            end = datetime.strptime(body.week_end, "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=400, detail="week_end 须为 YYYY-MM-DD")
    prior_start, prior_end = start - timedelta(days=7), start - timedelta(days=1)
    s, e, ps, pe = start.isoformat(), end.isoformat(), prior_start.isoformat(), prior_end.isoformat()

    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            ci = _fetch(cur, "SELECT data FROM user_checkins WHERE email=%s AND checkin_at::date "
                             "BETWEEN %s AND %s", (email, s, e))
            ci_prior = _fetch(cur, "SELECT data FROM user_checkins WHERE email=%s AND checkin_at::date "
                                   "BETWEEN %s AND %s", (email, ps, pe))
            tl = _fetch(cur, "SELECT completed, perceived_helpfulness FROM formation_task_logs "
                             "WHERE email=%s AND created_at::date BETWEEN %s AND %s", (email, s, e))
            ex = _fetch(cur, "SELECT consolation_level, gratitude, confession, consolation, "
                             "desolation, tomorrow_step FROM examen_entries "
                             "WHERE email=%s AND entry_date BETWEEN %s AND %s", (email, s, e))

        checkins = [{"data": r[0] or {}} for r in ci]
        prior_checkins = [{"data": r[0] or {}} for r in ci_prior]
        task_logs = [{"completed": r[0], "perceived_helpfulness": r[1]} for r in tl]
        examens = [{"consolation_level": r[0], "gratitude": r[1], "confession": r[2],
                    "consolation": r[3], "desolation": r[4], "tomorrow_step": r[5]} for r in ex]

        review = engine.summarize(s, e, checkins=checkins, prior_checkins=prior_checkins,
                                  task_logs=task_logs, examens=examens)

        # best-effort 神学安全审查（Skill 9 闭环）：审查鼓励/进展文本
        try:
            from routers.theological_safety import safety_review_and_log
            narrative = "\n".join([review.get("encouragement_summary", ""),
                                   review.get("progress_summary", "")])
            safety = safety_review_and_log(email=email, content=narrative,
                                           content_type="weekly_review")
            review["safety_status"] = safety.get("review_status")
        except Exception:
            review["safety_status"] = "skipped"

        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO weekly_reviews "
                "(email, week_start, week_end, main_theme, progress_summary, struggle_summary, "
                " repentance_summary, encouragement_summary, trend_anxiety, trend_prayer, "
                " trend_scripture, trend_community, overall_trend, metrics, recommended_next_steps, "
                " suggested_prayer_requests, generated_by_agent) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (email, week_start) DO UPDATE SET "
                " week_end=EXCLUDED.week_end, main_theme=EXCLUDED.main_theme, "
                " progress_summary=EXCLUDED.progress_summary, struggle_summary=EXCLUDED.struggle_summary, "
                " repentance_summary=EXCLUDED.repentance_summary, "
                " encouragement_summary=EXCLUDED.encouragement_summary, "
                " trend_anxiety=EXCLUDED.trend_anxiety, trend_prayer=EXCLUDED.trend_prayer, "
                " trend_scripture=EXCLUDED.trend_scripture, trend_community=EXCLUDED.trend_community, "
                " overall_trend=EXCLUDED.overall_trend, metrics=EXCLUDED.metrics, "
                " recommended_next_steps=EXCLUDED.recommended_next_steps, "
                " suggested_prayer_requests=EXCLUDED.suggested_prayer_requests, "
                " generated_by_agent=EXCLUDED.generated_by_agent, updated_at=now() "
                "RETURNING id",
                (email, s, e, review["main_theme"], review["progress_summary"],
                 review["struggle_summary"], review["repentance_summary"],
                 review["encouragement_summary"], review["trend_anxiety"], review["trend_prayer"],
                 review["trend_scripture"], review["trend_community"], review["overall_trend"],
                 _Json(review["metrics"]), _Json(review["recommended_next_steps"]),
                 _Json(review["suggested_prayer_requests"]), review["generated_by_agent"]),
            )
            review["id"] = cur.fetchone()[0]
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"generate failed: {exc}")
    finally:
        _state["release_db"](conn)

    return {"ok": True, **review}


def _row_to_dict(r, to_iso) -> dict:
    return {
        "id": r[0], "week_start": str(r[1]), "week_end": str(r[2]), "main_theme": r[3],
        "progress_summary": r[4], "struggle_summary": r[5], "repentance_summary": r[6],
        "encouragement_summary": r[7], "trend_anxiety": r[8], "trend_prayer": r[9],
        "trend_scripture": r[10], "trend_community": r[11], "overall_trend": r[12],
        "metrics": r[13], "recommended_next_steps": r[14], "suggested_prayer_requests": r[15],
        "created_at": to_iso(r[16]),
    }


_SELECT = ("SELECT id, week_start, week_end, main_theme, progress_summary, struggle_summary, "
           "repentance_summary, encouragement_summary, trend_anxiety, trend_prayer, "
           "trend_scripture, trend_community, overall_trend, metrics, recommended_next_steps, "
           "suggested_prayer_requests, created_at FROM weekly_reviews ")


@router.get("/current")
def current(request: Request) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(_SELECT + "WHERE email=%s ORDER BY week_start DESC LIMIT 1", (user["email"],))
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not row:
        return {"ok": True, "review": None}
    return {"ok": True, "review": _row_to_dict(row, to_iso)}


@router.get("/list")
def list_reviews(request: Request, limit: int = Query(default=12, ge=1, le=52)) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(_SELECT + "WHERE email=%s ORDER BY week_start DESC LIMIT %s",
                        (user["email"], limit))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "count": len(rows), "items": [_row_to_dict(r, to_iso) for r in rows]}
