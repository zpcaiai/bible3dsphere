"""
preference_vector.py — user preference vector from implicit verse feedback.

A user's preference vector is the average of the BGE-M3 embeddings of all
verses they have saved, prayed, or shared.  When fused with the query vector
at retrieval time, it biases search results toward the user's established
spiritual resonance patterns.

    pref_vec = mean(saved_verse_embeddings)   # shape (1024,)
    fused    = (1 - ALPHA) * query_vec + ALPHA * pref_vec
    fused   /= ||fused||                       # re-normalise

Usage:
    from preference_vector import get_user_preference_vector, ALPHA

    pref = get_user_preference_vector(user_id, db_pool, min_feedback=2)
    # pref is np.ndarray(1024,) or None if not enough data
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Fusion weight: how much the preference vector biases the query
# 0.0 = pure query,  1.0 = pure preference
ALPHA: float = 0.25

# Minimum number of feedback records required before applying personalisation
MIN_FEEDBACK: int = 2


def get_user_preference_vector(
    user_id: str,
    db_pool,
    min_feedback: int = MIN_FEEDBACK,
    feedback_types: tuple[str, ...] = ("saved", "prayed", "shared"),
    max_records: int = 50,
) -> Optional[np.ndarray]:
    """
    Return the averaged embedding for a user's implicit verse feedback,
    or None if there is insufficient data.

    Parameters
    ----------
    user_id       : user identifier
    db_pool       : psycopg2 connection pool
    min_feedback  : minimum number of records with embeddings required
    feedback_types: which feedback actions count as positive signal
    max_records   : cap — only use the most recent N records to keep fresh

    Returns
    -------
    np.ndarray of shape (embedding_dim,) normalised to unit length, or None.
    """
    if not db_pool:
        return None

    placeholders = ",".join(f"%s" for _ in feedback_types)
    sql = f"""
        SELECT embedding
        FROM   user_verse_feedback
        WHERE  user_id      = %s
          AND  feedback_type IN ({placeholders})
          AND  embedding     IS NOT NULL
        ORDER  BY created_at DESC
        LIMIT  %s
    """
    params = (user_id, *feedback_types, max_records)

    conn = None
    rows: list = []
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    except Exception as exc:
        logger.warning(f"[preference_vector] DB query failed: {exc}")
        return None
    finally:
        if conn is not None:
            db_pool.putconn(conn)

    if len(rows) < min_feedback:
        logger.debug(
            f"[preference_vector] user={user_id[:8]} only {len(rows)} records "
            f"(need {min_feedback}); skipping personalisation"
        )
        return None

    # Each row[0] is a list of floats from Postgres REAL[]
    vectors = []
    for (emb,) in rows:
        if emb and len(emb) > 0:
            vectors.append(np.array(emb, dtype=np.float32))

    if len(vectors) < min_feedback:
        return None

    pref = np.mean(vectors, axis=0)
    norm = np.linalg.norm(pref)
    if norm < 1e-8:
        return None
    return (pref / norm).astype(np.float32)


def fuse_query_with_preference(
    query_vec: np.ndarray,
    pref_vec: Optional[np.ndarray],
    alpha: float = ALPHA,
) -> np.ndarray:
    """
    Blend query_vec with pref_vec and return a normalised fused vector.

    If pref_vec is None or alpha is 0, returns query_vec unchanged.

    Parameters
    ----------
    query_vec : (dim,) normalised query embedding
    pref_vec  : (dim,) normalised preference vector, or None
    alpha     : fusion weight for preference side

    Returns
    -------
    np.ndarray of same shape, normalised to unit length
    """
    if pref_vec is None or alpha <= 0.0:
        return query_vec

    fused = (1.0 - alpha) * query_vec + alpha * pref_vec
    norm = np.linalg.norm(fused)
    if norm < 1e-8:
        return query_vec  # fallback: pref cancelled query
    return (fused / norm).astype(np.float32)
