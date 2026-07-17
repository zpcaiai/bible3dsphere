"""AES-256-GCM envelope encryption for Formation Twin sensitive content."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass(frozen=True)
class EncryptedContent:
    key_version: str
    nonce: bytes
    ciphertext: bytes
    sha256: str


def _key() -> tuple[str, bytes]:
    explicit = os.getenv("FORMATION_TWIN_ENCRYPTION_KEY", "").strip()
    if explicit:
        raw = bytes.fromhex(explicit)
        if len(raw) != 32:
            raise RuntimeError("FORMATION_TWIN_ENCRYPTION_KEY must be 64 hex characters")
        return "formation-twin-v1", raw

    # Existing deployments already require a strong JWT secret. Derive a
    # purpose-separated key so local/test environments remain usable while
    # production can rotate with the dedicated key above.
    secret = os.getenv("JWT_SECRET_KEY", "").encode("utf-8")
    if len(secret) < 16:
        raise RuntimeError("Formation Twin encryption is not configured")
    return "derived-jwt-v1", hashlib.sha256(b"formation-twin-sensitive-content\x00" + secret).digest()


def encrypt_text(value: str, *, associated_data: bytes) -> EncryptedContent:
    key_version, key = _key()
    plaintext = value.encode("utf-8")
    nonce = os.urandom(12)
    return EncryptedContent(
        key_version=key_version,
        nonce=nonce,
        ciphertext=AESGCM(key).encrypt(nonce, plaintext, associated_data),
        sha256=hashlib.sha256(plaintext).hexdigest(),
    )


def decrypt_text(value: EncryptedContent, *, associated_data: bytes) -> str:
    key_version, key = _key()
    if value.key_version != key_version:
        raise RuntimeError("Formation Twin encryption key version is unavailable")
    return AESGCM(key).decrypt(value.nonce, value.ciphertext, associated_data).decode("utf-8")
