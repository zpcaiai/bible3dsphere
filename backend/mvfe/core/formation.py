"""
FORMATION ENGINE (CORE)
Computes formation_score, drift_score, stability_score from extracted states.
"""
import logging
from dataclasses import dataclass, asdict
from typing import Optional

from .emotion import EmotionState
from .attention import AttentionState
from .decision import DecisionState

logger = logging.getLogger(__name__)


EMA_ALPHA = 0.3  # weight of current session vs. history


@dataclass
class FormationResult:
    formation_score: float       # 0.0-1.0 instantaneous
    drift_score: float           # 0.0-1.0 temporal change proxy
    stability_score: float       # 0.0-1.0
    emotion_contribution: float
    attention_contribution: float
    decision_contribution: float
    formation_score_ema: float = 0.0  # 0.0-1.0 EMA across sessions
    session_count: int = 0            # total sessions for this user


class FormationEngine:
    """
    Computes formation dynamics from extracted state layers.

    formation_score = 0.4 * emotion_intensity + 0.3 * fixation_score + 0.3 * avoidance_score
    drift_score     = |current - previous_ema|
    stability_score = 1.0 - drift_score
    formation_score_ema = EMA_ALPHA * current + (1 - EMA_ALPHA) * previous_ema
                          (cross-session; seed = first instantaneous score)
    """

    def __init__(self):
        # In-process cache so we don't hit DB on every call within same session
        self._ema_cache: dict = {}  # user_id -> (ema, session_count)

    def compute(
        self,
        user_id: str,
        emotion: EmotionState,
        attention: AttentionState,
        decision: DecisionState,
        previous_ema: float = 0.0,
        previous_session_count: int = 0,
    ) -> FormationResult:
        """Compute formation metrics.

        Args:
            previous_ema: EMA loaded from DB at start of session (0.0 if first session).
            previous_session_count: number of sessions already stored in DB.
        """
        avoidance_score = 1.0 if decision.type == "avoidance" else 0.0
        avoidance_weighted = avoidance_score * decision.drivers.fear

        emotion_contribution = 0.4 * emotion.intensity
        attention_contribution = 0.3 * attention.fixation_score
        decision_contribution = 0.3 * avoidance_weighted

        formation_score = _clamp(
            emotion_contribution + attention_contribution + decision_contribution
        )

        # Load in-process cache (falls back to DB-seeded value)
        cached_ema, cached_count = self._ema_cache.get(
            user_id, (previous_ema, previous_session_count)
        )

        # Drift: distance from EMA, not from raw previous score
        drift_score = _clamp(abs(formation_score - cached_ema))
        stability_score = _clamp(1.0 - drift_score)

        # Update EMA
        if cached_count == 0:
            new_ema = formation_score  # seed on first session
        else:
            new_ema = _clamp(EMA_ALPHA * formation_score + (1.0 - EMA_ALPHA) * cached_ema)
        new_count = cached_count + 1

        # Update in-process cache
        self._ema_cache[user_id] = (new_ema, new_count)

        result = FormationResult(
            formation_score=round(formation_score, 4),
            drift_score=round(drift_score, 4),
            stability_score=round(stability_score, 4),
            emotion_contribution=round(emotion_contribution, 4),
            attention_contribution=round(attention_contribution, 4),
            decision_contribution=round(decision_contribution, 4),
            formation_score_ema=round(new_ema, 4),
            session_count=new_count,
        )
        logger.info(
            f"[formation] user={user_id[:8]} score={result.formation_score} "
            f"ema={result.formation_score_ema} drift={result.drift_score} "
            f"sessions={result.session_count}"
        )
        return result

    def to_dict(self, result: FormationResult) -> dict:
        return asdict(result)


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))
