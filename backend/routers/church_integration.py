"""
Church Integration router — 教会生活整合 (/api/church-integration)

  POST /api/church-integration/connections          设置/更新当前教会连接
  GET  /api/church-integration/connections/current  当前连接
  POST /api/church-integration/recommend            按连接状态推荐整合步骤
  POST /api/church-integration/rhythms              创建教会生活节奏
  GET  /api/church-integration/rhythms              列出节奏
  POST /api/church-integration/checkins             教会生活打卡
  POST /api/church-integration/reentry-plans        创建安全重返计划（教会创伤）
  GET  /api/church-integration/profiles             教会档案
  POST /api/church-integration/profiles             建教会档案

不强迫不安全的教会/权柄;教会创伤 → 先医治、设界限、慢重返;线上不替代实体教会。email 标识用户。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/church-integration", tags=["church-integration"])

_state: Dict[str, Any] = {}

_RHYTHM_TEMPLATES = ["lord_day_worship", "worship_preparation", "communion_reflection", "baptism_preparation",
                     "membership_exploration", "weekly_small_group", "service_once_month", "pastoral_checkin",
                     "mission_prayer", "generosity_reflection"]

_STEPS = {
    "not_connected": ["为寻找教会祷告", "去探访一间教会", "请一位信任的信徒推荐", "谨慎了解教会的教义与文化"],
    "exploring": ["规律探访一两间", "了解其教义与带领", "认识一两个人"],
    "visiting": ["连接一个小组", "和一位同工/牧者简短认识", "尝试一次低压力参与"],
    "regular_attender": ["探索成为成员", "加入小组", "尝试一个服事"],
    "member": ["按恩赐稳定服事", "建立安息界限", "考虑陪伴新人"],
    "serving_member": ["设服事界限,避免 burnout", "与牧者谈节奏", "保护安息与家庭"],
}


def init_church_integration_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
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


def _church_hurt(text: str) -> bool:
    try:
        from crisis_engine import detect_spiritual_crisis
        ct = detect_spiritual_crisis(text or "")
        return ct in ("church_trauma", "spiritual_abuse")
    except Exception:
        t = (text or "")
        return any(k in t for k in ["教会伤害", "属灵虐待", "被牧师", "被长老", "灵性操控", "教会创伤"])


class ConnectionUpsert(BaseModel):
    church_profile_id: str = Field(default="", max_length=64)
    connection_status: str = Field(default="not_connected", max_length=20)
    baptism_status: str = Field(default="unknown", max_length=16)
    membership_status: str = Field(default="unknown", max_length=16)
    small_group_status: str = Field(default="unknown", max_length=16)
    pastoral_contact_status: str = Field(default="unknown", max_length=16)
    notes: str = Field(default="", max_length=2000)


def _assert_org_member(email, org_id):
    from core.tenancy import require_membership
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            require_membership(cur, email, org_id)
    finally:
        _state["release_db"](conn)


def _auto_member_org(email):
    """用户恰好属于 1 个 active 组织时返回其 org_id,否则 None(用于签到自动归属)。绝不抛出。"""
    try:
        from core.tenancy import list_memberships
        conn = _state["get_db"]()
        try:
            with conn.cursor() as cur:
                ms = list_memberships(cur, email)
        finally:
            _state["release_db"](conn)
        return ms[0]["org_id"] if len(ms) == 1 else None
    except Exception:
        return None


@router.post("/connections")
def upsert_connection(request: Request, body: ConnectionUpsert) -> dict:
    user = _require_user(request); email = user["email"]
    cid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_church_connections (id, email, church_profile_id, connection_status, baptism_status, "
                "membership_status, small_group_status, pastoral_contact_status, notes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (cid, email, body.church_profile_id, body.connection_status, body.baptism_status,
                 body.membership_status, body.small_group_status, body.pastoral_contact_status, body.notes),
            )
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="save failed")
    finally:
        _state["release_db"](conn)
    out = {"ok": True, "connection_id": cid}
    if _church_hurt(body.notes):
        out["church_hurt_detected"] = True
        out["care_route"] = {"message": "听见你在教会经历的伤害。重返之前,医治与安全界限更重要。",
                             "next_endpoint": "/api/church-integration/reentry-plans", "also": "/api/care/healing"}
    return out


@router.get("/connections/current")
def current_connection(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, church_profile_id, connection_status, baptism_status, membership_status, "
                        "small_group_status, pastoral_contact_status, notes FROM user_church_connections "
                        "WHERE email=%s ORDER BY created_at DESC LIMIT 1", (user["email"],))
            r = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not r:
        return {"ok": True, "connection": None}
    return {"ok": True, "connection": {"id": r[0], "church_profile_id": r[1] or "", "connection_status": r[2],
            "baptism_status": r[3], "membership_status": r[4], "small_group_status": r[5],
            "pastoral_contact_status": r[6], "notes": r[7] or ""}}


class RecommendBody(BaseModel):
    context_text: str = Field(default="", max_length=2000)


@router.post("/recommend")
def recommend(request: Request, body: RecommendBody) -> dict:
    user = _require_user(request)
    if _church_hurt(body.context_text):
        return {"ok": True, "church_hurt": True,
                "message": "在重返教会之前,先处理伤害:医治、安全界限、信任的人同行,然后慢慢、自主地重返。",
                "steps": ["做一个安全重返计划", "列出需要的界限", "找一位信任的人同行", "先以小而安全的方式参与"],
                "care_route": "/api/care/healing"}
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT connection_status FROM user_church_connections WHERE email=%s ORDER BY created_at DESC LIMIT 1", (user["email"],))
            r = cur.fetchone()
            status = r[0] if r else "not_connected"
    finally:
        _state["release_db"](conn)
    return {"ok": True, "connection_status": status, "steps": _STEPS.get(status, _STEPS["not_connected"]),
            "note": "教会整合是渐进、具身、智慧的;线上操练不替代实体教会。"}


class RhythmCreate(BaseModel):
    rhythm_type: str = Field(default="worship", max_length=24)
    title: str = Field(..., max_length=160)
    frequency_type: str = Field(default="weekly", max_length=12)


@router.post("/rhythms")
def create_rhythm(request: Request, body: RhythmCreate) -> dict:
    user = _require_user(request)
    rid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO church_life_rhythms (id, email, rhythm_type, title, frequency_type) "
                        "VALUES (%s,%s,%s,%s,%s)", (rid, user["email"], body.rhythm_type, body.title, body.frequency_type))
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="create failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "rhythm_id": rid}


@router.get("/rhythms")
def list_rhythms(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, rhythm_type, title, frequency_type, status FROM church_life_rhythms "
                        "WHERE email=%s AND status='active' ORDER BY created_at DESC", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "rhythms": [{"id": r[0], "rhythm_type": r[1], "title": r[2], "frequency_type": r[3], "status": r[4]} for r in rows],
            "templates": _RHYTHM_TEMPLATES}


class CheckinCreate(BaseModel):
    rhythm_id: str = Field(default="", max_length=64)
    checkin_type: str = Field(default="worship", max_length=16)
    attended: Optional[bool] = None
    reflection: str = Field(default="", max_length=2000)
    next_step: str = Field(default="", max_length=1000)
    org_id: Optional[str] = Field(default=None, max_length=64)


@router.post("/checkins")
def create_checkin(request: Request, body: CheckinCreate) -> dict:
    user = _require_user(request)
    org_id = body.org_id
    if org_id:
        _assert_org_member(user["email"], org_id)   # 显式指定 → 必须是该组织成员
    else:
        org_id = _auto_member_org(user["email"])     # 未指定 → 唯一所属组织自动归属
    cid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO church_life_checkins (id, email, rhythm_id, checkin_type, attended, reflection, next_step, org_id) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (cid, user["email"], body.rhythm_id, body.checkin_type,
                        body.attended, body.reflection, body.next_step, org_id))
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="checkin failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": cid}


class ReentryCreate(BaseModel):
    reason_for_reentry: str = Field(default="church_hurt", max_length=24)
    safety_concerns: List[str] = Field(default_factory=list)
    desired_church_traits: List[str] = Field(default_factory=list)
    boundaries_needed: List[str] = Field(default_factory=list)
    first_steps: List[str] = Field(default_factory=list)
    support_person_needed: bool = Field(default=True)
    org_id: Optional[str] = Field(default=None, max_length=64)


@router.post("/reentry-plans")
def create_reentry(request: Request, body: ReentryCreate) -> dict:
    user = _require_user(request)
    j = lambda x: json.dumps(x, ensure_ascii=False)
    pid = uuid.uuid4().hex
    if body.org_id:
        _assert_org_member(user["email"], body.org_id)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO church_reentry_plans (id, email, reason_for_reentry, safety_concerns, desired_church_traits, "
                "boundaries_needed, first_steps, support_person_needed) VALUES (%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s)",
                (pid, user["email"], body.reason_for_reentry, j(body.safety_concerns), j(body.desired_church_traits),
                 j(body.boundaries_needed), j(body.first_steps), body.support_person_needed),
            )
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        print(f"[church_integration] create_reentry failed: {exc!r}", flush=True)
        raise HTTPException(status_code=500, detail="create failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "plan_id": pid,
            "guidance": "按你自己的节奏来。安全、被尊重、被陪伴是底线;任何施压你立刻回到伤害环境的,都不是健康的。"}


class ProfileCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str = Field(default="", max_length=2000)
    denomination: str = Field(default="", max_length=120)
    location_text: str = Field(default="", max_length=200)
    org_id: Optional[str] = Field(default=None, max_length=64)


@router.post("/profiles")
def create_profile(request: Request, body: ProfileCreate) -> dict:
    user = _require_user(request)
    pid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO church_profiles (id, name, description, denomination, location_text, created_by_email, org_id) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s)", (pid, body.name, body.description, body.denomination, body.location_text, user["email"], body.org_id))
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="create failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "church_profile_id": pid}


@router.get("/profiles")
def list_profiles(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, description, denomination, location_text FROM church_profiles "
                        "WHERE public=TRUE OR created_by_email=%s ORDER BY created_at DESC LIMIT 100", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "profiles": [{"id": r[0], "name": r[1], "description": r[2] or "", "denomination": r[3] or "", "location_text": r[4] or ""} for r in rows]}
