"""
Domain Model — Motive

Canonical motive analysis representation.
Motives are driving forces behind decisions — not judgments of character.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


MOTIVE_TYPES = [
    "fear",       # avoiding threat / loss
    "pride",      # proving worth / avoiding shame
    "shame",      # hiding inadequacy
    "desire",     # obtaining pleasure / relief
    "love",       # genuine other-orientation
    "duty",       # obligation / responsibility
    "truth",      # alignment with principle
    "growth",     # genuine development intent
]


@dataclass
class MotiveProfile:
    """
    Motive score distribution for a decision.
    Scores are 0–1 probability weights, sum ≈ 1.0.
    These describe DRIVING TENDENCIES — not character judgments.
    """
    scores: Dict[str, float] = field(default_factory=dict)

    @property
    def dominant(self) -> Optional[str]:
        if not self.scores:
            return None
        return max(self.scores, key=lambda k: self.scores[k])

    @property
    def dominant_score(self) -> float:
        if not self.scores:
            return 0.0
        return self.scores.get(self.dominant or "", 0.0)

    def to_dict(self):
        return {
            "scores":        self.scores,
            "dominant":      self.dominant,
            "dominant_score":round(self.dominant_score, 3),
        }
