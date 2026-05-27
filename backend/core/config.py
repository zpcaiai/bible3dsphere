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
    google_tts_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_TTS_API_KEY", ""))

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "smtp_from",
            os.getenv("SMTP_FROM", self.smtp_user or "noreply@bible-sphere.com"),
        )


settings = Settings()
