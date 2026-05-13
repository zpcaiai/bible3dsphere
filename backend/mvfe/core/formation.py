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


@dataclass
class FormationResult:
    formation_score: float  # 0.0-1.0
    drift_score: float  # 0.0-1.0 temporal change proxy
    stability_score: float  # 0.0-1.0
    emotion_contribution: float
    attention_contribution: float
    decision_contribution: float


class FormationEngine:
    """
    Computes formation dynamics from extracted state layers.

    formation_score = 0.4 * emotion_intensity + 0.3 * fixation_score + 0.3 * avoidance_score
    drift_score = temporal delta between current and previous formation_score
    stability_score = 1.0 - drift_score
    """

    def __init__(self):
        self._previous_scores: dict = {}  # user_id -> last formation_score

    def compute(
        self,
        user_id: str,
        emotion: EmotionState,
        attention: AttentionState,
        decision: DecisionState,
    ) -> FormationResult:
        """Compute formation metrics."""
        avoidance_score = 1.0 if decision.type == "avoidance" else 0.0
        # Weight by driver confidence
        avoidance_weighted = avoidance_score * decision.drivers.fear

        emotion_contribution = 0.4 * emotion.intensity
        attention_contribution = 0.3 * attention.fixation_score
        decision_contribution = 0.3 * avoidance_weighted

        formation_score = _clamp(
            emotion_contribution + attention_contribution + decision_contribution
        )

        # Drift: compare to previous
        prev = self._previous_scores.get(user_id, formation_score)
        drift_score = _clamp(abs(formation_score - prev))
        stability_score = _clamp(1.0 - drift_score)

        # Update history
        self._previous_scores[user_id] = formation_score

        result = FormationResult(
            formation_score=round(formation_score, 4),
            drift_score=round(drift_score, 4),
            stability_score=round(stability_score, 4),
            emotion_contribution=round(emotion_contribution, 4),
            attention_contribution=round(attention_contribution, 4),
            decision_contribution=round(decision_contribution, 4),
        )
        logger.info(
            f"[formation] user={user_id[:8]} score={result.formation_score} "
            f"drift={result.drift_score} stability={result.stability_score}"
        )
        return result

    def to_dict(self, result: FormationResult) -> dict:
        return asdict(result)


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))
