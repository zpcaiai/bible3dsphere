"""自高之事 (Stronghold) cloud persistence API.

Stores each "self-discernment" scan so the frontend's local-first history can
sync to the cloud, and exposes a non-shaming aggregate summary that mirrors the
frontend's summarizeStrongholdHistory / buildGrowthInsight.

Follows the same conventions as routers/spiritual_formation.py:
psycopg2 (sync), email-as-user_id, init_*_router loads a .sql schema at startup.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

router = APIRouter(prefix="/api/strongholds", tags=["strongholds"])
_state: Dict[str, Any] = {}

MODULE_DISCLAIMER = (
    "This tool is a spiritual formation aid. It does not replace Scripture, "
    "prayer, the Holy Spirit, the local church, pastoral care, wise "
    "accountability, or professional help when needed."
)

# 触发器有效值（与前端 TriggerType 对齐）/ valid trigger types
TRIGGER_TYPES = {
    "criticism", "failure", "uncertainty", "comparison", "rejection",
    "loneliness", "fatigue", "conflict", "temptation", "success",
    "financial_pressure", "family_pressure", "church_hurt",
    "suffering_event", "spiritual_dryness",
}

DAY_MS = 24 * 60 * 60 * 1000


# ──────────────────────────────────────────────────────────────────────────
# Pure aggregation (no DB) — mirrors frontend lib/strongholdHistory.ts
# ──────────────────────────────────────────────────────────────────────────
def _ms(iso: Any) -> int:
    """Parse an ISO timestamp (or datetime) to epoch milliseconds."""
    if iso is None:
        return 0
    if isinstance(iso, datetime):
        dt = iso
    else:
        try:
            dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        except Exception:
            return 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _sorted_counts(counter: Dict[str, int]) -> List[Dict[str, Any]]:
    return [
        {"key": k, "count": c}
        for k, c in sorted(counter.items(), key=lambda kv: kv[1], reverse=True)
    ]


def summarize_records(records: List[dict], range_days: int, now_ms: Optional[int] = None) -> dict:
    """Aggregate scan records into top strongholds (with trend), archetype
    spread, triggers (with linked strongholds), and emotions. Pure + testable."""
    if now_ms is None:
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    cutoff = now_ms - range_days * DAY_MS
    in_range = sorted(
        [r for r in records if _ms(r.get("date")) >= cutoff],
        key=lambda r: _ms(r.get("date")),
    )
    mid = cutoff + (now_ms - cutoff) / 2

    stronghold: Dict[str, int] = {}
    early: Dict[str, int] = {}
    late: Dict[str, int] = {}
    archetype: Dict[str, int] = {}
    trigger: Dict[str, int] = {}
    trigger_links: Dict[str, set] = {}
    emotion: Dict[str, int] = {}

    for r in in_range:
        code = r.get("primaryCode")
        if code:
            stronghold[code] = stronghold.get(code, 0) + 1
            half = early if _ms(r.get("date")) < mid else late
            half[code] = half.get(code, 0) + 1
        arc = r.get("archetypeCode")
        if arc:
            archetype[arc] = archetype.get(arc, 0) + 1
        tr = r.get("triggerType")
        if tr:
            trigger[tr] = trigger.get(tr, 0) + 1
            trigger_links.setdefault(tr, set())
            if code:
                trigger_links[tr].add(code)
        for e in (r.get("emotions") or []):
            emotion[e] = emotion.get(e, 0) + 1

    top_strongholds = []
    for item in _sorted_counts(stronghold):
        code, count = item["key"], item["count"]
        e, l = early.get(code, 0), late.get(code, 0)
        trend = "stable"
        if count >= 2:
            if l > e:
                trend = "rising"
            elif e > l:
                trend = "falling"
        top_strongholds.append({"code": code, "count": count, "trend": trend})

    return {
        "rangeDays": range_days,
        "totalScans": len(in_range),
        "topStrongholds": top_strongholds,
        "archetypeDistribution": [{"code": i["key"], "count": i["count"]} for i in _sorted_counts(archetype)],
        "topTriggers": [
            {"type": i["key"], "count": i["count"], "linkedStrongholds": sorted(trigger_links.get(i["key"], set()))}
            for i in _sorted_counts(trigger)
        ],
        "topEmotions": [{"emotion": i["key"], "count": i["count"]} for i in _sorted_counts(emotion)],
        "recent": list(reversed(in_range))[:10],
    }


def build_insight(summary: dict) -> dict:
    """Gentle weekly focus — mirrors frontend buildGrowthInsight."""
    tops = summary.get("topStrongholds", [])
    if summary.get("totalScans", 0) < 2 or not tops:
        return {"hasData": False, "growthSignals": [], "watchPoints": []}

    triggers = summary.get("topTriggers", [])

    def trigger_for(code: str) -> Optional[str]:
        best = None
        for t in triggers:
            if code in t.get("linkedStrongholds", []) and (best is None or t["count"] > best["count"]):
                best = t
        if best:
            return best["type"]
        return triggers[0]["type"] if triggers else None

    top = tops[0]
    focus = {
        "strongholdCode": top["code"],
        "trend": top["trend"],
        "topTrigger": trigger_for(top["code"]),
        "count": top["count"],
    }
    growth_signals = [{"strongholdCode": s["code"]} for s in tops if s["trend"] == "falling"]
    watch_points = [
        {"strongholdCode": s["code"], "trigger": trigger_for(s["code"])}
        for s in tops if s["trend"] != "falling"
    ][:2]
    return {"hasData": True, "focus": focus, "growthSignals": growth_signals, "watchPoints": watch_points}



def _day_key(v) -> str:
    return str(v or "")[:10]  # YYYY-MM-DD from iso or date


def _reduction_score(records: List[dict], code: Optional[str], range_days: int, now_ms: int) -> float:
    """How much a stronghold has eased recently (early vs late half). 0..100."""
    if not code:
        return 0.0
    cutoff = now_ms - range_days * DAY_MS
    pts = sorted(
        [r for r in records if r.get("primaryCode") == code and _ms(r.get("date")) >= cutoff],
        key=lambda r: _ms(r.get("date")),
    )
    if len(pts) < 2:
        return 0.0
    mid = cutoff + (now_ms - cutoff) / 2
    early = sum(1 for r in pts if _ms(r.get("date")) < mid)
    late = len(pts) - early
    return max(0.0, min(100.0, (early - late) / max(early, 1) * 100))


def build_profile(stronghold_records: List[dict], daily_records: List[dict], range_days: int, now_ms: Optional[int] = None) -> dict:
    """Dynamic spiritual profile merging stronghold scans + daily examens.
    Describes patterns, never labels identity. Pure + testable."""
    if now_ms is None:
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    cutoff = now_ms - range_days * DAY_MS
    sh = summarize_records(stronghold_records, range_days, now_ms)
    sh_in = [r for r in stronghold_records if _ms(r.get("date")) >= cutoff]
    daily_in = [r for r in daily_records if _ms(r.get("date")) >= cutoff]

    blocked: Dict[str, int] = {}
    for r in sh_in:
        c = r.get("blockedDoctrineCode")
        if c:
            blocked[c] = blocked.get(c, 0) + 1

    sin: Dict[str, int] = {}
    sin_emotions: Dict[str, int] = {}
    for r in daily_in:
        p = r.get("primarySin")
        if p:
            sin[p] = sin.get(p, 0) + 1
        else:
            for c in (r.get("sinPatterns") or []):
                sin[c] = sin.get(c, 0) + 1
        e = r.get("emotion")
        if e:
            sin_emotions[e] = sin_emotions.get(e, 0) + 1

    days = {_day_key(r.get("date")) for r in sh_in} | {_day_key(r.get("date")) for r in daily_in}
    active_days = len([d for d in days if d])
    consistency = round(active_days / max(range_days, 1), 3)

    insight = build_insight(sh)
    rec_focus = None
    if insight["hasData"]:
        f = insight["focus"]
        rec_focus = {
            "strongholdCode": f["strongholdCode"],
            "topTrigger": f["topTrigger"],
            "reason": "近期较常出现，可在此多倚靠基督的恩典。",
        }

    encouragements: List[str] = []
    if any(s_["trend"] == "falling" for s_ in sh["topStrongholds"]):
        encouragements.append("有模式最近出现得更少了，这是恩典在你里面工作的迹象。")
    if active_days >= max(2, range_days // 10):
        encouragements.append("你持续来到神面前省察，这本身就是恩典的记号。")
    if not encouragements:
        encouragements.append("无论你看见什么，你都是在基督里被接纳、被爱的人。")

    cautions: List[str] = []
    if any(s_["trend"] == "rising" for s_ in sh["topStrongholds"]):
        cautions.append("有模式近期上升，可留意它常被什么触发，并把它带到神面前。")

    def _ranked(d):
        return [{"code": k, "count": v} for k, v in sorted(d.items(), key=lambda kv: kv[1], reverse=True)]

    return {
        "rangeDays": range_days,
        "stronghold": {
            "dominant": sh["topStrongholds"],
            "archetypes": sh["archetypeDistribution"],
            "triggers": sh["topTriggers"],
            "blockedDoctrines": _ranked(blocked),
        },
        "sinPattern": {
            "dominant": _ranked(sin),
            "emotions": [{"emotion": k, "count": v} for k, v in sorted(sin_emotions.items(), key=lambda kv: kv[1], reverse=True)],
        },
        "rhythm": {
            "strongholdScans": sh["totalScans"],
            "dailyExamens": len(daily_in),
            "activeDays": active_days,
            "rangeDays": range_days,
            "consistency": consistency,
        },
        "recommendedFocus": rec_focus,
        "encouragements": encouragements,
        "cautions": cautions,
    }


def build_progress(stronghold_records: List[dict], daily_records: List[dict], range_days: int, now_ms: Optional[int] = None) -> dict:
    """Formation progress as direction + signals (never a performance score)."""
    if now_ms is None:
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    cutoff = now_ms - range_days * DAY_MS
    sh = summarize_records(stronghold_records, range_days, now_ms)
    sh_in = [r for r in stronghold_records if _ms(r.get("date")) >= cutoff]
    daily_in = [r for r in daily_records if _ms(r.get("date")) >= cutoff]
    total = len(sh_in) + len(daily_in)

    days = {_day_key(r.get("date")) for r in sh_in} | {_day_key(r.get("date")) for r in daily_in}
    active_days = len([d for d in days if d])

    if total < 3:
        return {
            "rangeDays": range_days, "overallTrend": "insufficient_data",
            "awarenessScore": 0.0, "strongholdReductionScore": 0.0, "engagementScore": 0.0,
            "growthSignals": [], "struggleSignals": [], "nextGrowthEdge": None,
        }

    engagement = max(0.0, min(100.0, active_days / max(range_days, 1) * 100 * 3))  # ~每3天一次≈满
    variety = len({s_["code"] for s_ in sh["topStrongholds"]})
    awareness = max(0.0, min(100.0, engagement * 0.7 + min(variety, 5) / 5 * 100 * 0.3))

    top = sh["topStrongholds"][0]["code"] if sh["topStrongholds"] else None
    reduction = _reduction_score(stronghold_records, top, range_days, now_ms)

    rising = [s_["code"] for s_ in sh["topStrongholds"] if s_["trend"] == "rising"]
    falling = [s_["code"] for s_ in sh["topStrongholds"] if s_["trend"] == "falling"]

    if reduction > 0 and len(rising) <= len(falling):
        overall = "growing"
    elif len(rising) > len(falling) and len(rising) >= 2:
        overall = "struggling"
    else:
        overall = "stable"

    edge = None
    ins = build_insight(sh)
    if ins["hasData"]:
        f = ins["focus"]
        edge = {"strongholdCode": f["strongholdCode"], "topTrigger": f["topTrigger"]}

    return {
        "rangeDays": range_days,
        "overallTrend": overall,
        "awarenessScore": round(awareness, 1),
        "strongholdReductionScore": round(reduction, 1),
        "engagementScore": round(engagement, 1),
        "growthSignals": [{"strongholdCode": c} for c in falling],
        "struggleSignals": [{"strongholdCode": c} for c in rising],
        "nextGrowthEdge": edge,
    }


# ──────────────────────────────────────────────────────────────────────────
# Wiring + DB helpers
# ──────────────────────────────────────────────────────────────────────────
def init_strongholds_router(*, get_db, release_db, get_session_user, to_shanghai_iso, root_dir=None) -> None:
    _state.update(locals())
    if get_db and release_db:
        _init_tables(get_db, release_db, root_dir)


def _init_tables(get_db, release_db, root_dir=None) -> None:
    schema_path = Path(root_dir or Path(__file__).resolve().parents[2]) / "backend" / "stronghold_schema.sql"
    sql = schema_path.read_text(encoding="utf-8")
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        release_db(conn)


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _db_user_id(user: dict) -> str:
    return str(user.get("email") or user.get("id") or "")


def _new_id() -> str:
    return f"sh_{uuid.uuid4().hex}"


def _Json(obj):
    try:
        from psycopg2.extras import Json
        return Json(obj)
    except Exception:
        return obj


def _json(value, fallback):
    return fallback if value is None else value


def _iso(value):
    if value is None:
        return None
    to_iso = _state.get("to_shanghai_iso")
    if to_iso:
        try:
            return to_iso(value)
        except Exception:
            pass
    try:
        return value.isoformat()
    except Exception:
        return str(value)


def _range_days(range_str: Optional[str]) -> int:
    if not range_str:
        return 30
    s = str(range_str).strip().lower()
    if s in ("all", "max"):
        return 3650
    s = s.rstrip("d")
    try:
        return max(1, min(3650, int(s)))
    except Exception:
        return 30


# ──────────────────────────────────────────────────────────────────────────
# Models + serialization
# ──────────────────────────────────────────────────────────────────────────
class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class ScanIn(CamelModel):
    id: Optional[str] = Field(default=None, max_length=120)
    date: Optional[str] = Field(default=None, max_length=40)
    text: str = Field(default="", max_length=8000)
    emotions: List[str] = Field(default_factory=list, max_length=30)
    primary_code: Optional[str] = Field(default=None, alias="primaryCode", max_length=80)
    detected_codes: List[str] = Field(default_factory=list, alias="detectedCodes", max_length=30)
    archetype_code: Optional[str] = Field(default=None, alias="archetypeCode", max_length=80)
    blocked_doctrine_code: Optional[str] = Field(default=None, alias="blockedDoctrineCode", max_length=80)
    trigger_type: Optional[str] = Field(default=None, alias="triggerType", max_length=40)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("emotions", "detected_codes")
    @classmethod
    def clean_list(cls, values):
        return [str(v)[:80] for v in values]

    @field_validator("trigger_type")
    @classmethod
    def clean_trigger(cls, v):
        return v if v in TRIGGER_TYPES else None


def _scan_row(row) -> dict:
    return {
        "id": row[0],
        "userId": row[1],
        "date": _iso(row[2]),
        "text": row[3] or "",
        "emotions": _json(row[4], []),
        "primaryCode": row[5],
        "detectedCodes": _json(row[6], []),
        "archetypeCode": row[7],
        "blockedDoctrineCode": row[8],
        "triggerType": row[9],
        "confidence": float(row[10]) if row[10] is not None else 0.0,
    }


_COLS = (
    "id, user_id, scanned_at, text, emotions, primary_code, detected_codes, "
    "archetype_code, blocked_doctrine_code, trigger_type, confidence"
)


# ──────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────
@router.post("/scans")
def upsert_scan(payload: ScanIn, request: Request):
    user = _require_user(request)
    uid = _db_user_id(user)
    # 仅保存有信号的记录（与前端一致）/ only persist records that detected a pattern
    if not payload.primary_code:
        return {"record": None, "skipped": True}

    scan_id = payload.id or _new_id()
    scanned_at = payload.date or datetime.now(timezone.utc).isoformat()

    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO stronghold_scans
                  (id, user_id, scanned_at, text, emotions, primary_code,
                   detected_codes, archetype_code, blocked_doctrine_code,
                   trigger_type, confidence)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                  scanned_at=EXCLUDED.scanned_at, text=EXCLUDED.text,
                  emotions=EXCLUDED.emotions, primary_code=EXCLUDED.primary_code,
                  detected_codes=EXCLUDED.detected_codes,
                  archetype_code=EXCLUDED.archetype_code,
                  blocked_doctrine_code=EXCLUDED.blocked_doctrine_code,
                  trigger_type=EXCLUDED.trigger_type,
                  confidence=EXCLUDED.confidence, updated_at=NOW()
                WHERE stronghold_scans.user_id = %s
                RETURNING {_COLS}
                """,
                (
                    scan_id, uid, scanned_at, payload.text,
                    _Json(payload.emotions), payload.primary_code,
                    _Json(payload.detected_codes), payload.archetype_code,
                    payload.blocked_doctrine_code, payload.trigger_type,
                    payload.confidence, uid,
                ),
            )
            row = cur.fetchone()
            # 若 id 冲突且归属他人，ON CONFLICT ... WHERE 不会更新任何行 → 拒绝越权覆盖
            if row is None:
                conn.rollback()
                raise HTTPException(status_code=409, detail="记录不存在或无权修改")
        conn.commit()
        try:
            import formation_events as _fe
            _fe.record_event(uid, "strongholds", "diagnosis", domain=payload.primary_code,
                             title="营垒扫描", summary=(payload.text or "")[:120] or None,
                             severity="amber", ref_id="scan:%s" % scan_id)
        except Exception:
            pass
        return {"record": _scan_row(row)}
    except HTTPException:
        raise
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[strongholds] save scan failed: {exc!r}", flush=True)
        raise HTTPException(status_code=500, detail="Failed to save scan")
    finally:
        _state["release_db"](conn)


