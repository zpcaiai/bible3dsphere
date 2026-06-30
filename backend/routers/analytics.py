"""
Formation Analytics router — 成长分析 (/api/analytics)

  GET  /api/analytics/summary?period=weekly|monthly   跨模块指标摘要(恩典优先)
  GET  /api/analytics/grace-evidence                  恩典证据
  POST /api/analytics/grace-evidence                  手动记录恩典证据
  GET  /api/analytics/overload                         过载信号
  POST /api/analytics/reports/generate?period=monthly 生成报告(持久化)
  GET  /api/analytics/reports                          报告列表
  GET  /api/analytics/reports/{id}                     报告详情

指标是反思镜子,不是属灵成绩;恩典证据排在表现指标之前;过载/危机优先于"打卡多"。email 标识用户。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

_state: Dict[str, Any] = {}


def init_analytics_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _c(cur, sql, params) -> int:
    try:
        cur.execute(sql, params); r = cur.fetchone(); return (r[0] or 0) if r else 0
    except Exception:
        return 0


def _aggregate(cur, email: str, days: int) -> Dict[str, Any]:
    p = (email, days)
    def since(sql):  # sql 用 %s for email, INTERVAL via days
        return _c(cur, sql.replace("{D}", str(days)), (email,))
    practice = {
        "examen": since("SELECT COUNT(*) FROM examen_entries WHERE email=%s AND entry_date >= CURRENT_DATE - INTERVAL '{D} days'"),
        "prayer_sessions": since("SELECT COUNT(*) FROM prayer_rule_sessions WHERE email=%s AND status='completed' AND session_date >= CURRENT_DATE - INTERVAL '{D} days'"),
        "lectio": since("SELECT COUNT(*) FROM lectio_sessions WHERE email=%s AND session_date >= CURRENT_DATE - INTERVAL '{D} days'"),
        "psalm_prayer": since("SELECT COUNT(*) FROM psalm_prayer_sessions WHERE email=%s AND session_date >= CURRENT_DATE - INTERVAL '{D} days'"),
        "presence_checkins": since("SELECT COUNT(*) FROM presence_checkins WHERE email=%s AND checkin_time >= NOW() - INTERVAL '{D} days'"),
        "intercession_prayed": since("SELECT COUNT(*) FROM intercession_prayer_logs WHERE email=%s AND prayed_at >= NOW() - INTERVAL '{D} days'"),
        "sabbath_sessions": since("SELECT COUNT(*) FROM sabbath_sessions WHERE email=%s AND sabbath_date >= CURRENT_DATE - INTERVAL '{D} days'"),
        "fasting_completed": since("SELECT COUNT(*) FROM fasting_plans WHERE email=%s AND status='completed' AND updated_at >= NOW() - INTERVAL '{D} days'"),
        "temptation_resisted": since("SELECT COUNT(*) FROM temptation_checkins WHERE email=%s AND outcome IN ('resisted','escaped') AND checked_in_at >= NOW() - INTERVAL '{D} days'"),
    }
    community = {
        "mentor_sessions": since("SELECT COUNT(*) FROM mentor_sessions WHERE mentee_email=%s AND status='completed' AND session_date >= NOW() - INTERVAL '{D} days'"),
        "group_checkins": since("SELECT COUNT(*) FROM accountability_group_checkins WHERE email=%s AND checkin_date >= CURRENT_DATE - INTERVAL '{D} days'"),
        "discipleship_steps": since("SELECT COUNT(*) FROM discipleship_path_steps WHERE email=%s AND status='completed' AND updated_at >= NOW() - INTERVAL '{D} days'"),
        "church_checkins": since("SELECT COUNT(*) FROM church_life_checkins WHERE email=%s AND checkin_date >= CURRENT_DATE - INTERVAL '{D} days'"),
    }
    learning = {
        "doctrine_completed": since("SELECT COUNT(*) FROM user_doctrine_progress WHERE email=%s AND status='completed' AND updated_at >= NOW() - INTERVAL '{D} days'"),
    }
    grace = {
        "answered_prayers": since("SELECT COUNT(*) FROM intercession_requests WHERE email=%s AND status='answered' AND answered_at >= NOW() - INTERVAL '{D} days'"),
        "repentance_steps": since("SELECT COUNT(*) FROM temptation_failure_reviews WHERE email=%s AND created_at >= NOW() - INTERVAL '{D} days'"),
        "recorded_grace": since("SELECT COUNT(*) FROM formation_grace_evidence WHERE email=%s AND evidence_date >= CURRENT_DATE - INTERVAL '{D} days'"),
        "temptation_resisted": practice["temptation_resisted"],
    }
    # fruit latest avg
    fruit_avg = None
    try:
        cur.execute("SELECT id FROM fruit_assessments WHERE email=%s ORDER BY assessment_date DESC LIMIT 1", (email,))
        a = cur.fetchone()
        if a:
            cur.execute("SELECT AVG(score) FROM fruit_assessment_scores WHERE assessment_id=%s AND score IS NOT NULL", (a[0],))
            v = cur.fetchone()
            fruit_avg = round(float(v[0]), 1) if v and v[0] is not None else None
    except Exception:
        pass
    return {"practice": practice, "community": community, "learning": learning, "grace": grace, "fruit_latest_avg": fruit_avg}


def _grace_lines(agg) -> List[str]:
    g = agg["grace"]; out = []
    if g["answered_prayers"]: out.append(f"看见 {g['answered_prayers']} 个代祷蒙应允——记念神的信实。")
    if g["temptation_resisted"]: out.append(f"在试探中选择忠心 {g['temptation_resisted']} 次,这是恩典里的得胜。")
    if g["repentance_steps"]: out.append("你诚实面对了跌倒并回到神面前——悔改本身就是恩典的工作。")
    if g["recorded_grace"]: out.append(f"你记录了 {g['recorded_grace']} 处神的恩典。")
    if not out: out.append("恩典常在不起眼处。试着留意这周神给你的一个小礼物。")
    return out


def _overload(agg) -> List[str]:
    p = agg["practice"]; signals = []
    total = sum(p.values())
    if total == 0:
        signals.append("这段时间记录很少——没关系,这不是评分。可以从一句晨祷重新开始。")
    if p["sabbath_sessions"] == 0 and (p["prayer_sessions"] + p["examen"]) > 12:
        signals.append("操练不少但没有安息记录:留意别把成长变成另一种效率偶像,给自己一个安息时段。")
    return signals


@router.get("/summary")
def summary(request: Request, period: str = Query(default="weekly", max_length=12)) -> dict:
    user = _require_user(request)
    days = 30 if period == "monthly" else 7
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            agg = _aggregate(cur, user["email"], days)
    finally:
        _state["release_db"](conn)
    return {"ok": True, "period": period, "days": days,
            "grace_evidence": _grace_lines(agg),
            "metrics": agg,
            "cautions": _overload(agg),
            "note": "这些是反思镜子,不是属灵成绩,也不与任何人比较。低分往往是邀请,不是定罪。"}


class GraceCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: str = Field(default="", max_length=2000)
    evidence_type: str = Field(default="other", max_length=30)
    source_module: str = Field(default="", max_length=40)


@router.post("/grace-evidence")
def add_grace(request: Request, body: GraceCreate) -> dict:
    user = _require_user(request)
    gid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO formation_grace_evidence (id, email, evidence_type, title, description, source_module) "
                        "VALUES (%s,%s,%s,%s,%s,%s)", (gid, user["email"], body.evidence_type, body.title, body.description, body.source_module))
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": gid}


@router.get("/grace-evidence")
def list_grace(request: Request) -> dict:
    user = _require_user(request); to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, evidence_date, evidence_type, title, description, source_module FROM formation_grace_evidence "
                        "WHERE email=%s ORDER BY evidence_date DESC LIMIT 60", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "grace_evidence": [
        {"id": r[0], "evidence_date": str(r[1]), "evidence_type": r[2], "title": r[3], "description": r[4] or "", "source_module": r[5] or ""} for r in rows
    ]}


@router.get("/overload")
def overload(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            agg = _aggregate(cur, user["email"], 7)
    finally:
        _state["release_db"](conn)
    return {"ok": True, "signals": _overload(agg)}


@router.post("/reports/generate")
def generate_report(request: Request, period: str = Query(default="monthly", max_length=12)) -> dict:
    user = _require_user(request); email = user["email"]
    days = 30 if period == "monthly" else 90 if period == "quarterly" else 7
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            agg = _aggregate(cur, email, days)
            grace = _grace_lines(agg); cautions = _overload(agg)
            p = agg["practice"]
            growth = []
            if p["examen"]: growth.append(f"省察 {p['examen']} 次")
            if p["prayer_sessions"]: growth.append(f"完成祷告 {p['prayer_sessions']} 次")
            if p["lectio"] + p["psalm_prayer"]: growth.append(f"读经/诗篇祷告 {p['lectio']+p['psalm_prayer']} 次")
            if agg["community"]["group_checkins"] or agg["community"]["mentor_sessions"]:
                growth.append("有群体/导师的连接")
            sections = [
                {"key": "grace", "title": "恩典证据", "items": grace},
                {"key": "growth", "title": "成长迹象", "items": growth or ["这段时间记录不多,温柔地重新开始即可。"]},
                {"key": "cautions", "title": "需要留意", "items": cautions or ["节奏看起来稳健。"]},
            ]
            rec = [{"title": "简化与稳定", "description": "下一段时间专注:晨祷一句、一次读经、安息一段。"}] if (sum(p.values()) > 20 or cautions) else \
                  [{"title": "保持节奏", "description": "继续小而稳的相交,加入一次群体连接。"}]
            title = ("季度" if period == "quarterly" else "月度" if period == "monthly" else "每周") + "成长回顾"
            summary_txt = "这段时间" + ("呈现稳定的相交节奏。" if sum(p.values()) else "记录较少,可温柔重启。") + " 恩典常在不起眼处。"
            rid = uuid.uuid4().hex
            cur.execute(
                "INSERT INTO formation_reports (id, email, report_type, period_start, period_end, title, summary, sections, recommendations) "
                "VALUES (%s,%s,%s, CURRENT_DATE - (%s || ' days')::interval, CURRENT_DATE, %s,%s,%s::jsonb,%s::jsonb)",
                (rid, email, period, str(days), title, summary_txt,
                 json.dumps(sections, ensure_ascii=False), json.dumps(rec, ensure_ascii=False)),
            )
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"report failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "report_id": rid, "title": title, "summary": summary_txt,
            "sections": sections, "recommendations": rec,
            "disclaimer": "本报告只反映已记录的活动与你的反思,不是你在神面前生命的全部真实。"}


@router.get("/reports")
def list_reports(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, report_type, title, period_start, period_end, created_at FROM formation_reports "
                        "WHERE email=%s ORDER BY created_at DESC LIMIT 24", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "reports": [
        {"id": r[0], "report_type": r[1], "title": r[2], "period_start": str(r[3]) if r[3] else "", "period_end": str(r[4]) if r[4] else ""} for r in rows
    ]}


@router.get("/reports/{rid}")
def get_report(rid: str, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT report_type, title, summary, sections, recommendations FROM formation_reports WHERE id=%s AND email=%s", (rid, user["email"]))
            r = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not r:
        raise HTTPException(status_code=404, detail="report not found")
    def jl(v):
        if isinstance(v, (list, dict)): return v
        try: return json.loads(v)
        except Exception: return []
    return {"ok": True, "report": {"report_type": r[0], "title": r[1], "summary": r[2] or "", "sections": jl(r[3]), "recommendations": jl(r[4])}}


# ── 时间序列 / 热力图 (B11 可视化) ──
_SERIES_SOURCES = [
    ("examen", "省察", "SELECT entry_date::date d, COUNT(*) FROM examen_entries WHERE email=%s AND entry_date >= CURRENT_DATE - INTERVAL '{D} days' GROUP BY 1"),
    ("prayer", "祷告", "SELECT session_date::date d, COUNT(*) FROM prayer_rule_sessions WHERE email=%s AND status='completed' AND session_date >= CURRENT_DATE - INTERVAL '{D} days' GROUP BY 1"),
    ("lectio", "读经默想", "SELECT session_date::date d, COUNT(*) FROM lectio_sessions WHERE email=%s AND session_date >= CURRENT_DATE - INTERVAL '{D} days' GROUP BY 1"),
    ("psalm", "诗篇祷告", "SELECT session_date::date d, COUNT(*) FROM psalm_prayer_sessions WHERE email=%s AND session_date >= CURRENT_DATE - INTERVAL '{D} days' GROUP BY 1"),
    ("presence", "同在操练", "SELECT checkin_time::date d, COUNT(*) FROM presence_checkins WHERE email=%s AND checkin_time >= NOW() - INTERVAL '{D} days' GROUP BY 1"),
    ("intercession", "代祷", "SELECT prayed_at::date d, COUNT(*) FROM intercession_prayer_logs WHERE email=%s AND prayed_at >= NOW() - INTERVAL '{D} days' GROUP BY 1"),
    ("sabbath", "安息", "SELECT sabbath_date::date d, COUNT(*) FROM sabbath_sessions WHERE email=%s AND sabbath_date >= CURRENT_DATE - INTERVAL '{D} days' GROUP BY 1"),
    ("group", "小组", "SELECT checkin_date::date d, COUNT(*) FROM accountability_group_checkins WHERE email=%s AND checkin_date >= CURRENT_DATE - INTERVAL '{D} days' GROUP BY 1"),
    ("church", "教会", "SELECT checkin_date::date d, COUNT(*) FROM church_life_checkins WHERE email=%s AND checkin_date >= CURRENT_DATE - INTERVAL '{D} days' GROUP BY 1"),
    ("grace", "恩典证据", "SELECT evidence_date::date d, COUNT(*) FROM formation_grace_evidence WHERE email=%s AND evidence_date >= CURRENT_DATE - INTERVAL '{D} days' GROUP BY 1"),
]


@router.get("/series")
def series(request: Request, days: int = Query(default=84, ge=7, le=180)) -> dict:
    """按天的属灵操练活动序列(热力图/趋势用)。恩典优先:这是迹象,不是评分。"""
    import datetime as _dt
    user = _require_user(request)
    email = user["email"]
    daily: Dict[str, int] = {}
    bycat: List[dict] = []
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            for key, label, tmpl in _SERIES_SOURCES:
                total = 0
                try:
                    cur.execute(tmpl.replace("{D}", str(days)), (email,))
                    for d, n in cur.fetchall():
                        ds = d.isoformat() if hasattr(d, "isoformat") else str(d)
                        daily[ds] = daily.get(ds, 0) + int(n or 0)
                        total += int(n or 0)
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                bycat.append({"source": key, "label": label, "count": total})
    finally:
        _state["release_db"](conn)
    today = _dt.date.today()
    out_daily: List[dict] = []
    maxd = 0
    for i in range(days - 1, -1, -1):
        d = today - _dt.timedelta(days=i)
        ds = d.isoformat()
        cnt = daily.get(ds, 0)
        maxd = max(maxd, cnt)
        out_daily.append({"date": ds, "count": cnt, "dow": d.isoweekday() % 7})  # 0=周日..6=周六
    weekly: List[dict] = []
    for row in out_daily:
        d = _dt.date.fromisoformat(row["date"])
        ywk = d.isocalendar()
        wkey = "%d-W%02d" % (ywk[0], ywk[1])
        if not weekly or weekly[-1]["week"] != wkey:
            weekly.append({"week": wkey, "label": "%d/%d" % (d.month, d.day), "count": 0})
        weekly[-1]["count"] += row["count"]
    bycat = sorted(bycat, key=lambda x: -x["count"])
    return {"ok": True, "days": days, "daily": out_daily, "weekly": weekly,
            "by_category": bycat, "max_daily": maxd,
            "total": sum(r["count"] for r in out_daily),
            "note": "这是属灵操练的迹象图,不是成绩单;空白的日子往往是恩典的邀请,不是定罪。"}
