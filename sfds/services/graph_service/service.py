"""
Graph Service — Neo4j structural analysis layer.

Responsibilities:
  - Execute Cypher queries via Neo4j driver
  - Pattern detection
  - Loop extraction
  - Causal chain tracing
  - Intervention point identification

Does NOT contain LLM logic (that lives in core-engine / ai/).
Does NOT contain TimescaleDB logic.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ai.reasoning.graph_query_engine import (
    GraphQueryEngine, GQEMode, UserStateInput,
)

logger = logging.getLogger(__name__)

_instance: Optional["GraphService"] = None


def get_graph_service() -> "GraphService":
    global _instance
    if _instance is None:
        _instance = GraphService()
    return _instance


class GraphService:
    """
    Service boundary: Neo4j graph layer.

    All Neo4j query execution lives here.
    Returns structured dicts — no raw graph objects outside this service.
    """

    def __init__(self, neo4j_driver=None):
        self._driver = neo4j_driver
        self._gqe    = GraphQueryEngine(driver=neo4j_driver)

    # ── Core APIs ─────────────────────────────────────────────

    async def get_patterns(self) -> Dict[str, Any]:
        """Return the known human behavioral loop pattern library."""
        from graph.patterns.library import PATTERN_LIBRARY
        return {"patterns": PATTERN_LIBRARY, "count": len(PATTERN_LIBRARY)}

    async def detect_loop(self, user_id: str) -> Dict[str, Any]:
        """
        Detect active behavioral loops for a user.
        Queries REINFORCES edges in the user's subgraph.
        """
        from graph.queries.loop_queries import detect_active_loops
        try:
            loops = detect_active_loops(self._driver, user_id)
            return {
                "user_id":  user_id,
                "loops":    loops,
                "detected": len(loops) > 0,
                "note":     "Loop detection is structural, not deterministic.",
            }
        except Exception as exc:
            logger.warning("[graph-service] detect_loop failed: %s", exc)
            return {"user_id": user_id, "loops": [], "detected": False}

    async def trace_root_cause(self, behavior_type: str) -> Dict[str, Any]:
        """
        Trace the most probable upstream causes of a behavior type.
        Follows CAUSES edges upstream to EmotionNode / MotiveNode roots.
        """
        from graph.queries.causal_queries import trace_upstream
        try:
            chain = trace_upstream(self._driver, behavior_type)
            return {"behavior": behavior_type, "upstream_chain": chain}
        except Exception as exc:
            logger.warning("[graph-service] trace_root_cause failed: %s", exc)
            return {"behavior": behavior_type, "upstream_chain": []}

    async def find_intervention_points(self, user_id: str) -> Dict[str, Any]:
        """
        Identify highest-leverage intervention nodes for a user.
        Motive-level nodes > Behavior-level > Emotion-level.
        """
        from graph.queries.intervention_queries import find_interventions
        try:
            points = find_interventions(self._driver, user_id)
            return {"user_id": user_id, "intervention_points": points}
        except Exception as exc:
            logger.warning("[graph-service] find_intervention_points failed: %s", exc)
            return {"user_id": user_id, "intervention_points": []}

    async def analyze(
        self,
        user_id:           str,
        dominant_motive:   str,
        emotions:          List[Dict[str, Any]],
        decision_category: str,
        past_behaviors:    List[str],
    ) -> Dict[str, Any]:
        """
        Full structural analysis — called by CoreEngine.
        Returns causal chains, loops, patterns, and intervention points.
        """
        loops      = (await self.detect_loop(user_id)).get("loops", [])
        patterns   = await self.get_patterns()
        interventions = (await self.find_intervention_points(user_id)).get("intervention_points", [])
        return {
            "loops":               loops,
            "pattern_labels":      [p["label"] for p in patterns.get("patterns", [])[:5]],
            "intervention_points": interventions,
            "structural_summary":  f"Active motive: {dominant_motive}. {len(loops)} loop(s) detected.",
        }

    async def reason(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Entry point for 6-layer Graph Reasoning Fusion.
        Delegates to ai/reasoning layer.
        """
        from ai.reasoning.graph_reasoning import run_graph_reasoning
        return await run_graph_reasoning(body)

    async def gqe_reason(
        self,
        user_id:       str,
        emotion:       str,
        motive:        str,
        behavior:      str,
        category:      str = "fear",
        mode:          str = "loop_simulation",
        question:      str = "",
    ) -> Dict[str, Any]:
        """
        GQE v3.3 — full 7-step graph reasoning pipeline.

        This is the primary entry point for MODE-based graph reasoning:
          - structural_traversal  : understand causal structure
          - loop_simulation       : forward-propagate if unchanged
          - breakpoint_detection  : find highest-leverage intervention
          - principle_activation  : match principle to loop structure

        Returns GQEOutput.to_dict() — fully populated 7-step result.
        Falls back gracefully to pattern library when Neo4j is unavailable.
        """
        _mode_map = {
            "structural_traversal": GQEMode.STRUCTURAL_TRAVERSAL,
            "loop_simulation":      GQEMode.LOOP_SIMULATION,
            "breakpoint_detection": GQEMode.BREAKPOINT_DETECTION,
            "principle_activation": GQEMode.PRINCIPLE_ACTIVATION,
        }
        gqe_mode = _mode_map.get(mode, GQEMode.LOOP_SIMULATION)
        state    = UserStateInput(
            emotion_node  = emotion,
            motive_node   = motive,
            behavior_node = behavior,
            user_id       = user_id,
            category      = category,
        )
        try:
            result = await self._gqe.reason(state, mode=gqe_mode, question=question)
            return result.to_dict()
        except Exception as exc:
            logger.warning("[graph-service] gqe_reason failed: %s", exc)
            return {
                "mode":    mode,
                "error":   "GQE reasoning unavailable.",
                "disclaimer": (
                    "Structural analysis temporarily unavailable. "
                    "Pattern library fallback also failed."
                ),
            }