@router.get("/scans")
def list_scans(request: Request, range: str = Query(default="365d"), limit: int = Query(default=500, ge=1, le=2000)):
    user = _require_user(request)
    uid = _db_user_id(user)
    days = _range_days(range)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {_COLS} FROM stronghold_scans
                WHERE user_id=%s AND scanned_at >= NOW() - (%s || ' days')::interval
                ORDER BY scanned_at DESC
                LIMIT %s
                """,
                (uid, str(days), limit),
            )
            rows = cur.fetchall()
        return {"items": [_scan_row(r) for r in rows]}
    finally:
        _state["release_db"](conn)


@router.delete("/scans")
def clear_scans(request: Request):
    user = _require_user(request)
    uid = _db_user_id(user)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM stronghold_scans WHERE user_id=%s", (uid,))
            deleted = cur.rowcount
        conn.commit()
        return {"deleted": deleted}
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to clear scans: {exc}")
    finally:
        _state["release_db"](conn)


@router.delete("/scans/{scan_id}")
def delete_scan(scan_id: str, request: Request):
    user = _require_user(request)
    uid = _db_user_id(user)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM stronghold_scans WHERE id=%s AND user_id=%s", (scan_id, uid))
            deleted = cur.rowcount
        conn.commit()
        return {"deleted": deleted}
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to delete scan: {exc}")
    finally:
        _state["release_db"](conn)


@router.get("/summary")
def scan_summary(request: Request, range: str = Query(default="30d")):
    user = _require_user(request)
    uid = _db_user_id(user)
    days = _range_days(range)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLS} FROM stronghold_scans WHERE user_id=%s ORDER BY scanned_at DESC LIMIT 2000",
                (uid,),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)

    records = [_scan_row(r) for r in rows]
    summary = summarize_records(records, days)
    return {"summary": summary, "insight": build_insight(summary), "disclaimer": MODULE_DISCLAIMER}


# ──────────────────────────────────────────────────────────────────────────
# Profile + progress (server-side stats merging stronghold scans + daily examens)
# ──────────────────────────────────────────────────────────────────────────
def _load_stronghold_records(uid: str) -> List[dict]:
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLS} FROM stronghold_scans WHERE user_id=%s ORDER BY scanned_at DESC LIMIT 2000",
                (uid,),
            )
            rows = cur.fetchall()
        return [_scan_row(r) for r in rows]
    finally:
        _state["release_db"](conn)


def _load_daily_examens(uid: str, days: int) -> List[dict]:
    """Read daily examens to merge the sin-pattern dimension. Safe if table absent."""
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT date, strongest_emotion, triggers, detected_sin_patterns, selected_primary_sin_pattern
                FROM spiritual_daily_examens
                WHERE user_id=%s AND date >= (NOW() - (%s || ' days')::interval)::date
                ORDER BY date DESC LIMIT 2000
                """,
                (uid, str(days)),
            )
            rows = cur.fetchall()
        return [
            {
                "date": str(r[0]),
                "emotion": r[1],
                "triggers": _json(r[2], []),
                "sinPatterns": _json(r[3], []),
                "primarySin": r[4],
            }
            for r in rows
        ]
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []
    finally:
        _state["release_db"](conn)


@router.get("/profile")
def spiritual_profile(request: Request, range: str = Query(default="90d")):
    user = _require_user(request)
    uid = _db_user_id(user)
    days = _range_days(range)
    sh = _load_stronghold_records(uid)
    daily = _load_daily_examens(uid, days)
    return {"profile": build_profile(sh, daily, days), "disclaimer": MODULE_DISCLAIMER}


@router.get("/progress")
def formation_progress(request: Request, range: str = Query(default="30d")):
    user = _require_user(request)
    uid = _db_user_id(user)
    days = _range_days(range)
    sh = _load_stronghold_records(uid)
    daily = _load_daily_examens(uid, days)
    return {"progress": build_progress(sh, daily, days), "disclaimer": MODULE_DISCLAIMER}
