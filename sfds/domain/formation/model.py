"""
Domain Model — Formation

The canonical domain representation of character formation state.
Used across formation-engine, api, and shared-types.

This is the domain layer — no DB logic, no LLM logic here.
Pure data model + business invariants.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


# ── Formation State Vector ────────────────────────────────────
# The 8-dimension behavioral tendency representation.
# NOT moral scores. NOT identity. Trajectory signals.

@dataclass
class FormationVector:
    """
    8-dimension FormationStateVector.

    Values: 0.05–0.95. Never 0 (no absolute absence) or 1 (no absolute presence).
    fear_tendency + pride_tendency: higher = more active loop (not "worse")
    All others: higher = healthier tendency direction.
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
        return {k: round(v, 3) for k, v in self.__dict__.items()}

    def clamp(self) -> "FormationVector":
        """Enforce 0.05–0.95 bounds on all dimensions."""
        for k, v in self.__dict__.items():
            setattr(self, k, max(0.05, min(0.95, v)))
        return self


# ── Formation Arc ─────────────────────────────────────────────

class FormationArc:
    BREAKING_THROUGH = "breaking_through"
    DEEPENING_LOOPS  = "deepening_loops"
    STABILIZING      = "stabilizing"
    UNKNOWN          = "unknown"


# ── Trajectory Direction ──────────────────────────────────────

class TrajectoryDir:
    STABILIZING           = "stabilizing"
    FRAGMENTING           = "fragmenting"
    IMPROVING_CLARITY     = "improving_clarity"
    INCREASING_VOLATILITY = "increasing_volatility"
    CYCLICAL              = "cyclical"
    UNKNOWN               = "unknown"


# ── Domain invariant enforcement ──────────────────────────────

DESIGN_INVARIANTS = {
    "no_identity_labels":   True,
    "no_moral_scoring":     True,
    "no_deterministic_pred":True,
    "confidence_cap":       0.90,
    "score_min":            0.05,
    "score_max":            0.95,
    "probabilistic_language":True,
}
