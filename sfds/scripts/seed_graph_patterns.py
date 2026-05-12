#!/usr/bin/env python3
"""
Seed Script — Neo4j Graph Patterns

Seeds all patterns from graph/patterns/library.py into Neo4j.
Run: python scripts/seed_graph_patterns.py
"""

import os
import sys

_sfds_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _sfds_root)

from graph.patterns._loops_part1 import _LOOPS_A_B_C
from graph.patterns._loops_part2 import _LOOPS_D_E_F
PATTERN_LIBRARY = _LOOPS_A_B_C + _LOOPS_D_E_F


def _node_label(node_type: str) -> str:
    """Map known emotion/motive names to their graph label; default BehaviorNode."""
    emotions = {
        "fear", "anxiety", "shame", "pride", "guilt", "grief", "joy",
        "peace", "loneliness", "spiritual_dryness", "confusion", "discomfort",
        "love", "desire", "drivenness",
    }
    motives = {
        "control_drive", "approval_seeking", "self_sufficiency", "need_to_win",
        "avoidance", "truth_seeking", "love_orientation",
    }
    if node_type in emotions:
        return "EmotionNode"
    if node_type in motives:
        return "MotiveNode"
    if node_type.startswith("principle_"):
        return "PrincipleNode"
    return "BehaviorNode"


def seed(uri: str, user: str, password: str) -> None:
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(uri, auth=(user, password))

    with driver.session() as session:
        seeded = 0
        for pattern in PATTERN_LIBRARY:
            pid = pattern["id"]
            cat = pattern["category"]
            loop_type = pattern["loop_type"]
            trigger = pattern.get("trigger_emotion", "")
            print(f"  [{cat}] {pid}")

            # Seed chain nodes
            for node_type in pattern["chain"]:
                label = _node_label(node_type)
                session.run(
                    f"MERGE (n:{label} {{type: $t}}) "
                    "SET n.pattern_id = $pid, n.category = $cat, "
                    "n.loop_type = $lt, n.trigger_emotion = $trigger",
                    t=node_type, pid=pid, cat=cat, lt=loop_type, trigger=trigger,
                )

            # Seed causal + reinforcement edges
            for (src, edge_type, tgt) in pattern["edges"]:
                session.run(
                    f"""
                    MATCH (a {{type: $a}}), (b {{type: $b}})
                    MERGE (a)-[:{edge_type} {{pattern_id: $pid, loop_type: $lt}}]->(b)
                    """,
                    a=src, b=tgt, pid=pid, lt=loop_type,
                )

            # Seed break edges (principle → node)
            for (principle_id, edge_type, tgt) in pattern.get("break_edges", []):
                session.run(
                    """
                    MERGE (p:PrincipleNode {id: $pid})
                    WITH p
                    MATCH (t {type: $tgt})
                    MERGE (p)-[:BREAKS {pattern_id: $pat_id}]->(t)
                    """,
                    pid=principle_id, tgt=tgt, pat_id=pid,
                )

            seeded += 1

        print(f"\n✓ Seeded {seeded} patterns ({len(PATTERN_LIBRARY)} total) into Neo4j.")
    driver.close()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    seed(
        uri      = os.getenv("NEO4J_URI",      "bolt://localhost:7687"),
        user     = os.getenv("NEO4J_USER",     "neo4j"),
        password = os.getenv("NEO4J_PASSWORD", ""),
    )
