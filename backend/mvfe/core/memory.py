"""
MEMORY MODULE (pgvector)
Embedding generation, similarity search, memory insertion.
"""
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MemoryItem:
    id: str
    user_id: str
    content: str
    similarity: float  # 0.0-1.0 cosine similarity
    timestamp: str


class MemoryStore:
    """Vector-based semantic memory using pgvector."""

    def __init__(self, db_pool, embedding_fn):
        """
        Args:
            db_pool: psycopg2 ThreadedConnectionPool
            embedding_fn: callable(text: str) -> List[float] — embedding function
        """
        self._pool = db_pool
        self._embed = embedding_fn

    def insert(self, user_id: str, content: str) -> str:
        """Insert a new memory and return its ID."""
        memory_id = str(uuid.uuid4())
        embedding = self._embed(content)
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO mvfe_memories (id, user_id, content, embedding, created_at)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (memory_id, user_id, content, embedding, datetime.utcnow()),
                )
                conn.commit()
            logger.info(f"[memory] inserted id={memory_id[:8]} user={user_id[:8]}")
            return memory_id
        except Exception as e:
            conn.rollback()
            logger.error(f"[memory] insert failed: {e}")
            raise
        finally:
            self._pool.putconn(conn)

    def search(self, user_id: str, query: str, top_k: int = 5) -> List[MemoryItem]:
        """Retrieve top-k most similar memories using cosine similarity."""
        embedding = self._embed(query)
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, user_id, content, created_at,
                              1 - (embedding <=> %s::vector) AS similarity
                       FROM mvfe_memories
                       WHERE user_id = %s
                       ORDER BY embedding <=> %s::vector
                       LIMIT %s""",
                    (embedding, user_id, embedding, top_k),
                )
                rows = cur.fetchall()
                return [
                    MemoryItem(
                        id=str(row[0]),
                        user_id=str(row[1]),
                        content=row[2],
                        timestamp=row[3].isoformat() if row[3] else "",
                        similarity=float(row[4]) if row[4] else 0.0,
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.warning(f"[memory] search failed: {e}")
            return []
        finally:
            self._pool.putconn(conn)
