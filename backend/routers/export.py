"""
Export router — 导出我的数据 (/api/export/me)

把用户在各模块留下的属灵数据聚合成一个 JSON 返回，便于「带走自己的数据」。
每张表的查询都 best-effort：表不存在或出错则跳过，不影响其余。用户以 email 标识。
"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/export", tags=["export"])
_state: Dict[str, Any] = {}


def init_export_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# (key, SQL, 列名)  —— 全部按 email 过滤
_SOURCES = [
    ("checkins", "SELECT checkin_at, emotion_label, mood FROM user_checkins WHERE email=%s ORDER BY checkin_at DESC LIMIT 1000",
     ["time", "emotion", "mood"]),
    ("devotion_journals", "SELECT journal_date, title, scripture_text, reflection, prayer FROM devotion_journals WHERE email=%s AND deleted_at IS NULL ORDER BY journal_date DESC LIMIT 1000",
     ["date", "title", "scripture", "reflection", "prayer"]),
    ("examen", "SELECT entry_date, consolation, desolation, gratitude, confession, tomorrow_step, consolation_level FROM examen_entries WHERE email=%s ORDER BY entry_date DESC LIMIT 1000",
     ["date", "consolation", "desolation", "gratitude", "confession", "tomorrow_step", "closeness"]),
    ("gratitude", "SELECT content, created_at FROM gratitude_entries WHERE email=%s ORDER BY created_at DESC LIMIT 2000",
     ["content", "time"]),
    ("attachment_sessions", "SELECT top_target, top_intensity, risk_level, summary, created_at FROM attachment_sessions WHERE email=%s ORDER BY created_at DESC LIMIT 1000",
     ["top_target", "intensity", "risk", "summary", "time"]),
    ("waiting_cases", "SELECT waiting_for, waiting_type, created_at FROM waiting_cases WHERE email=%s ORDER BY created_at DESC LIMIT 1000",
     ["waiting_for", "type", "time"]),
    ("memory_verses", "SELECT reference, verse_text, repetitions, due_date FROM memory_verses WHERE email=%s ORDER BY created_at DESC LIMIT 1000",
     ["reference", "text", "reps", "due"]),
    ("reading_progress", "SELECT plan_id, day_key, completed_at FROM reading_plan_progress WHERE email=%s ORDER BY completed_at DESC LIMIT 2000",
     ["plan", "day", "time"]),
    ("accountability_goals", "SELECT title, detail, cadence, created_at FROM accountability_goals WHERE email=%s AND active=TRUE ORDER BY created_at",
     ["title", "detail", "cadence", "time"]),
]


@router.get("/me")
def export_me(request: Request) -> dict:
    user = _require_user(request)
    email = user["email"]
    to_iso = _state["to_shanghai_iso"]
    data: Dict[str, List[dict]] = {}
    conn = _state["get_db"]()
    try:
        for key, sql, cols in _SOURCES:
            try:
                with conn.cursor() as cur:
                    cur.execute(sql, (email,))
                    rows = cur.fetchall()
                items = []
                for r in rows:
                    rec = {}
                    for i, c in enumerate(cols):
                        v = r[i]
                        rec[c] = to_iso(v) if hasattr(v, "isoformat") else v
                    items.append(rec)
                data[key] = items
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                data[key] = []
    finally:
        _state["release_db"](conn)

    counts = {k: len(v) for k, v in data.items()}
    return {"ok": True, "account": email, "exported_at": _now_iso(to_iso),
            "counts": counts, "data": data}


def _now_iso(to_iso):
    from datetime import datetime, timezone
    return to_iso(datetime.now(timezone.utc))
