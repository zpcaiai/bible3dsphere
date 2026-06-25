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
        "lastBySource": {}, "recentFlags": [],
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
            cur.execute("SELECT source, max(occurred_at) FROM formation_events WHERE email=%s GROUP BY source", (email,))
            state["lastBySource"] = {r[0]: (r[1].isoformat() if r[1] else None) for r in cur.fetchall()}
            cur.execute(
                "SELECT source, domain, title, severity, occurred_at FROM formation_events "
                "WHERE email=%s AND severity IN ('amber','red','medium','high') "
                "AND occurred_at > now() - interval '21 days' "
                "ORDER BY occurred_at DESC, id DESC LIMIT 5", (email,))
            state["recentFlags"] = [{"source": r[0], "domain": r[1], "title": r[2],
                                     "severity": r[3], "occurredAt": r[4].isoformat() if r[4] else None}
                                    for r in cur.fetchall()]
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


def _days_since(iso: Optional[str]) -> Optional[float]:
    if not iso:
        return None
    from datetime import datetime, timezone
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0
    except Exception:
        return None


# 节律纪律：source -> (中文名, 提醒阈值天数, 前端路由)
_RHYTHM = [
    ("checkin", "情绪觉察 / 签到", 2, "checkin"),
    ("prayer", "祷告", 3, "prayer"),
    ("bible_reading", "读经", 3, "bible"),
    ("habits", "感恩 / 操练", 3, "practice"),
    ("examen", "省察 Examen", 5, "examen"),
    ("weekly_review", "每周复盘", 8, "weekly_review"),
]


def next_step(email: str, st: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """跨域节律引擎（规则版）：读 growth_state 的各域信号 + 最近事件，按优先级给出下一步。

    顶层仍含 kind/title/reason/action（向后兼容 SoulDashboard），并附：
      steps   —— 去重后的候选清单（最多 3 条），供 onboarding / dashboard 展示
      signals —— 决策依据（风险、偶像、活跃主题、逾期纪律），便于解释为何这样推荐
    可传入 st 复用一次已算好的画像（onboarding 用）。
    """
    st = st or growth_state(email)
    last = st.get("lastBySource") or {}
    flags = st.get("recentFlags") or []
    idols = st.get("dominantIdols") or []
    themes = set(st.get("activeThemes") or [])
    focus = st.get("currentFocus")
    cands: List[Dict[str, Any]] = []

    # 0) 安全优先
    if st.get("riskLevel") == "red":
        cands.append({"priority": 0, "kind": "care", "route": "care",
                      "title": "先照顾你的安全与心灵",
                      "reason": "近期检测到较重的属灵 / 情绪负荷",
                      "action": "此刻先不分析。把重担带到神面前，并联系你信任的人或专业支持。"})

    # 1) 有未跟进的诊断红/琥珀旗：落到一次操练
    if flags:
        f = flags[0]
        dsf = _days_since(f.get("occurredAt"))
        dsp = _days_since(last.get("habits"))
        if dsp is None or (dsf is not None and dsp > dsf):
            dom = f.get("domain") or f.get("title") or "近期的发现"
            cands.append({"priority": 1, "kind": "practice", "route": "practice", "domain": f.get("domain"),
                          "title": "把「%s」落到一次操练" % dom,
                          "reason": "最近一次%s仍未跟进" % (f.get("title") or "诊断"),
                          "action": "围绕「%s」做：默想一段经文 + 一句反谎言祷告 + 一个具体顺服行动。" % dom})

    # 2) 有明显偶像但近期没做真理 / 叙事更新
    if idols and not ({"truth", "narrative", "worldview", "idolatry"} & themes):
        cands.append({"priority": 2, "kind": "truth", "route": "discernment", "domain": "truth",
                      "title": "为「%s」做一次真理映射" % idols[0],
                      "reason": "画像显示「%s」可能正在靠近内心中心" % idols[0],
                      "action": "到「辨识 · 真理映射」把谎言写下来，让圣经真理重构它，再写进新的叙事。"})

    # 3) 节律纪律里最久没碰的一项
    overdue = []
    for src, name, thr, route in _RHYTHM:
        d = _days_since(last.get(src))
        if d is None or d > thr:
            overdue.append((d if d is not None else 9999.0, src, name, route))
    overdue.sort(reverse=True)
    if overdue and st.get("hasData"):
        gap, src, name, route = overdue[0]
        reason = ("还没有开始" + name) if gap >= 9999 else ("已经 %d 天没有%s" % (int(gap), name))
        cands.append({"priority": 3, "kind": "rhythm", "route": route, "domain": src,
                      "title": "恢复你的%s节律" % name, "reason": reason,
                      "action": "今天用一小步重启「%s」，不求多，只求在神面前真实。" % name})

    # 4) 当前成长焦点
    if focus:
        cands.append({"priority": 4, "kind": "practice", "route": "practice", "domain": focus,
                      "title": "针对当前焦点的一次操练",
                      "reason": "当前成长焦点：%s" % focus,
                      "action": "今天围绕「%s」做一次默想 + 一句反谎言祷告 + 一个具体顺服行动。" % focus})

    # 5) 完全没有数据：先做基线诊断
    if not st.get("hasData"):
        cands.append({"priority": 5, "kind": "diagnose", "route": "onboarding",
                      "title": "先做一次基线属灵诊断",
                      "reason": "还没有足够的成长数据",
                      "action": "用 3–5 分钟做一次基线诊断，系统据此为你生成个性化的成长路径。"})

    # 6) 兜底：本周复盘
    cands.append({"priority": 8, "kind": "review", "route": "weekly_review",
                  "title": "做一次本周复盘", "reason": "把近期的经历交在神面前",
                  "action": "回顾本周的观察、感恩、悔改与下一步顺服。"})

    cands.sort(key=lambda c: c["priority"])
    steps: List[Dict[str, Any]] = []
    seen = set()
    for c in cands:
        key = c.get("route") or c["kind"]
        if key in seen:
            continue
        seen.add(key)
        c2 = {k: v for k, v in c.items() if k != "priority"}
        steps.append(c2)
        if len(steps) >= 3:
            break
    top = dict(steps[0])
    top["steps"] = steps
    top["signals"] = {
        "riskLevel": st.get("riskLevel"), "hasData": st.get("hasData"),
        "dominantIdols": idols[:3], "activeThemes": st.get("activeThemes") or [],
        "overdue": [o[2] for o in overdue][:4], "eventCount": st.get("eventCount", 0),
    }
    return top
