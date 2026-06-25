"""
formation_events.py — 统一成长事件流 + 画像聚合（整合层 Phase 0）

各模块（诊断/重写/操练/复盘/危机/恩赐…）产出后 best-effort 写入 formation_events，
形成「一个人」的纵向成长时间轴；growth_state 读时从事件流 + worldview_profiles 聚合当前画像。
不替换任何既有逻辑；失败不影响主流程。email 为用户键。DB 走 core.deps。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _acquire():
    try:
        from core.deps import acquire_conn, release_conn
        return acquire_conn(), release_conn
    except Exception:
        return None, None


def _Json(obj):
    try:
        from psycopg2.extras import Json
        return Json(obj)
    except Exception:
        import json as _json
        return _json.dumps(obj)


def record_event(email: str, source: str, event_type: str, *, domain: Optional[str] = None,
                 title: Optional[str] = None, summary: Optional[str] = None,
                 severity: Optional[str] = None, refs: Optional[list] = None,
                 payload: Optional[dict] = None, ref_id: Optional[str] = None) -> Optional[int]:
    """写入一条成长事件（best-effort，幂等需带 ref_id）。返回 id 或 None。"""
    if not email or not source or not event_type:
        return None
    conn, release = _acquire()
    if conn is None:
        return None
    eid = None
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO formation_events "
                "(email, source, event_type, domain, title, summary, severity, refs, payload, ref_id) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING id",
                (email, source[:40], event_type[:40], (domain or None),
                 (title[:300] if title else None), ((summary or "")[:2000] or None),
                 (severity or None), _Json(refs or []), _Json(payload or {}), (ref_id or None)),
            )
            row = cur.fetchone()
            eid = row[0] if row else None
            conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        eid = None
    finally:
        if release:
            release(conn)
    return eid


def timeline(email: str, *, limit: int = 100, source: Optional[str] = None,
             event_type: Optional[str] = None) -> List[Dict[str, Any]]:
    conn, release = _acquire()
    if conn is None:
        return []
    out: List[Dict[str, Any]] = []
    try:
        clauses = ["email=%s"]
        params: List[Any] = [email]
        if source:
            clauses.append("source=%s"); params.append(source)
        if event_type:
            clauses.append("event_type=%s"); params.append(event_type)
        params.append(min(int(limit or 100), 500))
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, occurred_at, source, event_type, domain, title, summary, severity, refs, payload, ref_id "
                "FROM formation_events WHERE " + " AND ".join(clauses) +
                " ORDER BY occurred_at DESC, id DESC LIMIT %s",
                tuple(params),
            )
            for r in cur.fetchall():
                out.append({
                    "id": r[0], "occurredAt": r[1].isoformat() if r[1] else None,
                    "source": r[2], "type": r[3], "domain": r[4], "title": r[5],
                    "summary": r[6], "severity": r[7], "refs": r[8] or [], "payload": r[9] or {}, "refId": r[10],
                })
    except Exception:
        out = []
    finally:
        if release:
            release(conn)
    return out


def growth_state(email: str) -> Dict[str, Any]:
    conn, release = _acquire()
    state: Dict[str, Any] = {
        "hasData": False, "summary": None, "dominantIdols": [], "activeThemes": [],
        "currentFocus": None, "maturityLevel": None, "riskLevel": "green",
        "lastEventAt": None, "eventCount": 0, "bySource": {},
    }
    if conn is None:
        return state
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*), max(occurred_at), "
                " max(CASE WHEN severity IN ('red','high') THEN 3 "
                "          WHEN severity IN ('amber','medium') THEN 2 ELSE 1 END) "
                "FROM formation_events WHERE email=%s", (email,))
            row = cur.fetchone()
            cnt = (row[0] or 0) if row else 0
            state["eventCount"] = cnt
            state["lastEventAt"] = row[1].isoformat() if (row and row[1]) else None
            state["riskLevel"] = {3: "red", 2: "amber", 1: "green"}.get((row[2] if row else 1) or 1, "green")
            cur.execute("SELECT source, count(*) FROM formation_events WHERE email=%s GROUP BY source", (email,))
            state["bySource"] = {r[0]: r[1] for r in cur.fetchall()}
            cur.execute(
                "SELECT domain, count(*) FROM formation_events WHERE email=%s AND domain IS NOT NULL "
                "AND occurred_at > now() - interval '60 days' GROUP BY domain ORDER BY count(*) DESC LIMIT 6",
                (email,))
            state["activeThemes"] = [r[0] for r in cur.fetchall()]
            state["hasData"] = cnt > 0
            # 用既有 worldview 画像富化（若存在）
            try:
                cur.execute(
                    "SELECT summary, dominant_idols, maturity_level, current_growth_focus, risk_level "
                    "FROM worldview_profiles WHERE email=%s", (email,))
                p = cur.fetchone()
                if p:
                    state["summary"] = p[0]
                    state["dominantIdols"] = p[1] or []
                    state["maturityLevel"] = p[2]
                    state["currentFocus"] = p[3]
                    if p[4]:
                        state["riskLevel"] = p[4]
                    state["hasData"] = True
            except Exception:
                pass
    except Exception:
        pass
    finally:
        if release:
            release(conn)
    return state


def next_step(email: str) -> Dict[str, Any]:
    """节律引擎（Phase 0 规则版）：据当前画像给出今日该做的一件事。"""
    st = growth_state(email)
    if st.get("riskLevel") == "red":
        return {"kind": "care", "title": "先照顾你的安全与心灵",
                "reason": "近期检测到较重的属灵 / 情绪负荷",
                "action": "此刻先不分析。把重担带到神面前，并联系你信任的人或专业支持。"}
    focus = st.get("currentFocus")
    if focus:
        return {"kind": "practice", "title": "针对当前焦点的一次操练",
                "reason": "当前成长焦点：%s" % focus,
                "action": "今天围绕「%s」做一次默想 + 一句反谎言祷告 + 一个具体顺服行动。" % focus}
    if not st.get("hasData"):
        return {"kind": "diagnose", "title": "先做一次世界观 / 属灵诊断",
                "reason": "还没有足够的成长数据",
                "action": "到「世界观 · 生命叙事」做一次诊断，系统会据此给出操练方向。"}
    return {"kind": "review", "title": "做一次本周复盘",
            "reason": "把近期的经历交在神面前",
            "action": "回顾本周的观察、感恩、悔改与下一步顺服。"}
