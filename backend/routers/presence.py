"""
Practicing Presence router — 操练与神同在 (/api/presence)

  GET  /api/presence/practices             短操练库
  POST /api/presence/recommend             按情境/情绪推荐一个短操练
  POST /api/presence/checkins              开始一次 check-in
  POST /api/presence/checkins/{id}/complete  完成（觉知前后 + 短祷 + 回转行动）
  POST /api/presence/rules                 创建提醒规则
  GET  /api/presence/rules                 列出规则
  GET  /api/presence/today                 今日 check-in + 一个推荐
  GET  /api/presence/reflection            日/周反思（含过度打卡护栏）

短而频的回转；不要把觉知变成焦虑或强迫打卡。awareness 仅作主观成长指示，
不是神临在的度量。email 标识用户。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/presence", tags=["presence"])

_state: Dict[str, Any] = {}

_RECO = [
    (["焦虑", "害怕", "紧张", "anxiety", "fear"], ["one_minute_breath_prayer", "scripture_recollection", "surrender_prayer"]),
    (["愤怒", "冲突", "生气", "anger", "conflict"], ["conflict_pause", "silence_60_seconds", "surrender_prayer"]),
    (["疲惫", "累", "倦", "fatigue", "tired"], ["fatigue_rest_prayer", "gratitude_pause"]),
    (["试探", "诱惑", "冲动", "temptation"], ["temptation_pause", "scripture_recollection"]),
    (["工作", "编程", "coding", "work"], ["work_offering", "gratitude_pause", "one_minute_breath_prayer"]),
    (["通勤", "路上", "commute"], ["commute_intercession", "one_minute_breath_prayer", "gratitude_pause"]),
    (["无聊", "麻木", "空", "boredom", "numb"], ["gratitude_pause", "silence_60_seconds"]),
]
_DEFAULT = ["one_minute_breath_prayer", "gratitude_pause"]


def init_presence_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
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


def _practice(r) -> dict:
    return {"practice_key": r[0], "title": r[1], "description": r[2] or "", "practice_type": r[3],
            "duration_seconds": r[4], "scripture_refs": _jl(r[5]), "difficulty": r[6]}


_P_COLS = "practice_key, title, description, practice_type, duration_seconds, scripture_refs, difficulty"
_C_COLS = ("id, email, practice_key, checkin_time, context_label, awareness_before, awareness_after, "
           "emotional_state, short_prayer, distraction_noted, return_action, completed")


def _checkin_row(r, to_iso) -> dict:
    return {"id": r[0], "practice_key": r[2] or "", "checkin_time": to_iso(r[3]) if r[3] else None,
            "context_label": r[4] or "", "awareness_before": r[5], "awareness_after": r[6],
            "emotional_state": _jl(r[7]), "short_prayer": r[8] or "", "distraction_noted": r[9] or "",
            "return_action": r[10] or "", "completed": bool(r[11])}


@router.get("/practices")
def list_practices(request: Request) -> dict:
    _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_P_COLS} FROM presence_practices WHERE active=TRUE ORDER BY sort_order")
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "practices": [_practice(r) for r in rows]}


class RecommendBody(BaseModel):
    context_label: str = Field(default="", max_length=40)
    emotion: str = Field(default="", max_length=200)


@router.post("/recommend")
def recommend(request: Request, body: RecommendBody) -> dict:
    _require_user(request)
    blob = f"{body.context_label} {body.emotion}".lower()
    keys: List[str] = []
    for kws, ks in _RECO:
        if any(k.lower() in blob for k in kws):
            keys.extend(ks)
    if not keys:
        keys = list(_DEFAULT)
    seen = set(); keys = [k for k in keys if not (k in seen or seen.add(k))]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_P_COLS} FROM presence_practices WHERE practice_key IN %s AND active=TRUE", (tuple(keys),))
            by = {r[0]: r for r in cur.fetchall()}
    finally:
        _state["release_db"](conn)
    practices = [_practice(by[k]) for k in keys if k in by]
    return {"ok": True, "practices": practices,
            "note": "只需 30–60 秒。觉知是为了回到神面前，不是为了打卡或自我监控。"}


class CheckinStart(BaseModel):
    practice_key: str = Field(default="", max_length=40)
    context_label: str = Field(default="", max_length=40)
    awareness_before: Optional[int] = Field(default=None, ge=0, le=10)
    emotional_state: List[str] = Field(default_factory=list)


@router.post("/checkins")
def create_checkin(request: Request, body: CheckinStart) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    cid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO presence_checkins (id, email, practice_key, context_label, awareness_before, emotional_state) "
                "VALUES (%s,%s,%s,%s,%s,%s::jsonb)",
                (cid, user["email"], body.practice_key, body.context_label, body.awareness_before,
                 json.dumps(body.emotional_state, ensure_ascii=False)),
            )
            conn.commit()
            cur.execute(f"SELECT {_C_COLS} FROM presence_checkins WHERE id=%s", (cid,))
            row = cur.fetchone()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "checkin": _checkin_row(row, to_iso)}


class CheckinComplete(BaseModel):
    awareness_after: Optional[int] = Field(default=None, ge=0, le=10)
    short_prayer: str = Field(default="", max_length=2000)
    distraction_noted: str = Field(default="", max_length=2000)
    return_action: str = Field(default="", max_length=2000)


@router.post("/checkins/{cid}/complete")
def complete_checkin(cid: str, request: Request, body: CheckinComplete) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE presence_checkins SET completed=TRUE, awareness_after=%s, short_prayer=%s, "
                "distraction_noted=%s, return_action=%s WHERE id=%s AND email=%s",
                (body.awareness_after, body.short_prayer, body.distraction_noted, body.return_action, cid, user["email"]),
            )
            if not cur.rowcount:
                raise HTTPException(status_code=404, detail="checkin not found")
            conn.commit()
            cur.execute(f"SELECT {_C_COLS} FROM presence_checkins WHERE id=%s", (cid,))
            row = cur.fetchone()
    except HTTPException:
        raise
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"complete failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "checkin": _checkin_row(row, to_iso)}


class RuleCreate(BaseModel):
    title: str = Field(..., max_length=120)
    trigger_type: str = Field(default="manual", max_length=20)
    trigger_config: Dict[str, Any] = Field(default_factory=dict)
    practice_key: str = Field(default="", max_length=40)


@router.post("/rules")
def create_rule(request: Request, body: RuleCreate) -> dict:
    user = _require_user(request)
    rid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO presence_rules (id, email, title, trigger_type, trigger_config, practice_key) "
                "VALUES (%s,%s,%s,%s,%s::jsonb,%s)",
                (rid, user["email"], body.title, body.trigger_type,
                 json.dumps(body.trigger_config, ensure_ascii=False), body.practice_key),
            )
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "rule_id": rid}


@router.get("/rules")
def list_rules(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, active, trigger_type, trigger_config, practice_key "
                        "FROM presence_rules WHERE email=%s AND active=TRUE ORDER BY created_at DESC", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "rules": [
        {"id": r[0], "title": r[1], "active": bool(r[2]), "trigger_type": r[3],
         "trigger_config": _jl(r[4]) if isinstance(_jl(r[4]), dict) else (r[4] or {}), "practice_key": r[5] or ""} for r in rows
    ]}


@router.get("/today")
def today(request: Request) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_C_COLS} FROM presence_checkins WHERE email=%s "
                        "AND checkin_time::date=(NOW() AT TIME ZONE 'Asia/Shanghai')::date "
                        "ORDER BY checkin_time DESC", (user["email"],))
            rows = cur.fetchall()
            cur.execute(f"SELECT {_P_COLS} FROM presence_practices WHERE practice_key='one_minute_breath_prayer'")
            rec = cur.fetchone()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "checkins": [_checkin_row(r, to_iso) for r in rows],
            "recommended": _practice(rec) if rec else None}


@router.get("/reflection")
def reflection(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM presence_checkins WHERE email=%s "
                        "AND checkin_time::date=(NOW() AT TIME ZONE 'Asia/Shanghai')::date", (user["email"],))
            today_n = cur.fetchone()[0] or 0
            cur.execute("SELECT context_label, COUNT(*) FROM presence_checkins WHERE email=%s "
                        "AND checkin_time >= NOW() - INTERVAL '7 days' AND context_label<>'' "
                        "GROUP BY context_label ORDER BY COUNT(*) DESC LIMIT 5", (user["email"],))
            contexts = [{"context": r[0], "count": r[1]} for r in cur.fetchall()]
    finally:
        _state["release_db"](conn)
    insights = []
    if today_n > 8:
        insights.append("今天的 check-in 偏多。操练与神同在是为了释放，不是又一项要追赶的指标——可以减少次数，让它自然些。")
    elif today_n > 0:
        insights.append("今天你有几次回到神面前的小停顿，这就是与神同在的操练。")
    else:
        insights.append("可以从一次开始：下次切换任务前，做一次一分钟呼吸祷告。")
    if contexts:
        insights.append("这周你最常在「" + contexts[0]["context"] + "」时回到神面前。")
    return {"ok": True, "today_checkins": today_n, "common_contexts": contexts, "insights": insights}
