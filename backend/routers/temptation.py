"""
Temptation Resistance router — 试探抵抗 (/api/temptation)

  GET  /api/temptation/types                试探类型库
  POST /api/temptation/resist               即时抵抗引导（逃离 + 替代 + 经文 + 监督）
  POST /api/temptation/plans                创建抵抗计划
  GET  /api/temptation/plans                列出计划
  GET  /api/temptation/plans/{id}           计划详情
  PATCH/api/temptation/plans/{id}           更新计划
  POST /api/temptation/checkins             记录一次试探 check-in（结果）
  POST /api/temptation/checkins/{id}/failure-review  失败后温柔复盘，导向认罪

原则：试探≠罪；不羞辱、不自惩；不索取露骨细节；成瘾导向人帮助；
绝望/危机导向危机陪伴；失败温柔导向 /api/confession。email 标识用户。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/temptation", tags=["temptation"])

_state: Dict[str, Any] = {}

_GENERIC_ESCAPE = ["离开当前的房间 5 分钟", "把触发的设备 / 物品放远", "出门走一走", "给一位守望人发一句：我现在需要陪伴"]
_GENERIC_REPLACE = ["大声读一节经文（如 诗 23:1）", "喝一杯水，做 60 秒呼吸", "做一件有用的小事 5 分钟"]

_T_COLS = "type_key, display_name, description, common_triggers, escape_principles, opposite_virtues, scripture_refs"
_PLAN_COLS = ("id, email, title, temptation_type_key, status, vulnerable_contexts, early_warning_signs, "
              "escape_actions, replacement_actions, scripture_anchors, accountability_contacts, created_at")
_CHK_COLS = ("id, email, plan_id, checked_in_at, context_label, intensity_before, intensity_after, "
             "trigger_text, chosen_escape_action, chosen_replacement_action, outcome, notes")


def init_temptation_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
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


def _plan_row(r, to_iso) -> dict:
    return {"id": r[0], "title": r[2], "temptation_type_key": r[3] or "", "status": r[4],
            "vulnerable_contexts": _jl(r[5]), "early_warning_signs": _jl(r[6]),
            "escape_actions": _jl(r[7]), "replacement_actions": _jl(r[8]),
            "scripture_anchors": _jl(r[9]), "accountability_contacts": _jl(r[10]),
            "created_at": to_iso(r[11])}


@router.get("/types")
def list_types(request: Request) -> dict:
    _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_T_COLS} FROM temptation_types WHERE active=TRUE ORDER BY sort_order")
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "types": [
        {"type_key": r[0], "display_name": r[1], "description": r[2] or "",
         "common_triggers": _jl(r[3]), "escape_principles": _jl(r[4]),
         "opposite_virtues": _jl(r[5]), "scripture_refs": _jl(r[6])} for r in rows
    ]}


class ResistBody(BaseModel):
    text: str = Field(default="", max_length=4000)
    type_key: str = Field(default="", max_length=40)
    context_label: str = Field(default="", max_length=40)
    intensity: Optional[int] = Field(default=None, ge=0, le=10)


@router.post("/resist")
def resist(request: Request, body: ResistBody) -> dict:
    _require_user(request)
    # 危机/绝望优先
    try:
        from safety_scan import scan_crisis
        crisis = scan_crisis(body.text)
    except Exception:
        crisis = None
    if crisis or body.type_key == "despair":
        return {"ok": True, "route": "crisis_care", "block_normal": True,
                "message": "你此刻的重担很重要，安全比战胜冲动更优先。请现在联系一位信任的人，或在「危机陪伴」获得即时支持。",
                "next_endpoint": "/api/crisis", "crisis": crisis}

    escape, virtues, scripture = list(_GENERIC_ESCAPE), [], "林前10:13"
    if body.type_key:
        conn = _state["get_db"]()
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT {_T_COLS} FROM temptation_types WHERE type_key=%s", (body.type_key,))
                r = cur.fetchone()
        finally:
            _state["release_db"](conn)
        if r:
            ep = _jl(r[4]); escape = ep or escape
            virtues = _jl(r[5])
            refs = _jl(r[6]); scripture = refs[0] if refs else scripture

    high = (body.intensity or 0) >= 7
    return {"ok": True, "route": "temptation_resistance", "block_normal": False,
            "message": "这是试探的一刻，不是你的身份。你不必赢得整场战争，只需把这一步交托给神。",
            "first_step": "停下来，把身体从触发点移开。",
            "escape_actions": escape,
            "replacement_actions": _GENERIC_REPLACE,
            "opposite_virtues": virtues,
            "scripture_anchor": scripture,
            "accountability_suggestion": ("强度较高时，现在就给一位成熟的信徒发条消息——这不是软弱，是智慧。" if high
                                          else "若强度上升到 7/10 以上，给一位守望人发条消息。"),
            "next_endpoint": "/api/temptation/checkins"}


class PlanCreate(BaseModel):
    title: str = Field(..., max_length=160)
    temptation_type_key: str = Field(default="", max_length=40)
    vulnerable_contexts: List[str] = Field(default_factory=list)
    early_warning_signs: List[str] = Field(default_factory=list)
    escape_actions: List[str] = Field(default_factory=list)
    replacement_actions: List[str] = Field(default_factory=list)
    scripture_anchors: List[str] = Field(default_factory=list)
    accountability_contacts: List[str] = Field(default_factory=list)


@router.post("/plans")
def create_plan(request: Request, body: PlanCreate) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    pid = uuid.uuid4().hex
    j = lambda x: json.dumps(x, ensure_ascii=False)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO temptation_plans (id, email, title, temptation_type_key, vulnerable_contexts, "
                "early_warning_signs, escape_actions, replacement_actions, scripture_anchors, accountability_contacts) "
                "VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb)",
                (pid, user["email"], body.title, body.temptation_type_key, j(body.vulnerable_contexts),
                 j(body.early_warning_signs), j(body.escape_actions), j(body.replacement_actions),
                 j(body.scripture_anchors), j(body.accountability_contacts)),
            )
            conn.commit()
            cur.execute(f"SELECT {_PLAN_COLS} FROM temptation_plans WHERE id=%s", (pid,))
            row = cur.fetchone()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "plan": _plan_row(row, to_iso)}


@router.get("/plans")
def list_plans(request: Request) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_PLAN_COLS} FROM temptation_plans WHERE email=%s AND status='active' "
                        "ORDER BY created_at DESC", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "plans": [_plan_row(r, to_iso) for r in rows]}


@router.get("/plans/{pid}")
def get_plan(pid: str, request: Request) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_PLAN_COLS} FROM temptation_plans WHERE id=%s AND email=%s", (pid, user["email"]))
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not row:
        raise HTTPException(status_code=404, detail="plan not found")
    return {"ok": True, "plan": _plan_row(row, to_iso)}


class PlanUpdate(BaseModel):
    status: Optional[str] = Field(default=None, max_length=12)
    title: Optional[str] = Field(default=None, max_length=160)


@router.patch("/plans/{pid}")
def update_plan(pid: str, request: Request, body: PlanUpdate) -> dict:
    user = _require_user(request)
    sets, params = [], []
    if body.status is not None: sets.append("status=%s"); params.append(body.status)
    if body.title is not None: sets.append("title=%s"); params.append(body.title)
    if not sets:
        return {"ok": True, "unchanged": True}
    sets.append("updated_at=NOW()")
    params.extend([pid, user["email"]])
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE temptation_plans SET {', '.join(sets)} WHERE id=%s AND email=%s", tuple(params))
            conn.commit()
            n = cur.rowcount
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"update failed: {exc}")
    finally:
        _state["release_db"](conn)
    if not n:
        raise HTTPException(status_code=404, detail="plan not found")
    return {"ok": True}


class CheckinCreate(BaseModel):
    plan_id: str = Field(default="", max_length=64)
    context_label: str = Field(default="", max_length=40)
    intensity_before: Optional[int] = Field(default=None, ge=0, le=10)
    intensity_after: Optional[int] = Field(default=None, ge=0, le=10)
    trigger_text: str = Field(default="", max_length=2000)
    chosen_escape_action: str = Field(default="", max_length=500)
    chosen_replacement_action: str = Field(default="", max_length=500)
    outcome: str = Field(default="still_struggling", max_length=20)
    notes: str = Field(default="", max_length=2000)


@router.post("/checkins")
def create_checkin(request: Request, body: CheckinCreate) -> dict:
    user = _require_user(request)
    cid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO temptation_checkins (id, email, plan_id, context_label, intensity_before, intensity_after, "
                "trigger_text, chosen_escape_action, chosen_replacement_action, outcome, notes) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (cid, user["email"], body.plan_id, body.context_label, body.intensity_before, body.intensity_after,
                 body.trigger_text, body.chosen_escape_action, body.chosen_replacement_action, body.outcome, body.notes),
            )
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    out = {"ok": True, "id": cid}
    if body.outcome in ("resisted", "escaped"):
        out["encouragement"] = "你选择了忠心的一步——这是恩典里的得胜，值得记念。"
        try:
            from formation_bridge import record_formation
            record_formation(user.get("id"), ["growth"], loop_broken=True, decision_category="temptation")
        except Exception:
            pass
    elif body.outcome == "failed":
        out["grace_route"] = {"message": "失败很痛，但它不是你的身份，也不是终点。来到神面前，领受赦免，重新开始。",
                              "next_endpoint": "/api/confession"}
    try:
        from safety_scan import scan_crisis
        c = scan_crisis(body.trigger_text, body.notes)
        if c: out["crisis"] = c
    except Exception:
        pass
    return out


class FailureReview(BaseModel):
    checkin_id: str = Field(default="", max_length=64)
    what_happened: str = Field(default="", max_length=4000)
    trigger_chain: List[str] = Field(default_factory=list)
    shame_level: Optional[int] = Field(default=None, ge=0, le=10)
    next_plan_adjustment: str = Field(default="", max_length=2000)


@router.post("/checkins/{cid}/failure-review")
def failure_review(cid: str, request: Request, body: FailureReview) -> dict:
    user = _require_user(request)
    rid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO temptation_failure_reviews (id, email, checkin_id, what_happened, trigger_chain, shame_level, next_plan_adjustment) "
                "VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s)",
                (rid, user["email"], cid or body.checkin_id, body.what_happened,
                 json.dumps(body.trigger_chain, ensure_ascii=False), body.shame_level, body.next_plan_adjustment),
            )
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"review failed: {exc}")
    finally:
        _state["release_db"](conn)
    out = {"ok": True, "id": rid,
           "message": "谢谢你诚实面对。复盘是为了学习，不是为了定罪。在基督里没有定罪（罗 8:1）。",
           "grace_route": {"title": "领受赦免，重新开始", "next_endpoint": "/api/confession"}}
    if (body.shame_level or 0) >= 8:
        out["pastoral_note"] = "羞耻感很强时，独自循环容易越陷越深。考虑找一位成熟的牧者或弟兄姊妹同行。"
    return out
