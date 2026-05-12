"""
SFDS v3 — System Configuration

Reads from environment variables.
All safety constraints are enforced here — they CANNOT be overridden at runtime.
"""

import os
from typing import List


class Settings:
    # ── OpenAI ───────────────────────────────────────────────
    OPENAI_API_KEY:         str   = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL:           str   = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_EMBEDDING_MODEL: str   = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    # ── Postgres ─────────────────────────────────────────────
    POSTGRES_URL:           str   = os.getenv("POSTGRES_URL", "")

    # ── TimescaleDB ──────────────────────────────────────────
    TIMESCALE_URL:          str   = os.getenv("TIMESCALE_URL", "")

    # ── Neo4j ────────────────────────────────────────────────
    NEO4J_URI:              str   = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER:             str   = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD:         str   = os.getenv("NEO4J_PASSWORD", "")

    # ── Redis ────────────────────────────────────────────────
    REDIS_URL:              str   = os.getenv("REDIS_URL", "redis://localhost:6379")
    CACHE_TTL_SECONDS:      int   = int(os.getenv("CACHE_TTL_SECONDS", "300"))

    # ── API ──────────────────────────────────────────────────
    ENVIRONMENT:            str   = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL:              str   = os.getenv("LOG_LEVEL", "INFO")
    API_SECRET_KEY:         str   = os.getenv("API_SECRET_KEY", "dev-secret")

    @property
    def CORS_ORIGINS(self) -> List[str]:
        raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
        return [o.strip() for o in raw.split(",")]

    # ── Formation Engine ─────────────────────────────────────
    FORMATION_RECENCY_DECAY:  float = float(os.getenv("FORMATION_RECENCY_DECAY", "0.92"))
    FORMATION_SCORE_MIN:      float = float(os.getenv("FORMATION_SCORE_MIN", "0.05"))
    FORMATION_SCORE_MAX:      float = float(os.getenv("FORMATION_SCORE_MAX", "0.95"))
    FORMATION_CONFIDENCE_CAP: float = float(os.getenv("FORMATION_CONFIDENCE_CAP", "0.90"))

    # ── Safety constraints (HARD-CODED — DO NOT OVERRIDE) ────
    # These are design invariants, not configuration options.
    SYSTEM_MAX_CONFIDENCE:      float = 0.90    # never claim certainty
    SYSTEM_ALLOW_IDENTITY_LABELS: bool = False  # NEVER assign identity labels
    SYSTEM_ALLOW_MORAL_SCORING:   bool = False  # NEVER judge moral worth


settings = Settings()
