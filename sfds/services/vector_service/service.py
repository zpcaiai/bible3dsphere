"""
Vector Service — pgvector semantic search layer.

Responsibilities:
  - Embedding generation (OpenAI text-embedding-3-small)
  - Similarity search against spiritual_principles table
  - Historical case matching
  - Semantic context retrieval for core-engine

Does NOT contain graph logic.
Does NOT contain time-series logic.
Does NOT run LLM reasoning (only embeddings).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_instance: Optional["VectorService"] = None


def get_vector_service() -> "VectorService":
    global _instance
    if _instance is None:
        _instance = VectorService()
    return _instance


class VectorService:
    """
    Service boundary: pgvector semantic memory.

    Generates embeddings and performs cosine similarity search.
    Returns structured principle/case objects — no raw vectors outside.
    """

    def __init__(self, db_pool=None, openai_client=None):
        self._db_pool = db_pool
        self._openai  = openai_client

    async def search(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Semantic similarity search against the principles embedding store.
        """
        try:
            embedding = await self._embed(query)
            results   = await self._search_db(embedding, top_k)
            return {"query": query, "results": results, "count": len(results)}
        except Exception as exc:
            logger.warning("[vector-service] search failed: %s", exc)
            return {"query": query, "results": [], "count": 0}

    async def get_principles(self, context: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Retrieve spiritually aligned principles relevant to a decision context.
        """
        try:
            embedding = await self._embed(context)
            results   = await self._search_db(embedding, top_k)
            return {
                "context":    context[:100] + "..." if len(context) > 100 else context,
                "principles": results,
                "note":       "Principles are offered as reflective context, not directives.",
            }
        except Exception as exc:
            logger.warning("[vector-service] get_principles failed: %s", exc)
            return {"principles": []}

    async def _embed(self, text: str) -> List[float]:
        """Generate embedding via OpenAI API."""
        if not self._openai:
            from packages.config.connections import get_openai_client
            self._openai = get_openai_client()
        response = await self._openai.embeddings.create(
            input=text,
            model="text-embedding-3-small",
        )
        return response.data[0].embedding

    async def _search_db(
        self, embedding: List[float], top_k: int
    ) -> List[Dict[str, Any]]:
        """Execute pgvector cosine similarity query."""
        if not self._db_pool:
            return []
        async with self._db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, principle_en, principle_zh, category, source_ref,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM spiritual_principles
                ORDER BY embedding <=> $1::vector
                LIMIT $2
                """,
                embedding, top_k,
            )
            return [dict(r) for r in rows]
