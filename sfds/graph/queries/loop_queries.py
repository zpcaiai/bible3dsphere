"""
Graph Queries — Loop Detection

Reusable Cypher query functions for behavioral loop detection.
All queries use parameterized inputs — never string interpolation.
"""

from typing import Any, Dict, List


def detect_active_loops(
    driver, user_id: str
) -> List[Dict[str, Any]]:
    """
    Detect behavioral loops active for a user.
    Finds REINFORCES edges in the user's behavior subgraph.
    """
    if not driver:
        return []
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (u:UserStateNode {user_id: $uid})-[:HAS_STATE]->(e)
                MATCH path = (e)-[:CAUSES|LEADS_TO*1..5]->(b)
                MATCH (b)-[r:REINFORCES]->(target)
                RETURN
                    b.type          AS source_node,
                    r.pattern_id    AS pattern_id,
                    target.type     AS target_node,
                    COUNT(r)        AS recurrence
                ORDER BY recurrence DESC
                LIMIT 5
                """,
                uid=user_id,
            )
            return [dict(record) for record in result]
    except Exception:
        return []


def get_loop_intensity(driver, user_id: str, pattern_id: str) -> float:
    """
    Measure how entrenched a specific loop is for this user.
    Returns 0–1 intensity score based on edge recurrence count.
    """
    if not driver:
        return 0.0
    try:
        with driver.session() as session:
            count = session.run(
                """
                MATCH (u:UserStateNode {user_id: $uid})-[:HAS_STATE*1..3]->(n)
                MATCH (n)-[r:LEADS_TO {pattern_id: $pid}]->()
                RETURN COUNT(r) AS count
                """,
                uid=user_id, pid=pattern_id,
            ).single()
            raw = count["count"] if count else 0
            return min(0.95, raw * 0.1)
    except Exception:
        return 0.0
