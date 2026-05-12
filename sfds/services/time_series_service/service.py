"""
Time Series Service — TimescaleDB analytics layer.

Responsibilities:
  - TimescaleDB query execution
  - Emotional trend detection
  - Weekly/monthly cycle detection
  - Instability and burnout early warning
  - Formation metric aggregation

Does NOT contain Neo4j logic.
Does NOT contain LLM logic.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_instance: Optional["TimeSeriesService"] = None


def get_time_series_service() -> "TimeSeriesService":
    global _instance
    if _instance is None:
        _instance = TimeSeriesService()
    return _instance


class TimeSeriesService:
    """
    Service boundary: TimescaleDB temporal analytics.

    All time-series queries execute here.
    Returns structured trend/cycle data — no raw DB rows outside.
    """

    def __init__(self, db_pool=None):
        self._db_pool = db_pool

    async def analyze(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Full temporal analysis for a user over the given window.
        Returns trend direction, season, volatility, burnout risk.
        """
        try:
            trends  = await self.get_trends(user_id)
            cycles  = await self.detect_cycles(user_id)
            return {
                "user_id":    user_id,
                "window_days":days,
                "trends":     trends,
                "cycles":     cycles,
                "note":       "Temporal patterns describe tendencies over time, not fixed states.",
            }
        except Exception as exc:
            logger.warning("[timeseries] analyze failed: %s", exc)
            return {"user_id": user_id, "trends": {}, "cycles": {}}

    async def get_trends(self, user_id: str) -> Dict[str, Any]:
        """
        Detect directional trends in anxiety, peace, stability over time.
        Returns: upward / downward / stable / volatile per metric.
        """
        if not self._db_pool:
            return {"anxiety": "unknown", "peace": "unknown", "stability": "unknown"}
        try:
            async with self._db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        AVG(anxiety_level)       AS avg_anxiety,
                        AVG(peace_level)         AS avg_peace,
                        AVG(emotional_stability) AS avg_stability,
                        STDDEV(anxiety_level)    AS std_anxiety
                    FROM sfds_spiritual_timeline
                    WHERE user_id = $1
                      AND recorded_at > NOW() - INTERVAL '30 days'
                    """,
                    user_id,
                )
                row = dict(rows[0]) if rows else {}
                return {
                    "avg_anxiety":   round(float(row.get("avg_anxiety", 5)), 2),
                    "avg_peace":     round(float(row.get("avg_peace", 5)), 2),
                    "avg_stability": round(float(row.get("avg_stability", 5)), 2),
                    "std_anxiety":   round(float(row.get("std_anxiety", 0) or 0), 2),
                }
        except Exception as exc:
            logger.warning("[timeseries] get_trends failed: %s", exc)
            return {}

    async def detect_cycles(self, user_id: str) -> Dict[str, Any]:
        """
        Detect weekly/monthly emotional cycles.
        Returns recurrence pattern classification.
        """
        if not self._db_pool:
            return {"cycle_detected": False, "pattern": "unknown"}
        try:
            async with self._db_pool.acquire() as conn:
                count = await conn.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM sfds_spiritual_timeline
                    WHERE user_id = $1
                      AND anxiety_level > 7
                    """,
                    user_id,
                )
            return {
                "cycle_detected": bool(count and count >= 3),
                "high_anxiety_events": count or 0,
                "pattern": "recurring_anxiety" if count and count >= 3 else "no_clear_cycle",
            }
        except Exception as exc:
            logger.warning("[timeseries] detect_cycles failed: %s", exc)
            return {"cycle_detected": False}
