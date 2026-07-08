"""
admin_ops.py — 管理端：订阅/账单、运营分析、内容反馈信号。

prefix: /api/admin （复用 admin_common 已注入的共享状态与鉴权）
鉴权：每个端点首先调用 require_admin(request)。

只读为主。订阅写操作（改套餐 / 改状态）仅更新本地 subscriptions 记录，
用于人工调整 / 赠送 / 标记，绝不调用支付渠道、绝不发起扣款或退款。
所有聚合查询防御式执行：缺表 / 缺列时回滚并返回 0/[]，不使整页 500。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:
    from routers.admin_common import _state, require_admin, audit, paginate
except ImportError:  # pragma: no cover
    from backend.routers.admin_common import _state, require_admin, audit, paginate

router = APIRouter(prefix="/api/admin", tags=["admin-ops"])


# ─────────────────────────────────────────────────────────────────────────────
# 防御式查询辅助（缺表/缺列 → 回滚 + 返回 0/[]，避免中断后续查询）
# ─────────────────────────────────────────────────────────────────────────────
def _scalar(cur, sql: str, params=()) -> int:
    try:
        cur.execute(sql, params)
        r = cur.fetchone()
        return int(r[0] or 0) if r and r[0] is not None else 0
    except Exception:
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return 0


def _rows(cur, sql: str, params=()):
    try:
        cur.execute(sql, params)
        return cur.fetchall()
    except Exception:
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return []


def _iso(v):
    to = _state.get("to_shanghai_iso")
    if v is not None and to is not None:
        try:
            return to(v)
        except Exception:
            pass
    return v.isoformat() if hasattr(v, "isoformat") else v


def _date_str(v):
    return v.isoformat() if hasattr(v, "isoformat") else (str(v) if v is not None else None)


# ═════════════════════════════════════════════════════════════════════════════
# 订阅 / 账单
# ═════════════════════════════════════════════════════════════════════════════
@router.get("/billing/summary")
def billing_summary(request: Request) -> dict:
    require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            plans = _rows(
                cur,
                "SELECT p.plan_key, p.display_name, p.plan_type, p.price_cents, p.billing_interval, "
                "COALESCE(s.cnt,0) "
                "FROM product_plans p "
                "LEFT JOIN (SELECT plan_key, COUNT(*) cnt FROM subscriptions WHERE status='active' GROUP BY plan_key) s "
                "ON s.plan_key = p.plan_key "
                "ORDER BY p.sort_order, p.price_cents",
            )
            total_active = _scalar(cur, "SELECT COUNT(*) FROM subscriptions WHERE status='active'")
            paid_active = _scalar(
                cur,
                "SELECT COUNT(*) FROM subscriptions WHERE status='active' AND plan_key <> 'free_individual'",
            )
            mrr = _scalar(
                cur,
                "SELECT COALESCE(SUM(p.price_cents),0) FROM subscriptions s "
                "JOIN product_plans p ON p.plan_key = s.plan_key "
                "WHERE s.status='active' AND p.billing_interval='monthly'",
            )
            status_rows = _rows(cur, "SELECT status, COUNT(*) FROM subscriptions GROUP BY status ORDER BY 2 DESC")
    finally:
        _state["release_db"](conn)

    plan_items = [
        {
            "plan_key": r[0], "display_name": r[1], "plan_type": r[2],
            "price_cents": int(r[3] or 0), "billing_interval": r[4], "active_count": int(r[5] or 0),
        }
        for r in plans
    ]
    return {
        "ok": True,
        "plans": plan_items,
        "totals": {
            "active_subscriptions": total_active,
            "paid_subscriptions": paid_active,
            "free_subscriptions": max(0, total_active - paid_active),
            "mrr_cents": mrr,
        },
        "by_status": {r[0]: int(r[1] or 0) for r in status_rows},
        "note": "MRR 仅按月付计划的挂牌价估算；不含年付/自定义/折扣，非财务口径。",
    }


@router.get("/subscriptions")
def list_subscriptions(
    request: Request,
    email: str = Query(default=""),
    plan_key: str = Query(default=""),
    status: str = Query(default=""),
    scope: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            filters, params = [], []
            if email:
                filters.append("s.email ILIKE %s"); params.append(f"%{email}%")
            if plan_key:
                filters.append("s.plan_key = %s"); params.append(plan_key)
            if status:
                filters.append("s.status = %s"); params.append(status)
            if scope:
                filters.append("s.scope = %s"); params.append(scope)
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            total = _scalar(cur, f"SELECT COUNT(*) FROM subscriptions s {where}", params)
            rows = _rows(
                cur,
                "SELECT s.id, s.email, s.organization_id, s.plan_key, p.display_name, s.scope, s.status, "
                "s.billing_provider, s.current_period_end, s.stripe_subscription_id, s.created_at "
                "FROM subscriptions s LEFT JOIN product_plans p ON p.plan_key = s.plan_key "
                f"{where} ORDER BY s.created_at DESC LIMIT %s OFFSET %s",
                params + [limit, offset],
            )
    finally:
        _state["release_db"](conn)

    items = [
        {
            "id": r[0], "email": r[1], "organization_id": r[2], "plan_key": r[3], "plan_name": r[4],
            "scope": r[5], "status": r[6], "billing_provider": r[7],
            "current_period_end": _iso(r[8]), "stripe_subscription_id": r[9], "created_at": _iso(r[10]),
        }
        for r in rows
    ]
    return {"ok": True, "items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/plans")
def list_plans(request: Request) -> dict:
    require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            rows = _rows(
                cur,
                "SELECT plan_key, display_name, plan_type, billing_interval, price_cents, public, sort_order "
                "FROM product_plans ORDER BY sort_order, price_cents",
            )
    finally:
        _state["release_db"](conn)
    items = [
        {
            "plan_key": r[0], "display_name": r[1], "plan_type": r[2], "billing_interval": r[3],
            "price_cents": int(r[4] or 0), "public": bool(r[5]), "sort_order": int(r[6] or 0),
        }
        for r in rows
    ]
    return {"ok": True, "items": items}


class ChangePlanBody(BaseModel):
    plan_key: str = Field(..., max_length=40)
    note: str = Field(default="", max_length=500)


@router.post("/subscriptions/{sid}/change-plan")
def change_plan(sid: str, request: Request, body: ChangePlanBody) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM product_plans WHERE plan_key=%s", (body.plan_key,))
            if not cur.fetchone():
                raise HTTPException(status_code=400, detail="计划不存在")
            cur.execute("SELECT plan_key FROM subscriptions WHERE id=%s", (sid,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="订阅不存在")
            old = row[0]
            cur.execute("UPDATE subscriptions SET plan_key=%s, updated_at=now() WHERE id=%s", (body.plan_key, sid))
            audit(cur, admin["email"], "sub_change_plan", "subscription", sid,
                  {"from": old, "to": body.plan_key, "note": body.note, "manual": True})
            conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": sid, "plan_key": body.plan_key,
            "note": "仅更新本地订阅记录（人工调整/赠送）；不触发任何支付或退款。"}


_ALLOWED_SUB_STATUS = {"active", "canceled", "past_due", "paused", "trialing"}


class SetStatusBody(BaseModel):
    status: str = Field(..., max_length=12)
    note: str = Field(default="", max_length=500)


@router.post("/subscriptions/{sid}/set-status")
def set_sub_status(sid: str, request: Request, body: SetStatusBody) -> dict:
    admin = require_admin(request)
    if body.status not in _ALLOWED_SUB_STATUS:
        raise HTTPException(status_code=400, detail="状态无效，仅支持 active/canceled/past_due/paused/trialing")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM subscriptions WHERE id=%s", (sid,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="订阅不存在")
            old = row[0]
            cur.execute("UPDATE subscriptions SET status=%s, updated_at=now() WHERE id=%s", (body.status, sid))
            audit(cur, admin["email"], "sub_set_status", "subscription", sid,
                  {"from": old, "to": body.status, "note": body.note, "manual": True})
            conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": sid, "status": body.status,
            "note": "仅更新本地订阅状态；不调用支付渠道，不产生退款。"}


# ═════════════════════════════════════════════════════════════════════════════
# 运营分析
# ═════════════════════════════════════════════════════════════════════════════
@router.get("/analytics/overview")
def analytics_overview(request: Request, days: int = Query(default=30, ge=1, le=365)) -> dict:
    require_admin(request)
    d = int(days)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            total_users = _scalar(cur, "SELECT COUNT(*) FROM users")
            new_users = _scalar(cur, "SELECT COUNT(*) FROM users WHERE created_at >= NOW() - INTERVAL '%s days'" % d)
            dau = _scalar(cur, "SELECT COUNT(DISTINCT email) FROM user_tokens WHERE created_at >= NOW() - INTERVAL '1 days'")
            wau = _scalar(cur, "SELECT COUNT(DISTINCT email) FROM user_tokens WHERE created_at >= NOW() - INTERVAL '7 days'")
            mau = _scalar(cur, "SELECT COUNT(DISTINCT email) FROM user_tokens WHERE created_at >= NOW() - INTERVAL '30 days'")
            reg_rows = _rows(
                cur,
                "SELECT (created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Shanghai')::date, COUNT(*) "
                "FROM users WHERE created_at >= NOW() - INTERVAL '%s days' GROUP BY 1 ORDER BY 1" % d,
            )
            content = {
                "posts":        _scalar(cur, "SELECT COUNT(*) FROM community_posts  WHERE created_at >= NOW() - INTERVAL '%s days'" % d),
                "prayers":      _scalar(cur, "SELECT COUNT(*) FROM prayers          WHERE created_at >= NOW() - INTERVAL '%s days'" % d),
                "checkins":     _scalar(cur, "SELECT COUNT(*) FROM user_checkins    WHERE checkin_at >= NOW() - INTERVAL '%s days'" % d),
                "gratitude":    _scalar(cur, "SELECT COUNT(*) FROM gratitude_entries WHERE created_at >= NOW() - INTERVAL '%s days'" % d),
                "devotion_journals": _scalar(cur, "SELECT COUNT(*) FROM devotion_journals WHERE created_at >= NOW() - INTERVAL '%s days'" % d),
                "sermon_journals":   _scalar(cur, "SELECT COUNT(*) FROM sermon_journals   WHERE created_at >= NOW() - INTERVAL '%s days'" % d),
                "memory_verses":     _scalar(cur, "SELECT COUNT(*) FROM memory_verses     WHERE created_at >= NOW() - INTERVAL '%s days'" % d),
                "testimonies":       _scalar(cur, "SELECT COUNT(*) FROM testimonies       WHERE created_at >= NOW() - INTERVAL '%s days'" % d),
            }
    finally:
        _state["release_db"](conn)

    series = [{"date": _date_str(r[0]), "count": int(r[1] or 0)} for r in reg_rows]
    return {
        "ok": True, "days": d,
        "users": {"total": total_users, "new_in_period": new_users},
        "active": {"dau": dau, "wau": wau, "mau": mau},
        "content": content,
        "registration_series": series,
    }


@router.get("/analytics/feature-adoption")
def feature_adoption(request: Request) -> dict:
    require_admin(request)
    feats = [
        ("社区发帖", "community_posts", "email"),
        ("代祷", "prayers", "email"),
        ("每日签到", "user_checkins", "email"),
        ("感恩日记", "gratitude_entries", "email"),
        ("灵修笔记", "devotion_journals", "email"),
        ("讲道笔记", "sermon_journals", "email"),
        ("背经", "memory_verses", "email"),
        ("见证墙", "testimonies", "email"),
        ("Guardian 情绪", "guardian_emotion_events", "email"),
        ("门徒塑造", "disciple_profiles", "email"),
        ("习惯追踪", "habit_state_machines", "user_id"),
        ("读经计划", "reading_plan_enrollment", "email"),
        ("省察 Examen", "examen_entries", "email"),
        ("属灵体检", "spiritual_checkups", "email"),
    ]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            out = []
            for label, tbl, col in feats:
                n = _scalar(cur, f"SELECT COUNT(DISTINCT {col}) FROM {tbl}")
                out.append({"key": tbl, "label": label, "users": n})
    finally:
        _state["release_db"](conn)
    out.sort(key=lambda x: x["users"], reverse=True)
    return {"ok": True, "features": out}


_SERIES_METRICS = {
    "registrations": ("users", "created_at", "新增用户"),
    "posts": ("community_posts", "created_at", "社区帖子"),
    "prayers": ("prayers", "created_at", "代祷"),
    "checkins": ("user_checkins", "checkin_at", "签到"),
    "gratitude": ("gratitude_entries", "created_at", "感恩日记"),
    "devotion_journals": ("devotion_journals", "created_at", "灵修笔记"),
    "memory_verses": ("memory_verses", "created_at", "背经"),
}


@router.get("/analytics/engagement-series")
def engagement_series(
    request: Request,
    metric: str = Query(default="posts"),
    days: int = Query(default=30, ge=1, le=365),
) -> dict:
    require_admin(request)
    if metric not in _SERIES_METRICS:
        raise HTTPException(status_code=400, detail="metric 无效")
    tbl, ts, label = _SERIES_METRICS[metric]
    d = int(days)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            rows = _rows(
                cur,
                f"SELECT ({ts} AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Shanghai')::date, COUNT(*) "
                f"FROM {tbl} WHERE {ts} >= NOW() - INTERVAL '%s days' GROUP BY 1 ORDER BY 1" % d,
            )
    finally:
        _state["release_db"](conn)
    return {
        "ok": True, "metric": metric, "label": label, "days": d,
        "series": [{"date": _date_str(r[0]), "count": int(r[1] or 0)} for r in rows],
        "metrics": [{"key": k, "label": v[2]} for k, v in _SERIES_METRICS.items()],
    }

# ═════════════════════════════════════════════════════════════════════════════
# 内容反馈信号（user_verse_feedback：用户对经文的 保存/祷告/分享 隐式反馈）
# ═════════════════════════════════════════════════════════════════════════════
@router.get("/verse-feedback")
def verse_feedback(
    request: Request,
    feedback_type: str = Query(default=""),
    user_id: str = Query(default=""),
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            filters, params = [], []
            if feedback_type:
                filters.append("feedback_type = %s"); params.append(feedback_type)
            if user_id:
                filters.append("user_id = %s"); params.append(user_id)
            if q:
                filters.append("(verse_ref ILIKE %s OR verse_text ILIKE %s)"); params += [f"%{q}%", f"%{q}%"]
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            total = _scalar(cur, f"SELECT COUNT(*) FROM user_verse_feedback {where}", params)
            rows = _rows(
                cur,
                "SELECT id, user_id, verse_ref, verse_text, feedback_type, created_at "
                f"FROM user_verse_feedback {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
                params + [limit, offset],
            )
            tb_filters, tb_params = [], []
            if q:
                tb_filters.append("(verse_ref ILIKE %s OR verse_text ILIKE %s)"); tb_params += [f"%{q}%", f"%{q}%"]
            tb_where = ("WHERE " + " AND ".join(tb_filters)) if tb_filters else ""
            tb = _rows(cur, f"SELECT feedback_type, COUNT(*) FROM user_verse_feedback {tb_where} GROUP BY feedback_type", tb_params)
    finally:
        _state["release_db"](conn)

    items = [
        {
            "id": r[0], "user_id": r[1], "verse_ref": r[2],
            "verse_text": (r[3] or "")[:300], "feedback_type": r[4], "created_at": _iso(r[5]),
        }
        for r in rows
    ]
    return {"ok": True, "items": items, "total": total, "page": page, "page_size": page_size,
            "by_type": {r[0]: int(r[1] or 0) for r in tb}}


@router.get("/verse-feedback/top")
def verse_feedback_top(
    request: Request,
    feedback_type: str = Query(default=""),
    days: int = Query(default=90, ge=1, le=3650),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    d = int(days)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            filters = ["created_at >= NOW() - INTERVAL '%s days'" % d, "verse_ref <> ''"]
            params: list = []
            if feedback_type:
                filters.append("feedback_type = %s"); params.append(feedback_type)
            where = "WHERE " + " AND ".join(filters)
            rows = _rows(
                cur,
                f"SELECT verse_ref, COUNT(*) c FROM user_verse_feedback {where} "
                "GROUP BY verse_ref ORDER BY c DESC LIMIT %s",
                params + [limit],
            )
    finally:
        _state["release_db"](conn)
    return {"ok": True, "items": [{"verse_ref": r[0], "count": int(r[1] or 0)} for r in rows]}
