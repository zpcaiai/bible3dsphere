"""
Graph Queries — Intervention Point Identification

Finds highest-leverage nodes where formation change is most accessible.
Leverage hierarchy: PrincipleNode > EmotionNode > MotiveNode > BehaviorNode > OutcomeNode
"""

from typing import Any, Dict, List


LEVERAGE_SCORES = {
    "PrincipleNode": 1.00,
    "EmotionNode":   0.95,
    "MotiveNode":    0.90,
    "SpiritualNode": 0.85,
    "BehaviorNode":  0.65,
    "OutcomeNode":   0.30,
}


def find_interventions(driver, user_id: str) -> List[Dict[str, Any]]:
    """
    Find highest-leverage intervention points in the user's behavioral subgraph.
    Returns nodes sorted by leverage score.
    """
    if not driver:
        return []
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (u:UserStateNode {user_id: $uid})-[:HAS_STATE*1..4]->(n)
                WHERE n:EmotionNode OR n:MotiveNode OR n:PrincipleNode
                RETURN
                    labels(n)[0] AS node_label,
                    n.type       AS node_type,
                    COUNT(n)     AS recurrence
                ORDER BY recurrence DESC
                LIMIT 8
                """,
                uid=user_id,
            )
            points = []
            for r in result:
                record = dict(r)
                label = record.get("node_label", "BehaviorNode")
                record["leverage_score"] = LEVERAGE_SCORES.get(label, 0.50)
                points.append(record)
            points.sort(key=lambda x: x["leverage_score"], reverse=True)
            return points[:4]
    except Exception:
        return []
