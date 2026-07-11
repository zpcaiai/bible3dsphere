"""
Mentor Coaching router — 导师陪跑 (/api/mentor)

  POST /api/mentor/relationships                建立陪跑关系（{counterpart_email,my_role}）
  GET  /api/mentor/relationships                我的关系（作为 mentee 或 mentor）
  PATCH/api/mentor/relationships/{id}           更新状态/同意范围
  POST /api/mentor/relationships/{id}/sessions  创建会面
  GET  /api/mentor/relationships/{id}/sessions  会面列表
  PATCH/api/mentor/sessions/{id}                更新会面
  POST /api/mentor/relationships/{id}/observations  添加成长观察
  GET  /api/mentor/relationships/{id}/observations  观察列表（mentee 只见 visible 的）
  GET  /api/mentor/questions                    提问库（?category=）
  POST /api/mentor/recommend                    按会面类型推荐议程+提问
  POST /api/mentor/relationships/{id}/action-plans  创建行动计划
  GET  /api/mentor/relationships/{id}/action-plans  行动计划列表
  POST /api/mentor/relationships/{id}/review    生成回顾摘要

同意优先:调用者须是关系双方之一;导师不索取超出同意范围的隐私;危机超出角色应升级到牧养/危机。
email 标识用户。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/mentor", tags=["mentor"])

_state: Dict[str, Any] = {}

_REL_COLS = "id, mentee_email, mentor_email, relationship_type, status, permission_scope, goals, start_date, created_at"
_SES_COLS = ("id, relationship_id, mentee_email, mentor_email, session_date, session_type, agenda, summary, "
             "prayer_notes, action_items, status, created_at")

_RECO = {
    "discipleship_review": (["heart", "gospel", "habits"], ["以祷告和一件感恩开始", "回顾上次的行动计划", "谈一处成长证据与一处挣扎", "选一个下一步", "代祷与约定下次"]),
    "habit_review": (["habits", "virtue"], ["回顾本周操练", "哪个是生命的、哪个成了负担", "需要简化哪一个", "下一步"]),
    "virtue_review": (["virtue", "vice"], ["神在培养哪样品格", "反复出现的挣扎模式", "对应的操练", "代祷"]),
    "calling_discernment": (["calling", "mission"], ["你的负担与恩赐在哪里相遇", "最近在哪服事有生命", "一个低风险的尝试", "群体印证"]),
    "crisis_followup": (["suffering", "heart"], ["先确认安全与被陪伴", "你现在正承受什么", "需要什么实际帮助", "是否需要牧养/专业支持"]),
    "prayer": (["prayer", "scripture"], ["你的祷告现在怎样", "哪段经文在对你说话", "一起祷告"]),
    "leadership_training": (["leadership", "gospel", "virtue"], ["带领中哪里被试探用掌控/形象", "谁向你说真话", "谦卑与服事的下一步"]),
    "checkin": (["heart", "gospel", "prayer"], ["以祷告和一件感恩开始", "这段时间你的心被什么占据", "哪里需要帮助而非建议", "代祷与下次约定"]),
}


def init_mentor_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
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


def _party(cur, rid: str, email: str):
    """返回关系行(若 email 是 mentee 或 mentor),否则 None。"""
    cur.execute(f"SELECT {_REL_COLS} FROM mentor_relationships WHERE id=%s AND (mentee_email=%s OR mentor_email=%s)",
                (rid, email, email))
    return cur.fetchone()


def _rel_row(r, to_iso) -> dict:
    return {"id": r[0], "mentee_email": r[1], "mentor_email": r[2], "relationship_type": r[3],
            "status": r[4], "permission_scope": r[5], "goals": _jl(r[6]),
            "start_date": str(r[7]) if r[7] else "", "created_at": to_iso(r[8])}


def _ses_row(r, to_iso) -> dict:
    return {"id": r[0], "relationship_id": r[1], "session_date": to_iso(r[4]) if r[4] else None,
            "session_type": r[5], "agenda": _jl(r[6]), "summary": r[7] or "",
            "prayer_notes": r[8] or "", "action_items": _jl(r[9]), "status": r[10] or "planned",
            "created_at": to_iso(r[11])}


class RelCreate(BaseModel):
    counterpart_email: str = Field(..., max_length=255)
    my_role: str = Field(default="mentee", max_length=12)  # mentee / mentor
    relationship_type: str = Field(default="mentor", max_length=20)
    permission_scope: str = Field(default="session_only", max_length=24)
    org_id: Optional[str] = Field(default=None, max_length=64)


def _assert_org_member(email, org_id):
    from core.tenancy import require_membership
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            require_membership(cur, email, org_id)
    finally:
        _state["release_db"](conn)


# Known-value sets per migrations/0113_mentor.sql column comments.
_VALID_MY_ROLES = {"mentee", "mentor"}
_VALID_REL_TYPES = {"mentor", "pastor", "group_leader", "coach", "discipler", "peer_mentor"}
_VALID_PERMISSION_SCOPES = {"session_only", "growth_summary", "formation_dashboard", "care_flags"}


@router.post("/relationships")
def create_rel(request: Request, body: RelCreate) -> dict:
    user = _require_user(request); email = user["email"]
    to_iso = _state["to_shanghai_iso"]
    # 校验枚举，拒绝非法角色/关系类型/权限范围
    if body.my_role not in _VALID_MY_ROLES:
        raise HTTPException(status_code=400, detail="invalid my_role")
    if body.relationship_type not in _VALID_REL_TYPES:
        raise HTTPException(status_code=400, detail="invalid relationship_type")
    if body.permission_scope not in _VALID_PERMISSION_SCOPES:
        raise HTTPException(status_code=400, detail="invalid permission_scope")
    mentee = email if body.my_role == "mentee" else body.counterpart_email
    mentor = body.counterpart_email if body.my_role == "mentee" else email
    rid = uuid.uuid4().hex
    if body.org_id:
        _assert_org_member(email, body.org_id)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO mentor_relationships (id, mentee_email, mentor_email, relationship_type, permission_scope, start_date, org_id) "
                "VALUES (%s,%s,%s,%s,%s,(NOW() AT TIME ZONE 'Asia/Shanghai')::date,%s)",
                (rid, mentee, mentor, body.relationship_type, body.permission_scope, body.org_id),
            )
            conn.commit()
            cur.execute(f"SELECT {_REL_COLS} FROM mentor_relationships WHERE id=%s", (rid,))
            row = cur.fetchone()
    except HTTPException:
        raise
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        print(f"[mentor] create_rel failed: {exc!r}", flush=True)
        raise HTTPException(status_code=500, detail="create failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "relationship": _rel_row(row, to_iso)}


@router.get("/relationships")
def list_rels(request: Request) -> dict:
    user = _require_user(request); to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_REL_COLS} FROM mentor_relationships WHERE mentee_email=%s OR mentor_email=%s "
                        "ORDER BY created_at DESC", (user["email"], user["email"]))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    me = user["email"]
    return {"ok": True, "relationships": [{**_rel_row(r, to_iso), "my_role": ("mentee" if r[1] == me else "mentor")} for r in rows]}


class RelUpdate(BaseModel):
    status: Optional[str] = Field(default=None, max_length=12)
    permission_scope: Optional[str] = Field(default=None, max_length=24)


@router.patch("/relationships/{rid}")
def update_rel(rid: str, request: Request, body: RelUpdate) -> dict:
    user = _require_user(request)
    sets, params = [], []
    if body.status is not None: sets.append("status=%s"); params.append(body.status)
    if body.permission_scope is not None: sets.append("permission_scope=%s"); params.append(body.permission_scope)
    if not sets:
        return {"ok": True, "unchanged": True}
    sets.append("updated_at=NOW()"); params.extend([rid, user["email"], user["email"]])
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE mentor_relationships SET {', '.join(sets)} WHERE id=%s AND (mentee_email=%s OR mentor_email=%s)", tuple(params))
            conn.commit(); n = cur.rowcount
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="update failed")
    finally:
        _state["release_db"](conn)
    if not n:
        raise HTTPException(status_code=404, detail="relationship not found or no permission")
    return {"ok": True}


class SessionCreate(BaseModel):
    session_type: str = Field(default="checkin", max_length=24)
    agenda: List[str] = Field(default_factory=list)
    summary: str = Field(default="", max_length=8000)
    prayer_notes: str = Field(default="", max_length=4000)
    action_items: List[str] = Field(default_factory=list)
    status: str = Field(default="planned", max_length=12)


@router.post("/relationships/{rid}/sessions")
def create_session(rid: str, request: Request, body: SessionCreate) -> dict:
    user = _require_user(request); to_iso = _state["to_shanghai_iso"]
    sid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            rel = _party(cur, rid, user["email"])
            if not rel:
                raise HTTPException(status_code=404, detail="relationship not found or no permission")
            cur.execute(
                "INSERT INTO mentor_sessions (id, relationship_id, mentee_email, mentor_email, session_type, agenda, "
                "summary, prayer_notes, action_items, status) VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s::jsonb,%s)",
                (sid, rid, rel[1], rel[2], body.session_type, json.dumps(body.agenda, ensure_ascii=False),
                 body.summary, body.prayer_notes, json.dumps(body.action_items, ensure_ascii=False), body.status),
            )
            conn.commit()
            cur.execute(f"SELECT {_SES_COLS} FROM mentor_sessions WHERE id=%s", (sid,))
            row = cur.fetchone()
    except HTTPException:
        raise
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="create failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "session": _ses_row(row, to_iso)}


@router.get("/relationships/{rid}/sessions")
def list_sessions(rid: str, request: Request) -> dict:
    user = _require_user(request); to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if not _party(cur, rid, user["email"]):
                raise HTTPException(status_code=404, detail="no permission")
            cur.execute(f"SELECT {_SES_COLS} FROM mentor_sessions WHERE relationship_id=%s ORDER BY session_date DESC", (rid,))
            rows = cur.fetchall()
    except HTTPException:
        raise
    finally:
        _state["release_db"](conn)
    return {"ok": True, "sessions": [_ses_row(r, to_iso) for r in rows]}


class SessionUpdate(BaseModel):
    summary: Optional[str] = Field(default=None, max_length=8000)
    prayer_notes: Optional[str] = Field(default=None, max_length=4000)
    status: Optional[str] = Field(default=None, max_length=12)


@router.patch("/sessions/{sid}")
def update_session(sid: str, request: Request, body: SessionUpdate) -> dict:
    user = _require_user(request)
    sets, params = [], []
    if body.summary is not None: sets.append("summary=%s"); params.append(body.summary)
    if body.prayer_notes is not None: sets.append("prayer_notes=%s"); params.append(body.prayer_notes)
    if body.status is not None: sets.append("status=%s"); params.append(body.status)
    if not sets:
        return {"ok": True, "unchanged": True}
    sets.append("updated_at=NOW()"); params.extend([sid, user["email"], user["email"]])
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE mentor_sessions SET {', '.join(sets)} WHERE id=%s AND (mentee_email=%s OR mentor_email=%s)", tuple(params))
            conn.commit(); n = cur.rowcount
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="update failed")
    finally:
        _state["release_db"](conn)
    if not n:
        raise HTTPException(status_code=404, detail="session not found or no permission")
    return {"ok": True}


class ObsCreate(BaseModel):
    observation_type: str = Field(default="encouragement", max_length=24)
    title: str = Field(..., max_length=200)
    description: str = Field(default="", max_length=4000)
    recommended_next_step: str = Field(default="", max_length=2000)
    visible_to_mentee: bool = Field(default=True)


@router.post("/relationships/{rid}/observations")
def add_obs(rid: str, request: Request, body: ObsCreate) -> dict:
    user = _require_user(request)
    oid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            rel = _party(cur, rid, user["email"])
            if not rel:
                raise HTTPException(status_code=404, detail="no permission")
            cur.execute(
                "INSERT INTO mentor_growth_observations (id, relationship_id, mentee_email, mentor_email, observation_type, "
                "title, description, recommended_next_step, visible_to_mentee) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (oid, rid, rel[1], rel[2], body.observation_type, body.title, body.description,
                 body.recommended_next_step, body.visible_to_mentee),
            )
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="create failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": oid}


@router.get("/relationships/{rid}/observations")
def list_obs(rid: str, request: Request) -> dict:
    user = _require_user(request); to_iso = _state["to_shanghai_iso"]; email = user["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            rel = _party(cur, rid, email)
            if not rel:
                raise HTTPException(status_code=404, detail="no permission")
            is_mentee = rel[1] == email
            if is_mentee:
                cur.execute("SELECT id, observation_type, title, description, recommended_next_step, observation_date, visible_to_mentee "
                            "FROM mentor_growth_observations WHERE relationship_id=%s AND visible_to_mentee=TRUE ORDER BY observation_date DESC", (rid,))
            else:
                cur.execute("SELECT id, observation_type, title, description, recommended_next_step, observation_date, visible_to_mentee "
                            "FROM mentor_growth_observations WHERE relationship_id=%s ORDER BY observation_date DESC", (rid,))
            rows = cur.fetchall()
    except HTTPException:
        raise
    finally:
        _state["release_db"](conn)
    return {"ok": True, "observations": [
        {"id": r[0], "observation_type": r[1], "title": r[2], "description": r[3] or "",
         "recommended_next_step": r[4] or "", "observation_date": str(r[5]), "visible_to_mentee": bool(r[6])} for r in rows
    ]}


@router.get("/questions")
def list_questions(request: Request, category: str = Query(default="", max_length=20)) -> dict:
    _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if category:
                cur.execute("SELECT id, question_text, question_category FROM mentor_questions WHERE active=TRUE AND question_category=%s ORDER BY sort_order", (category,))
            else:
                cur.execute("SELECT id, question_text, question_category FROM mentor_questions WHERE active=TRUE ORDER BY sort_order")
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "questions": [{"id": r[0], "question_text": r[1], "question_category": r[2]} for r in rows]}


class RecommendBody(BaseModel):
    session_type: str = Field(default="checkin", max_length=24)


@router.post("/recommend")
def recommend(request: Request, body: RecommendBody) -> dict:
    _require_user(request)
    cats, agenda = _RECO.get(body.session_type, _RECO["checkin"])
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT question_text FROM mentor_questions WHERE active=TRUE AND question_category IN %s ORDER BY sort_order", (tuple(cats),))
            qs = [r[0] for r in cur.fetchall()]
    finally:
        _state["release_db"](conn)
    return {"ok": True, "session_type": body.session_type, "suggested_agenda": agenda,
            "suggested_questions": qs[:5],
            "cautions": ["不要索取超出同意范围的隐私细节。", "若出现危机/虐待迹象，升级到牧养或危机陪伴，而非自行处理。"]}


class PlanCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: str = Field(default="", max_length=4000)
    plan_type: str = Field(default="habit", max_length=20)
    actions: List[str] = Field(default_factory=list)


@router.post("/relationships/{rid}/action-plans")
def create_plan(rid: str, request: Request, body: PlanCreate) -> dict:
    user = _require_user(request)
    pid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            rel = _party(cur, rid, user["email"])
            if not rel:
                raise HTTPException(status_code=404, detail="no permission")
            cur.execute(
                "INSERT INTO mentor_action_plans (id, relationship_id, mentee_email, mentor_email, title, description, plan_type, actions) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
                (pid, rid, rel[1], rel[2], body.title, body.description, body.plan_type, json.dumps(body.actions, ensure_ascii=False)),
            )
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="create failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "plan_id": pid}


@router.get("/relationships/{rid}/action-plans")
def list_plans(rid: str, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if not _party(cur, rid, user["email"]):
                raise HTTPException(status_code=404, detail="no permission")
            cur.execute("SELECT id, title, description, plan_type, actions, status, review_date FROM mentor_action_plans "
                        "WHERE relationship_id=%s ORDER BY created_at DESC", (rid,))
            rows = cur.fetchall()
    except HTTPException:
        raise
    finally:
        _state["release_db"](conn)
    return {"ok": True, "plans": [
        {"id": r[0], "title": r[1], "description": r[2] or "", "plan_type": r[3],
         "actions": _jl(r[4]), "status": r[5], "review_date": str(r[6]) if r[6] else ""} for r in rows
    ]}


@router.post("/relationships/{rid}/review")
def review(rid: str, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if not _party(cur, rid, user["email"]):
                raise HTTPException(status_code=404, detail="no permission")
            cur.execute("SELECT COUNT(*) FROM mentor_sessions WHERE relationship_id=%s AND status='completed'", (rid,))
            sessions = cur.fetchone()[0] or 0
            cur.execute("SELECT COUNT(*) FROM mentor_growth_observations WHERE relationship_id=%s AND observation_type='concern'", (rid,))
            concerns = cur.fetchone()[0] or 0
            cur.execute("SELECT COUNT(*) FROM mentor_action_plans WHERE relationship_id=%s AND status='active'", (rid,))
            plans = cur.fetchone()[0] or 0
    except HTTPException:
        raise
    finally:
        _state["release_db"](conn)
    summary = []
    if sessions:
        summary.append(f"已完成 {sessions} 次会面，关系在持续。")
    else:
        summary.append("还没有完成的会面——可以从一次低压力的祷告与聆听开始。")
    if plans:
        summary.append(f"有 {plans} 个进行中的行动计划。")
    escalation = concerns >= 2
    if escalation:
        summary.append("出现多处关注信号:考虑升级到牧养或专业支持。")
    return {"ok": True, "summary": " ".join(summary),
            "stats": {"completed_sessions": sessions, "active_plans": plans, "concerns": concerns},
            "escalation_recommended": escalation}
