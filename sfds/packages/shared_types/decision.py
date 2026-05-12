"""
Shared DTOs for the Decision domain.
Used across api, core-engine, and all services.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DecisionRequest:
    """Input DTO for a decision analysis request."""
    user_id:             str
    decision_id:         str   = field(default_factory=lambda: str(uuid.uuid4()))
    title:               str   = ""
    description:         str   = ""
    category:            str   = "other"
    urgency:             int   = 3       # 1–5
    importance:          int   = 3       # 1–5

    # Emotional state (0–10)
    anxiety_level:       int   = 5
    peace_level:         int   = 5
    clarity_level:       int   = 5
    spiritual_dryness:   int   = 5
    emotional_stability: int   = 5
    stress_level:        int   = 5

    # Active emotions: [{"type": "fear", "intensity": 7, "trigger": "..."}]
    emotions:            List[Dict[str, Any]] = field(default_factory=list)

    # Motive scores (0–1): {"fear": 0.7, "pride": 0.2, ...}
    motive_scores:       Optional[Dict[str, float]] = None

    # Dominant motive (derived or supplied)
    dominant_motive:     Optional[str] = None

    # Past behavior labels for cycle detection
    past_behavior_types: List[str] = field(default_factory=list)

    # Optional user reflection text — activates reflection damping
    reflection_notes:    str = ""


@dataclass
class AnalysisResponse:
    """Full pipeline output DTO."""
    user_id:     str
    decision_id: str
    schema:      str = "v3.1"
    semantic:    Dict[str, Any] = field(default_factory=dict)
    structural:  Dict[str, Any] = field(default_factory=dict)
    temporal:    Dict[str, Any] = field(default_factory=dict)
    reasoning:   Dict[str, Any] = field(default_factory=dict)
    formation:   Dict[str, Any] = field(default_factory=dict)
    disclaimer:  str = (
        "This analysis describes patterns and tendencies only. "
        "It is offered as a reflective mirror, not an authority. "
        "You remain the agent of your own formation."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id":     self.user_id,
            "decision_id": self.decision_id,
            "schema":      self.schema,
            "semantic":    self.semantic,
            "structural":  self.structural,
            "temporal":    self.temporal,
            "reasoning":   self.reasoning,
            "formation":   self.formation,
            "disclaimer":  self.disclaimer,
        }
