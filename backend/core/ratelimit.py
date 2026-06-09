"""Shared application rate limiter (slowapi).

The app runs behind a reverse proxy (HF Spaces) and uvicorn is started without
``--proxy-headers``, so ``request.client.host`` is the *proxy* IP — the same for
every visitor. Keying limits on that would throttle all users collectively.

``client_ip`` therefore derives the real client IP from ``X-Forwarded-For``
(left-most entry) / ``X-Real-IP``, falling back to the socket peer. This makes
both the global ceiling and the per-endpoint limits genuinely per-user.

A generous global ``default_limits`` ceiling stops automated floods / cost
amplification on every route; expensive paid endpoints add tighter limits on
top via ``@limiter.limit(...)``.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address


def client_ip(request) -> str:
    try:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            ip = xff.split(",")[0].strip()
            if ip:
                return ip
        xri = request.headers.get("x-real-ip")
        if xri:
            return xri.strip()
    except Exception:
        pass
    return get_remote_address(request)


# Global per-IP ceiling. Generous enough for normal browsing (page loads fan out
# to a handful of API calls; the auto-translate engine micro-batches), but well
# below what an automated abuse loop would generate.
limiter = Limiter(key_func=client_ip, default_limits=["600/minute"])
