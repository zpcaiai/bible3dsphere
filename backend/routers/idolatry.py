"""
Idolatry router — 偶像监测系统 / 依附强度指数 (Attachment Intensity Index)

Endpoints (prefix /api/idolatry):
  GET  /meta            静态配置：7 类偶像、6 问题、5 维度、风险标签
  GET  /signals         从情绪/形成等子系统读取的客观信号 + 建议省察的偶像类型
  POST /assess          对一次省察打分，落库并返回完整分析
  GET  /patterns        历史依附模式 (按会话聚合)
  GET  /latest          最近一次省察摘要 (供「今日心镜」卡片)

「偶像监测」不定罪、不审判，只温柔地观测：什么正在取代神成为内心中心。
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

try:  # 兼容两种导入路径 (backend.* / 顶层)
    from backend import idolatry_engine as engine
except Exception:  # pragma: no cover
    import idolatry_engine as engine  # type: ignore

router = APIRouter(prefix="/api/idolatry", tags=["idolatry"])

_state: Dict[str, Any] = {}


def init_idolatry_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# 中文情绪标签 → 内部信号键
_EMO_MAP = {
    "焦虑": "anxiety", "紧张": "anxiety", "不安": "anxiety",
    "恐惧": "fear", "惧怕": "fear", "害怕": "fear",
    "嫉妒": "envy", "羡慕": "envy", "比较": "envy",
}
# 场景/领域 → 注意力焦点
_FOCUS_MAP = {
    "工作": "work", "职业": "career", "事业": "work",
    "金钱": "money", "财务": "finance", "理财": "finance",
    "关系": "relationship", "恋爱": "relationship", "婚姻": "relationship", "家庭": "family",
    "未来": "future", "自我": "self", "信仰": "spirituality", "灵性": "spirituality",
}


def _gather_signals(email: str) -> Dict[str, Any]:
    """Best-effort：从近期 checkin 读取情绪/注意力客观信号。失败则返回空。"""
    signals: Dict[str, Any] = {}
    try:
        conn = _state["get_db"]()
    except Exception:
        return signals
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT data, emotion_label FROM user_checkins "
                "WHERE email=%s ORDER BY checkin_at DESC LIMIT 20",
                (email,),
            )
            rows = cur.fetchall()
    except Exception:
        rows = []
    finally:
        try:
            _state["release_db"](conn)
        except Exception:
            pass

    if not rows:
        return signals

    emo_counts: Dict[str, int] = {}
    focus_counts: Dict[str, int] = {}
    total = 0
    for data, emotion_label in rows:
        total += 1
        d = data if isinstance(data, dict) else {}
        label = (emotion_label or d.get("emotionLabel") or d.get("emotion_label") or "")
        for zh, key in _EMO_MAP.items():
            if zh in label:
                emo_counts[key] = emo_counts.get(key, 0) + 1
        scenario = (d.get("scenarioCategory") or d.get("scenarioDetail") or "")
        for zh, key in _FOCUS_MAP.items():
            if zh in scenario:
                focus_counts[key] = focus_counts.get(key, 0) + 1

    if emo_counts and total:
        signals["emotion"] = {k: round(v / total, 3) for k, v in emo_counts.items()}
    if focus_counts:
        signals["top_focus"] = max(focus_counts.items(), key=lambda kv: kv[1])[0]
    return signals


# ── Request models ────────────────────────────────────────────────────────────
class RatingItem(BaseModel):
    target_type: str = Field(min_length=1, max_length=40)
    target_name: str = Field(default="", max_length=200)
    fear_of_loss: float = Field(default=0.0, ge=0.0, le=1.0)
    identity_dependency: float = Field(default=0.0, ge=0.0, le=1.0)
    peace_disruption: float = Field(default=0.0, ge=0.0, le=1.0)
    obedience_conflict: float = Field(default=0.0, ge=0.0, le=1.0)
    attention_capture: float = Field(default=0.0, ge=0.0, le=1.0)


class AssessRequest(BaseModel):
    ratings: List[RatingItem] = Field(default_factory=list, max_length=7)
    answers: Dict[str, str] = Field(default_factory=dict)  # 6 个核心问题的自由作答 (留底)
    use_signals: bool = True

    @field_validator("answers")
    @classmethod
    def cap_answers(cls, v):
        # 防滥用：截断
        return {str(k)[:40]: str(val)[:1000] for k, val in list(v.items())[:12]}


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("/meta")
def get_meta() -> dict:
    return {"ok": True, **engine.meta()}


@router.get("/signals")
def get_signals(request: Request) -> dict:
    user = _require_user(request)
    sig = _gather_signals(user["email"])
    return {
        "ok": True,
        "signals": sig,
        "suggested_targets": engine.suggested_targets(sig),
    }


@router.post("/assess")
def post_assess(request: Request, body: AssessRequest) -> dict:
    user = _require_user(request)
    email = user["email"]

    signals = _gather_signals(email) if body.use_signals else None
    ratings = [r.model_dump() for r in body.ratings]
    result = engine.assess(ratings, signals)

    patterns = result["patterns"]
    session_id = uuid.uuid4().hex
    top = result.get("top") or {}

    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO attachment_sessions "
                "(id, email, top_target, top_intensity, risk_level, summary, answers) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (
                    session_id, email,
                    top.get("target_type", ""),
                    float(top.get("intensity", 0.0)),
                    top.get("risk_level", "low"),
                    result["summary"],
                    _Json(body.answers),
                ),
            )
            for p in patterns:
                d = p["dims"]
                cur.execute(
                    "INSERT INTO attachment_patterns "
                    "(id, session_id, email, target_type, target_name, "
                    " fear_of_loss, identity_dependency, peace_disruption, "
                    " obedience_conflict, attention_capture, intensity, risk_level, "
                    " detected_from, explanation) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        uuid.uuid4().hex, session_id, email,
                        p["target_type"], p["target_name"],
                        d["fear_of_loss"], d["identity_dependency"], d["peace_disruption"],
                        d["obedience_conflict"], d["attention_capture"],
                        p["intensity"], p["risk_level"],
                        p["detected_from"][:64], p["explanation"],
                    ),
                )
        conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="save failed")
    finally:
        _state["release_db"](conn)

    # 回流 Formation 八维（闭环，best-effort，静默失败）
    try:
        from formation_bridge import record_formation
        sig = engine.formation_signal(result)
        if sig:
            pats, lb, refl, emo = sig
            record_formation(user.get("id"), pats, loop_broken=lb,
                             reflection_active=refl, emotional_intensity=emo,
                             decision_category="idolatry")
    except Exception:
        pass

    try:
        import formation_events as _fe
        _top = result.get("top") or {}
        _risk = _top.get("risk_level") or ""
        _sev = "red" if _risk == "high" else "amber" if _risk in ("elevated", "medium") else "green"
        _fe.record_event(email, "idolatry", "diagnosis", domain=(_top.get("name") or None),
                         title="偶像省察", summary=(result.get("summary") or "")[:160],
                         severity=_sev, ref_id="idolatry:%s" % session_id)
    except Exception:
        pass

    _out = {"ok": True, "session_id": session_id, **result}
    try:
        from safety_scan import scan_crisis
        _c = scan_crisis(" ".join(str(v) for v in (body.answers or {}).values()))
        if _c and "crisis" not in _out:
            _out["crisis"] = _c
    except Exception:
        pass
    return _out


@router.get("/patterns")
def get_patterns(request: Request,
                 limit: int = Query(default=20, ge=1, le=100)) -> dict:
    user = _require_user(request)
    email = user["email"]
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, top_target, top_intensity, risk_level, summary, created_at "
                "FROM attachment_sessions WHERE email=%s "
                "ORDER BY created_at DESC LIMIT %s",
                (email, limit),
            )
            sessions = cur.fetchall()
            ids = [s[0] for s in sessions]
            pats: Dict[str, List[dict]] = {}
            if ids:
                cur.execute(
                    "SELECT session_id, target_type, target_name, intensity, risk_level, "
                    " fear_of_loss, identity_dependency, peace_disruption, "
                    " obedience_conflict, attention_capture, explanation "
                    "FROM attachment_patterns WHERE session_id IN %s "
                    "ORDER BY intensity DESC",
                    (tuple(ids),),
                )
                for row in cur.fetchall():
                    pats.setdefault(row[0], []).append({
                        "target_type": row[1], "target_name": row[2],
                        "intensity": row[3], "risk_level": row[4],
                        "dims": {
                            "fear_of_loss": row[5], "identity_dependency": row[6],
                            "peace_disruption": row[7], "obedience_conflict": row[8],
                            "attention_capture": row[9],
                        },
                        "explanation": row[10],
                    })
    finally:
        _state["release_db"](conn)

    out = []
    for s in sessions:
        out.append({
            "session_id": s[0], "top_target": s[1], "top_intensity": s[2],
            "risk_level": s[3], "summary": s[4], "created_at": to_iso(s[5]),
            "patterns": pats.get(s[0], []),
        })
    return {"ok": True, "count": len(out), "sessions": out}


@router.get("/latest")
def get_latest(request: Request) -> dict:
    user = _require_user(request)
    email = user["email"]
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, top_target, top_intensity, risk_level, summary, created_at "
                "FROM attachment_sessions WHERE email=%s "
                "ORDER BY created_at DESC LIMIT 1",
                (email,),
            )
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)

    if not row:
        return {"ok": True, "has_data": False}
    name = ""
    idol = engine.IDOL_INDEX.get(row[1])
    if idol:
        name = idol["name"]
    return {
        "ok": True, "has_data": True,
        "session_id": row[0], "top_target": row[1], "top_target_name": name,
        "top_intensity": row[2], "risk_level": row[3], "summary": row[4],
        "created_at": to_iso(row[5]),
    }


# psycopg2 Json 包装；延迟导入以避免顶层硬依赖
def _Json(obj):
    try:
        from psycopg2.extras import Json
        return Json(obj)
    except Exception:
        import json as _json
        return _json.dumps(obj)
