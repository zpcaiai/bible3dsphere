"""
Sabbath & Rest router — 安息日与休息操练 (/api/sabbath)

  POST /api/sabbath/plans            创建安息计划
  GET  /api/sabbath/plans/active     当前安息计划
  PATCH/api/sabbath/plans/{id}       更新计划
  POST /api/sabbath/sessions         创建安息日 session
  PATCH/api/sabbath/sessions/{id}    更新 session（完成/打扰）
  POST /api/sabbath/audit            休息审计（检测效率偶像 + 推荐）
  GET  /api/sabbath/audit/latest     最近审计
  POST /api/sabbath/boundaries       创建界限
  GET  /api/sabbath/boundaries       列出界限
  GET  /api/sabbath/recommend        基于最近审计推荐安息/休息操练

抵抗效率偶像；不强制周日、不律法化；burnout 时减负。email 标识用户。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/sabbath", tags=["sabbath"])

_state: Dict[str, Any] = {}

_PLAN_COLS = ("id, email, title, status, sabbath_day, start_time, end_time, worship_plan, "
              "rest_practices, delight_practices, technology_boundaries, work_boundaries, preparation_tasks")
_AUDIT_COLS = ("id, email, audit_date, sleep_quality_score, physical_fatigue_score, emotional_fatigue_score, "
               "spiritual_dryness_score, work_pressure_score, technology_overload_score, relational_depletion_score, "
               "main_rest_blockers, idols_detected, recommended_rest_response")


def init_sabbath_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _jl(v):
    if v is None: return []
    if isinstance(v, (list, dict)): return v
    try: return json.loads(v)
    except Exception: return []


def _plan_row(r) -> dict:
    return {"id": r[0], "title": r[2], "status": r[3], "sabbath_day": r[4],
            "start_time": str(r[5])[:5] if r[5] else "", "end_time": str(r[6])[:5] if r[6] else "",
            "worship_plan": r[7] or "", "rest_practices": _jl(r[8]), "delight_practices": _jl(r[9]),
            "technology_boundaries": _jl(r[10]), "work_boundaries": _jl(r[11]), "preparation_tasks": _jl(r[12])}


def _analyze_audit(a: dict) -> Dict[str, Any]:
    """从审计分数推断休息阻碍、效率偶像与推荐。分数 0-10，越高越严重。"""
    blockers, idols, recs = [], [], []
    def hi(k): return (a.get(k) or 0) >= 7
    if hi("physical_fatigue_score") or (a.get("sleep_quality_score") or 10) <= 3:
        blockers.append("身体疲惫 / 睡眠不足"); recs.append("优先睡眠与身体休息，降低本周操练强度。")
    if hi("emotional_fatigue_score"):
        blockers.append("情绪耗竭"); recs.append("给自己独处与哀歌祷告的空间，减少社交负荷。")
    if hi("spiritual_dryness_score"):
        blockers.append("灵性枯干"); recs.append("用诗篇祷告、敬拜与温柔读经，而非更多属灵表现。")
    if hi("work_pressure_score"):
        blockers.append("工作压力"); idols.append("productivity"); recs.append("设一条工作界限，并做一次信靠的交托祷告。")
    if hi("technology_overload_score"):
        blockers.append("信息过载"); idols.append("fear_of_missing_out"); recs.append("做一次手机安息 / 离线时段与安静。")
    if hi("relational_depletion_score"):
        blockers.append("关系消耗"); recs.append("选择独处或低消耗的同在，按你此刻的需要。")
    if hi("work_pressure_score") and hi("technology_overload_score"):
        idols.append("control")
    burnout = sum(1 for k in ("physical_fatigue_score", "emotional_fatigue_score", "spiritual_dryness_score", "work_pressure_score") if hi(k)) >= 3
    if burnout:
        recs.insert(0, "多项指标偏高，像是 burnout 边缘：请先减总负荷——本周只保留一次晨祷与一段安息时段。")
    if not recs:
        recs.append("整体看起来还有余力。可以照常守一个安息时段，单纯地享受与领受。")
    seen = set(); idols = [i for i in idols if not (i in seen or seen.add(i))]
    return {"blockers": blockers, "idols": idols, "recommendations": recs, "burnout_risk": burnout}


class PlanCreate(BaseModel):
    title: str = Field(default="我的安息", max_length=120)
    sabbath_day: str = Field(default="sunday", max_length=12)
    start_time: str = Field(default="", max_length=8)
    end_time: str = Field(default="", max_length=8)
    worship_plan: str = Field(default="", max_length=2000)
    rest_practices: List[str] = Field(default_factory=list)
    delight_practices: List[str] = Field(default_factory=list)
    technology_boundaries: List[str] = Field(default_factory=list)
    work_boundaries: List[str] = Field(default_factory=list)
    preparation_tasks: List[str] = Field(default_factory=list)


@router.post("/plans")
def create_plan(request: Request, body: PlanCreate) -> dict:
    user = _require_user(request)
    pid = uuid.uuid4().hex
    j = lambda x: json.dumps(x, ensure_ascii=False)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE sabbath_plans SET status='archived' WHERE email=%s AND status='active'", (user["email"],))
            cur.execute(
                "INSERT INTO sabbath_plans (id, email, title, sabbath_day, start_time, end_time, worship_plan, "
                "rest_practices, delight_practices, technology_boundaries, work_boundaries, preparation_tasks) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb)",
                (pid, user["email"], body.title, body.sabbath_day, body.start_time or None, body.end_time or None,
                 body.worship_plan, j(body.rest_practices), j(body.delight_practices), j(body.technology_boundaries),
                 j(body.work_boundaries), j(body.preparation_tasks)),
            )
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="create failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "plan_id": pid}


@router.get("/plans/active")
def active_plan(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_PLAN_COLS} FROM sabbath_plans WHERE email=%s AND status='active' "
                        "ORDER BY created_at DESC LIMIT 1", (user["email"],))
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "plan": _plan_row(row) if row else None}


class PlanUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=120)
    status: Optional[str] = Field(default=None, max_length=12)
    worship_plan: Optional[str] = Field(default=None, max_length=2000)


@router.patch("/plans/{pid}")
def update_plan(pid: str, request: Request, body: PlanUpdate) -> dict:
    user = _require_user(request)
    sets, params = [], []
    if body.title is not None: sets.append("title=%s"); params.append(body.title)
    if body.status is not None: sets.append("status=%s"); params.append(body.status)
    if body.worship_plan is not None: sets.append("worship_plan=%s"); params.append(body.worship_plan)
    if not sets:
        return {"ok": True, "unchanged": True}
    sets.append("updated_at=NOW()"); params.extend([pid, user["email"]])
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE sabbath_plans SET {', '.join(sets)} WHERE id=%s AND email=%s", tuple(params))
            conn.commit(); n = cur.rowcount
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="update failed")
    finally:
        _state["release_db"](conn)
    if not n:
        raise HTTPException(status_code=404, detail="plan not found")
    return {"ok": True}


class SessionCreate(BaseModel):
    sabbath_plan_id: str = Field(default="", max_length=64)


@router.post("/sessions")
def create_session(request: Request, body: SessionCreate) -> dict:
    user = _require_user(request)
    sid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sabbath_sessions (id, email, sabbath_plan_id, sabbath_date, started_at, status) "
                "VALUES (%s,%s,%s,(NOW() AT TIME ZONE 'Asia/Shanghai')::date, NOW(), 'started')",
                (sid, user["email"], body.sabbath_plan_id),
            )
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="create failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "session_id": sid}


class SessionUpdate(BaseModel):
    status: Optional[str] = Field(default=None, max_length=12)
    worship_completed: Optional[bool] = None
    rest_completed: Optional[bool] = None
    delight_completed: Optional[bool] = None
    disruption_notes: Optional[str] = Field(default=None, max_length=2000)
    grace_noticed: Optional[str] = Field(default=None, max_length=2000)


@router.patch("/sessions/{sid}")
def update_session(sid: str, request: Request, body: SessionUpdate) -> dict:
    user = _require_user(request)
    sets, params = [], []
    for col, val in (("status", body.status), ("worship_completed", body.worship_completed),
                     ("rest_completed", body.rest_completed), ("delight_completed", body.delight_completed),
                     ("disruption_notes", body.disruption_notes), ("grace_noticed", body.grace_noticed)):
        if val is not None:
            sets.append(f"{col}=%s"); params.append(val)
    if not sets:
        return {"ok": True, "unchanged": True}
    if body.status == "completed":
        sets.append("ended_at=NOW()")
    sets.append("updated_at=NOW()"); params.extend([sid, user["email"]])
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE sabbath_sessions SET {', '.join(sets)} WHERE id=%s AND email=%s", tuple(params))
            conn.commit(); n = cur.rowcount
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="update failed")
    finally:
        _state["release_db"](conn)
    if not n:
        raise HTTPException(status_code=404, detail="session not found")
    return {"ok": True}


class AuditCreate(BaseModel):
    sleep_quality_score: Optional[int] = Field(default=None, ge=0, le=10)
    physical_fatigue_score: Optional[int] = Field(default=None, ge=0, le=10)
    emotional_fatigue_score: Optional[int] = Field(default=None, ge=0, le=10)
    spiritual_dryness_score: Optional[int] = Field(default=None, ge=0, le=10)
    work_pressure_score: Optional[int] = Field(default=None, ge=0, le=10)
    technology_overload_score: Optional[int] = Field(default=None, ge=0, le=10)
    relational_depletion_score: Optional[int] = Field(default=None, ge=0, le=10)
    main_rest_blockers: List[str] = Field(default_factory=list)


@router.post("/audit")
def create_audit(request: Request, body: AuditCreate) -> dict:
    user = _require_user(request)
    a = body.model_dump()
    analysis = _analyze_audit(a)
    aid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO rest_audits (id, email, audit_date, sleep_quality_score, physical_fatigue_score, "
                "emotional_fatigue_score, spiritual_dryness_score, work_pressure_score, technology_overload_score, "
                "relational_depletion_score, main_rest_blockers, idols_detected, recommended_rest_response) "
                "VALUES (%s,%s,(NOW() AT TIME ZONE 'Asia/Shanghai')::date,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s)",
                (aid, user["email"], body.sleep_quality_score, body.physical_fatigue_score, body.emotional_fatigue_score,
                 body.spiritual_dryness_score, body.work_pressure_score, body.technology_overload_score,
                 body.relational_depletion_score, json.dumps(body.main_rest_blockers, ensure_ascii=False),
                 json.dumps(analysis["idols"], ensure_ascii=False), " ".join(analysis["recommendations"])),
            )
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="audit failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "audit_id": aid, "analysis": analysis}


@router.get("/audit/latest")
def latest_audit(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_AUDIT_COLS} FROM rest_audits WHERE email=%s ORDER BY audit_date DESC, created_at DESC LIMIT 1", (user["email"],))
            r = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not r:
        return {"ok": True, "audit": None}
    return {"ok": True, "audit": {
        "id": r[0], "audit_date": str(r[2]), "sleep_quality_score": r[3], "physical_fatigue_score": r[4],
        "emotional_fatigue_score": r[5], "spiritual_dryness_score": r[6], "work_pressure_score": r[7],
        "technology_overload_score": r[8], "relational_depletion_score": r[9],
        "main_rest_blockers": _jl(r[10]), "idols_detected": _jl(r[11]), "recommended_rest_response": r[12] or ""}}


class BoundaryCreate(BaseModel):
    title: str = Field(..., max_length=120)
    boundary_type: str = Field(default="work", max_length=16)
    rule_text: str = Field(default="", max_length=2000)
    exception_policy: str = Field(default="", max_length=1000)


@router.post("/boundaries")
def create_boundary(request: Request, body: BoundaryCreate) -> dict:
    user = _require_user(request)
    bid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO rest_boundary_rules (id, email, title, boundary_type, rule_text, exception_policy) "
                        "VALUES (%s,%s,%s,%s,%s,%s)",
                        (bid, user["email"], body.title, body.boundary_type, body.rule_text, body.exception_policy))
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="create failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "boundary_id": bid}


@router.get("/boundaries")
def list_boundaries(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, boundary_type, rule_text, exception_policy FROM rest_boundary_rules "
                        "WHERE email=%s AND active=TRUE ORDER BY created_at DESC", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "boundaries": [
        {"id": r[0], "title": r[1], "boundary_type": r[2], "rule_text": r[3] or "", "exception_policy": r[4] or ""} for r in rows
    ]}


@router.get("/recommend")
def recommend(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_AUDIT_COLS} FROM rest_audits WHERE email=%s ORDER BY audit_date DESC, created_at DESC LIMIT 1", (user["email"],))
            r = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not r:
        return {"ok": True, "recommendations": ["先做一次休息审计，我再按你的状态推荐安息操练。"],
                "default_practices": ["手机离线的清晨", "敬拜预备", "慢慢吃一餐并感恩", "不带播客地散步"]}
    a = {"sleep_quality_score": r[3], "physical_fatigue_score": r[4], "emotional_fatigue_score": r[5],
         "spiritual_dryness_score": r[6], "work_pressure_score": r[7], "technology_overload_score": r[8],
         "relational_depletion_score": r[9]}
    analysis = _analyze_audit(a)
    return {"ok": True, "recommendations": analysis["recommendations"], "idols_detected": analysis["idols"],
            "burnout_risk": analysis["burnout_risk"]}
