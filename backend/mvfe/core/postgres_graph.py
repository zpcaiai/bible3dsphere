"""
POSTGRES GRAPH MODULE
Replaces Neo4j with PostgreSQL Recursive CTEs for causal graph storage and loop detection.

HIDOS formation loop (5-hop cycle):
  (Emotion) -[CAUSES]->    (Desire)
  (Desire)  -[DRIVES]->    (Behavior)
  (Behavior)-[LEADS_TO]->  (Outcome)
  (Outcome) -[REINFORCES]->(Belief)
  (Belief)  -[AMPLIFIES]-> (Emotion)   ← closes the loop
"""
import logging
import uuid
from typing import Dict, List, Optional

from ..db.graph_schema import LOOP_DETECTION_CTE, MVFE_GRAPH_SCHEMA_SQL

logger = logging.getLogger(__name__)


class PostgresGraphModule:
    """
    Causal graph stored in PostgreSQL (mvfe_graph_nodes + mvfe_graph_edges).
    Loop detection uses a Recursive CTE — no Neo4j required.
    """

    def __init__(self, db_pool=None):
        self._pool = db_pool
        self._enabled = db_pool is not None
        if self._enabled:
            self._ensure_tables()
            logger.info("[pg-graph] PostgreSQL graph module enabled")
        else:
            logger.info("[pg-graph] No DB pool — running in no-op mode")

    # ── Public API (matches original GraphModule interface) ──────────────

    @property
    def enabled(self) -> bool:
        return self._enabled

    def update(self, user_id: str, emotion: dict, attention: dict, decision: dict):
        """Upsert basic causal nodes: Emotion → Attention → Decision."""
        if not self._enabled:
            return
        try:
            emotion_id = self._upsert_node(
                user_id, "Emotion",
                emotion.get("primary_emotion", "unknown"),
                {"intensity": emotion.get("intensity", 0.5)},
                strength=emotion.get("intensity", 0.5),
            )
            attention_id = self._upsert_node(
                user_id, "Attention",
                attention.get("focus", "unknown"),
                {"fixation_score": attention.get("fixation_score", 0.5)},
                strength=attention.get("fixation_score", 0.5),
            )
            decision_id = self._upsert_node(
                user_id, "Decision",
                decision.get("type", "avoidance"),
                {"drivers": decision.get("drivers", {})},
                strength=decision.get("drivers", {}).get("fear", 0.5),
            )
            self._upsert_edge(user_id, emotion_id, attention_id, "DRIVES")
            self._upsert_edge(user_id, attention_id, decision_id, "LEADS_TO")
            logger.debug(f"[pg-graph] basic update done user={user_id[:8]}")
        except Exception as e:
            logger.warning(f"[pg-graph] update failed: {e}")

    def update_rich(self, user_id: str, emotion: dict, attention: dict,
                    decision: dict, context: dict = None):
        """
        Build full HIDOS formation loop in Postgres:
          Emotion → Desire → Behavior → Outcome → Belief → Emotion
        """
        if not self._enabled:
            return
        try:
            emotion_type   = emotion.get("primary_emotion", "unknown")
            intensity      = emotion.get("intensity", 0.5)
            desire_name    = self._infer_desire(emotion, decision)
            belief_stmt    = self._infer_belief(decision, emotion)
            dtype          = decision.get("type", "avoidance")
            outcome_name   = "逃避模式" if dtype == "avoidance" else "进取模式"
            focus          = attention.get("focus", "未知")
            behavior_name  = f"{focus}相关的行为"

            # Upsert all 5 node types
            emotion_id   = self._upsert_node(user_id, "Emotion",   emotion_type,  {"intensity": intensity},       strength=intensity)
            desire_id    = self._upsert_node(user_id, "Desire",    desire_name,   {"strength": intensity},        strength=intensity)
            behavior_id  = self._upsert_node(user_id, "Behavior",  behavior_name, {"frequency": 1},               strength=intensity * 0.8)
            outcome_id   = self._upsert_node(user_id, "Outcome",   outcome_name,  {"type": dtype},                strength=intensity * 0.7)
            belief_id    = self._upsert_node(user_id, "Belief",    belief_stmt,   {"confidence": intensity},      strength=intensity * 0.9)

            # Upsert 5 edges — the HIDOS cycle
            self._upsert_edge(user_id, emotion_id,  desire_id,   "CAUSES")
            self._upsert_edge(user_id, desire_id,   behavior_id, "DRIVES")
            self._upsert_edge(user_id, behavior_id, outcome_id,  "LEADS_TO")
            self._upsert_edge(user_id, outcome_id,  belief_id,   "REINFORCES")
            self._upsert_edge(user_id, belief_id,   emotion_id,  "AMPLIFIES")

            logger.info(f"[pg-graph] rich update done user={user_id[:8]} emotion={emotion_type}")
        except Exception as e:
            logger.warning(f"[pg-graph] rich update failed: {e}")

    def detect_loops(self, user_id: str) -> List[Dict]:
        """
        Detect HIDOS formation loops via Recursive CTE.
        Returns list of dicts with loop_anchor, loop_depth, path, loop_count.
        """
        if not self._enabled:
            return []
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(LOOP_DETECTION_CTE, {"user_id": user_id})
                rows = cur.fetchall()
                loops = []
                seen_anchors = set()
                for row in rows:
                    anchor = row[0]
                    if anchor in seen_anchors:
                        continue
                    seen_anchors.add(anchor)
                    loops.append({
                        "loop_anchor":  anchor,
                        "loop_strength": min(float(row[1]) * float(row[4] or 1.0), 1.0),
                        "loop_depth":   int(row[2]),
                        "path":         list(row[3]),
                        "loop_count":   int(row[5]),
                        # Extract desires and beliefs from path labels
                        "desires":      [p.split(":")[1] for p in (row[3] or []) if p.startswith("Desire:")],
                        "beliefs":      [p.split(":")[1] for p in (row[3] or []) if p.startswith("Belief:")],
                    })
                return loops
        except Exception as e:
            logger.warning(f"[pg-graph] loop detection failed: {e}")
            return []
        finally:
            self._pool.putconn(conn)

    def get_formation_insight(self, user_id: str,
                              emotion: dict = None,
                              decision: dict = None) -> Dict:
        """
        Return formation insight dict.
        1st priority: real loops from Recursive CTE (if DB graph has ≥1 entry)
        2nd priority: local rule-based detection (no DB needed)
        """
        if self._enabled:
            loops = self.detect_loops(user_id)
            if loops:
                strongest = loops[0]
                return {
                    "loop_detected":    True,
                    "loop_type":        f"由 {strongest['loop_anchor']} 驱动的形成回路",
                    "loop_strength":    round(min(strongest["loop_strength"], 1.0), 2),
                    "dominant_desires": strongest["desires"][:3],
                    "core_beliefs":     strongest["beliefs"][:3],
                    "loop_depth":       strongest["loop_depth"],
                    "source":           "postgres_cte",
                }

        # ── Local rule-based fallback (always runs when DB loop not found yet) ──
        return self._local_rule_insight(emotion or {}, decision or {})

    def get_neighbourhood(self, user_id: str, node_id: str, max_depth: int = 3) -> List[Dict]:
        """3-hop neighbourhood query around a given node (for future use)."""
        if not self._enabled:
            return []
        from ..db.graph_schema import NEIGHBOURHOOD_CTE
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(NEIGHBOURHOOD_CTE, {
                    "user_id":   user_id,
                    "start_id":  node_id,
                    "max_depth": max_depth,
                })
                return [
                    {"source": r[0], "target": r[1], "depth": r[2],
                     "edge_type": r[3], "node_name": r[4], "node_type": r[5]}
                    for r in cur.fetchall()
                ]
        except Exception as e:
            logger.warning(f"[pg-graph] neighbourhood query failed: {e}")
            return []
        finally:
            self._pool.putconn(conn)

    # ── Internal helpers ─────────────────────────────────────────────────

    def _ensure_tables(self):
        """Create graph tables if they don't exist."""
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(MVFE_GRAPH_SCHEMA_SQL)
                conn.commit()
            logger.info("[pg-graph] graph tables ensured")
        except Exception as e:
            conn.rollback()
            logger.error(f"[pg-graph] table init failed: {e}")
        finally:
            self._pool.putconn(conn)

    def _upsert_node(self, user_id: str, node_type: str, node_name: str,
                     props: dict, strength: float = 1.0) -> str:
        """
        UPSERT a node; return its UUID.
        On conflict (same user/type/name) → update strength + properties.
        """
        conn = self._pool.getconn()
        try:
            import json
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO mvfe_graph_nodes (user_id, node_type, node_name, properties, strength)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, node_type, node_name) DO UPDATE
                       SET properties = mvfe_graph_nodes.properties || EXCLUDED.properties,
                           strength   = GREATEST(mvfe_graph_nodes.strength, EXCLUDED.strength),
                           updated_at = NOW()
                    RETURNING id
                    """,
                    (user_id, node_type, node_name, json.dumps(props), strength),
                )
                node_id = str(cur.fetchone()[0])
                conn.commit()
                return node_id
        finally:
            self._pool.putconn(conn)

    def _upsert_edge(self, user_id: str, source_id: str, target_id: str,
                     edge_type: str, weight: float = 1.0):
        """
        UPSERT an edge; increment traversal_count on conflict.
        """
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO mvfe_graph_edges
                        (user_id, source_id, target_id, edge_type, weight)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, source_id, target_id, edge_type) DO UPDATE
                       SET traversal_count = mvfe_graph_edges.traversal_count + 1,
                           weight          = GREATEST(mvfe_graph_edges.weight, EXCLUDED.weight),
                           updated_at      = NOW()
                    """,
                    (user_id, source_id, target_id, edge_type, weight),
                )
                conn.commit()
        finally:
            self._pool.putconn(conn)

    @staticmethod
    def _local_rule_insight(emotion: dict, decision: dict) -> Dict:
        """Rule-based loop inference when DB graph is empty or unavailable."""
        if not emotion or not decision:
            return {"loop_detected": False, "loop_type": None, "loop_strength": 0.0, "source": "none"}

        primary  = emotion.get("primary_emotion", "unknown")
        intensity = emotion.get("intensity", 0.0)
        dtype    = decision.get("type", "approach")
        drivers  = decision.get("drivers", {})
        fear     = drivers.get("fear", 0.0)
        ego      = drivers.get("ego", 0.0)

        logger.info(
            f"[pg-graph-rule] primary={primary} intensity={intensity:.2f} "
            f"dtype={dtype} fear={fear:.2f} ego={ego:.2f}"
        )
        print(
            f"[pg-graph-rule] primary={primary} intensity={intensity:.2f} "
            f"dtype={dtype} fear={fear:.2f} ego={ego:.2f}",
            flush=True,
        )

        if intensity >= 0.6 and dtype == "avoidance" and fear >= 0.5:
            return {
                "loop_detected": True,
                "loop_type": "fear_avoidance_loop",
                "loop_strength": round(min(intensity * fear, 1.0), 2),
                "dominant_desires": ["safety", "control"],
                "core_beliefs": ["avoidance_prevents_harm"],
                "source": "rule",
            }
        if intensity >= 0.6 and ego >= 0.5:
            return {
                "loop_detected": True,
                "loop_type": "pride_validation_loop",
                "loop_strength": round(min(intensity * ego, 1.0), 2),
                "dominant_desires": ["validation", "recognition"],
                "core_beliefs": ["self_worth_requires_achievement"],
                "source": "rule",
            }
        if primary in ("shame", "guilt", "羞耻", "内疚") and intensity >= 0.5 and dtype == "avoidance":
            return {
                "loop_detected": True,
                "loop_type": "羞耻-逃避回路",
                "loop_strength": round(intensity * 0.8, 2),
                "dominant_desires": ["隐藏", "寻求认可"],
                "core_beliefs": ["我做得不够好"],
                "source": "rule",
            }
        if primary in ("despair", "loneliness", "绝望", "孤独") and intensity >= 0.6 and dtype == "avoidance":
            return {
                "loop_detected": True,
                "loop_type": "绝望-孤立回路",
                "loop_strength": round(intensity * 0.75, 2),
                "dominant_desires": ["麻木", "寻求解脱"],
                "core_beliefs": ["连接是不可能的"],
                "source": "rule",
            }
        print(
            f"[pg-graph-rule] no loop: intensity={intensity:.2f} "
            f"fear={fear:.2f} dtype={dtype}",
            flush=True,
        )
        return {"loop_detected": False, "loop_type": None, "loop_strength": 0.0, "source": "rule"}

    @staticmethod
    def _infer_desire(emotion: dict, decision: dict) -> str:
        primary = emotion.get("primary_emotion", "未知")
        drivers = decision.get("drivers", {})
        if drivers.get("fear", 0) > 0.5:
            return "安全感" if primary in ("anxiety", "fear", "焦虑", "恐惧") else "控制欲"
        if drivers.get("love", 0) > 0.5:
            return "连接感"
        if drivers.get("ego", 0) > 0.5:
            return "认同感"
        return "缓解感"

    @staticmethod
    def _infer_belief(decision: dict, emotion: dict) -> str:
        dtype   = decision.get("type", "avoidance")
        primary = emotion.get("primary_emotion", "未知")
        if dtype == "avoidance" and primary in ("fear", "anxiety", "恐惧", "焦虑"):
            return "逃避可以防止伤害"
        if dtype == "avoidance":
            return "情感保留可以起到保护作用"
        if primary in ("desire", "hope", "渴望", "希望"):
            return "追求可以带来满足"
        return "采取行动是必要的"
