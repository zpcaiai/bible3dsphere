#!/usr/bin/env python3
"""
Graph Health Checker — Data governance for the PostgreSQL graph layer.

Provides:
- Isolated node detection (nodes with no edges)
- Dangling edge detection (edges referencing non-existent nodes)
- Connected component analysis
- Auto-repair capabilities
- Dynamic edge weight updates based on user interaction

Design: Operates as a maintenance/governance module, not part of the
hot path. Can be run as a scheduled check or admin API call.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class GraphHealthReport:
    """Complete graph health assessment."""
    timestamp: str = ""
    total_nodes: int = 0
    total_edges: int = 0
    isolated_nodes: List[Dict[str, Any]] = field(default_factory=list)
    dangling_edges: List[Dict[str, Any]] = field(default_factory=list)
    connected_components: int = 0
    max_loop_depth: int = 0
    repairs_made: int = 0
    status: str = "healthy"  # healthy | warning | critical

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "isolated_node_count": len(self.isolated_nodes),
            "isolated_nodes": self.isolated_nodes[:20],  # Cap for API response
            "dangling_edge_count": len(self.dangling_edges),
            "dangling_edges": self.dangling_edges[:20],
            "connected_components": self.connected_components,
            "max_loop_depth": self.max_loop_depth,
            "repairs_made": self.repairs_made,
            "status": self.status,
        }


class GraphHealthChecker:
    """Graph data governance and integrity checker."""

    def __init__(self, db_pool=None):
        self._pool = db_pool
        self._enabled = db_pool is not None

    @property
    def enabled(self) -> bool:
        return self._enabled

    def find_isolated_nodes(self, user_id: str = None) -> List[Dict[str, Any]]:
        """Find nodes with zero incoming and zero outgoing edges."""
        if not self._enabled:
            return []
        from mvfe.db.graph_schema import ISOLATED_NODES_SQL
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(ISOLATED_NODES_SQL, {"user_id": user_id})
                return [
                    {"id": str(r[0]), "node_type": r[1], "node_name": r[2], "user_id": r[3]}
                    for r in cur.fetchall()
                ]
        except Exception as e:
            logger.warning(f"[graph-health] isolated nodes query failed: {e}")
            return []
        finally:
            self._pool.putconn(conn)

    def find_dangling_edges(self, user_id: str = None) -> List[Dict[str, Any]]:
        """Find edges that reference non-existent source or target nodes."""
        if not self._enabled:
            return []
        from mvfe.db.graph_schema import DANGLING_EDGES_SQL
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(DANGLING_EDGES_SQL, {"user_id": user_id})
                return [
                    {"id": str(r[0]), "source_id": str(r[1]),
                     "target_id": str(r[2]), "edge_type": r[3]}
                    for r in cur.fetchall()
                ]
        except Exception as e:
            logger.warning(f"[graph-health] dangling edges query failed: {e}")
            return []
        finally:
            self._pool.putconn(conn)

    def count_connected_components(self, user_id: str = None) -> int:
        """Count the number of connected components in a user's graph."""
        if not self._enabled:
            return 0
        from mvfe.db.graph_schema import CONNECTED_COMPONENTS_SQL
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(CONNECTED_COMPONENTS_SQL, {"user_id": user_id})
                row = cur.fetchone()
                return int(row[0] or 0) if row else 0
        except Exception as e:
            logger.warning(f"[graph-health] component count failed: {e}")
            return 0
        finally:
            self._pool.putconn(conn)

    def auto_repair(self, user_id: str = None) -> Dict[str, Any]:
        """
        Auto-repair graph integrity issues:
        1. Remove dangling edges (referencing non-existent nodes)
        2. Mark isolated nodes for review (never invent semantically unsafe edges)
        """
        if not self._enabled:
            return {"repaired": False, "reason": "db not connected"}

        repairs = 0
        canonical_reseed = {"nodes": 0, "edges": 0}
        if user_id in (None, "__system__"):
            try:
                from graph_layer import seed_patterns_to_postgres
                canonical_reseed = seed_patterns_to_postgres(self._pool)
            except Exception as exc:
                logger.warning("[graph-health] canonical pattern reseed failed: %s", exc)
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                # Remove dangling edges
                cur.execute(
                    """
                    DELETE FROM mvfe_graph_edges e
                    WHERE (
                        NOT EXISTS (SELECT 1 FROM mvfe_graph_nodes n WHERE n.id = e.source_id)
                        OR NOT EXISTS (SELECT 1 FROM mvfe_graph_nodes n WHERE n.id = e.target_id)
                    )
                      AND (%s IS NULL OR e.user_id = %s)
                    """,
                    (user_id, user_id),
                )
                repairs += cur.rowcount
                dangling_removed = cur.rowcount
                # A PatternMatch has one deterministic owner edge. Restore it
                # only when the same user's UserState exists; no meaning is guessed.
                cur.execute(
                    """
                    INSERT INTO mvfe_graph_edges
                        (user_id, source_id, target_id, edge_type, properties)
                    SELECT pattern.user_id, state.id, pattern.id, 'MATCHED_PATTERN',
                           '{"auto_repaired": true}'::jsonb
                    FROM mvfe_graph_nodes pattern
                    JOIN mvfe_graph_nodes state
                      ON state.user_id=pattern.user_id
                     AND state.node_type='UserState'
                    WHERE pattern.node_type='PatternMatch'
                      AND (%s IS NULL OR pattern.user_id=%s)
                      AND NOT EXISTS (
                          SELECT 1 FROM mvfe_graph_edges existing
                          WHERE existing.source_id=pattern.id OR existing.target_id=pattern.id
                      )
                    ON CONFLICT (user_id, source_id, target_id, edge_type) DO NOTHING
                    """,
                    (user_id, user_id),
                )
                deterministic_edges_restored = cur.rowcount
                repairs += deterministic_edges_restored
                cur.execute(
                    """
                    UPDATE mvfe_graph_nodes n
                    SET properties = n.properties || jsonb_build_object(
                            'graph_health', 'isolated',
                            'graph_health_checked_at', NOW()::text
                        ),
                        updated_at = NOW()
                    WHERE (%s IS NULL OR n.user_id = %s)
                      AND NOT EXISTS (
                          SELECT 1 FROM mvfe_graph_edges e
                          WHERE e.source_id = n.id OR e.target_id = n.id
                      )
                      AND COALESCE(n.properties->>'graph_health', '') <> 'isolated'
                    """,
                    (user_id, user_id),
                )
                isolated_marked = cur.rowcount
                repairs += isolated_marked
                conn.commit()

            return {
                "repaired": True,
                "dangling_edges_removed": dangling_removed,
                "deterministic_edges_restored": deterministic_edges_restored,
                "isolated_nodes_marked": isolated_marked,
                "canonical_pattern_upserts": canonical_reseed,
                "repairs_made": repairs,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            conn.rollback()
            logger.warning(f"[graph-health] auto-repair failed: {e}")
            return {"repaired": False, "reason": str(e)}
        finally:
            self._pool.putconn(conn)

    def full_report(self, user_id: str = None) -> GraphHealthReport:
        """Generate a comprehensive graph health report."""
        report = GraphHealthReport(
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        if not self._enabled:
            report.status = "disabled"
            return report

        from mvfe.db.graph_schema import GRAPH_HEALTH_CHECK_SQL, LOOP_DETECTION_CTE
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(GRAPH_HEALTH_CHECK_SQL, {"user_id": user_id})
                counts = cur.fetchone()
                if counts:
                    report.total_nodes = int(counts[0] or 0)
                    report.total_edges = int(counts[1] or 0)
                if user_id:
                    cur.execute(LOOP_DETECTION_CTE, {"user_id": user_id})
                    loop_rows = cur.fetchall()
                    report.max_loop_depth = max((int(row[2]) for row in loop_rows), default=0)

        except Exception as e:
            logger.warning(f"[graph-health] report generation failed: {e}")
            report.status = "error"
        finally:
            self._pool.putconn(conn)

        if report.status == "error":
            return report
        report.isolated_nodes = self.find_isolated_nodes(user_id)
        report.dangling_edges = self.find_dangling_edges(user_id)
        report.connected_components = self.count_connected_components(user_id)
        if report.dangling_edges:
            report.status = "critical"
        elif report.total_nodes and len(report.isolated_nodes) > report.total_nodes * 0.2:
            report.status = "warning"
        else:
            report.status = "healthy"

        return report


def update_edge_weight_on_interaction(
    db_pool,
    user_id: str,
    source_node_id: str,
    target_node_id: str,
    interaction_type: str = "click",
) -> bool:
    """
    Increment edge weight and traversal_count when a user interacts
    with a relationship (e.g., clicks a connection in the 3D sphere).

    Args:
        db_pool: PostgreSQL connection pool
        user_id: The user performing the interaction
        source_node_id: UUID of the source node
        target_node_id: UUID of the target node
        interaction_type: Type of interaction (click, hover, expand)

    Returns:
        True if an edge was updated, False otherwise
    """
    if not db_pool:
        return False

    weight_increment = {
        "click": 0.1,
        "hover": 0.02,
        "expand": 0.15,
        "bookmark": 0.3,
    }.get(interaction_type, 0.05)

    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE mvfe_graph_edges
                SET weight = LEAST(weight + %s, 10.0),
                    traversal_count = traversal_count + 1,
                    updated_at = NOW()
                WHERE user_id = %s
                  AND source_id = %s::uuid
                  AND target_id = %s::uuid
                RETURNING id
                """,
                (weight_increment, user_id, source_node_id, target_node_id),
            )
            updated = cur.fetchone() is not None
            conn.commit()
            return updated
    except Exception as e:
        conn.rollback()
        logger.warning(f"[graph-health] edge weight update failed: {e}")
        return False
    finally:
        db_pool.putconn(conn)


# Module singleton
_health_checker: Optional[GraphHealthChecker] = None


def get_health_checker() -> GraphHealthChecker:
    global _health_checker
    if _health_checker is None:
        _health_checker = GraphHealthChecker()
    return _health_checker


def init_health_checker(db_pool) -> GraphHealthChecker:
    global _health_checker
    _health_checker = GraphHealthChecker(db_pool=db_pool)
    return _health_checker
