"""
Pastoral router — 每周「牧养小结」 (/api/pastoral/weekly)

聚合最近 7 天的 checkin 情绪、偶像监测、等候之路信号，交给 pastoral_engine
生成温柔的牧养小结。只读、不写库。用户以 email 标识。
"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request

try:
    from backend import pastoral_engine as engine
except Exception:  # pragma: no cover
    import pastoral_engine as engine  # type: ignore

router = APIRouter(prefix="/api/pastoral", tags=["pastoral"])

_state: Dict[str, Any] = {}


def init_pastoral_router(*, get_db, release_db, get_session_user) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.get("/weekly")
def weekly(request: Request) -> dict:
    user = _require_user(request)
    email = user["email"]
    data: Dict[str, Any] = {
        "checkin_count": 0, "dominant_emotion": "", "emotion_counts": {},
        "top_attachment": None, "waiting_types": [], "activity_count": 0,
    }
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            # checkin 情绪（近 7 天）
            try:
                cur.execute(
                    "SELECT emotion_label, data FROM user_checkins "
                    "WHERE email=%s AND checkin_at > NOW() - INTERVAL '7 days'",
                    (email,),
                )
                emo_counts: Dict[str, int] = {}
                cc = 0
                for label, d in cur.fetchall():
                    cc += 1
                    dd = d if isinstance(d, dict) else {}
                    lab = label or dd.get("emotionLabel") or dd.get("emotion_label") or ""
                    # 中文标签 → 英文键（与 pastoral_engine EMOTION_ZH 对齐）
                    for en, zh in engine.EMOTION_ZH.items():
                        if zh and zh in lab:
                            emo_counts[en] = emo_counts.get(en, 0) + 1
                            break
                data["checkin_count"] = cc
                data["emotion_counts"] = emo_counts
                if emo_counts:
                    data["dominant_emotion"] = max(emo_counts.items(), key=lambda kv: kv[1])[0]
            except Exception:
                pass

            # 偶像监测（近 7 天最高依附）
            try:
                cur.execute(
                    "SELECT top_target, top_intensity, risk_level FROM attachment_sessions "
                    "WHERE email=%s AND created_at > NOW() - INTERVAL '7 days' "
                    "ORDER BY top_intensity DESC LIMIT 1",
                    (email,),
                )
                row = cur.fetchone()
                if row and row[0]:
                    try:
                        from idolatry_engine import IDOL_INDEX
                        name = IDOL_INDEX.get(row[0], {}).get("name", row[0])
                    except Exception:
                        name = row[0]
                    data["top_attachment"] = {"name": name, "risk": row[2]}
            except Exception:
                pass

            # 等候之路（近 7 天类型）
            try:
                cur.execute(
                    "SELECT DISTINCT waiting_type FROM waiting_cases "
                    "WHERE email=%s AND created_at > NOW() - INTERVAL '7 days'",
                    (email,),
                )
                data["waiting_types"] = [r[0] for r in cur.fetchall() if r[0]]
            except Exception:
                pass
    finally:
        _state["release_db"](conn)

    att = 1 if data["top_attachment"] else 0
    data["activity_count"] = data["checkin_count"] + att + len(data["waiting_types"])
    return {"ok": True, **engine.summarize(data)}
