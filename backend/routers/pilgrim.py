"""Pilgrim router — 天路客 (/api/pilgrim). 据近期状态定位天路历程所在地。"""
from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

try:
    from backend import pilgrim_engine as engine
except Exception:  # pragma: no cover
    import pilgrim_engine as engine  # type: ignore

router = APIRouter(prefix="/api/pilgrim", tags=["pilgrim"])
_state: Dict[str, Any] = {}

_POS = {"喜乐", "感恩", "平静", "盼望", "爱"}
_EMO_ZH = {"anxiety": "焦虑", "fear": "恐惧", "sadness": "悲伤", "joy": "喜乐",
           "peace": "平静", "gratitude": "感恩", "hope": "盼望", "anger": "愤怒",
           "loneliness": "孤独", "shame": "羞耻"}


def init_pilgrim_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _gather(email: str) -> Dict[str, Any]:
    sig: Dict[str, Any] = {}
    try:
        conn = _state["get_db"]()
    except Exception:
        return sig
    try:
        with conn.cursor() as cur:
            # 最近一次低潮体检
            try:
                cur.execute("SELECT index_score, ratings FROM spiritual_checkups "
                            "WHERE email=%s ORDER BY created_at DESC LIMIT 1", (email,))
                row = cur.fetchone()
                if row:
                    sig["low_index"] = float(row[0] or 0)
                    r = row[1] if isinstance(row[1], dict) else {}
                    if float(r.get("assurance_loss", 0) or 0) >= 6:
                        sig["doubt"] = True
            except Exception:
                pass
            # 最近主导情绪（近 14 天 checkin）
            try:
                cur.execute("SELECT emotion_label FROM user_checkins WHERE email=%s "
                            "AND checkin_at > NOW() - INTERVAL '14 days'", (email,))
                counts: Dict[str, int] = {}
                for (lab,) in cur.fetchall():
                    if not lab:
                        continue
                    for en, zh in _EMO_ZH.items():
                        if zh and zh in lab:
                            counts[zh] = counts.get(zh, 0) + 1
                if counts:
                    dom = max(counts.items(), key=lambda kv: kv[1])[0]
                    sig["emotion"] = dom
                    if dom == "恐惧":
                        sig["fear"] = True
                    if dom in _POS:
                        sig["positive"] = True
            except Exception:
                pass
            # 最近偶像
            try:
                cur.execute("SELECT top_target FROM attachment_sessions WHERE email=%s "
                            "ORDER BY created_at DESC LIMIT 1", (email,))
                row = cur.fetchone()
                if row and row[0]:
                    sig["idol"] = row[0]
            except Exception:
                pass
    finally:
        try:
            _state["release_db"](conn)
        except Exception:
            pass
    return sig


@router.get("/current")
def current(request: Request) -> dict:
    user = _require_user(request)
    email = user["email"]
    sig = _gather(email)
    key = engine.locate(sig)
    p = engine.place(key)

    # 记录旅程（仅当与上次不同）
    try:
        conn = _state["get_db"]()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT place_key FROM pilgrim_visits WHERE email=%s "
                            "ORDER BY created_at DESC LIMIT 1", (email,))
                last = cur.fetchone()
                if not last or last[0] != key:
                    cur.execute("INSERT INTO pilgrim_visits (id, email, place_key) VALUES (%s,%s,%s)",
                                (uuid.uuid4().hex, email, key))
                    conn.commit()
        finally:
            _state["release_db"](conn)
    except Exception:
        pass

    return {"ok": True, "current": key, "place": p, "places": engine.PLACES, "signals": sig}


@router.get("/journey")
def journey(request: Request) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT place_key, created_at FROM pilgrim_visits WHERE email=%s "
                        "ORDER BY created_at DESC LIMIT 30", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "visits": [{"place_key": r[0],
                                    "name": engine.place(r[0])["name"],
                                    "at": to_iso(r[1])} for r in rows]}
