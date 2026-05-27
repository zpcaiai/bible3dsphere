"""Pure security helpers shared by backend routes and tests."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on deployment extras
    bcrypt = None
    BCRYPT_AVAILABLE = False


EMAIL_RE = re.compile(r'^[\w.+\-]+@[\w\-]+\.[\w.\-]+$')
DATE_RE = re.compile(r'^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$')
_DANGEROUS_TAG_RE = re.compile(
    r'<\s*/?\s*(script|iframe|object|embed|link|style|form|input|button|svg|math|meta|base)\b[^>]*>',
    re.IGNORECASE,
)
_EVENT_HANDLER_RE = re.compile(r'\s*on\w+\s*=', re.IGNORECASE)


def sanitize_text(text: str | None) -> str:
    """Strip dangerous HTML tags and event handlers from user text input."""
    if not text:
        return text or ''
    cleaned = _DANGEROUS_TAG_RE.sub('', text)
    cleaned = _EVENT_HANDLER_RE.sub(' ', cleaned)
    return cleaned.strip()


def validate_date_str(value: str) -> str:
    """Validate YYYY-MM-DD date format."""
    if not DATE_RE.match(value):
        raise ValueError('日期格式不正确，应为 YYYY-MM-DD')
    return value


def hash_password(password: str) -> str:
    """Hash a password with bcrypt when available, otherwise SHA256+salt."""
    if BCRYPT_AVAILABLE and bcrypt is not None:
        return 'bcrypt:' + bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return f'sha256:{salt}:{digest}'


def verify_password(password: str, stored: str) -> bool:
    """Verify bcrypt, prefixed sha256, and legacy salt:digest password hashes."""
    try:
        if not stored or stored.strip() == '':
            return False
        if stored.startswith('bcrypt:'):
            if not BCRYPT_AVAILABLE or bcrypt is None:
                return False
            hash_value = stored[7:]
            return bcrypt.checkpw(password.encode('utf-8'), hash_value.encode('utf-8'))
        if stored.startswith('sha256:'):
            _, salt, digest = stored.split(':', 2)
            return hmac.compare_digest(
                hashlib.sha256((salt + password).encode()).hexdigest(),
                digest,
            )
        if ':' in stored:
            salt, digest = stored.split(':', 1)
            return hmac.compare_digest(
                hashlib.sha256((salt + password).encode()).hexdigest(),
                digest,
            )
        return False
    except Exception:
        return False
