"""Centralized runtime configuration for the backend.

This module intentionally avoids a hard dependency on pydantic-settings so it
can run in the existing lightweight deployment environment.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _env_csv(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", ""))
    allowed_origins: list[str] = field(default_factory=lambda: _env_csv("ALLOWED_ORIGINS", "*"))
    debug_api: bool = field(default_factory=lambda: _env_bool("DEBUG_API", False))

    hf_token: str = field(default_factory=lambda: os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN", ""))
    hf_stats_repo: str = field(default_factory=lambda: os.getenv("HF_STATS_REPO", "StephenZao/bible-sphere-stats"))
    hf_stats_path: str = field(default_factory=lambda: os.getenv("HF_STATS_PATH", "visit_stats.json"))
    hf_data_repo: str = field(default_factory=lambda: os.getenv("HF_DATA_REPO", "StephenZao/biblesphere"))

    wx_app_id: str = field(default_factory=lambda: os.getenv("WX_APP_ID", ""))
    wx_app_secret: str = field(default_factory=lambda: os.getenv("WX_APP_SECRET", ""))
    wx_redirect_uri: str = field(default_factory=lambda: os.getenv("WX_REDIRECT_URI", "http://localhost:8000/api/auth/wechat/callback"))

    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "smtp.sina.com"))
    smtp_port: int = field(default_factory=lambda: _env_int("SMTP_PORT", 465))
    smtp_user: str = field(default_factory=lambda: os.getenv("SMTP_USER", ""))
    smtp_pass: str = field(default_factory=lambda: os.getenv("SMTP_PASS", ""))
    smtp_from: str = field(init=False)
    resend_api_key: str = field(default_factory=lambda: os.getenv("RESEND_API_KEY", ""))
    sendgrid_api_key: str = field(default_factory=lambda: os.getenv("SENDGRID_API_KEY", ""))

    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", "") or os.getenv("GEMINI_API_CHAT_KEY", ""))
    siliconflow_api_key: str = field(default_factory=lambda: os.getenv("SILICONFLOW_API_KEY", ""))
    deepseek_api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    google_tts_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_TTS_API_KEY", ""))
    # ── ElevenLabs TTS（最接近真人的优美嗓音；配置 key 后 /api/tts 优先使用）──
    elevenlabs_api_key: str = field(default_factory=lambda: os.getenv("ELEVENLABS_API_KEY", ""))
    # 默认 Matilda（温暖女声，eleven_multilingual_v2 中文自然）；建议在 ElevenLabs Voice
    # Library 选中文/多语女声并设 ELEVENLABS_VOICE_ID 覆盖。
    elevenlabs_voice_id: str = field(default_factory=lambda: os.getenv("ELEVENLABS_VOICE_ID", "XrExE9yKIg1WjnnlVkGX"))
    elevenlabs_model: str = field(default_factory=lambda: os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2"))
    vapid_public_key: str = field(default_factory=lambda: os.getenv("VAPID_PUBLIC_KEY", ""))
    vapid_private_key: str = field(default_factory=lambda: os.getenv("VAPID_PRIVATE_KEY", ""))
    vapid_subject: str = field(default_factory=lambda: os.getenv("VAPID_SUBJECT", "mailto:noreply@bible-sphere.com"))
    push_cron_secret: str = field(default_factory=lambda: os.getenv("PUSH_CRON_SECRET", ""))

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "smtp_from",
            os.getenv("SMTP_FROM", self.smtp_user or "noreply@bible-sphere.com"),
        )


settings = Settings()
