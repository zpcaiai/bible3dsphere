"""
Lectio Divina router — 圣经默想 / 灵修阅读 (/api/lectio)

古典五步：读经 read → 默想 meditate → 祷告 pray → 默观 contemplate → 顺服 obey。

  GET  /api/lectio/passages          经文库
  GET  /api/lectio/passages/daily    今日推荐经文（按年内日序轮换）
  POST /api/lectio/sessions          开始一次默想（body: {passage_id}）
  GET  /api/lectio/sessions/{sid}    读取
  POST /api/lectio/sessions/{sid}/stage     提交某一步（含危机扫描），返回下一步引导
  POST /api/lectio/sessions/{sid}/complete  完成（须有一个具体顺服）+ 回流 formation
  GET  /api/lectio/history           历史

安全：每一步的自由文本都过 detect_spiritual_crisis；若命中，记录 crisis_flag 并在
响应中给出温柔的危机指引（route=/api/crisis），但绝不阻断用户保存。不定罪、温柔陪伴。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/lectio", tags=["lectio"])

_state: Dict[str, Any] = {}

# 五步顺序与每步对应的存储列
_STAGE_ORDER = ["read", "meditate", "pray", "contemplate", "obey", "completed"]
_STAGE_COL = {
    "read": "read_notes",
    "meditate": "meditation_notes",
    "pray": "prayer_text",
    "contemplate": "contemplation_notes",
    "obey": "obedience_action",
}
_STAGE_GUIDE = {
    "read": "慢慢读两三遍。哪一个字、词或画面停留在你心里？把它记下来。",
    "meditate": "把这字句带到你此刻的生活：它触到你的什么渴望、惧怕、盼望或亏欠？",
    "pray": "把默想化作向神的祷告。不必工整，可以先用一句话开始。",
    "contemplate": "停下言语，在神面前安静一会儿。不必做什么，只是与他同在。",
    "obey": "选一个 24 小时内、具体、可衡量的小顺服。小而真实胜过大而空泛。",
    "completed": "愿这段话今天与你同行。你已完成今天的默想。",
}

_SESSION_COLS = ("id, email, passage_id, passage_ref, session_date, stage, read_notes, "
                 "key_words, meditation_notes, prayer_text, contemplation_notes, "
                 "obedience_action, grace_received, completion_score, crisis_flag, created_at")


def init_lectio_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _scan_crisis(*texts: str) -> Optional[dict]:
    """对自由文本做属灵危机扫描。命中返回危机指引 dict，否则 None。best-effort。"""
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
        "message": "我听见你字里行间的重担。比起继续这个操练，此刻你的安全与被陪伴更重要。",
        "route": "/api/crisis",
        "note": "你并不孤单。若愿意，可以现在联系一位信任的人，或在「危机陪伴」里获得即时支持。",
    }


def _jsonb_list(v) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    try:
        out = json.loads(v)
        return out if isinstance(out, list) else []
    except Exception:
        return []


def _session_row(r, to_iso) -> dict:
    return {
        "id": r[0], "email": r[1], "passage_id": r[2] or "", "passage_ref": r[3] or "",
        "session_date": str(r[4]) if r[4] else "", "stage": r[5] or "read",
        "read_notes": r[6] or "", "key_words": _jsonb_list(r[7]),
        "meditation_notes": r[8] or "", "prayer_text": r[9] or "",
        "contemplation_notes": r[10] or "", "obedience_action": r[11] or "",
        "grace_received": r[12] or "", "completion_score": r[13] or 0,
        "crisis_flag": r[14] or "", "created_at": to_iso(r[15]),
    }


def _fetch_session(cur, sid: str, email: str):
    cur.execute(
        f"SELECT {_SESSION_COLS} FROM lectio_sessions WHERE id=%s AND email=%s",
        (sid, email),
    )
    return cur.fetchone()


# ── 经文库 ────────────────────────────────────────────────────────────────────

@router.get("/passages")
def list_passages(request: Request) -> dict:
    _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, ref, book, translation, passage_text, theme_tags, difficulty "
                "FROM lectio_passages ORDER BY sort_order, ref"
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "passages": [
        {"id": r[0], "ref": r[1], "book": r[2] or "", "translation": r[3] or "CUV",
         "passage_text": r[4] or "", "theme_tags": _jsonb_list(r[5]),
         "difficulty": r[6] or "normal"} for r in rows
    ]}


@router.get("/passages/daily")
def daily_passage(request: Request) -> dict:
    _require_user(request)
    from datetime import datetime as _dt
    try:
        from zoneinfo import ZoneInfo as _Z
        doy = _dt.now(_Z("Asia/Shanghai")).timetuple().tm_yday
    except Exception:
        doy = _dt.utcnow().timetuple().tm_yday
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM lectio_passages")
            n = cur.fetchone()[0] or 0
            if n == 0:
                return {"ok": True, "passage": None}
            offset = doy % n
            cur.execute(
                "SELECT id, ref, book, translation, passage_text, theme_tags, difficulty "
                "FROM lectio_passages ORDER BY sort_order, ref OFFSET %s LIMIT 1",
                (offset,),
            )
            r = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not r:
        return {"ok": True, "passage": None}
    return {"ok": True, "passage": {
        "id": r[0], "ref": r[1], "book": r[2] or "", "translation": r[3] or "CUV",
        "passage_text": r[4] or "", "theme_tags": _jsonb_list(r[5]), "difficulty": r[6] or "normal"
    }}


# ── 默想会话 ──────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    passage_id: str = Field(default="", max_length=64)


@router.post("/sessions")
def create_session(request: Request, body: SessionCreate) -> dict:
    user = _require_user(request)
    email = user["email"]
    to_iso = _state["to_shanghai_iso"]
    sid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            passage_ref = ""
            if body.passage_id:
                cur.execute("SELECT ref FROM lectio_passages WHERE id=%s", (body.passage_id,))
                pr = cur.fetchone()
                passage_ref = pr[0] if pr else ""
            cur.execute(
                "INSERT INTO lectio_sessions "
                "(id, email, passage_id, passage_ref, session_date, stage) "
                "VALUES (%s,%s,%s,%s,(NOW() AT TIME ZONE 'Asia/Shanghai')::date,'read')",
                (sid, email, body.passage_id, passage_ref),
            )
            conn.commit()
            row = _fetch_session(cur, sid, email)
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="create failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "session": _session_row(row, to_iso),
            "guidance": _STAGE_GUIDE["read"]}


@router.get("/sessions/{sid}")
def get_session(sid: str, request: Request) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _fetch_session(cur, sid, user["email"])
    finally:
        _state["release_db"](conn)
    if not row:
        raise HTTPException(status_code=404, detail="session not found")
    return {"ok": True, "session": _session_row(row, to_iso)}


class StageSubmit(BaseModel):
    stage: str = Field(..., max_length=20)
    text: str = Field(default="", max_length=8000)
    key_words: List[str] = Field(default_factory=list)


@router.post("/sessions/{sid}/stage")
def submit_stage(sid: str, request: Request, body: StageSubmit) -> dict:
    user = _require_user(request)
    email = user["email"]
    to_iso = _state["to_shanghai_iso"]
    stage = (body.stage or "").strip().lower()
    if stage not in _STAGE_COL:
        raise HTTPException(status_code=400, detail=f"invalid stage: {stage}")

    crisis = _scan_crisis(body.text, " ".join(body.key_words))
    col = _STAGE_COL[stage]
    next_stage = _STAGE_ORDER[min(_STAGE_ORDER.index(stage) + 1, len(_STAGE_ORDER) - 1)]

    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _fetch_session(cur, sid, email)
            if not row:
                raise HTTPException(status_code=404, detail="session not found")
            sets = [f"{col}=%s", "stage=%s", "updated_at=NOW()"]
            params: list = [body.text.strip(), next_stage]
            if stage == "read":
                sets.append("key_words=%s::jsonb")
                params.append(json.dumps(body.key_words, ensure_ascii=False))
            if crisis:
                sets.append("crisis_flag=%s")
                params.append(crisis["type"])
            params.extend([sid, email])
            cur.execute(
                f"UPDATE lectio_sessions SET {', '.join(sets)} WHERE id=%s AND email=%s",
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
        raise HTTPException(status_code=500, detail="stage failed")
    finally:
        _state["release_db"](conn)

    out = {"ok": True, "session": _session_row(row, to_iso),
           "next_stage": next_stage, "guidance": _STAGE_GUIDE.get(next_stage, "")}
    if crisis:
        out["crisis"] = crisis
    return out


class CompleteBody(BaseModel):
    obedience_action: str = Field(default="", max_length=2000)
    grace_received: str = Field(default="", max_length=2000)


@router.post("/sessions/{sid}/complete")
def complete_session(sid: str, request: Request, body: CompleteBody) -> dict:
    user = _require_user(request)
    email = user["email"]
    to_iso = _state["to_shanghai_iso"]
    obedience = body.obedience_action.strip()
    if not obedience:
        raise HTTPException(status_code=400, detail="需要一个具体的顺服行动才能完成")

    crisis = _scan_crisis(obedience, body.grace_received)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            row = _fetch_session(cur, sid, email)
            if not row:
                raise HTTPException(status_code=404, detail="session not found")
            # completion_score：每填一栏 +20，封顶 100
            filled = sum(1 for v in (row[6], row[8], row[9], row[10]) if (v or "").strip())
            score = min(100, (filled + 1) * 20)
            sets = ["obedience_action=%s", "grace_received=%s", "stage='completed'",
                    "completion_score=%s", "updated_at=NOW()"]
            params: list = [obedience, body.grace_received.strip(), score]
            if crisis:
                sets.append("crisis_flag=%s")
                params.append(crisis["type"])
            params.extend([sid, email])
            cur.execute(
                f"UPDATE lectio_sessions SET {', '.join(sets)} WHERE id=%s AND email=%s",
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
        raise HTTPException(status_code=500, detail="complete failed")
    finally:
        _state["release_db"](conn)

    # 回流 Formation（默想=灵命滋养，导向成长）
    try:
        from formation_bridge import record_formation
        record_formation(user.get("id"), ["growth", "spiritual"], loop_broken=True,
                         reflection_active=True, emotional_intensity=4.0,
                         decision_category="lectio")
    except Exception:
        pass
    # 时间线事件
    try:
        import formation_events as _fe
        _fe.record_event(email, "lectio", "lectio", title="圣经默想 Lectio Divina",
                         summary=(_session_row(row, to_iso)["passage_ref"] or "完成默想"),
                         severity="amber" if crisis else "green")
    except Exception:
        pass

    out = {"ok": True, "session": _session_row(row, to_iso), "guidance": _STAGE_GUIDE["completed"]}
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
                f"SELECT {_SESSION_COLS} FROM lectio_sessions WHERE email=%s "
                "ORDER BY session_date DESC, created_at DESC LIMIT %s",
                (user["email"], limit),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "sessions": [_session_row(r, to_iso) for r in rows]}
