"""
Psalm Prayer router — 诗篇祷告 (/api/psalm)

用诗篇结构带领祷告：在神面前诚实表达真实情绪，又被经文重新定位。

  GET  /api/psalm/psalms              诗篇库
  GET  /api/psalm/psalms/{n}          单篇
  POST /api/psalm/recommend           按情绪/需要推荐诗篇（body: {emotion?, need?}）
  POST /api/psalm/sessions            开始祷告（body: {psalm_number, mode, emotional_state_before?}）
  POST /api/psalm/sessions/{sid}/movement   提交一个祷告动作，返回下一动作引导
  POST /api/psalm/sessions/{sid}/complete   完成（顺服或安息一步）+ 回流 formation
  GET  /api/psalm/history             历史

不强求廉价正能量：哀歌容许停在未解的痛里；咒诅诗把伸冤交给神。
自由文本过 detect_spiritual_crisis；命中记 crisis_flag 并温柔提示，但不阻断保存。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/psalm", tags=["psalm"])

_state: Dict[str, Any] = {}

# 各祷告模式的「动作序列」（movement flow）
_MOVEMENTS = {
    "lament":      ["address_god", "honest_complaint", "ask_help", "remember_truth", "confess_trust", "rest"],
    "praise":      ["address_god", "remember_truth", "praise", "thanksgiving", "vow_obedience", "rest"],
    "confession":  ["address_god", "honest_confession", "ask_mercy", "receive_grace", "vow_obedience", "rest"],
    "trust":       ["address_god", "name_fear", "remember_truth", "confess_trust", "ask_help", "rest"],
    "thanksgiving":["address_god", "remember_truth", "thanksgiving", "praise", "vow_obedience", "rest"],
    "free":        ["address_god", "honest_complaint", "rest"],
}

_GUIDE = {
    "address_god":      "先称呼神。用你此刻能用的称呼向他开口——父、主、我的牧者，或只是「神啊」。",
    "honest_complaint": "诚实地把你的难处、困惑、愤怒或悲伤说出来。诗人也这样向神倾诉，你不必先修饰。",
    "honest_confession":"把你想认的罪如实说出，不夸大、也不掩饰。",
    "name_fear":        "说出你在惧怕、想掌控、或不敢失去的是什么。",
    "ask_help":         "向神求助。具体地说出你需要他为你做什么。",
    "ask_mercy":        "求神的怜悯与赦免。赦免不是靠你赚来的，是他白白的恩典。",
    "remember_truth":   "想起一句关于神的真理——他的慈爱、信实、同在。哪怕你此刻还感受不到。",
    "receive_grace":    "安静领受赦免的确据。你在基督里不被定罪。",
    "praise":           "为神本身赞美他——不是为处境，是为他是谁。",
    "thanksgiving":     "数算一件具体的恩典，向他道谢。",
    "confess_trust":    "向神表达信靠。可以是「我虽不明白，仍要倚靠你」这样诚实的信靠。",
    "vow_obedience":    "回应神：今天有哪一个具体的顺服？",
    "rest":             "停在神面前安息。可以带着未解的问题——带着未完成的信靠安歇，也是诚实的信心。",
    "completed":        "愿这篇诗与你同行。你已完成今天的诗篇祷告。",
}

# 情绪/需要 → 推荐诗篇号（仅返回库中实际存在的）
_RECO = [
    (["焦虑", "害怕", "惧怕", "恐惧", "不安", "anxiety", "fear", "afraid"], [23, 27, 46, 121]),
    (["愧疚", "认罪", "罪", "羞耻", "guilt", "confession", "shame", "sin"], [32, 51, 130]),
    (["悲伤", "哀伤", "忧伤", "难过", "低谷", "grief", "lament", "sad", "sorrow"], [13, 42, 88]),
    (["感恩", "赞美", "喜乐", "感谢", "praise", "gratitude", "thanks", "joy"], [8, 100, 103, 145]),
    (["愤怒", "不公", "不平", "嫉妒", "anger", "injustice", "unfair", "envy"], [37, 73]),
    (["智慧", "成长", "默想", "定志", "wisdom", "formation", "growth"], [1, 19, 119]),
    (["出行", "旅程", "等候", "前路", "journey", "pilgrim", "waiting"], [121]),
    (["身份", "孤单", "被知", "identity", "lonely", "known"], [139, 23]),
]

_PROFILE_COLS = ("psalm_number, title, psalm_type, translation, text, dominant_emotions, "
                 "formation_themes, suggested_use_cases, difficulty, caution_notes")
_SESSION_COLS = ("id, email, psalm_number, session_date, mode, current_movement, movements, "
                 "emotional_state_before, emotional_state_after, key_verse, honest_prayer_text, "
                 "reoriented_prayer_text, obedience_or_rest_step, completion_score, crisis_flag, "
                 "completed_at, created_at")


def init_psalm_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


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
    return {
        "type": ctype,
        "message": "我听见你向神倾诉里的重担。此刻你的安全与被陪伴，比完成这篇祷告更重要。",
        "route": "/api/crisis",
        "note": "你并不孤单。若愿意，可以现在联系一位信任的人，或在「危机陪伴」里获得即时支持。",
    }


def _jl(v):
    if v is None:
        return []
    if isinstance(v, (list, dict)):
        return v
    try:
        return json.loads(v)
    except Exception:
        return []


def _profile_row(r) -> dict:
    return {
        "psalm_number": r[0], "title": r[1] or "", "psalm_type": r[2] or "mixed",
        "translation": r[3] or "CUV", "text": r[4] or "",
        "dominant_emotions": _jl(r[5]), "formation_themes": _jl(r[6]),
        "suggested_use_cases": _jl(r[7]), "difficulty": r[8] or "normal",
        "caution_notes": r[9] or "",
    }


def _session_row(r, to_iso) -> dict:
    return {
        "id": r[0], "email": r[1], "psalm_number": r[2], "session_date": str(r[3]) if r[3] else "",
        "mode": r[4] or "guided", "current_movement": r[5] or "", "movements": _jl(r[6]),
        "emotional_state_before": _jl(r[7]), "emotional_state_after": _jl(r[8]),
        "key_verse": r[9] or "", "honest_prayer_text": r[10] or "",
        "reoriented_prayer_text": r[11] or "", "obedience_or_rest_step": r[12] or "",
        "completion_score": r[13] or 0, "crisis_flag": r[14] or "",
        "completed_at": to_iso(r[15]) if r[15] else None, "created_at": to_iso(r[16]),
    }


def _resolve_mode(mode: str, psalm_type: str) -> str:
    mode = (mode or "guided").strip().lower()
    if mode in _MOVEMENTS:
        return mode
    # guided：按诗篇体裁选流程
    if psalm_type == "lament":
        return "lament"
    if psalm_type == "penitential":
        return "confession"
    if psalm_type in ("praise", "thanksgiving", "creation"):
        return "praise"
    return "trust"


def _fetch_profile(cur, n: int):
    cur.execute(f"SELECT {_PROFILE_COLS} FROM psalm_profiles WHERE psalm_number=%s", (n,))
    return cur.fetchone()


def _fetch_session(cur, sid: str, email: str):
    cur.execute(f"SELECT {_SESSION_COLS} FROM psalm_prayer_sessions WHERE id=%s AND email=%s", (sid, email))
    return cur.fetchone()


# ── 诗篇库 ────────────────────────────────────────────────────────────────────

@router.get("/psalms")
def list_psalms(request: Request) -> dict:
    _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_PROFILE_COLS} FROM psalm_profiles ORDER BY sort_order, psalm_number")
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "psalms": [_profile_row(r) for r in rows]}


@router.get("/psalms/{n}")
def get_psalm(n: int, request: Request) -> dict:
    _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            r = _fetch_profile(cur, n)
    finally:
        _state["release_db"](conn)
    if not r:
        raise HTTPException(status_code=404, detail="psalm not found")
    return {"ok": True, "psalm": _profile_row(r)}


class RecommendBody(BaseModel):
    emotion: str = Field(default="", max_length=200)
    need: str = Field(default="", max_length=200)


@router.post("/recommend")
def recommend(request: Request, body: RecommendBody) -> dict:
    _require_user(request)
    blob = f"{body.emotion} {body.need}".lower()
    wanted: List[int] = []
    for keys, nums in _RECO:
        if any(k.lower() in blob for k in keys):
            wanted.extend(nums)
    # 去重保序
    seen = set()
    wanted = [n for n in wanted if not (n in seen or seen.add(n))]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if wanted:
                cur.execute(
                    f"SELECT {_PROFILE_COLS} FROM psalm_profiles WHERE psalm_number IN %s",
                    (tuple(wanted),),
                )
                by_num = {r[0]: r for r in cur.fetchall()}
                rows = [by_num[n] for n in wanted if n in by_num]
            else:
                cur.execute(
                    f"SELECT {_PROFILE_COLS} FROM psalm_profiles "
                    "WHERE psalm_number IN %s ORDER BY sort_order",
                    ((23, 42, 103),),
                )
                rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "psalms": [_profile_row(r) for r in rows]}


# ── 祷告会话 ──────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    psalm_number: int = Field(..., ge=1, le=150)
    mode: str = Field(default="guided", max_length=20)
    emotional_state_before: List[str] = Field(default_factory=list)


@router.post("/sessions")
def create_session(request: Request, body: SessionCreate) -> dict:
    user = _require_user(request)
    email = user["email"]
    to_iso = _state["to_shanghai_iso"]
    sid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            prof = _fetch_profile(cur, body.psalm_number)
            if not prof:
                raise HTTPException(status_code=404, detail="psalm not found")
            mode = _resolve_mode(body.mode, prof[2] or "mixed")
            first = _MOVEMENTS[mode][0]
            cur.execute(
                "INSERT INTO psalm_prayer_sessions "
                "(id, email, psalm_number, session_date, mode, current_movement, "
                " emotional_state_before) "
                "VALUES (%s,%s,%s,(NOW() AT TIME ZONE 'Asia/Shanghai')::date,%s,%s,%s::jsonb)",
                (sid, email, body.psalm_number, mode, first,
                 json.dumps(body.emotional_state_before, ensure_ascii=False)),
            )
            conn.commit()
            row = _fetch_session(cur, sid, email)
    except HTTPException:
        raise
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"create failed: {exc}")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "session": _session_row(row, to_iso), "psalm": _profile_row(prof),
            "movement": first, "guidance": _GUIDE.get(first, "")}


class MovementSubmit(BaseModel):
    movement_key: str = Field(..., max_length=24)
    text: str = Field(default="", max_length=8000)


@router.post("/sessions/{sid}/movement")
def submit_movement(sid: str, request: Request, body: MovementSubmit) -> dict:
    user = _require_user(request)
    email = user["email"]
    to_iso = _state["to_shanghai_iso"]
    crisis = _scan_crisis(body.text)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _fetch_session(cur, sid, email)
            if not row:
                raise HTTPException(status_code=404, detail="session not found")
            mode = row[4] or "guided"
            seq = _MOVEMENTS.get(mode, _MOVEMENTS["trust"])
            mk = (body.movement_key or "").strip()
            if mk not in seq:
                raise HTTPException(status_code=400, detail=f"invalid movement: {mk}")
            moves = _jl(row[6]) or {}
            if not isinstance(moves, dict):
                moves = {}
            moves[mk] = body.text.strip()
            idx = seq.index(mk)
            nxt = seq[idx + 1] if idx + 1 < len(seq) else "completed"
            # honest_prayer_text 累积「诚实」类动作；reoriented 累积「真理/信靠」类
            honest_keys = {"honest_complaint", "honest_confession", "name_fear"}
            reorient_keys = {"remember_truth", "receive_grace", "confess_trust", "praise"}
            sets = ["movements=%s::jsonb", "current_movement=%s", "updated_at=NOW()"]
            params: list = [json.dumps(moves, ensure_ascii=False), nxt]
            if mk in honest_keys and body.text.strip():
                sets.append("honest_prayer_text=%s")
                params.append(body.text.strip())
            if mk in reorient_keys and body.text.strip():
                sets.append("reoriented_prayer_text=%s")
                params.append(body.text.strip())
            if crisis:
                sets.append("crisis_flag=%s")
                params.append(crisis["type"])
            params.extend([sid, email])
            cur.execute(
                f"UPDATE psalm_prayer_sessions SET {', '.join(sets)} WHERE id=%s AND email=%s",
                tuple(params),
            )
            conn.commit()
            row = _fetch_session(cur, sid, email)
    except HTTPException:
        raise
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"movement failed: {exc}")
    finally:
        _state["release_db"](conn)
    out = {"ok": True, "session": _session_row(row, to_iso),
           "movement": nxt, "guidance": _GUIDE.get(nxt, "")}
    if crisis:
        out["crisis"] = crisis
    return out


class CompleteBody(BaseModel):
    obedience_or_rest_step: str = Field(default="", max_length=2000)
    key_verse: str = Field(default="", max_length=200)
    emotional_state_after: List[str] = Field(default_factory=list)


@router.post("/sessions/{sid}/complete")
def complete_session(sid: str, request: Request, body: CompleteBody) -> dict:
    user = _require_user(request)
    email = user["email"]
    to_iso = _state["to_shanghai_iso"]
    crisis = _scan_crisis(body.obedience_or_rest_step)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _fetch_session(cur, sid, email)
            if not row:
                raise HTTPException(status_code=404, detail="session not found")
            moves = _jl(row[6]) or {}
            filled = len([1 for v in (moves.values() if isinstance(moves, dict) else []) if str(v).strip()])
            score = min(100, max(20, filled * 20))
            sets = ["obedience_or_rest_step=%s", "key_verse=%s", "emotional_state_after=%s::jsonb",
                    "current_movement='completed'", "completion_score=%s",
                    "completed_at=NOW()", "updated_at=NOW()"]
            params: list = [body.obedience_or_rest_step.strip(), body.key_verse.strip(),
                            json.dumps(body.emotional_state_after, ensure_ascii=False), score]
            if crisis:
                sets.append("crisis_flag=%s")
                params.append(crisis["type"])
            params.extend([sid, email])
            cur.execute(
                f"UPDATE psalm_prayer_sessions SET {', '.join(sets)} WHERE id=%s AND email=%s",
                tuple(params),
            )
            conn.commit()
            row = _fetch_session(cur, sid, email)
    except HTTPException:
        raise
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"complete failed: {exc}")
    finally:
        _state["release_db"](conn)

    try:
        from formation_bridge import record_formation
        record_formation(user.get("id"), ["spiritual", "growth"], loop_broken=True,
                         reflection_active=True, emotional_intensity=4.5,
                         decision_category="psalm_prayer")
    except Exception:
        pass
    try:
        import formation_events as _fe
        sr = _session_row(row, to_iso)
        _fe.record_event(email, "psalm_prayer", "psalm", title="诗篇祷告 Psalm",
                         summary=f"诗篇 {sr['psalm_number']} · {sr['mode']}",
                         severity="amber" if crisis else "green")
    except Exception:
        pass

    out = {"ok": True, "session": _session_row(row, to_iso), "guidance": _GUIDE["completed"]}
    if crisis:
        out["crisis"] = crisis
    return out


@router.get("/history")
def history(request: Request, limit: int = Query(default=30, ge=1, le=120)) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_SESSION_COLS} FROM psalm_prayer_sessions WHERE email=%s "
                "ORDER BY session_date DESC, created_at DESC LIMIT %s",
                (user["email"], limit),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "sessions": [_session_row(r, to_iso) for r in rows]}
