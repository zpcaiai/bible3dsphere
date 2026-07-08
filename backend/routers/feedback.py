"""
feedback router -- implicit verse feedback for personalised retrieval.

Endpoints:
  POST /api/feedback/verse
       Record that a user saved / prayed / shared a verse.
       Embeds the verse text via BGE-M3 (SiliconFlow) and stores it in
       user_verse_feedback so get_user_preference_vector() can use it.

  GET  /api/feedback/verse
       Return the authenticated user's recent feedback (for UI display).

  GET  /api/feedback/preference-preview
       Return the top-3 feature labels that the user's preference vector
       most strongly activates -- useful for "Your spiritual themes" UI card.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Optional

from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

# Injected by init_feedback_router
_get_db: Optional[Callable]        = None
_release_db: Optional[Callable]    = None
_get_session_user: Optional[Callable] = None
_get_embeddings: Optional[Callable] = None   # query_emotion_verses.get_embeddings
_features_file: Optional[str]      = None
_matches_file: Optional[str]       = None
_cache_file: Optional[str]         = None


def init_feedback_router(
    *,
    get_db: Callable,
    release_db: Callable,
    get_session_user: Callable,
    get_embeddings: Callable,
    features_file: str,
    matches_file: str,
    cache_file: str,
) -> None:
    global _get_db, _release_db, _get_session_user, _get_embeddings
    global _features_file, _matches_file, _cache_file
    _get_db            = get_db
    _release_db        = release_db
    _get_session_user  = get_session_user
    _get_embeddings    = get_embeddings
    _features_file     = features_file
    _matches_file      = matches_file
    _cache_file        = cache_file
    logger.info("[feedback router] initialized")


# ── Request/Response models ───────────────────────────────────────────────────

class VerseFeedbackRequest(BaseModel):
    verse_pk_id:   Optional[str] = None
    verse_ref:     str           = Field("", max_length=120)
    verse_text:    str           = Field("", max_length=2000)
    feedback_type: str           = Field("saved", pattern="^(saved|prayed|shared)$")


# ── POST /api/feedback/verse ──────────────────────────────────────────────────

@router.post("/api/feedback/verse", status_code=201)
async def record_verse_feedback(payload: VerseFeedbackRequest, request: Request):
    """
    Record implicit feedback and embed the verse text asynchronously.
    Returns the created record id.
    """
    user = _get_session_user(request) if _get_session_user else None
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = str(user.get("user_id") or user.get("email") or "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    if _get_db is None:
        raise HTTPException(status_code=503, detail="DB not initialised")

    # Generate embedding (may be None if SiliconFlow is down)
    embedding: Optional[list] = None
    verse_for_embed = (payload.verse_text or payload.verse_ref).strip()
    if verse_for_embed and _get_embeddings:
        try:
            import numpy as np
            vecs = _get_embeddings([verse_for_embed])
            if vecs is not None and len(vecs) > 0:
                embedding = vecs[0].tolist()
        except Exception as emb_err:
            logger.warning(f"[feedback] embedding failed: {emb_err}")

    conn = _get_db()
    try:
        with conn.cursor() as cur:
            if payload.verse_pk_id:
                # UPSERT: one record per (user, verse, type)
                cur.execute(
                    """
                    INSERT INTO user_verse_feedback
                        (user_id, verse_pk_id, verse_ref, verse_text, feedback_type, embedding, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, verse_pk_id, feedback_type) DO UPDATE SET
                        verse_text  = EXCLUDED.verse_text,
                        embedding   = EXCLUDED.embedding,
                        created_at  = EXCLUDED.created_at
                    RETURNING id
                    """,
                    (
                        user_id,
                        payload.verse_pk_id,
                        payload.verse_ref[:120],
                        payload.verse_text[:2000],
                        payload.feedback_type,
                        embedding,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO user_verse_feedback
                        (user_id, verse_ref, verse_text, feedback_type, embedding, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        user_id,
                        payload.verse_ref[:120],
                        payload.verse_text[:2000],
                        payload.feedback_type,
                        embedding,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
            row = cur.fetchone()
            conn.commit()
        return {"ok": True, "id": row[0], "embedding_stored": embedding is not None}
    except Exception as exc:
        conn.rollback()
        logger.error(f"[feedback] insert failed: {exc}")
        raise HTTPException(status_code=500, detail="Failed to record feedback") from exc
    finally:
        _release_db(conn)


# ── GET /api/feedback/verse ───────────────────────────────────────────────────

@router.get("/api/feedback/verse")
async def get_verse_feedback(request: Request, limit: int = Query(default=30, ge=1, le=100)):
    """Return the user's recent verse feedback items."""
    user = _get_session_user(request) if _get_session_user else None
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    user_id = str(user.get("user_id") or user.get("email") or "")

    if _get_db is None:
        raise HTTPException(status_code=503, detail="DB not initialised")

    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, verse_pk_id, verse_ref, verse_text, feedback_type, created_at
                FROM   user_verse_feedback
                WHERE  user_id = %s
                ORDER  BY created_at DESC
                LIMIT  %s
                """,
                (user_id, limit),
            )
            rows = cur.fetchall()
        items = [
            {
                "id": r[0], "verse_pk_id": r[1], "verse_ref": r[2],
                "verse_text": r[3][:200], "feedback_type": r[4],
                "created_at": r[5].isoformat() if hasattr(r[5], "isoformat") else str(r[5]),
            }
            for r in rows
        ]
        return {"ok": True, "items": items, "count": len(items)}
    except Exception as exc:
        logger.error(f"[feedback] select failed: {exc}")
        raise HTTPException(status_code=500, detail="Failed to retrieve feedback") from exc
    finally:
        _release_db(conn)


# ── GET /api/feedback/preference-preview ─────────────────────────────────────

@router.get("/api/feedback/preference-preview")
async def preference_preview(request: Request):
    """
    Return the top-3 SAE feature labels that this user's preference vector
    activates most strongly -- a 'Your spiritual themes' summary card.
    """
    user = _get_session_user(request) if _get_session_user else None
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    user_id = str(user.get("user_id") or user.get("email") or "")

    if _get_db is None:
        raise HTTPException(status_code=503, detail="DB not initialised")

    try:
        from preference_vector import get_user_preference_vector
        import sys, os
        # db_pool access -- we borrow the raw pool from deps if available
        pref = None
        try:
            from core.deps import get_db_pool
            pref = get_user_preference_vector(user_id, get_db_pool())
        except Exception:
            pass

        if pref is None:
            return {"ok": True, "themes": [], "message": "insufficient_data"}

        # Load feature embeddings and find top matches
        from query_emotion_verses import _ensure_loaded, select_top_features
        import numpy as np

        features, feature_embeddings, _ = _ensure_loaded(
            _features_file, _matches_file, _cache_file
        )
        scores = np.dot(feature_embeddings, pref)
        top_idx = np.argsort(scores)[::-1][:5]
        themes = [
            {
                "label":      features[i].get("zh_label") or features[i].get("description", "")[:40],
                "feature_id": features[i].get("feature_id"),
                "score":      round(float(scores[i]), 4),
            }
            for i in top_idx
        ]
        return {"ok": True, "themes": themes}

    except Exception as exc:
        logger.error(f"[feedback] preference-preview error: {exc}")
        return {"ok": True, "themes": [], "message": "error"}
