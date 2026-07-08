"""Shared application rate limiter (slowapi).

The app runs behind a reverse proxy (HF Spaces) and uvicorn is started without
``--proxy-headers``, so ``request.client.host`` is the *proxy* IP — the same for
every visitor. Keying limits on that would throttle all users collectively.

``client_ip`` therefore derives the real client IP from ``X-Forwarded-For``
/ ``X-Real-IP``, falling back to the socket peer. It uses the *right-most* XFF
entry (the value appended by our own trusted proxy) rather than the left-most
one, because the left-most is fully client-controlled and can be spoofed to
evade per-IP limits. ``TRUSTED_PROXY_HOPS`` (default 1) selects which entry from
the right is the real client (increase it if there are multiple trusted proxies
in front of the app). This makes both the global ceiling and the per-endpoint
limits genuinely per-user.

A generous global ``default_limits`` ceiling stops automated floods / cost
amplification on every route; expensive paid endpoints add tighter limits on
top via ``@limiter.limit(...)``.
"""
from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address


def _trusted_proxy_hops() -> int:
    """Number of trusted proxy hops in front of the app (>=1). The real client
    IP is the ``hops``-th X-Forwarded-For entry counted from the right."""
    try:
        h = int(os.getenv("TRUSTED_PROXY_HOPS", "1"))
        return h if h >= 1 else 1
    except Exception:
        return 1


def client_ip(request) -> str:
    try:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            parts = [p.strip() for p in xff.split(",") if p.strip()]
            if parts:
                # Take the entry our trusted proxy appended (right-most by
                # default). Never trust the left-most, client-supplied value.
                hops = _trusted_proxy_hops()
                idx = -hops if hops <= len(parts) else -len(parts)
                ip = parts[idx]
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
