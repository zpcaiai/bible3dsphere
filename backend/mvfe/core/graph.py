"""
GRAPH MODULE (Neo4j optional)
Creates and maintains causal relationship graph.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GraphModule:
    """
    Manages causal graph in Neo4j.
    Nodes: Emotion, Attention, Decision, Outcome
    Relationships:
      (Emotion)-[:DRIVES]->(Attention)
      (Attention)-[:LEADS_TO]->(Decision)
      (Decision)-[:RESULTS_IN]->(Outcome)
      (Outcome)-[:REINFORCES]->(Emotion)
    """

    def __init__(self, driver=None):
        """
        Args:
            driver: neo4j.Driver instance or None (disabled mode)
        """
        self._driver = driver
        self._enabled = driver is not None
        if self._enabled:
            logger.info("[graph] Neo4j graph module enabled")
        else:
            logger.info("[graph] Neo4j disabled, running in no-op mode")

    @property
    def enabled(self) -> bool:
        return self._enabled

    def update(self, user_id: str, emotion: dict, attention: dict, decision: dict):
        """Update causal graph with new state data."""
        if not self._enabled:
            return

        try:
            with self._driver.session() as session:
                # Merge Emotion node
                session.run(
                    """
                    MERGE (e:Emotion {user_id: $user_id, type: $emotion_type})
                    SET e.intensity = $intensity, e.updated_at = datetime()
                    """,
                    user_id=user_id,
                    emotion_type=emotion.get("primary_emotion", "unknown"),
                    intensity=emotion.get("intensity", 0.5),
                )

                # Merge Attention node
                session.run(
                    """
                    MERGE (a:Attention {user_id: $user_id, focus: $focus})
                    SET a.fixation_score = $fixation, a.updated_at = datetime()
                    """,
                    user_id=user_id,
                    focus=attention.get("focus", "unknown"),
                    fixation=attention.get("fixation_score", 0.5),
                )

                # Merge Decision node
                session.run(
                    """
                    MERGE (d:Decision {user_id: $user_id, type: $dtype})
                    SET d.fear = $fear, d.ego = $ego, d.love = $love, d.updated_at = datetime()
                    """,
                    user_id=user_id,
                    dtype=decision.get("type", "avoidance"),
                    fear=decision.get("drivers", {}).get("fear", 0.5),
                    ego=decision.get("drivers", {}).get("ego", 0.3),
                    love=decision.get("drivers", {}).get("love", 0.2),
                )

                # Create relationships (DRIVES, LEADS_TO)
                session.run(
                    """
                    MATCH (e:Emotion {user_id: $user_id, type: $emotion_type})
                    MATCH (a:Attention {user_id: $user_id, focus: $focus})
                    MERGE (e)-[:DRIVES]->(a)
                    """,
                    user_id=user_id,
                    emotion_type=emotion.get("primary_emotion", "unknown"),
                    focus=attention.get("focus", "unknown"),
                )

                session.run(
                    """
                    MATCH (a:Attention {user_id: $user_id, focus: $focus})
                    MATCH (d:Decision {user_id: $user_id, type: $dtype})
                    MERGE (a)-[:LEADS_TO]->(d)
                    """,
                    user_id=user_id,
                    focus=attention.get("focus", "unknown"),
                    dtype=decision.get("type", "avoidance"),
                )

            logger.info(f"[graph] updated causal graph for user={user_id[:8]}")
        except Exception as e:
            logger.warning(f"[graph] update failed: {e}")
