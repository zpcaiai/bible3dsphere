"""
Postgres initialization for MVFE.
Uses the existing psycopg2 ThreadedConnectionPool from main app.
"""
import logging

from .models import MVFE_TABLES_SQL, MVFE_TABLES_SQL_NO_VECTOR

logger = logging.getLogger(__name__)


def init_mvfe_tables(db_pool) -> bool:
    """
    Initialize MVFE tables. Tries with pgvector first, falls back to no-vector version.
    Returns True if successful.
    """
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            # Try with pgvector
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                conn.commit()
                cur.execute(MVFE_TABLES_SQL)
                conn.commit()
                logger.info("[mvfe-db] tables initialized with pgvector")
                return True
            except Exception:
                conn.rollback()
                # Fallback: without vector column
                cur.execute(MVFE_TABLES_SQL_NO_VECTOR)
                conn.commit()
                logger.info("[mvfe-db] tables initialized without pgvector (fallback)")
                return True
    except Exception as e:
        conn.rollback()
        logger.error(f"[mvfe-db] table init failed: {e}")
        return False
    finally:
        db_pool.putconn(conn)


def get_formation_state(db_pool, user_id: str) -> dict:
    """Get current formation state for a user."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT emotion, attention, decision, formation_score, drift_score, updated_at "
                "FROM mvfe_formation_state WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "emotion": row[0],
                "attention": row[1],
                "decision": row[2],
                "formation_score": row[3],
                "drift_score": row[4],
                "updated_at": row[5].isoformat() if row[5] else None,
            }
    finally:
        db_pool.putconn(conn)


def get_events_history(db_pool, user_id: str, limit: int = 20) -> list:
    """Get recent events for a user."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, type, payload, created_at FROM mvfe_events "
                "WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
                (user_id, limit),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": str(row[0]),
                    "type": row[1],
                    "payload": row[2],
                    "created_at": row[3].isoformat() if row[3] else None,
                }
                for row in rows
            ]
    finally:
        db_pool.putconn(conn)
