"""
care_engine.py — Advanced Batch · Module 3 (Group Leader Care Dashboard)

A small-group leader sees CARE SIGNALS, never private data. By construction the
dashboard reads only from ``care_signals`` (authorised summaries) — it can never
surface raw reflection logs, unauthorised diagnostic findings, "spiritual
scores", or rankings, because those columns are not in the query at all.

Visibility rules:
  • A signal is shown only if the member consented (consent_share + visible_*)
    OR it is a crisis escalation (signal_level in high/critical).
  • Pastor-only signals are hidden from plain group leaders.
  • Every dashboard view and care action is written to audit_logs.

Functions are cursor-based (the router owns the connection) so the payload
builder is unit-testable with a fake cursor under ``-m no_db``.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

# Roles (in church_members.role) that may use the care dashboard.
LEADER_ROLES = {"leader", "small_group_leader", "co_leader"}
PASTOR_ROLES = {"pastor", "elder", "owner", "admin"}
CARE_ROLES = LEADER_ROLES | PASTOR_ROLES

ACTION_TYPES = {"pray", "message", "meet_1on1", "refer_to_pastor", "follow_up"}

_LEVEL_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
HIGH_TOUCH_NOTICE = "这个情况需要真实关怀，请尽快联系本人，并按教会关怀流程处理。"


def member_role(cur, email: str, church_id: int) -> Optional[str]:
    cur.execute(
        "SELECT role FROM church_members WHERE church_id=%s AND email=%s LIMIT 1",
        (church_id, email),
    )
    row = cur.fetchone()
    return row[0] if row else None


def can_view_care(role: Optional[str]) -> bool:
    return (role or "") in CARE_ROLES


def is_pastor_level(role: Optional[str]) -> bool:
    return (role or "") in PASTOR_ROLES


def _mask_email(email: str) -> str:
    try:
        local, _, domain = email.partition("@")
        head = local[:2]
        return f"{head}{'*' * max(1, len(local) - 2)}@{domain}" if domain else head + "***"
    except Exception:
        return "member"


def _display_name(cur, email: str) -> str:
    try:
        cur.execute("SELECT nickname FROM users WHERE email=%s LIMIT 1", (email,))
        row = cur.fetchone()
        if row and (row[0] or "").strip():
            return row[0].strip()
    except Exception:
        pass
    return _mask_email(email)


# ── Build the dashboard payload (authorised summaries only) ──────────────────
_DASHBOARD_SQL = """
    SELECT id, email, signal_type, signal_level, title, summary,
           suggested_action, requires_followup, updated_at
    FROM care_signals
    WHERE church_id = %s
      AND resolved = FALSE
      AND (
            (consent_share = TRUE AND (visible_to_group_leader = TRUE OR visible_to_pastor = TRUE))
         OR signal_level IN ('high', 'critical')
      )
      AND (%s = TRUE OR visible_to_group_leader = TRUE)   -- non-pastors don't see pastor-only
    ORDER BY CASE signal_level WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                               WHEN 'medium' THEN 2 ELSE 3 END,
             updated_at DESC
    LIMIT 200
