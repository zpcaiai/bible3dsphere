#!/usr/bin/env python3
"""
SFDS Formation Engine — v3.1

Layer 5 of the SFDS architecture: Long-term human character evolution.

Core question answered: "WHO AM I BECOMING?"

This engine models character NOT as static scoring but as TRAJECTORY EVOLUTION —
a dynamic representation of how repeated decisions, emotional patterns, and
behavioral loops progressively shape human inner dispositions over time.

The Formation Engine computes across 5 internal layers:

  Layer 1 — Behavioral Reinforcement Analysis
             Which loops are strengthening? Which are weakening?

  Layer 2 — Trajectory Direction Analysis
             stabilizing / fragmenting / improving_clarity / increasing_volatility / cyclical

  Layer 3 — Character Drift Detection
             Slow long-term changes across the 8 formation dimensions.

  Layer 4 — Loop Dominance Analysis
             Which behavioral loop currently dominates formation?

  Layer 5 — Spiritual Alignment Trend (non-dogmatic)
             Behavioral alignment toward truth, humility, love, rest — NOT moral judgment.

Update is weighted by:
  - Recency (more recent events weigh more)
  - Emotional intensity (high-intensity decisions matter more)
  - Loop repetition (repeated patterns amplified)
  - Reflection (user insight reduces negative reinforcement)

Output: FormationStateVector — 8 behavioral tendency indicators (0.05–0.95).
        NOT moral scores. NOT identity labels. Trajectory signals only.

Design invariants:
    - Dimensions are TENDENCIES, not identities. Never lock.
    - All values bounded 0.05–0.95. Never claim 0 or 1.
    - Output: probabilistic, descriptive, non-directive.
    - System is a mirror of becoming. NOT a verdict on being.
    - Genuine transformation is always structurally possible.
"""

from __future__ import annotations

import asyncio
import logging
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Character Dimensions
# ──────────────────────────────────────────────────────────────────────────────

class CharacterDimension(str, Enum):
    """
    The 8-dimension Formation State Vector.

    Each dimension is a BEHAVIORAL TENDENCY indicator — a directional signal
    built from repeated decisions and pattern engagement over time.

    These are NOT:
        - moral scores
        - personality type labels
        - fixed identity classifications

    They ARE:
        - trajectory tendency signals (0.05–0.95)
        - mirrors of behavioral momentum
        - indicators of formation direction
    """
    HUMILITY            = "humility"             # truth-seeking vs self-protection tendency
    FEAR_TENDENCY       = "fear_tendency"         # fear-driven response tendency (higher = more fear-driven)
    PRIDE_TENDENCY      = "pride_tendency"        # pride-driven response tendency (higher = more pride-driven)
    EMOTIONAL_STABILITY = "emotional_stability"   # regulated response vs reactive volatility
    TRUTH_ALIGNMENT     = "truth_alignment"       # alignment with honest self-perception + principle
    RELATIONAL_HEALTH   = "relational_health"     # other-oriented vs self-absorbed relational patterns
    RESILIENCE          = "resilience"            # recovery tendency after adversity
    SPIRITUAL_CLARITY   = "spiritual_clarity"     # clarity of inner values + reduction of dryness


# ── Dominant Loop Types ──────────────────────────────────────────────────────

class DominantLoop(str, Enum):
    """
    The 5 behavioral loops that most influence formation trajectory.
    Loop dominance indicates which structural dynamic is most actively
    shaping the user's character at this point in time.
    """
    FEAR_CONTROL        = "fear_control_loop"       # fear → control → overwork → burnout → fear
    SHAME_AVOIDANCE     = "shame_avoidance_loop"    # shame → avoidance → procrastination → anxiety
    PRIDE_COMPARISON    = "pride_comparison_loop"   # pride → comparison → anxiety → instability
    DESIRE_IMPULSE      = "desire_impulse_loop"     # desire → impulsive_action → regret → desire
    TRUTH_STABILITY     = "truth_stability_loop"    # truth-facing → reflection → stability (healthy)
    UNKNOWN             = "unknown"


# ── Trajectory Direction ─────────────────────────────────────────────────────

class TrajectoryDirection(str, Enum):
    STABILIZING          = "stabilizing"          # volatility decreasing, clarity improving
    FRAGMENTING          = "fragmenting"           # stability decreasing, loops intensifying
    IMPROVING_CLARITY    = "improving_clarity"     # truth_alignment + spiritual_clarity ↑
    INCREASING_VOLATILITY= "increasing_volatility" # emotional_stability ↓, fear_tendency ↑
    CYCLICAL             = "cyclical"              # repeating up/down, no net direction
    UNKNOWN              = "unknown"


# ── Pattern Category → Dimension Impact ─────────────────────────────────────
# Per-session raw delta values (before weighting).
# Negative = reinforcing a fear/pride/shame-driven tendency or reducing stability.
# Positive = movement toward health/clarity.

