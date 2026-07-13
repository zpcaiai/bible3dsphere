"""Skill 15: step-up authentication, sensitive-export approval and secure sessions.

Pure-python invariants for the sensitive export lifecycle. A sensitive export
requires: (1) a fresh step-up verification, (2) an approver who is not the
requester, (3) a hashed one-time download token, (4) a watermark label, and
(5) a short expiry after which the artifact is auto-deleted.
"""
from __future__ import annotations
import hashlib
from datetime import datetime, timezone

STATES = frozenset({
    "requested", "step_up_pending", "approved", "denied",
    "ready", "downloaded", "expired", "revoked",
})
# Only these transitions are permitted; everything else fails closed.
_TRANSITIONS = {
    "requested": {"step_up_pending", "denied", "revoked"},
    "step_up_pending": {"approved", "denied", "revoked"},
    "approved": {"ready", "revoked", "expired"},
    "ready": {"downloaded", "expired", "revoked"},
    "downloaded": {"downloaded", "expired", "revoked"},
    "denied": set(),
    "expired": set(),
    "revoked": set(),
}

STEP_UP_METHODS = frozenset({"totp", "webauthn", "email_code", "sms_code"})
MAX_STEP_UP_AGE_SECONDS = 15 * 60      # step-up must be recent to authorize approval
MAX_EXPIRY_SECONDS = 24 * 60 * 60      # sensitive download links are short-lived


def hash_token(raw: str) -> str:
    """One-way hash of the download token; the raw token is never stored/audited."""
    if not raw or len(raw) < 16:
        raise ValueError("download token must be a high-entropy secret")
    return hashlib.sha256(raw.encode()).hexdigest()


def can_transition(current: str, nxt: str) -> bool:
    if current not in STATES or nxt not in STATES:
        raise ValueError("unknown export state")
    return nxt in _TRANSITIONS[current]


def assert_transition(current: str, nxt: str) -> None:
    if not can_transition(current, nxt):
        raise ValueError(f"illegal export transition {current} -> {nxt}")


def step_up_fresh(verified_at: datetime | None, *, now: datetime | None = None,
                  max_age_seconds: int = MAX_STEP_UP_AGE_SECONDS) -> bool:
    if verified_at is None or verified_at.tzinfo is None:
        return False
    now = now or datetime.now(timezone.utc)
    return 0 <= (now - verified_at).total_seconds() <= max_age_seconds


def validate_step_up_method(method: str) -> str:
    if method not in STEP_UP_METHODS:
        raise ValueError(f"unsupported step-up method: {method!r}")
    return method


def can_approve(*, requester_id: str, approver_id: str,
                step_up_verified_at: datetime | None, now: datetime | None = None) -> None:
    """Raise unless an independent approver with a fresh step-up may approve."""
    if not approver_id:
        raise ValueError("approver required")
    if requester_id == approver_id:
        raise ValueError("sensitive export approver cannot be the requester")
    if not step_up_fresh(step_up_verified_at, now=now):
        raise ValueError("approval requires a fresh step-up verification")


def validate_expiry(expires_at: datetime, *, now: datetime | None = None,
                    max_seconds: int = MAX_EXPIRY_SECONDS) -> datetime:
    if expires_at.tzinfo is None:
        raise ValueError("expiry must be timezone-aware")
    now = now or datetime.now(timezone.utc)
    delta = (expires_at - now).total_seconds()
    if delta <= 0:
        raise ValueError("expiry must be in the future")
    if delta > max_seconds:
        raise ValueError("sensitive export expiry exceeds maximum window")
    return expires_at


def download_available(*, status: str, expires_at: datetime, downloads: int,
                       max_downloads: int, revoked_at: datetime | None = None,
                       now: datetime | None = None) -> bool:
    """Fail closed: only ready/downloaded, unexpired, unrevoked, under the cap."""
    now = now or datetime.now(timezone.utc)
    if revoked_at is not None:
        return False
    if status not in ("ready", "downloaded"):
        return False
    if expires_at.tzinfo is None or expires_at <= now:
        return False
    return downloads < max_downloads


def require_watermark(label: str | None) -> str:
    if not label or not label.strip():
        raise ValueError("sensitive export must carry a watermark label")
    return label.strip()[:120]


def is_expired(expires_at: datetime, *, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    return expires_at.tzinfo is not None and expires_at <= now
