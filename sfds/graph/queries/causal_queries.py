"""
Graph Queries — Causal Chain Tracing

Cypher queries for upstream causal path tracing.
"""

from typing import Any, Dict, List


def trace_upstream(driver, behavior_type: str) -> List[Dict[str, Any]]:
    """
    Trace most probable upstream causes for a behavior type.
    Follows CAUSES edges backward from BehaviorNode.
    """
    if not driver:
        return []
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH path = (root)-[:CAUSES|LEADS_TO*1..4]->(b:BehaviorNode {type: $behavior})
                WHERE NOT ()-[:CAUSES]->(root)
                RETURN
                    [node in nodes(path) | node.type] AS chain,
                    length(path)                       AS depth
                ORDER BY depth DESC
                LIMIT 3
                """,
                behavior=behavior_type,
            )
            return [dict(r) for r in result]
    except Exception:
        return []
