"""
Prayer Rule router — 固定祷告规则 / 每日祷告节奏 (/api/prayer-rule)

  GET  /api/prayer-rule/templates           祷告模板库
  POST /api/prayer-rule/rules               创建规则
  POST /api/prayer-rule/rules/default       一键创建初学者默认规则（晨/午/晚）
  GET  /api/prayer-rule/rules/active        当前规则 + 时段
  POST /api/prayer-rule/rules/{rid}/slots   添加时段
  PATCH/api/prayer-rule/slots/{sid}         更新时段
  POST /api/prayer-rule/sessions            开始一次祷告（{slot_id}）
  POST /api/prayer-rule/sessions/{sid}/complete  完成（感恩/认罪/祈求/恩典）
  GET  /api/prayer-rule/today               今日节奏与完成状态
  GET  /api/prayer-rule/review              温柔的每周回顾（错过不定罪）

焦点是与神相交，不是表现；错过不羞辱，鼓励小而稳，必要时建议减负。email 标识用户。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/prayer-rule", tags=["prayer-rule"])

_state: Dict[str, Any] = {}

_DEFAULT_SLOTS = [
    ("morning", "晨祷 · 交托", "07:00", 5, "pt_morning", 0),
    ("midday", "午间 · 临在", "12:30", 2, "pt_midday", 1),
    ("evening", "晚祷 · 感恩与安息", "21:30", 7, "pt_evening", 2),
]
_SLOT_COLS = ("id, email, rule_id, slot_key, display_name, target_time, duration_minutes, "
              "template_id, enabled, sort_order")
_SESSION_COLS = ("id, email, rule_id, slot_id, session_date, started_at, completed_at, duration_minutes, "
                 "prayer_text, gratitude_items, confession_items, petitions, grace_received, status, created_at")


def init_prayer_rule_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
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


def _slot_row(r) -> dict:
    return {"id": r[0], "rule_id": r[2], "slot_key": r[3], "display_name": r[4],
            "target_time": str(r[5])[:5] if r[5] else "", "duration_minutes": r[6],
            "template_id": r[7] or "", "enabled": bool(r[8]), "sort_order": r[9]}


def _session_row(r, to_iso) -> dict:
    return {"id": r[0], "rule_id": r[2] or "", "slot_id": r[3] or "",
            "session_date": str(r[4]) if r[4] else "", "started_at": to_iso(r[5]) if r[5] else None,
            "completed_at": to_iso(r[6]) if r[6] else None, "duration_minutes": r[7],
            "prayer_text": r[8] or "", "gratitude_items": _jl(r[9]), "confession_items": _jl(r[10]),
            "petitions": _jl(r[11]), "grace_received": r[12] or "", "status": r[13] or "started",
            "created_at": to_iso(r[14])}


@router.get("/templates")
def list_templates(request: Request) -> dict:
    _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, tradition_tag, template_type, body, scripture_refs "
                        "FROM prayer_templates WHERE public=TRUE ORDER BY id")
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "templates": [
        {"id": r[0], "title": r[1], "tradition_tag": r[2], "template_type": r[3],
         "body": r[4] or "", "scripture_refs": _jl(r[5])} for r in rows
    ]}


class RuleCreate(BaseModel):
    title: str = Field(default="我的祷告规则", max_length=120)
    description: str = Field(default="", max_length=2000)
    rule_type: str = Field(default="daily", max_length=20)


def _create_rule(cur, email, title, description, rule_type) -> str:
    rid = uuid.uuid4().hex
    cur.execute("UPDATE prayer_rules SET active=FALSE WHERE email=%s AND active=TRUE", (email,))
    cur.execute("INSERT INTO prayer_rules (id, email, title, description, rule_type, active) "
                "VALUES (%s,%s,%s,%s,%s,TRUE)", (rid, email, title, description, rule_type))
    return rid


@router.post("/rules")
def create_rule(request: Request, body: RuleCreate) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            rid = _create_rule(cur, user["email"], body.title, body.description, body.rule_type)
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "rule_id": rid}


@router.post("/rules/default")
def create_default_rule(request: Request) -> dict:
    user = _require_user(request)
    email = user["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            rid = _create_rule(cur, email, "初学者祷告规则", "小而稳的每日祷告节奏：晨祷交托、午间临在、晚祷感恩。", "daily")
            for slot_key, name, t, dur, tpl, order in _DEFAULT_SLOTS:
                cur.execute(
                    "INSERT INTO prayer_rule_slots (id, email, rule_id, slot_key, display_name, target_time, duration_minutes, template_id, sort_order) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (uuid.uuid4().hex, email, rid, slot_key, name, t, dur, tpl, order),
                )
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "rule_id": rid}


def _active_rule_with_slots(cur, email):
    cur.execute("SELECT id, title, description, rule_type FROM prayer_rules WHERE email=%s AND active=TRUE "
                "ORDER BY created_at DESC LIMIT 1", (email,))
    rule = cur.fetchone()
    if not rule:
        return None, []
    cur.execute(f"SELECT {_SLOT_COLS} FROM prayer_rule_slots WHERE rule_id=%s AND enabled=TRUE ORDER BY sort_order", (rule[0],))
    slots = [_slot_row(r) for r in cur.fetchall()]
    return rule, slots


@router.get("/rules/active")
def active_rule(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            rule, slots = _active_rule_with_slots(cur, user["email"])
    finally:
        _state["release_db"](conn)
    if not rule:
        return {"ok": True, "rule": None}
    return {"ok": True, "rule": {"id": rule[0], "title": rule[1], "description": rule[2] or "", "rule_type": rule[3], "slots": slots}}


class SlotCreate(BaseModel):
    slot_key: str = Field(default="custom", max_length=24)
    display_name: str = Field(..., max_length=80)
    target_time: str = Field(default="", max_length=8)
    duration_minutes: int = Field(default=5, ge=1, le=180)
    template_id: str = Field(default="", max_length=64)
    sort_order: int = Field(default=0)


@router.post("/rules/{rid}/slots")
def add_slot(rid: str, request: Request, body: SlotCreate) -> dict:
    user = _require_user(request)
    sid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM prayer_rules WHERE id=%s AND email=%s", (rid, user["email"]))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="rule not found")
            cur.execute(
                "INSERT INTO prayer_rule_slots (id, email, rule_id, slot_key, display_name, target_time, duration_minutes, template_id, sort_order) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (sid, user["email"], rid, body.slot_key, body.display_name,
                 body.target_time or None, body.duration_minutes, body.template_id, body.sort_order),
            )
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "slot_id": sid}


class SlotUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=80)
    target_time: Optional[str] = Field(default=None, max_length=8)
    duration_minutes: Optional[int] = Field(default=None, ge=1, le=180)
    enabled: Optional[bool] = None


@router.patch("/slots/{sid}")
def update_slot(sid: str, request: Request, body: SlotUpdate) -> dict:
    user = _require_user(request)
    sets, params = [], []
    if body.display_name is not None: sets.append("display_name=%s"); params.append(body.display_name)
    if body.target_time is not None: sets.append("target_time=%s"); params.append(body.target_time or None)
    if body.duration_minutes is not None: sets.append("duration_minutes=%s"); params.append(body.duration_minutes)
    if body.enabled is not None: sets.append("enabled=%s"); params.append(body.enabled)
    if not sets:
        return {"ok": True, "unchanged": True}
    sets.append("updated_at=NOW()")
    params.extend([sid, user["email"]])
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE prayer_rule_slots SET {', '.join(sets)} WHERE id=%s AND email=%s", tuple(params))
            conn.commit()
            n = cur.rowcount
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"update failed: {exc}")
    finally:
        _state["release_db"](conn)
    if not n:
        raise HTTPException(status_code=404, detail="slot not found")
    return {"ok": True}


class SessionStart(BaseModel):
    slot_id: str = Field(default="", max_length=64)
    rule_id: str = Field(default="", max_length=64)


@router.post("/sessions")
def start_session(request: Request, body: SessionStart) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    sid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO prayer_rule_sessions (id, email, rule_id, slot_id, session_date, started_at, status) "
                "VALUES (%s,%s,%s,%s,(NOW() AT TIME ZONE 'Asia/Shanghai')::date, NOW(), 'started')",
                (sid, user["email"], body.rule_id, body.slot_id),
            )
            conn.commit()
            cur.execute(f"SELECT {_SESSION_COLS} FROM prayer_rule_sessions WHERE id=%s", (sid,))
            row = cur.fetchone()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"start failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "session": _session_row(row, to_iso)}


class SessionComplete(BaseModel):
    prayer_text: str = Field(default="", max_length=8000)
    gratitude_items: List[str] = Field(default_factory=list)
    confession_items: List[str] = Field(default_factory=list)
    petitions: List[str] = Field(default_factory=list)
    grace_received: str = Field(default="", max_length=2000)
    duration_minutes: Optional[int] = Field(default=None, ge=0, le=600)


@router.post("/sessions/{sid}/complete")
def complete_session(sid: str, request: Request, body: SessionComplete) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE prayer_rule_sessions SET status='completed', completed_at=NOW(), prayer_text=%s, "
                "gratitude_items=%s::jsonb, confession_items=%s::jsonb, petitions=%s::jsonb, "
                "grace_received=%s, duration_minutes=%s, updated_at=NOW() WHERE id=%s AND email=%s",
                (body.prayer_text,
                 json.dumps(body.gratitude_items, ensure_ascii=False),
                 json.dumps(body.confession_items, ensure_ascii=False),
                 json.dumps(body.petitions, ensure_ascii=False),
                 body.grace_received, body.duration_minutes, sid, user["email"]),
            )
            if not cur.rowcount:
                raise HTTPException(status_code=404, detail="session not found")
            conn.commit()
            cur.execute(f"SELECT {_SESSION_COLS} FROM prayer_rule_sessions WHERE id=%s", (sid,))
            row = cur.fetchone()
    except HTTPException:
        raise
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"complete failed: {exc}")
    finally:
        _state["release_db"](conn)
    try:
        from formation_bridge import record_formation
        record_formation(user.get("id"), ["spiritual", "growth"], reflection_active=True, decision_category="prayer_rule")
    except Exception:
        pass
    out = {"ok": True, "session": _session_row(row, to_iso),
           "encouragement": "你与神相交的一刻是真实的。祷告是相交，不是表现——无论长短，神都看为宝贵。"}
    try:
        from safety_scan import scan_crisis
        c = scan_crisis(body.prayer_text, body.grace_received)
        if c: out["crisis"] = c
    except Exception:
        pass
    return out


@router.get("/today")
def today(request: Request) -> dict:
    user = _require_user(request)
    email = user["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            rule, slots = _active_rule_with_slots(cur, email)
            done = set()
            if rule:
                cur.execute(
                    "SELECT slot_id FROM prayer_rule_sessions WHERE email=%s AND status='completed' "
                    "AND session_date=(NOW() AT TIME ZONE 'Asia/Shanghai')::date", (email,))
                done = {r[0] for r in cur.fetchall()}
    finally:
        _state["release_db"](conn)
    if not rule:
        return {"ok": True, "rule": None, "slots": [], "hint": "还没有祷告规则。可一键创建初学者规则（晨/午/晚）。"}
    plan = [{**s, "completed_today": s["id"] in done} for s in slots]
    return {"ok": True, "rule_id": rule[0], "rule_title": rule[1], "slots": plan,
            "completed_count": sum(1 for s in plan if s["completed_today"]), "total": len(plan)}


@router.get("/review")
def review(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM prayer_rule_sessions WHERE email=%s AND status='completed' "
                        "AND session_date >= (NOW() AT TIME ZONE 'Asia/Shanghai')::date - INTERVAL '7 days'", (user["email"],))
            completed = cur.fetchone()[0] or 0
            rule, slots = _active_rule_with_slots(cur, user["email"])
    finally:
        _state["release_db"](conn)
    expected = (len(slots) * 7) if slots else 0
    insights = []
    if expected and completed <= expected * 0.3:
        insights.append("这周完成得不多，没关系——这不是评分。也许规则偏重了，可以先把它减到一个晨祷与一句睡前感恩。")
    elif completed > 0:
        insights.append("这周你回到了与神相交的节奏，哪怕只是几次，都是恩典里的忠心。")
    else:
        insights.append("新的一周，可以从最小的一步开始：早晨一句「父啊，我把今天交给你」。")
    return {"ok": True, "summary": {"completed_7d": completed, "expected_7d": expected}, "insights": insights}
