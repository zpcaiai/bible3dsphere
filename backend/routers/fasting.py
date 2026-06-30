"""
Fasting & Simplicity router — 禁食与简朴操练 (/api/fasting)

  GET  /api/fasting/practices            操练库
  POST /api/fasting/recommend            按成长需要推荐禁食/简朴操练
  POST /api/fasting/plans                创建禁食计划（食物禁食有安全闸）
  GET  /api/fasting/plans/active         当前计划
  PATCH/api/fasting/plans/{id}           更新计划
  POST /api/fasting/plans/{id}/checkins  禁食中 check-in（欲望/祷告/洞见）
  POST /api/fasting/plans/{id}/review    禁食回顾
  POST /api/fasting/simplicity/audit     简朴审视（检测消费主义 + 推荐）
  GET  /api/fasting/simplicity/audit/latest
  POST /api/fasting/simplicity/actions   简朴行动
  PATCH/api/fasting/simplicity/actions/{id}

安全第一：不施压食物禁食；进食障碍/孕期/糖尿病/服药/体弱/减重动机 → 禁止食物禁食、改非食物。
食物禁食必须 health_acknowledgement=true。简朴是为了爱与自由，不夸耀、不极端。email 标识用户。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/fasting", tags=["fasting"])

_state: Dict[str, Any] = {}

_UNSAFE = ["进食障碍", "厌食", "暴食症", "催吐", "孕", "怀孕", "糖尿", "胰岛素", "随餐服药", "晕倒", "昏倒",
           "体重过轻", "太瘦", "减肥", "瘦身", "惩罚自己", "不配吃", "eating disorder", "anorexia", "bulimia",
           "pregnan", "diabet", "insulin", "faint", "underweight", "lose weight", "weight loss", "punish"]
_NONFOOD_ALTS = ["social_media_24h_fast", "phone_evening_fast", "spending_fast_one_week",
                 "speech_fast_half_day", "comfort_fast", "simplicity_audit", "generosity_response"]

_RECO = [
    (["分心", "社媒", "刷", "注意力", "distraction", "social"], ["social_media_24h_fast", "digital_declutter"]),
    (["消费", "购物", "攀比", "比较", "物质", "consumer", "compare"], ["spending_fast_one_week", "simplicity_audit", "generosity_response"]),
    (["怒", "言语", "说话", "八卦", "anger", "speech", "gossip"], ["speech_fast_half_day"]),
    (["舒适", "安逸", "comfort"], ["comfort_fast"]),
    (["贪", "物质主义", "greed", "material"], ["simplicity_audit", "generosity_response"]),
    (["麻木", "枯干", "空虚", "numb", "dry"], ["social_media_24h_fast", "entertainment_fast"]),
]
_BURNOUT = ["burnout", "耗竭", "累垮", "精疲力竭", "倦怠"]

_PRACTICE_COLS = "practice_key, title, description, fasting_type, difficulty, typical_duration, health_caution, formation_purpose"
_PLAN_COLS = ("id, email, practice_key, title, status, fasting_type, start_at, end_at, purpose, prayer_focus, "
              "simplicity_focus, generosity_response, health_acknowledgement, safety_flags, created_at")


def init_fasting_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
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


def _detect_unsafe(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in _UNSAFE)


def _validate_food_fast(title: str, purpose: str, health_ack: bool) -> Tuple[bool, str]:
    if _detect_unsafe(f"{title} {purpose}"):
        return False, "你提到的情况涉及健康风险，不建议食物禁食。可以改用非食物禁食（社媒/手机/消费/言语/舒适），同样能操练依靠与节制。"
    if not health_ack:
        return False, "食物禁食前需确认健康状况：若有进食障碍、孕期、糖尿病、需随餐服药、体弱，或以减重为主要动机，请勿食物禁食，改用非食物禁食并咨询医生。"
    return True, ""


def _practice(r) -> dict:
    return {"practice_key": r[0], "title": r[1], "description": r[2] or "", "fasting_type": r[3],
            "difficulty": r[4], "typical_duration": r[5] or "", "health_caution": r[6] or "",
            "formation_purpose": _jl(r[7])}


def _plan_row(r, to_iso) -> dict:
    return {"id": r[0], "practice_key": r[2] or "", "title": r[3], "status": r[4], "fasting_type": r[5],
            "start_at": to_iso(r[6]) if r[6] else None, "end_at": to_iso(r[7]) if r[7] else None,
            "purpose": r[8] or "", "prayer_focus": r[9] or "", "simplicity_focus": r[10] or "",
            "generosity_response": r[11] or "", "health_acknowledgement": bool(r[12]),
            "safety_flags": _jl(r[13]), "created_at": to_iso(r[14])}


@router.get("/practices")
def list_practices(request: Request) -> dict:
    _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_PRACTICE_COLS} FROM fasting_practices ORDER BY sort_order")
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "practices": [_practice(r) for r in rows]}


class RecommendBody(BaseModel):
    formation_need: str = Field(default="", max_length=200)
    health_context: str = Field(default="", max_length=400)


@router.post("/recommend")
def recommend(request: Request, body: RecommendBody) -> dict:
    _require_user(request)
    need = (body.formation_need or "").lower()
    if any(k in need for k in _BURNOUT):
        return {"ok": True, "practices": [], "redirect": "/api/sabbath",
                "message": "你正处于耗竭状态——此刻不宜强度禁食。先安息、减负，让身心灵恢复，比操练禁食更要紧。"}
    keys: List[str] = []
    for kws, ks in _RECO:
        if any(k in need for k in kws):
            keys.extend(ks)
    if not keys:
        keys = ["phone_evening_fast", "simplicity_audit"]
    avoid_food = _detect_unsafe(body.health_context)
    seen = set(); keys = [k for k in keys if not (k in seen or seen.add(k))]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_PRACTICE_COLS} FROM fasting_practices WHERE practice_key IN %s", (tuple(keys),))
            by = {r[0]: r for r in cur.fetchall()}
    finally:
        _state["release_db"](conn)
    practices = [_practice(by[k]) for k in keys if k in by and not (avoid_food and by[k][3] == "food")]
    return {"ok": True, "practices": practices,
            "note": "禁食是为了把欲望转向神、操练自由与慷慨，不是为了表现或律法。"}


class PlanCreate(BaseModel):
    practice_key: str = Field(default="", max_length=40)
    title: str = Field(..., max_length=160)
    fasting_type: str = Field(default="media", max_length=20)
    purpose: str = Field(default="", max_length=2000)
    prayer_focus: str = Field(default="", max_length=2000)
    simplicity_focus: str = Field(default="", max_length=2000)
    generosity_response: str = Field(default="", max_length=2000)
    duration_hours: int = Field(default=24, ge=1, le=720)
    health_acknowledgement: bool = Field(default=False)


@router.post("/plans")
def create_plan(request: Request, body: PlanCreate) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    # 安全闸：食物禁食
    if body.fasting_type == "food":
        ok, reason = _validate_food_fast(body.title, body.purpose, body.health_acknowledgement)
        if not ok:
            conn = _state["get_db"]()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT practice_key, title, fasting_type FROM fasting_practices WHERE practice_key IN %s", (tuple(_NONFOOD_ALTS),))
                    alts = [{"practice_key": r[0], "title": r[1], "fasting_type": r[2]} for r in cur.fetchall()]
            finally:
                _state["release_db"](conn)
            return {"ok": True, "created": False, "blocked": True, "reason": reason,
                    "safe_alternatives": alts, "require_health_acknowledgement": True}
    pid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO fasting_plans (id, email, practice_key, title, fasting_type, start_at, end_at, "
                "purpose, prayer_focus, simplicity_focus, generosity_response, health_acknowledgement) "
                "VALUES (%s,%s,%s,%s,%s, NOW(), NOW() + (%s || ' hours')::interval, %s,%s,%s,%s,%s)",
                (pid, user["email"], body.practice_key, body.title, body.fasting_type, str(body.duration_hours),
                 body.purpose, body.prayer_focus, body.simplicity_focus, body.generosity_response, body.health_acknowledgement),
            )
            conn.commit()
            cur.execute(f"SELECT {_PLAN_COLS} FROM fasting_plans WHERE id=%s", (pid,))
            row = cur.fetchone()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "created": True, "plan": _plan_row(row, to_iso)}


@router.get("/plans/active")
def active_plans(request: Request) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_PLAN_COLS} FROM fasting_plans WHERE email=%s AND status='active' ORDER BY created_at DESC", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "plans": [_plan_row(r, to_iso) for r in rows]}


class PlanUpdate(BaseModel):
    status: str = Field(..., max_length=12)


@router.patch("/plans/{pid}")
def update_plan(pid: str, request: Request, body: PlanUpdate) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE fasting_plans SET status=%s, updated_at=NOW() WHERE id=%s AND email=%s",
                        (body.status, pid, user["email"]))
            conn.commit(); n = cur.rowcount
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
    hunger_or_desire_level: Optional[int] = Field(default=None, ge=0, le=10)
    emotional_state: List[str] = Field(default_factory=list)
    temptation_or_resistance: str = Field(default="", max_length=2000)
    prayer_text: str = Field(default="", max_length=4000)
    desire_insight: str = Field(default="", max_length=2000)


@router.post("/plans/{pid}/checkins")
def add_checkin(pid: str, request: Request, body: CheckinCreate) -> dict:
    user = _require_user(request)
    cid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM fasting_plans WHERE id=%s AND email=%s", (pid, user["email"]))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="plan not found")
            cur.execute(
                "INSERT INTO fasting_checkins (id, email, fasting_plan_id, hunger_or_desire_level, emotional_state, "
                "temptation_or_resistance, prayer_text, desire_insight) VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s,%s)",
                (cid, user["email"], pid, body.hunger_or_desire_level,
                 json.dumps(body.emotional_state, ensure_ascii=False),
                 body.temptation_or_resistance, body.prayer_text, body.desire_insight),
            )
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"checkin failed: {exc}")
    finally:
        _state["release_db"](conn)
    out = {"ok": True, "id": cid,
           "note": "当欲望升起，把它当作转向神的提醒：「主，我真正渴望的是你。」"}
    try:
        from safety_scan import scan_crisis
        c = scan_crisis(body.temptation_or_resistance, body.desire_insight)
        if c: out["crisis"] = c
    except Exception:
        pass
    return out


class ReviewCreate(BaseModel):
    desire_patterns_noticed: List[str] = Field(default_factory=list)
    prayer_insights: List[str] = Field(default_factory=list)
    gratitude_insights: List[str] = Field(default_factory=list)
    generosity_completed: bool = Field(default=False)
    summary: str = Field(default="", max_length=4000)


@router.post("/plans/{pid}/review")
def add_review(pid: str, request: Request, body: ReviewCreate) -> dict:
    user = _require_user(request)
    rid = uuid.uuid4().hex
    legalism = "" if body.generosity_completed or body.gratitude_insights else \
        "留意：若禁食变成「我做到了」的自我满足，就偏离了它的目的。禁食是为了自由与爱，不是积分。"
    nxt = "把省下的资源或时间，转为对一个人的具体祝福。" if not body.generosity_completed else "继续在自由里操练慷慨与简朴。"
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM fasting_plans WHERE id=%s AND email=%s", (pid, user["email"]))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="plan not found")
            cur.execute(
                "INSERT INTO fasting_reviews (id, email, fasting_plan_id, review_date, desire_patterns_noticed, "
                "prayer_insights, gratitude_insights, generosity_completed, legalism_warning, recommended_next_step, summary) "
                "VALUES (%s,%s,%s,(NOW() AT TIME ZONE 'Asia/Shanghai')::date,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,%s,%s)",
                (rid, user["email"], pid, json.dumps(body.desire_patterns_noticed, ensure_ascii=False),
                 json.dumps(body.prayer_insights, ensure_ascii=False), json.dumps(body.gratitude_insights, ensure_ascii=False),
                 body.generosity_completed, legalism, nxt, body.summary),
            )
            cur.execute("UPDATE fasting_plans SET status='completed', updated_at=NOW() WHERE id=%s", (pid,))
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"review failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": rid, "legalism_warning": legalism, "recommended_next_step": nxt}


# ── 简朴 ──────────────────────────────────────────────────────────────────────

class SimplicityAudit(BaseModel):
    money_clutter_score: Optional[int] = Field(default=None, ge=0, le=10)
    possession_clutter_score: Optional[int] = Field(default=None, ge=0, le=10)
    schedule_clutter_score: Optional[int] = Field(default=None, ge=0, le=10)
    digital_clutter_score: Optional[int] = Field(default=None, ge=0, le=10)
    desire_pressure_score: Optional[int] = Field(default=None, ge=0, le=10)
    comparison_pressure_score: Optional[int] = Field(default=None, ge=0, le=10)
    identified_excesses: List[str] = Field(default_factory=list)
    gratitude_items: List[str] = Field(default_factory=list)


def _analyze_simplicity(scores: Dict[str, Optional[int]]) -> Dict[str, Any]:
    label = {"money_clutter_score": "金钱", "possession_clutter_score": "物品", "schedule_clutter_score": "日程",
             "digital_clutter_score": "数字", "desire_pressure_score": "欲望", "comparison_pressure_score": "比较"}
    idol = {"money_clutter_score": "security", "schedule_clutter_score": "productivity",
            "digital_clutter_score": "fear_of_missing_out", "comparison_pressure_score": "comparison",
            "desire_pressure_score": "pleasure", "possession_clutter_score": "security"}
    nonzero = {k: v for k, v in scores.items() if v is not None}
    if not nonzero:
        return {"dominant_clutter": None, "possible_idol": None,
                "recommended_action": "先为已有的恩典数算三件感恩。", "generosity_response": "把一件不用的东西送给需要的人。",
                "gratitude_practice": "说出三件你已经领受的礼物。"}
    dom = max(nonzero, key=lambda k: nonzero[k])
    return {"dominant_clutter": label.get(dom, dom), "possible_idol": idol.get(dom),
            "recommended_action": f"针对「{label.get(dom, dom)}」的过剩，迈出一个简化小步（如退订/清理/取消一笔购买）。",
            "generosity_response": "把省下的转为对一个人的祝福。",
            "gratitude_practice": "数算三件已经领受的礼物，让知足取代攀比。"}


@router.post("/simplicity/audit")
def simplicity_audit(request: Request, body: SimplicityAudit) -> dict:
    user = _require_user(request)
    scores = {"money_clutter_score": body.money_clutter_score, "possession_clutter_score": body.possession_clutter_score,
              "schedule_clutter_score": body.schedule_clutter_score, "digital_clutter_score": body.digital_clutter_score,
              "desire_pressure_score": body.desire_pressure_score, "comparison_pressure_score": body.comparison_pressure_score}
    analysis = _analyze_simplicity(scores)
    aid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO simplicity_audits (id, email, audit_date, money_clutter_score, possession_clutter_score, "
                "schedule_clutter_score, digital_clutter_score, desire_pressure_score, comparison_pressure_score, "
                "identified_excesses, gratitude_items, possible_generosity_actions, simplification_actions) "
                "VALUES (%s,%s,(NOW() AT TIME ZONE 'Asia/Shanghai')::date,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb)",
                (aid, user["email"], body.money_clutter_score, body.possession_clutter_score, body.schedule_clutter_score,
                 body.digital_clutter_score, body.desire_pressure_score, body.comparison_pressure_score,
                 json.dumps(body.identified_excesses, ensure_ascii=False), json.dumps(body.gratitude_items, ensure_ascii=False),
                 json.dumps([analysis["generosity_response"]], ensure_ascii=False),
                 json.dumps([analysis["recommended_action"]], ensure_ascii=False)),
            )
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"audit failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "audit_id": aid, "analysis": analysis}


@router.get("/simplicity/audit/latest")
def latest_simplicity(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, audit_date, money_clutter_score, possession_clutter_score, schedule_clutter_score, "
                        "digital_clutter_score, desire_pressure_score, comparison_pressure_score, identified_excesses, "
                        "gratitude_items, possible_generosity_actions, simplification_actions FROM simplicity_audits "
                        "WHERE email=%s ORDER BY audit_date DESC, created_at DESC LIMIT 1", (user["email"],))
            r = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not r:
        return {"ok": True, "audit": None}
    return {"ok": True, "audit": {
        "id": r[0], "audit_date": str(r[1]), "money_clutter_score": r[2], "possession_clutter_score": r[3],
        "schedule_clutter_score": r[4], "digital_clutter_score": r[5], "desire_pressure_score": r[6],
        "comparison_pressure_score": r[7], "identified_excesses": _jl(r[8]), "gratitude_items": _jl(r[9]),
        "possible_generosity_actions": _jl(r[10]), "simplification_actions": _jl(r[11])}}


class ActionCreate(BaseModel):
    audit_id: str = Field(default="", max_length=64)
    action_type: str = Field(default="declutter", max_length=24)
    description: str = Field(..., max_length=2000)


@router.post("/simplicity/actions")
def create_action(request: Request, body: ActionCreate) -> dict:
    user = _require_user(request)
    aid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO simplicity_actions (id, email, audit_id, action_type, description) "
                        "VALUES (%s,%s,%s,%s,%s)", (aid, user["email"], body.audit_id, body.action_type, body.description))
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "action_id": aid}


class ActionUpdate(BaseModel):
    status: str = Field(..., max_length=12)
    completion_notes: str = Field(default="", max_length=2000)


@router.patch("/simplicity/actions/{aid}")
def update_action(aid: str, request: Request, body: ActionUpdate) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE simplicity_actions SET status=%s, completion_notes=%s, updated_at=NOW() WHERE id=%s AND email=%s",
                        (body.status, body.completion_notes, aid, user["email"]))
            conn.commit(); n = cur.rowcount
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"update failed: {exc}")
    finally:
        _state["release_db"](conn)
    if not n:
        raise HTTPException(status_code=404, detail="action not found")
    return {"ok": True}
