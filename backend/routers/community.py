"""
community router — anonymous aggregate emotion data for community resonance layer.

Endpoints:
  GET  /api/community/emotion-heatmap
       Returns aggregated emotion counts across all users (anonymized).
       Used by the 3-D sphere halo overlay in the frontend.

No PII is exposed — only emotion_label counts + optional hour bucket.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Callable, Optional

from fastapi import APIRouter, Request, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level dependency holders (injected by init_community_router)
_get_db: Optional[Callable] = None
_release_db: Optional[Callable] = None


def init_community_router(*, get_db: Callable, release_db: Callable) -> None:
    """Wire database helpers — called from main.py lifespan."""
    global _get_db, _release_db
    _get_db = get_db
    _release_db = release_db
    logger.info("[community router] initialized")


# ── Emotion colour mapping (consistent with frontend sphere colours) ──────────
_EMOTION_COLOURS: dict[str, str] = {
    "joy":         "#FFD700",   # gold
    "peace":       "#87CEEB",   # sky blue
    "gratitude":   "#90EE90",   # light green
    "hope":        "#DDA0DD",   # plum
    "love":        "#FF69B4",   # hot pink
    "anxiety":     "#FFA500",   # orange
    "sadness":     "#6495ED",   # cornflower blue
    "fear":        "#DC143C",   # crimson
    "anger":       "#FF4500",   # orange red
    "shame":       "#8B4513",   # saddle brown
    "loneliness":  "#708090",   # slate gray
    "doubt":       "#9370DB",   # medium purple
    "exhaustion":  "#A9A9A9",   # dark gray
    # Chinese labels
    "喜乐":  "#FFD700",
    "平安":  "#87CEEB",
    "感恩":  "#90EE90",
    "盼望":  "#DDA0DD",
    "爱":    "#FF69B4",
    "焦虑":  "#FFA500",
    "悲伤":  "#6495ED",
    "恐惧":  "#DC143C",
    "愤怒":  "#FF4500",
    "羞愧":  "#8B4513",
    "孤独":  "#708090",
    "疑惑":  "#9370DB",
    "疲惫":  "#A9A9A9",
}

_DEFAULT_COLOUR = "#AAAAAA"


@router.get("/api/community/emotion-heatmap")
async def emotion_heatmap(
    request: Request,
    window_hours: int = 24,
    top_n: int = 12,
):
    """
    Return top-N anonymous emotion counts for the past `window_hours`.

    Response shape:
    {
      "window_hours": 24,
      "total_checkins": 312,
      "emotions": [
        { "label": "peace",  "count": 87, "pct": 27.9, "colour": "#87CEEB" },
        ...
      ],
      "generated_at": "2025-05-27T10:00:00Z"
    }
    """
    if window_hours < 1 or window_hours > 168:
        raise HTTPException(status_code=400, detail="window_hours must be 1–168")
    if top_n < 1 or top_n > 50:
        raise HTTPException(status_code=400, detail="top_n must be 1–50")

    if _get_db is None:
        raise HTTPException(status_code=503, detail="DB not initialised")

    conn = _get_db()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT emotion_label,
                       COUNT(*) AS cnt
                FROM   user_checkins
                WHERE  checkin_at >= %s
                  AND  emotion_label <> ''
                GROUP  BY emotion_label
                ORDER  BY cnt DESC
                LIMIT  %s
                """,
                (cutoff, top_n),
            )
            rows = cur.fetchall()

        total_checkins: int
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM user_checkins WHERE checkin_at >= %s",
                (cutoff,),
            )
            total_checkins = cur.fetchone()[0] or 0

        counted_total = sum(r[1] for r in rows) or 1  # avoid /0
        emotions = [
            {
                "label":  row[0],
                "count":  row[1],
                "pct":    round(row[1] / counted_total * 100, 1),
                "colour": _EMOTION_COLOURS.get(row[0], _DEFAULT_COLOUR),
            }
            for row in rows
        ]

        return {
            "window_hours":   window_hours,
            "total_checkins": total_checkins,
            "emotions":       emotions,
            "generated_at":   datetime.now(timezone.utc).isoformat(),
        }

    except Exception as exc:
        logger.error(f"[community] emotion-heatmap error: {exc}")
        raise HTTPException(status_code=500, detail="Internal error") from exc
    finally:
        _release_db(conn)
