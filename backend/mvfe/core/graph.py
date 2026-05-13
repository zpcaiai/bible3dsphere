"""
GRAPH MODULE (Neo4j optional)
Rich causal relationship graph: Emotion, Desire, Belief, Behavior, Outcome, Principle.
HIDOS core formation loop:
  (Emotion)-[:CAUSES]->(Desire)
  (Desire)-[:DRIVES]->(Behavior)
  (Behavior)-[:LEADS_TO]->(Outcome)
  (Outcome)-[:REINFORCES]->(Belief)
  (Belief)-[:AMPLIFIES]->(Emotion)
"""
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class GraphModule:
    """
    Manages rich causal graph in Neo4j.
    Nodes: Emotion, Attention, Decision, Outcome, Desire, Belief, Principle
    """

    def __init__(self, driver=None):
        self._driver = driver
        self._enabled = driver is not None
        if self._enabled:
            logger.info("[graph] Neo4j graph module enabled (rich causal graph)")
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
                session.run(
                    """MERGE (e:Emotion {user_id: $user_id, type: $emotion_type})
                    SET e.intensity = $intensity, e.updated_at = datetime()""",
                    user_id=user_id, emotion_type=emotion.get("primary_emotion", "unknown"),
                    intensity=emotion.get("intensity", 0.5),
                )
                session.run(
                    """MERGE (a:Attention {user_id: $user_id, focus: $focus})
                    SET a.fixation_score = $fixation, a.updated_at = datetime()""",
                    user_id=user_id, focus=attention.get("focus", "unknown"),
                    fixation=attention.get("fixation_score", 0.5),
                )
                session.run(
                    """MERGE (d:Decision {user_id: $user_id, type: $dtype})
                    SET d.fear = $fear, d.ego = $ego, d.love = $love, d.updated_at = datetime()""",
                    user_id=user_id, dtype=decision.get("type", "avoidance"),
                    fear=decision.get("drivers", {}).get("fear", 0.5),
                    ego=decision.get("drivers", {}).get("ego", 0.3),
                    love=decision.get("drivers", {}).get("love", 0.2),
                )
                session.run(
                    """MATCH (e:Emotion {user_id: $user_id, type: $emotion_type})
                    MATCH (a:Attention {user_id: $user_id, focus: $focus})
                    MERGE (e)-[:DRIVES]->(a)""",
                    user_id=user_id, emotion_type=emotion.get("primary_emotion", "unknown"),
                    focus=attention.get("focus", "unknown"),
                )
                session.run(
                    """MATCH (a:Attention {user_id: $user_id, focus: $focus})
                    MATCH (d:Decision {user_id: $user_id, type: $dtype})
                    MERGE (a)-[:LEADS_TO]->(d)""",
                    user_id=user_id, focus=attention.get("focus", "unknown"),
                    dtype=decision.get("type", "avoidance"),
                )
            logger.info(f"[graph] updated causal graph for user={user_id[:8]}")
        except Exception as e:
            logger.warning(f"[graph] update failed: {e}")

    def update_rich(self, user_id: str, emotion: dict, attention: dict, decision: dict, context: dict = None):
        """Build full HIDOS formation loop with Desire, Belief, Behavior, Outcome nodes."""
        if not self._enabled:
            return
        try:
            with self._driver.session() as session:
                emotion_type = emotion.get("primary_emotion", "unknown")
                intensity = emotion.get("intensity", 0.5)
                focus = attention.get("focus", "unknown")
                desire_name = self._infer_desire(emotion, decision)
                belief_stmt = self._infer_belief(decision, emotion)
                outcome = "avoidance_pattern" if decision.get("type") == "avoidance" else "approach_pattern"
                behavior = focus.replace(" ", "_") + "_behavior"

                session.run(
                    """MERGE (e:Emotion {user_id: $uid, type: $etype})
                    SET e.intensity = $int, e.updated_at = datetime()""",
                    uid=user_id, etype=emotion_type, int=intensity,
                )
                session.run(
                    """MERGE (de:Desire {user_id: $uid, name: $dname})
                    SET de.strength = $int, de.updated_at = datetime()""",
                    uid=user_id, dname=desire_name, int=intensity,
                )
                session.run(
                    """MERGE (b:Belief {user_id: $uid, statement: $stmt})
                    SET b.strength = $str, b.updated_at = datetime()""",
                    uid=user_id, stmt=belief_stmt, str=decision.get("drivers", {}).get("fear", 0.5),
                )
                session.run(
                    """MERGE (o:Outcome {user_id: $uid, result: $out})
                    SET o.updated_at = datetime()""",
                    uid=user_id, out=outcome,
                )
                session.run(
                    """MERGE (be:Behavior {user_id: $uid, action: $act})
                    SET be.frequency = coalesce(be.frequency, 0) + 1, be.updated_at = datetime()""",
                    uid=user_id, act=behavior,
                )
                session.run(
                    """MATCH (e:Emotion {user_id: $uid, type: $etype})
                    MATCH (de:Desire {user_id: $uid, name: $dname})
                    MERGE (e)-[:CAUSES]->(de)""",
                    uid=user_id, etype=emotion_type, dname=desire_name,
                )
                session.run(
                    """MATCH (de:Desire {user_id: $uid, name: $dname})
                    MATCH (be:Behavior {user_id: $uid, action: $act})
                    MERGE (de)-[:DRIVES]->(be)""",
                    uid=user_id, dname=desire_name, act=behavior,
                )
                session.run(
                    """MATCH (be:Behavior {user_id: $uid, action: $act})
                    MATCH (o:Outcome {user_id: $uid, result: $out})
                    MERGE (be)-[:LEADS_TO]->(o)""",
                    uid=user_id, act=behavior, out=outcome,
                )
                session.run(
                    """MATCH (o:Outcome {user_id: $uid, result: $out})
                    MATCH (b:Belief {user_id: $uid, statement: $stmt})
                    MERGE (o)-[:REINFORCES]->(b)""",
                    uid=user_id, out=outcome, stmt=belief_stmt,
                )
                session.run(
                    """MATCH (b:Belief {user_id: $uid, statement: $stmt})
                    MATCH (e:Emotion {user_id: $uid, type: $etype})
                    MERGE (b)-[:AMPLIFIES]->(e)""",
                    uid=user_id, stmt=belief_stmt, etype=emotion_type,
                )
            logger.info(f"[graph] rich causal graph updated for user={user_id[:8]}")
        except Exception as e:
            logger.warning(f"[graph] rich update failed: {e}")

    def detect_loops(self, user_id: str) -> List[Dict]:
        """Detect formation loops in causal graph."""
        if not self._enabled:
            return []
        try:
            with self._driver.session() as session:
                result = session.run(
                    """MATCH path = (e:Emotion {user_id: $uid})-[:CAUSES]->(de:Desire)
                                 -[:DRIVES]->(be:Behavior)-[:LEADS_TO]->(o:Outcome)
                                 -[:REINFORCES]->(b:Belief)-[:AMPLIFIES]->(e2:Emotion {user_id: $uid})
                    WHERE e.type = e2.type
                    RETURN e.type AS loop_anchor, count(path) AS loop_strength,
                           collect(DISTINCT de.name) AS desires,
                           collect(DISTINCT b.statement) AS beliefs
                    ORDER BY loop_strength DESC""",
                    uid=user_id,
                )
                loops = []
                for record in result:
                    loops.append({
                        "loop_anchor": record["loop_anchor"],
                        "loop_strength": record["loop_strength"],
                        "desires": record["desires"],
                        "beliefs": record["beliefs"],
                    })
                return loops
        except Exception as e:
            logger.warning(f"[graph] loop detection failed: {e}")
            return []

    def get_formation_insight(self, user_id: str) -> Dict:
        """Return graph-based formation insight for writeback to Postgres."""
        loops = self.detect_loops(user_id)
        if not loops:
            return {"loop_detected": False, "loop_type": None, "loop_strength": 0.0}
        strongest = loops[0]
        return {
            "loop_detected": True,
            "loop_type": f"{strongest['loop_anchor']}-driven formation loop",
            "loop_strength": min(strongest["loop_strength"] * 0.1, 1.0),
            "dominant_desires": strongest["desires"][:3],
            "core_beliefs": strongest["beliefs"][:3],
        }

    @staticmethod
    def _infer_desire(emotion: dict, decision: dict) -> str:
        """Infer desire name from emotion + decision drivers."""
        primary = emotion.get("primary_emotion", "unknown")
        drivers = decision.get("drivers", {})
        if drivers.get("fear", 0) > 0.5:
            return "safety" if primary in ("anxiety", "fear") else "control"
        if drivers.get("love", 0) > 0.5:
            return "connection"
        if drivers.get("ego", 0) > 0.5:
            return "validation"
        return "relief"

    @staticmethod
    def _infer_belief(decision: dict, emotion: dict) -> str:
        """Infer belief statement from decision type + emotion."""
        dtype = decision.get("type", "avoidance")
        primary = emotion.get("primary_emotion", "unknown")
        if dtype == "avoidance" and primary in ("fear", "anxiety"):
            return "avoidance_prevents_harm"
        if dtype == "avoidance":
            return "withholding_protects"
        if primary in ("desire", "hope"):
            return "pursuit_brings_fulfillment"
        return "action_is_necessary"
