"""
Billing router — 计费 / Stripe (/api/billing) · B12-4

  GET  /api/billing/status     当前订阅状态
  POST /api/billing/checkout   创建 Stripe Checkout 会话 → 返回 checkout_url
  POST /api/billing/webhook    Stripe webhook → 更新 subscriptions 状态

与隔离解耦。优雅降级:未配置 STRIPE_SECRET_KEY 时 checkout 返回 503(并明确告知:
危机/安全功能不受订阅限制,始终可用)。webhook 在配置了 STRIPE_WEBHOOK_SECRET 时校验签名。
env:STRIPE_SECRET_KEY、STRIPE_WEBHOOK_SECRET、STRIPE_PRICE_<PLAN_KEY 大写>、PUBLIC_BASE_URL。
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/billing", tags=["billing"])

_state: Dict[str, Any] = {}


def init_billing_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _configured() -> bool:
    return bool(os.environ.get("STRIPE_SECRET_KEY"))


def _stripe():
    key = os.environ.get("STRIPE_SECRET_KEY")
    if not key:
        return None
    try:
        import stripe  # type: ignore
        stripe.api_key = key
        return stripe
    except Exception:
        return None


@router.get("/status")
def status(request: Request) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT plan_key, scope, status, billing_provider, current_period_end, stripe_subscription_id "
                        "FROM subscriptions WHERE email=%s ORDER BY updated_at DESC LIMIT 1", (user["email"],))
            r = cur.fetchone()
    finally:
        _state["release_db"](conn)
    sub = None
    if r:
        sub = {"plan_key": r[0], "scope": r[1], "status": r[2], "billing_provider": r[3],
               "current_period_end": to_iso(r[4]) if r[4] else None, "stripe_linked": bool(r[5])}
    return {"ok": True, "billing_configured": _configured(), "subscription": sub,
            "note": "危机与安全功能不受订阅状态影响,始终可用。"}


class CheckoutBody(BaseModel):
    plan_key: str = Field(..., max_length=40)
    organization_id: Optional[str] = Field(default=None, max_length=64)
    success_url: Optional[str] = Field(default=None, max_length=400)
    cancel_url: Optional[str] = Field(default=None, max_length=400)


@router.post("/checkout")
def checkout(request: Request, body: CheckoutBody) -> dict:
    user = _require_user(request)
    email = user["email"]
    stripe = _stripe()
    if not stripe:
        raise HTTPException(status_code=503,
                            detail="billing_not_configured:未配置 STRIPE_SECRET_KEY,订阅暂不可用。危机/安全功能不受影响,始终可用。")
    price = os.environ.get("STRIPE_PRICE_" + body.plan_key.upper())
    if not price:
        raise HTTPException(status_code=400,
                            detail="no Stripe price for plan '%s' (set env STRIPE_PRICE_%s)" % (body.plan_key, body.plan_key.upper()))
    base = (os.environ.get("PUBLIC_BASE_URL") or "").rstrip("/")
    success = body.success_url or (base + "/billing/success" if base else "https://example.com/billing/success")
    cancel = body.cancel_url or (base + "/billing/cancel" if base else "https://example.com/billing/cancel")
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price, "quantity": 1}],
            customer_email=email,
            client_reference_id=email,
            metadata={"email": email, "plan_key": body.plan_key, "organization_id": body.organization_id or ""},
            success_url=success,
            cancel_url=cancel,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="stripe error: " + str(exc)[:200])
    return {"ok": True, "checkout_url": getattr(session, "url", None) or session.get("url"),
            "session_id": getattr(session, "id", None) or session.get("id")}


@router.post("/webhook")
async def webhook(request: Request) -> dict:
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    stripe = _stripe()
    if not stripe:
        raise HTTPException(status_code=503, detail="billing_not_configured")
    if secret:
        try:
            stripe.Webhook.construct_event(payload, sig, secret)  # 验签;失败抛出
        except Exception as exc:
            raise HTTPException(status_code=400, detail="invalid signature: " + str(exc)[:120])
    try:
        event = json.loads(payload.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="invalid payload")
    etype = event.get("type")
    obj = ((event.get("data") or {}).get("object")) or {}
    _apply_event(etype, obj)
    return {"ok": True, "received": True, "type": etype}


def _apply_event(etype: Optional[str], obj: Dict[str, Any]) -> None:
    """把 Stripe 事件落到 subscriptions。任何异常吞掉(webhook 不应 500)。"""
    try:
        meta = obj.get("metadata") or {}
        email = plan = sub_id = cust = new_status = None
        if etype == "checkout.session.completed":
            email = meta.get("email") or obj.get("customer_email") or obj.get("client_reference_id")
            plan = meta.get("plan_key") or None
            sub_id = obj.get("subscription")
            cust = obj.get("customer")
            new_status = "active"
        elif etype in ("customer.subscription.updated", "customer.subscription.deleted"):
            sub_id = obj.get("id")
            cust = obj.get("customer")
            new_status = "canceled" if etype.endswith("deleted") else (obj.get("status") or "active")
        else:
            return
        conn = _state["get_db"]()
        try:
            with conn.cursor() as cur:
                if email:
                    cur.execute("SELECT id FROM subscriptions WHERE email=%s ORDER BY updated_at DESC LIMIT 1", (email,))
                    row = cur.fetchone()
                    if row:
                        cur.execute("UPDATE subscriptions SET plan_key=COALESCE(%s,plan_key), status=COALESCE(%s,status), "
                                    "billing_provider='stripe', stripe_subscription_id=COALESCE(%s,stripe_subscription_id), "
                                    "stripe_customer_id=COALESCE(%s,stripe_customer_id), updated_at=now() WHERE id=%s",
                                    (plan, new_status, sub_id, cust, row[0]))
                    else:
                        cur.execute("INSERT INTO subscriptions (id,email,plan_key,scope,status,billing_provider,stripe_subscription_id,stripe_customer_id) "
                                    "VALUES (%s,%s,COALESCE(%s,'free_individual'),'user',COALESCE(%s,'active'),'stripe',%s,%s)",
                                    (uuid.uuid4().hex, email, plan, new_status, sub_id, cust))
                elif sub_id:
                    cur.execute("UPDATE subscriptions SET status=COALESCE(%s,status), stripe_customer_id=COALESCE(%s,stripe_customer_id), "
                                "updated_at=now() WHERE stripe_subscription_id=%s", (new_status, cust, sub_id))
                conn.commit()
        finally:
            _state["release_db"](conn)
    except Exception:
        pass
