#!/usr/bin/env python3
"""
SFDS Temporal Engine — Time-series analytics module.

Responsibilities:
- Ingest spiritual timeline records from TimescaleDB (or in-memory fallback)
- Detect cycles, spirals, burnout trajectories, and spiritual seasons
- Identify intervention windows (when user is most vulnerable to poor decisions)
- Produce TemporalInsight for the V2 Discernment Engine
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Domain enumerations
# ──────────────────────────────────────────────────────────────────────────────

class TrendDirection(str, Enum):
    IMPROVING   = "improving"
    DECLINING   = "declining"
    STABLE      = "stable"
    VOLATILE    = "volatile"
    UNKNOWN     = "unknown"


class PatternType(str, Enum):
    CYCLE       = "cycle"       # repeating up/down at regular interval
    SPIRAL      = "spiral"      # feedback loop worsening each cycle
    BURNOUT     = "burnout"     # sustained high-stress → crash
    SEASONAL    = "seasonal"    # multi-week low / high season
    ACUTE       = "acute"       # sudden spike, not part of pattern
    STABLE      = "stable"
    IMPROVING   = "improving"


class SpiritualSeason(str, Enum):
    DRY         = "dry"         # dryness > 6, peace < 4
    STABLE      = "stable"
    GROWING     = "growing"     # clarity ↑, peace ↑
    CONFUSED    = "confused"    # high volatility, low clarity
    RESTORING   = "restoring"   # recovering from dry/burnout


# ──────────────────────────────────────────────────────────────────────────────
# Data containers
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SpiritualDataPoint:
    """One row from sfds_user_spiritual_timeline."""
    recorded_at:        datetime
    anxiety_level:      float = 5.0
    peace_level:        float = 5.0
    clarity_level:      float = 5.0
    spiritual_dryness:  float = 5.0
    emotional_stability: float = 5.0
    decision_confidence: float = 5.0


@dataclass
class EmotionDataPoint:
    """One row from sfds_emotional_cycle_series."""
    recorded_at:   datetime
    emotion_type:  str
    intensity:     float


@dataclass
class DetectedPattern:
    pattern_type:  PatternType
    description:   str
    confidence:    float            # 0.0 – 1.0
    affected_metric: Optional[str] = None
    recurrence_days: Optional[int] = None   # approx period in days
    severity:      str = "moderate"         # low / moderate / high


@dataclass
class TemporalInsight:
    """Output delivered to the V2 Discernment Engine."""
    trend_direction:        TrendDirection
    spiritual_season:       SpiritualSeason
    detected_patterns:      List[DetectedPattern]

    # Specific flags
    is_peak_anxiety:        bool = False
    is_burnout_risk:        bool = False
    is_intervention_window: bool = False   # worst time to make decisions
    recurrence_count:       int  = 0       # how many times this pattern has appeared

    # Narrative summaries
    temporal_summary:       str = ""
    trend_detail:           str = ""
    intervention_guidance:  str = ""

    # Raw statistics (last N days)
    avg_anxiety_14d:        float = 0.0
    avg_peace_14d:          float = 0.0
    avg_dryness_14d:        float = 0.0
    avg_stability_14d:      float = 0.0
    data_points_available:  int   = 0


# ──────────────────────────────────────────────────────────────────────────────
# Database accessor
# ──────────────────────────────────────────────────────────────────────────────

class TemporalDataAccess:
    """
    Wraps PostgreSQL/TimescaleDB queries.
    Falls back gracefully if DB is not available.
    """

    def __init__(self, db_pool=None):
        self._pool = db_pool

    def get_spiritual_timeline(
        self,
        user_id: str,
        days: int = 90,
    ) -> List[SpiritualDataPoint]:
        if not self._pool:
            return []
        try:
            import psycopg2.extras
            conn = self._pool.getconn()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(
                        """
                        SELECT recorded_at, anxiety_level, peace_level, clarity_level,
                               spiritual_dryness, emotional_stability, decision_confidence
                        FROM sfds_user_spiritual_timeline
                        WHERE user_id = %s
                          AND recorded_at > NOW() - INTERVAL '%s days'
                        ORDER BY recorded_at ASC
                        """,
                        (user_id, days),
                    )
                    rows = cur.fetchall()
                    return [
                        SpiritualDataPoint(
                            recorded_at=r["recorded_at"],
                            anxiety_level=float(r["anxiety_level"] or 5),
                            peace_level=float(r["peace_level"] or 5),
                            clarity_level=float(r["clarity_level"] or 5),
                            spiritual_dryness=float(r["spiritual_dryness"] or 5),
                            emotional_stability=float(r["emotional_stability"] or 5),
                            decision_confidence=float(r["decision_confidence"] or 5),
                        )
                        for r in rows
                    ]
            finally:
                self._pool.putconn(conn)
        except Exception as exc:
            logger.warning("[temporal] get_spiritual_timeline failed: %s", exc)
            return []

    def get_emotion_series(
        self,
        user_id: str,
        emotion_type: Optional[str] = None,
        days: int = 90,
    ) -> List[EmotionDataPoint]:
        if not self._pool:
            return []
        try:
            import psycopg2.extras
            conn = self._pool.getconn()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    if emotion_type:
                        cur.execute(
                            """
                            SELECT recorded_at, emotion_type, intensity
                            FROM sfds_emotional_cycle_series
                            WHERE user_id = %s AND emotion_type = %s
                              AND recorded_at > NOW() - INTERVAL '%s days'
                            ORDER BY recorded_at ASC
                            """,
                            (user_id, emotion_type, days),
                        )
                    else:
                        cur.execute(
                            """
                            SELECT recorded_at, emotion_type, intensity
                            FROM sfds_emotional_cycle_series
                            WHERE user_id = %s
                              AND recorded_at > NOW() - INTERVAL '%s days'
                            ORDER BY recorded_at ASC
                            """,
                            (user_id, days),
                        )
                    rows = cur.fetchall()
                    return [
                        EmotionDataPoint(
                            recorded_at=r["recorded_at"],
                            emotion_type=r["emotion_type"],
                            intensity=float(r["intensity"]),
                        )
                        for r in rows
                    ]
            finally:
                self._pool.putconn(conn)
        except Exception as exc:
            logger.warning("[temporal] get_emotion_series failed: %s", exc)
            return []

    def insert_spiritual_record(
        self,
        user_id: str,
        anxiety: int,
        peace: int,
        clarity: int,
        dryness: int,
        stability: int,
        confidence: int,
        source_type: str = "checkin",
        source_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        if not self._pool:
            return False
        try:
            conn = self._pool.getconn()
            try:
                with conn.cursor() as cur:
                    composite = round(
                        (peace + clarity + stability + confidence - anxiety - dryness) / 6 + 5, 2
                    )
                    composite = max(0.0, min(10.0, composite))
                    cur.execute(
                        """
                        INSERT INTO sfds_user_spiritual_timeline
                          (user_id, anxiety_level, peace_level, clarity_level,
                           spiritual_dryness, emotional_stability, decision_confidence,
                           source_type, source_id, wellbeing_composite)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (user_id, recorded_at) DO NOTHING
                        """,
                        (user_id, anxiety, peace, clarity, dryness,
                         stability, confidence, source_type, source_id, composite),
                    )
                    conn.commit()
                    return True
            finally:
                self._pool.putconn(conn)
        except Exception as exc:
            logger.warning("[temporal] insert_spiritual_record failed: %s", exc)
            return False

    def insert_emotion_record(
        self,
        user_id: str,
        emotion_type: str,
        intensity: int,
        trigger: Optional[str] = None,
        decision_id: Optional[str] = None,
    ) -> bool:
        if not self._pool:
            return False
        try:
            conn = self._pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO sfds_emotional_cycle_series
                          (user_id, emotion_type, intensity, trigger_description, decision_context_id)
                        VALUES (%s,%s,%s,%s,%s)
                        """,
                        (user_id, emotion_type, intensity, trigger, decision_id),
                    )
                    conn.commit()
                    return True
            finally:
                self._pool.putconn(conn)
        except Exception as exc:
            logger.warning("[temporal] insert_emotion_record failed: %s", exc)
            return False


