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
import hashlib
import json
import logging
import math
import uuid
from typing import Any, Dict, List, Optional

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
                    decision: dict, context: dict = None,
                    event_id: Optional[str] = None) -> bool:
        """
        Persist the observed part of a HIDOS formation chain in PostgreSQL.

        Outcome and belief remain absent until the user's later review supplies
        them. This keeps aggregate graph data and event history durable without
        turning model inference into a completed formation loop.
        """
        if not self._enabled:
            return False
        try:
            emotion_type   = emotion.get("primary_emotion", "unknown")
            desire_name    = self._infer_desire(emotion, decision)
            dtype          = decision.get("type", "avoidance")
            focus          = attention.get("focus", "未知")
            behavior_name  = f"{focus}相关的行为"
            persisted = self.persist_formation_chain(
                str(user_id),
                event_id or str(uuid.uuid4()),
                emotion_name=emotion_type,
                desire_name=desire_name,
                behavior_name=behavior_name,
                decision_category=dtype,
            )
            if persisted:
                logger.info(
                    "[pg-graph] observed formation chain persisted user=%s emotion=%s",
                    str(user_id)[:8], emotion_type,
                )
            return persisted
        except Exception as e:
            logger.warning(f"[pg-graph] rich update failed: {e}")
            return False

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

    def resolve_focus_node(self, user_id: str, focus_node_id: Optional[str] = None) -> Optional[str]:
        """Resolve a user-owned focus node, or select the strongest recent node."""
        if not self._enabled:
            return None
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                if focus_node_id:
                    cur.execute(
                        "SELECT id FROM mvfe_graph_nodes WHERE id = %s::uuid AND user_id = %s",
                        (focus_node_id, user_id),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id FROM mvfe_graph_nodes
                        WHERE user_id = %s
                        ORDER BY updated_at DESC, strength DESC, id
                        LIMIT 1
                        """,
                        (user_id,),
                    )
                row = cur.fetchone()
                return str(row[0]) if row else None
        except Exception as exc:
            logger.warning("[pg-graph] focus resolution failed: %s", exc)
            return None
        finally:
            self._pool.putconn(conn)

    def get_subgraph(self, user_id: str, focus_node_id: Optional[str] = None,
                     depth: int = 2, max_nodes: int = 200) -> Dict:
        """Return a subgraph centered on focus_node_id with edges."""
        if not self._enabled:
            return {"nodes": [], "edges": [], "stats": {}}
        focus_node_id = self.resolve_focus_node(user_id, focus_node_id)
        if not focus_node_id:
            return {
                "nodes": [], "edges": [],
                "stats": {"node_count": 0, "edge_count": 0},
                "focus_node": None,
            }
        from ..db.graph_schema import SUBGRAPH_CTE
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                # Get nodes via subgraph CTE
                cur.execute(SUBGRAPH_CTE, {
                    "user_id": user_id,
                    "focus_id": focus_node_id,
                    "max_depth": depth,
                    "max_nodes": max_nodes,
                })
                nodes = []
                node_ids = set()
                missing_positions = []
                for index, r in enumerate(cur.fetchall()):
                    nid = str(r[0])
                    node_ids.add(nid)
                    position = {
                        "x": float(r[5]) if r[5] is not None else None,
                        "y": float(r[6]) if r[6] is not None else None,
                        "z": float(r[7]) if r[7] is not None else None,
                    }
                    if any(value is None for value in position.values()):
                        position = self._stable_position(nid, int(r[8]), index)
                        missing_positions.append({"node_id": nid, **position})
                    nodes.append({
                        "id": nid, "node_type": r[1], "node_name": r[2],
                        "properties": r[3] if isinstance(r[3], dict) else {},
                        "strength": float(r[4]) if r[4] else 1.0,
                        "position": position,
                        "depth": int(r[8]),
                    })

                # Get edges between the returned nodes
                if node_ids:
                    placeholders = ",".join(["%s"] * len(node_ids))
                    cur.execute(
                        f"""
                        SELECT id, source_id, target_id, edge_type, weight, traversal_count
                        FROM mvfe_graph_edges
                        WHERE user_id = %s
                          AND source_id::text IN ({placeholders})
                          AND target_id::text IN ({placeholders})
                        """,
                        [user_id] + list(node_ids) + list(node_ids),
                    )
                    edges = [
                        {"id": str(r[0]), "source": str(r[1]), "target": str(r[2]),
                         "edge_type": r[3], "weight": float(r[4]), "traversal_count": int(r[5])}
                        for r in cur.fetchall()
                    ]
                else:
                    edges = []

                # Persist deterministic coordinates once. A write failure does not
                # discard the usable subgraph response; the same coordinates will be
                # regenerated deterministically on the next request.
                if missing_positions:
                    try:
                        for pos in missing_positions:
                            cur.execute(
                                """
                                UPDATE mvfe_graph_nodes
                                SET position_x=%s, position_y=%s, position_z=%s
                                WHERE id=%s::uuid AND user_id=%s
                                  AND (position_x IS NULL OR position_y IS NULL OR position_z IS NULL)
                                """,
                                (pos["x"], pos["y"], pos["z"], pos["node_id"], user_id),
                            )
                        conn.commit()
                    except Exception as exc:
                        conn.rollback()
                        logger.warning("[pg-graph] position precompute persistence failed: %s", exc)

                return {
                    "nodes": nodes,
                    "edges": edges,
                    "focus_node": focus_node_id,
                    "depth": depth,
                    "stats": {
                        "node_count": len(nodes),
                        "edge_count": len(edges),
                        "positions_precomputed": len(missing_positions),
                        "truncated": len(nodes) >= max_nodes,
                    },
                }
        except Exception as e:
            logger.warning(f"[pg-graph] subgraph query failed: {e}")
            return {"nodes": [], "edges": [], "stats": {}}
        finally:
            self._pool.putconn(conn)

    def update_node_positions(self, user_id: str, positions: List[Dict]) -> int:
        """Batch update 3D positions for nodes. Returns count of updated nodes."""
        if not self._enabled or not positions:
            return 0
        valid_positions = []
        for pos in positions:
            try:
                values = [float(pos[key]) for key in ("x", "y", "z")]
                if not all(math.isfinite(value) and abs(value) <= 10000 for value in values):
                    continue
                uuid.UUID(str(pos["node_id"]))
                valid_positions.append({"node_id": str(pos["node_id"]), "x": values[0], "y": values[1], "z": values[2]})
            except (KeyError, TypeError, ValueError, OverflowError):
                continue
        if not valid_positions:
            return 0
        conn = self._pool.getconn()
        try:
            updated = 0
            with conn.cursor() as cur:
                for pos in valid_positions:
                    cur.execute(
                        """
                        UPDATE mvfe_graph_nodes
                        SET position_x = %s, position_y = %s, position_z = %s, updated_at = NOW()
                        WHERE id = %s::uuid AND user_id = %s
                        """,
                        (pos.get("x"), pos.get("y"), pos.get("z"), pos["node_id"], user_id),
                    )
                    updated += cur.rowcount
                conn.commit()
            return updated
        except Exception as e:
            conn.rollback()
            logger.warning(f"[pg-graph] position update failed: {e}")
            return 0
        finally:
            self._pool.putconn(conn)

    def get_graph_stats(self, user_id: str) -> Dict:
        """Return summary statistics for a user's graph."""
        if not self._enabled:
            return {}
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM mvfe_graph_nodes WHERE user_id = %s", (user_id,))
                node_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM mvfe_graph_edges WHERE user_id = %s", (user_id,))
                edge_count = cur.fetchone()[0]
                cur.execute(
                    "SELECT node_type, COUNT(*) FROM mvfe_graph_nodes WHERE user_id = %s GROUP BY node_type",
                    (user_id,)
                )
                type_counts = {r[0]: r[1] for r in cur.fetchall()}
                cur.execute(
                    """
                    SELECT COUNT(*) FILTER (
                               WHERE position_x IS NOT NULL
                                 AND position_y IS NOT NULL
                                 AND position_z IS NOT NULL
                           ),
                           MAX(updated_at)
                    FROM mvfe_graph_nodes
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )
                positioned_count, last_updated = cur.fetchone()
                cur.execute(
                    """
                    SELECT COUNT(*), COUNT(*) FILTER (WHERE status='REVIEWED')
                    FROM mvfe_graph_events WHERE user_id=%s
                    """,
                    (user_id,),
                )
                event_count, reviewed_event_count = cur.fetchone()
                cur.execute(LOOP_DETECTION_CTE, {"user_id": user_id})
                loop_count = len(cur.fetchall())
                return {
                    "user_id": user_id,
                    "node_count": node_count,
                    "edge_count": edge_count,
                    "node_types": type_counts,
                    "positioned_node_count": positioned_count,
                    "position_coverage": round(positioned_count / node_count, 4) if node_count else 0.0,
                    "last_updated": last_updated.isoformat() if last_updated else None,
                    "loop_count": loop_count,
                    "event_count": int(event_count or 0),
                    "reviewed_event_count": int(reviewed_event_count or 0),
                }
        except Exception as e:
            logger.warning(f"[pg-graph] stats query failed: {e}")
            return {}
        finally:
            self._pool.putconn(conn)

    def find_semantic_anchors(
        self,
        user_id: str,
        query_text: str,
        principles: Optional[List[Dict[str, Any]]] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Resolve semantic/vector matches to user or canonical graph nodes."""
        if not self._enabled:
            return []
        raw_terms = [query_text]
        for principle in principles or []:
            raw_terms.extend([
                str(principle.get("title") or principle.get("principle_id") or ""),
                str(principle.get("text") or principle.get("content") or ""),
                str(principle.get("category") or ""),
            ])
        aliases = {
            "焦虑": ["anxiety", "fear"], "恐惧": ["fear", "anxiety"],
            "逃避": ["avoidance", "withdrawal", "procrastination"],
            "羞耻": ["shame"], "骄傲": ["pride"], "孤独": ["loneliness"],
            "控制": ["control", "micromanaging"], "干渴": ["dryness", "emptiness"],
            "安息": ["rest"], "真理": ["truth"], "谦卑": ["humility"],
        }
        terms = set()
        combined = " ".join(raw_terms).lower()
        for raw in raw_terms:
            for token in str(raw).lower().replace("_", " ").split():
                if len(token) >= 3:
                    terms.add(token[:80])
        for zh, values in aliases.items():
            if zh in combined:
                terms.update(values)
        if not terms:
            return []
        patterns = [f"%{term}%" for term in sorted(terms)[:24]]
        pattern_text = chr(31).join(patterns)
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, node_type, node_name, properties, strength
                    FROM mvfe_graph_nodes
                    WHERE user_id IN (%s, '__system__')
                      AND EXISTS (
                          SELECT 1
                          FROM unnest(string_to_array(%s, CHR(31))) AS search(pattern)
                          WHERE node_name ILIKE search.pattern
                             OR properties::text ILIKE search.pattern
                      )
                    ORDER BY CASE WHEN user_id = %s THEN 0 ELSE 1 END,
                             strength DESC, updated_at DESC
                    LIMIT %s
                    """,
                    (user_id, pattern_text, user_id, limit),
                )
                return [
                    {
                        "node_id": str(row[0]), "graph_user_id": row[1],
                        "node_type": row[2], "node_name": row[3],
                        "properties": row[4] if isinstance(row[4], dict) else {},
                        "strength": float(row[5] or 1.0),
                    }
                    for row in cur.fetchall()
                ]
        except Exception as exc:
            logger.warning("[pg-graph] semantic anchor lookup failed: %s", exc)
            return []
        finally:
            self._pool.putconn(conn)

    @staticmethod
    def _stable_position(node_id: str, depth: int, index: int) -> Dict[str, float]:
        """Deterministic spherical coordinates, avoiding runtime force layout."""
        digest = hashlib.sha256(node_id.encode("utf-8")).digest()
        u = int.from_bytes(digest[:8], "big") / float(2**64 - 1)
        v = int.from_bytes(digest[8:16], "big") / float(2**64 - 1)
        theta = 2.0 * math.pi * u
        phi = math.acos(max(-1.0, min(1.0, 2.0 * v - 1.0)))
        radius = 3.0 + max(0, depth) * 3.25 + (index % 3) * 0.2
        return {
            "x": round(radius * math.sin(phi) * math.cos(theta), 4),
            "y": round(radius * math.cos(phi), 4),
            "z": round(radius * math.sin(phi) * math.sin(theta), 4),
        }

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
                     edge_type: str, weight: float = 1.0,
                     properties: Optional[Dict[str, Any]] = None):
        """
        UPSERT an edge; increment traversal_count on conflict.
        """
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO mvfe_graph_edges
                        (user_id, source_id, target_id, edge_type, weight, properties)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, source_id, target_id, edge_type) DO UPDATE
                       SET traversal_count = mvfe_graph_edges.traversal_count + 1,
                           weight          = GREATEST(mvfe_graph_edges.weight, EXCLUDED.weight),
                           properties      = mvfe_graph_edges.properties || EXCLUDED.properties,
                           updated_at      = NOW()
                    """,
                    (user_id, source_id, target_id, edge_type, weight,
                     json.dumps(properties or {})),
                )
                conn.commit()
        finally:
            self._pool.putconn(conn)

    def persist_formation_chain(
        self,
        user_id: str,
        event_id: str,
        *,
        emotion_name: str,
        desire_name: str,
        behavior_name: str,
        decision_category: str,
        outcome_name: Optional[str] = None,
        belief_name: Optional[str] = None,
        matched_patterns: Optional[List[str]] = None,
    ) -> bool:
        """Atomically persist aggregate graph structure and its history event."""
        if not self._enabled:
            return False
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                def node(node_type: str, name: str, props: Dict[str, Any], strength: float = 1.0):
                    cur.execute(
                        """
                        INSERT INTO mvfe_graph_nodes
                            (user_id, node_type, node_name, properties, strength)
                        VALUES (%s,%s,%s,%s,%s)
                        ON CONFLICT (user_id, node_type, node_name) DO UPDATE
                        SET properties=mvfe_graph_nodes.properties || EXCLUDED.properties,
                            strength=GREATEST(mvfe_graph_nodes.strength, EXCLUDED.strength),
                            updated_at=NOW()
                        RETURNING id
                        """,
                        (user_id, node_type, name, json.dumps(props), strength),
                    )
                    return cur.fetchone()[0]

                def edge(source_id, target_id, edge_type: str, *, weight: float = 1.0,
                         evidence_status: str = "observed"):
                    cur.execute(
                        """
                        INSERT INTO mvfe_graph_edges
                            (user_id, source_id, target_id, edge_type, weight, properties)
                        VALUES (%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (user_id, source_id, target_id, edge_type) DO UPDATE
                        SET traversal_count=mvfe_graph_edges.traversal_count + 1,
                            weight=GREATEST(mvfe_graph_edges.weight, EXCLUDED.weight),
                            properties=mvfe_graph_edges.properties || EXCLUDED.properties,
                            updated_at=NOW()
                        """,
                        (user_id, source_id, target_id, edge_type, weight,
                         json.dumps({"evidence_status": evidence_status})),
                    )

                emotion_id = node("Emotion", emotion_name, {
                    "category": decision_category, "last_decision_id": event_id,
                    "evidence_status": "observed",
                })
                desire_id = node("Desire", desire_name, {
                    "last_decision_id": event_id, "evidence_status": "inferred",
                })
                behavior_id = node("Behavior", behavior_name, {
                    "last_decision_id": event_id, "evidence_status": "observed",
                })
                edge(emotion_id, desire_id, "CAUSES", evidence_status="inferred")
                edge(desire_id, behavior_id, "DRIVES")

                if outcome_name:
                    resolved_belief = belief_name or f"reflection:{desire_name}"
                    outcome_id = node("Outcome", outcome_name, {
                        "last_decision_id": event_id, "evidence_status": "reviewed",
                    })
                    belief_id = node("Belief", resolved_belief, {
                        "last_decision_id": event_id,
                        "evidence_status": "user_reviewed" if belief_name else "hypothesis",
                    })
                    edge(behavior_id, outcome_id, "LEADS_TO", evidence_status="reviewed")
                    edge(
                        outcome_id, belief_id, "REINFORCES",
                        evidence_status="reviewed" if belief_name else "inferred",
                    )
                    edge(
                        belief_id, emotion_id, "AMPLIFIES",
                        weight=0.7 if belief_name else 0.4,
                        evidence_status="reviewed" if belief_name else "inferred",
                    )

                if matched_patterns:
                    user_state_id = node("UserState", user_id, {})
                    for pattern_id in matched_patterns:
                        pattern_node_id = node("PatternMatch", pattern_id, {
                            "last_decision_id": event_id,
                        })
                        edge(user_state_id, pattern_node_id, "MATCHED_PATTERN")

                cur.execute(
                    """
                    INSERT INTO mvfe_graph_events
                        (user_id, event_id, emotion_name, desire_name, behavior_name,
                         outcome_name, belief_name, status, matched_patterns, properties,
                         reviewed_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                            CASE WHEN %s IS NULL THEN NULL ELSE NOW() END)
                    ON CONFLICT (user_id, event_id) DO UPDATE
                    SET emotion_name=EXCLUDED.emotion_name,
                        desire_name=EXCLUDED.desire_name,
                        behavior_name=EXCLUDED.behavior_name,
                        outcome_name=COALESCE(EXCLUDED.outcome_name, mvfe_graph_events.outcome_name),
                        belief_name=COALESCE(EXCLUDED.belief_name, mvfe_graph_events.belief_name),
                        status=EXCLUDED.status,
                        matched_patterns=EXCLUDED.matched_patterns,
                        properties=mvfe_graph_events.properties || EXCLUDED.properties,
                        reviewed_at=COALESCE(EXCLUDED.reviewed_at, mvfe_graph_events.reviewed_at),
                        updated_at=NOW()
                    """,
                    (
                        user_id, event_id, emotion_name, desire_name, behavior_name,
                        outcome_name, belief_name,
                        "REVIEWED" if outcome_name else "OBSERVED",
                        json.dumps(matched_patterns or []),
                        json.dumps({"decision_category": decision_category}),
                        outcome_name,
                    ),
                )
            conn.commit()
            return True
        except Exception as exc:
            conn.rollback()
            logger.warning("[pg-graph] atomic formation persistence failed: %s", exc)
            return False
        finally:
            self._pool.putconn(conn)

    def record_event(
        self,
        user_id: str,
        event_id: str,
        *,
        emotion_name: str,
        desire_name: str,
        behavior_name: str,
        outcome_name: Optional[str] = None,
        belief_name: Optional[str] = None,
        matched_patterns: Optional[List[str]] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Persist one auditable event while aggregate graph nodes may be reused."""
        if not self._enabled:
            return False
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO mvfe_graph_events
                        (user_id, event_id, emotion_name, desire_name, behavior_name,
                         outcome_name, belief_name, status, matched_patterns, properties,
                         reviewed_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                            CASE WHEN %s IS NULL THEN NULL ELSE NOW() END)
                    ON CONFLICT (user_id, event_id) DO UPDATE
                    SET emotion_name=EXCLUDED.emotion_name,
                        desire_name=EXCLUDED.desire_name,
                        behavior_name=EXCLUDED.behavior_name,
                        outcome_name=COALESCE(EXCLUDED.outcome_name, mvfe_graph_events.outcome_name),
                        belief_name=COALESCE(EXCLUDED.belief_name, mvfe_graph_events.belief_name),
                        status=EXCLUDED.status,
                        matched_patterns=EXCLUDED.matched_patterns,
                        properties=mvfe_graph_events.properties || EXCLUDED.properties,
                        reviewed_at=COALESCE(EXCLUDED.reviewed_at, mvfe_graph_events.reviewed_at),
                        updated_at=NOW()
                    """,
                    (
                        user_id, event_id, emotion_name, desire_name, behavior_name,
                        outcome_name, belief_name,
                        "REVIEWED" if outcome_name else "OBSERVED",
                        json.dumps(matched_patterns or []), json.dumps(properties or {}),
                        outcome_name,
                    ),
                )
                conn.commit()
            return True
        except Exception as exc:
            conn.rollback()
            logger.warning("[pg-graph] event persistence failed: %s", exc)
            return False
        finally:
            self._pool.putconn(conn)

    def get_event(self, user_id: str, event_id: str) -> Optional[Dict[str, Any]]:
        if not self._enabled:
            return None
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT emotion_name, desire_name, behavior_name, outcome_name,
                           belief_name, matched_patterns, properties
                    FROM mvfe_graph_events
                    WHERE user_id=%s AND event_id=%s
                    """,
                    (user_id, event_id),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "emotion_name": row[0], "desire_name": row[1],
                    "behavior_name": row[2], "outcome_name": row[3],
                    "belief_name": row[4], "matched_patterns": row[5] or [],
                    "properties": row[6] or {},
                }
        finally:
            self._pool.putconn(conn)

    def get_events(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Return a bounded, newest-first history of formation chains."""
        if not self._enabled:
            return []
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT event_id, emotion_name, desire_name, behavior_name,
                           outcome_name, belief_name, status, matched_patterns,
                           observed_at, reviewed_at
                    FROM mvfe_graph_events
                    WHERE user_id=%s
                    ORDER BY observed_at DESC
                    LIMIT %s
                    """,
                    (user_id, max(1, min(int(limit), 100))),
                )
                return [{
                    "event_id": row[0], "emotion": row[1], "desire": row[2],
                    "behavior": row[3], "outcome": row[4], "belief": row[5],
                    "status": row[6], "matched_patterns": row[7] or [],
                    "observed_at": row[8].isoformat() if row[8] else None,
                    "reviewed_at": row[9].isoformat() if row[9] else None,
                } for row in cur.fetchall()]
        except Exception as exc:
            logger.warning("[pg-graph] event history query failed: %s", exc)
            return []
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
