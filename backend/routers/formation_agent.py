"""
AI Formation Agent router — 个人成长 Agent / 统一编排层 (/api/formation-agent)

  GET  /api/formation-agent/dashboard       跨模块统一今日快照
  POST /api/formation-agent/route           意图 → 模块路由(安全优先)
  POST /api/formation-agent/daily-plan      生成今日计划(并持久化)
  GET  /api/formation-agent/daily-plan/today  今日计划
  GET  /api/formation-agent/recommendations  今日 top 推荐

安全优先:任何危机文本先路由危机陪伴,阻断常规;计划温柔、克制(默认 3 项)、可解释。
不是 God、不是牧者/治疗师/紧急服务。email 标识用户。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/formation-agent", tags=["formation-agent"])

_state: Dict[str, Any] = {}

# 意图关键词 → (module, skill, endpoint)
_ROUTES = [
    (["自杀", "自伤", "想死", "活不下去", "伤害自己", "结束生命"], ("suffering_care", "crisis", "/api/crisis")),
    (["祷告", "祈祷", "代祷"], ("prayer_communion", "prayer_rule", "/api/prayer-rule/today")),
    (["读经", "默想", "经文"], ("scripture_formation", "lectio", "/api/lectio/passages/daily")),
    (["背经", "记忆"], ("scripture_formation", "memory", "/api/memory/due")),
    (["认罪", "悔改", "赦免"], ("scripture_formation", "confession", "/api/confession/record")),
    (["省察", "回顾这一天"], ("scripture_formation", "examen", "/api/examen/today")),
    (["试探", "诱惑", "冲动", "想犯"], ("virtue_vice", "temptation", "/api/temptation/resist")),
    (["偶像", "掌控", "贪", "嫉妒"], ("virtue_vice", "idolatry", "/api/idolatry/meta")),
    (["果子", "成长怎么样"], ("virtue_vice", "fruit", "/api/fruit/dimensions")),
    (["安息", "休息", "burnout", "累垮", "倦怠"], ("holy_habit", "sabbath", "/api/sabbath/recommend")),
    (["禁食", "简朴", "断舍离"], ("holy_habit", "fasting", "/api/fasting/practices")),
    (["世界观", "信念", "为什么我总是"], ("worldview", "belief", "/api/worldview/meta")),
    (["决定", "抉择", "该不该"], ("worldview", "decision", "/api/discern/meta")),
    (["苦难", "受苦", "为什么是我"], ("suffering_care", "suffering", "/api/suffering/cases/analyze")),
    (["哀伤", "失去", "悲伤", "医治"], ("suffering_care", "healing", "/api/care/my-consent")),
    (["导师", "陪跑"], ("discipleship_community", "mentor", "/api/mentor/relationships")),
    (["小组", "同伴", "监督"], ("discipleship_community", "accountability_group", "/api/accountability-group/groups")),
    (["门徒", "成长阶段", "下一步成长"], ("discipleship_community", "discipleship", "/api/discipleship/stages")),
    (["教会", "聚会", "重返教会"], ("discipleship_community", "church", "/api/church-integration/recommend")),
    (["恩赐", "呼召", "服事"], ("gift_calling", "gift", "/api/gift/meta")),
    (["使命", "职场见证", "活出信仰"], ("gift_calling", "mission_life", "/api/mission-life/domains")),
    (["教义", "学习", "称义", "三一"], ("bible_doctrine", "doctrine", "/api/doctrine/topics")),
    (["时间线", "救赎历史", "圣经故事"], ("bible_doctrine", "timeline", "/api/timeline/overview")),
    (["人物", "大卫", "摩西"], ("bible_doctrine", "characters", "/api/characters")),
]


def init_formation_agent_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _scan(text: str) -> Optional[dict]:
    try:
        from safety_scan import scan_crisis
        return scan_crisis(text)
    except Exception:
        return None


def _count(cur, sql, params=()) -> int:
    try:
        cur.execute(sql, params)
        r = cur.fetchone()
        return (r[0] or 0) if r else 0
    except Exception:
        return 0


def _exists(cur, sql, params=()) -> bool:
    try:
        cur.execute(sql, params)
        return cur.fetchone() is not None
    except Exception:
        return False


@router.get("/dashboard")
def dashboard(request: Request) -> dict:
    user = _require_user(request); email = user["email"]
    today_sql = "(NOW() AT TIME ZONE 'Asia/Shanghai')::date"
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            examen_done = _exists(cur, f"SELECT 1 FROM examen_entries WHERE email=%s AND entry_date={today_sql}", (email,))
            lectio_today = _count(cur, f"SELECT COUNT(*) FROM lectio_sessions WHERE email=%s AND session_date={today_sql}", (email,))
            prayer_done = _count(cur, f"SELECT COUNT(*) FROM prayer_rule_sessions WHERE email=%s AND status='completed' AND session_date={today_sql}", (email,))
            interc_due = _count(cur, "SELECT COUNT(*) FROM intercession_requests WHERE email=%s AND status='active' AND (next_pray_at IS NULL OR next_pray_at <= NOW())", (email,))
            tempt_plans = _count(cur, "SELECT COUNT(*) FROM temptation_plans WHERE email=%s AND status='active'", (email,))
            fruit_recent = _exists(cur, "SELECT 1 FROM fruit_assessments WHERE email=%s AND assessment_date >= CURRENT_DATE - INTERVAL '30 days'", (email,))
            # 关怀/危机标志
            care_flag = _exists(cur, "SELECT 1 FROM crisis_events WHERE user_id=%s AND status='open'", (email,)) if True else False
    finally:
        _state["release_db"](conn)

    flags = []
    if care_flag:
        flags.append({"type": "care", "message": "有未结的关怀/危机记录,安全与陪伴优先。", "route": "/api/crisis"})

    next_action = None
    if not examen_done:
        next_action = {"title": "今天的省察", "module": "scripture_formation", "endpoint": "/api/examen/today"}
    elif interc_due:
        next_action = {"title": f"为 {interc_due} 个代祷事项祷告", "module": "prayer_communion", "endpoint": "/api/intercession/today"}
    elif not fruit_recent:
        next_action = {"title": "做一次圣灵果子自评", "module": "virtue_vice", "endpoint": "/api/fruit/dimensions"}

    return {"ok": True, "today": {
        "examen_done": examen_done, "lectio_sessions": lectio_today, "prayer_sessions_completed": prayer_done,
        "intercession_due": interc_due, "active_temptation_plans": tempt_plans, "fruit_assessed_30d": fruit_recent,
        "care_flags": flags, "recommended_next_action": next_action,
    }, "message": "愿你今天在恩典里走一小步。这是相交,不是表现。"}


class RouteBody(BaseModel):
    intent_text: str = Field(..., max_length=4000)


@router.post("/route")
def route_intent(request: Request, body: RouteBody) -> dict:
    user = _require_user(request); email = user["email"]
    text = body.intent_text or ""
    crisis = _scan(text)
    # 安全优先
    if crisis:
        try:
            conn = _state["get_db"]()
            with conn.cursor() as cur:
                cur.execute("INSERT INTO formation_agent_sessions (id, email, intent_text, detected_intent, risk_level, routed_module) "
                            "VALUES (%s,%s,%s,'crisis','high','suffering_care')", (uuid.uuid4().hex, email, text[:2000]))
                conn.commit()
            _state["release_db"](conn)
        except Exception:
            pass
        return {"ok": True, "risk_level": "high", "block_normal": True,
                "route": {"module": "suffering_care", "skill": "crisis", "endpoint": "/api/crisis"},
                "message": "你此刻的安全与被陪伴最重要。请现在联系一位信任的人,或在「危机陪伴」获得即时支持。",
                "crisis": crisis}

    low = text.lower()
    matched = None
    for kws, (mod, skill, ep) in _ROUTES:
        if any(k.lower() in low for k in kws):
            matched = (mod, skill, ep); break
    if not matched:
        matched = ("scripture_formation", "examen", "/api/examen/today")
        why = "未识别明确意图,先从今天的省察开始。"
    else:
        why = "根据你的描述匹配到最相关的操练。"

    try:
        conn = _state["get_db"]()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO formation_agent_sessions (id, email, intent_text, detected_intent, risk_level, routed_module) "
                        "VALUES (%s,%s,%s,%s,'none',%s)", (uuid.uuid4().hex, email, text[:2000], matched[1], matched[0]))
            conn.commit()
        _state["release_db"](conn)
    except Exception:
        pass

    return {"ok": True, "risk_level": "none", "block_normal": False,
            "route": {"module": matched[0], "skill": matched[1], "endpoint": matched[2]}, "why": why}


def _default_practices() -> List[dict]:
    return [
        {"module": "prayer_communion", "skill": "prayer_rule", "title": "晨祷 · 一句交托", "minimum": "父啊,我把今天交在你手中。", "duration_minutes": 3},
        {"module": "scripture_formation", "skill": "lectio", "title": "默想今日经文", "minimum": "慢读一遍,留意一个字。", "duration_minutes": 5},
        {"module": "virtue_vice", "skill": "fruit", "title": "一个微小的爱的行动", "minimum": "向一个人表达关心或感谢。", "duration_minutes": 3},
    ]


class PlanBody(BaseModel):
    energy_level: str = Field(default="normal", max_length=12)


@router.post("/daily-plan")
def daily_plan(request: Request, body: PlanBody) -> dict:
    user = _require_user(request); email = user["email"]
    practices = _default_practices()
    guardrails = ["不必全部完成——挑一个真实地做。", "今天若疲惫,只做第一项即可。"]
    if (body.energy_level or "").lower() == "low":
        practices = practices[:1]
        guardrails.insert(0, "你说精力低:今天只保留一句晨祷,其余交给恩典。")
    pid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO daily_formation_plans (id, email, plan_date, primary_focus, practices, guardrails) "
                "VALUES (%s,%s,(NOW() AT TIME ZONE 'Asia/Shanghai')::date,%s,%s::jsonb,%s::jsonb) "
                "ON CONFLICT (email, plan_date) DO UPDATE SET practices=EXCLUDED.practices, guardrails=EXCLUDED.guardrails, updated_at=NOW()",
                (pid, email, "稳定的相交", json.dumps(practices, ensure_ascii=False), json.dumps(guardrails, ensure_ascii=False)),
            )
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"plan failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "plan": {"plan_title": "今日的忠心一小步", "primary_focus": "稳定的相交",
            "practices": practices, "guardrails": guardrails}}


@router.get("/daily-plan/today")
def today_plan(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT plan_title, primary_focus, practices, guardrails FROM daily_formation_plans "
                        "WHERE email=%s AND plan_date=(NOW() AT TIME ZONE 'Asia/Shanghai')::date", (user["email"],))
            r = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not r:
        return {"ok": True, "plan": None}
    def jl(v):
        if isinstance(v, (list, dict)): return v
        try: return json.loads(v)
        except Exception: return []
    return {"ok": True, "plan": {"plan_title": r[0], "primary_focus": r[1] or "", "practices": jl(r[2]), "guardrails": jl(r[3])}}


@router.get("/recommendations")
def recommendations(request: Request) -> dict:
    user = _require_user(request); email = user["email"]
    today_sql = "(NOW() AT TIME ZONE 'Asia/Shanghai')::date"
    recs = []
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if not _exists(cur, f"SELECT 1 FROM examen_entries WHERE email=%s AND entry_date={today_sql}", (email,)):
                recs.append({"title": "今天的省察", "endpoint": "/api/examen/today", "reason": "今天还没回顾这一天", "effort": "low"})
            if _count(cur, "SELECT COUNT(*) FROM intercession_requests WHERE email=%s AND status='active' AND (next_pray_at IS NULL OR next_pray_at <= NOW())", (email,)) > 0:
                recs.append({"title": "为到期的代祷祷告", "endpoint": "/api/intercession/today", "reason": "有代祷事项到期", "effort": "low"})
            if not _exists(cur, "SELECT 1 FROM fruit_assessments WHERE email=%s AND assessment_date >= CURRENT_DATE - INTERVAL '30 days'", (email,)):
                recs.append({"title": "圣灵果子自评", "endpoint": "/api/fruit/dimensions", "reason": "近一个月没做过", "effort": "moderate"})
    finally:
        _state["release_db"](conn)
    if not recs:
        recs.append({"title": "默想今日经文", "endpoint": "/api/lectio/passages/daily", "reason": "保持与神相交的节奏", "effort": "low"})
    return {"ok": True, "recommendations": recs[:3],
            "note": "每天最多 3 项,小而稳胜过多而散。"}
