"""
SFDS v3 — Connection lifecycle management.

All service connections initialized once at startup, closed at shutdown.
Services obtain connections via module-level accessors.
"""

from __future__ import annotations

import logging
from typing import Dict

logger = logging.getLogger(__name__)

# ── Connection singletons ──────────────────────────────────────
_postgres_pool = None
_timescale_pool = None
_neo4j_driver   = None
_openai_client  = None
_redis_client   = None


async def init_connections() -> None:
    """Initialize all external service connections at app startup."""
    global _postgres_pool, _timescale_pool, _neo4j_driver, _openai_client, _redis_client

    from packages.config.settings import settings

    # Postgres + pgvector
    try:
        import asyncpg
        _postgres_pool = await asyncpg.create_pool(settings.POSTGRES_URL, min_size=2, max_size=10)
        logger.info("[connections] Postgres pool ready")
    except Exception as exc:
        logger.warning("[connections] Postgres failed: %s", exc)

    # TimescaleDB
    try:
        import asyncpg
        _timescale_pool = await asyncpg.create_pool(settings.TIMESCALE_URL, min_size=2, max_size=10)
        logger.info("[connections] TimescaleDB pool ready")
    except Exception as exc:
        logger.warning("[connections] TimescaleDB failed: %s", exc)

    # Neo4j
    try:
        from neo4j import AsyncGraphDatabase
        _neo4j_driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
        logger.info("[connections] Neo4j driver ready")
    except Exception as exc:
        logger.warning("[connections] Neo4j failed: %s", exc)

    # OpenAI
    try:
        from openai import AsyncOpenAI
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info("[connections] OpenAI client ready")
    except Exception as exc:
        logger.warning("[connections] OpenAI failed: %s", exc)

    # Redis (optional)
    try:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(settings.REDIS_URL)
        logger.info("[connections] Redis ready")
    except Exception as exc:
        logger.warning("[connections] Redis failed (optional): %s", exc)


async def close_connections() -> None:
    """Gracefully close all connections at app shutdown."""
    if _postgres_pool:
        await _postgres_pool.close()
    if _timescale_pool:
        await _timescale_pool.close()
    if _neo4j_driver:
        await _neo4j_driver.close()
    if _redis_client:
        await _redis_client.aclose()
    logger.info("[connections] All connections closed")


async def check_connections() -> Dict[str, bool]:
    """Health check — returns connectivity status for each store."""
    status: Dict[str, bool] = {}

    status["postgres"]   = _postgres_pool   is not None
    status["timescale"]  = _timescale_pool  is not None
    status["neo4j"]      = _neo4j_driver    is not None
    status["openai"]     = _openai_client   is not None
    status["redis"]      = _redis_client    is not None

    return status


def get_postgres_pool():      return _postgres_pool
def get_timescale_pool():     return _timescale_pool
def get_neo4j_driver():       return _neo4j_driver
def get_openai_client():      return _openai_client
def get_redis_client():       return _redis_client
