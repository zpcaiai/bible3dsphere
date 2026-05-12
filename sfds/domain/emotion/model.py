"""
Domain Model — Emotion

Canonical emotion representation for SFDS.
"""

from dataclasses import dataclass
from typing import Optional


EMOTION_CATEGORIES = [
    "fear", "anxiety", "peace", "joy", "shame",
    "guilt", "anger", "grief", "hope", "confusion",
    "loneliness", "gratitude", "pride", "love", "despair",
]


@dataclass
class EmotionSignal:
    """
    A single active emotion signal from the user's reported state.
    intensity: 0–10 scale.
    trigger: optional description of what triggered this emotion.
    """
    emotion_type: str
    intensity:    float   # 0–10
    trigger:      Optional[str] = None
    category:     str = "other"   # maps to pattern category

    def to_dict(self):
        return {
            "type":      self.emotion_type,
            "intensity": self.intensity,
            "trigger":   self.trigger,
            "category":  self.category,
        }
