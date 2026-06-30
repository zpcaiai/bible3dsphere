"""
Suffering router — 苦难神学与危机联动 (/api/suffering)   Advanced Batch · Module 6

  POST /api/suffering/cases/analyze            分析痛苦 → 生成 case/哀歌/关怀计划（高危则联动危机）
  GET  /api/suffering/cases                    我的苦难案例列表
  GET  /api/suffering/cases/{id}               单个案例 + 哀歌 + 关怀计划
  POST /api/suffering/cases/{id}/lament-prayer 写一篇哀歌
  GET  /api/suffering/care-plans/active        我进行中的关怀计划
  PATCH /api/suffering/care-plans/{id}/status  更新关怀计划状态

边界：仅本人可访问自己的数据；危机语言必须触发 crisis_event 并建议真实人介入，
不可只给经文；AI 不替代牧者或专业帮助。
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

try:
    from backend import suffering_engine as se  # type: ignore
except Exception:  # pragma: no cover
    import suffering_engine as se  # type: ignore

router = APIRouter(prefix="/api/suffering", tags=["suffering"])
_state: Dict[str, Any] = {}

_VALID_PLAN_STATUS = {"draft", "active", "completed", "paused"}


def init_suffering_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


class AnalyzeBody(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    source_type: str = Field(default="reflection_log", max_length=40)
    source_id: Optional[str] = Field(default=None, max_length=64)


class LamentBody(BaseModel):
    raw_lament: str = Field(min_length=1, max_length=8000)
    title: str = Field(default="我的哀歌", max_length=200)
    guided_prayer: Optional[str] = Field(default=None, max_length=4000)
    share_level: str = Field(default="private", max_length=20)


class PlanStatusBody(BaseModel):
    status: str = Field(max_length=20)


@router.post("/cases/analyze")
def analyze(body: AnalyzeBody, request: Request) -> dict:
    user = _require_user(request)
    result = se.run_and_persist(
        user["email"], body.content, source_type=body.source_type,
        source_id=body.source_id, get_db=_state["get_db"], release_db=_state["release_db"],
    )
    out = {"ok": True, **result}
    try:
        from safety_scan import scan_crisis
        _c = scan_crisis(body.content)
        if _c and "crisis" not in out:
            out["crisis"] = _c
    except Exception:
        pass
    return out


@router.get("/cases")
def list_cases(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, case_type, title, summary, risk_level, theological_theme, "
                "status, crisis_event_id, created_at FROM suffering_cases "
                "WHERE email=%s ORDER BY created_at DESC LIMIT 100",
                (user["email"],),
            )
            cases = [{
                "id": str(r[0]), "case_type": r[1], "title": r[2], "summary": r[3],
                "risk_level": r[4], "theological_theme": r[5], "status": r[6],
                "crisis_linked": bool(r[7]), "created_at": _state["to_shanghai_iso"](r[8]),
            } for r in cur.fetchall()]
        return {"ok": True, "cases": cases}
    finally:
        _state["release_db"](conn)


@router.get("/cases/{case_id}")
def get_case(case_id: str, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, case_type, title, summary, risk_level, suffering_stage, "
                "theological_theme, status, crisis_event_id, created_at FROM suffering_cases "
                "WHERE id=%s AND email=%s",
                (case_id, user["email"]),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="case not found")
            case = {
                "id": str(row[0]), "case_type": row[1], "title": row[2], "summary": row[3],
                "risk_level": row[4], "suffering_stage": row[5], "theological_theme": row[6],
                "status": row[7], "crisis_linked": bool(row[8]),
                "created_at": _state["to_shanghai_iso"](row[9]),
            }
            cur.execute(
                "SELECT id, title, guided_prayer, scripture_anchors, share_level, created_at "
                "FROM lament_prayers WHERE suffering_case_id=%s AND email=%s ORDER BY created_at DESC",
                (case_id, user["email"]),
            )
            case["lament_prayers"] = [{
                "id": str(r[0]), "title": r[1], "guided_prayer": r[2],
                "scripture_anchors": r[3], "share_level": r[4],
                "created_at": _state["to_shanghai_iso"](r[5]),
            } for r in cur.fetchall()]
            cur.execute(
                "SELECT id, title, plan_type, scripture_path, prayer_path, community_actions, "
                "duration_days, status FROM suffering_care_plans "
                "WHERE suffering_case_id=%s AND email=%s ORDER BY created_at DESC",
                (case_id, user["email"]),
            )
            case["care_plans"] = [{
                "id": str(r[0]), "title": r[1], "plan_type": r[2], "scripture_path": r[3],
                "prayer_path": r[4], "community_actions": r[5], "duration_days": r[6],
                "status": r[7],
            } for r in cur.fetchall()]
        return {"ok": True, "case": case}
    finally:
        _state["release_db"](conn)


@router.post("/cases/{case_id}/lament-prayer")
def add_lament(case_id: str, body: LamentBody, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM suffering_cases WHERE id=%s AND email=%s", (case_id, user["email"]))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="case not found")
            cur.execute(
                "INSERT INTO lament_prayers (email, suffering_case_id, title, raw_lament, "
                "guided_prayer, share_level) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                (user["email"], case_id, body.title, body.raw_lament, body.guided_prayer, body.share_level),
            )
            lid = str(cur.fetchone()[0])
        conn.commit()
        return {"ok": True, "lament_prayer_id": lid}
    finally:
        _state["release_db"](conn)


@router.get("/care-plans/active")
def active_plans(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, suffering_case_id, title, plan_type, scripture_path, prayer_path, "
                "community_actions, duration_days, status FROM suffering_care_plans "
                "WHERE email=%s AND status IN ('draft','active') ORDER BY created_at DESC",
                (user["email"],),
            )
            plans = [{
                "id": str(r[0]), "suffering_case_id": str(r[1]) if r[1] else None, "title": r[2],
                "plan_type": r[3], "scripture_path": r[4], "prayer_path": r[5],
                "community_actions": r[6], "duration_days": r[7], "status": r[8],
            } for r in cur.fetchall()]
        return {"ok": True, "care_plans": plans}
    finally:
        _state["release_db"](conn)


@router.patch("/care-plans/{plan_id}/status")
def update_plan_status(plan_id: str, body: PlanStatusBody, request: Request) -> dict:
    user = _require_user(request)
    if body.status not in _VALID_PLAN_STATUS:
        raise HTTPException(status_code=400, detail="invalid status")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE suffering_care_plans SET status=%s, updated_at=now() "
                "WHERE id=%s AND email=%s RETURNING id",
                (body.status, plan_id, user["email"]),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="care plan not found")
        conn.commit()
        return {"ok": True, "status": body.status}
    finally:
        _state["release_db"](conn)
