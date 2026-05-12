"""
Formation Engine Service — Layer 5 of SFDS v3

Responsibility:
  - Compute the 8-dimension FormationStateVector
  - Track long-term character trajectory across sessions
  - Run 5-layer internal analysis (reinforcement, trajectory,
    drift, loop dominance, alignment trend)

See: backend/formation_engine.py for full v3.1 implementation.
This module is the service wrapper that integrates with the
new repo structure — it re-exports the core engine class.
"""

from typing import Optional

# Re-export the full implementation from backend (until migration completes)
from backend.formation_engine import FormationEngine, FormationInsight  # type: ignore

_instance: Optional[FormationEngine] = None


def get_formation_engine(db_pool=None) -> FormationEngine:
    global _instance
    if _instance is None:
        _instance = FormationEngine(db_pool=db_pool)
    return _instance


__all__ = ["FormationEngine", "FormationInsight", "get_formation_engine"]