"""


def build_dashboard(cur, church_id: int, viewer_role: str, *, to_iso=None) -> Dict[str, Any]:
    to_iso = to_iso or (lambda d: d.isoformat() if d else None)
    viewer_is_pastor = is_pastor_level(viewer_role)
    cur.execute(_DASHBOARD_SQL, (church_id, viewer_is_pastor))
    rows = cur.fetchall() or []

    items: List[Dict[str, Any]] = []
    prayer_count = followup_count = high_risk_count = 0
    for r in rows:
        (_id, email, stype, level, title, summary, suggested, req_follow, updated) = r
        if stype == "prayer_request":
            prayer_count += 1
        if req_follow:
            followup_count += 1
        if level in ("high", "critical"):
            high_risk_count += 1
        items.append({
            "signal_id": str(_id),
            "user_id": email,                       # opaque key; UI shows display_name
            "display_name": _display_name(cur, email),
            "signal_level": level,
            "signal_type": stype,
            "title": title,
            "summary": summary,                     # authorised summary, not raw logs
            "suggested_action": suggested or "",
            "requires_followup": bool(req_follow),
            "high_touch_notice": HIGH_TOUCH_NOTICE if level in ("high", "critical") else None,
            "last_updated_at": to_iso(updated),
        })

    # Belt-and-suspenders: sort in Python too (do not depend on SQL ORDER BY alone).
    items.sort(key=lambda i: _LEVEL_RANK.get(i["signal_level"], 9))

    members_count = 0
    try:
        cur.execute("SELECT COUNT(*) FROM church_members WHERE church_id=%s", (church_id,))
        members_count = int(cur.fetchone()[0])
    except Exception:
        members_count = len({i["user_id"] for i in items})

    return {
        "church_id": church_id,
        "summary": {
            "members_count": members_count,
            "prayer_requests_count": prayer_count,
            "needs_followup_count": followup_count,
            "high_risk_count": high_risk_count,
        },
        "items": items,
        "notice": "本面板只显示关怀信号与授权摘要，不显示私密日志、属灵分数或排名。",
    }


# ── Mutations ────────────────────────────────────────────────────────────────
def create_signal(
    cur, *, email: str, church_id: Optional[int], signal_type: str, signal_level: str,
    title: str, summary: str, suggested_action: str = "", source_type: str = "",
    source_id: str = "", consent_share: bool = False, visible_to_group_leader: bool = False,
    visible_to_pastor: bool = False, requires_followup: bool = False,
) -> str:
    cur.execute(
        """
        INSERT INTO care_signals
          (email, church_id, signal_type, signal_level, title, summary, suggested_action,
           source_type, source_id, consent_share, visible_to_group_leader,
           visible_to_pastor, requires_followup)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
        """,
        (email, church_id, signal_type, signal_level, title, summary, suggested_action,
         source_type, source_id, consent_share, visible_to_group_leader,
         visible_to_pastor, requires_followup),
    )
    return str(cur.fetchone()[0])


def record_action(
    cur, *, care_signal_id: str, actor_email: str, target_email: str,
    church_id: Optional[int], action_type: str, action_note: str = "",
    followup_date=None,
) -> str:
    if action_type not in ACTION_TYPES:
        raise ValueError(f"invalid action_type: {action_type}")
    cur.execute(
        """
        INSERT INTO care_actions
          (care_signal_id, actor_email, target_email, church_id, action_type,
           action_note, followup_date)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
        """,
        (care_signal_id, actor_email, target_email, church_id, action_type,
         action_note, followup_date),
    )
    new_id = str(cur.fetchone()[0])
    if action_type == "refer_to_pastor":
        cur.execute(
            "UPDATE care_signals SET visible_to_pastor=TRUE, requires_followup=TRUE, updated_at=now() "
            "WHERE id=%s",
            (care_signal_id,),
        )
    return new_id


def resolve_signal(cur, signal_id: str, actor_email: str) -> None:
    cur.execute(
        "UPDATE care_signals SET resolved=TRUE, resolved_at=now(), updated_at=now() WHERE id=%s",
        (signal_id,),
    )


def write_audit(
    cur, *, actor_email: str, action: str, subject_email: Optional[str] = None,
    resource_type: str = "", resource_id: str = "", church_id: Optional[int] = None,
    detail: Optional[dict] = None, ip: str = "",
) -> None:
    """Append-only audit row. Best-effort: never let auditing break the request."""
    try:
        cur.execute(
            """
            INSERT INTO audit_logs
              (actor_email, subject_email, action, resource_type, resource_id,
               church_id, detail, ip)
            VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
            """,
            (actor_email, subject_email, action, resource_type, str(resource_id),
             church_id, json.dumps(detail or {}), ip),
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Formation roll-up (human-in-the-loop triage)：跨成员聚合 formation_events 的
# 风险信号，帮助牧者/小组长看见「谁这阵子可能需要被关怀」。
#
# 隐私边界（与关怀面板一致，且更严）：
#   - 仅 pastor 级（pastor/owner/admin）可见；group_leader 不可见（信号源自私密活动）。
#   - 只暴露「类别 title + 严重度 + 时间」，绝不暴露 summary / 日志全文 / 分数排名。
#   - 仅列出近 window_days 内有 amber/red 信号的成员（这是关怀触发清单，不是全员监视）。
# ---------------------------------------------------------------------------
def formation_flags(cur, church_id: int, viewer_role: str, *, to_iso=None,
                    days: int = 21) -> Dict[str, Any]:
    if not is_pastor_level(viewer_role):
        return {"items": [], "restricted": True, "window_days": days,
                "notice": "关怀风险汇总仅向牧者级开放；小组长请使用关怀信号面板。"}

    def _iso(dt):
        if not dt:
            return None
        return to_iso(dt) if to_iso else dt.isoformat()

    agg: Dict[str, Dict[str, Any]] = {}
    try:
        cur.execute(
            "SELECT fe.email, count(*), "
            " sum(CASE WHEN fe.severity IN ('red','high') THEN 1 ELSE 0 END), "
            " sum(CASE WHEN fe.severity IN ('amber','medium') THEN 1 ELSE 0 END), "
            " max(fe.occurred_at) "
            "FROM formation_events fe "
            "JOIN church_members cm ON cm.email = fe.email AND cm.church_id = %s "
            "WHERE COALESCE((SELECT cc.share_formation_flags FROM care_consent cc WHERE cc.email=fe.email), TRUE) = TRUE AND fe.severity IN ('red','high','amber','medium') "
            "AND fe.occurred_at > now() - (%s || ' days')::interval "
            "GROUP BY fe.email", (church_id, str(days)))
        for em, cnt, red, amber, last in cur.fetchall():
            agg[em] = {
                "user_id": em, "name": _display_name(cur, em), "email_masked": _mask_email(em),
                "risk": "red" if (red or 0) else "amber",
                "red": int(red or 0), "amber": int(amber or 0), "count": int(cnt or 0),
                "last_at": _iso(last), "flags": [],
            }
        if agg:
            cur.execute(
                "SELECT email, title, severity, occurred_at, source FROM ("
                " SELECT fe.email, fe.title, fe.severity, fe.occurred_at, fe.source, "
                "   row_number() OVER (PARTITION BY fe.email ORDER BY fe.occurred_at DESC) rn "
                " FROM formation_events fe "
                " JOIN church_members cm ON cm.email = fe.email AND cm.church_id = %s "
                " WHERE COALESCE((SELECT cc.share_formation_flags FROM care_consent cc WHERE cc.email=fe.email), TRUE) = TRUE AND fe.severity IN ('red','high','amber','medium') "
                "   AND fe.occurred_at > now() - (%s || ' days')::interval"
                ") t WHERE rn <= 3 ORDER BY email, occurred_at DESC", (church_id, str(days)))
            for em, title, sev, at, src in cur.fetchall():
                if em in agg:
                    agg[em]["flags"].append({"title": title, "severity": sev,
                                             "at": _iso(at), "source": src})
    except Exception:
        return {"items": [], "restricted": False, "window_days": days, "error": "aggregation_failed"}

    items = sorted(agg.values(), key=lambda x: (x["red"], x["amber"], x["count"]), reverse=True)
    return {"items": items, "restricted": False, "window_days": days, "members_flagged": len(items)}