PATTERN_DIMENSION_IMPACT: Dict[str, Dict[CharacterDimension, float]] = {
    "fear": {
        CharacterDimension.FEAR_TENDENCY:        +0.18,   # fear loop reinforces fear tendency
        CharacterDimension.EMOTIONAL_STABILITY:  -0.12,
        CharacterDimension.HUMILITY:             -0.05,
        CharacterDimension.SPIRITUAL_CLARITY:    -0.08,
    },
    "pride": {
        CharacterDimension.PRIDE_TENDENCY:       +0.18,
        CharacterDimension.HUMILITY:             -0.20,
        CharacterDimension.RELATIONAL_HEALTH:    -0.10,
        CharacterDimension.TRUTH_ALIGNMENT:      -0.10,
    },
    "shame": {
        CharacterDimension.TRUTH_ALIGNMENT:      -0.15,
        CharacterDimension.EMOTIONAL_STABILITY:  -0.15,
        CharacterDimension.RESILIENCE:           -0.10,
        CharacterDimension.SPIRITUAL_CLARITY:    -0.10,
    },
    "desire": {
        CharacterDimension.RESILIENCE:           -0.08,
        CharacterDimension.EMOTIONAL_STABILITY:  -0.08,
        CharacterDimension.TRUTH_ALIGNMENT:      -0.05,
    },
    "relational": {
        CharacterDimension.RELATIONAL_HEALTH:    -0.12,
        CharacterDimension.TRUTH_ALIGNMENT:      -0.05,
        CharacterDimension.EMOTIONAL_STABILITY:  -0.06,
    },
    "spiritual": {
        CharacterDimension.HUMILITY:             -0.10,
        CharacterDimension.SPIRITUAL_CLARITY:    -0.18,
        CharacterDimension.EMOTIONAL_STABILITY:  -0.08,
        CharacterDimension.TRUTH_ALIGNMENT:      -0.08,
    },
    "growth": {
        CharacterDimension.RESILIENCE:           +0.15,
        CharacterDimension.TRUTH_ALIGNMENT:      +0.12,
        CharacterDimension.HUMILITY:             +0.08,
        CharacterDimension.SPIRITUAL_CLARITY:    +0.10,
        CharacterDimension.FEAR_TENDENCY:        -0.05,   # growth reduces fear loop
        CharacterDimension.PRIDE_TENDENCY:       -0.05,
    },
}

# Loop-break gains: applied when the engine detects a loop was interrupted
BREAKPOINT_DIMENSION_GAIN: Dict[str, Dict[CharacterDimension, float]] = {
    "fear": {
        CharacterDimension.FEAR_TENDENCY:        -0.20,   # reduces fear loop strength
        CharacterDimension.EMOTIONAL_STABILITY:  +0.15,
        CharacterDimension.SPIRITUAL_CLARITY:    +0.10,
    },
    "pride": {
        CharacterDimension.PRIDE_TENDENCY:       -0.20,
        CharacterDimension.HUMILITY:             +0.20,
        CharacterDimension.RELATIONAL_HEALTH:    +0.10,
    },
    "shame": {
        CharacterDimension.TRUTH_ALIGNMENT:      +0.20,
        CharacterDimension.RESILIENCE:           +0.15,
        CharacterDimension.EMOTIONAL_STABILITY:  +0.10,
    },
    "desire": {
        CharacterDimension.RESILIENCE:           +0.12,
        CharacterDimension.TRUTH_ALIGNMENT:      +0.10,
    },
    "relational": {
        CharacterDimension.RELATIONAL_HEALTH:    +0.20,
        CharacterDimension.TRUTH_ALIGNMENT:      +0.10,
    },
    "spiritual": {
        CharacterDimension.SPIRITUAL_CLARITY:    +0.20,
        CharacterDimension.HUMILITY:             +0.12,
        CharacterDimension.EMOTIONAL_STABILITY:  +0.10,
    },
    "growth": {
        CharacterDimension.RESILIENCE:           +0.10,
        CharacterDimension.TRUTH_ALIGNMENT:      +0.10,
        CharacterDimension.SPIRITUAL_CLARITY:    +0.08,
    },
}

# Loop category → DominantLoop classification
CATEGORY_TO_LOOP: Dict[str, DominantLoop] = {
    "fear":      DominantLoop.FEAR_CONTROL,
    "pride":     DominantLoop.PRIDE_COMPARISON,
    "shame":     DominantLoop.SHAME_AVOIDANCE,
    "desire":    DominantLoop.DESIRE_IMPULSE,
    "growth":    DominantLoop.TRUTH_STABILITY,
}


# ──────────────────────────────────────────────────────────────────────────────
# Formation data models
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class DimensionScore:
    """
    Tendency indicator for one character dimension.

    Score: 0.05–0.95 — a directional signal, never an absolute verdict.
    For FEAR_TENDENCY and PRIDE_TENDENCY: higher score = more active tendency.
    For all others: higher score = healthier tendency.
    """
    dimension:   CharacterDimension
    score:       float   # 0.05–0.95
    delta:       float   # weighted delta this session
    trend:       str     # "strengthening" | "weakening" | "stable"
    confidence:  float   # 0–0.90
    note:        str = ""


@dataclass
class FormationStateVector:
    """
    The core output of the Formation Engine.
    8-dimensional behavioral tendency representation.

    These are NOT moral scores. They are trajectory signals.
    """
    humility:            float = 0.50
    fear_tendency:       float = 0.50
    pride_tendency:      float = 0.50
    emotional_stability: float = 0.50
    truth_alignment:     float = 0.50
    relational_health:   float = 0.50
    resilience:          float = 0.50
    spiritual_clarity:   float = 0.50

    def to_dict(self) -> Dict[str, float]:
        return {
            "humility":            round(self.humility, 3),
            "fear_tendency":       round(self.fear_tendency, 3),
            "pride_tendency":      round(self.pride_tendency, 3),
            "emotional_stability": round(self.emotional_stability, 3),
            "truth_alignment":     round(self.truth_alignment, 3),
            "relational_health":   round(self.relational_health, 3),
            "resilience":          round(self.resilience, 3),
            "spiritual_clarity":   round(self.spiritual_clarity, 3),
        }

    @classmethod
    def from_scores(
        cls, scores: Dict[CharacterDimension, DimensionScore]
    ) -> "FormationStateVector":
        return cls(**{
            dim.value: sc.score
            for dim, sc in scores.items()
        })


