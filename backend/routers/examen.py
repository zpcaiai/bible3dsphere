"""
Examen router — 每日省察 (/api/examen)

  GET  /api/examen/today      今天的省察（或空）
  POST /api/examen            保存/更新今天的省察（每天一条，upsert）+ 回流 formation
  GET  /api/examen/history    历史

依纳爵式：安慰/枯涩 → 感恩 → 求恕 → 明日微顺服。不定罪、温柔陪伴。
"""
from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/examen", tags=["examen"])

_state: Dict[str, Any] = {}


def init_examen_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _row(r, to_iso) -> dict:
    return {
        "id": r[0], "entry_date": str(r[1]) if r[1] else "",
        "consolation": r[2] or "", "desolation": r[3] or "",
        "gratitude": r[4] or "", "confession": r[5] or "",
        "tomorrow_step": r[6] or "", "consolation_level": r[7],
        "created_at": to_iso(r[8]),
    }


_COLS = ("id, entry_date, consolation, desolation, gratitude, confession, "
         "tomorrow_step, consolation_level, created_at")


class ExamenSave(BaseModel):
    consolation: str = Field(default="", max_length=4000)
    desolation: str = Field(default="", max_length=4000)
    gratitude: str = Field(default="", max_length=2000)
    confession: str = Field(default="", max_length=2000)
    tomorrow_step: str = Field(default="", max_length=2000)
    consolation_level: float = Field(default=5, ge=0, le=10)


@router.get("/today")
def get_today(request: Request) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLS} FROM examen_entries "
                "WHERE email=%s AND entry_date = (NOW() AT TIME ZONE 'Asia/Shanghai')::date",
                (user["email"],),
            )
            row = cur.fetchone()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "entry": _row(row, to_iso) if row else None}


@router.post("")
def save(request: Request, body: ExamenSave) -> dict:
    user = _require_user(request)
    email = user["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO examen_entries "
                "(id, email, entry_date, consolation, desolation, gratitude, confession, "
                " tomorrow_step, consolation_level) "
                "VALUES (%s,%s,(NOW() AT TIME ZONE 'Asia/Shanghai')::date,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (email, entry_date) DO UPDATE SET "
                " consolation=EXCLUDED.consolation, desolation=EXCLUDED.desolation, "
                " gratitude=EXCLUDED.gratitude, confession=EXCLUDED.confession, "
                " tomorrow_step=EXCLUDED.tomorrow_step, "
                " consolation_level=EXCLUDED.consolation_level, updated_at=NOW()",
                (uuid.uuid4().hex, email, body.consolation.strip(), body.desolation.strip(),
                 body.gratitude.strip(), body.confession.strip(),
                 body.tomorrow_step.strip(), body.consolation_level),
            )
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"save failed: {exc}")
    finally:
        _state["release_db"](conn)

    # 回流 Formation（省察=reflection；亲近感高=growth/spiritual，低=轻推 fear）
    try:
        from formation_bridge import record_formation
        lvl = float(body.consolation_level)
        if lvl >= 6:
            pats, lb, emo = ["growth", "spiritual"], True, 4.0
        elif lvl <= 3:
            pats, lb, emo = ["fear"], False, 6.0
        else:
            pats, lb, emo = ["growth"], False, 5.0
        record_formation(user.get("id"), pats, loop_broken=lb,
                         reflection_active=True, emotional_intensity=emo,
                         decision_category="examen")
    except Exception:
        pass
    try:
        from routers.semantic_search import index_content
        from datetime import datetime as _dt
        try:
            from zoneinfo import ZoneInfo as _Z
            _d = _dt.now(_Z("Asia/Shanghai")).date().isoformat()
        except Exception:
            _d = _dt.utcnow().date().isoformat()
        _itxt = chr(10).join(t for t in [body.consolation, body.desolation, body.gratitude,
                                         body.confession, body.tomorrow_step] if t and t.strip())
        if _itxt.strip():
            index_content(email=email, source_type="examen", content=_itxt, source_id="examen:" + _d)
    except Exception:
        pass
    return {"ok": True}


@router.get("/history")
def history(request: Request, limit: int = Query(default=30, ge=1, le=120)) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLS} FROM examen_entries WHERE email=%s "
                "ORDER BY entry_date DESC LIMIT %s",
                (user["email"], limit),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "entries": [_row(r, to_iso) for r in rows]}
