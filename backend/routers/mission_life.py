"""
Mission Life Design router — 使命生活设计 (/api/mission-life)

把基督的使命整合进日常（职业/家庭/邻舍/款待/金钱/时间/技能/科技/安息…）。
不是要人人全职服事，而是全人在神面前的管家职分。

  GET  /api/mission-life/domains              使命领域库
  POST /api/mission-life/profiles             创建使命生活画像
  GET  /api/mission-life/profiles/latest      最近一个画像
  POST /api/mission-life/design               按生命季节生成推荐（含过载/救世主情结护栏）
  POST /api/mission-life/profiles/{pid}/commitments  添加领域承诺
  GET  /api/mission-life/commitments          列出承诺
  PATCH /api/mission-life/commitments/{cid}   更新承诺状态
  POST /api/mission-life/projects             创建使命项目
  GET  /api/mission-life/projects             列出项目
  POST /api/mission-life/projects/{pid}/logs  记录项目进展
  GET  /api/mission-life/review               简要回顾 + 过载提醒

护栏：使命始于日常忠心，不靠新项目证明自己；安息/教会节奏不塌陷前不扩张；
burnout/低能量季节先恢复、简化。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/mission-life", tags=["mission-life"])

_state: Dict[str, Any] = {}

_SEASON_RECO = {
    "student":         ["learning_teaching", "workplace_witness", "prayer_mission", "rest_as_witness"],
    "single_worker":   ["workplace_witness", "hospitality", "prayer_mission", "rest_as_witness"],
    "married":         ["family_discipleship", "hospitality", "church_service", "money_stewardship"],
    "parent":          ["family_discipleship", "neighborhood_presence", "rest_as_witness", "prayer_mission"],
    "caregiver":       ["prayer_mission", "rest_as_witness", "mercy_justice", "family_discipleship"],
    "ministry_worker": ["rest_as_witness", "prayer_mission", "family_discipleship", "skill_stewardship"],
    "entrepreneur":    ["workplace_witness", "money_stewardship", "rest_as_witness", "mercy_justice"],
    "academic":        ["learning_teaching", "workplace_witness", "creative_mission", "prayer_mission"],
    "retired":         ["prayer_mission", "mercy_justice", "hospitality", "learning_teaching"],
    "transition":      ["rest_as_witness", "prayer_mission", "learning_teaching", "time_stewardship"],
    "suffering":       ["rest_as_witness", "prayer_mission", "mercy_justice"],
    "rebuilding":      ["rest_as_witness", "prayer_mission", "time_stewardship"],
}
_DEFAULT_RECO = ["workplace_witness", "hospitality", "prayer_mission", "rest_as_witness"]
_RECOVERY_SEASONS = {"suffering", "rebuilding", "ministry_worker", "caregiver", "transition"}

_PROFILE_COLS = ("id, email, title, life_season, vocation_summary, family_context, work_context, "
                 "neighborhood_context, key_constraints, key_opportunities, mission_summary, status, created_at")
_COMMIT_COLS = ("id, email, profile_id, domain_key, title, description, frequency, minimum_action, "
                "normal_action, stretch_action, status, created_at")
_PROJECT_COLS = ("id, email, title, description, project_type, desired_fruit, status, start_date, created_at")
_LOG_COLS = ("id, email, project_id, log_date, action_taken, fruit_observed, obstacles, next_step, created_at")


def init_mission_life_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _jl(v):
    if v is None:
        return []
    if isinstance(v, (list, dict)):
        return v
    try:
        return json.loads(v)
    except Exception:
        return []


def _scan_crisis(*texts: str) -> Optional[dict]:
    blob = "\n".join(t for t in texts if t and t.strip())
    if not blob.strip():
        return None
    try:
        from crisis_engine import detect_spiritual_crisis
        ctype = detect_spiritual_crisis(blob)
    except Exception:
        return None
    if not ctype:
        return None
    return {"type": ctype, "route": "/api/crisis",
            "message": "你字里行间的重担很重要。此刻被陪伴比规划使命更要紧。",
            "note": "若愿意，可以现在联系一位信任的人，或在「危机陪伴」里获得支持。"}


def _profile_row(r, to_iso) -> dict:
    return {"id": r[0], "email": r[1], "title": r[2] or "", "life_season": r[3] or "",
            "vocation_summary": r[4] or "", "family_context": r[5] or "", "work_context": r[6] or "",
            "neighborhood_context": r[7] or "", "key_constraints": _jl(r[8]), "key_opportunities": _jl(r[9]),
            "mission_summary": r[10] or "", "status": r[11] or "active", "created_at": to_iso(r[12])}


def _commit_row(r, to_iso) -> dict:
    return {"id": r[0], "email": r[1], "profile_id": r[2] or "", "domain_key": r[3] or "",
            "title": r[4] or "", "description": r[5] or "", "frequency": r[6] or "weekly",
            "minimum_action": r[7] or "", "normal_action": r[8] or "", "stretch_action": r[9] or "",
            "status": r[10] or "active", "created_at": to_iso(r[11])}


def _project_row(r, to_iso) -> dict:
    return {"id": r[0], "email": r[1], "title": r[2] or "", "description": r[3] or "",
            "project_type": r[4] or "personal", "desired_fruit": _jl(r[5]), "status": r[6] or "active",
            "start_date": str(r[7]) if r[7] else "", "created_at": to_iso(r[8])}


# ── 领域库 ────────────────────────────────────────────────────────────────────

@router.get("/domains")
def list_domains(request: Request) -> dict:
    _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT domain_key, display_name, description, examples FROM mission_domains ORDER BY sort_order")
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "domains": [
        {"domain_key": r[0], "display_name": r[1], "description": r[2] or "", "examples": _jl(r[3])} for r in rows
    ]}


# ── 画像 ──────────────────────────────────────────────────────────────────────

class ProfileCreate(BaseModel):
    life_season: str = Field(default="single_worker", max_length=30)
    title: str = Field(default="使命生活", max_length=120)
    vocation_summary: str = Field(default="", max_length=2000)
    family_context: str = Field(default="", max_length=2000)
    work_context: str = Field(default="", max_length=2000)
    neighborhood_context: str = Field(default="", max_length=2000)
    key_constraints: List[str] = Field(default_factory=list)
    key_opportunities: List[str] = Field(default_factory=list)


@router.post("/profiles")
def create_profile(request: Request, body: ProfileCreate) -> dict:
    user = _require_user(request)
    email = user["email"]
    to_iso = _state["to_shanghai_iso"]
    pid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO mission_life_profiles "
                "(id, email, title, life_season, vocation_summary, family_context, work_context, "
                " neighborhood_context, key_constraints, key_opportunities) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)",
                (pid, email, body.title, body.life_season, body.vocation_summary, body.family_context,
                 body.work_context, body.neighborhood_context,
                 json.dumps(body.key_constraints, ensure_ascii=False),
                 json.dumps(body.key_opportunities, ensure_ascii=False)),
            )
            conn.commit()
            cur.execute(f"SELECT {_PROFILE_COLS} FROM mission_life_profiles WHERE id=%s", (pid,))
            row = cur.fetchone()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "profile": _profile_row(row, to_iso)}


@router.get("/profiles/latest")
def latest_profile(request: Request) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_PROFILE_COLS} FROM mission_life_profiles WHERE email=%s "
                        "ORDER BY created_at DESC LIMIT 1", (user["email"],))
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "profile": _profile_row(row, to_iso) if row else None}


# ── 设计推荐 ──────────────────────────────────────────────────────────────────

class DesignBody(BaseModel):
    life_season: str = Field(default="single_worker", max_length=30)
    energy_level: str = Field(default="normal", max_length=20)  # low/normal/high
    formation_need: str = Field(default="", max_length=200)


@router.post("/design")
def design(request: Request, body: DesignBody) -> dict:
    _require_user(request)
    season = (body.life_season or "single_worker").strip()
    recovery = season in _RECOVERY_SEASONS or (body.energy_level or "").strip().lower() == "low"
    keys = list(_SEASON_RECO.get(season, _DEFAULT_RECO))
    if recovery:
        keys = keys[:2]  # 恢复季节：少而稳

    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT domain_key, display_name, description, examples FROM mission_domains WHERE domain_key IN %s", (tuple(keys),))
            by = {r[0]: r for r in cur.fetchall()}
    finally:
        _state["release_db"](conn)

    recommended = []
    for k in keys:
        r = by.get(k)
        if not r:
            continue
        ex = _jl(r[3])
        recommended.append({
            "domain_key": k, "display_name": r[1],
            "commitment": (r[2] or "")[:80],
            "minimum_viable_action": ex[0] if ex else "迈出一小步",
            "normal_action": ex[1] if len(ex) > 1 else "",
        })

    guardrails = [
        "使命始于在日常责任上的忠心，不必靠新项目来证明自己。",
        "在安息与教会节奏不塌陷之前，不要新增高强度的使命项目。",
    ]
    if recovery:
        guardrails.insert(0, "你正处于需要恢复的季节：先安息、简化，第一步保持小而真实。")

    return {"ok": True, "life_season": season, "recovery_mode": recovery,
            "mission_summary": "在你当下的季节里，作一个忠心、不焦虑、以爱待人的见证者与管家。",
            "recommended_domains": recommended, "guardrails": guardrails}


# ── 承诺 ──────────────────────────────────────────────────────────────────────

class CommitmentCreate(BaseModel):
    domain_key: str = Field(..., max_length=40)
    title: str = Field(..., max_length=160)
    description: str = Field(default="", max_length=2000)
    frequency: str = Field(default="weekly", max_length=20)
    minimum_action: str = Field(default="", max_length=500)
    normal_action: str = Field(default="", max_length=500)
    stretch_action: str = Field(default="", max_length=500)


@router.post("/profiles/{pid}/commitments")
def add_commitment(pid: str, request: Request, body: CommitmentCreate) -> dict:
    user = _require_user(request)
    email = user["email"]
    to_iso = _state["to_shanghai_iso"]
    cid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            # 过载护栏：daily 承诺超过 3 个时提醒
            cur.execute("SELECT COUNT(*) FROM mission_commitments WHERE email=%s AND status='active' AND frequency='daily'", (email,))
            daily_n = cur.fetchone()[0] or 0
            cur.execute(
                "INSERT INTO mission_commitments "
                "(id, email, profile_id, domain_key, title, description, frequency, minimum_action, normal_action, stretch_action) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (cid, email, pid, body.domain_key, body.title, body.description, body.frequency,
                 body.minimum_action, body.normal_action, body.stretch_action),
            )
            conn.commit()
            cur.execute(f"SELECT {_COMMIT_COLS} FROM mission_commitments WHERE id=%s", (cid,))
            row = cur.fetchone()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    try:
        from formation_bridge import record_formation
        record_formation(user.get("id"), ["growth"], reflection_active=True,
                         decision_category="mission_life")
    except Exception:
        pass
    out = {"ok": True, "commitment": _commit_row(row, to_iso)}
    if body.frequency == "daily" and daily_n >= 3:
        out["overload_warning"] = "你已有多个每日使命承诺。小而稳胜过多而散——考虑把部分降为每周，留出安息。"
    return out


@router.get("/commitments")
def list_commitments(request: Request) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_COMMIT_COLS} FROM mission_commitments WHERE email=%s AND status<>'archived' "
                        "ORDER BY created_at DESC", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "commitments": [_commit_row(r, to_iso) for r in rows]}


class CommitmentUpdate(BaseModel):
    status: str = Field(..., max_length=20)


@router.patch("/commitments/{cid}")
def update_commitment(cid: str, request: Request, body: CommitmentUpdate) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE mission_commitments SET status=%s, updated_at=NOW() WHERE id=%s AND email=%s",
                        (body.status, cid, user["email"]))
            conn.commit()
            n = cur.rowcount
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"update failed: {exc}")
    finally:
        _state["release_db"](conn)
    if not n:
        raise HTTPException(status_code=404, detail="commitment not found")
    return {"ok": True}


# ── 项目 ──────────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    title: str = Field(..., max_length=160)
    description: str = Field(default="", max_length=4000)
    project_type: str = Field(default="personal", max_length=30)
    desired_fruit: List[str] = Field(default_factory=list)


@router.post("/projects")
def create_project(request: Request, body: ProjectCreate) -> dict:
    user = _require_user(request)
    email = user["email"]
    to_iso = _state["to_shanghai_iso"]
    pid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO mission_projects (id, email, title, description, project_type, desired_fruit, start_date) "
                "VALUES (%s,%s,%s,%s,%s,%s::jsonb,(NOW() AT TIME ZONE 'Asia/Shanghai')::date)",
                (pid, email, body.title, body.description, body.project_type,
                 json.dumps(body.desired_fruit, ensure_ascii=False)),
            )
            conn.commit()
            cur.execute(f"SELECT {_PROJECT_COLS} FROM mission_projects WHERE id=%s", (pid,))
            row = cur.fetchone()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "project": _project_row(row, to_iso)}


@router.get("/projects")
def list_projects(request: Request) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_PROJECT_COLS} FROM mission_projects WHERE email=%s AND status<>'archived' "
                        "ORDER BY created_at DESC", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "projects": [_project_row(r, to_iso) for r in rows]}


class ProjectLogCreate(BaseModel):
    action_taken: str = Field(default="", max_length=2000)
    fruit_observed: List[str] = Field(default_factory=list)
    obstacles: str = Field(default="", max_length=2000)
    next_step: str = Field(default="", max_length=2000)


@router.post("/projects/{pid}/logs")
def add_project_log(pid: str, request: Request, body: ProjectLogCreate) -> dict:
    user = _require_user(request)
    email = user["email"]
    crisis = _scan_crisis(body.obstacles, body.action_taken)
    lid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM mission_projects WHERE id=%s AND email=%s", (pid, email))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="project not found")
            cur.execute(
                "INSERT INTO mission_project_logs "
                "(id, email, project_id, log_date, action_taken, fruit_observed, obstacles, next_step) "
                "VALUES (%s,%s,%s,(NOW() AT TIME ZONE 'Asia/Shanghai')::date,%s,%s::jsonb,%s,%s)",
                (lid, email, pid, body.action_taken,
                 json.dumps(body.fruit_observed, ensure_ascii=False), body.obstacles, body.next_step),
            )
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"log failed: {exc}")
    finally:
        _state["release_db"](conn)
    out = {"ok": True, "id": lid}
    if crisis:
        out["crisis"] = crisis
    return out


@router.get("/review")
def review(request: Request) -> dict:
    user = _require_user(request)
    email = user["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM mission_commitments WHERE email=%s AND status='active'", (email,))
            commits = cur.fetchone()[0] or 0
            cur.execute("SELECT COUNT(*) FROM mission_commitments WHERE email=%s AND status='active' AND frequency='daily'", (email,))
            daily = cur.fetchone()[0] or 0
            cur.execute("SELECT COUNT(*) FROM mission_projects WHERE email=%s AND status='active'", (email,))
            projects = cur.fetchone()[0] or 0
            cur.execute("SELECT COUNT(*) FROM mission_project_logs WHERE email=%s", (email,))
            logs = cur.fetchone()[0] or 0
    finally:
        _state["release_db"](conn)
    insights = []
    if daily > 3:
        insights.append("每日使命承诺偏多，考虑简化、留出安息，避免把使命变成另一种效率偶像。")
    if projects > 2:
        insights.append("同时进行的项目较多；忠于少数、做深，胜过铺得太广。")
    if not insights:
        insights.append("节奏看起来稳健。继续在日常责任上的忠心。")
    return {"ok": True, "summary": {"active_commitments": commits, "daily_commitments": daily,
            "active_projects": projects, "project_logs": logs}, "insights": insights}