@dataclass
class FormationSnapshot:
    """Complete formation snapshot for one pipeline session."""
    user_id:              str
    recorded_at:          datetime
    state_vector:         FormationStateVector
    dimensions:           Dict[str, DimensionScore]   # keyed by CharacterDimension.value
    dominant_dimension:   str                         # dimension with largest |delta|
    formation_arc:        str                         # breaking_through | deepening_loops | stabilizing | unknown
    trajectory_direction: str                         # TrajectoryDirection value
    dominant_loop:        str                         # DominantLoop value
    session_id:           str = ""
    decision_category:    str = ""
    pattern_categories:   List[str] = field(default_factory=list)
    loop_broken:          bool = False


@dataclass
class ReinforcementAnalysis:
    """Result of Layer 1: behavioral reinforcement state."""
    strengthening_dimensions: List[str]    # dimensions gaining strength
    weakening_dimensions:     List[str]    # dimensions losing strength
    dominant_loop:            str          # most active loop type
    loop_intensity:           float        # 0–1: how entrenched the loop is
    reinforcement_narrative:  str


@dataclass
class DriftAnalysis:
    """Result of Layer 3: long-term character drift."""
    drifting_dimensions: List[Tuple[str, float]]  # (dimension, drift_magnitude)
    drift_direction:     str                       # "toward_fear" | "toward_clarity" | "volatile" | "stable"
    drift_narrative:     str
    drift_detected:      bool


