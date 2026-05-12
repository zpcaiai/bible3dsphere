"""
AI Reasoning — Graph Reasoning Fusion

Entry point for the 6-layer Graph Reasoning Fusion Engine.
Delegates to backend/graph_reasoning_engine.py (core implementation).
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


async def run_graph_reasoning(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run 6-layer graph reasoning fusion.
    Delegates to the core GraphReasoningFusion implementation.
    """
    try:
        from backend.graph_reasoning_engine import GraphReasoningFusion  # type: ignore
        from backend.graph_layer import GraphEngine, Neo4jConnection       # type: ignore

        neo4j = Neo4jConnection()
        graph = GraphEngine(neo4j)
        fusion = GraphReasoningFusion(graph_engine=graph)

        user_id          = body.get("user_id", "")
        dominant_emotion = body.get("dominant_emotion", "")
        dominant_motive  = body.get("dominant_motive", "")
        emotions         = body.get("emotions", [])
        past_behaviors   = body.get("past_behaviors", [])
        category         = body.get("category", "other")
        vector_principles= body.get("vector_principles", [])
        temporal_context = body.get("temporal_context", {})

        graph_insight = graph.analyze(
            user_id             = user_id,
            dominant_motive     = dominant_motive,
            emotions            = emotions,
            decision_category   = category,
            past_behavior_types = past_behaviors,
        )

        formation_reasoning = fusion.reason(
            user_id          = user_id,
            dominant_emotion = dominant_emotion,
            dominant_motive  = dominant_motive,
            graph_insight    = graph_insight,
            vector_principles= vector_principles,
            temporal_context = temporal_context,
        )

        return {
            "user_id":  user_id,
            "schema":   "v2.2",
            "reasoning":formation_reasoning.to_dict(),
            "note": (
                "Graph reasoning output describes structural patterns and "
                "possible intervention points. Not a directive or authority statement."
            ),
        }

    except Exception as exc:
        logger.warning("[graph-reasoning] failed: %s", exc)
        return {
            "user_id":  body.get("user_id", ""),
            "schema":   "v2.2",
            "reasoning":{},
            "error":    "Graph reasoning unavailable.",
        }