# ──────────────────────────────────────────────────────────────────────────────
# Temporal Engine
# ──────────────────────────────────────────────────────────────────────────────

class TemporalEngine:
    """
    Analyzes spiritual formation time-series data to produce a TemporalInsight.

    Works in two modes:
    - **Live**: reads real user data from TimescaleDB via TemporalDataAccess.
    - **Snapshot**: accepts inline data when no DB history exists (e.g., first-time users).
    """

    def __init__(self, data_access: Optional[TemporalDataAccess] = None):
        self.dao = data_access or TemporalDataAccess()

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze(
        self,
        user_id: str,
        current_snapshot: Optional[Dict[str, Any]] = None,
        window_days: int = 90,
    ) -> TemporalInsight:
        """
        Build a TemporalInsight for a user.

        Args:
            user_id:          User UUID string.
            current_snapshot: Dict with keys matching SpiritualDataPoint fields
                              (used as the most recent data point when provided).
            window_days:      How many days of history to analyse.
        """
        timeline = self.dao.get_spiritual_timeline(user_id, window_days)
        emotion_series = self.dao.get_emotion_series(user_id, days=window_days)

        # Inject current snapshot as the most recent point
        if current_snapshot:
            now = datetime.now(tz=timezone.utc)
            timeline.append(SpiritualDataPoint(
                recorded_at=now,
                anxiety_level=float(current_snapshot.get("anxiety_level", 5)),
                peace_level=float(current_snapshot.get("peace_level", 5)),
                clarity_level=float(current_snapshot.get("clarity_level", 5)),
                spiritual_dryness=float(current_snapshot.get("spiritual_dryness", 5)),
                emotional_stability=float(current_snapshot.get("emotional_stability", 5)),
                decision_confidence=float(current_snapshot.get("decision_confidence", 5)),
            ))

        if not timeline:
            return self._empty_insight()

        stats_14d = self._compute_stats(timeline, days=14)
        trend = self._compute_trend(timeline)
        season = self._classify_season(stats_14d, trend)
        patterns = self._detect_patterns(timeline, emotion_series)
        is_peak_anxiety = stats_14d.get("anxiety", 5) >= 7
        is_burnout_risk = self._check_burnout(timeline)
        is_intervention = is_peak_anxiety or is_burnout_risk or (
            stats_14d.get("stability", 5) < 4
        )
        recurrence = self._count_recurrences(patterns)

        summary = self._build_summary(
            trend, season, patterns, is_peak_anxiety, is_burnout_risk, stats_14d
        )
        guidance = self._build_intervention_guidance(is_intervention, patterns, season)

        return TemporalInsight(
            trend_direction=trend,
            spiritual_season=season,
            detected_patterns=patterns,
            is_peak_anxiety=is_peak_anxiety,
            is_burnout_risk=is_burnout_risk,
            is_intervention_window=is_intervention,
            recurrence_count=recurrence,
            temporal_summary=summary,
            trend_detail=self._trend_detail(timeline),
            intervention_guidance=guidance,
            avg_anxiety_14d=round(stats_14d.get("anxiety", 5), 2),
            avg_peace_14d=round(stats_14d.get("peace", 5), 2),
            avg_dryness_14d=round(stats_14d.get("dryness", 5), 2),
            avg_stability_14d=round(stats_14d.get("stability", 5), 2),
            data_points_available=len(timeline),
        )

    # ── Trend computation ─────────────────────────────────────────────────────

    def _compute_stats(
        self, timeline: List[SpiritualDataPoint], days: int = 14
    ) -> Dict[str, float]:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        recent = [p for p in timeline if p.recorded_at.replace(tzinfo=timezone.utc) >= cutoff]
        if not recent:
            recent = timeline[-min(5, len(timeline)):]
        if not recent:
            return {"anxiety": 5, "peace": 5, "clarity": 5, "dryness": 5, "stability": 5}

        def avg(vals):
            return statistics.mean(vals) if vals else 5.0

        return {
            "anxiety":   avg([p.anxiety_level       for p in recent]),
            "peace":     avg([p.peace_level          for p in recent]),
            "clarity":   avg([p.clarity_level        for p in recent]),
            "dryness":   avg([p.spiritual_dryness    for p in recent]),
            "stability": avg([p.emotional_stability  for p in recent]),
            "confidence":avg([p.decision_confidence  for p in recent]),
        }

    def _compute_trend(self, timeline: List[SpiritualDataPoint]) -> TrendDirection:
        if len(timeline) < 4:
            return TrendDirection.UNKNOWN

        # Compare average wellbeing of first half vs second half
        mid = len(timeline) // 2
        first_half  = timeline[:mid]
        second_half = timeline[mid:]

        def wellbeing(pts: List[SpiritualDataPoint]) -> float:
            return statistics.mean(
                (p.peace_level + p.clarity_level + p.emotional_stability
                 - p.anxiety_level - p.spiritual_dryness) / 3
                for p in pts
            )

        w1 = wellbeing(first_half)
        w2 = wellbeing(second_half)
        delta = w2 - w1

        # Volatility check
        stabilities = [p.emotional_stability for p in timeline[-10:]]
        vol = statistics.stdev(stabilities) if len(stabilities) >= 3 else 0
        if vol > 2.5:
            return TrendDirection.VOLATILE

        if delta > 1.0:
            return TrendDirection.IMPROVING
        elif delta < -1.0:
            return TrendDirection.DECLINING
        return TrendDirection.STABLE

    # ── Pattern detection ─────────────────────────────────────────────────────

    def _detect_patterns(
        self,
        timeline: List[SpiritualDataPoint],
        emotion_series: List[EmotionDataPoint],
    ) -> List[DetectedPattern]:
        patterns: List[DetectedPattern] = []

        patterns.extend(self._detect_anxiety_cycle(timeline))
        patterns.extend(self._detect_burnout_trajectory(timeline))
        patterns.extend(self._detect_spiral(timeline))
        patterns.extend(self._detect_seasonality(timeline))
        patterns.extend(self._detect_emotion_cycles(emotion_series))

        return patterns

    def _detect_anxiety_cycle(
        self, timeline: List[SpiritualDataPoint]
    ) -> List[DetectedPattern]:
        """Detect recurring spikes in anxiety (e.g. weekly Monday pattern)."""
        if len(timeline) < 14:
            return []

        spikes = [p for p in timeline if p.anxiety_level >= 7]
        if len(spikes) < 2:
            return []

        # Check for regular spacing
        if len(spikes) >= 3:
            gaps = []
            for i in range(1, len(spikes)):
                delta = (spikes[i].recorded_at - spikes[i - 1].recorded_at).days
                gaps.append(delta)
            avg_gap = statistics.mean(gaps)
            gap_stdev = statistics.stdev(gaps) if len(gaps) >= 2 else 999

            if gap_stdev < avg_gap * 0.4:  # Regular spacing
                period = round(avg_gap)
                return [DetectedPattern(
                    pattern_type=PatternType.CYCLE,
                    description=f"Anxiety spikes detected approximately every {period} days.",
                    confidence=min(0.9, 0.5 + len(spikes) * 0.1),
                    affected_metric="anxiety_level",
                    recurrence_days=period,
                    severity="high" if len(spikes) >= 5 else "moderate",
                )]

        return [DetectedPattern(
            pattern_type=PatternType.ACUTE,
            description=f"Multiple high-anxiety episodes detected ({len(spikes)} spikes in {len(timeline)} data points).",
            confidence=0.6,
            affected_metric="anxiety_level",
            severity="moderate",
        )]

    def _detect_burnout_trajectory(
        self, timeline: List[SpiritualDataPoint]
    ) -> List[DetectedPattern]:
        """High sustained stress + declining peace/stability = burnout trajectory."""
        if len(timeline) < 7:
            return []

        recent = timeline[-14:]
        high_dryness_count = sum(1 for p in recent if p.spiritual_dryness >= 7)
        low_peace_count    = sum(1 for p in recent if p.peace_level <= 3)
        low_stability      = sum(1 for p in recent if p.emotional_stability <= 4)

        score = (high_dryness_count + low_peace_count + low_stability) / (3 * len(recent))
        if score > 0.5:
            return [DetectedPattern(
                pattern_type=PatternType.BURNOUT,
                description=(
                    f"Burnout trajectory detected: sustained spiritual dryness "
                    f"({high_dryness_count}/{len(recent)} readings), low peace, "
                    f"and emotional instability over the last {len(recent)} data points."
                ),
                confidence=min(0.95, score + 0.3),
                affected_metric="spiritual_dryness",
                severity="high",
            )]
        return []

    def _detect_spiral(
        self, timeline: List[SpiritualDataPoint]
    ) -> List[DetectedPattern]:
        """Fear/avoidance → more anxiety → deeper spiral."""
        if len(timeline) < 6:
            return []

        # Compute wellbeing score at each quarter
        n = len(timeline)
        q = max(1, n // 4)
        quarters = [
            statistics.mean(p.anxiety_level for p in timeline[i:i + q])
            for i in range(0, n, q)
        ]

        # Monotonically worsening anxiety across quarters = spiral
        if len(quarters) >= 3 and all(quarters[i] < quarters[i + 1] for i in range(len(quarters) - 1)):
            return [DetectedPattern(
                pattern_type=PatternType.SPIRAL,
                description=(
                    "Escalating anxiety spiral detected: anxiety has increased each "
                    "successive period, suggesting a self-reinforcing feedback loop."
                ),
                confidence=0.75,
                affected_metric="anxiety_level",
                severity="high",
            )]
        return []

    def _detect_seasonality(
        self, timeline: List[SpiritualDataPoint]
    ) -> List[DetectedPattern]:
        """Detect multi-week low / high seasons."""
        if len(timeline) < 21:
            return []

        # Rolling 7-day average dryness
        window = 7
        rolling_dryness = []
        for i in range(len(timeline) - window + 1):
            chunk = timeline[i:i + window]
            rolling_dryness.append(statistics.mean(p.spiritual_dryness for p in chunk))

        sustained_dry = sum(1 for v in rolling_dryness if v > 6)
        ratio = sustained_dry / len(rolling_dryness)

        if ratio > 0.4:
            return [DetectedPattern(
                pattern_type=PatternType.SEASONAL,
                description=(
                    "Extended spiritual dryness season detected: dryness sustained "
                    f"above threshold for {round(ratio * 100)}% of the observation window."
                ),
                confidence=0.7,
                affected_metric="spiritual_dryness",
                recurrence_days=21,
                severity="moderate",
            )]
        return []

    def _detect_emotion_cycles(
        self, emotion_series: List[EmotionDataPoint]
    ) -> List[DetectedPattern]:
        """Detect recurring emotion spikes in the emotion cycle series."""
        if not emotion_series:
            return []

        # Group by emotion type
        from collections import defaultdict
        by_type: Dict[str, List[EmotionDataPoint]] = defaultdict(list)
        for ep in emotion_series:
            by_type[ep.emotion_type].append(ep)

        results: List[DetectedPattern] = []
        for etype, pts in by_type.items():
            high_pts = [p for p in pts if p.intensity >= 7]
            if len(high_pts) < 3:
                continue

            # Check for regularity
            if len(high_pts) >= 3:
                gaps = [
                    (high_pts[i + 1].recorded_at - high_pts[i].recorded_at).days
                    for i in range(len(high_pts) - 1)
                ]
                avg_gap = statistics.mean(gaps)
                stdev_gap = statistics.stdev(gaps) if len(gaps) >= 2 else 999

                if stdev_gap < avg_gap * 0.5 and avg_gap <= 14:
                    results.append(DetectedPattern(
                        pattern_type=PatternType.CYCLE,
                        description=(
                            f"Recurring '{etype}' emotion cycle: "
                            f"high-intensity episodes (~{round(avg_gap)} days apart, "
                            f"{len(high_pts)} occurrences)."
                        ),
                        confidence=min(0.9, 0.4 + len(high_pts) * 0.1),
                        affected_metric=f"emotion:{etype}",
                        recurrence_days=round(avg_gap),
                        severity="high" if etype in ("fear", "shame", "despair") else "moderate",
                    ))
        return results

    # ── Season classification ─────────────────────────────────────────────────

    def _classify_season(
        self, stats: Dict[str, float], trend: TrendDirection
    ) -> SpiritualSeason:
        dryness = stats.get("dryness", 5)
        peace   = stats.get("peace", 5)
        clarity = stats.get("clarity", 5)
        anxiety = stats.get("anxiety", 5)
        stability = stats.get("stability", 5)

        if dryness > 6 and peace < 4:
            return SpiritualSeason.DRY

        if trend == TrendDirection.IMPROVING and peace > 6 and clarity > 6:
            return SpiritualSeason.GROWING

        if trend in (TrendDirection.VOLATILE,) or (anxiety > 6 and clarity < 4) or stability < 3:
            return SpiritualSeason.CONFUSED

        if trend == TrendDirection.IMPROVING and dryness > 4:
            return SpiritualSeason.RESTORING

        return SpiritualSeason.STABLE

    # ── Burnout check ─────────────────────────────────────────────────────────

    def _check_burnout(self, timeline: List[SpiritualDataPoint]) -> bool:
        if len(timeline) < 5:
            return False
        recent = timeline[-7:]
        avg_dryness  = statistics.mean(p.spiritual_dryness   for p in recent)
        avg_peace    = statistics.mean(p.peace_level         for p in recent)
        avg_stability= statistics.mean(p.emotional_stability for p in recent)
        return avg_dryness > 6.5 and avg_peace < 3.5 and avg_stability < 4.0

    # ── Recurrence counting ───────────────────────────────────────────────────

    def _count_recurrences(self, patterns: List[DetectedPattern]) -> int:
        return sum(
            1 for p in patterns
            if p.pattern_type in (PatternType.CYCLE, PatternType.SPIRAL)
        )

    # ── Narrative builders ────────────────────────────────────────────────────

    def _build_summary(
        self,
        trend: TrendDirection,
        season: SpiritualSeason,
        patterns: List[DetectedPattern],
        is_peak_anxiety: bool,
        is_burnout: bool,
        stats: Dict[str, float],
    ) -> str:
        lines = []

        trend_msgs = {
            TrendDirection.IMPROVING:  "在观察期内，整体灵性稳定性有所提升。",
            TrendDirection.DECLINING:  "在上一个周期，整体灵性稳定性有所下降。",
            TrendDirection.STABLE:     "灵性指标大致稳定。",
            TrendDirection.VOLATILE:   "检测到情绪稳定性有明显波动——指标起伏不定。",
            TrendDirection.UNKNOWN:    "历史数据不足，无法进行可靠的趋势评估。",
        }
        lines.append(trend_msgs.get(trend, ""))

        season_msgs = {
            SpiritualSeason.DRY:        "当前灵性季节：枯竭期。平安感较低，干渴感上升。",
            SpiritualSeason.GROWING:    "当前灵性季节：成长期。清晰度和内部平安感正在上升。",
            SpiritualSeason.CONFUSED:   "当前灵性季节：迷茫期。焦虑感高，清晰度低。",
            SpiritualSeason.RESTORING:  "当前灵性季节：恢复期。正在从一段艰难时期中恢复。",
            SpiritualSeason.STABLE:     "当前灵性季节：平稳期。",
        }
        lines.append(season_msgs.get(season, ""))

        if is_peak_anxiety:
            lines.append(
                f"⚠ 检测到焦虑高峰 (14天平均值: {stats.get('anxiety', 0):.1f}/10)。"
                "这是反应式决策的高风险窗口。"
            )
        if is_burnout:
            lines.append("⚠ 存在职业/灵性倦怠风险指标。休息与更新迫在眉睫。")

        if patterns:
            lines.append(f"识别出 {len(patterns)} 个时间模式：")
            for p in patterns[:3]:
                lines.append(f"  • {p.description}")

        return "\n".join(filter(None, lines))

    def _trend_detail(self, timeline: List[SpiritualDataPoint]) -> str:
        if len(timeline) < 3:
            return "数据不足，无法进行详细趋势分析。"
        recent = timeline[-min(14, len(timeline)):]
        avg_peace    = statistics.mean(p.peace_level         for p in recent)
        avg_anxiety  = statistics.mean(p.anxiety_level       for p in recent)
        avg_dryness  = statistics.mean(p.spiritual_dryness   for p in recent)
        avg_stability= statistics.mean(p.emotional_stability for p in recent)
        return (
            f"最后 {len(recent)} 个数据点 — "
            f"平安: {avg_peace:.1f}, 焦虑: {avg_anxiety:.1f}, "
            f"干渴: {avg_dryness:.1f}, 稳定性: {avg_stability:.1f}"
        )

    def _build_intervention_guidance(
        self,
        is_intervention: bool,
        patterns: List[DetectedPattern],
        season: SpiritualSeason,
    ) -> str:
        if not is_intervention:
            return (
                "当前状态未显示急性干预信号。请继续常规灵性操练，并进行正常的决策辨识。"
            )

        lines = ["这似乎是一个高风险的决策窗口。请考虑："]

        if any(p.pattern_type == PatternType.BURNOUT for p in patterns):
            lines.append("  • 在决定前，优先安排休息与恢复。倦怠感会扭曲判断力。")

        if any(p.pattern_type == PatternType.CYCLE for p in patterns):
            lines.append("  • 你可能正处于周期性的低谷。如果可能，请推迟决定，过几天再重新审视。")

        if any(p.pattern_type == PatternType.SPIRAL for p in patterns):
            lines.append("  • 恐惧螺旋可能会放大感知到的风险。请寻求稳重者的建议。")

        if season == SpiritualSeason.DRY:
            lines.append("  • 枯竭期的决策往往依赖于感觉而非信心。请寻求社群的支持。")

        if season == SpiritualSeason.CONFUSED:
            lines.append("  • 当前处于迷茫期：请慢下来，避免做出不可逆转的决定。")

        lines.append(
            "\n注：此引导反映了观察到的模式，而非命令。请将这些观察带入祷告，并咨询值得信赖的顾问。"
        )
        return "\n".join(lines)

    def _empty_insight(self) -> TemporalInsight:
        return TemporalInsight(
            trend_direction=TrendDirection.UNKNOWN,
            spiritual_season=SpiritualSeason.STABLE,
            detected_patterns=[],
            temporal_summary="暂无历史数据。此分析仅基于当前快照。",
            trend_detail="",
            intervention_guidance="",
        )