@dataclass
class FormationInsight:
    """
    Full output of Formation Engine — Layer 5 of SFDS pipeline.
    Passed into FormationOutput as the `formation` pillar.
    """
    user_id:              str
    current_snapshot:     FormationSnapshot
    state_vector:         FormationStateVector
    history_available:    bool
    data_points:          int

    # 5-layer analysis outputs
    reinforcement:        ReinforcementAnalysis
    trajectory_direction: str                    # TrajectoryDirection.value
    drift:                DriftAnalysis
    dominant_loop:        str                    # DominantLoop.value
    alignment_trend:      str                    # "improving" | "declining" | "stable"

    # Synthesized outputs
    trajectory_narrative: str
    current_trajectory:   str                    # one-line description
    dominant_patterns:    List[str]
    reinforcement_mechanisms: List[str]
    weakening_factors:    List[str]
    growth_moments:       List[str]
    reflective_question:  str

    formation_arc:        str
    dimension_scores:     Dict[str, float]       # flat dict for API

    DISCLAIMER: str = field(default=(
        "Formation patterns describe tendencies, not fixed traits. "
        "Genuine transformation is always structurally possible. "
        "These signals are offered as a mirror for awareness, "
        "not a judgment on character or identity. "
        "This system NEVER optimizes for: human behavior change, "
        "emotional outcome optimization, personality state improvement, "
        "or behavioral compliance rate."
    ), compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_vector":        self.state_vector.to_dict(),
            "dimension_scores":    self.dimension_scores,
            "formation_arc":       self.formation_arc,
            "trajectory_direction":self.trajectory_direction,
            "dominant_loop":       self.dominant_loop,
            "alignment_trend":     self.alignment_trend,
            "current_trajectory":  self.current_trajectory,
            "dominant_patterns":   self.dominant_patterns,
            "reinforcement_mechanisms": self.reinforcement_mechanisms,
            "weakening_factors":   self.weakening_factors,
            "growth_moments":      self.growth_moments,
            "trajectory_narrative":self.trajectory_narrative,
            "reflective_question": self.reflective_question,
            "history_available":   self.history_available,
            "data_points":         self.data_points,
            "reinforcement": {
                "strengthening": self.reinforcement.strengthening_dimensions,
                "weakening":     self.reinforcement.weakening_dimensions,
                "dominant_loop": self.reinforcement.dominant_loop,
                "loop_intensity":self.reinforcement.loop_intensity,
                "narrative":     self.reinforcement.reinforcement_narrative,
            },
            "drift": {
                "detected":   self.drift.drift_detected,
                "direction":  self.drift.drift_direction,
                "dimensions": [
                    {"dimension": d, "magnitude": round(m, 3)}
                    for d, m in self.drift.drifting_dimensions
                ],
                "narrative":  self.drift.drift_narrative,
            },
            "disclaimer": self.DISCLAIMER,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Formation Engine — 5-Layer Computation
# ──────────────────────────────────────────────────────────────────────────────

class FormationEngine:
    """
    SFDS v3.1 Formation Engine — 5-layer character trajectory system.

    Answers: "WHO AM I BECOMING?"

    Computes the 8-dimension FormationStateVector via 5 internal layers:
      Layer 1: Behavioral Reinforcement (which loops are strengthening?)
      Layer 2: Trajectory Direction (where is this heading?)
      Layer 3: Character Drift Detection (slow long-term shifts)
      Layer 4: Loop Dominance (which behavioral loop dominates?)
      Layer 5: Spiritual Alignment Trend (behavioral alignment patterns)

    Update weighting:
      - Recency: exponential decay (more recent = higher weight)
      - Emotional intensity: multiplier on delta magnitude
      - Loop repetition: amplification factor for repeated patterns
      - Reflection: damping of negative impact when reflection is active
    """

    BASELINE_SCORE: float = 0.50
    SCORE_MIN:      float = 0.05
    SCORE_MAX:      float = 0.95
    RECENCY_DECAY:  float = 0.92    # per-session exponential decay (history[0] = weight 1.0)

    def __init__(self, db_pool=None):
        self._db_pool = db_pool

    # ── Public interface ──────────────────────────────────────────────────────

    async def analyze(
        self,
        user_id:             str,
        pattern_categories:  List[str],
        loop_broken:         bool = False,
        decision_category:   str = "other",
        session_id:          str = "",
        emotional_intensity: float = 5.0,   # 0–10; higher = more impactful
        reflection_active:   bool = False,
    ) -> FormationInsight:
        try:
            history = await self._load_recent_history(user_id, limit=30)
        except Exception as exc:
            logger.warning("[formation] DB load failed, using baseline: %s", exc)
            history = []
        return self._run_engine(
            user_id, pattern_categories, loop_broken,
            decision_category, session_id, history,
            emotional_intensity, reflection_active,
        )

    def analyze_sync(
        self,
        user_id:             str,
        pattern_categories:  List[str],
        loop_broken:         bool = False,
        decision_category:   str = "other",
        session_id:          str = "",
        preloaded_history:   Optional[List[Dict[str, Any]]] = None,
        emotional_intensity: float = 5.0,
        reflection_active:   bool = False,
    ) -> FormationInsight:
        """
        Synchronous entry point — used by FormationPipeline.run().
        Uses preloaded history or baseline when no DB access.
        """
        history = preloaded_history or []
        return self._run_engine(
            user_id, pattern_categories, loop_broken,
            decision_category, session_id, history,
            emotional_intensity, reflection_active,
        )

    async def record_formation_event(
        self,
        user_id:            str,
        session_id:         str,
        pattern_categories: List[str],
        loop_broken:        bool,
        dimension_deltas:   Dict[str, float],
        decision_category:  str = "other",
    ) -> None:
        """Persist to TimescaleDB sfds_formation_metrics. Silent failure."""
        if not self._db_pool:
            return

        def _sync_insert():
            conn = self._db_pool.getconn()
            try:
                _uid = _canon_uid(conn, user_id)
                with conn.cursor() as cur:
                    now = datetime.now(tz=timezone.utc)
                    cur.execute(
                        """
                        INSERT INTO sfds_formation_metrics (
                            user_id, session_id, recorded_at, decision_category,
                            loop_broken, pattern_categories,
                            humility_delta, fear_tendency_delta, pride_tendency_delta,
                            emotional_stability_delta, truth_alignment_delta,
                            relational_health_delta, resilience_delta, spiritual_clarity_delta
                        ) VALUES (
                            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                        )
                        """,
                        (
                            _uid, session_id, now, decision_category,
                            loop_broken, pattern_categories,
                            dimension_deltas.get("humility", 0.0),
                            dimension_deltas.get("fear_tendency", 0.0),
                            dimension_deltas.get("pride_tendency", 0.0),
                            dimension_deltas.get("emotional_stability", 0.0),
                            dimension_deltas.get("truth_alignment", 0.0),
                            dimension_deltas.get("relational_health", 0.0),
                            dimension_deltas.get("resilience", 0.0),
                            dimension_deltas.get("spiritual_clarity", 0.0),
                        ),
                    )
                    conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                self._db_pool.putconn(conn)

        try:
            await asyncio.to_thread(_sync_insert)
        except Exception as exc:
            logger.warning("[formation] record_formation_event failed: %s", exc)

    async def get_profile(self, user_id: str) -> Dict[str, Any]:
        try:
            history = await self._load_recent_history(user_id, limit=50)
        except Exception:
            history = []
        # Re-construct current session categories from most-recent history so
        # _layer4_loop_dominance has something to work with when no live
        # session is in progress.
        current_cats: List[str] = []
        if history:
            most_recent = history[0]
            current_cats = most_recent.get("pattern_categories") or []
        insight = self._run_engine(user_id, current_cats, False, "other", "", history)
        # Hide loop when not enough data points so the frontend naturally
        # suppresses the dominant_loop section (checks !== 'none').
        dominant_loop = insight.dominant_loop
        if dominant_loop == "unknown" and len(history) < 3:
            dominant_loop = "none"
        return {
            "user_id":            user_id,
            "schema":             "v3.1",
            "state_vector":       insight.state_vector.to_dict(),
            "formation_arc":      insight.formation_arc,
            "trajectory_direction": insight.trajectory_direction,
            "dominant_loop":      dominant_loop,
            "alignment_trend":    insight.alignment_trend,
            "current_trajectory": insight.current_trajectory,
            "dominant_patterns":  insight.dominant_patterns,
            "reinforcement_mechanisms": insight.reinforcement_mechanisms,
            "weakening_factors":  insight.weakening_factors,
            "growth_moments":     insight.growth_moments,
            "trajectory_narrative": insight.trajectory_narrative,
            "reflective_question":  insight.reflective_question,
            "data_points":        insight.data_points,
            "note": (
                "Formation state reflects accumulated tendencies, not fixed identity. "
                "Every decision creates new formation possibilities."
            ),
        }

    # ── Core 5-Layer Engine ───────────────────────────────────────────────────

    def _run_engine(
        self,
        user_id:             str,
        pattern_categories:  List[str],
        loop_broken:         bool,
        decision_category:   str,
        session_id:          str,
        history:             List[Dict[str, Any]],
        emotional_intensity: float = 5.0,
        reflection_active:   bool = False,
    ) -> FormationInsight:
        """Execute all 5 formation layers and synthesize output."""

        # Compute weighted base scores from history
        base = self._aggregate_history_weighted(history)

        # Layer 1 — Behavioral Reinforcement Analysis
        reinforcement = self._layer1_reinforcement(
            pattern_categories, loop_broken, history, emotional_intensity, reflection_active
        )

        # Apply weighted deltas to base scores
        scores = self._apply_deltas(
            base, pattern_categories, loop_broken,
            emotional_intensity, reflection_active, len(history)
        )

        # Layer 2 — Trajectory Direction
        trajectory_direction = self._layer2_trajectory(scores, history)

        # Layer 3 — Character Drift Detection
        drift = self._layer3_drift(scores, history)

        # Layer 4 — Loop Dominance
        dominant_loop = self._layer4_loop_dominance(
            pattern_categories, scores, history
        )

        # Layer 5 — Spiritual Alignment Trend
        alignment_trend = self._layer5_alignment(scores, history)

        # Build state vector
        state_vector = FormationStateVector.from_scores(scores)

        # Synthesize
        snapshot = FormationSnapshot(
            user_id              = user_id,
            recorded_at          = datetime.now(tz=timezone.utc),
            state_vector         = state_vector,
            dimensions           = {dim.value: sc for dim, sc in scores.items()},
            dominant_dimension   = max(scores, key=lambda d: abs(scores[d].delta)).value,
            formation_arc        = self._classify_arc(scores, history),
            trajectory_direction = trajectory_direction.value,
            dominant_loop        = dominant_loop.value,
            session_id           = session_id,
            decision_category    = decision_category,
            pattern_categories   = pattern_categories,
            loop_broken          = loop_broken,
        )

        flat = state_vector.to_dict()

        return FormationInsight(
            user_id              = user_id,
            current_snapshot     = snapshot,
            state_vector         = state_vector,
            history_available    = len(history) > 0,
            data_points          = len(history),
            reinforcement        = reinforcement,
            trajectory_direction = trajectory_direction.value,
            drift                = drift,
            dominant_loop        = dominant_loop.value,
            alignment_trend      = alignment_trend,
            trajectory_narrative = self._trajectory_narrative(
                snapshot, trajectory_direction, dominant_loop, drift, len(history)
            ),
            current_trajectory   = self._one_line_trajectory(trajectory_direction),
            dominant_patterns    = self._dominant_patterns(pattern_categories, dominant_loop),
            reinforcement_mechanisms = reinforcement.strengthening_dimensions,
            weakening_factors    = reinforcement.weakening_dimensions,
            growth_moments       = self._growth_moments(loop_broken, dominant_loop),
            reflective_question  = self._reflective_question(snapshot.dominant_dimension),
            formation_arc        = snapshot.formation_arc,
            dimension_scores     = flat,
        )

    # ── Layer 1: Behavioral Reinforcement ────────────────────────────────────

    def _layer1_reinforcement(
        self,
        categories:         List[str],
        loop_broken:        bool,
        history:            List[Dict[str, Any]],
        emotional_intensity: float,
        reflection_active:  bool,
    ) -> ReinforcementAnalysis:
        """
        Determine which loops/dimensions are strengthening vs weakening.
        Loop intensity = how many recent history rows share the same category.
        """
        strengthening: List[str] = []
        weakening:     List[str] = []

        for category in categories:
            impacts = PATTERN_DIMENSION_IMPACT.get(category, {})
            for dim, impact in impacts.items():
                adjusted = self._weight_impact(impact, emotional_intensity, reflection_active)
                if adjusted > 0.03:
                    strengthening.append(dim.value)
                elif adjusted < -0.03:
                    weakening.append(dim.value)

        if loop_broken:
            for category in categories:
                for dim in BREAKPOINT_DIMENSION_GAIN.get(category, {}):
                    if dim.value not in strengthening:
                        strengthening.append(dim.value)

        # Loop intensity: fraction of recent history sharing same category
        if history and categories:
            same = sum(
                1 for row in history[-10:]
                if any(c in (row.get("pattern_categories") or []) for c in categories)
            )
            intensity = min(0.95, same / max(len(history[-10:]), 1))
        else:
            intensity = 0.0

        dominant = CATEGORY_TO_LOOP.get(
            categories[0] if categories else "", DominantLoop.UNKNOWN
        )

        narrative = (
            f"Patterns in '{', '.join(categories)}' may be "
            + ("strengthening" if intensity > 0.5 else "active but not yet entrenched")
            + f" (loop intensity: {int(intensity * 100)}%). "
        )
        if loop_broken:
            narrative += "A loop interruption was detected — formation momentum may be shifting."

        return ReinforcementAnalysis(
            strengthening_dimensions = list(dict.fromkeys(strengthening))[:4],
            weakening_dimensions     = list(dict.fromkeys(weakening))[:4],
            dominant_loop            = dominant.value,
            loop_intensity           = round(intensity, 2),
            reinforcement_narrative  = narrative,
        )

    # ── Layer 2: Trajectory Direction ────────────────────────────────────────

    def _layer2_trajectory(
        self,
        scores:  Dict[CharacterDimension, DimensionScore],
        history: List[Dict[str, Any]],
    ) -> TrajectoryDirection:
        """
        Classify the overall formation trajectory direction.
        """
        stability_delta  = scores[CharacterDimension.EMOTIONAL_STABILITY].delta
        clarity_delta    = scores[CharacterDimension.SPIRITUAL_CLARITY].delta
        truth_delta      = scores[CharacterDimension.TRUTH_ALIGNMENT].delta
        fear_delta       = scores[CharacterDimension.FEAR_TENDENCY].delta
        resilience_delta = scores[CharacterDimension.RESILIENCE].delta

        # Check for cyclic pattern in history
        if len(history) >= 6:
            stab_vals = [row.get("emotional_stability_delta", 0) for row in history[:6]]
            if stab_vals:
                variance = statistics.variance(stab_vals) if len(stab_vals) > 1 else 0
                if variance > 0.02:
                    return TrajectoryDirection.CYCLICAL

        if clarity_delta > 0.05 and truth_delta > 0.05:
            return TrajectoryDirection.IMPROVING_CLARITY
        if stability_delta < -0.08 and fear_delta > 0.08:
            return TrajectoryDirection.INCREASING_VOLATILITY
        if resilience_delta > 0.05 and fear_delta < -0.03:
            return TrajectoryDirection.STABILIZING
        if fear_delta > 0.10 or stability_delta < -0.12:
            return TrajectoryDirection.FRAGMENTING
        return TrajectoryDirection.UNKNOWN

    # ── Layer 3: Character Drift Detection ───────────────────────────────────

    def _layer3_drift(
        self,
        scores:  Dict[CharacterDimension, DimensionScore],
        history: List[Dict[str, Any]],
    ) -> DriftAnalysis:
        """
        Detect slow long-term directional shifts across dimensions.
        A dimension is 'drifting' if its score is >0.15 away from baseline
        AND the delta direction is consistent across recent sessions.
        """
        drifting: List[Tuple[str, float]] = []

        for dim, sc in scores.items():
            drift_magnitude = abs(sc.score - self.BASELINE_SCORE)
            if drift_magnitude > 0.12:
                drifting.append((dim.value, round(drift_magnitude, 3)))

        drifting.sort(key=lambda x: x[1], reverse=True)
        drift_detected = len(drifting) >= 2

        # Classify drift direction
        fear_score    = scores[CharacterDimension.FEAR_TENDENCY].score
        clarity_score = scores[CharacterDimension.SPIRITUAL_CLARITY].score
        truth_score   = scores[CharacterDimension.TRUTH_ALIGNMENT].score

        if fear_score > 0.65:
            direction = "toward_fear_dominance"
        elif clarity_score > 0.65 and truth_score > 0.65:
            direction = "toward_clarity"
        elif drift_detected:
            direction = "volatile"
        else:
            direction = "stable"

        if drift_detected:
            drift_dims = ", ".join(d for d, _ in drifting[:3])
            narrative = (
                f"A possible long-term drift may be occurring in: {drift_dims}. "
                f"This is a slow structural shift, not a single-event reaction. "
                f"Sustained attention to these dimensions may be relevant."
            )
        else:
            narrative = (
                "No significant long-term character drift detected at this time. "
                "Formation appears within normal variation range."
            )

        return DriftAnalysis(
            drifting_dimensions = drifting[:5],
            drift_direction     = direction,
            drift_narrative     = narrative,
            drift_detected      = drift_detected,
        )

    # ── Layer 4: Loop Dominance ───────────────────────────────────────────────

    def _layer4_loop_dominance(
        self,
        categories: List[str],
        scores:     Dict[CharacterDimension, DimensionScore],
        history:    List[Dict[str, Any]],
    ) -> DominantLoop:
        """
        Identify the loop most structurally dominant in the user's formation.
        Uses both current category and historical pattern frequency.
        """
        # Count category frequency in history
        freq: Dict[str, int] = {}
        for row in history:
            for cat in (row.get("pattern_categories") or []):
                freq[cat] = freq.get(cat, 0) + 1

        # Add current session
        for cat in categories:
            freq[cat] = freq.get(cat, 0) + 3  # current session weighted x3

        if not freq:
            # Infer from state vector
            fear_score  = scores[CharacterDimension.FEAR_TENDENCY].score
            pride_score = scores[CharacterDimension.PRIDE_TENDENCY].score
            if fear_score > 0.60:
                return DominantLoop.FEAR_CONTROL
            if pride_score > 0.60:
                return DominantLoop.PRIDE_COMPARISON
            truth_score = scores[CharacterDimension.TRUTH_ALIGNMENT].score
            if truth_score > 0.65:
                return DominantLoop.TRUTH_STABILITY
            return DominantLoop.UNKNOWN

        dominant_cat = max(freq, key=lambda k: freq[k])
        return CATEGORY_TO_LOOP.get(dominant_cat, DominantLoop.UNKNOWN)

    # ── Layer 5: Spiritual Alignment Trend ───────────────────────────────────

    def _layer5_alignment(
        self,
        scores:  Dict[CharacterDimension, DimensionScore],
        history: List[Dict[str, Any]],
    ) -> str:
        """
        Behavioral alignment trend — NOT moral judgment.
        Measures movement toward/away from truth, humility, love, rest patterns.
        """
        truth_delta    = scores[CharacterDimension.TRUTH_ALIGNMENT].delta
        humility_delta = scores[CharacterDimension.HUMILITY].delta
        clarity_delta  = scores[CharacterDimension.SPIRITUAL_CLARITY].delta
        stability_delta= scores[CharacterDimension.EMOTIONAL_STABILITY].delta

        alignment_signal = truth_delta + humility_delta + clarity_delta + stability_delta

        if alignment_signal > 0.08:
            return "improving"
        if alignment_signal < -0.08:
            return "declining"
        return "stable"

    # ── Weighted Delta Application ────────────────────────────────────────────

    def _apply_deltas(
        self,
        base:                Dict[CharacterDimension, float],
        categories:          List[str],
        loop_broken:         bool,
        emotional_intensity: float,
        reflection_active:   bool,
        n_history:           int,
    ) -> Dict[CharacterDimension, DimensionScore]:
        """
        Apply weighted impact deltas to base scores and build DimensionScore objects.

        Weighting rules:
          1. Emotional intensity: scales delta by intensity/5.0 (intensity=5 → 1.0x)
          2. Reflection damping: reduces negative impact by 40% when active
          3. Loop repetition: handled via history aggregation (already in base)
        """
        raw_deltas: Dict[CharacterDimension, float] = {dim: 0.0 for dim in CharacterDimension}

        intensity_multiplier = emotional_intensity / 5.0  # 5=baseline, 10=double impact

        for category in categories:
            impacts = PATTERN_DIMENSION_IMPACT.get(category, {})
            for dim, impact in impacts.items():
                weighted = self._weight_impact(impact, emotional_intensity, reflection_active)
                raw_deltas[dim] += weighted

        if loop_broken:
            for category in categories:
                gains = BREAKPOINT_DIMENSION_GAIN.get(category, {})
                for dim, gain in gains.items():
                    raw_deltas[dim] += gain * intensity_multiplier

        # Build DimensionScore
        results: Dict[CharacterDimension, DimensionScore] = {}
        confidence = min(0.90, 0.25 + n_history * 0.025)

        for dim in CharacterDimension:
            old   = base.get(dim, self.BASELINE_SCORE)
            delta = raw_deltas.get(dim, 0.0)
            new   = max(self.SCORE_MIN, min(self.SCORE_MAX, old + delta))
            trend = self._score_trend(delta)
            results[dim] = DimensionScore(
                dimension  = dim,
                score      = round(new, 3),
                delta      = round(delta, 3),
                trend      = trend,
                confidence = round(confidence, 2),
                note       = self._dimension_note(dim, new, trend),
            )

        return results

    def _weight_impact(
        self, impact: float, emotional_intensity: float, reflection_active: bool
    ) -> float:
        multiplier = emotional_intensity / 5.0
        if impact < 0 and reflection_active:
            multiplier *= 0.60   # reflection dampens negative reinforcement
        return impact * multiplier

    # ── History Aggregation (recency-weighted) ────────────────────────────────

    def _aggregate_history_weighted(
        self, history: List[Dict[str, Any]]
    ) -> Dict[CharacterDimension, float]:
        """
        Aggregate historical dimension deltas using exponential recency weighting.
        history[0] = most recent → weight 1.0
        history[k] = weight = RECENCY_DECAY^k
        """
        agg: Dict[CharacterDimension, float] = {}
        total_weights: Dict[CharacterDimension, float] = {}

        for i, row in enumerate(history):
            w = self.RECENCY_DECAY ** i
            for dim in CharacterDimension:
                col = dim.value + "_delta"
                delta = row.get(col, 0.0) or 0.0
                agg[dim]           = agg.get(dim, 0.0) + delta * w
                total_weights[dim] = total_weights.get(dim, 0.0) + w

        result: Dict[CharacterDimension, float] = {}
        for dim in CharacterDimension:
            raw_acc = agg.get(dim, 0.0)
            result[dim] = max(
                self.SCORE_MIN,
                min(self.SCORE_MAX, self.BASELINE_SCORE + raw_acc)
            )
        return result

    # ── Synthesis helpers ─────────────────────────────────────────────────────

    def _classify_arc(
        self,
        scores:  Dict[CharacterDimension, DimensionScore],
        history: List[Dict[str, Any]],
    ) -> str:
        healthy_pos = sum(
            1 for dim, sc in scores.items()
            if sc.delta > 0.04
            and dim not in (CharacterDimension.FEAR_TENDENCY, CharacterDimension.PRIDE_TENDENCY)
        )
        fear_rising  = scores[CharacterDimension.FEAR_TENDENCY].delta > 0.06
        pride_rising = scores[CharacterDimension.PRIDE_TENDENCY].delta > 0.06

        if healthy_pos >= 3:
            return "breaking_through"
        if fear_rising or pride_rising:
            return "deepening_loops"
        if len(history) > 8:
            avg = statistics.mean(sc.score for dim, sc in scores.items()
                                  if dim not in (CharacterDimension.FEAR_TENDENCY,
                                                 CharacterDimension.PRIDE_TENDENCY))
            if avg > 0.58:
                return "stabilizing"
        return "unknown"

    def _trajectory_narrative(
        self,
        snapshot:    FormationSnapshot,
        direction:   TrajectoryDirection,
        loop:        DominantLoop,
        drift:       DriftAnalysis,
        n_history:   int,
    ) -> str:
        dir_phrases: Dict[TrajectoryDirection, str] = {
            TrajectoryDirection.STABILIZING: (
                "The formation trajectory may be stabilizing — patterns of clarity and "
                "emotional regulation appear to be gaining ground."
            ),
            TrajectoryDirection.FRAGMENTING: (
                "The formation trajectory may be fragmenting — fear-driven or reactive "
                "patterns appear to be intensifying. This is a structural observation, "
                "not a permanent condition."
            ),
            TrajectoryDirection.IMPROVING_CLARITY: (
                "A movement toward greater truth-alignment and spiritual clarity may be "
                "underway. This is a possible formation season of growing insight."
            ),
            TrajectoryDirection.INCREASING_VOLATILITY: (
                "Emotional volatility may be increasing — the gap between reactive patterns "
                "and reflective response may be widening. This signals a possible intervention window."
            ),
            TrajectoryDirection.CYCLICAL: (
                "A cyclical pattern may be active — the same dynamics appearing, "
                "stabilizing, and re-emerging over time. Structural intervention may "
                "be more effective than behavioral willpower alone."
            ),
            TrajectoryDirection.UNKNOWN: (
                "Formation trajectory is not yet clearly directional. "
                "More sessions over time will reveal the pattern."
            ),
        }
        base = dir_phrases.get(direction, dir_phrases[TrajectoryDirection.UNKNOWN])
        if loop != DominantLoop.UNKNOWN:
            base += f" The dominant behavioral loop may be: '{loop.value}'."
        if drift.drift_detected:
            base += f" {drift.drift_narrative}"
        if n_history == 0:
            base += " This is the beginning of the formation record."
        return base

    def _one_line_trajectory(self, direction: TrajectoryDirection) -> str:
        return {
            TrajectoryDirection.STABILIZING:           "stabilizing",
            TrajectoryDirection.FRAGMENTING:           "fragmenting",
            TrajectoryDirection.IMPROVING_CLARITY:     "improving clarity",
            TrajectoryDirection.INCREASING_VOLATILITY: "increasing volatility",
            TrajectoryDirection.CYCLICAL:              "cyclical",
            TrajectoryDirection.UNKNOWN:               "not yet determined",
        }.get(direction, "not yet determined")

    def _dominant_patterns(
        self, categories: List[str], loop: DominantLoop
    ) -> List[str]:
        patterns: List[str] = []
        if loop != DominantLoop.UNKNOWN:
            patterns.append(loop.value)
        for cat in categories:
            label = f"{cat}_pattern"
            if label not in patterns:
                patterns.append(label)
        return patterns[:3]

    def _growth_moments(self, loop_broken: bool, loop: DominantLoop) -> List[str]:
        if not loop_broken:
            return []
        return [
            f"A '{loop.value}' loop interruption may have occurred — "
            "a structural formation moment. "
            "Pattern breaks are often small and incremental, "
            "not dramatic breakthroughs."
        ]

    def _reflective_question(self, dominant_dimension: str) -> str:
        questions: Dict[str, str] = {
            "humility":            "What might be driving the need to protect your own perspective right now?",
            "fear_tendency":       "What might you be trying to control that you actually can't, and what would it feel like to release it?",
            "pride_tendency":      "Where might the need to be right or seen as capable be creating distance from others?",
            "emotional_stability": "What patterns seem to trigger reactions before reflection has a chance to engage?",
            "truth_alignment":     "Where might there be a gap between what you believe and how you're actually responding?",
            "relational_health":   "Whose perspective or needs might you be finding it difficult to hold alongside your own?",
            "resilience":          "What would recovery look like for you after a setback — not avoidance, but actual return?",
            "spiritual_clarity":   "What has been making it harder to access your own inner sense of clarity recently?",
        }
        return questions.get(
            dominant_dimension,
            "What is this pattern trying to show you about what you most deeply need right now?",
        )

    def _score_trend(self, delta: float) -> str:
        if delta > 0.03:  return "strengthening"
        if delta < -0.03: return "weakening"
        return "stable"

    def _dimension_note(self, dim: CharacterDimension, score: float, trend: str) -> str:
        if dim in (CharacterDimension.FEAR_TENDENCY, CharacterDimension.PRIDE_TENDENCY):
            if trend == "strengthening":
                return f"The '{dim.value}' may be increasing — this loop is gaining momentum."
            if trend == "weakening":
                return f"The '{dim.value}' may be decreasing — loop momentum may be slowing."
        else:
            if trend == "strengthening":
                return f"A tendency toward '{dim.value}' may be emerging — a possible formation signal."
            if trend == "weakening":
                return f"The '{dim.value}' may be under pressure — a possible formation area."
        return f"The '{dim.value}' appears relatively stable in current patterns."

    # ── DB access ─────────────────────────────────────────────────────────────

    async def _load_recent_history(
        self, user_id: str, limit: int = 30
    ) -> List[Dict[str, Any]]:
        if not self._db_pool:
            return []

        def _sync_load():
            conn = self._db_pool.getconn()
            try:
                _uid = _canon_uid(conn, user_id)
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                            recorded_at, loop_broken, pattern_categories,
                            humility_delta, fear_tendency_delta, pride_tendency_delta,
                            emotional_stability_delta, truth_alignment_delta,
                            relational_health_delta, resilience_delta, spiritual_clarity_delta
                        FROM sfds_formation_metrics
                        WHERE user_id = %s
                        ORDER BY recorded_at DESC
                        LIMIT %s
                        """,
                        (_uid, limit),
                    )
                    cols = [d[0] for d in cur.description]
                    return [dict(zip(cols, row)) for row in cur.fetchall()]
            finally:
                self._db_pool.putconn(conn)

        return await asyncio.to_thread(_sync_load)


# ──────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ──────────────────────────────────────────────────────────────────────────────

_formation_engine: Optional[FormationEngine] = None


_UID_EMAIL_CACHE: Dict[str, str] = {}


def _canon_uid(conn, user_id) -> str:
    """把数字 users.id 归一化成 email（formation 身份统一为 email）。
    非数字(已是 email/匿名)原样返回；查不到也原样返回。带进程内缓存。"""
    s = str(user_id or "")
    if not s.isdigit():
        return s
    if s in _UID_EMAIL_CACHE:
        return _UID_EMAIL_CACHE[s]
    email = s
    try:
        with conn.cursor() as c:
            c.execute("SELECT email FROM users WHERE id = %s", (int(s),))
            row = c.fetchone()
            if row and row[0]:
                email = str(row[0])
    except Exception:
        pass
    _UID_EMAIL_CACHE[s] = email
    return email


def get_formation_engine(db_pool=None) -> FormationEngine:
    global _formation_engine
    if _formation_engine is None:
        _formation_engine = FormationEngine(db_pool=db_pool)
    # Upgrade an existing engine that was created without a db_pool
    elif db_pool is not None and _formation_engine._db_pool is None:
        _formation_engine._db_pool = db_pool
    return _formation_engine


def init_formation_engine(db_pool) -> FormationEngine:
    global _formation_engine
    _formation_engine = FormationEngine(db_pool=db_pool)
    return _formation_engine
