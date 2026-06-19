"""
notify.py — 可插拔的危机通知发送器（SMS / 通用 webhook）。

设计与本仓库 LLM / push provider 一致：配了凭据就真的发，没配就「记录意图 + 审计」，
绝不影响应用其余部分。所有发送都返回结构化结果，供 crisis_events 审计。

通道优先级：
  1. Twilio SMS    TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER + 守护人 phone
  2. 通用 Webhook  CRISIS_NOTIFY_WEBHOOK_URL  （POST {to, body, meta}，可对接自建短信网关）
  3. 未配置        返回 status=not_configured（只记录意图，不泄露）

安全：只对「已预授权（consent_enabled）且权限覆盖该等级」的守护人调用本模块。
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def _twilio_ready() -> bool:
    return bool(_env("TWILIO_ACCOUNT_SID") and _env("TWILIO_AUTH_TOKEN") and _env("TWILIO_FROM_NUMBER"))


def _webhook_ready() -> bool:
    return bool(_env("CRISIS_NOTIFY_WEBHOOK_URL"))


def configured_channels() -> List[str]:
    chans = []
    if _twilio_ready():
        chans.append("sms")
    if _webhook_ready():
        chans.append("webhook")
    return chans


def sms_configured() -> bool:
    """是否存在任意可用的发送通道。"""
    return bool(configured_channels())


def _send_webhook(to: str, body: str, meta: Optional[Dict]) -> Dict[str, object]:
    if not _webhook_ready():
        return {"ok": False, "status": "not_configured", "provider": None}
    try:
        import httpx
        resp = httpx.post(_env("CRISIS_NOTIFY_WEBHOOK_URL"),
                          json={"to": to, "body": body, "meta": meta or {}}, timeout=15)
        ok = resp.status_code < 400
        return {"ok": ok, "provider": "webhook", "status": "sent" if ok else f"webhook_http_{resp.status_code}"}
    except Exception as exc:  # pragma: no cover - network dependent
        return {"ok": False, "provider": "webhook", "status": "webhook_exception", "error": str(exc)[:160]}


def send_sms(to: str, body: str, meta: Optional[Dict] = None) -> Dict[str, object]:
    """发送一条短信（Twilio → 通用 webhook → not_configured）。永不抛异常。"""
    to = (to or "").strip()
    if not to:
        return {"ok": False, "status": "no_recipient", "provider": None}

    if _twilio_ready():
        sid, tok, frm = _env("TWILIO_ACCOUNT_SID"), _env("TWILIO_AUTH_TOKEN"), _env("TWILIO_FROM_NUMBER")
        try:
            import httpx
            resp = httpx.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                data={"To": to, "From": frm, "Body": body}, auth=(sid, tok), timeout=15)
            ok = resp.status_code < 400
            return {"ok": ok, "provider": "twilio", "status": "sent" if ok else f"twilio_http_{resp.status_code}"}
        except Exception as exc:  # pragma: no cover
            return {"ok": False, "provider": "twilio", "status": "twilio_exception", "error": str(exc)[:160]}

    return _send_webhook(to, body, meta)


def send_notification(*, body: str, methods: Optional[List[str]] = None,
                      phone: str = "", meta: Optional[Dict] = None) -> Dict[str, object]:
    """
    依据守护人的 notify_methods 选择通道（当前支持 sms / webhook）。
    返回 {ok, status, provider}。未配置任何通道时返回 not_configured。
    """
    methods = methods or (["sms"] if phone else [])
    if ("sms" in methods or not methods) and phone and _twilio_ready():
        return send_sms(phone, body, meta)
    if "webhook" in methods or not configured_channels():
        if _webhook_ready():
            return _send_webhook(phone or "guardian", body, meta)
        return {"ok": False, "status": "not_configured", "provider": None}
    if phone and _twilio_ready():
        return send_sms(phone, body, meta)
    if _webhook_ready():
        return _send_webhook(phone or "guardian", body, meta)
    return {"ok": False, "status": "not_configured", "provider": None}
