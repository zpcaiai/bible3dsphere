"""
MVFE Stats Router
GET /api/mvfe/stats  — pipeline performance and governance audit metrics
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mvfe", tags=["mvfe"])

# Injected at startup
_get_db = None
_release_db = None
_get_session_user = None


def init_mvfe_stats_router(*, get_db, release_db, get_session_user=None):
    global _get_db, _release_db, _get_session_user
    _get_db = get_db
    _release_db = release_db
    _get_session_user = get_session_user


@router.get("/stats")
async def get_mvfe_stats(
    days: int = Query(default=30, ge=1, le=365, description="Lookback window in days"),
    user_scope: bool = Query(default=False, description="Scope to authenticated user only"),
):
    """Return aggregate MVFE pipeline statistics over the requested time window.

    Includes:
    - Pipeline run count and latency percentiles
    - Governance pass rate and violation breakdown
    - Critic coherence and overfit-risk averages
    - Formation score distribution
    - Top-10 detected primary emotions
    """
    from mvfe.metrics import get_pipeline_stats  # type: ignore

    user_id: Optional[str] = None
    if user_scope and _get_session_user is not None:
        try:
            user_id = _get_session_user()
        except Exception:
            pass

    db = None
    try:
        db = _get_db()
        stats = get_pipeline_stats(db, user_id=user_id, last_n_days=days)
        return {"ok": True, "stats": stats}
    except Exception as exc:
        logger.error(f"[mvfe_stats] get_stats failed: {exc}")
        return {"ok": False, "error": str(exc)}
    finally:
        if db is not None and _release_db is not None:
            try:
                _release_db(db)
            except Exception:
                pass
