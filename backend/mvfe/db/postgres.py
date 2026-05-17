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


def get_dashboard_data(db_pool, user_id: str, hours: int = 168) -> dict:
    """
    Aggregate time-series data for the MVFE Dashboard.
    Returns emotion series, attention map, decision flow, formation curve.
    """
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            # Emotion time series
            cur.execute(
                """SELECT payload, created_at FROM mvfe_events
                   WHERE user_id = %s AND type = 'process' AND created_at > NOW() - INTERVAL '%s hours'
                   ORDER BY created_at ASC""",
                (user_id, hours),
            )
            emotion_series = []
            attention_series = []
            decision_series = []
            formation_series = []
            for row in cur.fetchall():
                payload = row[0] or {}
                ts = row[1].isoformat() if row[1] else None
                if isinstance(payload, str):
                    import json
                    try:
                        payload = json.loads(payload)
                    except:
                        payload = {}
                if payload.get("emotion"):
                    emotion_series.append({
                        "timestamp": ts,
                        **payload["emotion"],
                    })
                if payload.get("attention"):
                    attention_series.append({
                        "timestamp": ts,
                        **payload["attention"],
                    })
                if payload.get("decision"):
                    decision_series.append({
                        "timestamp": ts,
                        **payload["decision"],
                        "emotion": payload.get("emotion"),
                        "attention": payload.get("attention"),
                        "input": payload.get("input"),
                        "formation_score": payload.get("formation_score"),
                        "drift_score": payload.get("drift_score"),
                    })
                if payload.get("formation_score") is not None:
                    formation_series.append({
                        "timestamp": ts,
                        "formation_score": payload.get("formation_score", 0),
                        "drift_score": payload.get("drift_score", 0),
                    })

            # Attention aggregation — focus frequency
            focus_counts = {}
            for a in attention_series:
                focus = a.get("focus", "unknown")
                focus_counts[focus] = focus_counts.get(focus, 0) + 1
            total = sum(focus_counts.values()) or 1
            attention_map = {k: round(v / total, 3) for k, v in focus_counts.items()}

            # Decision flow (keep drivers + full context for detail modal)
            decision_flow = [
                {
                    "timestamp": d["timestamp"],
                    "type": d.get("type", "avoidance"),
                    "confidence": d.get("confidence", 0.5),
                    "drivers": d.get("drivers") or {"fear": 0.5, "ego": 0.3, "love": 0.2},
                    "emotion": d.get("emotion"),
                    "attention": d.get("attention"),
                    "input": d.get("input"),
                    "formation_score": d.get("formation_score"),
                    "drift_score": d.get("drift_score"),
                }
                for d in decision_series
            ]

            # Formation curve
            formation_curve = [
                {
                    "timestamp": f["timestamp"],
                    "formation_score": f.get("formation_score", 0),
                    "drift_score": f.get("drift_score", 0),
                }
                for f in formation_series
            ]

            return {
                "emotion_series": emotion_series,
                "attention_map": attention_map,
                "decision_flow": decision_flow,
                "formation_curve": formation_curve,
                "data_points": len(emotion_series),
            }
    finally:
        db_pool.putconn(conn)
